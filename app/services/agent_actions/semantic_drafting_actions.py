from __future__ import annotations

from app.db.models import AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    DraftSemanticGroundedDocumentTaskInput,
    DraftSemanticGroundedDocumentTaskOutput,
    PrepareSemanticGenerationBriefTaskInput,
    PrepareSemanticGenerationBriefTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition, AgentTaskExecutor


def build_semantic_drafting_action_definitions(
    *,
    prepare_semantic_generation_brief_executor: AgentTaskExecutor,
    draft_semantic_grounded_document_executor: AgentTaskExecutor,
) -> dict[str, AgentTaskActionDefinition]:
    return {
        "prepare_semantic_generation_brief": AgentTaskActionDefinition(
            task_type="prepare_semantic_generation_brief",
            capability="semantic_memory",
            definition_kind="workflow",
            description=(
                "Build a typed semantic generation brief and dossier for knowledge-brief drafting."
            ),
            payload_model=PrepareSemanticGenerationBriefTaskInput,
            executor=prepare_semantic_generation_brief_executor,
            output_model=PrepareSemanticGenerationBriefTaskOutput,
            output_schema_name="prepare_semantic_generation_brief_output",
            output_schema_version="1.0",
            input_example={
                "title": "Integration Governance Brief",
                "goal": "Summarize the knowledge base guidance on integration governance.",
                "audience": "Operators",
                "document_ids": ["00000000-0000-0000-0000-000000000000"],
                "target_length": "medium",
                "review_policy": "allow_candidate_with_disclosure",
                "include_shadow_candidates": False,
                "candidate_extractor_name": "concept_ranker_v1",
                "candidate_score_threshold": 0.34,
                "max_shadow_candidates": 8,
            },
            context_builder_name="prepare_semantic_generation_brief",
        ),
        "draft_semantic_grounded_document": AgentTaskActionDefinition(
            task_type="draft_semantic_grounded_document",
            capability="semantic_memory",
            definition_kind="draft",
            description=(
                "Draft a semantic-grounded knowledge brief from a typed semantic generation brief."
            ),
            payload_model=DraftSemanticGroundedDocumentTaskInput,
            executor=draft_semantic_grounded_document_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftSemanticGroundedDocumentTaskOutput,
            output_schema_name="draft_semantic_grounded_document_output",
            output_schema_version="1.0",
            input_example={"target_task_id": "00000000-0000-0000-0000-000000000000"},
            context_builder_name="draft_semantic_grounded_document",
        ),
    }
