from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskStatus,
)
from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskDetailResponse,
    AgentTaskSummaryResponse,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _initial_task_status(*, requires_approval: bool, has_incomplete_dependencies: bool) -> str:
    if has_incomplete_dependencies:
        return AgentTaskStatus.BLOCKED.value
    if requires_approval:
        return AgentTaskStatus.AWAITING_APPROVAL.value
    return AgentTaskStatus.QUEUED.value


def _build_summary(task: AgentTask) -> AgentTaskSummaryResponse:
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


def _list_dependency_ids(session: Session, task_id: UUID) -> list[UUID]:
    return list(
        session.execute(
            select(AgentTaskDependency.depends_on_task_id)
            .where(AgentTaskDependency.task_id == task_id)
            .order_by(AgentTaskDependency.created_at, AgentTaskDependency.depends_on_task_id)
        ).scalars()
    )


def _count_task_attempts(session: Session, task_id: UUID) -> int:
    from app.db.models import AgentTaskAttempt

    return session.execute(
        select(func.count()).select_from(AgentTaskAttempt).where(AgentTaskAttempt.task_id == task_id)
    ).scalar_one()


def _count_task_artifacts(session: Session, task_id: UUID) -> int:
    return session.execute(
        select(func.count()).select_from(AgentTaskArtifact).where(AgentTaskArtifact.task_id == task_id)
    ).scalar_one()


def _build_detail(session: Session, task: AgentTask) -> AgentTaskDetailResponse:
    summary = _build_summary(task)
    return AgentTaskDetailResponse(
        **summary.model_dump(),
        dependency_task_ids=_list_dependency_ids(session, task.id),
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
        artifact_count=_count_task_artifacts(session, task.id),
        attempt_count=_count_task_attempts(session, task.id),
    )


def _validate_dependency_ids(session: Session, dependency_task_ids: list[UUID]) -> None:
    if not dependency_task_ids:
        return
    existing_ids = set(
        session.execute(select(AgentTask.id).where(AgentTask.id.in_(dependency_task_ids))).scalars()
    )
    missing_ids = [task_id for task_id in dependency_task_ids if task_id not in existing_ids]
    if missing_ids:
        missing_str = ", ".join(str(task_id) for task_id in missing_ids)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dependency task(s) not found: {missing_str}",
        )


def _validate_parent_task_id(session: Session, parent_task_id: UUID | None) -> None:
    if parent_task_id is None:
        return
    if session.get(AgentTask, parent_task_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent task not found: {parent_task_id}",
        )


def _incomplete_dependency_count(session: Session, dependency_task_ids: list[UUID]) -> int:
    if not dependency_task_ids:
        return 0
    return session.execute(
        select(func.count())
        .select_from(AgentTask)
        .where(
            AgentTask.id.in_(dependency_task_ids),
            AgentTask.status != AgentTaskStatus.COMPLETED.value,
        )
    ).scalar_one()


def _task_has_incomplete_dependencies(session: Session, task_id: UUID) -> bool:
    return (
        session.execute(
            select(func.count())
            .select_from(AgentTaskDependency)
            .join(AgentTask, AgentTask.id == AgentTaskDependency.depends_on_task_id)
            .where(
                AgentTaskDependency.task_id == task_id,
                AgentTask.status != AgentTaskStatus.COMPLETED.value,
            )
        ).scalar_one()
        > 0
    )


def create_agent_task(session: Session, payload: AgentTaskCreateRequest) -> AgentTaskDetailResponse:
    now = _utcnow()
    dependency_task_ids = list(dict.fromkeys(payload.dependency_task_ids))

    if payload.parent_task_id is not None and payload.parent_task_id in dependency_task_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot depend on its parent task explicitly.",
        )

    _validate_parent_task_id(session, payload.parent_task_id)
    _validate_dependency_ids(session, dependency_task_ids)
    has_incomplete_dependencies = _incomplete_dependency_count(session, dependency_task_ids) > 0

    task = AgentTask(
        task_type=payload.task_type,
        status=_initial_task_status(
            requires_approval=payload.requires_approval,
            has_incomplete_dependencies=has_incomplete_dependencies,
        ),
        priority=payload.priority,
        side_effect_level=payload.side_effect_level,
        requires_approval=payload.requires_approval,
        parent_task_id=payload.parent_task_id,
        input_json=payload.input,
        result_json={},
        workflow_version=payload.workflow_version,
        tool_version=payload.tool_version,
        prompt_version=payload.prompt_version,
        model=payload.model,
        model_settings_json=payload.model_settings,
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    session.flush()

    for dependency_task_id in dependency_task_ids:
        session.add(
            AgentTaskDependency(
                task_id=task.id,
                depends_on_task_id=dependency_task_id,
                created_at=now,
            )
        )

    session.commit()
    return _build_detail(session, task)


def list_agent_tasks(
    session: Session,
    *,
    statuses: list[str] | None = None,
    limit: int = 50,
) -> list[AgentTaskSummaryResponse]:
    statement = select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit)
    if statuses:
        statement = statement.where(AgentTask.status.in_(statuses))
    return [_build_summary(task) for task in session.execute(statement).scalars().all()]


def get_agent_task_detail(session: Session, task_id: UUID) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    return _build_detail(session, task)


def approve_agent_task(
    session: Session,
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    if not task.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task does not require approval.",
        )
    if task.approved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task has already been approved.",
        )
    if task.status in {AgentTaskStatus.COMPLETED.value, AgentTaskStatus.FAILED.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed or failed tasks cannot be approved.",
        )

    now = _utcnow()
    task.approved_at = now
    task.approved_by = payload.approved_by
    task.approval_note = payload.approval_note
    task.updated_at = now
    task.status = (
        AgentTaskStatus.BLOCKED.value
        if _task_has_incomplete_dependencies(session, task.id)
        else AgentTaskStatus.QUEUED.value
    )
    session.commit()
    return _build_detail(session, task)
