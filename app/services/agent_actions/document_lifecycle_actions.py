from __future__ import annotations

from app.db.models import AgentTaskSideEffectLevel
from app.schemas.agent_task_search_workflows import (
    EnqueueDocumentReprocessTaskInput,
    EnqueueDocumentReprocessTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition, AgentTaskExecutor


def build_document_lifecycle_action_definitions(
    *,
    enqueue_document_reprocess_executor: AgentTaskExecutor,
) -> dict[str, AgentTaskActionDefinition]:
    return {
        "enqueue_document_reprocess": AgentTaskActionDefinition(
            task_type="enqueue_document_reprocess",
            capability="document_lifecycle",
            definition_kind="promotion",
            description=(
                "Queue a new processing run for an existing document after explicit approval."
            ),
            payload_model=EnqueueDocumentReprocessTaskInput,
            executor=enqueue_document_reprocess_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=EnqueueDocumentReprocessTaskOutput,
            output_schema_name="enqueue_document_reprocess_output",
            output_schema_version="1.0",
            input_example={
                "document_id": "00000000-0000-0000-0000-000000000000",
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Triaged replay regression needs a fresh parse.",
            },
            context_builder_name="generic",
        )
    }
