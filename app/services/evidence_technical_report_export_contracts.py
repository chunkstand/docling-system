from __future__ import annotations

from app.db.models import ClaimEvidenceDerivation
from app.services.evidence_common import string_values as _string_values

_CLAIM_PROVENANCE_LOCK_LIST_FIELDS = (
    "source_search_request_ids",
    "source_search_request_result_ids",
    "source_evidence_package_export_ids",
    "source_evidence_package_sha256s",
    "source_evidence_trace_sha256s",
    "semantic_ontology_snapshot_ids",
    "semantic_graph_snapshot_ids",
    "retrieval_reranker_artifact_ids",
    "search_harness_release_ids",
    "release_audit_bundle_ids",
    "release_validation_receipt_ids",
)


def _claim_derivation_provenance_lock_contract_mismatches(
    row: ClaimEvidenceDerivation,
) -> list[str]:
    lock = dict(row.provenance_lock_json or {})
    if not lock:
        return ["provenance_lock"]
    mismatches: list[str] = []
    if lock.get("schema_name") != "technical_report_claim_provenance_lock":
        mismatches.append("schema_name")
    if lock.get("schema_version") != "1.0":
        mismatches.append("schema_version")
    if str(lock.get("claim_id") or "") != str(row.claim_id):
        mismatches.append("claim_id")
    row_values = {
        "source_search_request_ids": row.source_search_request_ids_json or [],
        "source_search_request_result_ids": row.source_search_request_result_ids_json or [],
        "source_evidence_package_export_ids": (row.source_evidence_package_export_ids_json or []),
        "source_evidence_package_sha256s": row.source_evidence_package_sha256s_json or [],
        "source_evidence_trace_sha256s": row.source_evidence_trace_sha256s_json or [],
        "semantic_ontology_snapshot_ids": row.semantic_ontology_snapshot_ids_json or [],
        "semantic_graph_snapshot_ids": row.semantic_graph_snapshot_ids_json or [],
        "retrieval_reranker_artifact_ids": row.retrieval_reranker_artifact_ids_json or [],
        "search_harness_release_ids": row.search_harness_release_ids_json or [],
        "release_audit_bundle_ids": row.release_audit_bundle_ids_json or [],
        "release_validation_receipt_ids": row.release_validation_receipt_ids_json or [],
    }
    for field_name in _CLAIM_PROVENANCE_LOCK_LIST_FIELDS:
        if _string_values(lock.get(field_name) or []) != _string_values(row_values[field_name]):
            mismatches.append(field_name)
    coverage = dict(lock.get("coverage") or {})
    coverage_fields = {
        "source_search_request_count": "source_search_request_ids",
        "source_search_request_result_count": "source_search_request_result_ids",
        "source_evidence_package_export_count": "source_evidence_package_export_ids",
        "semantic_ontology_snapshot_count": "semantic_ontology_snapshot_ids",
        "semantic_graph_snapshot_count": "semantic_graph_snapshot_ids",
        "retrieval_reranker_artifact_count": "retrieval_reranker_artifact_ids",
        "search_harness_release_count": "search_harness_release_ids",
        "release_audit_bundle_count": "release_audit_bundle_ids",
        "release_validation_receipt_count": "release_validation_receipt_ids",
    }
    for coverage_key, field_name in coverage_fields.items():
        if coverage.get(coverage_key) != len(_string_values(lock.get(field_name) or [])):
            mismatches.append(f"coverage.{coverage_key}")
    return mismatches


def _claim_derivation_support_judgment_contract_mismatches(
    row: ClaimEvidenceDerivation,
) -> list[str]:
    judgment = dict(row.support_judgment_json or {})
    if not judgment:
        return ["support_judgment"]
    mismatches: list[str] = []
    if judgment.get("schema_name") != "technical_report_claim_support_judgment":
        mismatches.append("schema_name")
    if judgment.get("schema_version") != "1.0":
        mismatches.append("schema_version")
    if judgment.get("judge_kind") != "deterministic_claim_support_v1":
        mismatches.append("judge_kind")
    if str(judgment.get("claim_id") or "") != str(row.claim_id):
        mismatches.append("claim_id")
    if judgment.get("verdict") != row.support_verdict:
        mismatches.append("verdict")
    try:
        judgment_score = float(judgment.get("support_score"))
    except (TypeError, ValueError):
        mismatches.append("support_score")
    else:
        if row.support_score is None or abs(judgment_score - row.support_score) > 0.0001:
            mismatches.append("support_score")
    if _string_values(judgment.get("source_search_request_result_ids") or []) != (
        row.source_search_request_result_ids_json or []
    ):
        mismatches.append("source_search_request_result_ids")
    if sorted(_string_values(judgment.get("evidence_card_ids") or [])) != sorted(
        row.evidence_card_ids_json or []
    ):
        mismatches.append("evidence_card_ids")
    if sorted(_string_values(judgment.get("graph_edge_ids") or [])) != sorted(
        row.graph_edge_ids_json or []
    ):
        mismatches.append("graph_edge_ids")
    return mismatches


claim_derivation_provenance_lock_contract_mismatches = (
    _claim_derivation_provenance_lock_contract_mismatches
)
claim_derivation_support_judgment_contract_mismatches = (
    _claim_derivation_support_judgment_contract_mismatches
)
