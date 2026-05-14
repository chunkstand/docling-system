from __future__ import annotations

from app.db.models import AgentTaskSideEffectLevel
from app.schemas.agent_task_reports import (
    BuildReportEvidenceCardsTaskInput,
    BuildReportEvidenceCardsTaskOutput,
    DraftTechnicalReportTaskInput,
    DraftTechnicalReportTaskOutput,
    EvaluateDocumentGenerationContextPackTaskInput,
    EvaluateDocumentGenerationContextPackTaskOutput,
    PlanTechnicalReportTaskInput,
    PlanTechnicalReportTaskOutput,
    PrepareReportAgentHarnessTaskInput,
    PrepareReportAgentHarnessTaskOutput,
    VerifyTechnicalReportTaskInput,
    VerifyTechnicalReportTaskOutput,
)
from app.services.agent_actions.report_context_pack import (
    evaluate_document_generation_context_pack_executor,
)
from app.services.agent_actions.report_drafting import (
    draft_technical_report_executor,
    verify_technical_report_executor,
)
from app.services.agent_actions.report_evidence import (
    build_report_evidence_cards_executor,
    prepare_report_agent_harness_executor,
)
from app.services.agent_actions.report_planning import (
    plan_technical_report_executor,
)
from app.services.agent_actions.types import AgentTaskActionDefinition


def build_report_action_definitions() -> dict[str, AgentTaskActionDefinition]:
    return {
        "plan_technical_report": AgentTaskActionDefinition(
            task_type="plan_technical_report",
            capability="technical_reports",
            definition_kind="workflow",
            description=(
                "Plan a technical report from semantic evidence, graph memory, "
                "and retrieval requirements."
            ),
            payload_model=PlanTechnicalReportTaskInput,
            executor=plan_technical_report_executor,
            output_model=PlanTechnicalReportTaskOutput,
            output_schema_name="plan_technical_report_output",
            output_schema_version="1.0",
            input_example={
                "title": "Integration Governance Technical Report",
                "goal": "Write a technical report grounded in ingested integration evidence.",
                "audience": "Operators",
                "document_ids": ["00000000-0000-0000-0000-000000000000"],
                "target_length": "medium",
                "review_policy": "allow_candidate_with_disclosure",
            },
            context_builder_name="plan_technical_report",
        ),
        "build_report_evidence_cards": AgentTaskActionDefinition(
            task_type="build_report_evidence_cards",
            capability="technical_reports",
            definition_kind="workflow",
            description="Bind a technical report plan to typed evidence cards and graph refs.",
            payload_model=BuildReportEvidenceCardsTaskInput,
            executor=build_report_evidence_cards_executor,
            output_model=BuildReportEvidenceCardsTaskOutput,
            output_schema_name="build_report_evidence_cards_output",
            output_schema_version="1.0",
            input_example={"target_task_id": "00000000-0000-0000-0000-000000000000"},
            context_builder_name="build_report_evidence_cards",
        ),
        "prepare_report_agent_harness": AgentTaskActionDefinition(
            task_type="prepare_report_agent_harness",
            capability="technical_reports",
            definition_kind="workflow",
            description=(
                "Package the LLM wake-up context with tools, skills, evidence cards, "
                "graph memory, and verifier gates."
            ),
            payload_model=PrepareReportAgentHarnessTaskInput,
            executor=prepare_report_agent_harness_executor,
            output_model=PrepareReportAgentHarnessTaskOutput,
            output_schema_name="prepare_report_agent_harness_output",
            output_schema_version="1.0",
            input_example={"target_task_id": "00000000-0000-0000-0000-000000000000"},
            context_builder_name="prepare_report_agent_harness",
        ),
        "evaluate_document_generation_context_pack": AgentTaskActionDefinition(
            task_type="evaluate_document_generation_context_pack",
            capability="technical_reports",
            definition_kind="verifier",
            description=(
                "Evaluate the reusable document-generation context pack before report drafting."
            ),
            payload_model=EvaluateDocumentGenerationContextPackTaskInput,
            executor=evaluate_document_generation_context_pack_executor,
            output_model=EvaluateDocumentGenerationContextPackTaskOutput,
            output_schema_name="evaluate_document_generation_context_pack_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "min_traceable_claim_ratio": 1.0,
                "min_context_ref_count": 1,
                "max_blocked_step_count": 0,
                "require_source_evidence_packages": True,
                "require_fresh_context": False,
            },
            context_builder_name="evaluate_document_generation_context_pack",
        ),
        "draft_technical_report": AgentTaskActionDefinition(
            task_type="draft_technical_report",
            capability="technical_reports",
            definition_kind="draft",
            description="Draft a verification-ready technical report from a report agent harness.",
            payload_model=DraftTechnicalReportTaskInput,
            executor=draft_technical_report_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftTechnicalReportTaskOutput,
            output_schema_name="draft_technical_report_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "generator_mode": "structured_fallback",
            },
            context_builder_name="draft_technical_report",
        ),
        "verify_technical_report": AgentTaskActionDefinition(
            task_type="verify_technical_report",
            capability="technical_reports",
            definition_kind="verifier",
            description=(
                "Verify technical report claim traceability, graph approval, citations, "
                "and wake-up context."
            ),
            payload_model=VerifyTechnicalReportTaskInput,
            executor=verify_technical_report_executor,
            output_model=VerifyTechnicalReportTaskOutput,
            output_schema_name="verify_technical_report_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "max_unsupported_claim_count": 0,
                "require_full_claim_traceability": True,
                "require_full_concept_coverage": True,
                "require_graph_edges_approved": True,
                "block_stale_context": False,
            },
            context_builder_name="verify_technical_report",
        ),
    }
