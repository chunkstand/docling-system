from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

import app.services.audit_bundle_replay_alert_corpus as _audit_bundle_replay_alert_corpus
from app.core.time import utcnow
from app.db.public.audit_and_evidence import AuditBundleExport
from app.db.public.retrieval import (
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    SearchHarnessRelease,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.audit_bundle_training_run_payloads import (
    retrieval_hard_negative_payload,
    retrieval_judgment_payload,
    retrieval_judgment_set_payload,
    retrieval_training_run_full_payload,
    retrieval_training_run_payload,
)
from app.services.audit_bundle_training_run_provenance import (
    training_run_prov_graph as _training_run_prov_graph,
)
from app.services.semantic_governance import (
    semantic_governance_event_payload as _semantic_governance_event_payload,
)
from app.services.storage import StorageService

RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND = "retrieval_training_run_provenance"
RETRIEVAL_TRAINING_RUN_SOURCE_TABLE = "retrieval_training_runs"
RETRIEVAL_TRAINING_RUN_AUDIT_SCHEMA_VERSION = "1.1"

_claim_support_replay_alert_corpus_lineage_payload = (
    _audit_bundle_replay_alert_corpus.claim_support_replay_alert_corpus_lineage_payload
)
_training_audit_bundle_claim_support_replay_alert_corpus_lineage_status = (
    _audit_bundle_replay_alert_corpus.training_audit_bundle_claim_support_replay_alert_corpus_lineage_status
)

__all__ = [
    "RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND",
    "RETRIEVAL_TRAINING_RUN_AUDIT_SCHEMA_VERSION",
    "RETRIEVAL_TRAINING_RUN_SOURCE_TABLE",
    "TrainingRunAuditBundleRuntime",
    "build_retrieval_training_run_payload",
    "create_retrieval_training_run_audit_bundle_row",
    "ensure_retrieval_training_run_audit_bundles_for_release",
    "load_training_run_governance_events",
    "retrieval_hard_negative_payload",
    "retrieval_judgment_payload",
    "retrieval_judgment_set_payload",
    "retrieval_training_run_full_payload",
    "retrieval_training_run_payload",
    "training_audit_bundle_current_for_training_run",
    "training_audit_bundle_hashes_match_training_run",
]


@dataclass(frozen=True)
class TrainingRunAuditBundleRuntime:
    canonical_json_bytes: Callable[[Any], bytes]
    payload_sha256: Callable[[Any], str]
    sign_bundle: Callable[..., dict[str, Any]]
    training_run_not_completed: Callable[[RetrievalTrainingRun], Exception]


def _load_governance_event_chain(
    session: Session,
    seed_events: list[SemanticGovernanceEvent],
) -> list[SemanticGovernanceEvent]:
    events_by_id = {row.id: row for row in seed_events}
    pending_ids = {
        row.previous_event_id
        for row in seed_events
        if row.previous_event_id is not None and row.previous_event_id not in events_by_id
    }
    while pending_ids:
        rows = (
            session.execute(
                select(SemanticGovernanceEvent).where(SemanticGovernanceEvent.id.in_(pending_ids))
            )
            .scalars()
            .all()
        )
        pending_ids = set()
        for row in rows:
            if row.id in events_by_id:
                continue
            events_by_id[row.id] = row
            if row.previous_event_id is not None and row.previous_event_id not in events_by_id:
                pending_ids.add(row.previous_event_id)
    return sorted(
        events_by_id.values(),
        key=lambda row: (row.event_sequence, row.created_at, str(row.id)),
    )


def load_training_run_governance_events(
    session: Session,
    training_run: RetrievalTrainingRun,
) -> list[SemanticGovernanceEvent]:
    conditions = [
        and_(
            SemanticGovernanceEvent.subject_table == RETRIEVAL_TRAINING_RUN_SOURCE_TABLE,
            SemanticGovernanceEvent.subject_id == training_run.id,
        )
    ]
    if training_run.semantic_governance_event_id is not None:
        conditions.append(SemanticGovernanceEvent.id == training_run.semantic_governance_event_id)
    seed_events = (
        session.execute(
            select(SemanticGovernanceEvent)
            .where(or_(*conditions))
            .order_by(SemanticGovernanceEvent.event_sequence.asc())
        )
        .scalars()
        .all()
    )
    return _load_governance_event_chain(session, seed_events)


def training_audit_bundle_hashes_match_training_run(
    bundle: AuditBundleExport | None,
    training_run: RetrievalTrainingRun,
) -> bool:
    if bundle is None:
        return False
    payload = (bundle.bundle_payload_json or {}).get("payload") or {}
    payload_source = payload.get("source") or {}
    payload_training_run = payload.get("retrieval_training_run") or {}
    payload_integrity = payload.get("integrity") or {}
    return all(
        (
            bundle.bundle_kind == RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
            bundle.source_table == RETRIEVAL_TRAINING_RUN_SOURCE_TABLE,
            bundle.source_id == training_run.id,
            bundle.retrieval_training_run_id == training_run.id,
            payload_source.get("source_table") == RETRIEVAL_TRAINING_RUN_SOURCE_TABLE,
            payload_source.get("source_id") == str(training_run.id),
            payload_training_run.get("retrieval_training_run_id") == str(training_run.id),
            payload_training_run.get("training_dataset_sha256")
            == training_run.training_dataset_sha256,
            payload_integrity.get("training_dataset_hash_matches") is True,
        )
    )


def training_audit_bundle_current_for_training_run(
    session: Session,
    bundle: AuditBundleExport | None,
    training_run: RetrievalTrainingRun,
) -> bool:
    if not training_audit_bundle_hashes_match_training_run(bundle, training_run):
        return False
    lineage_status = _training_audit_bundle_claim_support_replay_alert_corpus_lineage_status(
        session,
        bundle,
        training_run,
    )
    return (
        lineage_status["bundle_complete"] == lineage_status["current_complete"]
        and lineage_status["source_reference_counts_match"]
    )


def build_retrieval_training_run_payload(
    session: Session,
    *,
    training_run: RetrievalTrainingRun,
    bundle_id: UUID,
    created_by: str | None,
    created_at: datetime,
    runtime: TrainingRunAuditBundleRuntime,
) -> dict[str, Any]:
    judgment_set = session.get(RetrievalJudgmentSet, training_run.judgment_set_id)
    judgments = (
        session.execute(
            select(RetrievalJudgment)
            .where(RetrievalJudgment.judgment_set_id == training_run.judgment_set_id)
            .order_by(RetrievalJudgment.deduplication_key.asc(), RetrievalJudgment.id.asc())
        )
        .scalars()
        .all()
    )
    hard_negatives = (
        session.execute(
            select(RetrievalHardNegative)
            .where(RetrievalHardNegative.judgment_set_id == training_run.judgment_set_id)
            .order_by(
                RetrievalHardNegative.deduplication_key.asc(),
                RetrievalHardNegative.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    governance_events = load_training_run_governance_events(session, training_run)
    claim_support_replay_alert_corpus_lineage = _claim_support_replay_alert_corpus_lineage_payload(
        session,
        judgments=judgments,
        hard_negatives=hard_negatives,
    )
    training_payload = training_run.training_payload_json or {}
    training_payload_sha256 = runtime.payload_sha256(training_payload)
    judgment_counts = {
        "positive": sum(1 for row in judgments if row.judgment_kind == "positive"),
        "negative": sum(1 for row in judgments if row.judgment_kind == "negative"),
        "missing": sum(1 for row in judgments if row.judgment_kind == "missing"),
    }
    source_payload_hashes = sorted(
        {
            source_hash
            for source_hash in [
                *(row.source_payload_sha256 for row in judgments),
                *(row.source_payload_sha256 for row in hard_negatives),
            ]
            if source_hash
        }
    )
    source_payload_hashes_complete = all(
        row.source_payload_sha256 for row in [*judgments, *hard_negatives]
    )
    evidence_ref_count = sum(
        len(row.evidence_refs_json or []) for row in [*judgments, *hard_negatives]
    )
    training_payload_count_matches = len(training_payload.get("judgments") or []) == len(
        judgments
    ) and len(training_payload.get("hard_negatives") or []) == len(hard_negatives)
    judgment_count_matches = (
        len(judgments)
        == training_run.positive_count + training_run.negative_count + training_run.missing_count
        and len(judgments) == (judgment_set.judgment_count if judgment_set else len(judgments))
    )
    hard_negative_count_matches = len(hard_negatives) == training_run.hard_negative_count and len(
        hard_negatives
    ) == (judgment_set.hard_negative_count if judgment_set else len(hard_negatives))
    example_count_matches = len(judgments) + len(hard_negatives) == training_run.example_count
    training_dataset_hash_matches = (
        training_payload_sha256 == training_run.training_dataset_sha256
        and (
            judgment_set is None
            or judgment_set.payload_sha256 == training_run.training_dataset_sha256
        )
    )
    governance_event_ids = {row.id for row in governance_events}
    has_primary_governance_event = (
        training_run.semantic_governance_event_id in governance_event_ids
        if training_run.semantic_governance_event_id is not None
        else any(
            row.subject_table == RETRIEVAL_TRAINING_RUN_SOURCE_TABLE
            and row.subject_id == training_run.id
            for row in governance_events
        )
    )
    corpus_lineage_integrity = claim_support_replay_alert_corpus_lineage["integrity"]
    corpus_lineage_required = bool(corpus_lineage_integrity["source_reference_count"])
    audit_checklist = {
        "has_training_run_record": True,
        "has_judgment_set_record": judgment_set is not None,
        "training_dataset_hash_matches": training_dataset_hash_matches,
        "judgment_count_matches": judgment_count_matches,
        "hard_negative_count_matches": hard_negative_count_matches,
        "example_count_matches": example_count_matches,
        "training_payload_count_matches": training_payload_count_matches,
        "source_payload_hashes_complete": source_payload_hashes_complete,
        "has_primary_governance_event": has_primary_governance_event,
        "has_prov_graph": True,
        "claim_support_replay_alert_corpus_lineage_complete": (
            corpus_lineage_integrity["complete"] if corpus_lineage_required else True
        ),
    }
    audit_checklist["complete"] = all(bool(value) for value in audit_checklist.values())
    return {
        "schema_name": "retrieval_training_run_audit_payload",
        "schema_version": RETRIEVAL_TRAINING_RUN_AUDIT_SCHEMA_VERSION,
        "bundle_id": str(bundle_id),
        "bundle_kind": RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
        "created_at": created_at.isoformat(),
        "created_by": created_by,
        "source": {
            "source_table": RETRIEVAL_TRAINING_RUN_SOURCE_TABLE,
            "source_id": str(training_run.id),
        },
        "retrieval_training_run": retrieval_training_run_full_payload(training_run),
        "retrieval_judgment_set": (
            retrieval_judgment_set_payload(judgment_set) if judgment_set else None
        ),
        "retrieval_judgments": [retrieval_judgment_payload(row) for row in judgments],
        "retrieval_hard_negatives": [
            retrieval_hard_negative_payload(row) for row in hard_negatives
        ],
        "semantic_governance_events": [
            _semantic_governance_event_payload(row) for row in governance_events
        ],
        "claim_support_replay_alert_corpus_source_references": (
            claim_support_replay_alert_corpus_lineage["source_references"]
        ),
        "claim_support_replay_alert_corpus_snapshots": (
            claim_support_replay_alert_corpus_lineage["snapshots"]
        ),
        "claim_support_replay_alert_corpus_rows": (
            claim_support_replay_alert_corpus_lineage["rows"]
        ),
        "claim_support_replay_alert_promotion_artifacts": (
            claim_support_replay_alert_corpus_lineage["promotion_artifacts"]
        ),
        "claim_support_replay_alert_promotion_events": (
            claim_support_replay_alert_corpus_lineage["promotion_events"]
        ),
        "claim_support_replay_alert_escalation_events": (
            claim_support_replay_alert_corpus_lineage["escalation_events"]
        ),
        "claim_support_replay_alert_snapshot_governance_artifacts": (
            claim_support_replay_alert_corpus_lineage["snapshot_governance_artifacts"]
        ),
        "claim_support_replay_alert_snapshot_governance_events": (
            claim_support_replay_alert_corpus_lineage["snapshot_governance_events"]
        ),
        "claim_support_replay_alert_corpus_integrity": corpus_lineage_integrity,
        "source_payload_hashes": source_payload_hashes,
        "audit_checklist": audit_checklist,
        "integrity": {
            "training_payload_sha256": training_payload_sha256,
            "stored_training_dataset_sha256": training_run.training_dataset_sha256,
            "training_dataset_hash_matches": training_dataset_hash_matches,
            "judgment_count": len(judgments),
            "expected_judgment_count": training_run.positive_count
            + training_run.negative_count
            + training_run.missing_count,
            "hard_negative_count": len(hard_negatives),
            "expected_hard_negative_count": training_run.hard_negative_count,
            "example_count": len(judgments) + len(hard_negatives),
            "expected_example_count": training_run.example_count,
            "positive_count": judgment_counts["positive"],
            "expected_positive_count": training_run.positive_count,
            "negative_count": judgment_counts["negative"],
            "expected_negative_count": training_run.negative_count,
            "missing_count": judgment_counts["missing"],
            "expected_missing_count": training_run.missing_count,
            "source_payload_hash_count": len(source_payload_hashes),
            "source_payload_hashes_complete": source_payload_hashes_complete,
            "evidence_ref_count": evidence_ref_count,
            "semantic_governance_event_count": len(governance_events),
            "has_primary_governance_event": has_primary_governance_event,
            "claim_support_replay_alert_corpus_lineage_complete": (
                corpus_lineage_integrity["complete"] if corpus_lineage_required else True
            ),
            "claim_support_replay_alert_corpus_source_reference_count": (
                corpus_lineage_integrity["source_reference_count"]
            ),
            "claim_support_replay_alert_corpus_row_count": corpus_lineage_integrity["row_count"],
            "claim_support_replay_alert_corpus_snapshot_count": corpus_lineage_integrity[
                "snapshot_count"
            ],
        },
        "prov": _training_run_prov_graph(
            training_run=training_run,
            judgment_set=judgment_set,
            judgments=judgments,
            hard_negatives=hard_negatives,
            governance_events=governance_events,
            claim_support_replay_alert_corpus_lineage=claim_support_replay_alert_corpus_lineage,
            bundle_id=bundle_id,
            created_by=created_by,
            bundle_kind=RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
            source_table=RETRIEVAL_TRAINING_RUN_SOURCE_TABLE,
        ),
    }


def create_retrieval_training_run_audit_bundle_row(
    session: Session,
    *,
    training_run: RetrievalTrainingRun,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
    runtime: TrainingRunAuditBundleRuntime,
) -> AuditBundleExport:
    if training_run.status != "completed":
        raise runtime.training_run_not_completed(training_run)
    bundle_id = uuid.uuid4()
    created_at = utcnow()
    audit_payload = build_retrieval_training_run_payload(
        session,
        training_run=training_run,
        bundle_id=bundle_id,
        created_by=created_by,
        created_at=created_at,
        runtime=runtime,
    )
    bundle = runtime.sign_bundle(
        bundle_id=bundle_id,
        bundle_kind=RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
        source_table=RETRIEVAL_TRAINING_RUN_SOURCE_TABLE,
        source_id=training_run.id,
        payload=audit_payload,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    bundle_path = storage_service.get_audit_bundle_json_path(
        RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
        bundle_id,
    )
    bundle_path.write_bytes(runtime.canonical_json_bytes(bundle))
    integrity = {
        "payload_hash_matches_bundle": True,
        "bundle_hash_matches_bundle": True,
        "signature_valid": True,
        "file_exists": True,
        "stored_payload_matches_file": True,
        "complete": True,
    }
    row = AuditBundleExport(
        id=bundle_id,
        bundle_kind=RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
        source_table=RETRIEVAL_TRAINING_RUN_SOURCE_TABLE,
        source_id=training_run.id,
        search_harness_release_id=training_run.search_harness_release_id,
        retrieval_training_run_id=training_run.id,
        storage_path=str(bundle_path),
        payload_sha256=bundle["bundle_export"]["payload_sha256"],
        bundle_sha256=bundle["bundle_export"]["bundle_sha256"],
        signature=bundle["bundle_export"]["signature"],
        signature_algorithm=bundle["bundle_export"]["signature_algorithm"],
        signing_key_id=bundle["bundle_export"]["signing_key_id"],
        bundle_payload_json=bundle,
        integrity_json=integrity,
        created_by=created_by,
        export_status="completed",
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    return row


def ensure_retrieval_training_run_audit_bundles_for_release(
    session: Session,
    *,
    release: SearchHarnessRelease,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
    runtime: TrainingRunAuditBundleRuntime,
) -> list[AuditBundleExport]:
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
    learning_candidate_ids = {row.id for row in learning_candidates}
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
        session.execute(select(RetrievalRerankerArtifact).where(or_(*reranker_artifact_conditions)))
        .scalars()
        .all()
    )
    training_run_ids = sorted(
        {
            *(row.retrieval_training_run_id for row in learning_candidates),
            *(row.retrieval_training_run_id for row in reranker_artifacts),
        },
        key=str,
    )
    if not training_run_ids:
        return []
    existing_bundle_rows = (
        session.execute(
            select(AuditBundleExport)
            .where(
                AuditBundleExport.retrieval_training_run_id.in_(training_run_ids),
                AuditBundleExport.bundle_kind == RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
            )
            .order_by(
                AuditBundleExport.retrieval_training_run_id.asc(),
                AuditBundleExport.created_at.desc(),
                AuditBundleExport.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    existing_bundle_by_run_id: dict[UUID, AuditBundleExport] = {}
    for row in existing_bundle_rows:
        if row.retrieval_training_run_id is None:
            continue
        existing_bundle_by_run_id.setdefault(row.retrieval_training_run_id, row)
    training_runs = (
        session.execute(
            select(RetrievalTrainingRun).where(RetrievalTrainingRun.id.in_(training_run_ids))
        )
        .scalars()
        .all()
    )
    training_runs_by_id = {row.id: row for row in training_runs}
    ensured_bundles: list[AuditBundleExport] = []
    for training_run_id in training_run_ids:
        training_run = training_runs_by_id.get(training_run_id)
        if training_run is None:
            continue
        existing_bundle = existing_bundle_by_run_id.get(training_run_id)
        if training_audit_bundle_current_for_training_run(
            session,
            existing_bundle,
            training_run,
        ):
            if existing_bundle is not None:
                ensured_bundles.append(existing_bundle)
            continue
        ensured_bundles.append(
            create_retrieval_training_run_audit_bundle_row(
                session,
                training_run=training_run,
                created_by=created_by,
                storage_service=storage_service,
                signing_key=signing_key,
                signing_key_id=signing_key_id,
                runtime=runtime,
            )
        )
    return ensured_bundles
