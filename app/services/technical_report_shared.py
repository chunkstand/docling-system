from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.agent_task_reports import TechnicalReportEvidenceCard


@dataclass(frozen=True)
class TechnicalReportVerificationOutcome:
    summary: dict[str, Any]
    success_metrics: list[dict[str, Any]]
    verification_outcome: str
    verification_metrics: dict[str, Any]
    verification_reasons: list[str]
    verification_details: dict[str, Any]


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


def claim_provenance_lock_contract_mismatches(claim) -> list[str]:
    lock = dict(claim.provenance_lock or {})
    if not lock:
        return ["provenance_lock"]
    mismatches: list[str] = []
    if lock.get("schema_name") != "technical_report_claim_provenance_lock":
        mismatches.append("schema_name")
    if lock.get("schema_version") != "1.0":
        mismatches.append("schema_version")
    if str(lock.get("claim_id") or "") != claim.claim_id:
        mismatches.append("claim_id")
    for field_name in _CLAIM_PROVENANCE_LOCK_LIST_FIELDS:
        claim_values = [str(value) for value in getattr(claim, field_name)]
        lock_values = [str(value) for value in lock.get(field_name) or []]
        if lock_values != claim_values:
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
        if coverage.get(coverage_key) != len(lock.get(field_name) or []):
            mismatches.append(f"coverage.{coverage_key}")
    return mismatches


def card_requires_source_match(card: TechnicalReportEvidenceCard) -> bool:
    source_type = str(card.source_type or "").strip().lower()
    evidence_kind = str(card.evidence_kind or "").strip().lower()
    return (
        source_type in {"chunk", "table", "figure"}
        or evidence_kind in {"source_evidence", "semantic_fact"}
        or bool(card.evidence_ids)
    )


def expert_alignment() -> list[dict[str, str]]:
    return [
        {
            "expert": "Jon Bratseth",
            "principle": (
                "Retrieval architecture should expose candidate generation, ranking, "
                "and serving contracts as production artifacts."
            ),
        },
        {
            "expert": "Omar Khattab",
            "principle": (
                "High-accuracy RAG requires explicit evidence binding, retriever "
                "evaluation, and reranker-replaceable interfaces."
            ),
        },
        {
            "expert": "Juan Sequeda",
            "principle": (
                "Semantic access should keep ontology and governed fact context "
                "visible to the data layer."
            ),
        },
        {
            "expert": "Luc Moreau / James Cheney",
            "principle": (
                "Generated claims need replayable provenance, immutable evidence refs, "
                "and auditable trace structure."
            ),
        },
        {
            "expert": "Joshua Yu + Nicolas Figay",
            "principle": (
                "Graph memory is a governed semantic control plane, not a source-of-truth shortcut."
            ),
        },
        {
            "expert": "Rich Sutton",
            "principle": (
                "Accuracy work should improve scalable data, compute, evaluation, "
                "and learning loops over fixed hand-coded rules."
            ),
        },
        {
            "expert": "Jerry Liu",
            "principle": (
                "Document-generation agents should consume a reusable, observable "
                "context pack rather than hidden prompt-only state."
            ),
        },
    ]


def success_metric(
    metric_key: str,
    stakeholder: str,
    passed: bool,
    summary: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "metric_key": metric_key,
        "stakeholder": stakeholder,
        "passed": passed,
        "summary": summary,
        "details": details or {},
    }
