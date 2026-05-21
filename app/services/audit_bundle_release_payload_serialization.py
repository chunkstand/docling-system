from __future__ import annotations

from typing import Any

from app.core.hashes import payload_sha256 as _payload_sha256
from app.db.public.audit_and_evidence import AuditBundleExport, AuditBundleValidationReceipt
from app.db.public.retrieval import (
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchReplayRun,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.semantic_governance import (
    semantic_governance_event_payload as _semantic_governance_event_payload,
)

SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND = "search_harness_release_provenance"
SEARCH_HARNESS_RELEASE_SOURCE_TABLE = "search_harness_releases"


def release_payload(row: SearchHarnessRelease) -> dict[str, Any]:
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


def evaluation_payload(row: SearchHarnessEvaluation | None) -> dict[str, Any] | None:
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


def source_payload(row: SearchHarnessEvaluationSource) -> dict[str, Any]:
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


def replay_payload(row: SearchReplayRun) -> dict[str, Any]:
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


def retrieval_learning_candidate_payload(
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


def retrieval_reranker_artifact_payload(row: RetrievalRerankerArtifact) -> dict[str, Any]:
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


def audit_bundle_reference_payload(row: AuditBundleExport) -> dict[str, Any]:
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


def validation_receipt_reference_payload(
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


def semantic_governance_event_payload(row: SemanticGovernanceEvent) -> dict[str, Any]:
    return _semantic_governance_event_payload(row)
