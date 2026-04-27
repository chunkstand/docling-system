from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.core.time import utcnow
from app.schemas.agent_tasks import (
    ContextFreshnessStatus,
    ContextRef,
    ReportAgentHarnessPayload,
    SemanticGenerationBriefPayload,
    SemanticGenerationClaimCandidate,
    TechnicalReportDraftPayload,
    TechnicalReportEvidenceBundlePayload,
    TechnicalReportEvidenceCard,
    TechnicalReportPlanPayload,
    TechnicalReportSectionPlan,
    TechnicalReportSkillContract,
    TechnicalReportToolContract,
)
from app.services.evidence import (
    apply_technical_report_derivation_links,
    build_technical_report_derivation_package,
)
from app.services.semantic_generation import prepare_semantic_generation_brief


@dataclass(frozen=True)
class TechnicalReportVerificationOutcome:
    summary: dict[str, Any]
    success_metrics: list[dict[str, Any]]
    verification_outcome: str
    verification_metrics: dict[str, Any]
    verification_reasons: list[str]
    verification_details: dict[str, Any]


def _payload_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unique_strings(values: list[str]) -> list[str]:
    return [value for value in dict.fromkeys(values) if value]


def _unique_uuids(values: list[UUID]) -> list[UUID]:
    return [value for value in dict.fromkeys(values) if value is not None]


def _expert_alignment() -> list[dict[str, str]]:
    return [
        {
            "expert": "Joshua Yu",
            "principle": (
                "Graph memory is a governed semantic control plane, "
                "not a source-of-truth shortcut."
            ),
        },
        {
            "expert": "Steve Yegge",
            "principle": (
                "The report loop is a reusable platform primitive with "
                "compact, durable artifacts."
            ),
        },
        {
            "expert": "Armin Ronacher",
            "principle": (
                "Control flow, schemas, tools, and failure modes are explicit "
                "instead of prompt-hidden."
            ),
        },
        {
            "expert": "Ryan Lopopolo",
            "principle": (
                "The harness is agent-legible: one typed packet carries task, "
                "context, and checks."
            ),
        },
        {
            "expert": "Nate B. Jones",
            "principle": (
                "Context ownership, freshness, and trust boundaries are visible "
                "at wake-up time."
            ),
        },
    ]


def _success_metric(
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
            claims_by_id[claim_id]
            for claim_id in section.claim_ids
            if claim_id in claims_by_id
        ]
        required_graph_edge_ids = _unique_strings(
            [
                graph_edge_id
                for claim in section_claims
                for graph_edge_id in claim.graph_edge_ids
            ]
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
                    str(document_ref.document_id)
                    for document_ref in semantic_brief.document_refs
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
        "expected_claims": [
            row.model_dump(mode="json") for row in semantic_brief.claim_candidates
        ],
        "expected_graph_edge_ids": expected_graph_edge_ids,
        "retrieval_plan": retrieval_plan,
        "semantic_brief": semantic_brief.model_dump(mode="json"),
        "warnings": _unique_strings(warnings),
        "expert_alignment": _expert_alignment(),
    }
    plan["success_metrics"] = [
        _success_metric(
            "semantic_plan_available",
            "Joshua Yu",
            bool(semantic_brief.claim_candidates),
            "The report plan is derived from the evidence-backed semantic brief.",
            {"claim_count": len(semantic_brief.claim_candidates)},
        ),
        _success_metric(
            "section_contract_available",
            "Ryan Lopopolo",
            bool(sections),
            "The plan exposes an agent-legible section and claim contract.",
            {"section_count": len(sections)},
        ),
        _success_metric(
            "graph_requirements_explicit",
            "Armin Ronacher",
            True,
            "Graph requirements are explicit even when no approved graph edges are in scope.",
            {"expected_graph_edge_count": len(expected_graph_edge_ids)},
        ),
    ]
    return TechnicalReportPlanPayload.model_validate(plan).model_dump(mode="json")


def build_report_evidence_cards(
    plan_payload: dict[str, Any],
    *,
    plan_task_id: UUID,
) -> dict[str, Any]:
    plan = TechnicalReportPlanPayload.model_validate(plan_payload)
    brief = plan.semantic_brief
    claims = list(brief.claim_candidates)
    evidence_cards: list[dict[str, Any]] = []
    card_id_by_evidence_label: dict[str, str] = {}
    card_ids_by_evidence_id: dict[UUID, list[str]] = {}
    card_ids_by_fact_id: dict[UUID, list[str]] = {}
    card_ids_by_assertion_id: dict[UUID, list[str]] = {}
    card_id_by_graph_edge_id: dict[str, str] = {}
    warnings = list(plan.warnings)
    next_card_index = 1

    for evidence in brief.evidence_pack:
        card_id = f"EC{next_card_index}"
        next_card_index += 1
        related_claims = [
            claim for claim in claims if evidence.citation_label in claim.evidence_labels
        ]
        concept_keys = _unique_strings(
            [concept_key for claim in related_claims for concept_key in claim.concept_keys]
        )
        assertion_ids = _unique_uuids(
            [assertion_id for claim in related_claims for assertion_id in claim.assertion_ids]
        )
        fact_ids = _unique_uuids(
            [fact_id for claim in related_claims for fact_id in claim.fact_ids]
        )
        card = TechnicalReportEvidenceCard(
            evidence_card_id=card_id,
            evidence_kind="source_evidence",
            source_type=evidence.source_type,
            citation_label=evidence.citation_label,
            document_id=evidence.document_id,
            run_id=evidence.run_id,
            semantic_pass_id=evidence.semantic_pass_id,
            source_document_ids=[evidence.document_id],
            source_filename=evidence.source_filename,
            page_from=evidence.page_from,
            page_to=evidence.page_to,
            excerpt=evidence.excerpt,
            source_artifact_api_path=evidence.source_artifact_api_path,
            evidence_ids=[evidence.evidence_id],
            fact_ids=fact_ids,
            assertion_ids=assertion_ids,
            concept_keys=concept_keys,
            support_level="source",
            review_status=evidence.review_status,
            metadata={"matched_terms": list(evidence.matched_terms)},
        )
        evidence_cards.append(card.model_dump(mode="json"))
        card_id_by_evidence_label[evidence.citation_label] = card_id
        card_ids_by_evidence_id.setdefault(evidence.evidence_id, []).append(card_id)
        for fact_id in fact_ids:
            card_ids_by_fact_id.setdefault(fact_id, []).append(card_id)
        for assertion_id in assertion_ids:
            card_ids_by_assertion_id.setdefault(assertion_id, []).append(card_id)

    for concept in brief.semantic_dossier:
        for fact in concept.facts:
            matched_card_ids = [
                card_id
                for evidence_id in fact.evidence_ids
                for card_id in card_ids_by_evidence_id.get(evidence_id, [])
            ]
            if matched_card_ids:
                for card in evidence_cards:
                    if card["evidence_card_id"] in matched_card_ids:
                        card["fact_ids"] = _unique_strings(
                            [*card.get("fact_ids", []), str(fact.fact_id)]
                        )
                        if fact.assertion_id:
                            card["assertion_ids"] = _unique_strings(
                                [
                                    *card.get("assertion_ids", []),
                                    str(fact.assertion_id),
                                ]
                            )
                card_ids_by_fact_id.setdefault(fact.fact_id, []).extend(matched_card_ids)
                if fact.assertion_id:
                    card_ids_by_assertion_id.setdefault(fact.assertion_id, []).extend(
                        matched_card_ids
                    )
                continue
            card_id = f"EC{next_card_index}"
            next_card_index += 1
            card = TechnicalReportEvidenceCard(
                evidence_card_id=card_id,
                evidence_kind="semantic_fact",
                source_type="semantic_fact",
                document_id=fact.document_id,
                run_id=fact.run_id,
                semantic_pass_id=fact.semantic_pass_id,
                source_document_ids=[fact.document_id],
                excerpt=fact.object_label or fact.object_value_text,
                evidence_ids=list(fact.evidence_ids),
                fact_ids=[fact.fact_id],
                assertion_ids=[fact.assertion_id] if fact.assertion_id else [],
                concept_keys=[concept.concept_key],
                support_level=concept.support_level,
                review_status=fact.review_status,
                relation_key=fact.relation_key,
                metadata={
                    "relation_label": fact.relation_label,
                    "subject_entity_key": fact.subject_entity_key,
                    "object_entity_key": fact.object_entity_key,
                },
            )
            evidence_cards.append(card.model_dump(mode="json"))
            card_ids_by_fact_id.setdefault(fact.fact_id, []).append(card_id)
            if fact.assertion_id:
                card_ids_by_assertion_id.setdefault(fact.assertion_id, []).append(card_id)

    for graph_edge in brief.graph_index:
        if graph_edge.review_status != "approved":
            warnings.append(
                f"{graph_edge.edge_id} is present in graph context with "
                f"review_status={graph_edge.review_status!r}; verifier approval is required."
            )
        card_id = f"EC{next_card_index}"
        next_card_index += 1
        concept_keys = [
            str(graph_edge.subject_entity_key).split("concept:", 1)[-1],
            str(graph_edge.object_entity_key).split("concept:", 1)[-1],
        ]
        card = TechnicalReportEvidenceCard(
            evidence_card_id=card_id,
            evidence_kind="approved_graph_edge",
            source_type="semantic_graph",
            source_document_ids=list(graph_edge.supporting_document_ids),
            excerpt=(
                f"{graph_edge.subject_label} -> {graph_edge.relation_label} -> "
                f"{graph_edge.object_label}"
            ),
            graph_edge_ids=[graph_edge.edge_id],
            concept_keys=concept_keys,
            support_level=graph_edge.support_level,
            review_status=graph_edge.review_status,
            relation_key=graph_edge.relation_key,
            metadata={
                "graph_snapshot_id": str(graph_edge.graph_snapshot_id),
                "graph_version": graph_edge.graph_version,
                "support_ref_ids": list(graph_edge.support_ref_ids),
            },
        )
        evidence_cards.append(card.model_dump(mode="json"))
        card_id_by_graph_edge_id[graph_edge.edge_id] = card_id

    claim_evidence_map: list[dict[str, Any]] = []
    for claim in claims:
        source_card_ids = [
            card_id_by_evidence_label[label]
            for label in claim.evidence_labels
            if label in card_id_by_evidence_label
        ]
        graph_card_ids = [
            card_id_by_graph_edge_id[edge_id]
            for edge_id in claim.graph_edge_ids
            if edge_id in card_id_by_graph_edge_id
        ]
        fact_card_ids = [
            card_id
            for fact_id in claim.fact_ids
            for card_id in card_ids_by_fact_id.get(fact_id, [])
        ]
        assertion_card_ids = [
            card_id
            for assertion_id in claim.assertion_ids
            for card_id in card_ids_by_assertion_id.get(assertion_id, [])
        ]
        missing_evidence_labels = [
            label for label in claim.evidence_labels if label not in card_id_by_evidence_label
        ]
        missing_graph_edge_ids = [
            edge_id for edge_id in claim.graph_edge_ids if edge_id not in card_id_by_graph_edge_id
        ]
        missing_fact_ids = [
            str(fact_id) for fact_id in claim.fact_ids if fact_id not in card_ids_by_fact_id
        ]
        missing_assertion_ids = [
            str(assertion_id)
            for assertion_id in claim.assertion_ids
            if assertion_id not in card_ids_by_assertion_id
        ]
        if missing_evidence_labels:
            warnings.append(
                f"{claim.claim_id} references missing evidence labels: "
                f"{', '.join(missing_evidence_labels)}."
            )
        if missing_graph_edge_ids:
            warnings.append(
                f"{claim.claim_id} references missing graph edges: "
                f"{', '.join(missing_graph_edge_ids)}."
            )
        if missing_fact_ids:
            warnings.append(
                f"{claim.claim_id} references facts without evidence cards: "
                f"{', '.join(missing_fact_ids)}."
            )
        if missing_assertion_ids:
            warnings.append(
                f"{claim.claim_id} references assertions without evidence cards: "
                f"{', '.join(missing_assertion_ids)}."
            )
        evidence_card_ids = _unique_strings(
            [*source_card_ids, *graph_card_ids, *fact_card_ids, *assertion_card_ids]
        )
        if not evidence_card_ids and not claim.graph_edge_ids:
            warnings.append(f"{claim.claim_id} has no resolvable report evidence support.")
        claim_evidence_map.append(
            {
                "claim_id": claim.claim_id,
                "section_id": claim.section_id,
                "summary": claim.summary,
                "concept_keys": list(claim.concept_keys),
                "evidence_card_ids": evidence_card_ids,
                "graph_edge_ids": list(claim.graph_edge_ids),
                "fact_ids": [str(fact_id) for fact_id in claim.fact_ids],
                "assertion_ids": [str(assertion_id) for assertion_id in claim.assertion_ids],
                "missing_evidence_labels": missing_evidence_labels,
                "missing_graph_edge_ids": missing_graph_edge_ids,
                "missing_fact_ids": missing_fact_ids,
                "missing_assertion_ids": missing_assertion_ids,
                "source_document_ids": [
                    str(document_id) for document_id in claim.source_document_ids
                ],
                "support_level": claim.support_level,
                "review_policy_status": claim.review_policy_status,
                "disclosure_note": claim.disclosure_note,
            }
        )

    bundle = {
        "plan_task_id": plan_task_id,
        "plan": plan.model_dump(mode="json"),
        "evidence_cards": evidence_cards,
        "claim_evidence_map": claim_evidence_map,
        "retrieval_index": list(plan.retrieval_plan),
        "graph_context": [edge.model_dump(mode="json") for edge in brief.graph_index],
        "warnings": _unique_strings(warnings),
        "expert_alignment": _expert_alignment(),
    }
    bundle["success_metrics"] = [
        _success_metric(
            "evidence_cards_available",
            "Ryan Lopopolo",
            bool(evidence_cards),
            "The report has stable evidence cards for agent-legible claim binding.",
            {"evidence_card_count": len(evidence_cards)},
        ),
        _success_metric(
            "table_evidence_preserved",
            "Joshua Yu",
            sum(1 for row in brief.evidence_pack if row.source_type == "table")
            == sum(1 for card in evidence_cards if card.get("source_type") == "table"),
            "Typed table evidence remains distinguishable from prose evidence.",
            {
                "source_table_count": sum(
                    1 for row in brief.evidence_pack if row.source_type == "table"
                ),
                "table_card_count": sum(
                    1 for card in evidence_cards if card.get("source_type") == "table"
                ),
                "source_types": sorted(
                    {str(card.get("source_type")) for card in evidence_cards}
                ),
            },
        ),
        _success_metric(
            "claim_contract_bound",
            "Nate B. Jones",
            all(
                (row["evidence_card_ids"] or row["graph_edge_ids"])
                and not row["missing_evidence_labels"]
                and not row["missing_graph_edge_ids"]
                and not row["missing_fact_ids"]
                and not row["missing_assertion_ids"]
                for row in claim_evidence_map
            ),
            "Every planned claim has explicit support or graph context before drafting.",
            {"claim_count": len(claim_evidence_map)},
        ),
    ]
    return TechnicalReportEvidenceBundlePayload.model_validate(bundle).model_dump(mode="json")


def _default_allowed_tools() -> list[dict[str, Any]]:
    return [
        TechnicalReportToolContract(
            tool_name="read_task_context",
            purpose="Load the canonical task context envelope at wake-up time.",
            access_pattern="GET /agent-tasks/{task_id}/context?format=json",
            input_contract={"task_id": "uuid", "format": "json"},
            output_contract={"schema_name": "agent_task_context"},
            required_capability="agent_tasks:read",
        ).model_dump(mode="json"),
        TechnicalReportToolContract(
            tool_name="read_task_artifact",
            purpose=(
                "Fetch typed report-plan, evidence-card, harness, draft, "
                "or verification artifacts."
            ),
            access_pattern="GET /agent-tasks/{task_id}/artifacts/{artifact_id}",
            input_contract={"task_id": "uuid", "artifact_id": "uuid"},
            output_contract={"payload": "typed artifact json"},
            required_capability="agent_tasks:read",
        ).model_dump(mode="json"),
        TechnicalReportToolContract(
            tool_name="search_corpus",
            purpose=(
                "Run additional bounded corpus search when a planned section "
                "has missing support."
            ),
            access_pattern="POST /search",
            input_contract={"query": "string", "document_id": "optional uuid"},
            output_contract={"results": "mixed chunks and tables"},
            required_capability="documents:read",
        ).model_dump(mode="json"),
        TechnicalReportToolContract(
            tool_name="create_followup_task",
            purpose=(
                "Create a follow-up agent task when evidence, graph, or "
                "freshness gaps block drafting."
            ),
            access_pattern="POST /agent-tasks",
            input_contract={"task_type": "string", "input": "object"},
            output_contract={"task_id": "uuid", "status": "string"},
            required_capability="agent_tasks:write",
        ).model_dump(mode="json"),
    ]


def _default_required_skills() -> list[dict[str, Any]]:
    return [
        TechnicalReportSkillContract(
            skill_name="technical_report_planning",
            purpose="Follow the section and claim plan instead of inventing a new outline.",
            instructions=[
                "Use source_plan.sections as the drafting outline.",
                "Only change section order when the harness explicitly allows it.",
            ],
        ).model_dump(mode="json"),
        TechnicalReportSkillContract(
            skill_name="evidence_card_usage",
            purpose="Bind every claim to evidence_card_ids before rendering prose.",
            instructions=[
                "Prefer table evidence cards for numeric or tabular claims.",
                "Do not cite a document unless the card carries that source_document_id.",
            ],
        ).model_dump(mode="json"),
        TechnicalReportSkillContract(
            skill_name="graph_context_usage",
            purpose="Use graph edges as relationship memory with underlying support refs.",
            instructions=[
                "Use only graph edges present in graph_context.",
                "Do not treat graph memory as source truth without evidence cards or support refs.",
            ],
        ).model_dump(mode="json"),
        TechnicalReportSkillContract(
            skill_name="unsupported_claim_handling",
            purpose="Block unsupported claims rather than filling gaps with plausible prose.",
            instructions=[
                "Move missing-support claims to blocked_claims.",
                "Create follow-up tasks when more retrieval or graph promotion is required.",
            ],
        ).model_dump(mode="json"),
        TechnicalReportSkillContract(
            skill_name="verification_ready_drafting",
            purpose="Draft in the exact shape the verifier can replay.",
            instructions=[
                "Preserve claim_id and section_id from the claim_contract.",
                "Emit evidence_card_ids, graph_edge_ids, fact_ids, and assertion_ids per claim.",
            ],
        ).model_dump(mode="json"),
    ]


def prepare_report_agent_harness(
    evidence_bundle_payload: dict[str, Any],
    *,
    harness_task_id: UUID,
    evidence_task_id: UUID,
    upstream_context_refs: list[ContextRef],
) -> dict[str, Any]:
    evidence_bundle = TechnicalReportEvidenceBundlePayload.model_validate(evidence_bundle_payload)
    plan = evidence_bundle.plan
    context_refs = [ref.model_dump(mode="json") for ref in upstream_context_refs]
    context_blockers = [
        ref
        for ref in context_refs
        if ref.get("freshness_status")
        in {
            ContextFreshnessStatus.MISSING.value,
            ContextFreshnessStatus.SCHEMA_MISMATCH.value,
        }
    ]
    blocked_steps: list[dict[str, Any]] = []
    if not context_refs:
        blocked_steps.append(
            {
                "step": "draft_technical_report",
                "reason": "Missing upstream context refs for agent wake-up.",
            }
        )
    if context_blockers:
        blocked_steps.append(
            {
                "step": "draft_technical_report",
                "reason": "Upstream context refs include missing or schema-mismatched inputs.",
                "ref_keys": [str(ref.get("ref_key")) for ref in context_blockers],
            }
        )
    harness = {
        "schema_name": "report_agent_harness",
        "schema_version": "1.0",
        "report_request": {
            "title": plan.title,
            "goal": plan.goal,
            "audience": plan.audience,
            "target_length": plan.target_length,
            "review_policy": plan.review_policy,
            "document_ids": [
                str(document_ref.document_id) for document_ref in plan.document_refs
            ],
            "required_concept_keys": list(plan.required_concept_keys),
        },
        "workflow_state": {
            "harness_task_id": str(harness_task_id),
            "plan_task_id": str(evidence_bundle.plan_task_id),
            "evidence_task_id": str(evidence_task_id),
            "completed_steps": [
                "plan_technical_report",
                "build_report_evidence_cards",
                "prepare_report_agent_harness",
            ],
            "next_task_type": "draft_technical_report",
            "blocked_steps": blocked_steps,
        },
        "context_refs": context_refs,
        "allowed_tools": _default_allowed_tools(),
        "required_skills": _default_required_skills(),
        "retrieval_plan": list(evidence_bundle.retrieval_index),
        "evidence_cards": [
            card.model_dump(mode="json") for card in evidence_bundle.evidence_cards
        ],
        "graph_context": [
            edge.model_dump(mode="json") for edge in evidence_bundle.graph_context
        ],
        "claim_contract": list(evidence_bundle.claim_evidence_map),
        "failure_policy": {
            "missing_evidence": "block_claim_and_create_followup",
            "stale_context": "warn_by_default_block_when_verifier_requires_it",
            "schema_mismatch": "block_task",
            "unsupported_claim": "do_not_render_as_supported_prose",
            "contradiction": "block_claim_and_surface_reason",
        },
        "verification_gate": {
            "target_task_type": "verify_technical_report",
            "max_unsupported_claim_count": 0,
            "require_full_claim_traceability": True,
            "require_full_concept_coverage": True,
            "require_graph_edges_approved": True,
            "block_stale_context": False,
        },
        "llm_adapter_contract": {
            "primary_context_schema": "report_agent_harness",
            "primary_context_ref": f"agent_task:{harness_task_id}:artifact:report_agent_harness",
            "harness_context_refs": context_refs,
            "required_output_schema": "draft_technical_report_output",
            "must_preserve_fields": [
                "claim_id",
                "section_id",
                "evidence_card_ids",
                "graph_edge_ids",
                "fact_ids",
                "assertion_ids",
                "source_document_ids",
            ],
            "allowed_tool_names": [
                tool["tool_name"] for tool in _default_allowed_tools()
            ],
            "required_skill_names": [
                skill["skill_name"] for skill in _default_required_skills()
            ],
        },
        "source_plan": plan.model_dump(mode="json"),
        "warnings": _unique_strings([*plan.warnings, *evidence_bundle.warnings]),
        "expert_alignment": _expert_alignment(),
    }
    harness["success_metrics"] = [
        _success_metric(
            "wake_up_packet_complete",
            "Ryan Lopopolo",
            bool(harness["allowed_tools"])
            and bool(harness["required_skills"])
            and bool(harness["claim_contract"])
            and bool(harness["evidence_cards"])
            and bool(context_refs)
            and not blocked_steps,
            "The wake-up packet includes tools, skills, claim contract, and evidence cards.",
            {
                "tool_count": len(harness["allowed_tools"]),
                "skill_count": len(harness["required_skills"]),
                "claim_contract_count": len(harness["claim_contract"]),
            },
        ),
        _success_metric(
            "owned_context",
            "Nate B. Jones",
            bool(context_refs),
            "The harness carries upstream context refs with freshness state.",
            {"context_ref_count": len(context_refs)},
        ),
        _success_metric(
            "explicit_tool_surface",
            "Armin Ronacher",
            all(tool.get("access_pattern") for tool in harness["allowed_tools"]),
            "Every allowed tool has an explicit access pattern and contract.",
            {"tool_names": [tool["tool_name"] for tool in harness["allowed_tools"]]},
        ),
        _success_metric(
            "platform_packet",
            "Steve Yegge",
            harness["schema_name"] == "report_agent_harness",
            "The report workflow compacts state into a reusable harness artifact.",
            {"schema_version": harness["schema_version"]},
        ),
    ]
    return ReportAgentHarnessPayload.model_validate(harness).model_dump(mode="json")


def draft_technical_report(
    harness_payload: dict[str, Any],
    *,
    harness_task_id: UUID,
    generator_mode: str = "structured_fallback",
    generator_model: str | None = None,
    llm_draft_markdown: str | None = None,
) -> dict[str, Any]:
    harness = ReportAgentHarnessPayload.model_validate(harness_payload)
    sections_by_id = {section.section_id: section for section in harness.source_plan.sections}
    section_claim_ids: dict[str, list[str]] = {section_id: [] for section_id in sections_by_id}
    claims: list[dict[str, Any]] = []
    blocked_claims: list[dict[str, Any]] = []

    for claim_contract in harness.claim_contract:
        evidence_card_ids = list(claim_contract.get("evidence_card_ids") or [])
        graph_edge_ids = list(claim_contract.get("graph_edge_ids") or [])
        fact_ids = [UUID(str(value)) for value in claim_contract.get("fact_ids") or []]
        assertion_ids = [
            UUID(str(value)) for value in claim_contract.get("assertion_ids") or []
        ]
        source_document_ids = [
            UUID(str(value)) for value in claim_contract.get("source_document_ids") or []
        ]
        if not evidence_card_ids and not graph_edge_ids:
            blocked_claims.append(
                {
                    "claim_id": claim_contract["claim_id"],
                    "section_id": claim_contract["section_id"],
                    "reason": (
                        "No evidence card or graph edge support was available."
                    ),
                    "fact_ids": [str(value) for value in fact_ids],
                    "assertion_ids": [str(value) for value in assertion_ids],
                }
            )
            continue
        rendered_text = str(claim_contract.get("summary") or "").strip()
        if claim_contract.get("disclosure_note"):
            rendered_text = f"{rendered_text} {claim_contract['disclosure_note']}"
        claims.append(
            {
                "claim_id": claim_contract["claim_id"],
                "section_id": claim_contract["section_id"],
                "rendered_text": rendered_text,
                "concept_keys": list(claim_contract.get("concept_keys") or []),
                "evidence_card_ids": evidence_card_ids,
                "graph_edge_ids": graph_edge_ids,
                "fact_ids": fact_ids,
                "assertion_ids": assertion_ids,
                "source_document_ids": source_document_ids,
                "support_level": claim_contract.get("support_level"),
                "review_policy_status": claim_contract.get("review_policy_status"),
                "disclosure_note": claim_contract.get("disclosure_note"),
            }
        )
        section_claim_ids.setdefault(claim_contract["section_id"], []).append(
            claim_contract["claim_id"]
        )

    claims_by_section: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        claims_by_section.setdefault(claim["section_id"], []).append(claim)

    sections: list[dict[str, Any]] = []
    markdown_parts = [
        f"# {harness.report_request['title']}",
        "",
        str(harness.report_request["goal"]),
    ]
    if harness.report_request.get("audience"):
        markdown_parts.extend(["", f"Audience: {harness.report_request['audience']}"])
    for section_id, section_plan in sections_by_id.items():
        body_lines = [section_plan.purpose, ""]
        for claim in claims_by_section.get(section_id, []):
            evidence_refs = " ".join(f"[{card_id}]" for card_id in claim["evidence_card_ids"])
            graph_refs = " ".join(f"[{edge_id}]" for edge_id in claim["graph_edge_ids"])
            ref_text = collapse_whitespace(" ".join([evidence_refs, graph_refs]))
            suffix = f" Evidence: {ref_text}." if ref_text else ""
            body_lines.append(f"- {claim['rendered_text']}{suffix}")
        body_markdown = "\n".join(body_lines).strip()
        sections.append(
            {
                "section_id": section_id,
                "title": section_plan.title,
                "body_markdown": body_markdown,
                "claim_ids": list(section_claim_ids.get(section_id, [])),
            }
        )
        markdown_parts.extend(["", f"## {section_plan.title}", "", body_markdown])

    markdown_parts.extend(["", "## Evidence Cards", ""])
    for card in harness.evidence_cards:
        excerpt = collapse_whitespace(card.excerpt) or "No excerpt captured."
        markdown_parts.append(
            f"- [{card.evidence_card_id}] {card.evidence_kind}"
            f" ({card.source_type or 'source'}): {excerpt}"
        )
    markdown = llm_draft_markdown or ("\n".join(markdown_parts).strip() + "\n")
    warnings = list(harness.warnings)
    if generator_mode == "llm_adapter" and not llm_draft_markdown:
        warnings.append(
            "LLM adapter mode was requested without an adapter draft; "
            "structured fallback rendered the draft."
        )

    draft = {
        "title": harness.report_request["title"],
        "goal": harness.report_request["goal"],
        "audience": harness.report_request.get("audience"),
        "target_length": harness.report_request["target_length"],
        "harness_task_id": harness_task_id,
        "generator_mode": generator_mode,
        "generator_model": generator_model,
        "used_fallback": generator_mode != "llm_adapter" or not llm_draft_markdown,
        "llm_adapter_contract": dict(harness.llm_adapter_contract),
        "document_refs": [
            row.model_dump(mode="json") for row in harness.source_plan.document_refs
        ],
        "required_concept_keys": list(harness.source_plan.required_concept_keys),
        "sections": sections,
        "claims": claims,
        "blocked_claims": blocked_claims,
        "evidence_cards": [
            card.model_dump(mode="json") for card in harness.evidence_cards
        ],
        "graph_context": [
            edge.model_dump(mode="json") for edge in harness.graph_context
        ],
        "markdown": markdown,
        "warnings": warnings,
    }
    derivation_package = apply_technical_report_derivation_links(draft)
    draft["success_metrics"] = [
        _success_metric(
            "claim_binding_preserved",
            "Ryan Lopopolo",
            all(claim["evidence_card_ids"] or claim["graph_edge_ids"] for claim in claims),
            "Rendered claims preserve evidence-card or graph-edge bindings.",
            {"claim_count": len(claims)},
        ),
        _success_metric(
            "unsupported_claims_blocked",
            "Armin Ronacher",
            True,
            "Claims without support are blocked instead of rendered as supported prose.",
            {"blocked_claim_count": len(blocked_claims)},
        ),
        _success_metric(
            "llm_adapter_pluggable",
            "Nate B. Jones",
            bool(harness.llm_adapter_contract),
            "The draft records the harness contract an external LLM adapter must consume.",
            {"generator_mode": generator_mode},
        ),
        _success_metric(
            "claim_derivations_frozen",
            "Nicolas Figay",
            bool(derivation_package.get("package_sha256"))
            and all(claim.get("derivation_sha256") for claim in draft["claims"]),
            "Each rendered claim is bound to a frozen derivation package hash.",
            {
                "evidence_package_sha256": derivation_package.get("package_sha256"),
                "claim_derivation_count": len(draft.get("claim_derivations") or []),
            },
        ),
    ]
    return TechnicalReportDraftPayload.model_validate(draft).model_dump(mode="json")


def _technical_report_verification_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _success_metric(
            "claim_traceability",
            "Ryan Lopopolo",
            summary["traceable_claim_ratio"] == 1.0
            and summary["unresolved_evidence_card_ref_count"] == 0
            and summary["unresolved_graph_edge_ref_count"] == 0,
            "Every rendered claim resolves to evidence cards and approved graph context.",
            {
                "traceable_claim_ratio": summary["traceable_claim_ratio"],
                "unresolved_evidence_card_ref_count": summary[
                    "unresolved_evidence_card_ref_count"
                ],
                "unresolved_graph_edge_ref_count": summary[
                    "unresolved_graph_edge_ref_count"
                ],
            },
        ),
        _success_metric(
            "explicit_context_gate",
            "Armin Ronacher",
            summary["context_blocker_count"] == 0
            and summary["missing_wake_context_count"] == 0,
            "Missing and schema-mismatched wake-up context is blocked by the verifier.",
            {
                "context_blocker_count": summary["context_blocker_count"],
                "missing_wake_context_count": summary["missing_wake_context_count"],
            },
        ),
        _success_metric(
            "graph_memory_governed",
            "Joshua Yu",
            summary["unapproved_graph_claim_count"] == 0,
            "Graph-backed claims use approved graph edges only.",
            {"graph_claim_count": summary["graph_claim_count"]},
        ),
        _success_metric(
            "owned_wake_context",
            "Nate B. Jones",
            summary["context_ref_count"] > 0 and summary["missing_wake_context_count"] == 0,
            "The draft is verified against the harness wake-up context.",
            {
                "context_ref_count": summary["context_ref_count"],
                "missing_wake_context_count": summary["missing_wake_context_count"],
            },
        ),
        _success_metric(
            "durable_platform_loop",
            "Steve Yegge",
            summary["claim_count"] > 0 and summary["evidence_card_count"] > 0,
            "The report loop produces reusable durable artifacts rather than one-off prose.",
            {
                "claim_count": summary["claim_count"],
                "evidence_card_count": summary["evidence_card_count"],
            },
        ),
        _success_metric(
            "frozen_evidence_package",
            "Nicolas Figay",
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
                "claims_with_derivation_hash_count": summary[
                    "claims_with_derivation_hash_count"
                ],
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
    ]


def verify_technical_report(
    draft_payload: dict[str, Any],
    *,
    max_unsupported_claim_count: int = 0,
    require_full_claim_traceability: bool = True,
    require_full_concept_coverage: bool = True,
    require_graph_edges_approved: bool = True,
    block_stale_context: bool = False,
) -> TechnicalReportVerificationOutcome:
    draft = TechnicalReportDraftPayload.model_validate(draft_payload)
    recomputed_derivation_package = build_technical_report_derivation_package(
        draft.model_dump(mode="json")
    )
    expected_package_sha256 = str(
        recomputed_derivation_package.get("package_sha256") or ""
    )
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
                    f"{claim.claim_id} derivation hash does not match recomputed "
                    "claim derivation."
                )
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
        unapproved_graph_refs = [
            edge for edge in graph_refs if edge.review_status != "approved"
        ]
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
        covered_required_concept_count / required_concept_count
        if required_concept_count
        else 1.0
    )
    graph_claim_count = sum(1 for claim in draft.claims if claim.graph_edge_ids)
    claims_with_evidence_package_hash_count = claim_count - missing_evidence_package_hash_count
    claims_with_derivation_hash_count = claim_count - missing_derivation_hash_count
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
    ):
        reasons.append(
            "Frozen evidence package and derivation hashes are required and must "
            "match recomputation."
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
        "draft_evidence_package_hash_present": bool(draft.evidence_package_sha256),
        "expected_evidence_package_sha256": expected_package_sha256,
        "missing_evidence_package_hash_count": missing_evidence_package_hash_count,
        "missing_derivation_hash_count": missing_derivation_hash_count,
        "evidence_package_mismatch_count": evidence_package_mismatch_count,
        "evidence_package_integrity_mismatch_count": evidence_package_integrity_mismatch_count,
        "derivation_integrity_mismatch_count": derivation_integrity_mismatch_count,
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
            }
        },
    )


def task_output_context_ref(
    *,
    ref_key: str,
    summary: str,
    task_id: UUID,
    schema_name: str | None,
    schema_version: str | None,
    output: dict[str, Any],
    source_updated_at,
    freshness_status: ContextFreshnessStatus | None,
) -> ContextRef:
    return ContextRef(
        ref_key=ref_key,
        ref_kind="task_output",
        summary=summary,
        task_id=task_id,
        schema_name=schema_name,
        schema_version=schema_version,
        observed_sha256=_payload_sha256(output),
        source_updated_at=source_updated_at,
        checked_at=utcnow(),
        freshness_status=freshness_status or ContextFreshnessStatus.FRESH,
    )
