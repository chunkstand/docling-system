from __future__ import annotations

from typing import Any

from app.core.hashes import payload_sha256 as _payload_sha256
from app.schemas.agent_task_core import ContextFreshnessStatus
from app.schemas.agent_task_reports import TechnicalReportDraftPayload
from app.services.evidence_technical_report_exports import build_technical_report_derivation_package
from app.services.technical_report_claim_support import (
    CLAIM_SUPPORT_VERDICTS,
    claim_support_judgment_contract_mismatches,
)
from app.services.technical_report_shared import (
    TechnicalReportVerificationOutcome,
    claim_provenance_lock_contract_mismatches,
    success_metric,
)


def _technical_report_verification_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        success_metric(
            "claim_traceability",
            "Luc Moreau / James Cheney",
            summary["traceable_claim_ratio"] == 1.0
            and summary["unresolved_evidence_card_ref_count"] == 0
            and summary["unresolved_graph_edge_ref_count"] == 0,
            "Every rendered claim resolves to evidence cards and approved graph context.",
            {
                "traceable_claim_ratio": summary["traceable_claim_ratio"],
                "unresolved_evidence_card_ref_count": summary["unresolved_evidence_card_ref_count"],
                "unresolved_graph_edge_ref_count": summary["unresolved_graph_edge_ref_count"],
            },
        ),
        success_metric(
            "explicit_context_gate",
            "Jerry Liu",
            summary["context_blocker_count"] == 0 and summary["missing_wake_context_count"] == 0,
            "Missing and schema-mismatched wake-up context is blocked by the verifier.",
            {
                "context_blocker_count": summary["context_blocker_count"],
                "missing_wake_context_count": summary["missing_wake_context_count"],
            },
        ),
        success_metric(
            "graph_memory_governed",
            "Joshua Yu + Nicolas Figay",
            summary["unapproved_graph_claim_count"] == 0,
            "Graph-backed claims use approved graph edges only.",
            {"graph_claim_count": summary["graph_claim_count"]},
        ),
        success_metric(
            "owned_wake_context",
            "Jerry Liu",
            summary["context_ref_count"] > 0 and summary["missing_wake_context_count"] == 0,
            "The draft is verified against the harness wake-up context.",
            {
                "context_ref_count": summary["context_ref_count"],
                "missing_wake_context_count": summary["missing_wake_context_count"],
            },
        ),
        success_metric(
            "durable_platform_loop",
            "Rich Sutton",
            summary["claim_count"] > 0 and summary["evidence_card_count"] > 0,
            "The report loop produces reusable durable artifacts rather than one-off prose.",
            {
                "claim_count": summary["claim_count"],
                "evidence_card_count": summary["evidence_card_count"],
            },
        ),
        success_metric(
            "frozen_evidence_package",
            "Luc Moreau / James Cheney",
            summary["claims_with_derivation_hash_count"] == summary["claim_count"]
            and summary["claims_with_evidence_package_hash_count"] == summary["claim_count"]
            and summary["draft_evidence_package_hash_present"]
            and summary["evidence_package_integrity_mismatch_count"] == 0
            and summary["derivation_integrity_mismatch_count"] == 0,
            (
                "Every claim is tied to a frozen evidence package and the frozen hashes "
                "match recomputation."
            ),
            {
                "claims_with_derivation_hash_count": summary["claims_with_derivation_hash_count"],
                "claims_with_evidence_package_hash_count": summary[
                    "claims_with_evidence_package_hash_count"
                ],
                "draft_evidence_package_hash_present": summary[
                    "draft_evidence_package_hash_present"
                ],
                "evidence_package_integrity_mismatch_count": summary[
                    "evidence_package_integrity_mismatch_count"
                ],
                "derivation_integrity_mismatch_count": summary[
                    "derivation_integrity_mismatch_count"
                ],
            },
        ),
        success_metric(
            "court_grade_claim_provenance_lock",
            "Luc Moreau / James Cheney",
            summary["claims_with_provenance_lock_count"] == summary["claim_count"]
            and summary["missing_provenance_lock_count"] == 0
            and summary["provenance_lock_integrity_mismatch_count"] == 0
            and summary["provenance_lock_contract_mismatch_count"] == 0
            and summary["claims_missing_source_search_request_result_count"] == 0,
            (
                "Every generated claim carries a recomputable provenance lock down to "
                "search result identifiers."
            ),
            {
                "claims_with_provenance_lock_count": summary["claims_with_provenance_lock_count"],
                "missing_provenance_lock_count": summary["missing_provenance_lock_count"],
                "provenance_lock_integrity_mismatch_count": summary[
                    "provenance_lock_integrity_mismatch_count"
                ],
                "provenance_lock_contract_mismatch_count": summary[
                    "provenance_lock_contract_mismatch_count"
                ],
                "claims_missing_source_search_request_result_count": summary[
                    "claims_missing_source_search_request_result_count"
                ],
            },
        ),
        success_metric(
            "court_grade_claim_support_gate",
            "Omar Khattab",
            summary["claims_with_support_judgment_count"] == summary["claim_count"]
            and summary["missing_support_judgment_count"] == 0
            and summary["support_judgment_integrity_mismatch_count"] == 0
            and summary["support_judgment_contract_mismatch_count"] == 0
            and summary["unsupported_support_judgment_count"] == 0
            and summary["claim_support_score_below_threshold_count"] == 0,
            (
                "Every generated claim carries an auditable support judgment that "
                "passes the groundedness threshold."
            ),
            {
                "claims_with_support_judgment_count": summary["claims_with_support_judgment_count"],
                "missing_support_judgment_count": summary["missing_support_judgment_count"],
                "support_judgment_integrity_mismatch_count": summary[
                    "support_judgment_integrity_mismatch_count"
                ],
                "support_judgment_contract_mismatch_count": summary[
                    "support_judgment_contract_mismatch_count"
                ],
                "unsupported_support_judgment_count": summary["unsupported_support_judgment_count"],
                "claim_support_score_below_threshold_count": summary[
                    "claim_support_score_below_threshold_count"
                ],
            },
        ),
    ]


def verify_technical_report(
    draft_payload: dict[str, Any],
    *,
    max_unsupported_claim_count: int = 0,
    require_full_claim_traceability: bool = True,
    require_full_concept_coverage: bool = True,
    require_graph_edges_approved: bool = True,
    block_stale_context: bool = False,
    require_claim_support_judgments: bool = True,
    min_claim_support_score: float = 0.34,
) -> TechnicalReportVerificationOutcome:
    draft = TechnicalReportDraftPayload.model_validate(draft_payload)
    recomputed_derivation_package = build_technical_report_derivation_package(
        draft.model_dump(mode="json")
    )
    expected_package_sha256 = str(recomputed_derivation_package.get("package_sha256") or "")
    expected_derivations_by_claim_id = {
        str(row.get("claim_id")): row
        for row in recomputed_derivation_package.get("claim_derivations", [])
        if row.get("claim_id")
    }
    card_ids = {card.evidence_card_id for card in draft.evidence_cards}
    graph_edges = {edge.edge_id: edge for edge in draft.graph_context}
    required_concept_keys = set(draft.required_concept_keys)
    supported_concept_keys: set[str] = set()
    resolved_claim_count = 0
    unsupported_claim_count = len(draft.blocked_claims)
    unapproved_graph_claim_count = 0
    unresolved_evidence_card_ref_count = 0
    unresolved_graph_edge_ref_count = 0
    missing_evidence_package_hash_count = 0
    missing_derivation_hash_count = 0
    missing_provenance_lock_count = 0
    provenance_lock_integrity_mismatch_count = 0
    provenance_lock_contract_mismatch_count = 0
    claims_missing_source_search_request_result_count = 0
    missing_support_judgment_count = 0
    support_judgment_integrity_mismatch_count = 0
    support_judgment_contract_mismatch_count = 0
    unsupported_support_judgment_count = 0
    claim_support_score_below_threshold_count = 0
    evidence_package_mismatch_count = 0
    evidence_package_integrity_mismatch_count = 0
    derivation_integrity_mismatch_count = 0
    reasons: list[str] = []
    stale_context_count = 0
    context_blocker_count = 0
    context_refs = []
    if draft.llm_adapter_contract.get("harness_context_refs"):
        context_refs = list(draft.llm_adapter_contract["harness_context_refs"])
    missing_wake_context_count = 0 if context_refs else 1

    for ref in context_refs:
        status = str(ref.get("freshness_status") or "")
        if status in {
            ContextFreshnessStatus.MISSING.value,
            ContextFreshnessStatus.SCHEMA_MISMATCH.value,
        }:
            context_blocker_count += 1
        elif status == ContextFreshnessStatus.STALE.value:
            stale_context_count += 1

    if not draft.evidence_package_sha256:
        reasons.append("The report draft is missing a frozen evidence package hash.")
    elif draft.evidence_package_sha256 != expected_package_sha256:
        evidence_package_integrity_mismatch_count += 1
        reasons.append(
            "Draft evidence package hash does not match recomputed derivation package hash."
        )

    for claim in draft.claims:
        if not claim.evidence_package_sha256:
            missing_evidence_package_hash_count += 1
            reasons.append(f"{claim.claim_id} is missing a frozen evidence package hash.")
        elif (
            draft.evidence_package_sha256
            and claim.evidence_package_sha256 != draft.evidence_package_sha256
        ):
            evidence_package_mismatch_count += 1
            reasons.append(
                f"{claim.claim_id} evidence package hash does not match the draft package hash."
            )
        if (
            claim.evidence_package_sha256
            and claim.evidence_package_sha256 != expected_package_sha256
        ):
            evidence_package_integrity_mismatch_count += 1
            reasons.append(
                f"{claim.claim_id} evidence package hash does not match recomputed package hash."
            )
        if not claim.derivation_sha256:
            missing_derivation_hash_count += 1
            reasons.append(f"{claim.claim_id} is missing a derivation hash.")
        else:
            expected_derivation = expected_derivations_by_claim_id.get(claim.claim_id)
            expected_derivation_sha256 = (
                str(expected_derivation.get("derivation_sha256") or "")
                if expected_derivation is not None
                else ""
            )
            if claim.derivation_sha256 != expected_derivation_sha256:
                derivation_integrity_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} derivation hash does not match recomputed claim derivation."
                )
        expected_derivation = expected_derivations_by_claim_id.get(claim.claim_id)
        expected_provenance_lock_sha256 = (
            str(expected_derivation.get("provenance_lock_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if not claim.provenance_lock or not claim.provenance_lock_sha256:
            missing_provenance_lock_count += 1
            reasons.append(f"{claim.claim_id} is missing a provenance lock.")
        elif (
            claim.provenance_lock_sha256 != _payload_sha256(claim.provenance_lock)
            or claim.provenance_lock_sha256 != expected_provenance_lock_sha256
        ):
            provenance_lock_integrity_mismatch_count += 1
            reasons.append(f"{claim.claim_id} provenance lock hash does not match recomputation.")
        lock_contract_mismatches = claim_provenance_lock_contract_mismatches(claim)
        if lock_contract_mismatches:
            provenance_lock_contract_mismatch_count += 1
            reasons.append(
                f"{claim.claim_id} provenance lock does not match claim fields: "
                f"{', '.join(lock_contract_mismatches)}."
            )
        if (
            not claim.support_verdict
            or claim.support_score is None
            or not claim.support_judge_run_id
            or not claim.support_judgment
            or not claim.support_judgment_sha256
        ):
            missing_support_judgment_count += 1
            reasons.append(f"{claim.claim_id} is missing a claim support judgment from the judge.")
        else:
            if claim.support_verdict not in CLAIM_SUPPORT_VERDICTS:
                support_judgment_contract_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} has an invalid support verdict '{claim.support_verdict}'."
                )
            if claim.support_judgment_sha256 != _payload_sha256(claim.support_judgment):
                support_judgment_integrity_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} support judgment hash does not match recomputation."
                )
            support_contract_mismatches = claim_support_judgment_contract_mismatches(
                claim,
                min_claim_support_score=min_claim_support_score,
            )
            if support_contract_mismatches:
                support_judgment_contract_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} support judgment does not match claim fields: "
                    f"{', '.join(support_contract_mismatches)}."
                )
            if claim.support_verdict != "supported":
                unsupported_support_judgment_count += 1
                reasons.append(
                    f"{claim.claim_id} support judge verdict is {claim.support_verdict}."
                )
            if float(claim.support_score) < min_claim_support_score:
                claim_support_score_below_threshold_count += 1
                reasons.append(
                    f"{claim.claim_id} support score {claim.support_score:.4f} is below "
                    f"the required threshold {min_claim_support_score:.4f}."
                )
        if not claim.source_search_request_result_ids:
            claims_missing_source_search_request_result_count += 1
            reasons.append(f"{claim.claim_id} is missing source search request result identifiers.")
        missing_evidence_card_ids = [
            card_id for card_id in claim.evidence_card_ids if card_id not in card_ids
        ]
        if missing_evidence_card_ids:
            unresolved_evidence_card_ref_count += len(missing_evidence_card_ids)
            reasons.append(
                f"{claim.claim_id} references missing evidence cards: "
                f"{', '.join(missing_evidence_card_ids)}."
            )
        evidence_resolved = bool(claim.evidence_card_ids) and all(
            card_id in card_ids for card_id in claim.evidence_card_ids
        )
        missing_graph_edge_ids = [
            edge_id for edge_id in claim.graph_edge_ids if edge_id not in graph_edges
        ]
        if missing_graph_edge_ids:
            unresolved_graph_edge_ref_count += len(missing_graph_edge_ids)
            reasons.append(
                f"{claim.claim_id} references missing graph edges: "
                f"{', '.join(missing_graph_edge_ids)}."
            )
        graph_refs = [
            graph_edges[edge_id] for edge_id in claim.graph_edge_ids if edge_id in graph_edges
        ]
        graph_resolved = bool(claim.graph_edge_ids) and len(graph_refs) == len(claim.graph_edge_ids)
        graph_approved = graph_resolved and all(
            edge.review_status == "approved" for edge in graph_refs
        )
        unapproved_graph_refs = [edge for edge in graph_refs if edge.review_status != "approved"]
        if unapproved_graph_refs and require_graph_edges_approved:
            unapproved_graph_claim_count += 1
            reasons.append(
                f"{claim.claim_id} references graph edges that are not approved: "
                f"{', '.join(edge.edge_id for edge in unapproved_graph_refs)}."
            )
        if evidence_resolved or graph_approved:
            resolved_claim_count += 1
            supported_concept_keys.update(claim.concept_keys)
        else:
            unsupported_claim_count += 1
            reasons.append(f"{claim.claim_id} does not resolve to allowed support.")

    claim_count = len(draft.claims)
    traceable_claim_ratio = resolved_claim_count / claim_count if claim_count else 0.0
    required_concept_count = len(required_concept_keys)
    covered_required_concept_count = len(required_concept_keys.intersection(supported_concept_keys))
    required_concept_coverage_ratio = (
        covered_required_concept_count / required_concept_count if required_concept_count else 1.0
    )
    graph_claim_count = sum(1 for claim in draft.claims if claim.graph_edge_ids)
    claims_with_evidence_package_hash_count = claim_count - missing_evidence_package_hash_count
    claims_with_derivation_hash_count = claim_count - missing_derivation_hash_count
    claims_with_provenance_lock_count = claim_count - missing_provenance_lock_count
    claims_with_support_judgment_count = claim_count - missing_support_judgment_count
    if unsupported_claim_count > max_unsupported_claim_count:
        reasons.append(
            f"Unsupported claim count {unsupported_claim_count} exceeds the allowed maximum "
            f"of {max_unsupported_claim_count}."
        )
    if require_full_claim_traceability and traceable_claim_ratio < 1.0:
        reasons.append("Not every rendered claim resolves to allowed report evidence.")
    if require_full_concept_coverage and required_concept_coverage_ratio < 1.0:
        reasons.append("The report does not cover every required concept from the harness.")
    if context_blocker_count:
        reasons.append("The report used missing or schema-mismatched wake-up context.")
    if missing_wake_context_count:
        reasons.append("The report draft does not carry refreshed wake-up context refs.")
    if require_full_claim_traceability and (
        missing_evidence_package_hash_count
        or missing_derivation_hash_count
        or evidence_package_mismatch_count
        or evidence_package_integrity_mismatch_count
        or derivation_integrity_mismatch_count
        or missing_provenance_lock_count
        or provenance_lock_integrity_mismatch_count
        or provenance_lock_contract_mismatch_count
        or claims_missing_source_search_request_result_count
    ):
        reasons.append(
            "Frozen evidence package, derivation hashes, provenance locks, and source "
            "search result identifiers are required and must match recomputation."
        )
    if require_claim_support_judgments and (
        missing_support_judgment_count
        or support_judgment_integrity_mismatch_count
        or support_judgment_contract_mismatch_count
        or unsupported_support_judgment_count
        or claim_support_score_below_threshold_count
    ):
        reasons.append(
            "Every generated claim must pass the claim support judge with a recomputable "
            "support judgment and score."
        )
    if block_stale_context and stale_context_count:
        reasons.append("The report used stale wake-up context while stale blocking was enabled.")

    summary = {
        "claim_count": claim_count,
        "section_count": len(draft.sections),
        "evidence_card_count": len(draft.evidence_cards),
        "graph_edge_count": len(draft.graph_context),
        "graph_claim_count": graph_claim_count,
        "resolved_claim_count": resolved_claim_count,
        "unsupported_claim_count": unsupported_claim_count,
        "claims_with_evidence_package_hash_count": claims_with_evidence_package_hash_count,
        "claims_with_derivation_hash_count": claims_with_derivation_hash_count,
        "claims_with_provenance_lock_count": claims_with_provenance_lock_count,
        "claims_with_support_judgment_count": claims_with_support_judgment_count,
        "draft_evidence_package_hash_present": bool(draft.evidence_package_sha256),
        "expected_evidence_package_sha256": expected_package_sha256,
        "missing_evidence_package_hash_count": missing_evidence_package_hash_count,
        "missing_derivation_hash_count": missing_derivation_hash_count,
        "missing_provenance_lock_count": missing_provenance_lock_count,
        "evidence_package_mismatch_count": evidence_package_mismatch_count,
        "evidence_package_integrity_mismatch_count": evidence_package_integrity_mismatch_count,
        "derivation_integrity_mismatch_count": derivation_integrity_mismatch_count,
        "provenance_lock_integrity_mismatch_count": provenance_lock_integrity_mismatch_count,
        "provenance_lock_contract_mismatch_count": provenance_lock_contract_mismatch_count,
        "claims_missing_source_search_request_result_count": (
            claims_missing_source_search_request_result_count
        ),
        "missing_support_judgment_count": missing_support_judgment_count,
        "support_judgment_integrity_mismatch_count": support_judgment_integrity_mismatch_count,
        "support_judgment_contract_mismatch_count": support_judgment_contract_mismatch_count,
        "unsupported_support_judgment_count": unsupported_support_judgment_count,
        "claim_support_score_below_threshold_count": claim_support_score_below_threshold_count,
        "min_claim_support_score": min_claim_support_score,
        "traceable_claim_ratio": traceable_claim_ratio,
        "required_concept_count": required_concept_count,
        "covered_required_concept_count": covered_required_concept_count,
        "required_concept_coverage_ratio": required_concept_coverage_ratio,
        "unapproved_graph_claim_count": unapproved_graph_claim_count,
        "unresolved_evidence_card_ref_count": unresolved_evidence_card_ref_count,
        "unresolved_graph_edge_ref_count": unresolved_graph_edge_ref_count,
        "context_ref_count": len(context_refs),
        "missing_wake_context_count": missing_wake_context_count,
        "context_blocker_count": context_blocker_count,
        "stale_context_count": stale_context_count,
    }
    success_metrics = _technical_report_verification_metrics(summary)
    return TechnicalReportVerificationOutcome(
        summary=summary,
        success_metrics=success_metrics,
        verification_outcome="failed" if reasons else "passed",
        verification_metrics=summary,
        verification_reasons=reasons,
        verification_details={
            "thresholds": {
                "max_unsupported_claim_count": max_unsupported_claim_count,
                "require_full_claim_traceability": require_full_claim_traceability,
                "require_full_concept_coverage": require_full_concept_coverage,
                "require_graph_edges_approved": require_graph_edges_approved,
                "block_stale_context": block_stale_context,
                "require_claim_support_judgments": require_claim_support_judgments,
                "min_claim_support_score": min_claim_support_score,
            }
        },
    )
