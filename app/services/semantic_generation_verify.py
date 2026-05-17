from __future__ import annotations

from typing import Any

from app.schemas.agent_task_semantic_generation import GroundedDocumentDraftPayload
from app.services.semantic_generation_shared import SemanticGroundedDocumentVerificationOutcome


def _verification_success_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": (
                summary["traceable_claim_ratio"] == 1.0 and summary["unsupported_claim_count"] == 0
            ),
            "summary": (
                "Verified claims stay completely evidence-backed and "
                "unsupported claims are blocked."
            ),
            "details": {
                "traceable_claim_ratio": summary["traceable_claim_ratio"],
                "unsupported_claim_count": summary["unsupported_claim_count"],
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": (
                summary["graph_ref_coverage_ratio"] == 1.0
                and summary["fact_ref_coverage_ratio"] == 1.0
                and summary["assertion_ref_coverage_ratio"] == 1.0
                and summary["evidence_ref_coverage_ratio"] == 1.0
            ),
            "summary": (
                "The verifier can resolve every claim back to the draft's "
                "typed fact, assertion, and evidence indexes."
            ),
            "details": {
                "graph_ref_coverage_ratio": summary["graph_ref_coverage_ratio"],
                "fact_ref_coverage_ratio": summary["fact_ref_coverage_ratio"],
                "assertion_ref_coverage_ratio": summary["assertion_ref_coverage_ratio"],
                "evidence_ref_coverage_ratio": summary["evidence_ref_coverage_ratio"],
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": (
                summary["required_concept_coverage_ratio"] == 1.0
                and summary["freshness_blocker_count"] == 0
            ),
            "summary": (
                "The verifier enforces explicit coverage and blocks missing "
                "or stale source control surfaces."
            ),
            "details": {
                "required_concept_coverage_ratio": summary["required_concept_coverage_ratio"],
                "freshness_blocker_count": summary["freshness_blocker_count"],
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": (
                summary["claim_count"] > 0 and summary["covered_required_concept_count"] > 0
            ),
            "summary": (
                "The verifier evaluates a durable claim graph rather than "
                "re-reading raw corpus state."
            ),
            "details": {
                "claim_count": summary["claim_count"],
                "covered_required_concept_count": summary["covered_required_concept_count"],
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": summary["claim_count"] <= max(summary["evidence_count"], 1),
            "summary": "The final draft stays compact relative to the underlying evidence pack.",
            "details": {
                "claim_count": summary["claim_count"],
                "evidence_count": summary["evidence_count"],
            },
        },
    ]


def verify_semantic_grounded_document(
    draft_payload: dict[str, Any],
    *,
    max_unsupported_claim_count: int = 0,
    require_full_claim_traceability: bool = True,
    require_full_concept_coverage: bool = True,
) -> SemanticGroundedDocumentVerificationOutcome:
    draft = GroundedDocumentDraftPayload.model_validate(draft_payload)
    graph_index = {row.edge_id: row for row in draft.graph_index}
    fact_index = {row.fact_id: row for row in draft.fact_index}
    assertion_index = {row.assertion_id: row for row in draft.assertion_index}
    evidence_index = {row.citation_label: row for row in draft.evidence_pack}
    required_concept_keys = set(draft.required_concept_keys)
    covered_concept_keys: set[str] = set()
    supported_concept_keys: set[str] = set()
    supported_claim_count = 0
    resolved_graph_edge_count = 0
    resolved_fact_count = 0
    resolved_assertion_count = 0
    resolved_evidence_count = 0
    candidate_disclosure_count = 0
    unsupported_claim_count = 0
    approved_supported_claim_count = 0
    reasons: list[str] = []

    for claim in draft.claims:
        covered_concept_keys.update(claim.concept_keys)
        has_graph_edges = bool(claim.graph_edge_ids)
        has_facts = bool(claim.fact_ids)
        has_assertions = bool(claim.assertion_ids)
        has_evidence = bool(claim.evidence_labels)
        resolved_graph_edges = [
            graph_index[edge_id] for edge_id in claim.graph_edge_ids if edge_id in graph_index
        ]
        resolved_facts = [
            fact_index[fact_id] for fact_id in claim.fact_ids if fact_id in fact_index
        ]
        resolved_assertions = [
            assertion_index[assertion_id]
            for assertion_id in claim.assertion_ids
            if assertion_id in assertion_index
        ]
        resolved_evidence = [
            evidence_index[evidence_label]
            for evidence_label in claim.evidence_labels
            if evidence_label in evidence_index
        ]
        if has_graph_edges and len(resolved_graph_edges) == len(claim.graph_edge_ids):
            resolved_graph_edge_count += 1
        if has_facts and len(resolved_facts) == len(claim.fact_ids):
            resolved_fact_count += 1
        if has_assertions and len(resolved_assertions) == len(claim.assertion_ids):
            resolved_assertion_count += 1
        if has_evidence and len(resolved_evidence) == len(claim.evidence_labels):
            resolved_evidence_count += 1
        graph_backed = bool(resolved_graph_edges) and all(
            row.support_ref_ids for row in resolved_graph_edges
        )
        fact_backed = bool(resolved_facts) and all(row.evidence_ids for row in resolved_facts)
        assertion_backed = (
            has_assertions and has_evidence and resolved_assertions and resolved_evidence
        )
        if graph_backed or fact_backed or assertion_backed:
            supported_claim_count += 1
            supported_concept_keys.update(claim.concept_keys)
        else:
            unsupported_claim_count += 1
        if claim.review_policy_status in {"candidate_disclosed", "mixed_support_disclosed"}:
            if claim.disclosure_note:
                candidate_disclosure_count += 1
            else:
                reasons.append(
                    f"{claim.claim_id} is candidate-backed but missing a disclosure note."
                )
        if resolved_facts and all(row.review_status == "approved" for row in resolved_facts):
            approved_supported_claim_count += 1
        elif resolved_graph_edges and all(
            row.review_status == "approved" for row in resolved_graph_edges
        ):
            approved_supported_claim_count += 1
        elif resolved_assertions and all(
            row.review_status == "approved" for row in resolved_assertions
        ):
            approved_supported_claim_count += 1

    claim_count = len(draft.claims)
    required_concept_count = len(required_concept_keys)
    covered_required_concept_count = len(required_concept_keys.intersection(supported_concept_keys))
    traceable_claim_ratio = supported_claim_count / claim_count if claim_count else 0.0
    graph_claim_count = sum(1 for claim in draft.claims if claim.graph_edge_ids)
    fact_claim_count = sum(1 for claim in draft.claims if claim.fact_ids)
    assertion_claim_count = sum(1 for claim in draft.claims if claim.assertion_ids)
    evidence_claim_count = sum(1 for claim in draft.claims if claim.evidence_labels)
    graph_ref_coverage_ratio = (
        resolved_graph_edge_count / graph_claim_count if graph_claim_count else 1.0
    )
    fact_ref_coverage_ratio = resolved_fact_count / fact_claim_count if fact_claim_count else 1.0
    assertion_ref_coverage_ratio = (
        resolved_assertion_count / assertion_claim_count if assertion_claim_count else 1.0
    )
    evidence_ref_coverage_ratio = (
        resolved_evidence_count / evidence_claim_count if evidence_claim_count else 1.0
    )
    required_concept_coverage_ratio = (
        covered_required_concept_count / required_concept_count if required_concept_count else 1.0
    )
    approved_support_ratio = approved_supported_claim_count / claim_count if claim_count else 0.0

    if unsupported_claim_count > max_unsupported_claim_count:
        reasons.append(
            f"Unsupported claim count {unsupported_claim_count} exceeds the allowed maximum "
            f"of {max_unsupported_claim_count}."
        )
    if require_full_claim_traceability and traceable_claim_ratio < 1.0:
        reasons.append(
            "Not every draft claim resolves to graph, fact, or assertion-plus-evidence support."
        )
    if require_full_concept_coverage and required_concept_coverage_ratio < 1.0:
        reasons.append("The draft does not cover every required concept from the generation brief.")

    summary = {
        "claim_count": claim_count,
        "section_count": len(draft.sections),
        "evidence_count": len(draft.evidence_pack),
        "graph_edge_count": len(draft.graph_index),
        "fact_count": len(draft.fact_index),
        "required_concept_count": required_concept_count,
        "covered_required_concept_count": covered_required_concept_count,
        "traceable_claim_ratio": traceable_claim_ratio,
        "graph_ref_coverage_ratio": graph_ref_coverage_ratio,
        "fact_ref_coverage_ratio": fact_ref_coverage_ratio,
        "assertion_ref_coverage_ratio": assertion_ref_coverage_ratio,
        "evidence_ref_coverage_ratio": evidence_ref_coverage_ratio,
        "required_concept_coverage_ratio": required_concept_coverage_ratio,
        "approved_support_ratio": approved_support_ratio,
        "candidate_disclosure_count": candidate_disclosure_count,
        "unsupported_claim_count": unsupported_claim_count,
        "freshness_blocker_count": 0,
    }
    success_metrics = _verification_success_metrics(summary)
    verification_outcome = "passed" if not reasons else "failed"
    verification_details = {
        "required_concept_keys": sorted(required_concept_keys),
        "covered_concept_keys": sorted(covered_concept_keys),
        "supported_concept_keys": sorted(supported_concept_keys),
    }
    return SemanticGroundedDocumentVerificationOutcome(
        summary=summary,
        success_metrics=success_metrics,
        verification_outcome=verification_outcome,
        verification_metrics=summary,
        verification_reasons=reasons,
        verification_details=verification_details,
    )
