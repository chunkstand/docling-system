from __future__ import annotations

from app.db.models import AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    DraftGraphPromotionsTaskInput,
    DraftGraphPromotionsTaskOutput,
    DraftOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskOutput,
    DraftSemanticGroundedDocumentTaskInput,
    DraftSemanticGroundedDocumentTaskOutput,
    DraftSemanticRegistryUpdateTaskInput,
    DraftSemanticRegistryUpdateTaskOutput,
    PrepareSemanticGenerationBriefTaskInput,
    PrepareSemanticGenerationBriefTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition, AgentTaskExecutor


def build_semantic_drafting_action_definitions(
    *,
    prepare_semantic_generation_brief_executor: AgentTaskExecutor,
    draft_semantic_registry_update_executor: AgentTaskExecutor,
    draft_ontology_extension_executor: AgentTaskExecutor,
    draft_graph_promotions_executor: AgentTaskExecutor,
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
        "draft_semantic_registry_update": AgentTaskActionDefinition(
            task_type="draft_semantic_registry_update",
            capability="semantic_memory",
            definition_kind="draft",
            description=(
                "Draft an additive semantic registry update from semantic triage or "
                "bootstrap candidate discovery."
            ),
            payload_model=DraftSemanticRegistryUpdateTaskInput,
            executor=draft_semantic_registry_update_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftSemanticRegistryUpdateTaskOutput,
            output_schema_name="draft_semantic_registry_update_output",
            output_schema_version="1.0",
            input_example={
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "rationale": "Add the missing synonym surfaced by semantic triage.",
                "candidate_ids": [],
            },
            context_builder_name="draft_semantic_registry_update",
        ),
        "draft_ontology_extension": AgentTaskActionDefinition(
            task_type="draft_ontology_extension",
            capability="semantic_memory",
            definition_kind="draft",
            description=(
                "Draft an additive ontology extension from semantic triage or bootstrap discovery."
            ),
            payload_model=DraftOntologyExtensionTaskInput,
            executor=draft_ontology_extension_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftOntologyExtensionTaskOutput,
            output_schema_name="draft_ontology_extension_output",
            output_schema_version="1.0",
            input_example={
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "rationale": "Extend the portable ontology from corpus evidence.",
                "candidate_ids": [],
            },
            context_builder_name="draft_ontology_extension",
        ),
        "draft_graph_promotions": AgentTaskActionDefinition(
            task_type="draft_graph_promotions",
            capability="semantic_memory",
            definition_kind="draft",
            description=(
                "Draft approved cross-document graph edges without mutating live graph "
                "memory."
            ),
            payload_model=DraftGraphPromotionsTaskInput,
            executor=draft_graph_promotions_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftGraphPromotionsTaskOutput,
            output_schema_name="draft_graph_promotions_output",
            output_schema_version="1.0",
            input_example={
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "edge_ids": [],
                "rationale": "Promote approved cross-document graph memory.",
                "min_score": 0.45,
            },
            context_builder_name="draft_graph_promotions",
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
