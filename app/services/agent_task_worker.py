from __future__ import annotations

import json
import os
import socket
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import AgentTask, AgentTaskAttempt, AgentTaskDependency, AgentTaskStatus
from app.services.agent_task_actions import execute_agent_task_action
from app.services.storage import StorageService

AgentTaskExecutor = Callable[[Session, AgentTask], dict]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def get_worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


logger = get_logger(__name__)


def is_retryable_agent_task_error(exc: Exception) -> bool:
    return not isinstance(exc, (ValueError, ValidationError))


def _current_attempt(session: Session, task: AgentTask) -> AgentTaskAttempt | None:
    return session.execute(
        select(AgentTaskAttempt).where(
            AgentTaskAttempt.task_id == task.id,
            AgentTaskAttempt.attempt_number == task.attempts,
        )
    ).scalar_one_or_none()


def _write_failure_artifact(
    storage_service: StorageService | None,
    task: AgentTask,
    exc: Exception,
    *,
    failure_stage: str | None,
) -> Path | None:
    if storage_service is None:
        return None

    failure_path = storage_service.get_agent_task_failure_artifact_path(task.id)
    payload = {
        "schema_version": "1.0",
        "task_id": str(task.id),
        "task_type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "side_effect_level": task.side_effect_level,
        "requires_approval": task.requires_approval,
        "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
        "attempts": task.attempts,
        "failure_type": exc.__class__.__name__,
        "failure_stage": failure_stage,
        "error_message": str(exc),
        "workflow_version": task.workflow_version,
        "tool_version": task.tool_version,
        "prompt_version": task.prompt_version,
        "model": task.model,
        "model_settings": task.model_settings_json,
        "input": task.input_json,
        "result": task.result_json,
        "created_at": _utcnow().isoformat(),
    }
    failure_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return failure_path


def unblock_ready_agent_tasks(session: Session) -> int:
    blocked_tasks = session.execute(
        select(AgentTask).where(AgentTask.status == AgentTaskStatus.BLOCKED.value)
    ).scalars()

    updated = 0
    for task in blocked_tasks:
        incomplete_dependency_count = session.execute(
            select(AgentTaskDependency.id)
            .join(AgentTask, AgentTask.id == AgentTaskDependency.depends_on_task_id)
            .where(
                AgentTaskDependency.task_id == task.id,
                AgentTask.status != AgentTaskStatus.COMPLETED.value,
            )
            .limit(1)
        ).first()
        if incomplete_dependency_count is not None:
            continue
        task.status = (
            AgentTaskStatus.AWAITING_APPROVAL.value
            if task.requires_approval and task.approved_at is None
            else AgentTaskStatus.QUEUED.value
        )
        task.updated_at = _utcnow()
        updated += 1

    if updated:
        session.commit()
        logger.info("agent_tasks_unblocked", count=updated)

    return updated


def requeue_stale_agent_tasks(
    session: Session,
    storage_service: StorageService | None = None,
) -> int:
    settings = get_settings()
    stale_before = _utcnow() - timedelta(seconds=settings.worker_lease_timeout_seconds)
    stale_tasks = session.execute(
        select(AgentTask).where(
            AgentTask.status == AgentTaskStatus.PROCESSING.value,
            AgentTask.last_heartbeat_at.is_not(None),
            AgentTask.last_heartbeat_at < stale_before,
        )
    ).scalars()

    updated = 0
    for task in stale_tasks:
        attempt = _current_attempt(session, task)
        if attempt is not None and attempt.status == "processing":
            attempt.status = "abandoned"
            attempt.completed_at = _utcnow()
            attempt.error_message = attempt.error_message or "Task lease became stale."

        task.locked_at = None
        task.locked_by = None
        task.last_heartbeat_at = None
        task.error_message = task.error_message or "Task lease became stale."
        task.result_json = {
            **(task.result_json or {}),
            "failure_type": "RuntimeError",
            "failure_stage": "stale_lease",
        }
        task.updated_at = _utcnow()
        if task.attempts >= settings.worker_max_attempts:
            task.status = AgentTaskStatus.FAILED.value
            task.completed_at = _utcnow()
            failure_path = _write_failure_artifact(
                storage_service,
                task,
                RuntimeError(task.error_message),
                failure_stage="stale_lease",
            )
            task.failure_artifact_path = str(failure_path) if failure_path is not None else None
        else:
            task.status = AgentTaskStatus.RETRY_WAIT.value
            task.next_attempt_at = _utcnow()
        updated += 1

    if updated:
        session.commit()
        logger.info("stale_agent_tasks_requeued", count=updated)

    return updated


def claim_next_agent_task(session: Session, worker_id: str) -> AgentTask | None:
    now = _utcnow()
    eligible_query: Select[tuple[AgentTask]] = (
        select(AgentTask)
        .where(
            or_(
                AgentTask.status == AgentTaskStatus.QUEUED.value,
                and_(
                    AgentTask.status == AgentTaskStatus.RETRY_WAIT.value,
                    or_(AgentTask.next_attempt_at.is_(None), AgentTask.next_attempt_at <= now),
                ),
            )
        )
        .order_by(AgentTask.priority.asc(), AgentTask.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    task = session.execute(eligible_query).scalar_one_or_none()
    if task is None:
        session.rollback()
        return None

    task.status = AgentTaskStatus.PROCESSING.value
    task.locked_at = now
    task.locked_by = worker_id
    task.last_heartbeat_at = now
    task.started_at = task.started_at or now
    task.next_attempt_at = None
    task.updated_at = now
    task.attempts += 1
    attempt = AgentTaskAttempt(
        task_id=task.id,
        attempt_number=task.attempts,
        status="processing",
        worker_id=worker_id,
        input_json=task.input_json,
        result_json={},
        created_at=now,
        started_at=now,
    )
    session.add(attempt)
    session.commit()
    session.refresh(task)
    logger.info("agent_task_claimed", task_id=str(task.id), task_type=task.task_type, worker_id=worker_id)
    return task


def heartbeat_agent_task(session: Session, task: AgentTask) -> None:
    task.last_heartbeat_at = _utcnow()
    task.updated_at = task.last_heartbeat_at
    session.commit()


def finalize_agent_task_success(
    session: Session,
    task: AgentTask,
    result: dict,
    *,
    storage_service: StorageService | None = None,
) -> None:
    now = _utcnow()
    task.locked_at = None
    task.locked_by = None
    task.last_heartbeat_at = None
    task.next_attempt_at = None
    task.status = AgentTaskStatus.COMPLETED.value
    task.result_json = result
    task.error_message = None
    task.completed_at = now
    task.updated_at = now
    if task.failure_artifact_path and storage_service is not None:
        storage_service.delete_file_if_exists(Path(task.failure_artifact_path))
    task.failure_artifact_path = None

    attempt = _current_attempt(session, task)
    if attempt is not None:
        attempt.status = "completed"
        attempt.result_json = result
        attempt.error_message = None
        attempt.completed_at = now

    session.commit()


def finalize_agent_task_failure(
    session: Session,
    task: AgentTask,
    exc: Exception,
    *,
    failure_stage: str | None = None,
    storage_service: StorageService | None = None,
) -> None:
    settings = get_settings()
    now = _utcnow()
    task.locked_at = None
    task.locked_by = None
    task.last_heartbeat_at = None
    task.error_message = str(exc)
    task.result_json = {
        **(task.result_json or {}),
        "failure_type": exc.__class__.__name__,
        "failure_stage": failure_stage,
    }
    task.updated_at = now

    attempt = _current_attempt(session, task)
    if attempt is not None:
        attempt.status = "failed"
        attempt.error_message = str(exc)
        attempt.result_json = {
            **(attempt.result_json or {}),
            "failure_type": exc.__class__.__name__,
            "failure_stage": failure_stage,
        }
        attempt.completed_at = now

    if is_retryable_agent_task_error(exc) and task.attempts < settings.worker_max_attempts:
        backoff_seconds = min(60, 2 ** max(task.attempts - 1, 0))
        task.status = AgentTaskStatus.RETRY_WAIT.value
        task.next_attempt_at = now + timedelta(seconds=backoff_seconds)
    else:
        task.status = AgentTaskStatus.FAILED.value
        task.completed_at = now

    failure_path = _write_failure_artifact(
        storage_service,
        task,
        exc,
        failure_stage=failure_stage,
    )
    task.failure_artifact_path = str(failure_path) if failure_path is not None else None
    session.commit()


def process_agent_task(
    session: Session,
    task_id: UUID,
    storage_service: StorageService,
    *,
    executor: AgentTaskExecutor | None = None,
) -> None:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task {task_id} does not exist.")

    try:
        failure_stage = "execute"
        logger.info("agent_task_processing_started", task_id=str(task.id), task_type=task.task_type)
        heartbeat_agent_task(session, task)
        active_executor = executor or execute_agent_task_action
        result = active_executor(session, task)
        heartbeat_agent_task(session, task)
        failure_stage = "complete"
        finalize_agent_task_success(session, task, result, storage_service=storage_service)
        logger.info("agent_task_processing_completed", task_id=str(task.id), task_type=task.task_type)
    except Exception as exc:
        session.rollback()
        task = session.get(AgentTask, task_id)
        if task is None:
            raise
        finalize_agent_task_failure(
            session,
            task,
            exc,
            failure_stage=failure_stage,
            storage_service=storage_service,
        )
        logger.exception(
            "agent_task_processing_failed",
            task_id=str(task.id),
            task_type=task.task_type,
            error=str(exc),
        )

def run_agent_task_worker_loop(*, executor: AgentTaskExecutor | None = None) -> None:
    from app.db.session import get_session_factory

    settings = get_settings()
    session_factory = get_session_factory()
    storage_service = StorageService()
    worker_id = get_worker_identity()

    while True:
        with session_factory() as session:
            unblock_ready_agent_tasks(session)
            requeue_stale_agent_tasks(session, storage_service=storage_service)
            task = claim_next_agent_task(session, worker_id)
            if task is None:
                time.sleep(settings.worker_poll_seconds)
                continue

            process_agent_task(
                session=session,
                task_id=task.id,
                storage_service=storage_service,
                executor=executor,
            )
