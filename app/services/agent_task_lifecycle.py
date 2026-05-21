from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskOutcome, AgentTaskStatus
from app.schemas.agent_task_core import (
    AgentTaskApprovalRequest,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskRejectionRequest,
)

DetailBuilder = Callable[[Session, AgentTask], AgentTaskDetailResponse]
NotFoundFactory = Callable[[UUID], HTTPException]
DependencyStatusReader = Callable[[Session, UUID], bool]


def create_agent_task_outcome(
    session: Session,
    task_id: UUID,
    payload: AgentTaskOutcomeCreateRequest,
    *,
    not_found_error_func: NotFoundFactory,
    to_outcome_response_func: Callable[[AgentTaskOutcome], AgentTaskOutcomeResponse],
) -> AgentTaskOutcomeResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise not_found_error_func(task_id)
    if task.status not in {
        AgentTaskStatus.COMPLETED.value,
        AgentTaskStatus.FAILED.value,
        AgentTaskStatus.REJECTED.value,
    }:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Only terminal tasks can receive outcome labels.",
            task_id=str(task_id),
            task_status=task.status,
        )
    existing = session.execute(
        select(AgentTaskOutcome).where(
            AgentTaskOutcome.task_id == task_id,
            AgentTaskOutcome.outcome_label == payload.outcome_label,
            AgentTaskOutcome.created_by == payload.created_by,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "agent_task_outcome_already_recorded",
            "This outcome label has already been recorded by that actor for this task.",
            task_id=str(task_id),
            outcome_label=payload.outcome_label,
            created_by=payload.created_by,
        )

    row = AgentTaskOutcome(
        task_id=task_id,
        outcome_label=payload.outcome_label,
        created_by=payload.created_by,
        note=payload.note,
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    session.commit()
    return to_outcome_response_func(row)


def approve_agent_task(
    session: Session,
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
    *,
    build_detail_func: DetailBuilder,
    has_incomplete_dependencies_func: DependencyStatusReader,
    not_found_error_func: NotFoundFactory,
) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise not_found_error_func(task_id)
    if not task.requires_approval:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task does not require approval.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.approved_at is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task has already been approved.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.rejected_at is not None or task.status == AgentTaskStatus.REJECTED.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Rejected tasks cannot be approved.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.status in {AgentTaskStatus.COMPLETED.value, AgentTaskStatus.FAILED.value}:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Completed or failed tasks cannot be approved.",
            task_id=str(task_id),
            task_status=task.status,
        )

    now = utcnow()
    task.approved_at = now
    task.approved_by = payload.approved_by
    task.approval_note = payload.approval_note
    task.updated_at = now
    task.status = (
        AgentTaskStatus.BLOCKED.value
        if has_incomplete_dependencies_func(session, task.id)
        else AgentTaskStatus.QUEUED.value
    )
    session.commit()
    return build_detail_func(session, task)


def reject_agent_task(
    session: Session,
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
    *,
    build_detail_func: DetailBuilder,
    not_found_error_func: NotFoundFactory,
) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise not_found_error_func(task_id)
    if not task.requires_approval:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task does not require approval.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.approved_at is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Approved tasks cannot be rejected.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.rejected_at is not None or task.status == AgentTaskStatus.REJECTED.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task has already been rejected.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.status in {
        AgentTaskStatus.COMPLETED.value,
        AgentTaskStatus.FAILED.value,
        AgentTaskStatus.PROCESSING.value,
        AgentTaskStatus.RETRY_WAIT.value,
        AgentTaskStatus.QUEUED.value,
    }:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Only pending approval tasks can be rejected.",
            task_id=str(task_id),
            task_status=task.status,
        )

    now = utcnow()
    task.status = AgentTaskStatus.REJECTED.value
    task.rejected_at = now
    task.rejected_by = payload.rejected_by
    task.rejection_note = payload.rejection_note
    task.updated_at = now
    task.completed_at = now
    task.next_attempt_at = None
    session.commit()
    return build_detail_func(session, task)
