from __future__ import annotations

from typing import Any

from app.services import semantic_generation_shared as _semantic_generation_shared


def _brief_success_metrics(brief: dict[str, Any]) -> list[dict[str, Any]]:
    document_refs = list(brief.get("document_refs") or [])
    claim_candidates = list(brief.get("claim_candidates") or [])
    evidence_pack = list(brief.get("evidence_pack") or [])
    semantic_dossier = list(brief.get("semantic_dossier") or [])
    graph_index = list(brief.get("graph_index") or [])
    shadow_candidates = list(brief.get("shadow_candidates") or [])
    traceable_claim_ratio = (
        sum(
            1
            for row in claim_candidates
            if row.get("graph_edge_ids")
            or row.get("fact_ids")
            or (row.get("assertion_ids") and row.get("evidence_labels"))
        )
        / len(claim_candidates)
        if claim_candidates
        else 0.0
    )
    facts_by_concept = {
        str(entry.get("concept_key") or ""): list(entry.get("facts") or [])
        for entry in semantic_dossier
    }
    fact_backed_claim_count = 0
    approved_fact_backed_claim_count = 0
    for row in claim_candidates:
        claim_facts = [
            fact
            for concept_key in row.get("concept_keys") or []
            for fact in facts_by_concept.get(str(concept_key), [])
        ]
        if not claim_facts:
            continue
        fact_backed_claim_count += 1
        if all(fact.get("review_status") == "approved" for fact in claim_facts):
            approved_fact_backed_claim_count += 1
    approved_fact_support_ratio = (
        approved_fact_backed_claim_count / fact_backed_claim_count
        if fact_backed_claim_count
        else 1.0
    )
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": bool(document_refs)
            and all(
                row.get("registry_version") and row.get("registry_sha256") for row in document_refs
            )
            and traceable_claim_ratio == 1.0,
            "summary": "Every brief claim is tied to version-stamped semantic sources "
            "and evidence.",
            "details": {
                "document_count": len(document_refs),
                "traceable_claim_ratio": traceable_claim_ratio,
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(claim_candidates)
            and all(row.get("claim_id") and row.get("section_id") for row in claim_candidates),
            "summary": "The generation brief exposes typed claims, sections, and "
            "evidence-pack labels.",
            "details": {
                "claim_count": len(claim_candidates),
                "section_count": len(brief.get("sections") or []),
                "graph_edge_count": len(graph_index),
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": (
                brief.get("document_kind")
                == _semantic_generation_shared.DOCUMENT_KIND_KNOWLEDGE_BRIEF
                and brief.get("review_policy")
                in {"approved_only", "allow_candidate_with_disclosure"}
            ),
            "summary": "Document generation stays bounded to one explicit artifact type "
            "and policy.",
            "details": {
                "document_kind": brief.get("document_kind"),
                "review_policy": brief.get("review_policy"),
            },
        },
        {
            "metric_key": "explicit_shadow_boundary",
            "stakeholder": "Figay",
            "passed": (
                not brief.get("shadow_mode")
                or all(
                    row.get("concept_key") not in set(brief.get("selected_concept_keys") or [])
                    for row in shadow_candidates
                )
            ),
            "summary": "Shadow candidates stay additive and separate from the live semantic "
            "dossier.",
            "details": {
                "shadow_mode": brief.get("shadow_mode"),
                "shadow_candidate_count": len(shadow_candidates),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(semantic_dossier) and bool(evidence_pack),
            "summary": "The brief persists owned semantic context instead of reconstructing "
            "it ad hoc.",
            "details": {
                "concept_count": len(semantic_dossier),
                "evidence_count": len(evidence_pack),
                "graph_edge_count": len(graph_index),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": bool(claim_candidates)
            and len(claim_candidates) <= max(len(evidence_pack), 1),
            "summary": "The brief compresses corpus evidence into compact claims for "
            "downstream agents.",
            "details": {
                "claim_count": len(claim_candidates),
                "evidence_count": len(evidence_pack),
            },
        },
        {
            "metric_key": "approved_fact_support_ratio",
            "stakeholder": "Milestone",
            "passed": not claim_candidates or approved_fact_support_ratio >= 0.8,
            "summary": "Generation prefers approved fact support when it is available.",
            "details": {
                "approved_fact_support_ratio": approved_fact_support_ratio,
                "fact_backed_claim_count": fact_backed_claim_count,
            },
        },
    ]
