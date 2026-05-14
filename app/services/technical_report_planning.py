from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.coercion import unique_strings as _unique_strings
from app.core.text import collapse_whitespace
from app.schemas.agent_task_reports import (
    TechnicalReportPlanPayload,
    TechnicalReportSectionPlan,
)
from app.schemas.agent_task_semantic_generation import (
    SemanticGenerationBriefPayload,
    SemanticGenerationClaimCandidate,
)
from app.services.semantic_generation import prepare_semantic_generation_brief
from app.services.technical_report_shared import expert_alignment, success_metric


def _claim_lookup(
    claims: list[SemanticGenerationClaimCandidate],
) -> dict[str, SemanticGenerationClaimCandidate]:
    return {claim.claim_id: claim for claim in claims}


def _section_retrieval_queries(
    title: str,
    concept_keys: list[str],
    category_keys: list[str],
) -> list[str]:
    query_parts = [title, *[key.replace("_", " ") for key in concept_keys]]
    if category_keys:
        query_parts.extend(key.replace("_", " ") for key in category_keys)
    return [collapse_whitespace(" ".join(query_parts))]


def plan_technical_report(
    session: Session,
    *,
    title: str,
    goal: str,
    audience: str | None,
    document_ids: list[UUID],
    concept_keys: list[str],
    category_keys: list[str],
    target_length: str,
    review_policy: str,
    include_shadow_candidates: bool = False,
    candidate_extractor_name: str = "concept_ranker_v1",
    candidate_score_threshold: float = 0.34,
    max_shadow_candidates: int = 8,
) -> dict[str, Any]:
    semantic_brief_payload = prepare_semantic_generation_brief(
        session,
        title=title,
        goal=goal,
        audience=audience,
        document_ids=document_ids,
        concept_keys=concept_keys,
        category_keys=category_keys,
        target_length=target_length,
        review_policy=review_policy,
        include_shadow_candidates=include_shadow_candidates,
        candidate_extractor_name=candidate_extractor_name,
        candidate_score_threshold=candidate_score_threshold,
        max_shadow_candidates=max_shadow_candidates,
    )
    semantic_brief = SemanticGenerationBriefPayload.model_validate(semantic_brief_payload)
    claims_by_id = _claim_lookup(list(semantic_brief.claim_candidates))
    warnings = list(semantic_brief.warnings)

    sections: list[dict[str, Any]] = []
    retrieval_plan: list[dict[str, Any]] = []
    for section in semantic_brief.sections:
        missing_claim_ids = [
            claim_id for claim_id in section.claim_ids if claim_id not in claims_by_id
        ]
        if missing_claim_ids:
            warnings.append(
                f"{section.section_id} references missing claim ids: "
                f"{', '.join(missing_claim_ids)}."
            )
        section_claims = [
            claims_by_id[claim_id] for claim_id in section.claim_ids if claim_id in claims_by_id
        ]
        required_graph_edge_ids = _unique_strings(
            [graph_edge_id for claim in section_claims for graph_edge_id in claim.graph_edge_ids]
        )
        queries = _section_retrieval_queries(
            section.title,
            list(section.focus_concept_keys),
            list(section.focus_category_keys),
        )
        section_plan = TechnicalReportSectionPlan(
            section_id=section.section_id,
            title=section.title,
            purpose=section.summary,
            focus_concept_keys=list(section.focus_concept_keys),
            focus_category_keys=list(section.focus_category_keys),
            expected_claim_ids=list(section.claim_ids),
            retrieval_queries=queries,
            required_graph_edge_ids=required_graph_edge_ids,
        )
        sections.append(section_plan.model_dump(mode="json"))
        retrieval_plan.append(
            {
                "section_id": section.section_id,
                "queries": queries,
                "document_ids": [
                    str(document_ref.document_id) for document_ref in semantic_brief.document_refs
                ],
                "filters": {
                    "concept_keys": list(section.focus_concept_keys),
                    "category_keys": list(section.focus_category_keys),
                },
                "expected_claim_ids": list(section.claim_ids),
            }
        )

    expected_graph_edge_ids = _unique_strings(
        [edge_id for claim in semantic_brief.claim_candidates for edge_id in claim.graph_edge_ids]
    )
    plan = {
        "report_type": "technical_report",
        "title": title,
        "goal": goal,
        "audience": audience,
        "review_policy": review_policy,
        "target_length": target_length,
        "document_refs": [row.model_dump(mode="json") for row in semantic_brief.document_refs],
        "required_concept_keys": list(semantic_brief.required_concept_keys),
        "selected_concept_keys": list(semantic_brief.selected_concept_keys),
        "selected_category_keys": list(semantic_brief.selected_category_keys),
        "sections": sections,
        "expected_claims": [row.model_dump(mode="json") for row in semantic_brief.claim_candidates],
        "expected_graph_edge_ids": expected_graph_edge_ids,
        "retrieval_plan": retrieval_plan,
        "semantic_brief": semantic_brief.model_dump(mode="json"),
        "warnings": _unique_strings(warnings),
        "expert_alignment": expert_alignment(),
    }
    plan["success_metrics"] = [
        success_metric(
            "semantic_plan_available",
            "Joshua Yu + Nicolas Figay",
            bool(semantic_brief.claim_candidates),
            "The report plan is derived from the evidence-backed semantic brief.",
            {"claim_count": len(semantic_brief.claim_candidates)},
        ),
        success_metric(
            "section_contract_available",
            "Jerry Liu",
            bool(sections),
            "The plan exposes an agent-legible section and claim contract.",
            {"section_count": len(sections)},
        ),
        success_metric(
            "graph_requirements_explicit",
            "Juan Sequeda",
            True,
            "Graph requirements are explicit even when no approved graph edges are in scope.",
            {"expected_graph_edge_count": len(expected_graph_edge_ids)},
        ),
    ]
    return TechnicalReportPlanPayload.model_validate(plan).model_dump(mode="json")
