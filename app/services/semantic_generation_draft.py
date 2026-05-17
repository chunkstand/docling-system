from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.text import collapse_whitespace
from app.schemas.agent_task_semantic_generation import SemanticGenerationBriefPayload
from app.services import semantic_generation_shared as _semantic_generation_shared


def _draft_success_metrics(draft: dict[str, Any]) -> list[dict[str, Any]]:
    claims = list(draft.get("claims") or [])
    sections = list(draft.get("sections") or [])
    evidence_pack = list(draft.get("evidence_pack") or [])
    graph_index = list(draft.get("graph_index") or [])
    fact_index = list(draft.get("fact_index") or [])
    assertion_index = list(draft.get("assertion_index") or [])
    traceable_claim_ratio = (
        sum(
            1
            for row in claims
            if row.get("graph_edge_ids")
            or row.get("fact_ids")
            or (row.get("assertion_ids") and row.get("evidence_labels"))
        )
        / len(claims)
        if claims
        else 0.0
    )
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": traceable_claim_ratio == 1.0 and bool(draft.get("markdown")),
            "summary": (
                "The generated document keeps every claim tied to semantic assertions and evidence."
            ),
            "details": {
                "traceable_claim_ratio": traceable_claim_ratio,
                "claim_count": len(claims),
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(sections)
            and bool(claims)
            and bool(graph_index or assertion_index or fact_index),
            "summary": (
                "The draft exposes sections, claims, fact or assertion refs, "
                "and an evidence appendix."
            ),
            "details": {
                "section_count": len(sections),
                "claim_count": len(claims),
                "graph_edge_count": len(graph_index),
                "fact_count": len(fact_index),
                "assertion_count": len(assertion_index),
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": (
                draft.get("generator_name") == "structured_fallback"
                and draft.get("document_kind")
                == _semantic_generation_shared.DOCUMENT_KIND_KNOWLEDGE_BRIEF
            ),
            "summary": (
                "Draft generation remains deterministic and bounded to the typed brief contract."
            ),
            "details": {
                "generator_name": draft.get("generator_name"),
                "used_fallback": draft.get("used_fallback"),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(draft.get("brief_task_id")) and bool(evidence_pack),
            "summary": (
                "The draft stays linked to a durable brief task and a reusable evidence pack."
            ),
            "details": {
                "brief_task_id": str(draft.get("brief_task_id")),
                "evidence_count": len(evidence_pack),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": bool(claims) and len(claims) <= max(len(evidence_pack), 1),
            "summary": "The draft turns dossier coverage into compact, reusable claim text.",
            "details": {
                "claim_count": len(claims),
                "evidence_count": len(evidence_pack),
            },
        },
    ]


def draft_semantic_grounded_document(
    brief_payload: dict[str, Any],
    *,
    brief_task_id: UUID,
) -> dict[str, Any]:
    brief = SemanticGenerationBriefPayload.model_validate(brief_payload)
    if not brief.claim_candidates:
        raise ValueError("Semantic generation brief does not contain any claim candidates.")

    assertion_index: list[dict[str, Any]] = []
    fact_index: list[dict[str, Any]] = []
    graph_index: list[dict[str, Any]] = [edge.model_dump(mode="json") for edge in brief.graph_index]
    for concept_entry in brief.semantic_dossier:
        for fact in concept_entry.facts:
            fact_index.append(fact.model_dump(mode="json"))
        for assertion in concept_entry.assertions:
            assertion_index.append(assertion.model_dump(mode="json"))

    claim_candidates_by_id = {claim.claim_id: claim for claim in brief.claim_candidates}
    claims: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    for section in brief.sections:
        section_claims = [claim_candidates_by_id[claim_id] for claim_id in section.claim_ids]
        body_lines = [section.summary, ""]
        for claim in section_claims:
            rendered_text = claim.summary
            if claim.disclosure_note:
                rendered_text = f"{rendered_text} {claim.disclosure_note}"
            claims.append(
                {
                    "claim_id": claim.claim_id,
                    "section_id": claim.section_id,
                    "rendered_text": rendered_text,
                    "concept_keys": list(claim.concept_keys),
                    "graph_edge_ids": list(claim.graph_edge_ids),
                    "fact_ids": list(claim.fact_ids),
                    "assertion_ids": list(claim.assertion_ids),
                    "evidence_labels": list(claim.evidence_labels),
                    "source_document_ids": list(claim.source_document_ids),
                    "support_level": claim.support_level,
                    "review_policy_status": claim.review_policy_status,
                    "disclosure_note": claim.disclosure_note,
                }
            )
            evidence_phrase = (
                f" Evidence: {', '.join(f'[{label}]' for label in claim.evidence_labels)}."
                if claim.evidence_labels
                else ""
            )
            body_lines.append(f"- {rendered_text}{evidence_phrase}")
        sections.append(
            {
                "section_id": section.section_id,
                "title": section.title,
                "body_markdown": "\n".join(body_lines).strip(),
                "claim_ids": list(section.claim_ids),
            }
        )

    scope_labels = ", ".join(
        _semantic_generation_shared._document_label(row.model_dump(mode="json"))
        for row in brief.document_refs
    )
    markdown_parts = [f"# {brief.title}", "", brief.goal]
    if brief.audience:
        markdown_parts.extend(["", f"Audience: {brief.audience}"])
    markdown_parts.extend(["", f"Corpus scope: {scope_labels}"])
    if brief.warnings:
        markdown_parts.extend(["", "Warnings:"])
        markdown_parts.extend(f"- {warning}" for warning in brief.warnings)
    for section in sections:
        markdown_parts.extend(["", f"## {section['title']}", "", section["body_markdown"]])
    markdown_parts.extend(["", "## Evidence Appendix", ""])
    for evidence in brief.evidence_pack:
        excerpt = collapse_whitespace(evidence.excerpt) or "No excerpt captured."
        markdown_parts.append(
            f"- [{evidence.citation_label}] {evidence.source_filename}, "
            f"{_semantic_generation_shared._page_label(evidence.page_from, evidence.page_to)} "
            f"({evidence.source_type}): {excerpt}"
        )
    markdown = "\n".join(markdown_parts).strip() + "\n"

    draft = {
        "document_kind": brief.document_kind,
        "title": brief.title,
        "goal": brief.goal,
        "audience": brief.audience,
        "review_policy": brief.review_policy,
        "target_length": brief.target_length,
        "brief_task_id": brief_task_id,
        "generator_name": "structured_fallback",
        "generator_model": None,
        "used_fallback": True,
        "required_concept_keys": list(brief.required_concept_keys or brief.selected_concept_keys),
        "document_refs": [row.model_dump(mode="json") for row in brief.document_refs],
        "graph_index": graph_index,
        "fact_index": fact_index,
        "assertion_index": assertion_index,
        "sections": sections,
        "claims": claims,
        "evidence_pack": [row.model_dump(mode="json") for row in brief.evidence_pack],
        "markdown": markdown,
        "markdown_path": None,
        "warnings": list(brief.warnings),
    }
    draft["success_metrics"] = _draft_success_metrics(draft)
    return draft
