from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import app.services.audit_bundle_replay_alert_corpus as _audit_bundle_replay_alert_corpus
import app.services.audit_bundle_training_runs as _audit_bundle_training_runs
from app.core.hashes import payload_sha256 as _payload_sha256
from app.db.models import (
    AuditBundleExport,
    AuditBundleValidationReceipt,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchReplayRun,
)
from app.services.audit_bundle_release_payload_prov import prov_graph
from app.services.audit_bundle_release_payload_serialization import (
    SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
    SEARCH_HARNESS_RELEASE_SOURCE_TABLE,
    audit_bundle_reference_payload,
    evaluation_payload,
    release_payload,
    replay_payload,
    retrieval_learning_candidate_payload,
    retrieval_reranker_artifact_payload,
    semantic_governance_event_payload,
    source_payload,
    validation_receipt_reference_payload,
)
from app.services.search_release_shared import release_package_sha256 as _release_package_sha256
from app.services.semantic_governance import (
    search_harness_release_semantic_governance_context,
)

_training_audit_bundle_claim_support_replay_alert_corpus_lineage_status = (
    _audit_bundle_replay_alert_corpus.training_audit_bundle_claim_support_replay_alert_corpus_lineage_status
)


def build_search_harness_release_payload(
    session: Session,
    *,
    release: SearchHarnessRelease,
    bundle_id: UUID,
    created_by: str | None,
    created_at,
) -> dict[str, object]:
    evaluation = session.get(SearchHarnessEvaluation, release.search_harness_evaluation_id)
    sources = (
        session.execute(
            select(SearchHarnessEvaluationSource)
            .where(
                SearchHarnessEvaluationSource.search_harness_evaluation_id
                == release.search_harness_evaluation_id
            )
            .order_by(SearchHarnessEvaluationSource.source_index.asc())
        )
        .scalars()
        .all()
    )
    replay_run_ids: list[UUID] = []
    for source in sources:
        replay_run_ids.extend([source.baseline_replay_run_id, source.candidate_replay_run_id])
    replay_runs = (
        session.execute(select(SearchReplayRun).where(SearchReplayRun.id.in_(replay_run_ids)))
        .scalars()
        .all()
        if replay_run_ids
        else []
    )
    replay_runs_by_id = {row.id: row for row in replay_runs}
    ordered_replay_runs = [
        replay_runs_by_id[replay_run_id]
        for replay_run_id in replay_run_ids
        if replay_run_id in replay_runs_by_id
    ]
    learning_candidates = (
        session.execute(
            select(RetrievalLearningCandidateEvaluation)
            .where(
                or_(
                    RetrievalLearningCandidateEvaluation.search_harness_release_id == release.id,
                    RetrievalLearningCandidateEvaluation.search_harness_evaluation_id
                    == release.search_harness_evaluation_id,
                )
            )
            .order_by(RetrievalLearningCandidateEvaluation.created_at.asc())
        )
        .scalars()
        .all()
    )
    learning_candidates_by_id = {row.id: row for row in learning_candidates}
    learning_candidate_ids = set(learning_candidates_by_id)
    reranker_artifact_conditions = [
        RetrievalRerankerArtifact.search_harness_release_id == release.id
    ]
    if learning_candidate_ids:
        reranker_artifact_conditions.append(
            RetrievalRerankerArtifact.retrieval_learning_candidate_evaluation_id.in_(
                learning_candidate_ids
            )
        )
    reranker_artifacts = (
        session.execute(
            select(RetrievalRerankerArtifact)
            .where(or_(*reranker_artifact_conditions))
            .order_by(RetrievalRerankerArtifact.created_at.asc())
        )
        .scalars()
        .all()
    )
    artifact_candidate_ids = {
        row.retrieval_learning_candidate_evaluation_id for row in reranker_artifacts
    }
    missing_candidate_ids = sorted(artifact_candidate_ids - learning_candidate_ids, key=str)
    if missing_candidate_ids:
        extra_candidates = (
            session.execute(
                select(RetrievalLearningCandidateEvaluation)
                .where(RetrievalLearningCandidateEvaluation.id.in_(missing_candidate_ids))
                .order_by(RetrievalLearningCandidateEvaluation.created_at.asc())
            )
            .scalars()
            .all()
        )
        for row in extra_candidates:
            learning_candidates_by_id[row.id] = row
        learning_candidates = sorted(
            learning_candidates_by_id.values(),
            key=lambda row: (row.created_at, str(row.id)),
        )
        learning_candidate_ids = set(learning_candidates_by_id)
    training_run_ids = sorted(
        {
            *(row.retrieval_training_run_id for row in learning_candidates),
            *(row.retrieval_training_run_id for row in reranker_artifacts),
        },
        key=str,
    )
    judgment_set_ids = sorted(
        {
            *(row.judgment_set_id for row in learning_candidates),
            *(row.judgment_set_id for row in reranker_artifacts),
        },
        key=str,
    )
    candidate_governance_event_ids = sorted(
        {
            row.semantic_governance_event_id
            for row in learning_candidates
            if row.semantic_governance_event_id is not None
        },
        key=str,
    )
    reranker_artifact_governance_event_ids = sorted(
        {
            row.semantic_governance_event_id
            for row in reranker_artifacts
            if row.semantic_governance_event_id is not None
        },
        key=str,
    )
    training_runs = (
        session.execute(
            select(RetrievalTrainingRun).where(RetrievalTrainingRun.id.in_(training_run_ids))
        )
        .scalars()
        .all()
        if training_run_ids
        else []
    )
    judgment_sets = (
        session.execute(
            select(RetrievalJudgmentSet).where(RetrievalJudgmentSet.id.in_(judgment_set_ids))
        )
        .scalars()
        .all()
        if judgment_set_ids
        else []
    )
    semantic_governance_context = search_harness_release_semantic_governance_context(
        session,
        release,
    )
    ordered_governance_events = semantic_governance_context["events"]
    semantic_governance_policy = semantic_governance_context["policy"]
    training_runs_by_id = {row.id: row for row in training_runs}
    judgment_sets_by_id = {row.id: row for row in judgment_sets}
    ordered_training_runs = [
        training_runs_by_id[training_run_id]
        for training_run_id in training_run_ids
        if training_run_id in training_runs_by_id
    ]
    ordered_judgment_sets = [
        judgment_sets_by_id[judgment_set_id]
        for judgment_set_id in judgment_set_ids
        if judgment_set_id in judgment_sets_by_id
    ]
    training_audit_bundle_rows = (
        session.execute(
            select(AuditBundleExport)
            .where(
                AuditBundleExport.retrieval_training_run_id.in_(training_run_ids),
                AuditBundleExport.bundle_kind
                == _audit_bundle_training_runs.RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
            )
            .order_by(
                AuditBundleExport.retrieval_training_run_id.asc(),
                AuditBundleExport.created_at.desc(),
                AuditBundleExport.id.asc(),
            )
        )
        .scalars()
        .all()
        if training_run_ids
        else []
    )
    latest_training_audit_bundles_by_run_id: dict[UUID, AuditBundleExport] = {}
    for row in training_audit_bundle_rows:
        if row.retrieval_training_run_id is None:
            continue
        latest_training_audit_bundles_by_run_id.setdefault(row.retrieval_training_run_id, row)
    ordered_training_audit_bundles = [
        latest_training_audit_bundles_by_run_id[training_run_id]
        for training_run_id in training_run_ids
        if training_run_id in latest_training_audit_bundles_by_run_id
    ]
    training_audit_bundle_ids = [row.id for row in ordered_training_audit_bundles]
    validation_receipt_rows = (
        session.execute(
            select(AuditBundleValidationReceipt)
            .where(
                AuditBundleValidationReceipt.audit_bundle_export_id.in_(training_audit_bundle_ids)
            )
            .order_by(
                AuditBundleValidationReceipt.audit_bundle_export_id.asc(),
                AuditBundleValidationReceipt.created_at.desc(),
                AuditBundleValidationReceipt.id.asc(),
            )
        )
        .scalars()
        .all()
        if training_audit_bundle_ids
        else []
    )
    latest_validation_receipts_by_bundle_id: dict[UUID, AuditBundleValidationReceipt] = {}
    for receipt in validation_receipt_rows:
        latest_validation_receipts_by_bundle_id.setdefault(receipt.audit_bundle_export_id, receipt)
    ordered_training_validation_receipts = [
        latest_validation_receipts_by_bundle_id[bundle.id]
        for bundle in ordered_training_audit_bundles
        if bundle.id in latest_validation_receipts_by_bundle_id
    ]
    training_audit_bundle_match_checks = []
    for training_run in ordered_training_runs:
        bundle = latest_training_audit_bundles_by_run_id.get(training_run.id)
        payload = (bundle.bundle_payload_json or {}).get("payload") if bundle else None
        payload_training_run = (
            ((payload or {}).get("retrieval_training_run") if payload else None) or {}
        )
        corpus_lineage_status = (
            _training_audit_bundle_claim_support_replay_alert_corpus_lineage_status(
                session,
                bundle,
                training_run,
            )
        )
        hashes_match_training_run = (
            _audit_bundle_training_runs.training_audit_bundle_hashes_match_training_run(
                bundle,
                training_run,
            )
        )
        check = {
            "retrieval_training_run_id": str(training_run.id),
            "audit_bundle_id": str(bundle.id) if bundle else None,
            "training_dataset_sha256": training_run.training_dataset_sha256,
            "payload_training_dataset_sha256": payload_training_run.get("training_dataset_sha256"),
            "hashes_match_training_run": hashes_match_training_run,
            "claim_support_replay_alert_corpus_lineage_required": corpus_lineage_status["required"],
            "claim_support_replay_alert_corpus_lineage_complete": corpus_lineage_status[
                "complete"
            ],
            "claim_support_replay_alert_corpus_lineage_bundle_complete": corpus_lineage_status[
                "bundle_complete"
            ],
            "claim_support_replay_alert_corpus_lineage_current_complete": corpus_lineage_status[
                "current_complete"
            ],
            "claim_support_replay_alert_corpus_source_reference_count": corpus_lineage_status[
                "current_source_reference_count"
            ],
            "payload_claim_support_replay_alert_corpus_source_reference_count": (
                corpus_lineage_status["bundle_source_reference_count"]
            ),
            "claim_support_replay_alert_corpus_source_reference_counts_match": (
                corpus_lineage_status["source_reference_counts_match"]
            ),
            "claim_support_replay_alert_corpus_current_failures": corpus_lineage_status[
                "current_failures"
            ],
            "complete": hashes_match_training_run and corpus_lineage_status["complete"],
        }
        training_audit_bundle_match_checks.append(check)
    release_package_hash_matches = (
        _release_package_sha256(release) == release.release_package_sha256
    )
    all_replay_runs_present = len(ordered_replay_runs) == len(set(replay_run_ids))
    all_replay_runs_completed = bool(ordered_replay_runs) and all(
        row.status == "completed" for row in ordered_replay_runs
    )
    learning_candidate_trace_complete = (
        len(ordered_training_runs) == len(training_run_ids)
        and len(ordered_judgment_sets) == len(judgment_set_ids)
        and set(candidate_governance_event_ids).issubset(
            {row.id for row in ordered_governance_events}
        )
    )
    reranker_artifact_release_links_match = all(
        (
            artifact.search_harness_release_id is None
            or artifact.search_harness_release_id == release.id
        )
        and artifact.search_harness_evaluation_id == release.search_harness_evaluation_id
        for artifact in reranker_artifacts
    )
    reranker_artifact_candidate_links_match = all(
        artifact.retrieval_learning_candidate_evaluation_id in learning_candidate_ids
        for artifact in reranker_artifacts
    )
    reranker_artifact_hashes_match = all(
        _payload_sha256(artifact.artifact_payload_json or {}) == artifact.artifact_sha256
        and artifact.artifact_sha256
        for artifact in reranker_artifacts
    )
    reranker_artifact_change_impacts_complete = all(
        (artifact.change_impact_report_json or {}).get("schema_name")
        == "retrieval_reranker_change_impact_report"
        and _payload_sha256(artifact.change_impact_report_json or {})
        == artifact.change_impact_sha256
        and artifact.change_impact_sha256
        for artifact in reranker_artifacts
    )
    reranker_artifact_trace_complete = (
        reranker_artifact_release_links_match
        and reranker_artifact_candidate_links_match
        and len(reranker_artifact_governance_event_ids) == len(reranker_artifacts)
        and set(reranker_artifact_governance_event_ids).issubset(
            {row.id for row in ordered_governance_events}
        )
        and all(
            artifact.retrieval_training_run_id in training_runs_by_id
            and artifact.judgment_set_id in judgment_sets_by_id
            for artifact in reranker_artifacts
        )
    )
    training_audit_bundle_trace_complete = len(ordered_training_audit_bundles) == len(
        training_run_ids
    )
    training_audit_bundle_hashes_match_training_runs = (
        len(training_audit_bundle_match_checks) == len(training_run_ids)
        and all(row["hashes_match_training_run"] for row in training_audit_bundle_match_checks)
    )
    training_audit_bundle_corpus_lineage_complete = len(training_audit_bundle_match_checks) == len(
        training_run_ids
    ) and all(
        row["claim_support_replay_alert_corpus_lineage_complete"]
        for row in training_audit_bundle_match_checks
    )
    training_audit_bundle_validation_receipts_complete = len(
        ordered_training_validation_receipts
    ) == len(ordered_training_audit_bundles) and all(
        row.validation_status == "passed" for row in ordered_training_validation_receipts
    )
    audit_checklist = {
        "has_release_record": True,
        "has_evaluation_record": evaluation is not None,
        "has_evaluation_snapshot": bool(release.evaluation_snapshot_json),
        "release_package_hash_matches": release_package_hash_matches,
        "has_replay_sources": bool(sources),
        "all_replay_runs_present": all_replay_runs_present,
        "all_replay_runs_completed": all_replay_runs_completed,
        "learning_candidate_count": len(learning_candidates),
        "learning_candidate_trace_complete": learning_candidate_trace_complete,
        "reranker_artifact_count": len(reranker_artifacts),
        "reranker_artifact_trace_complete": reranker_artifact_trace_complete,
        "reranker_artifact_hashes_match": reranker_artifact_hashes_match,
        "reranker_artifact_change_impacts_complete": reranker_artifact_change_impacts_complete,
        "training_audit_bundle_trace_complete": training_audit_bundle_trace_complete,
        "training_audit_bundle_hashes_match_training_runs": (
            training_audit_bundle_hashes_match_training_runs
        ),
        "training_audit_bundle_corpus_lineage_complete": (
            training_audit_bundle_corpus_lineage_complete
        ),
        "training_audit_bundle_validation_receipts_complete": (
            training_audit_bundle_validation_receipts_complete
        ),
        "semantic_governance_policy_complete": semantic_governance_policy["complete"],
        "has_prov_graph": True,
    }
    audit_checklist["complete"] = all(
        bool(value)
        for key, value in audit_checklist.items()
        if key not in {"learning_candidate_count", "reranker_artifact_count"}
    )
    return {
        "schema_name": "search_harness_release_audit_payload",
        "schema_version": "1.1",
        "bundle_id": str(bundle_id),
        "bundle_kind": SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        "created_at": created_at.isoformat(),
        "created_by": created_by,
        "source": {
            "source_table": SEARCH_HARNESS_RELEASE_SOURCE_TABLE,
            "source_id": str(release.id),
        },
        "release": release_payload(release),
        "evaluation": evaluation_payload(evaluation),
        "evaluation_sources": [source_payload(row) for row in sources],
        "replay_runs": [replay_payload(row) for row in ordered_replay_runs],
        "retrieval_learning_candidates": [
            retrieval_learning_candidate_payload(row) for row in learning_candidates
        ],
        "retrieval_reranker_artifacts": [
            retrieval_reranker_artifact_payload(row) for row in reranker_artifacts
        ],
        "retrieval_training_runs": [
            _audit_bundle_training_runs.retrieval_training_run_payload(row)
            for row in ordered_training_runs
        ],
        "retrieval_training_audit_bundles": [
            audit_bundle_reference_payload(row) for row in ordered_training_audit_bundles
        ],
        "retrieval_training_audit_bundle_validation_receipts": [
            validation_receipt_reference_payload(row)
            for row in ordered_training_validation_receipts
        ],
        "retrieval_judgment_sets": [
            _audit_bundle_training_runs.retrieval_judgment_set_payload(row)
            for row in ordered_judgment_sets
        ],
        "semantic_governance_events": [
            semantic_governance_event_payload(row) for row in ordered_governance_events
        ],
        "semantic_governance_policy": semantic_governance_policy,
        "audit_checklist": audit_checklist,
        "integrity": {
            "release_package_hash_matches": release_package_hash_matches,
            "expected_release_package_sha256": _release_package_sha256(release),
            "stored_release_package_sha256": release.release_package_sha256,
            "replay_run_count": len(ordered_replay_runs),
            "expected_replay_run_count": len(set(replay_run_ids)),
            "retrieval_learning_candidate_count": len(learning_candidates),
            "reranker_artifact_count": len(reranker_artifacts),
            "expected_reranker_artifact_count": len(reranker_artifacts),
            "reranker_artifact_trace_complete": reranker_artifact_trace_complete,
            "reranker_artifact_release_links_match": reranker_artifact_release_links_match,
            "reranker_artifact_candidate_links_match": reranker_artifact_candidate_links_match,
            "reranker_artifact_hashes_match": reranker_artifact_hashes_match,
            "reranker_artifact_change_impacts_complete": (
                reranker_artifact_change_impacts_complete
            ),
            "reranker_artifact_governance_event_count": len(
                reranker_artifact_governance_event_ids
            ),
            "training_run_count": len(ordered_training_runs),
            "expected_training_run_count": len(training_run_ids),
            "training_audit_bundle_count": len(ordered_training_audit_bundles),
            "expected_training_audit_bundle_count": len(training_run_ids),
            "training_audit_bundle_hashes_match_training_runs": (
                training_audit_bundle_hashes_match_training_runs
            ),
            "training_audit_bundle_corpus_lineage_complete": (
                training_audit_bundle_corpus_lineage_complete
            ),
            "training_audit_bundle_match_checks": training_audit_bundle_match_checks,
            "training_audit_bundle_validation_receipt_count": len(
                ordered_training_validation_receipts
            ),
            "expected_training_audit_bundle_validation_receipt_count": len(
                ordered_training_audit_bundles
            ),
            "training_audit_bundle_validation_receipts_complete": (
                training_audit_bundle_validation_receipts_complete
            ),
            "judgment_set_count": len(ordered_judgment_sets),
            "expected_judgment_set_count": len(judgment_set_ids),
            "semantic_governance_event_count": len(ordered_governance_events),
            "expected_candidate_governance_event_count": len(candidate_governance_event_ids),
            "expected_reranker_artifact_governance_event_count": len(
                reranker_artifact_governance_event_ids
            ),
            "semantic_governance_policy_complete": semantic_governance_policy["complete"],
        },
        "prov": prov_graph(
            release=release,
            evaluation=evaluation,
            sources=sources,
            replay_runs=ordered_replay_runs,
            learning_candidates=learning_candidates,
            reranker_artifacts=reranker_artifacts,
            training_runs=ordered_training_runs,
            training_audit_bundles=ordered_training_audit_bundles,
            judgment_sets=ordered_judgment_sets,
            governance_events=ordered_governance_events,
            bundle_id=bundle_id,
            created_by=created_by,
        ),
    }
