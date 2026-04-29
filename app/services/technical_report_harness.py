from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.coercion import unique_strings as _unique_strings
from app.schemas.agent_tasks import (
    ContextFreshnessStatus,
    ContextRef,
    ReportAgentHarnessPayload,
    TechnicalReportEvidenceBundlePayload,
    TechnicalReportSkillContract,
    TechnicalReportToolContract,
)
from app.services.technical_report_context_pack import build_document_generation_context_pack
from app.services.technical_report_shared import expert_alignment, success_metric


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
                "Fetch typed report-plan, evidence-card, harness, draft, or verification artifacts."
            ),
            access_pattern="GET /agent-tasks/{task_id}/artifacts/{artifact_id}",
            input_contract={"task_id": "uuid", "artifact_id": "uuid"},
            output_contract={"payload": "typed artifact json"},
            required_capability="agent_tasks:read",
        ).model_dump(mode="json"),
        TechnicalReportToolContract(
            tool_name="search_corpus",
            purpose=(
                "Run additional bounded corpus search when a planned section has missing support."
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
    release_readiness_assessments: list[dict[str, Any]] | None = None,
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
    release_readiness_assessment_refs = list(release_readiness_assessments or [])
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
            "document_ids": [str(document_ref.document_id) for document_ref in plan.document_refs],
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
            "next_task_type": "evaluate_document_generation_context_pack",
            "blocked_steps": blocked_steps,
        },
        "context_refs": context_refs,
        "allowed_tools": _default_allowed_tools(),
        "required_skills": _default_required_skills(),
        "retrieval_plan": list(evidence_bundle.retrieval_index),
        "evidence_cards": [card.model_dump(mode="json") for card in evidence_bundle.evidence_cards],
        "search_evidence_package_exports": list(evidence_bundle.search_evidence_package_exports),
        "release_readiness_assessments": release_readiness_assessment_refs,
        "graph_context": [edge.model_dump(mode="json") for edge in evidence_bundle.graph_context],
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
            "require_frozen_source_evidence": True,
            "require_release_readiness_assessments": True,
            "block_stale_context": False,
        },
        "llm_adapter_contract": {
            "primary_context_schema": "document_generation_context_pack",
            "primary_context_ref": (
                f"agent_task:{harness_task_id}:artifact:document_generation_context_pack"
            ),
            "source_harness_ref": f"agent_task:{harness_task_id}:artifact:report_agent_harness",
            "harness_context_refs": context_refs,
            "required_output_schema": "draft_technical_report_output",
            "must_preserve_fields": [
                "claim_id",
                "section_id",
                "evidence_card_ids",
                "graph_edge_ids",
                "source_evidence_package_export_ids",
                "source_search_request_ids",
                "source_search_request_result_ids",
                "source_evidence_match_keys",
                "source_evidence_match_status",
                "source_locator",
                "chunk_id",
                "table_id",
                "figure_id",
                "fact_ids",
                "assertion_ids",
                "source_document_ids",
            ],
            "allowed_tool_names": [tool["tool_name"] for tool in _default_allowed_tools()],
            "required_skill_names": [skill["skill_name"] for skill in _default_required_skills()],
        },
        "source_plan": plan.model_dump(mode="json"),
        "warnings": _unique_strings([*plan.warnings, *evidence_bundle.warnings]),
        "expert_alignment": expert_alignment(),
    }
    harness["success_metrics"] = [
        success_metric(
            "wake_up_packet_complete",
            "Jerry Liu",
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
        success_metric(
            "owned_context",
            "Jerry Liu",
            bool(context_refs),
            "The harness carries upstream context refs with freshness state.",
            {"context_ref_count": len(context_refs)},
        ),
        success_metric(
            "explicit_tool_surface",
            "Jon Bratseth",
            all(tool.get("access_pattern") for tool in harness["allowed_tools"]),
            "Every allowed tool has an explicit access pattern and contract.",
            {"tool_names": [tool["tool_name"] for tool in harness["allowed_tools"]]},
        ),
        success_metric(
            "platform_packet",
            "Jerry Liu",
            harness["schema_name"] == "report_agent_harness",
            "The report workflow compacts state into a reusable harness artifact.",
            {"schema_version": harness["schema_version"]},
        ),
    ]
    context_pack = build_document_generation_context_pack(
        harness,
        release_readiness_assessments=release_readiness_assessment_refs,
    )
    harness["document_generation_context_pack"] = context_pack
    harness["llm_adapter_contract"]["context_pack_sha256"] = context_pack["context_pack_sha256"]
    return ReportAgentHarnessPayload.model_validate(harness).model_dump(mode="json")
