from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_task_search_workflows import (
    EnqueueDocumentReprocessTaskInput,
    EnqueueDocumentReprocessTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.documents import reprocess_document


def _enqueue_document_reprocess_executor(
    session: Session,
    _task: AgentTask,
    payload: EnqueueDocumentReprocessTaskInput,
) -> dict:
    response = reprocess_document(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "reason": payload.reason,
        "reprocess": jsonable_encoder(response),
    }


def build_document_lifecycle_action_definitions(
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
            executor=_enqueue_document_reprocess_executor,
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
