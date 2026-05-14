from __future__ import annotations

from app.db.models import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_task_semantic_generation import (
    DraftSemanticGroundedDocumentTaskInput,
    DraftSemanticGroundedDocumentTaskOutput,
    PrepareSemanticGenerationBriefTaskInput,
    PrepareSemanticGenerationBriefTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context_resolvers import (
    resolve_required_dependency_task_output_context,
)
from app.services.semantic_generation import (
    draft_semantic_grounded_document,
    prepare_semantic_generation_brief,
)
from app.services.storage import StorageService


def _prepare_semantic_generation_brief_executor(
    session,
    task: AgentTask,
    payload: PrepareSemanticGenerationBriefTaskInput,
) -> dict:
    brief_payload = prepare_semantic_generation_brief(
        session,
        title=payload.title,
        goal=payload.goal,
        audience=payload.audience,
        document_ids=list(payload.document_ids),
        concept_keys=list(payload.concept_keys),
        category_keys=list(payload.category_keys),
        target_length=payload.target_length,
        review_policy=payload.review_policy,
        include_shadow_candidates=payload.include_shadow_candidates,
        candidate_extractor_name=payload.candidate_extractor_name,
        candidate_score_threshold=payload.candidate_score_threshold,
        max_shadow_candidates=payload.max_shadow_candidates,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_generation_brief",
        payload=brief_payload,
        storage_service=StorageService(),
        filename="semantic_generation_brief.json",
    )
    return {
        "brief": brief_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _draft_semantic_grounded_document_executor(
    session,
    task: AgentTask,
    payload: DraftSemanticGroundedDocumentTaskInput,
) -> dict:
    brief_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_semantic_generation_brief",
        expected_schema_name="prepare_semantic_generation_brief_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Grounded document drafts must declare the requested brief task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target semantic generation brief must be rerun after the context "
            "migration before drafting."
        ),
    )
    brief_output = PrepareSemanticGenerationBriefTaskOutput.model_validate(brief_context.output)
    draft_payload = draft_semantic_grounded_document(
        brief_output.brief.model_dump(mode="json"),
        brief_task_id=payload.target_task_id,
    )

    storage_service = StorageService()
    markdown_path = storage_service.get_agent_task_dir(task.id) / "semantic_grounded_document.md"
    markdown_path.write_text(draft_payload["markdown"])
    draft_payload["markdown_path"] = str(markdown_path)

    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_grounded_document_draft",
        payload=draft_payload,
        storage_service=storage_service,
        filename="semantic_grounded_document_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def build_semantic_drafting_action_definitions() -> dict[str, AgentTaskActionDefinition]:
    return {
        "prepare_semantic_generation_brief": AgentTaskActionDefinition(
            task_type="prepare_semantic_generation_brief",
            capability="semantic_memory",
            definition_kind="workflow",
            description=(
                "Build a typed semantic generation brief and dossier for knowledge-brief drafting."
            ),
            payload_model=PrepareSemanticGenerationBriefTaskInput,
            executor=_prepare_semantic_generation_brief_executor,
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
            executor=_draft_semantic_grounded_document_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftSemanticGroundedDocumentTaskOutput,
            output_schema_name="draft_semantic_grounded_document_output",
            output_schema_version="1.0",
            input_example={"target_task_id": "00000000-0000-0000-0000-000000000000"},
            context_builder_name="draft_semantic_grounded_document",
        ),
    }
