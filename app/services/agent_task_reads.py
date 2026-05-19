from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskAttempt,
    AgentTaskDependency,
    AgentTaskOutcome,
)
from app.schemas.agent_task_core import (
    AgentTaskArtifactResponse,
    AgentTaskDependencyResponse,
    AgentTaskDetailResponse,
    AgentTaskOutcomeResponse,
    AgentTaskSummaryResponse,
    AgentTaskTraceExportResponse,
    TaskContextEnvelope,
)
from app.services.agent_task_artifacts import list_agent_task_artifacts
from app.services.agent_task_context import (
    get_agent_task_context,
    get_agent_task_context_artifact,
)
from app.services.agent_task_verifications import (
    count_agent_task_verifications,
    list_agent_task_verifications,
)


def agent_task_not_found(task_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "agent_task_not_found",
        "Agent task not found.",
        task_id=str(task_id),
    )


def build_agent_task_summary(task: AgentTask) -> AgentTaskSummaryResponse:
    return AgentTaskSummaryResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        side_effect_level=task.side_effect_level,
        requires_approval=task.requires_approval,
        parent_task_id=task.parent_task_id,
        workflow_version=task.workflow_version,
        tool_version=task.tool_version,
        prompt_version=task.prompt_version,
        model=task.model,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


def list_dependency_ids(session: Session, task_id: UUID) -> list[UUID]:
    return list(
        session.execute(
            select(AgentTaskDependency.depends_on_task_id)
            .where(AgentTaskDependency.task_id == task_id)
            .order_by(AgentTaskDependency.created_at, AgentTaskDependency.depends_on_task_id)
        ).scalars()
    )


def list_dependency_edges(session: Session, task_id: UUID) -> list[AgentTaskDependencyResponse]:
    rows = (
        session.execute(
            select(AgentTaskDependency)
            .where(AgentTaskDependency.task_id == task_id)
            .order_by(AgentTaskDependency.created_at, AgentTaskDependency.depends_on_task_id)
        )
        .scalars()
        .all()
    )
    return [
        AgentTaskDependencyResponse(
            task_id=row.depends_on_task_id,
            dependency_kind=row.dependency_kind,
        )
        for row in rows
    ]


def count_task_attempts(session: Session, task_id: UUID) -> int:
    return session.execute(
        select(func.count())
        .select_from(AgentTaskAttempt)
        .where(AgentTaskAttempt.task_id == task_id)
    ).scalar_one()


def count_task_artifacts(session: Session, task_id: UUID) -> int:
    return session.execute(
        select(func.count())
        .select_from(AgentTaskArtifact)
        .where(AgentTaskArtifact.task_id == task_id)
    ).scalar_one()


def list_task_artifacts(session: Session, task_id: UUID) -> list[AgentTaskArtifactResponse]:
    return list_agent_task_artifacts(session, task_id, limit=20)


def to_outcome_response(row: AgentTaskOutcome) -> AgentTaskOutcomeResponse:
    return AgentTaskOutcomeResponse(
        outcome_id=row.id,
        task_id=row.task_id,
        outcome_label=row.outcome_label,
        created_by=row.created_by,
        note=row.note,
        created_at=row.created_at,
    )


def count_task_outcomes(session: Session, task_id: UUID) -> int:
    return session.execute(
        select(func.count())
        .select_from(AgentTaskOutcome)
        .where(AgentTaskOutcome.task_id == task_id)
    ).scalar_one()


def list_task_outcomes(session: Session, task_id: UUID) -> list[AgentTaskOutcomeResponse]:
    rows = (
        session.execute(
            select(AgentTaskOutcome)
            .where(AgentTaskOutcome.task_id == task_id)
            .order_by(AgentTaskOutcome.created_at.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )
    return [to_outcome_response(row) for row in rows]


def build_agent_task_detail(session: Session, task: AgentTask) -> AgentTaskDetailResponse:
    summary = build_agent_task_summary(task)
    context_envelope: TaskContextEnvelope | None = None
    context_artifact_id: UUID | None = None
    try:
        context_artifact = get_agent_task_context_artifact(session, task.id)
        context_artifact_id = context_artifact.id
        context_envelope = get_agent_task_context(session, task.id)
    except HTTPException:
        context_envelope = None
    return AgentTaskDetailResponse(
        **summary.model_dump(),
        dependency_task_ids=list_dependency_ids(session, task.id),
        dependency_edges=list_dependency_edges(session, task.id),
        input=task.input_json,
        result=task.result_json,
        model_settings=task.model_settings_json,
        error_message=task.error_message,
        failure_artifact_path=task.failure_artifact_path,
        attempts=task.attempts,
        locked_at=task.locked_at,
        locked_by=task.locked_by,
        last_heartbeat_at=task.last_heartbeat_at,
        next_attempt_at=task.next_attempt_at,
        approved_at=task.approved_at,
        approved_by=task.approved_by,
        approval_note=task.approval_note,
        rejected_at=task.rejected_at,
        rejected_by=task.rejected_by,
        rejection_note=task.rejection_note,
        artifact_count=count_task_artifacts(session, task.id),
        attempt_count=count_task_attempts(session, task.id),
        verification_count=count_agent_task_verifications(session, task.id),
        outcome_count=count_task_outcomes(session, task.id),
        context_summary=context_envelope.summary if context_envelope else None,
        context_refs=context_envelope.refs if context_envelope else [],
        context_artifact_id=context_artifact_id,
        context_freshness_status=context_envelope.freshness_status if context_envelope else None,
        artifacts=list_task_artifacts(session, task.id),
        verifications=list_agent_task_verifications(session, task.id),
        outcomes=list_task_outcomes(session, task.id),
    )


def list_agent_tasks(
    session: Session,
    *,
    statuses: list[str] | None = None,
    limit: int = 50,
) -> list[AgentTaskSummaryResponse]:
    statement = select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit)
    if statuses:
        statement = statement.where(AgentTask.status.in_(statuses))
    return [build_agent_task_summary(task) for task in session.execute(statement).scalars().all()]


def get_agent_task_detail(
    session: Session,
    task_id: UUID,
    *,
    not_found_error_func=agent_task_not_found,
) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise not_found_error_func(task_id)
    return build_agent_task_detail(session, task)


def list_agent_task_outcomes(
    session: Session,
    task_id: UUID,
    *,
    limit: int = 20,
    not_found_error_func=agent_task_not_found,
) -> list[AgentTaskOutcomeResponse]:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise not_found_error_func(task_id)
    rows = (
        session.execute(
            select(AgentTaskOutcome)
            .where(AgentTaskOutcome.task_id == task_id)
            .order_by(AgentTaskOutcome.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [to_outcome_response(row) for row in rows]


def export_agent_task_traces(
    session: Session,
    *,
    limit: int = 50,
    workflow_version: str | None = None,
    task_type: str | None = None,
    build_detail_func=build_agent_task_detail,
) -> AgentTaskTraceExportResponse:
    statement = select(AgentTask).order_by(AgentTask.created_at.desc())
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    tasks = session.execute(statement.limit(limit)).scalars().all()
    traces = [build_detail_func(session, task) for task in tasks]
    return AgentTaskTraceExportResponse(
        export_count=len(traces),
        workflow_version=workflow_version,
        task_type=task_type,
        traces=traces,
    )
