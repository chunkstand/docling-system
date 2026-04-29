from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.coercion import maybe_uuid as _uuid_or_none
from app.core.config import get_settings
from app.core.hashes import embedded_payload_hash_matches as _payload_hash_matches_embedded_field
from app.core.hashes import file_sha256 as _file_sha256
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.time import utcnow
from app.db.models import (
    AgentTaskArtifact,
    AuditBundleExport,
    AuditBundleValidationReceipt,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchReplayRun,
    SemanticGovernanceEvent,
)
from app.schemas.search import (
    AuditBundleExportResponse,
    AuditBundleExportSummaryResponse,
    AuditBundleValidationReceiptRequest,
    AuditBundleValidationReceiptResponse,
    AuditBundleValidationReceiptSummaryResponse,
    RetrievalTrainingRunAuditBundleRequest,
    SearchHarnessReleaseAuditBundleRequest,
)
from app.services.query_utils import load_by_ids as _load_by_ids
from app.services.search_release_shared import release_package_sha256 as _release_package_sha256
from app.services.search_release_shared import (
    search_harness_release_not_found_error as _release_not_found,
)
from app.services.semantic_governance import (
    search_harness_release_semantic_governance_context,
    semantic_governance_event_payload,
)
from app.services.storage import StorageService

SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND = "search_harness_release_provenance"
SEARCH_HARNESS_RELEASE_SOURCE_TABLE = "search_harness_releases"
RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND = "retrieval_training_run_provenance"
RETRIEVAL_TRAINING_RUN_SOURCE_TABLE = "retrieval_training_runs"
SIGNATURE_ALGORITHM = "hmac-sha256"
AUDIT_BUNDLE_VALIDATION_PROFILE = "audit_bundle_validation_v1"
RETRIEVAL_TRAINING_RUN_AUDIT_SCHEMA_VERSION = "1.1"
CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SOURCE_TYPE = "claim_support_replay_alert_corpus"
CLAIM_SUPPORT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot"
)
CLAIM_SUPPORT_FIXTURE_PROMOTION_EVENT_KIND = "claim_support_policy_impact_fixture_promoted"
CLAIM_SUPPORT_REPLAY_ESCALATION_EVENT_KIND = "claim_support_policy_impact_replay_escalated"
CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_EVENT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot_activated"
)


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _audit_bundle_not_found(bundle_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "audit_bundle_export_not_found",
        "Audit bundle export not found.",
        bundle_id=str(bundle_id),
    )


def _audit_bundle_validation_receipt_not_found(
    bundle_id: UUID,
    receipt_id: UUID | None = None,
) -> HTTPException:
    context = {"bundle_id": str(bundle_id)}
    if receipt_id is not None:
        context["receipt_id"] = str(receipt_id)
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "audit_bundle_validation_receipt_not_found",
        "Audit bundle validation receipt not found.",
        **context,
    )


def _training_run_not_found(training_run_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_training_run_not_found",
        "Retrieval training run not found.",
        retrieval_training_run_id=str(training_run_id),
    )


def _training_run_not_completed(training_run: RetrievalTrainingRun) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "retrieval_training_run_not_completed",
        "Retrieval training run must be completed before exporting an audit bundle.",
        retrieval_training_run_id=str(training_run.id),
        status=training_run.status,
    )


def _signing_key() -> tuple[str, str]:
    settings = get_settings()
    signing_key = getattr(settings, "audit_bundle_signing_key", None)
    if not signing_key:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "audit_bundle_signing_key_missing",
            "DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY is required to export signed audit bundles.",
        )
    key_id = getattr(settings, "audit_bundle_signing_key_id", None) or "local"
    return str(signing_key), str(key_id)


def _signature(payload_sha256: str, signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        payload_sha256.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _release_payload(row: SearchHarnessRelease) -> dict[str, Any]:
    return {
        "release_id": str(row.id),
        "evaluation_id": str(row.search_harness_evaluation_id),
        "outcome": row.outcome,
        "baseline_harness_name": row.baseline_harness_name,
        "candidate_harness_name": row.candidate_harness_name,
        "limit": row.limit,
        "source_types": row.source_types_json or [],
        "thresholds": row.thresholds_json or {},
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "details": row.details_json or {},
        "evaluation_snapshot": row.evaluation_snapshot_json or {},
        "release_package_sha256": row.release_package_sha256,
        "requested_by": row.requested_by,
        "review_note": row.review_note,
        "created_at": row.created_at.isoformat(),
    }


def _evaluation_payload(row: SearchHarnessEvaluation | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "evaluation_id": str(row.id),
        "status": row.status,
        "baseline_harness_name": row.baseline_harness_name,
        "candidate_harness_name": row.candidate_harness_name,
        "limit": row.limit,
        "source_types": row.source_types_json or [],
        "harness_overrides": row.harness_overrides_json or {},
        "total_shared_query_count": row.total_shared_query_count,
        "total_improved_count": row.total_improved_count,
        "total_regressed_count": row.total_regressed_count,
        "total_unchanged_count": row.total_unchanged_count,
        "summary": row.summary_json or {},
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _source_payload(row: SearchHarnessEvaluationSource) -> dict[str, Any]:
    return {
        "source_id": str(row.id),
        "source_index": row.source_index,
        "source_type": row.source_type,
        "baseline_replay_run_id": str(row.baseline_replay_run_id),
        "candidate_replay_run_id": str(row.candidate_replay_run_id),
        "baseline_status": row.baseline_status,
        "candidate_status": row.candidate_status,
        "shared_query_count": row.shared_query_count,
        "improved_count": row.improved_count,
        "regressed_count": row.regressed_count,
        "unchanged_count": row.unchanged_count,
        "acceptance_checks": row.acceptance_checks_json or {},
        "baseline_mrr": row.baseline_mrr,
        "candidate_mrr": row.candidate_mrr,
        "baseline_zero_result_count": row.baseline_zero_result_count,
        "candidate_zero_result_count": row.candidate_zero_result_count,
        "baseline_foreign_top_result_count": row.baseline_foreign_top_result_count,
        "candidate_foreign_top_result_count": row.candidate_foreign_top_result_count,
        "created_at": row.created_at.isoformat(),
    }


def _replay_payload(row: SearchReplayRun) -> dict[str, Any]:
    return {
        "replay_run_id": str(row.id),
        "source_type": row.source_type,
        "status": row.status,
        "harness_name": row.harness_name,
        "reranker_name": row.reranker_name,
        "reranker_version": row.reranker_version,
        "retrieval_profile_name": row.retrieval_profile_name,
        "harness_config": row.harness_config_json or {},
        "query_count": row.query_count,
        "passed_count": row.passed_count,
        "failed_count": row.failed_count,
        "zero_result_count": row.zero_result_count,
        "table_hit_count": row.table_hit_count,
        "top_result_changes": row.top_result_changes,
        "max_rank_shift": row.max_rank_shift,
        "summary": row.summary_json or {},
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _retrieval_learning_candidate_payload(
    row: RetrievalLearningCandidateEvaluation,
) -> dict[str, Any]:
    return {
        "candidate_evaluation_id": str(row.id),
        "retrieval_training_run_id": str(row.retrieval_training_run_id),
        "judgment_set_id": str(row.judgment_set_id),
        "search_harness_evaluation_id": str(row.search_harness_evaluation_id),
        "search_harness_release_id": (
            str(row.search_harness_release_id) if row.search_harness_release_id else None
        ),
        "semantic_governance_event_id": (
            str(row.semantic_governance_event_id) if row.semantic_governance_event_id else None
        ),
        "training_dataset_sha256": row.training_dataset_sha256,
        "training_example_count": row.training_example_count,
        "positive_count": row.positive_count,
        "negative_count": row.negative_count,
        "missing_count": row.missing_count,
        "hard_negative_count": row.hard_negative_count,
        "baseline_harness_name": row.baseline_harness_name,
        "candidate_harness_name": row.candidate_harness_name,
        "source_types": row.source_types_json or [],
        "limit": row.limit,
        "status": row.status,
        "gate_outcome": row.gate_outcome,
        "thresholds": row.thresholds_json or {},
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "learning_package_sha256": row.learning_package_sha256,
        "created_by": row.created_by,
        "review_note": row.review_note,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _retrieval_reranker_artifact_payload(row: RetrievalRerankerArtifact) -> dict[str, Any]:
    artifact_payload = row.artifact_payload_json or {}
    change_impact_report = row.change_impact_report_json or {}
    payload_training_run = artifact_payload.get("retrieval_training_run") or {}
    payload_evaluation = artifact_payload.get("evaluation") or {}
    payload_release = artifact_payload.get("release") or {}
    return {
        "artifact_id": str(row.id),
        "retrieval_training_run_id": str(row.retrieval_training_run_id),
        "judgment_set_id": str(row.judgment_set_id),
        "retrieval_learning_candidate_evaluation_id": str(
            row.retrieval_learning_candidate_evaluation_id
        ),
        "search_harness_evaluation_id": str(row.search_harness_evaluation_id),
        "search_harness_release_id": (
            str(row.search_harness_release_id) if row.search_harness_release_id else None
        ),
        "semantic_governance_event_id": (
            str(row.semantic_governance_event_id) if row.semantic_governance_event_id else None
        ),
        "artifact_kind": row.artifact_kind,
        "artifact_name": row.artifact_name,
        "artifact_version": row.artifact_version,
        "status": row.status,
        "gate_outcome": row.gate_outcome,
        "baseline_harness_name": row.baseline_harness_name,
        "candidate_harness_name": row.candidate_harness_name,
        "source_types": row.source_types_json or [],
        "limit": row.limit,
        "training_dataset_sha256": row.training_dataset_sha256,
        "training_example_count": row.training_example_count,
        "positive_count": row.positive_count,
        "negative_count": row.negative_count,
        "missing_count": row.missing_count,
        "hard_negative_count": row.hard_negative_count,
        "thresholds": row.thresholds_json or {},
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "feature_weights": row.feature_weights_json or {},
        "harness_overrides": row.harness_overrides_json or {},
        "artifact_sha256": row.artifact_sha256,
        "payload_artifact_sha256": _payload_sha256(artifact_payload),
        "change_impact_sha256": row.change_impact_sha256,
        "payload_change_impact_sha256": _payload_sha256(change_impact_report),
        "payload_training_run_id": payload_training_run.get("retrieval_training_run_id"),
        "payload_training_dataset_sha256": payload_training_run.get("training_dataset_sha256"),
        "payload_evaluation_id": payload_evaluation.get("evaluation_id"),
        "payload_release_id": payload_release.get("release_id"),
        "artifact_payload": artifact_payload,
        "change_impact_report": change_impact_report,
        "evaluation_snapshot": row.evaluation_snapshot_json or {},
        "release_snapshot": row.release_snapshot_json or {},
        "created_by": row.created_by,
        "review_note": row.review_note,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _retrieval_training_run_payload(row: RetrievalTrainingRun) -> dict[str, Any]:
    return {
        "retrieval_training_run_id": str(row.id),
        "judgment_set_id": str(row.judgment_set_id),
        "status": row.status,
        "run_kind": row.run_kind,
        "training_dataset_sha256": row.training_dataset_sha256,
        "example_count": row.example_count,
        "positive_count": row.positive_count,
        "negative_count": row.negative_count,
        "missing_count": row.missing_count,
        "hard_negative_count": row.hard_negative_count,
        "summary": row.summary_json or {},
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _retrieval_training_run_full_payload(row: RetrievalTrainingRun) -> dict[str, Any]:
    payload = _retrieval_training_run_payload(row)
    payload.update(
        {
            "search_harness_evaluation_id": (
                str(row.search_harness_evaluation_id) if row.search_harness_evaluation_id else None
            ),
            "search_harness_release_id": (
                str(row.search_harness_release_id) if row.search_harness_release_id else None
            ),
            "semantic_governance_event_id": (
                str(row.semantic_governance_event_id) if row.semantic_governance_event_id else None
            ),
            "training_payload": row.training_payload_json or {},
        }
    )
    return payload


def _retrieval_judgment_set_payload(row: RetrievalJudgmentSet) -> dict[str, Any]:
    return {
        "judgment_set_id": str(row.id),
        "set_name": row.set_name,
        "set_kind": row.set_kind,
        "source_types": row.source_types_json or [],
        "source_limit": row.source_limit,
        "criteria": row.criteria_json or {},
        "summary": row.summary_json or {},
        "judgment_count": row.judgment_count,
        "positive_count": row.positive_count,
        "negative_count": row.negative_count,
        "missing_count": row.missing_count,
        "hard_negative_count": row.hard_negative_count,
        "payload_sha256": row.payload_sha256,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat(),
    }


def _retrieval_judgment_payload(row: RetrievalJudgment) -> dict[str, Any]:
    return {
        "judgment_id": str(row.id),
        "judgment_set_id": str(row.judgment_set_id),
        "judgment_kind": row.judgment_kind,
        "judgment_label": row.judgment_label,
        "source_type": row.source_type,
        "source_ref_id": str(row.source_ref_id) if row.source_ref_id else None,
        "search_feedback_id": str(row.search_feedback_id) if row.search_feedback_id else None,
        "search_replay_query_id": (
            str(row.search_replay_query_id) if row.search_replay_query_id else None
        ),
        "search_replay_run_id": str(row.search_replay_run_id) if row.search_replay_run_id else None,
        "evaluation_query_id": str(row.evaluation_query_id) if row.evaluation_query_id else None,
        "source_search_request_id": (
            str(row.source_search_request_id) if row.source_search_request_id else None
        ),
        "search_request_id": str(row.search_request_id) if row.search_request_id else None,
        "search_request_result_id": (
            str(row.search_request_result_id) if row.search_request_result_id else None
        ),
        "result_rank": row.result_rank,
        "result_type": row.result_type,
        "result_id": str(row.result_id) if row.result_id else None,
        "document_id": str(row.document_id) if row.document_id else None,
        "run_id": str(row.run_id) if row.run_id else None,
        "score": row.score,
        "query_text": row.query_text,
        "mode": row.mode,
        "filters": row.filters_json or {},
        "expected_result_type": row.expected_result_type,
        "expected_top_n": row.expected_top_n,
        "harness_name": row.harness_name,
        "reranker_name": row.reranker_name,
        "reranker_version": row.reranker_version,
        "retrieval_profile_name": row.retrieval_profile_name,
        "rerank_features": row.rerank_features_json or {},
        "evidence_refs": row.evidence_refs_json or [],
        "rationale": row.rationale,
        "payload": row.payload_json or {},
        "source_payload_sha256": row.source_payload_sha256,
        "deduplication_key": row.deduplication_key,
        "created_at": row.created_at.isoformat(),
    }


def _retrieval_hard_negative_payload(row: RetrievalHardNegative) -> dict[str, Any]:
    return {
        "hard_negative_id": str(row.id),
        "judgment_set_id": str(row.judgment_set_id),
        "judgment_id": str(row.judgment_id),
        "positive_judgment_id": (
            str(row.positive_judgment_id) if row.positive_judgment_id else None
        ),
        "hard_negative_kind": row.hard_negative_kind,
        "source_type": row.source_type,
        "source_ref_id": str(row.source_ref_id) if row.source_ref_id else None,
        "search_feedback_id": str(row.search_feedback_id) if row.search_feedback_id else None,
        "search_replay_query_id": (
            str(row.search_replay_query_id) if row.search_replay_query_id else None
        ),
        "search_replay_run_id": str(row.search_replay_run_id) if row.search_replay_run_id else None,
        "evaluation_query_id": str(row.evaluation_query_id) if row.evaluation_query_id else None,
        "source_search_request_id": (
            str(row.source_search_request_id) if row.source_search_request_id else None
        ),
        "search_request_id": str(row.search_request_id) if row.search_request_id else None,
        "search_request_result_id": (
            str(row.search_request_result_id) if row.search_request_result_id else None
        ),
        "result_rank": row.result_rank,
        "result_type": row.result_type,
        "result_id": str(row.result_id) if row.result_id else None,
        "document_id": str(row.document_id) if row.document_id else None,
        "run_id": str(row.run_id) if row.run_id else None,
        "score": row.score,
        "query_text": row.query_text,
        "mode": row.mode,
        "filters": row.filters_json or {},
        "rerank_features": row.rerank_features_json or {},
        "expected_result_type": row.expected_result_type,
        "expected_top_n": row.expected_top_n,
        "evidence_refs": row.evidence_refs_json or [],
        "reason": row.reason,
        "details": row.details_json or {},
        "source_payload_sha256": row.source_payload_sha256,
        "deduplication_key": row.deduplication_key,
        "created_at": row.created_at.isoformat(),
    }


def _audit_bundle_reference_payload(row: AuditBundleExport) -> dict[str, Any]:
    payload = (row.bundle_payload_json or {}).get("payload") or {}
    payload_source = payload.get("source") or {}
    payload_training_run = payload.get("retrieval_training_run") or {}
    payload_integrity = payload.get("integrity") or {}
    payload_corpus_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
    return {
        "bundle_id": str(row.id),
        "bundle_kind": row.bundle_kind,
        "source_table": row.source_table,
        "source_id": str(row.source_id),
        "search_harness_release_id": (
            str(row.search_harness_release_id) if row.search_harness_release_id else None
        ),
        "retrieval_training_run_id": (
            str(row.retrieval_training_run_id) if row.retrieval_training_run_id else None
        ),
        "payload_sha256": row.payload_sha256,
        "bundle_sha256": row.bundle_sha256,
        "signature": row.signature,
        "signature_algorithm": row.signature_algorithm,
        "signing_key_id": row.signing_key_id,
        "payload_source_table": payload_source.get("source_table"),
        "payload_source_id": payload_source.get("source_id"),
        "payload_training_dataset_sha256": payload_training_run.get("training_dataset_sha256"),
        "payload_training_dataset_hash_matches": payload_integrity.get(
            "training_dataset_hash_matches"
        ),
        "payload_claim_support_replay_alert_corpus_lineage_complete": (
            payload_corpus_integrity.get("complete")
        ),
        "payload_claim_support_replay_alert_corpus_source_reference_count": (
            payload_corpus_integrity.get("source_reference_count")
        ),
        "created_by": row.created_by,
        "export_status": row.export_status,
        "created_at": row.created_at.isoformat(),
    }


def _validation_receipt_reference_payload(
    row: AuditBundleValidationReceipt,
) -> dict[str, Any]:
    return {
        "receipt_id": str(row.id),
        "audit_bundle_export_id": str(row.audit_bundle_export_id),
        "bundle_kind": row.bundle_kind,
        "source_table": row.source_table,
        "source_id": str(row.source_id),
        "validation_profile": row.validation_profile,
        "validation_status": row.validation_status,
        "payload_schema_valid": row.payload_schema_valid,
        "prov_graph_valid": row.prov_graph_valid,
        "bundle_integrity_valid": row.bundle_integrity_valid,
        "source_integrity_valid": row.source_integrity_valid,
        "receipt_sha256": row.receipt_sha256,
        "prov_jsonld_sha256": row.prov_jsonld_sha256,
        "signature": row.signature,
        "signature_algorithm": row.signature_algorithm,
        "signing_key_id": row.signing_key_id,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat(),
    }


def _semantic_governance_event_payload(row: SemanticGovernanceEvent) -> dict[str, Any]:
    return semantic_governance_event_payload(row)


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


def _load_training_run_governance_events(
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


def _claim_support_source_details(row: RetrievalJudgment | RetrievalHardNegative) -> dict[str, Any]:
    if row.source_type != CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SOURCE_TYPE:
        return {}
    payload = row.payload_json if isinstance(row, RetrievalJudgment) else row.details_json
    details = (payload or {}).get("source_details") or {}
    return dict(details) if isinstance(details, dict) else {}


def _claim_support_corpus_source_reference_payloads(
    rows: list[RetrievalJudgment | RetrievalHardNegative],
) -> tuple[list[dict[str, Any]], dict[str, set[UUID]], list[str]]:
    references: list[dict[str, Any]] = []
    ids: dict[str, set[UUID]] = {
        "snapshot_ids": set(),
        "row_ids": set(),
        "promotion_artifact_ids": set(),
        "promotion_event_ids": set(),
        "escalation_event_ids": set(),
        "snapshot_governance_artifact_ids": set(),
        "snapshot_governance_event_ids": set(),
    }
    failures: list[str] = []
    for row in rows:
        details = _claim_support_source_details(row)
        if not details:
            continue
        carrier_type = (
            "retrieval_judgment"
            if isinstance(row, RetrievalJudgment)
            else "retrieval_hard_negative"
        )
        snapshot = details.get("snapshot") if isinstance(details.get("snapshot"), dict) else {}
        corpus_row = details.get("row") if isinstance(details.get("row"), dict) else {}
        snapshot_id = _uuid_or_none(snapshot.get("snapshot_id"))
        corpus_row_id = _uuid_or_none(corpus_row.get("corpus_row_id"))
        promotion_artifact_id = _uuid_or_none(corpus_row.get("promotion_artifact_id"))
        promotion_event_id = _uuid_or_none(corpus_row.get("promotion_event_id"))
        snapshot_artifact_id = _uuid_or_none(snapshot.get("governance_artifact_id"))
        snapshot_event_id = _uuid_or_none(snapshot.get("semantic_governance_event_id"))
        escalation_event_ids = [
            _uuid_or_none(value)
            for value in corpus_row.get("source_escalation_event_ids") or []
        ]
        if snapshot_id is None:
            failures.append(f"{carrier_type}:{row.id}:snapshot_id_missing")
        else:
            ids["snapshot_ids"].add(snapshot_id)
        if corpus_row_id is None:
            failures.append(f"{carrier_type}:{row.id}:corpus_row_id_missing")
        else:
            ids["row_ids"].add(corpus_row_id)
        if promotion_artifact_id is None:
            failures.append(f"{carrier_type}:{row.id}:promotion_artifact_id_missing")
        else:
            ids["promotion_artifact_ids"].add(promotion_artifact_id)
        if promotion_event_id is None:
            failures.append(f"{carrier_type}:{row.id}:promotion_event_id_missing")
        else:
            ids["promotion_event_ids"].add(promotion_event_id)
        if snapshot_artifact_id is not None:
            ids["snapshot_governance_artifact_ids"].add(snapshot_artifact_id)
        if snapshot_event_id is not None:
            ids["snapshot_governance_event_ids"].add(snapshot_event_id)
        parsed_escalation_ids = [value for value in escalation_event_ids if value is not None]
        if len(parsed_escalation_ids) != len(corpus_row.get("source_escalation_event_ids") or []):
            failures.append(f"{carrier_type}:{row.id}:source_escalation_event_id_invalid")
        ids["escalation_event_ids"].update(parsed_escalation_ids)
        references.append(
            {
                "carrier_type": carrier_type,
                "carrier_id": str(row.id),
                "source_payload_sha256": row.source_payload_sha256,
                "snapshot_id": str(snapshot_id) if snapshot_id else None,
                "snapshot_sha256": snapshot.get("snapshot_sha256"),
                "corpus_row_id": str(corpus_row_id) if corpus_row_id else None,
                "case_id": corpus_row.get("case_id"),
                "case_identity_sha256": corpus_row.get("case_identity_sha256"),
                "fixture_sha256": corpus_row.get("fixture_sha256"),
                "promotion_event_id": str(promotion_event_id) if promotion_event_id else None,
                "promotion_artifact_id": (
                    str(promotion_artifact_id) if promotion_artifact_id else None
                ),
                "promotion_receipt_sha256": corpus_row.get("promotion_receipt_sha256"),
                "snapshot_governance_event_id": (
                    str(snapshot_event_id) if snapshot_event_id else None
                ),
                "snapshot_governance_artifact_id": (
                    str(snapshot_artifact_id) if snapshot_artifact_id else None
                ),
                "snapshot_governance_receipt_sha256": snapshot.get(
                    "governance_receipt_sha256"
                ),
                "source_change_impact_ids": list(corpus_row.get("source_change_impact_ids") or []),
                "source_escalation_event_ids": [
                    str(value) for value in parsed_escalation_ids
                ],
            }
        )
    return references, ids, failures


def _sorted_text_values(values: list[Any] | tuple[Any, ...] | set[Any] | None) -> list[str]:
    return sorted(str(value) for value in values or [])


def _agent_task_artifact_payload(row: AgentTaskArtifact) -> dict[str, Any]:
    payload = row.payload_json or {}
    receipt_sha256 = payload.get("receipt_sha256")
    return {
        "artifact_id": str(row.id),
        "task_id": str(row.task_id),
        "attempt_id": str(row.attempt_id) if row.attempt_id else None,
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "payload_sha256": _payload_sha256(payload),
        "receipt_sha256": receipt_sha256,
        "receipt_hash_matches": _payload_hash_matches_embedded_field(
            payload,
            hash_field="receipt_sha256",
        ),
        "payload": payload,
        "created_at": row.created_at.isoformat(),
    }


def _claim_support_corpus_snapshot_payload(
    row: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> dict[str, Any]:
    snapshot_payload = row.snapshot_payload_json or {}
    computed_sha256 = _payload_sha256(snapshot_payload)
    return {
        "snapshot_id": str(row.id),
        "snapshot_name": row.snapshot_name,
        "status": row.status,
        "snapshot_sha256": row.snapshot_sha256,
        "computed_snapshot_sha256": computed_sha256,
        "snapshot_hash_matches": computed_sha256 == row.snapshot_sha256,
        "fixture_count": row.fixture_count,
        "promotion_event_count": row.promotion_event_count,
        "promotion_fixture_set_count": row.promotion_fixture_set_count,
        "invalid_promotion_event_count": row.invalid_promotion_event_count,
        "source_promotion_event_ids": list(row.source_promotion_event_ids_json or []),
        "source_promotion_artifact_ids": list(row.source_promotion_artifact_ids_json or []),
        "source_promotion_receipt_sha256s": list(
            row.source_promotion_receipt_sha256s_json or []
        ),
        "source_fixture_set_ids": list(row.source_fixture_set_ids_json or []),
        "source_fixture_set_sha256s": list(row.source_fixture_set_sha256s_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        "invalid_promotion_event_ids": list(row.invalid_promotion_event_ids_json or []),
        "semantic_governance_event_id": (
            str(row.semantic_governance_event_id) if row.semantic_governance_event_id else None
        ),
        "governance_artifact_id": (
            str(row.governance_artifact_id) if row.governance_artifact_id else None
        ),
        "governance_receipt_sha256": row.governance_receipt_sha256,
        "snapshot_payload": snapshot_payload,
        "created_at": row.created_at.isoformat(),
        "superseded_at": row.superseded_at.isoformat() if row.superseded_at else None,
    }


def _claim_support_corpus_row_payload(
    row: ClaimSupportReplayAlertFixtureCorpusRow,
) -> dict[str, Any]:
    fixture = row.fixture_json or {}
    computed_fixture_sha256 = _payload_sha256(fixture)
    return {
        "corpus_row_id": str(row.id),
        "snapshot_id": str(row.snapshot_id),
        "row_index": row.row_index,
        "case_id": row.case_id,
        "case_identity_sha256": row.case_identity_sha256,
        "fixture_sha256": row.fixture_sha256,
        "computed_fixture_sha256": computed_fixture_sha256,
        "fixture_hash_matches": computed_fixture_sha256 == row.fixture_sha256,
        "fixture": fixture,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "promotion_event_id": str(row.promotion_event_id) if row.promotion_event_id else None,
        "promotion_artifact_id": (
            str(row.promotion_artifact_id) if row.promotion_artifact_id else None
        ),
        "promotion_receipt_sha256": row.promotion_receipt_sha256,
        "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        "replay_alert_source": row.replay_alert_source_json or {},
        "created_at": row.created_at.isoformat(),
    }


def _claim_support_replay_alert_corpus_lineage_payload(
    session: Session,
    *,
    judgments: list[RetrievalJudgment],
    hard_negatives: list[RetrievalHardNegative],
) -> dict[str, Any]:
    references, ids, failures = _claim_support_corpus_source_reference_payloads(
        [*judgments, *hard_negatives]
    )
    snapshots = _load_by_ids(
        session,
        ClaimSupportReplayAlertFixtureCorpusSnapshot,
        ids["snapshot_ids"],
    )
    rows = _load_by_ids(session, ClaimSupportReplayAlertFixtureCorpusRow, ids["row_ids"])
    promotion_artifacts = _load_by_ids(
        session,
        AgentTaskArtifact,
        ids["promotion_artifact_ids"],
    )
    snapshot_governance_artifacts = _load_by_ids(
        session,
        AgentTaskArtifact,
        ids["snapshot_governance_artifact_ids"],
    )
    promotion_events = _load_by_ids(
        session,
        SemanticGovernanceEvent,
        ids["promotion_event_ids"],
    )
    escalation_events = _load_by_ids(
        session,
        SemanticGovernanceEvent,
        ids["escalation_event_ids"],
    )
    snapshot_governance_events = _load_by_ids(
        session,
        SemanticGovernanceEvent,
        ids["snapshot_governance_event_ids"],
    )

    missing = {
        "snapshot_ids": sorted(str(value) for value in ids["snapshot_ids"] - set(snapshots)),
        "row_ids": sorted(str(value) for value in ids["row_ids"] - set(rows)),
        "promotion_artifact_ids": sorted(
            str(value) for value in ids["promotion_artifact_ids"] - set(promotion_artifacts)
        ),
        "promotion_event_ids": sorted(
            str(value) for value in ids["promotion_event_ids"] - set(promotion_events)
        ),
        "escalation_event_ids": sorted(
            str(value) for value in ids["escalation_event_ids"] - set(escalation_events)
        ),
        "snapshot_governance_artifact_ids": sorted(
            str(value)
            for value in ids["snapshot_governance_artifact_ids"]
            - set(snapshot_governance_artifacts)
        ),
        "snapshot_governance_event_ids": sorted(
            str(value)
            for value in ids["snapshot_governance_event_ids"] - set(snapshot_governance_events)
        ),
    }
    for key, values in missing.items():
        failures.extend(f"{key}:{value}:missing" for value in values)

    snapshot_payloads = [_claim_support_corpus_snapshot_payload(row) for row in snapshots.values()]
    corpus_row_payloads = [_claim_support_corpus_row_payload(row) for row in rows.values()]
    promotion_artifact_payloads = [
        _agent_task_artifact_payload(row) for row in promotion_artifacts.values()
    ]
    snapshot_artifact_payloads = [
        _agent_task_artifact_payload(row) for row in snapshot_governance_artifacts.values()
    ]
    promotion_event_payloads = [
        _semantic_governance_event_payload(row) for row in promotion_events.values()
    ]
    escalation_event_payloads = [
        _semantic_governance_event_payload(row) for row in escalation_events.values()
    ]
    snapshot_event_payloads = [
        _semantic_governance_event_payload(row) for row in snapshot_governance_events.values()
    ]

    reference_snapshot_hashes_match = all(
        (snapshot_id := _uuid_or_none(reference.get("snapshot_id"))) in snapshots
        and snapshots[snapshot_id].snapshot_sha256 == reference.get("snapshot_sha256")
        for reference in references
    )
    reference_row_identity_hashes_match = all(
        (corpus_row_id := _uuid_or_none(reference.get("corpus_row_id"))) in rows
        and rows[corpus_row_id].fixture_sha256 == reference.get("fixture_sha256")
        and rows[corpus_row_id].case_id == reference.get("case_id")
        and rows[corpus_row_id].case_identity_sha256
        == reference.get("case_identity_sha256")
        and rows[corpus_row_id].snapshot_id == _uuid_or_none(reference.get("snapshot_id"))
        for reference in references
    )
    reference_row_promotion_links_match = all(
        (corpus_row_id := _uuid_or_none(reference.get("corpus_row_id"))) in rows
        and str(rows[corpus_row_id].promotion_event_id) == reference.get("promotion_event_id")
        and str(rows[corpus_row_id].promotion_artifact_id)
        == reference.get("promotion_artifact_id")
        and rows[corpus_row_id].promotion_receipt_sha256
        == reference.get("promotion_receipt_sha256")
        for reference in references
    )
    reference_row_source_links_match = all(
        (corpus_row_id := _uuid_or_none(reference.get("corpus_row_id"))) in rows
        and _sorted_text_values(rows[corpus_row_id].source_change_impact_ids_json)
        == _sorted_text_values(reference.get("source_change_impact_ids"))
        and _sorted_text_values(rows[corpus_row_id].source_escalation_event_ids_json)
        == _sorted_text_values(reference.get("source_escalation_event_ids"))
        for reference in references
    )
    reference_snapshot_governance_links_match = all(
        (snapshot_id := _uuid_or_none(reference.get("snapshot_id"))) in snapshots
        and str(snapshots[snapshot_id].semantic_governance_event_id)
        == reference.get("snapshot_governance_event_id")
        and str(snapshots[snapshot_id].governance_artifact_id)
        == reference.get("snapshot_governance_artifact_id")
        and snapshots[snapshot_id].governance_receipt_sha256
        == reference.get("snapshot_governance_receipt_sha256")
        for reference in references
    )
    promotion_artifact_hashes_match = all(
        row["artifact_kind"] == CLAIM_SUPPORT_FIXTURE_PROMOTION_ARTIFACT_KIND
        and row["receipt_hash_matches"]
        for row in promotion_artifact_payloads
    )
    snapshot_artifact_hashes_match = all(
        row["artifact_kind"] == CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_ARTIFACT_KIND
        and row["receipt_hash_matches"]
        for row in snapshot_artifact_payloads
    )
    promotion_event_kinds_match = all(
        row.event_kind == CLAIM_SUPPORT_FIXTURE_PROMOTION_EVENT_KIND
        for row in promotion_events.values()
    )
    escalation_event_kinds_match = all(
        row.event_kind == CLAIM_SUPPORT_REPLAY_ESCALATION_EVENT_KIND
        and row.subject_table == "claim_support_policy_change_impacts"
        for row in escalation_events.values()
    )
    snapshot_event_kinds_match = all(
        row.event_kind == CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_EVENT_KIND
        and row.subject_table == "claim_support_replay_alert_fixture_corpus_snapshots"
        for row in snapshot_governance_events.values()
    )
    promotion_event_integrity_complete = all(
        row["integrity"]["complete"] for row in promotion_event_payloads
    )
    escalation_event_integrity_complete = all(
        row["integrity"]["complete"] for row in escalation_event_payloads
    )
    snapshot_event_integrity_complete = all(
        row["integrity"]["complete"] for row in snapshot_event_payloads
    )
    row_snapshot_links_match = all(row.snapshot_id in snapshots for row in rows.values())
    row_promotion_links_match = all(
        row.promotion_event_id in promotion_events
        and row.promotion_artifact_id in promotion_artifacts
        for row in rows.values()
    )
    row_escalation_links_match = all(
        all(
            _uuid_or_none(value) in escalation_events
            for value in row.source_escalation_event_ids_json
        )
        for row in rows.values()
    )
    snapshot_governance_links_match = all(
        row.semantic_governance_event_id in snapshot_governance_events
        and row.governance_artifact_id in snapshot_governance_artifacts
        for row in snapshots.values()
    )
    row_fixture_hashes_match = all(row["fixture_hash_matches"] for row in corpus_row_payloads)
    snapshot_hashes_match = all(row["snapshot_hash_matches"] for row in snapshot_payloads)
    source_references_resolve = not any(missing.values()) and not failures
    integrity = {
        "source_reference_count": len(references),
        "snapshot_count": len(snapshot_payloads),
        "row_count": len(corpus_row_payloads),
        "promotion_artifact_count": len(promotion_artifact_payloads),
        "promotion_event_count": len(promotion_event_payloads),
        "escalation_event_count": len(escalation_event_payloads),
        "snapshot_governance_artifact_count": len(snapshot_artifact_payloads),
        "snapshot_governance_event_count": len(snapshot_event_payloads),
        "source_references_resolve": source_references_resolve,
        "reference_snapshot_hashes_match": reference_snapshot_hashes_match,
        "reference_row_identity_hashes_match": reference_row_identity_hashes_match,
        "reference_row_promotion_links_match": reference_row_promotion_links_match,
        "reference_row_source_links_match": reference_row_source_links_match,
        "reference_snapshot_governance_links_match": (
            reference_snapshot_governance_links_match
        ),
        "row_fixture_hashes_match": row_fixture_hashes_match,
        "snapshot_hashes_match": snapshot_hashes_match,
        "promotion_artifact_hashes_match": promotion_artifact_hashes_match,
        "snapshot_artifact_hashes_match": snapshot_artifact_hashes_match,
        "promotion_event_kinds_match": promotion_event_kinds_match,
        "escalation_event_kinds_match": escalation_event_kinds_match,
        "snapshot_event_kinds_match": snapshot_event_kinds_match,
        "promotion_event_integrity_complete": promotion_event_integrity_complete,
        "escalation_event_integrity_complete": escalation_event_integrity_complete,
        "snapshot_event_integrity_complete": snapshot_event_integrity_complete,
        "row_snapshot_links_match": row_snapshot_links_match,
        "row_promotion_links_match": row_promotion_links_match,
        "row_escalation_links_match": row_escalation_links_match,
        "snapshot_governance_links_match": snapshot_governance_links_match,
        "missing": missing,
        "failures": sorted(set(failures)),
    }
    integrity["complete"] = all(
        bool(integrity[key])
        for key in (
            "source_references_resolve",
            "reference_snapshot_hashes_match",
            "reference_row_identity_hashes_match",
            "reference_row_promotion_links_match",
            "reference_row_source_links_match",
            "reference_snapshot_governance_links_match",
            "row_fixture_hashes_match",
            "snapshot_hashes_match",
            "promotion_artifact_hashes_match",
            "snapshot_artifact_hashes_match",
            "promotion_event_kinds_match",
            "escalation_event_kinds_match",
            "snapshot_event_kinds_match",
            "promotion_event_integrity_complete",
            "escalation_event_integrity_complete",
            "snapshot_event_integrity_complete",
            "row_snapshot_links_match",
            "row_promotion_links_match",
            "row_escalation_links_match",
            "snapshot_governance_links_match",
        )
    )
    return {
        "source_references": references,
        "snapshots": sorted(snapshot_payloads, key=lambda row: row["snapshot_id"]),
        "rows": sorted(corpus_row_payloads, key=lambda row: (row["snapshot_id"], row["row_index"])),
        "promotion_artifacts": sorted(
            promotion_artifact_payloads,
            key=lambda row: row["artifact_id"],
        ),
        "promotion_events": sorted(promotion_event_payloads, key=lambda row: row["event_id"]),
        "escalation_events": sorted(escalation_event_payloads, key=lambda row: row["event_id"]),
        "snapshot_governance_artifacts": sorted(
            snapshot_artifact_payloads,
            key=lambda row: row["artifact_id"],
        ),
        "snapshot_governance_events": sorted(
            snapshot_event_payloads,
            key=lambda row: row["event_id"],
        ),
        "integrity": integrity,
    }


def _training_run_claim_support_replay_alert_corpus_lineage_payload(
    session: Session,
    training_run: RetrievalTrainingRun,
) -> dict[str, Any]:
    judgments = (
        session.execute(
            select(RetrievalJudgment)
            .where(RetrievalJudgment.judgment_set_id == training_run.judgment_set_id)
            .order_by(RetrievalJudgment.created_at.asc(), RetrievalJudgment.id.asc())
        )
        .scalars()
        .all()
    )
    hard_negatives = (
        session.execute(
            select(RetrievalHardNegative)
            .where(RetrievalHardNegative.judgment_set_id == training_run.judgment_set_id)
            .order_by(RetrievalHardNegative.created_at.asc(), RetrievalHardNegative.id.asc())
        )
        .scalars()
        .all()
    )
    return _claim_support_replay_alert_corpus_lineage_payload(
        session,
        judgments=judgments,
        hard_negatives=hard_negatives,
    )


def _payload_requires_claim_support_replay_alert_corpus_lineage(
    payload: dict[str, Any],
) -> bool:
    corpus_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
    if corpus_integrity.get("source_reference_count", 0):
        return True
    return any(
        row.get("source_type") == CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SOURCE_TYPE
        for row in [
            *(payload.get("retrieval_judgments") or []),
            *(payload.get("retrieval_hard_negatives") or []),
        ]
        if isinstance(row, dict)
    )


def _payload_claim_support_replay_alert_corpus_lineage_complete(
    payload: dict[str, Any],
) -> bool:
    if not _payload_requires_claim_support_replay_alert_corpus_lineage(payload):
        return True
    audit_checklist = payload.get("audit_checklist") or {}
    corpus_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
    return (
        audit_checklist.get("claim_support_replay_alert_corpus_lineage_complete")
        is True
        and corpus_integrity.get("complete") is True
    )


def _training_audit_bundle_hashes_match_training_run(
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


def _training_audit_bundle_claim_support_replay_alert_corpus_lineage_status(
    session: Session,
    bundle: AuditBundleExport | None,
    training_run: RetrievalTrainingRun,
) -> dict[str, Any]:
    payload = (bundle.bundle_payload_json or {}).get("payload") if bundle else {}
    payload = payload if isinstance(payload, dict) else {}
    bundle_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
    current_lineage = _training_run_claim_support_replay_alert_corpus_lineage_payload(
        session,
        training_run,
    )
    current_integrity = current_lineage["integrity"]
    bundle_source_reference_count = int(bundle_integrity.get("source_reference_count") or 0)
    current_source_reference_count = int(current_integrity.get("source_reference_count") or 0)
    bundle_required = _payload_requires_claim_support_replay_alert_corpus_lineage(payload)
    current_required = current_source_reference_count > 0
    required = bundle_required or current_required
    bundle_complete = _payload_claim_support_replay_alert_corpus_lineage_complete(payload)
    current_complete = (
        True if not current_required else current_integrity.get("complete") is True
    )
    source_reference_counts_match = (
        bundle_source_reference_count == current_source_reference_count
    )
    complete = (
        True
        if not required
        else bundle_complete and current_complete and source_reference_counts_match
    )
    return {
        "required": required,
        "bundle_required": bundle_required,
        "current_required": current_required,
        "bundle_source_reference_count": bundle_source_reference_count,
        "current_source_reference_count": current_source_reference_count,
        "source_reference_counts_match": source_reference_counts_match,
        "bundle_complete": bundle_complete,
        "current_complete": current_complete,
        "complete": complete,
        "current_failures": list(current_integrity.get("failures") or []),
        "current_missing": current_integrity.get("missing") or {},
    }


def _training_audit_bundle_current_for_training_run(
    session: Session,
    bundle: AuditBundleExport | None,
    training_run: RetrievalTrainingRun,
) -> bool:
    if not _training_audit_bundle_hashes_match_training_run(bundle, training_run):
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


def _validation_error(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


def _append_missing_key_errors(
    errors: list[dict[str, str]],
    payload: dict[str, Any],
    required_keys: tuple[str, ...],
    *,
    path: str,
) -> None:
    for key in required_keys:
        if key not in payload:
            errors.append(
                _validation_error(
                    "required_key_missing",
                    f"Required key `{key}` is missing.",
                    f"{path}.{key}",
                )
            )


def _append_required_list_error(
    errors: list[dict[str, str]],
    payload: dict[str, Any],
    key: str,
    *,
    path: str,
) -> None:
    if not isinstance(payload.get(key), list):
        errors.append(
            _validation_error(
                "required_list_missing",
                f"Required list `{key}` is missing.",
                f"{path}.{key}",
            )
        )


def _validate_bundle_payload_schema(
    *,
    row: AuditBundleExport,
    bundle: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if bundle.get("schema_name") != "audit_bundle_export":
        errors.append(
            _validation_error(
                "invalid_bundle_schema",
                "Bundle schema_name must be audit_bundle_export.",
                "bundle.schema_name",
            )
        )
    export = bundle.get("bundle_export")
    payload = bundle.get("payload")
    if not isinstance(export, dict):
        errors.append(
            _validation_error(
                "bundle_export_missing",
                "Bundle export metadata must be present.",
                "bundle.bundle_export",
            )
        )
        export = {}
    if not isinstance(payload, dict):
        errors.append(
            _validation_error(
                "payload_missing",
                "Bundle payload must be present.",
                "bundle.payload",
            )
        )
        payload = {}
    for key in ("bundle_id", "bundle_kind", "source_table", "source_id", "payload_sha256"):
        if export.get(key) is None:
            errors.append(
                _validation_error(
                    "bundle_export_field_missing",
                    f"Bundle export field `{key}` is missing.",
                    f"bundle.bundle_export.{key}",
                )
            )
    if export.get("bundle_id") != str(row.id):
        errors.append(
            _validation_error(
                "bundle_id_mismatch",
                "Bundle export id does not match the database row.",
                "bundle.bundle_export.bundle_id",
            )
        )
    if export.get("bundle_kind") != row.bundle_kind:
        errors.append(
            _validation_error(
                "bundle_kind_mismatch",
                "Bundle export kind does not match the database row.",
                "bundle.bundle_export.bundle_kind",
            )
        )
    if row.bundle_kind == SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND:
        if payload.get("schema_name") != "search_harness_release_audit_payload":
            errors.append(
                _validation_error(
                    "invalid_release_payload_schema",
                    "Release audit payload schema_name is invalid.",
                    "bundle.payload.schema_name",
                )
            )
        release_payload_schema_version = payload.get("schema_version")
        requires_reranker_artifacts = (
            release_payload_schema_version != "1.0" or "retrieval_reranker_artifacts" in payload
        )
        requires_training_corpus_lineage = (
            release_payload_schema_version != "1.0"
            or "training_audit_bundle_corpus_lineage_complete" in (payload.get("integrity") or {})
        )
        required_keys = [
            "release",
            "evaluation",
            "evaluation_sources",
            "replay_runs",
            "retrieval_learning_candidates",
            "retrieval_training_runs",
            "retrieval_training_audit_bundles",
            "retrieval_training_audit_bundle_validation_receipts",
            "semantic_governance_events",
            "semantic_governance_policy",
            "audit_checklist",
            "integrity",
            "prov",
        ]
        required_list_keys = [
            "evaluation_sources",
            "replay_runs",
            "retrieval_learning_candidates",
            "retrieval_training_runs",
            "retrieval_training_audit_bundles",
            "retrieval_training_audit_bundle_validation_receipts",
            "semantic_governance_events",
        ]
        if requires_reranker_artifacts:
            required_keys.append("retrieval_reranker_artifacts")
            required_list_keys.append("retrieval_reranker_artifacts")
        _append_missing_key_errors(
            errors,
            payload,
            tuple(required_keys),
            path="bundle.payload",
        )
        for key in required_list_keys:
            _append_required_list_error(errors, payload, key, path="bundle.payload")
        audit_checklist = payload.get("audit_checklist") or {}
        integrity = payload.get("integrity") or {}
        if audit_checklist.get("complete") is not True:
            errors.append(
                _validation_error(
                    "audit_checklist_incomplete",
                    "Release audit checklist is not complete.",
                    "bundle.payload.audit_checklist.complete",
                )
            )
        if integrity.get("training_audit_bundle_hashes_match_training_runs") is not True:
            errors.append(
                _validation_error(
                    "training_bundle_hash_mismatch",
                    "Training audit bundle hashes must match linked training runs.",
                    "bundle.payload.integrity.training_audit_bundle_hashes_match_training_runs",
                )
            )
        if (
            requires_training_corpus_lineage
            and integrity.get("training_audit_bundle_corpus_lineage_complete") is not True
        ):
            errors.append(
                _validation_error(
                    "training_bundle_corpus_lineage_incomplete",
                    (
                        "Training audit bundles sourced from the replay-alert corpus "
                        "must still match current governed corpus lineage."
                    ),
                    "bundle.payload.integrity.training_audit_bundle_corpus_lineage_complete",
                )
            )
        if (
            requires_reranker_artifacts
            and integrity.get("reranker_artifact_hashes_match") is not True
        ):
            errors.append(
                _validation_error(
                    "reranker_artifact_hash_mismatch",
                    "Reranker artifact hashes must match their frozen payloads.",
                    "bundle.payload.integrity.reranker_artifact_hashes_match",
                )
            )
        if (
            requires_reranker_artifacts
            and integrity.get("reranker_artifact_change_impacts_complete") is not True
        ):
            errors.append(
                _validation_error(
                    "reranker_artifact_change_impact_incomplete",
                    "Reranker artifact change-impact reports must be complete.",
                    "bundle.payload.integrity.reranker_artifact_change_impacts_complete",
                )
            )
    elif row.bundle_kind == RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND:
        if payload.get("schema_name") != "retrieval_training_run_audit_payload":
            errors.append(
                _validation_error(
                    "invalid_training_payload_schema",
                    "Retrieval training audit payload schema_name is invalid.",
                    "bundle.payload.schema_name",
                )
            )
        training_payload_schema_version = payload.get("schema_version")
        requires_corpus_lineage = (
            training_payload_schema_version not in {None, "1.0"}
            or "claim_support_replay_alert_corpus_integrity" in payload
            or _payload_requires_claim_support_replay_alert_corpus_lineage(payload)
        )
        required_keys = [
            "retrieval_training_run",
            "retrieval_judgment_set",
            "retrieval_judgments",
            "retrieval_hard_negatives",
            "source_payload_hashes",
            "semantic_governance_events",
            "audit_checklist",
            "integrity",
            "prov",
        ]
        required_list_keys = [
            "retrieval_judgments",
            "retrieval_hard_negatives",
            "source_payload_hashes",
            "semantic_governance_events",
        ]
        if requires_corpus_lineage:
            required_keys.extend(
                [
                    "claim_support_replay_alert_corpus_source_references",
                    "claim_support_replay_alert_corpus_snapshots",
                    "claim_support_replay_alert_corpus_rows",
                    "claim_support_replay_alert_promotion_artifacts",
                    "claim_support_replay_alert_promotion_events",
                    "claim_support_replay_alert_escalation_events",
                    "claim_support_replay_alert_snapshot_governance_artifacts",
                    "claim_support_replay_alert_snapshot_governance_events",
                    "claim_support_replay_alert_corpus_integrity",
                ]
            )
            required_list_keys.extend(
                [
                    "claim_support_replay_alert_corpus_source_references",
                    "claim_support_replay_alert_corpus_snapshots",
                    "claim_support_replay_alert_corpus_rows",
                    "claim_support_replay_alert_promotion_artifacts",
                    "claim_support_replay_alert_promotion_events",
                    "claim_support_replay_alert_escalation_events",
                    "claim_support_replay_alert_snapshot_governance_artifacts",
                    "claim_support_replay_alert_snapshot_governance_events",
                ]
            )
        _append_missing_key_errors(
            errors,
            payload,
            tuple(required_keys),
            path="bundle.payload",
        )
        for key in required_list_keys:
            _append_required_list_error(errors, payload, key, path="bundle.payload")
        audit_checklist = payload.get("audit_checklist") or {}
        integrity = payload.get("integrity") or {}
        corpus_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
        if audit_checklist.get("complete") is not True:
            errors.append(
                _validation_error(
                    "audit_checklist_incomplete",
                    "Training audit checklist is not complete.",
                    "bundle.payload.audit_checklist.complete",
                )
            )
        if integrity.get("training_dataset_hash_matches") is not True:
            errors.append(
                _validation_error(
                    "training_dataset_hash_mismatch",
                    "Training dataset hash must match the canonical payload.",
                    "bundle.payload.integrity.training_dataset_hash_matches",
                )
            )
        if (
            requires_corpus_lineage
            and corpus_integrity.get("source_reference_count", 0)
            and corpus_integrity.get("complete") is not True
        ):
            errors.append(
                _validation_error(
                    "claim_support_replay_alert_corpus_lineage_incomplete",
                    "Claim-support replay-alert corpus lineage must be complete.",
                    "bundle.payload.claim_support_replay_alert_corpus_integrity.complete",
                )
            )
    else:
        errors.append(
            _validation_error(
                "unsupported_bundle_kind",
                "Audit bundle kind is not supported by the validation profile.",
                "bundle.bundle_export.bundle_kind",
            )
        )
    return errors


def _validate_bundle_source_integrity(
    *,
    row: AuditBundleExport,
    bundle: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    export = bundle.get("bundle_export") or {}
    payload = bundle.get("payload") or {}
    source = payload.get("source") or {}
    expected = {
        "bundle_kind": row.bundle_kind,
        "source_table": row.source_table,
        "source_id": str(row.source_id),
    }
    for key, expected_value in expected.items():
        if export.get(key) != expected_value:
            errors.append(
                _validation_error(
                    "bundle_export_source_mismatch",
                    f"Bundle export `{key}` does not match the database row.",
                    f"bundle.bundle_export.{key}",
                )
            )
    if source.get("source_table") != row.source_table:
        errors.append(
            _validation_error(
                "payload_source_table_mismatch",
                "Payload source_table does not match the database row.",
                "bundle.payload.source.source_table",
            )
        )
    if source.get("source_id") != str(row.source_id):
        errors.append(
            _validation_error(
                "payload_source_id_mismatch",
                "Payload source_id does not match the database row.",
                "bundle.payload.source.source_id",
            )
        )
    if row.bundle_kind == SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND:
        if row.search_harness_release_id != row.source_id or row.retrieval_training_run_id:
            errors.append(
                _validation_error(
                    "release_source_fk_mismatch",
                    "Release bundle source fields do not match release foreign keys.",
                    "audit_bundle_exports.search_harness_release_id",
                )
            )
    if row.bundle_kind == RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND:
        if row.retrieval_training_run_id != row.source_id:
            errors.append(
                _validation_error(
                    "training_source_fk_mismatch",
                    "Training bundle source fields do not match training run foreign keys.",
                    "audit_bundle_exports.retrieval_training_run_id",
                )
            )
        training_run = payload.get("retrieval_training_run") or {}
        if training_run.get("retrieval_training_run_id") != str(row.source_id):
            errors.append(
                _validation_error(
                    "training_payload_id_mismatch",
                    "Training payload id does not match the bundle source id.",
                    "bundle.payload.retrieval_training_run.retrieval_training_run_id",
                )
            )
    return errors


def _semantic_governance_chain_checks(
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    event_ids = {str(row.get("event_id")) for row in events if row.get("event_id")}
    event_hashes_by_id = {
        str(row.get("event_id")): row.get("event_hash") for row in events if row.get("event_id")
    }
    external_previous_event_count = 0
    hash_link_mismatch_count = 0
    for row in events:
        previous_event_id = row.get("previous_event_id")
        if not previous_event_id:
            continue
        if previous_event_id not in event_ids:
            external_previous_event_count += 1
            continue
        if row.get("previous_event_hash") != event_hashes_by_id.get(previous_event_id):
            hash_link_mismatch_count += 1
    return {
        "event_count": len(events),
        "external_previous_event_count": external_previous_event_count,
        "hash_link_mismatch_count": hash_link_mismatch_count,
        "hash_links_verified": (
            external_previous_event_count == 0 and hash_link_mismatch_count == 0
        ),
    }


def _validate_release_semantic_governance_policy(
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    policy = payload.get("semantic_governance_policy")
    if not isinstance(policy, dict):
        return [
            _validation_error(
                "semantic_governance_policy_missing",
                "Release audit payload must include a semantic governance policy profile.",
                "bundle.payload.semantic_governance_policy",
            )
        ]
    checks = policy.get("checks") or {}
    if policy.get("schema_name") != "search_harness_release_semantic_governance_policy":
        errors.append(
            _validation_error(
                "invalid_semantic_governance_policy_schema",
                "Release semantic governance policy schema_name is invalid.",
                "bundle.payload.semantic_governance_policy.schema_name",
            )
        )
    if checks.get("has_release_governance_event") is not True:
        errors.append(
            _validation_error(
                "release_governance_event_missing",
                "Release semantic governance policy must reference a release governance event.",
                "bundle.payload.semantic_governance_policy.checks.has_release_governance_event",
            )
        )
    events = payload.get("semantic_governance_events") or []
    chain_checks = _semantic_governance_chain_checks(events if isinstance(events, list) else [])
    if checks.get("hash_links_verified") is not True or not chain_checks["hash_links_verified"]:
        errors.append(
            _validation_error(
                "semantic_governance_chain_broken",
                "Semantic governance event previous-hash links must be closed and verified.",
                "bundle.payload.semantic_governance_policy.checks.hash_links_verified",
            )
        )
    if policy.get("semantic_coverage_claimed") is True:
        if checks.get("has_ontology_snapshot_reference") is not True:
            errors.append(
                _validation_error(
                    "semantic_ontology_snapshot_reference_missing",
                    "Semantic coverage claims require an ontology snapshot reference.",
                    (
                        "bundle.payload.semantic_governance_policy.checks."
                        "has_ontology_snapshot_reference"
                    ),
                )
            )
        if checks.get("has_semantic_graph_snapshot_reference") is not True:
            errors.append(
                _validation_error(
                    "semantic_graph_snapshot_reference_missing",
                    "Semantic coverage claims require a semantic graph snapshot reference.",
                    (
                        "bundle.payload.semantic_governance_policy.checks."
                        "has_semantic_graph_snapshot_reference"
                    ),
                )
            )
    if policy.get("complete") is not True or checks.get("complete") is not True:
        errors.append(
            _validation_error(
                "semantic_governance_policy_incomplete",
                "Release semantic governance policy is incomplete.",
                "bundle.payload.semantic_governance_policy.complete",
            )
        )
    return errors


def _prov_jsonld_node(node_id: str, attrs: dict[str, Any], fallback_type: str) -> dict[str, Any]:
    node = {"@id": node_id, "@type": attrs.get("prov:type") or fallback_type}
    for key, value in sorted(attrs.items()):
        if key == "prov:type":
            continue
        node[key] = value
    return node


def _prov_edge_id(edge_type: str, edge: dict[str, Any]) -> str:
    return "docling:edge:" + _payload_sha256({"edge_type": edge_type, "edge": edge})[:32]


def _prov_jsonld_from_graph(prov: dict[str, Any]) -> dict[str, Any]:
    graph: list[dict[str, Any]] = []
    for entity_id, attrs in sorted((prov.get("entity") or {}).items()):
        graph.append(_prov_jsonld_node(entity_id, attrs, "prov:Entity"))
    for activity_id, attrs in sorted((prov.get("activity") or {}).items()):
        graph.append(_prov_jsonld_node(activity_id, attrs, "prov:Activity"))
    for agent_id, attrs in sorted((prov.get("agent") or {}).items()):
        graph.append(_prov_jsonld_node(agent_id, attrs, "prov:Agent"))
    edge_specs = (
        ("wasGeneratedBy", "prov:Generation"),
        ("used", "prov:Usage"),
        ("wasDerivedFrom", "prov:Derivation"),
        ("wasAssociatedWith", "prov:Association"),
    )
    for edge_key, edge_type in edge_specs:
        for edge in prov.get(edge_key) or []:
            node = {"@id": _prov_edge_id(edge_key, edge), "@type": edge_type}
            for key, value in sorted(edge.items()):
                if isinstance(value, str) and key in {
                    "entity",
                    "activity",
                    "agent",
                    "generatedEntity",
                    "usedEntity",
                }:
                    node[f"prov:{key}"] = {"@id": value}
                else:
                    node[f"prov:{key}"] = value
            graph.append(node)
    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "@graph": graph,
    }


def _validate_prov_graph(bundle: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    payload = bundle.get("payload") or {}
    prov = payload.get("prov") or {}
    if not isinstance(prov, dict):
        return {}, [
            _validation_error(
                "prov_graph_missing",
                "PROV graph must be present.",
                "bundle.payload.prov",
            )
        ]
    entities = set((prov.get("entity") or {}).keys())
    activities = set((prov.get("activity") or {}).keys())
    agents = set((prov.get("agent") or {}).keys())
    if not entities:
        errors.append(
            _validation_error("prov_entities_missing", "PROV graph has no entities.", "prov.entity")
        )
    if not activities:
        errors.append(
            _validation_error(
                "prov_activities_missing",
                "PROV graph has no activities.",
                "prov.activity",
            )
        )
    for index, edge in enumerate(prov.get("wasGeneratedBy") or []):
        if edge.get("entity") not in entities:
            errors.append(
                _validation_error(
                    "prov_generated_entity_missing",
                    "wasGeneratedBy references a missing entity.",
                    f"prov.wasGeneratedBy[{index}].entity",
                )
            )
        if edge.get("activity") not in activities:
            errors.append(
                _validation_error(
                    "prov_generation_activity_missing",
                    "wasGeneratedBy references a missing activity.",
                    f"prov.wasGeneratedBy[{index}].activity",
                )
            )
    for index, edge in enumerate(prov.get("used") or []):
        if edge.get("activity") not in activities:
            errors.append(
                _validation_error(
                    "prov_usage_activity_missing",
                    "used references a missing activity.",
                    f"prov.used[{index}].activity",
                )
            )
        if edge.get("entity") not in entities:
            errors.append(
                _validation_error(
                    "prov_usage_entity_missing",
                    "used references a missing entity.",
                    f"prov.used[{index}].entity",
                )
            )
    for index, edge in enumerate(prov.get("wasDerivedFrom") or []):
        if edge.get("generatedEntity") not in entities:
            errors.append(
                _validation_error(
                    "prov_derivation_generated_entity_missing",
                    "wasDerivedFrom references a missing generated entity.",
                    f"prov.wasDerivedFrom[{index}].generatedEntity",
                )
            )
        if edge.get("usedEntity") not in entities:
            errors.append(
                _validation_error(
                    "prov_derivation_used_entity_missing",
                    "wasDerivedFrom references a missing used entity.",
                    f"prov.wasDerivedFrom[{index}].usedEntity",
                )
            )
    for index, edge in enumerate(prov.get("wasAssociatedWith") or []):
        if edge.get("activity") not in activities:
            errors.append(
                _validation_error(
                    "prov_association_activity_missing",
                    "wasAssociatedWith references a missing activity.",
                    f"prov.wasAssociatedWith[{index}].activity",
                )
            )
        if edge.get("agent") not in agents:
            errors.append(
                _validation_error(
                    "prov_association_agent_missing",
                    "wasAssociatedWith references a missing agent.",
                    f"prov.wasAssociatedWith[{index}].agent",
                )
            )
    return _prov_jsonld_from_graph(prov), errors


def _prov_graph(
    *,
    release: SearchHarnessRelease,
    evaluation: SearchHarnessEvaluation | None,
    sources: list[SearchHarnessEvaluationSource],
    replay_runs: list[SearchReplayRun],
    learning_candidates: list[RetrievalLearningCandidateEvaluation],
    reranker_artifacts: list[RetrievalRerankerArtifact],
    training_runs: list[RetrievalTrainingRun],
    training_audit_bundles: list[AuditBundleExport],
    judgment_sets: list[RetrievalJudgmentSet],
    governance_events: list[SemanticGovernanceEvent],
    bundle_id: UUID,
    created_by: str | None,
) -> dict[str, Any]:
    release_entity = f"docling:search_harness_release:{release.id}"
    evaluation_entity = f"docling:search_harness_evaluation:{release.search_harness_evaluation_id}"
    activity = f"docling:activity:search_harness_release_gate:{release.id}"
    exporter_activity = f"docling:activity:audit_bundle_export:{bundle_id}"
    agent = f"docling:agent:{created_by or release.requested_by or 'system'}"

    entities: dict[str, dict[str, Any]] = {
        release_entity: {
            "prov:type": "docling:SearchHarnessRelease",
            "docling:outcome": release.outcome,
            "docling:releasePackageSha256": release.release_package_sha256,
        },
        evaluation_entity: {
            "prov:type": "docling:SearchHarnessEvaluation",
            "docling:status": evaluation.status if evaluation else None,
        },
        f"docling:thresholds:{release.id}": {
            "prov:type": "docling:ReleaseThresholds",
            "docling:sha256": _payload_sha256(release.thresholds_json or {}),
        },
        f"docling:audit_bundle_export:{bundle_id}": {
            "prov:type": "docling:AuditBundleExport",
            "docling:bundleKind": SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        },
    }
    for source in sources:
        entities[f"docling:search_harness_evaluation_source:{source.id}"] = {
            "prov:type": "docling:SearchHarnessEvaluationSource",
            "docling:sourceType": source.source_type,
        }
    for replay_run in replay_runs:
        entities[f"docling:search_replay_run:{replay_run.id}"] = {
            "prov:type": "docling:SearchReplayRun",
            "docling:status": replay_run.status,
            "docling:harnessName": replay_run.harness_name,
        }
    for candidate in learning_candidates:
        entities[f"docling:retrieval_learning_candidate_evaluation:{candidate.id}"] = {
            "prov:type": "docling:RetrievalLearningCandidateEvaluation",
            "docling:gateOutcome": candidate.gate_outcome,
            "docling:learningPackageSha256": candidate.learning_package_sha256,
        }
    for artifact in reranker_artifacts:
        entities[f"docling:retrieval_reranker_artifact:{artifact.id}"] = {
            "prov:type": "docling:RetrievalRerankerArtifact",
            "docling:artifactKind": artifact.artifact_kind,
            "docling:artifactSha256": artifact.artifact_sha256,
            "docling:changeImpactSha256": artifact.change_impact_sha256,
            "docling:gateOutcome": artifact.gate_outcome,
        }
    for training_run in training_runs:
        entities[f"docling:retrieval_training_run:{training_run.id}"] = {
            "prov:type": "docling:RetrievalTrainingRun",
            "docling:trainingDatasetSha256": training_run.training_dataset_sha256,
            "docling:exampleCount": training_run.example_count,
        }
    for judgment_set in judgment_sets:
        entities[f"docling:retrieval_judgment_set:{judgment_set.id}"] = {
            "prov:type": "docling:RetrievalJudgmentSet",
            "docling:payloadSha256": judgment_set.payload_sha256,
            "docling:judgmentCount": judgment_set.judgment_count,
        }
    for bundle in training_audit_bundles:
        entities[f"docling:audit_bundle_export:{bundle.id}"] = {
            "prov:type": "docling:AuditBundleExport",
            "docling:bundleKind": bundle.bundle_kind,
            "docling:payloadSha256": bundle.payload_sha256,
            "docling:bundleSha256": bundle.bundle_sha256,
            "docling:sourceTable": bundle.source_table,
            "docling:sourceId": str(bundle.source_id),
        }
    for event in governance_events:
        entities[f"docling:semantic_governance_event:{event.id}"] = {
            "prov:type": "docling:SemanticGovernanceEvent",
            "docling:eventKind": event.event_kind,
            "docling:eventHash": event.event_hash,
            "docling:payloadSha256": event.payload_sha256,
        }

    used = [
        {"activity": activity, "entity": evaluation_entity},
        {"activity": activity, "entity": f"docling:thresholds:{release.id}"},
    ]
    was_derived_from = [
        {"generatedEntity": release_entity, "usedEntity": evaluation_entity},
    ]
    for source in sources:
        source_entity = f"docling:search_harness_evaluation_source:{source.id}"
        used.append({"activity": activity, "entity": source_entity})
        was_derived_from.append({"generatedEntity": release_entity, "usedEntity": source_entity})
        was_derived_from.append(
            {
                "generatedEntity": source_entity,
                "usedEntity": f"docling:search_replay_run:{source.baseline_replay_run_id}",
            }
        )
        was_derived_from.append(
            {
                "generatedEntity": source_entity,
                "usedEntity": f"docling:search_replay_run:{source.candidate_replay_run_id}",
            }
        )
    for candidate in learning_candidates:
        candidate_entity = f"docling:retrieval_learning_candidate_evaluation:{candidate.id}"
        training_run_entity = (
            f"docling:retrieval_training_run:{candidate.retrieval_training_run_id}"
        )
        judgment_set_entity = f"docling:retrieval_judgment_set:{candidate.judgment_set_id}"
        used.append({"activity": activity, "entity": candidate_entity})
        was_derived_from.append({"generatedEntity": release_entity, "usedEntity": candidate_entity})
        was_derived_from.append(
            {"generatedEntity": candidate_entity, "usedEntity": training_run_entity}
        )
        was_derived_from.append(
            {"generatedEntity": training_run_entity, "usedEntity": judgment_set_entity}
        )
        if candidate.semantic_governance_event_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": candidate_entity,
                    "usedEntity": (
                        "docling:semantic_governance_event:"
                        f"{candidate.semantic_governance_event_id}"
                    ),
                }
            )

    for artifact in reranker_artifacts:
        artifact_entity = f"docling:retrieval_reranker_artifact:{artifact.id}"
        candidate_entity = (
            "docling:retrieval_learning_candidate_evaluation:"
            f"{artifact.retrieval_learning_candidate_evaluation_id}"
        )
        training_run_entity = f"docling:retrieval_training_run:{artifact.retrieval_training_run_id}"
        used.append({"activity": activity, "entity": artifact_entity})
        was_derived_from.append({"generatedEntity": release_entity, "usedEntity": artifact_entity})
        was_derived_from.append(
            {"generatedEntity": artifact_entity, "usedEntity": candidate_entity}
        )
        was_derived_from.append(
            {"generatedEntity": artifact_entity, "usedEntity": training_run_entity}
        )
        if artifact.semantic_governance_event_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": artifact_entity,
                    "usedEntity": (
                        f"docling:semantic_governance_event:{artifact.semantic_governance_event_id}"
                    ),
                }
            )

    for bundle in training_audit_bundles:
        training_bundle_entity = f"docling:audit_bundle_export:{bundle.id}"
        used.append({"activity": exporter_activity, "entity": training_bundle_entity})
        was_derived_from.append(
            {
                "generatedEntity": f"docling:audit_bundle_export:{bundle_id}",
                "usedEntity": training_bundle_entity,
            }
        )

    return {
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "entity": entities,
        "activity": {
            activity: {
                "prov:type": "docling:SearchHarnessReleaseGate",
                "prov:endedAtTime": release.created_at.isoformat(),
            },
            exporter_activity: {
                "prov:type": "docling:AuditBundleExport",
            },
        },
        "agent": {
            agent: {
                "prov:type": "prov:Person" if created_by else "prov:SoftwareAgent",
                "docling:identifier": created_by or release.requested_by or "system",
            }
        },
        "wasGeneratedBy": [
            {"entity": release_entity, "activity": activity},
            {
                "entity": f"docling:audit_bundle_export:{bundle_id}",
                "activity": exporter_activity,
            },
        ],
        "used": used,
        "wasDerivedFrom": was_derived_from,
        "wasAssociatedWith": [
            {"activity": activity, "agent": agent},
            {"activity": exporter_activity, "agent": agent},
        ],
    }


def _training_run_prov_graph(
    *,
    training_run: RetrievalTrainingRun,
    judgment_set: RetrievalJudgmentSet | None,
    judgments: list[RetrievalJudgment],
    hard_negatives: list[RetrievalHardNegative],
    governance_events: list[SemanticGovernanceEvent],
    claim_support_replay_alert_corpus_lineage: dict[str, Any],
    bundle_id: UUID,
    created_by: str | None,
) -> dict[str, Any]:
    training_entity = f"docling:retrieval_training_run:{training_run.id}"
    dataset_entity = f"docling:retrieval_training_dataset:{training_run.id}"
    judgment_set_entity = f"docling:retrieval_judgment_set:{training_run.judgment_set_id}"
    exporter_activity = f"docling:activity:audit_bundle_export:{bundle_id}"
    materialization_activity = (
        f"docling:activity:retrieval_training_run_materialization:{training_run.id}"
    )
    agent = f"docling:agent:{created_by or training_run.created_by or 'system'}"

    entities: dict[str, dict[str, Any]] = {
        training_entity: {
            "prov:type": "docling:RetrievalTrainingRun",
            "docling:trainingDatasetSha256": training_run.training_dataset_sha256,
            "docling:exampleCount": training_run.example_count,
        },
        dataset_entity: {
            "prov:type": "docling:RetrievalTrainingDataset",
            "docling:sha256": training_run.training_dataset_sha256,
        },
        judgment_set_entity: {
            "prov:type": "docling:RetrievalJudgmentSet",
            "docling:payloadSha256": judgment_set.payload_sha256 if judgment_set else None,
            "docling:judgmentCount": judgment_set.judgment_count if judgment_set else None,
        },
        f"docling:audit_bundle_export:{bundle_id}": {
            "prov:type": "docling:AuditBundleExport",
            "docling:bundleKind": RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
        },
    }
    for judgment in judgments:
        entities[f"docling:retrieval_judgment:{judgment.id}"] = {
            "prov:type": "docling:RetrievalJudgment",
            "docling:judgmentKind": judgment.judgment_kind,
            "docling:sourcePayloadSha256": judgment.source_payload_sha256,
        }
    for hard_negative in hard_negatives:
        entities[f"docling:retrieval_hard_negative:{hard_negative.id}"] = {
            "prov:type": "docling:RetrievalHardNegative",
            "docling:hardNegativeKind": hard_negative.hard_negative_kind,
            "docling:sourcePayloadSha256": hard_negative.source_payload_sha256,
        }
    for event in governance_events:
        entities[f"docling:semantic_governance_event:{event.id}"] = {
            "prov:type": "docling:SemanticGovernanceEvent",
            "docling:eventKind": event.event_kind,
            "docling:eventHash": event.event_hash,
            "docling:payloadSha256": event.payload_sha256,
        }
    for snapshot in claim_support_replay_alert_corpus_lineage.get("snapshots") or []:
        snapshot_entity = (
            "docling:claim_support_replay_alert_corpus_snapshot:"
            f"{snapshot['snapshot_id']}"
        )
        entities[snapshot_entity] = {
            "prov:type": "docling:ClaimSupportReplayAlertFixtureCorpusSnapshot",
            "docling:snapshotSha256": snapshot.get("snapshot_sha256"),
            "docling:computedSnapshotSha256": snapshot.get("computed_snapshot_sha256"),
            "docling:fixtureCount": snapshot.get("fixture_count"),
        }
    for corpus_row in claim_support_replay_alert_corpus_lineage.get("rows") or []:
        entities[f"docling:claim_support_replay_alert_corpus_row:{corpus_row['corpus_row_id']}"] = {
            "prov:type": "docling:ClaimSupportReplayAlertFixtureCorpusRow",
            "docling:fixtureSha256": corpus_row.get("fixture_sha256"),
            "docling:computedFixtureSha256": corpus_row.get("computed_fixture_sha256"),
            "docling:caseId": corpus_row.get("case_id"),
        }
    for artifact in [
        *(claim_support_replay_alert_corpus_lineage.get("promotion_artifacts") or []),
        *(claim_support_replay_alert_corpus_lineage.get("snapshot_governance_artifacts") or []),
    ]:
        entities[f"docling:agent_task_artifact:{artifact['artifact_id']}"] = {
            "prov:type": "docling:AgentTaskArtifact",
            "docling:artifactKind": artifact.get("artifact_kind"),
            "docling:payloadSha256": artifact.get("payload_sha256"),
            "docling:receiptSha256": artifact.get("receipt_sha256"),
        }
    for event_payload in [
        *(claim_support_replay_alert_corpus_lineage.get("promotion_events") or []),
        *(claim_support_replay_alert_corpus_lineage.get("escalation_events") or []),
        *(claim_support_replay_alert_corpus_lineage.get("snapshot_governance_events") or []),
    ]:
        entities[f"docling:semantic_governance_event:{event_payload['event_id']}"] = {
            "prov:type": "docling:SemanticGovernanceEvent",
            "docling:eventKind": event_payload.get("event_kind"),
            "docling:eventHash": event_payload.get("event_hash"),
            "docling:payloadSha256": event_payload.get("payload_sha256"),
        }

    used = [{"activity": materialization_activity, "entity": judgment_set_entity}]
    was_derived_from = [
        {"generatedEntity": training_entity, "usedEntity": judgment_set_entity},
        {"generatedEntity": dataset_entity, "usedEntity": judgment_set_entity},
        {"generatedEntity": training_entity, "usedEntity": dataset_entity},
    ]
    for judgment in judgments:
        judgment_entity = f"docling:retrieval_judgment:{judgment.id}"
        used.append({"activity": materialization_activity, "entity": judgment_entity})
        was_derived_from.append({"generatedEntity": dataset_entity, "usedEntity": judgment_entity})
    for hard_negative in hard_negatives:
        hard_negative_entity = f"docling:retrieval_hard_negative:{hard_negative.id}"
        used.append({"activity": materialization_activity, "entity": hard_negative_entity})
        was_derived_from.append(
            {"generatedEntity": dataset_entity, "usedEntity": hard_negative_entity}
        )
        was_derived_from.append(
            {
                "generatedEntity": hard_negative_entity,
                "usedEntity": f"docling:retrieval_judgment:{hard_negative.judgment_id}",
            }
        )
        if hard_negative.positive_judgment_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": hard_negative_entity,
                    "usedEntity": (
                        f"docling:retrieval_judgment:{hard_negative.positive_judgment_id}"
                    ),
                }
            )
    for event in governance_events:
        governance_entity = f"docling:semantic_governance_event:{event.id}"
        used.append({"activity": exporter_activity, "entity": governance_entity})
        if event.subject_table == RETRIEVAL_TRAINING_RUN_SOURCE_TABLE:
            was_derived_from.append(
                {"generatedEntity": training_entity, "usedEntity": governance_entity}
            )
        if event.previous_event_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": governance_entity,
                    "usedEntity": f"docling:semantic_governance_event:{event.previous_event_id}",
                }
            )
    for reference in claim_support_replay_alert_corpus_lineage.get("source_references") or []:
        row_entity = f"docling:claim_support_replay_alert_corpus_row:{reference['corpus_row_id']}"
        snapshot_entity = (
            "docling:claim_support_replay_alert_corpus_snapshot:"
            f"{reference['snapshot_id']}"
        )
        carrier_entity = f"docling:{reference['carrier_type']}:{reference['carrier_id']}"
        used.append({"activity": materialization_activity, "entity": row_entity})
        was_derived_from.append({"generatedEntity": carrier_entity, "usedEntity": row_entity})
        was_derived_from.append({"generatedEntity": dataset_entity, "usedEntity": row_entity})
        was_derived_from.append({"generatedEntity": row_entity, "usedEntity": snapshot_entity})
        if reference.get("promotion_artifact_id"):
            was_derived_from.append(
                {
                    "generatedEntity": row_entity,
                    "usedEntity": (
                        f"docling:agent_task_artifact:{reference['promotion_artifact_id']}"
                    ),
                }
            )
        if reference.get("promotion_event_id"):
            was_derived_from.append(
                {
                    "generatedEntity": row_entity,
                    "usedEntity": (
                        f"docling:semantic_governance_event:{reference['promotion_event_id']}"
                    ),
                }
            )
        for escalation_event_id in reference.get("source_escalation_event_ids") or []:
            was_derived_from.append(
                {
                    "generatedEntity": row_entity,
                    "usedEntity": f"docling:semantic_governance_event:{escalation_event_id}",
                }
            )
    for snapshot in claim_support_replay_alert_corpus_lineage.get("snapshots") or []:
        snapshot_entity = (
            "docling:claim_support_replay_alert_corpus_snapshot:"
            f"{snapshot['snapshot_id']}"
        )
        if snapshot.get("governance_artifact_id"):
            was_derived_from.append(
                {
                    "generatedEntity": snapshot_entity,
                    "usedEntity": (
                        "docling:agent_task_artifact:"
                        f"{snapshot['governance_artifact_id']}"
                    ),
                }
            )
        if snapshot.get("semantic_governance_event_id"):
            was_derived_from.append(
                {
                    "generatedEntity": snapshot_entity,
                    "usedEntity": (
                        "docling:semantic_governance_event:"
                        f"{snapshot['semantic_governance_event_id']}"
                    ),
                }
            )

    return {
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "entity": entities,
        "activity": {
            materialization_activity: {
                "prov:type": "docling:RetrievalTrainingRunMaterialization",
                "prov:endedAtTime": (
                    training_run.completed_at.isoformat()
                    if training_run.completed_at
                    else training_run.created_at.isoformat()
                ),
            },
            exporter_activity: {
                "prov:type": "docling:AuditBundleExport",
            },
        },
        "agent": {
            agent: {
                "prov:type": "prov:Person" if created_by else "prov:SoftwareAgent",
                "docling:identifier": created_by or training_run.created_by or "system",
            }
        },
        "wasGeneratedBy": [
            {"entity": training_entity, "activity": materialization_activity},
            {"entity": dataset_entity, "activity": materialization_activity},
            {
                "entity": f"docling:audit_bundle_export:{bundle_id}",
                "activity": exporter_activity,
            },
        ],
        "used": used,
        "wasDerivedFrom": was_derived_from,
        "wasAssociatedWith": [
            {"activity": materialization_activity, "agent": agent},
            {"activity": exporter_activity, "agent": agent},
        ],
    }


def _build_retrieval_training_run_payload(
    session: Session,
    *,
    training_run: RetrievalTrainingRun,
    bundle_id: UUID,
    created_by: str | None,
    created_at,
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
    governance_events = _load_training_run_governance_events(session, training_run)
    claim_support_replay_alert_corpus_lineage = (
        _claim_support_replay_alert_corpus_lineage_payload(
            session,
            judgments=judgments,
            hard_negatives=hard_negatives,
        )
    )
    training_payload = training_run.training_payload_json or {}
    training_payload_sha256 = _payload_sha256(training_payload)
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
        "retrieval_training_run": _retrieval_training_run_full_payload(training_run),
        "retrieval_judgment_set": (
            _retrieval_judgment_set_payload(judgment_set) if judgment_set else None
        ),
        "retrieval_judgments": [_retrieval_judgment_payload(row) for row in judgments],
        "retrieval_hard_negatives": [
            _retrieval_hard_negative_payload(row) for row in hard_negatives
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
            "claim_support_replay_alert_corpus_row_count": corpus_lineage_integrity[
                "row_count"
            ],
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
            claim_support_replay_alert_corpus_lineage=(
                claim_support_replay_alert_corpus_lineage
            ),
            bundle_id=bundle_id,
            created_by=created_by,
        ),
    }


def _build_search_harness_release_payload(
    session: Session,
    *,
    release: SearchHarnessRelease,
    bundle_id: UUID,
    created_by: str | None,
    created_at,
) -> dict[str, Any]:
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
    missing_candidate_ids = sorted(
        artifact_candidate_ids - learning_candidate_ids,
        key=str,
    )
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
        if training_run_ids
        else []
    )
    latest_training_audit_bundles_by_run_id: dict[UUID, AuditBundleExport] = {}
    for row in training_audit_bundle_rows:
        if row.retrieval_training_run_id is None:
            continue
        latest_training_audit_bundles_by_run_id.setdefault(
            row.retrieval_training_run_id,
            row,
        )
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
        latest_validation_receipts_by_bundle_id.setdefault(
            receipt.audit_bundle_export_id,
            receipt,
        )
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
            (payload or {}).get("retrieval_training_run") if payload else None
        ) or {}
        corpus_lineage_status = (
            _training_audit_bundle_claim_support_replay_alert_corpus_lineage_status(
                session,
                bundle,
                training_run,
            )
        )
        hashes_match_training_run = _training_audit_bundle_hashes_match_training_run(
            bundle,
            training_run,
        )
        check = {
            "retrieval_training_run_id": str(training_run.id),
            "audit_bundle_id": str(bundle.id) if bundle else None,
            "training_dataset_sha256": training_run.training_dataset_sha256,
            "payload_training_dataset_sha256": payload_training_run.get("training_dataset_sha256"),
            "hashes_match_training_run": hashes_match_training_run,
            "claim_support_replay_alert_corpus_lineage_required": (
                corpus_lineage_status["required"]
            ),
            "claim_support_replay_alert_corpus_lineage_complete": (
                corpus_lineage_status["complete"]
            ),
            "claim_support_replay_alert_corpus_lineage_bundle_complete": (
                corpus_lineage_status["bundle_complete"]
            ),
            "claim_support_replay_alert_corpus_lineage_current_complete": (
                corpus_lineage_status["current_complete"]
            ),
            "claim_support_replay_alert_corpus_source_reference_count": (
                corpus_lineage_status["current_source_reference_count"]
            ),
            "payload_claim_support_replay_alert_corpus_source_reference_count": (
                corpus_lineage_status["bundle_source_reference_count"]
            ),
            "claim_support_replay_alert_corpus_source_reference_counts_match": (
                corpus_lineage_status["source_reference_counts_match"]
            ),
            "claim_support_replay_alert_corpus_current_failures": (
                corpus_lineage_status["current_failures"]
            ),
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
    training_audit_bundle_hashes_match_training_runs = len(
        training_audit_bundle_match_checks
    ) == len(training_run_ids) and all(
        row["hashes_match_training_run"] for row in training_audit_bundle_match_checks
    )
    training_audit_bundle_corpus_lineage_complete = len(
        training_audit_bundle_match_checks
    ) == len(training_run_ids) and all(
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
        "reranker_artifact_change_impacts_complete": (reranker_artifact_change_impacts_complete),
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
        "release": _release_payload(release),
        "evaluation": _evaluation_payload(evaluation),
        "evaluation_sources": [_source_payload(row) for row in sources],
        "replay_runs": [_replay_payload(row) for row in ordered_replay_runs],
        "retrieval_learning_candidates": [
            _retrieval_learning_candidate_payload(row) for row in learning_candidates
        ],
        "retrieval_reranker_artifacts": [
            _retrieval_reranker_artifact_payload(row) for row in reranker_artifacts
        ],
        "retrieval_training_runs": [
            _retrieval_training_run_payload(row) for row in ordered_training_runs
        ],
        "retrieval_training_audit_bundles": [
            _audit_bundle_reference_payload(row) for row in ordered_training_audit_bundles
        ],
        "retrieval_training_audit_bundle_validation_receipts": [
            _validation_receipt_reference_payload(row)
            for row in ordered_training_validation_receipts
        ],
        "retrieval_judgment_sets": [
            _retrieval_judgment_set_payload(row) for row in ordered_judgment_sets
        ],
        "semantic_governance_events": [
            _semantic_governance_event_payload(row) for row in ordered_governance_events
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
            "reranker_artifact_candidate_links_match": (reranker_artifact_candidate_links_match),
            "reranker_artifact_hashes_match": reranker_artifact_hashes_match,
            "reranker_artifact_change_impacts_complete": (
                reranker_artifact_change_impacts_complete
            ),
            "reranker_artifact_governance_event_count": len(reranker_artifact_governance_event_ids),
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
        "prov": _prov_graph(
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


def _bundle_without_bundle_sha256(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(bundle, default=str, sort_keys=True))
    export = normalized.get("bundle_export") or {}
    export.pop("bundle_sha256", None)
    normalized["bundle_export"] = export
    return normalized


def _bundle_sha256(bundle: dict[str, Any]) -> str:
    return _payload_sha256(_bundle_without_bundle_sha256(bundle))


def _signed_bundle(
    *,
    bundle_id: UUID,
    bundle_kind: str,
    source_table: str,
    source_id: UUID,
    payload: dict[str, Any],
    signing_key: str,
    signing_key_id: str,
) -> dict[str, Any]:
    payload_sha256 = _payload_sha256(payload)
    signature = _signature(payload_sha256, signing_key)
    bundle = {
        "schema_name": "audit_bundle_export",
        "schema_version": "1.0",
        "bundle_export": {
            "bundle_id": str(bundle_id),
            "bundle_kind": bundle_kind,
            "source_table": source_table,
            "source_id": str(source_id),
            "payload_sha256": payload_sha256,
            "signature": signature,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signing_key_id": signing_key_id,
        },
        "payload": payload,
    }
    bundle["bundle_export"]["bundle_sha256"] = _bundle_sha256(bundle)
    return bundle


def _to_summary(row: AuditBundleExport) -> AuditBundleExportSummaryResponse:
    return AuditBundleExportSummaryResponse(
        bundle_id=row.id,
        bundle_kind=row.bundle_kind,
        source_table=row.source_table,
        source_id=row.source_id,
        payload_sha256=row.payload_sha256,
        bundle_sha256=row.bundle_sha256,
        signature=row.signature,
        signature_algorithm=row.signature_algorithm,
        signing_key_id=row.signing_key_id,
        created_by=row.created_by,
        export_status=row.export_status,
        created_at=row.created_at,
    )


def _verify_bundle(
    row: AuditBundleExport,
    bundle: dict[str, Any],
    storage_service: StorageService,
) -> dict:
    payload = bundle.get("payload") or {}
    export = bundle.get("bundle_export") or {}
    payload_sha256 = _payload_sha256(payload)
    bundle_sha256 = _bundle_sha256(bundle)
    path = storage_service.resolve_existing_path(row.storage_path)
    file_sha256 = _file_sha256(path)
    try:
        signing_key, _key_id = _signing_key()
        signature_valid = hmac.compare_digest(
            row.signature,
            _signature(row.payload_sha256, signing_key),
        )
        signature_verification_status = "verified" if signature_valid else "mismatch"
    except HTTPException:
        signature_valid = False
        signature_verification_status = "signing_key_missing"
    checks = {
        "payload_hash_matches_row": payload_sha256 == row.payload_sha256,
        "payload_hash_matches_bundle": payload_sha256 == export.get("payload_sha256"),
        "bundle_hash_matches_row": bundle_sha256 == row.bundle_sha256,
        "bundle_hash_matches_bundle": bundle_sha256 == export.get("bundle_sha256"),
        "signature_matches_row": row.signature == export.get("signature"),
        "signature_valid": signature_valid,
        "file_exists": path is not None,
        "file_sha256": file_sha256,
        "stored_payload_matches_file": bool(row.bundle_payload_json == bundle),
    }
    checks["complete"] = all(
        bool(checks[key])
        for key in (
            "payload_hash_matches_row",
            "payload_hash_matches_bundle",
            "bundle_hash_matches_row",
            "bundle_hash_matches_bundle",
            "signature_matches_row",
            "signature_valid",
            "file_exists",
            "stored_payload_matches_file",
        )
    )
    checks["signature_verification_status"] = signature_verification_status
    return checks


def _to_response(
    row: AuditBundleExport,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    path = storage_service.resolve_existing_path(row.storage_path)
    if path is not None:
        bundle = json.loads(path.read_text())
    else:
        bundle = row.bundle_payload_json or {}
    integrity = _verify_bundle(row, bundle, storage_service)
    return AuditBundleExportResponse(
        **_to_summary(row).model_dump(),
        bundle=bundle,
        integrity=integrity,
    )


def _receipt_core(receipt: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(receipt, default=str, sort_keys=True))
    normalized.pop("receipt_sha256", None)
    normalized.pop("signature", None)
    normalized.pop("signature_algorithm", None)
    normalized.pop("signing_key_id", None)
    return normalized


def _receipt_sha256(receipt: dict[str, Any]) -> str:
    return _payload_sha256(_receipt_core(receipt))


def _validation_receipt_matches_bundle(
    receipt: AuditBundleValidationReceipt | None,
    bundle: AuditBundleExport,
) -> bool:
    if receipt is None or receipt.validation_status != "passed":
        return False
    payload = receipt.receipt_payload_json or {}
    audit_bundle = payload.get("audit_bundle") or {}
    return all(
        (
            receipt.audit_bundle_export_id == bundle.id,
            audit_bundle.get("bundle_id") == str(bundle.id),
            audit_bundle.get("payload_sha256") == bundle.payload_sha256,
            audit_bundle.get("bundle_sha256") == bundle.bundle_sha256,
            payload.get("validation_status") == "passed",
        )
    )


def _validate_audit_bundle(
    *,
    row: AuditBundleExport,
    bundle: dict[str, Any],
    storage_service: StorageService,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    bundle_integrity = _verify_bundle(row, bundle, storage_service)
    schema_errors = _validate_bundle_payload_schema(row=row, bundle=bundle)
    source_errors = _validate_bundle_source_integrity(row=row, bundle=bundle)
    prov_jsonld, prov_errors = _validate_prov_graph(bundle)
    payload = bundle.get("payload") or {}
    semantic_governance_errors = (
        _validate_release_semantic_governance_policy(payload)
        if row.bundle_kind == SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND
        else []
    )
    errors = [*schema_errors, *source_errors, *prov_errors, *semantic_governance_errors]
    if not bundle_integrity.get("complete"):
        errors.append(
            _validation_error(
                "bundle_integrity_failed",
                "Stored bundle hash, file, or signature integrity failed.",
                "audit_bundle.integrity",
            )
        )
    checks = {
        "payload_schema_valid": not schema_errors,
        "prov_graph_valid": not prov_errors,
        "bundle_integrity_valid": bool(bundle_integrity.get("complete")),
        "source_integrity_valid": not source_errors,
        "semantic_governance_valid": not semantic_governance_errors,
    }
    checks["complete"] = all(checks.values())
    return checks, prov_jsonld, errors


def _to_validation_receipt_summary(
    row: AuditBundleValidationReceipt,
) -> AuditBundleValidationReceiptSummaryResponse:
    return AuditBundleValidationReceiptSummaryResponse(
        receipt_id=row.id,
        audit_bundle_export_id=row.audit_bundle_export_id,
        bundle_kind=row.bundle_kind,
        source_table=row.source_table,
        source_id=row.source_id,
        validation_profile=row.validation_profile,
        validation_status=row.validation_status,
        payload_schema_valid=row.payload_schema_valid,
        prov_graph_valid=row.prov_graph_valid,
        bundle_integrity_valid=row.bundle_integrity_valid,
        source_integrity_valid=row.source_integrity_valid,
        semantic_governance_valid=row.semantic_governance_valid,
        receipt_sha256=row.receipt_sha256,
        prov_jsonld_sha256=row.prov_jsonld_sha256,
        signature=row.signature,
        signature_algorithm=row.signature_algorithm,
        signing_key_id=row.signing_key_id,
        created_by=row.created_by,
        created_at=row.created_at,
    )


def _verify_validation_receipt(
    row: AuditBundleValidationReceipt,
    *,
    storage_service: StorageService,
) -> dict[str, Any]:
    receipt_path = storage_service.resolve_existing_path(row.receipt_storage_path)
    prov_path = storage_service.resolve_existing_path(row.prov_jsonld_storage_path)
    receipt_payload = (
        json.loads(receipt_path.read_text())
        if receipt_path is not None
        else row.receipt_payload_json
    )
    prov_jsonld = (
        json.loads(prov_path.read_text()) if prov_path is not None else row.prov_jsonld_json
    )
    try:
        signing_key, _key_id = _signing_key()
        signature_valid = hmac.compare_digest(
            row.signature,
            _signature(row.receipt_sha256, signing_key),
        )
        signature_verification_status = "verified" if signature_valid else "mismatch"
    except HTTPException:
        signature_valid = False
        signature_verification_status = "signing_key_missing"
    checks = {
        "receipt_file_exists": receipt_path is not None,
        "prov_jsonld_file_exists": prov_path is not None,
        "receipt_hash_matches_row": _receipt_sha256(receipt_payload) == row.receipt_sha256,
        "receipt_hash_matches_payload": (
            _receipt_sha256(receipt_payload) == receipt_payload.get("receipt_sha256")
        ),
        "prov_jsonld_hash_matches_row": _payload_sha256(prov_jsonld) == row.prov_jsonld_sha256,
        "stored_receipt_matches_file": bool(row.receipt_payload_json == receipt_payload),
        "stored_prov_jsonld_matches_file": bool(row.prov_jsonld_json == prov_jsonld),
        "signature_valid": signature_valid,
    }
    checks["complete"] = all(bool(value) for value in checks.values())
    checks["signature_verification_status"] = signature_verification_status
    return checks


def _to_validation_receipt_response(
    row: AuditBundleValidationReceipt,
    *,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    receipt_path = storage_service.resolve_existing_path(row.receipt_storage_path)
    prov_path = storage_service.resolve_existing_path(row.prov_jsonld_storage_path)
    receipt = (
        json.loads(receipt_path.read_text())
        if receipt_path is not None
        else row.receipt_payload_json
    )
    prov_jsonld = (
        json.loads(prov_path.read_text()) if prov_path is not None else row.prov_jsonld_json
    )
    return AuditBundleValidationReceiptResponse(
        **_to_validation_receipt_summary(row).model_dump(),
        receipt=receipt,
        prov_jsonld=prov_jsonld,
        validation_errors=row.validation_errors_json or [],
        integrity=_verify_validation_receipt(row, storage_service=storage_service),
    )


def _create_audit_bundle_validation_receipt_row(
    session: Session,
    *,
    audit_bundle: AuditBundleExport,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> AuditBundleValidationReceipt:
    bundle_path = storage_service.resolve_existing_path(audit_bundle.storage_path)
    bundle = (
        json.loads(bundle_path.read_text())
        if bundle_path is not None
        else audit_bundle.bundle_payload_json or {}
    )
    validation_checks, prov_jsonld, validation_errors = _validate_audit_bundle(
        row=audit_bundle,
        bundle=bundle,
        storage_service=storage_service,
    )
    receipt_id = uuid.uuid4()
    created_at = utcnow()
    validation_status = "passed" if validation_checks["complete"] else "failed"
    prov_jsonld_sha256 = _payload_sha256(prov_jsonld)
    receipt_core = {
        "schema_name": "audit_bundle_validation_receipt",
        "schema_version": "1.0",
        "receipt_id": str(receipt_id),
        "audit_bundle": {
            "bundle_id": str(audit_bundle.id),
            "bundle_kind": audit_bundle.bundle_kind,
            "source_table": audit_bundle.source_table,
            "source_id": str(audit_bundle.source_id),
            "payload_sha256": audit_bundle.payload_sha256,
            "bundle_sha256": audit_bundle.bundle_sha256,
        },
        "validation_profile": AUDIT_BUNDLE_VALIDATION_PROFILE,
        "validation_status": validation_status,
        "validation_checks": validation_checks,
        "validation_errors": validation_errors,
        "prov_jsonld_sha256": prov_jsonld_sha256,
        "created_at": created_at.isoformat(),
        "created_by": created_by,
        "receipt_policy": (
            "Validation receipt for immutable audit bundles. The receipt links the "
            "signed bundle payload, signed bundle envelope, and standards-facing "
            "PROV JSON-LD export."
        ),
        "hash_chain": [
            {
                "position": 1,
                "name": "audit_bundle_payload",
                "sha256": audit_bundle.payload_sha256,
            },
            {
                "position": 2,
                "name": "audit_bundle_export",
                "sha256": audit_bundle.bundle_sha256,
                "derived_from": ["audit_bundle_payload"],
            },
            {
                "position": 3,
                "name": "prov_jsonld_export",
                "sha256": prov_jsonld_sha256,
                "derived_from": ["audit_bundle_export"],
            },
        ],
    }
    receipt_core["hash_chain_complete"] = all(
        bool(item.get("sha256")) for item in receipt_core["hash_chain"]
    )
    receipt_sha256 = _payload_sha256(receipt_core)
    receipt = {
        **receipt_core,
        "receipt_sha256": receipt_sha256,
        "signature": _signature(receipt_sha256, signing_key),
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signing_key_id": signing_key_id,
    }
    receipt_path = storage_service.get_audit_bundle_validation_receipt_json_path(
        audit_bundle.bundle_kind,
        audit_bundle.id,
        receipt_id,
    )
    prov_jsonld_path = storage_service.get_audit_bundle_validation_prov_jsonld_path(
        audit_bundle.bundle_kind,
        audit_bundle.id,
        receipt_id,
    )
    receipt_path.write_bytes(_canonical_json_bytes(receipt))
    prov_jsonld_path.write_bytes(_canonical_json_bytes(prov_jsonld))
    row = AuditBundleValidationReceipt(
        id=receipt_id,
        audit_bundle_export_id=audit_bundle.id,
        bundle_kind=audit_bundle.bundle_kind,
        source_table=audit_bundle.source_table,
        source_id=audit_bundle.source_id,
        validation_profile=AUDIT_BUNDLE_VALIDATION_PROFILE,
        validation_status=validation_status,
        payload_schema_valid=validation_checks["payload_schema_valid"],
        prov_graph_valid=validation_checks["prov_graph_valid"],
        bundle_integrity_valid=validation_checks["bundle_integrity_valid"],
        source_integrity_valid=validation_checks["source_integrity_valid"],
        semantic_governance_valid=validation_checks["semantic_governance_valid"],
        receipt_storage_path=str(receipt_path),
        prov_jsonld_storage_path=str(prov_jsonld_path),
        receipt_sha256=receipt_sha256,
        prov_jsonld_sha256=prov_jsonld_sha256,
        signature=receipt["signature"],
        signature_algorithm=SIGNATURE_ALGORITHM,
        signing_key_id=signing_key_id,
        validation_errors_json=validation_errors,
        receipt_payload_json=receipt,
        prov_jsonld_json=prov_jsonld,
        created_by=created_by,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    return row


def _ensure_audit_bundle_validation_receipts(
    session: Session,
    *,
    audit_bundles: list[AuditBundleExport],
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> None:
    bundle_ids = [row.id for row in audit_bundles]
    if not bundle_ids:
        return
    existing_receipts = (
        session.execute(
            select(AuditBundleValidationReceipt)
            .where(AuditBundleValidationReceipt.audit_bundle_export_id.in_(bundle_ids))
            .order_by(
                AuditBundleValidationReceipt.audit_bundle_export_id.asc(),
                AuditBundleValidationReceipt.created_at.desc(),
                AuditBundleValidationReceipt.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    receipts_by_bundle_id: dict[UUID, AuditBundleValidationReceipt] = {}
    for receipt in existing_receipts:
        receipts_by_bundle_id.setdefault(receipt.audit_bundle_export_id, receipt)
    for bundle in audit_bundles:
        receipt = receipts_by_bundle_id.get(bundle.id)
        if _validation_receipt_matches_bundle(receipt, bundle):
            continue
        _create_audit_bundle_validation_receipt_row(
            session,
            audit_bundle=bundle,
            created_by=created_by,
            storage_service=storage_service,
            signing_key=signing_key,
            signing_key_id=signing_key_id,
        )


def _create_retrieval_training_run_audit_bundle_row(
    session: Session,
    *,
    training_run: RetrievalTrainingRun,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> AuditBundleExport:
    if training_run.status != "completed":
        raise _training_run_not_completed(training_run)
    bundle_id = uuid.uuid4()
    created_at = utcnow()
    audit_payload = _build_retrieval_training_run_payload(
        session,
        training_run=training_run,
        bundle_id=bundle_id,
        created_by=created_by,
        created_at=created_at,
    )
    bundle = _signed_bundle(
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
    bundle_path.write_bytes(_canonical_json_bytes(bundle))
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


def _ensure_retrieval_training_run_audit_bundles_for_release(
    session: Session,
    *,
    release: SearchHarnessRelease,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
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
        if _training_audit_bundle_current_for_training_run(
            session,
            existing_bundle,
            training_run,
        ):
            if existing_bundle is not None:
                ensured_bundles.append(existing_bundle)
            continue
        ensured_bundles.append(
            _create_retrieval_training_run_audit_bundle_row(
                session,
                training_run=training_run,
                created_by=created_by,
                storage_service=storage_service,
                signing_key=signing_key,
                signing_key_id=signing_key_id,
            )
        )
    return ensured_bundles


def create_search_harness_release_audit_bundle(
    session: Session,
    release_id: UUID,
    payload: SearchHarnessReleaseAuditBundleRequest,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    release = session.get(SearchHarnessRelease, release_id)
    if release is None:
        raise _release_not_found(release_id)
    signing_key, signing_key_id = _signing_key()
    linked_training_bundles = _ensure_retrieval_training_run_audit_bundles_for_release(
        session,
        release=release,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    _ensure_audit_bundle_validation_receipts(
        session,
        audit_bundles=linked_training_bundles,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    bundle_id = uuid.uuid4()
    created_at = utcnow()
    audit_payload = _build_search_harness_release_payload(
        session,
        release=release,
        bundle_id=bundle_id,
        created_by=payload.created_by,
        created_at=created_at,
    )
    bundle = _signed_bundle(
        bundle_id=bundle_id,
        bundle_kind=SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        source_table=SEARCH_HARNESS_RELEASE_SOURCE_TABLE,
        source_id=release.id,
        payload=audit_payload,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    bundle_path = storage_service.get_audit_bundle_json_path(
        SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        bundle_id,
    )
    bundle_path.write_bytes(_canonical_json_bytes(bundle))
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
        bundle_kind=SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        source_table=SEARCH_HARNESS_RELEASE_SOURCE_TABLE,
        source_id=release.id,
        search_harness_release_id=release.id,
        storage_path=str(bundle_path),
        payload_sha256=bundle["bundle_export"]["payload_sha256"],
        bundle_sha256=bundle["bundle_export"]["bundle_sha256"],
        signature=bundle["bundle_export"]["signature"],
        signature_algorithm=bundle["bundle_export"]["signature_algorithm"],
        signing_key_id=bundle["bundle_export"]["signing_key_id"],
        bundle_payload_json=bundle,
        integrity_json=integrity,
        created_by=payload.created_by,
        export_status="completed",
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    _ensure_audit_bundle_validation_receipts(
        session,
        audit_bundles=[row],
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    return _to_response(row, storage_service=storage_service)


def create_retrieval_training_run_audit_bundle(
    session: Session,
    training_run_id: UUID,
    payload: RetrievalTrainingRunAuditBundleRequest,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    training_run = session.get(RetrievalTrainingRun, training_run_id)
    if training_run is None:
        raise _training_run_not_found(training_run_id)
    signing_key, signing_key_id = _signing_key()
    row = _create_retrieval_training_run_audit_bundle_row(
        session,
        training_run=training_run,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    return _to_response(row, storage_service=storage_service)


def get_audit_bundle_export(
    session: Session,
    bundle_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.get(AuditBundleExport, bundle_id)
    if row is None:
        raise _audit_bundle_not_found(bundle_id)
    return _to_response(row, storage_service=storage_service)


def _get_audit_bundle_row(session: Session, bundle_id: UUID) -> AuditBundleExport:
    row = session.get(AuditBundleExport, bundle_id)
    if row is None:
        raise _audit_bundle_not_found(bundle_id)
    return row


def create_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    payload: AuditBundleValidationReceiptRequest,
    *,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    audit_bundle = _get_audit_bundle_row(session, bundle_id)
    signing_key, signing_key_id = _signing_key()
    row = _create_audit_bundle_validation_receipt_row(
        session,
        audit_bundle=audit_bundle,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    return _to_validation_receipt_response(row, storage_service=storage_service)


def list_audit_bundle_validation_receipts(
    session: Session,
    bundle_id: UUID,
) -> list[AuditBundleValidationReceiptSummaryResponse]:
    _get_audit_bundle_row(session, bundle_id)
    rows = (
        session.execute(
            select(AuditBundleValidationReceipt)
            .where(AuditBundleValidationReceipt.audit_bundle_export_id == bundle_id)
            .order_by(
                AuditBundleValidationReceipt.created_at.desc(),
                AuditBundleValidationReceipt.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    return [_to_validation_receipt_summary(row) for row in rows]


def get_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    receipt_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    _get_audit_bundle_row(session, bundle_id)
    row = session.scalar(
        select(AuditBundleValidationReceipt).where(
            AuditBundleValidationReceipt.audit_bundle_export_id == bundle_id,
            AuditBundleValidationReceipt.id == receipt_id,
        )
    )
    if row is None:
        raise _audit_bundle_validation_receipt_not_found(bundle_id, receipt_id)
    return _to_validation_receipt_response(row, storage_service=storage_service)


def get_latest_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    _get_audit_bundle_row(session, bundle_id)
    row = session.scalar(
        select(AuditBundleValidationReceipt)
        .where(AuditBundleValidationReceipt.audit_bundle_export_id == bundle_id)
        .order_by(
            AuditBundleValidationReceipt.created_at.desc(),
            AuditBundleValidationReceipt.id.asc(),
        )
    )
    if row is None:
        raise _audit_bundle_validation_receipt_not_found(bundle_id)
    return _to_validation_receipt_response(row, storage_service=storage_service)


def get_latest_retrieval_training_run_audit_bundle(
    session: Session,
    training_run_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.retrieval_training_run_id == training_run_id,
            AuditBundleExport.bundle_kind == RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
        )
        .order_by(AuditBundleExport.created_at.desc())
    )
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "retrieval_training_run_audit_bundle_not_found",
            "Retrieval training run audit bundle not found.",
            retrieval_training_run_id=str(training_run_id),
        )
    return _to_response(row, storage_service=storage_service)


def get_latest_search_harness_release_audit_bundle(
    session: Session,
    release_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.search_harness_release_id == release_id,
            AuditBundleExport.bundle_kind == SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        )
        .order_by(AuditBundleExport.created_at.desc())
    )
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_release_audit_bundle_not_found",
            "Search harness release audit bundle not found.",
            release_id=str(release_id),
        )
    return _to_response(row, storage_service=storage_service)
