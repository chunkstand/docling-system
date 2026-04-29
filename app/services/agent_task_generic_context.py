from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ContextFreshnessStatus,
    TaskContextEnvelope,
    TaskContextSummary,
)


def build_generic_task_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    del session
    now = utcnow()
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=ContextFreshnessStatus.FRESH,
        summary=TaskContextSummary(
            headline=f"{task.task_type} produced typed output.",
            decision="Output captured as typed context.",
        ),
        refs=[],
        output=payload,
    )


__all__ = ["build_generic_task_context"]
