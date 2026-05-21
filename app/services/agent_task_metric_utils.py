from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskAttempt,
    AgentTaskOutcome,
    AgentTaskVerification,
)


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = max(0, min(len(ordered) - 1, ceil(percentile_value * len(ordered)) - 1))
    return ordered[index]


def median(values: list[float]) -> float | None:
    return percentile(values, 0.5)


def bucket_start(value: datetime, bucket: str) -> datetime:
    if bucket == "week":
        start_date: date = value.date() - timedelta(days=value.weekday())
    else:
        start_date = value.date()
    return datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)


def task_select_statement(
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
    task_types: tuple[str, ...] | None = None,
):
    statement = select(AgentTask)
    if task_types is not None:
        statement = statement.where(AgentTask.task_type.in_(task_types))
    elif task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return statement


def task_id_select_statement(
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
    task_types: tuple[str, ...] | None = None,
):
    statement = select(AgentTask.id)
    if task_types is not None:
        statement = statement.where(AgentTask.task_type.in_(task_types))
    elif task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return statement


def list_filtered_tasks(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
    task_types: tuple[str, ...] | None = None,
) -> list[AgentTask]:
    return (
        session.execute(
            task_select_statement(
                task_type=task_type,
                workflow_version=workflow_version,
                task_types=task_types,
            )
        )
        .scalars()
        .all()
    )


def list_task_attempt_rows(
    session: Session,
    *,
    task_ids: set[UUID] | None = None,
    task_id_select=None,
) -> list[AgentTaskAttempt]:
    statement = select(AgentTaskAttempt)
    if task_ids is not None:
        if not task_ids:
            return []
        statement = statement.where(AgentTaskAttempt.task_id.in_(task_ids))
    elif task_id_select is not None:
        statement = statement.where(AgentTaskAttempt.task_id.in_(task_id_select))
    return session.execute(statement).scalars().all()


def list_task_outcome_rows(
    session: Session,
    *,
    task_ids: set[UUID] | None = None,
) -> list[AgentTaskOutcome]:
    statement = select(AgentTaskOutcome)
    if task_ids is not None:
        if not task_ids:
            return []
        statement = statement.where(AgentTaskOutcome.task_id.in_(task_ids))
    return session.execute(statement).scalars().all()


def list_task_trend_rows(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> list[tuple[UUID, datetime, str]]:
    statement = select(AgentTask.id, AgentTask.created_at, AgentTask.status)
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return session.execute(statement).all()


def list_verification_trend_rows(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> list[tuple[datetime, str]]:
    statement = select(AgentTaskVerification.created_at, AgentTaskVerification.outcome).join(
        AgentTask, AgentTask.id == AgentTaskVerification.target_task_id
    )
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return session.execute(statement).all()


def list_approval_trend_rows(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> list[tuple[datetime | None, datetime | None]]:
    statement = select(AgentTask.approved_at, AgentTask.rejected_at)
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return session.execute(statement).all()


def task_ids(tasks: list[AgentTask]) -> set[UUID]:
    return {task.id for task in tasks}


def float_value(payload: dict, key: str) -> float:
    try:
        return float(payload.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def int_value(payload: dict, key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0
