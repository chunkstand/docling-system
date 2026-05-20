from __future__ import annotations

import threading
from collections.abc import Callable
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskAttempt, AgentTaskDependency, AgentTaskStatus
from app.services.agent_task_worker_finalization import current_attempt, write_failure_artifact
from app.services.storage import StorageService

logger = get_logger(__name__)
CurrentAttemptFunc = Callable[[Session, AgentTask], AgentTaskAttempt | None]


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
        task.updated_at = utcnow()
        updated += 1

    if updated:
        session.commit()
        logger.info("agent_tasks_unblocked", count=updated)

    return updated


def requeue_stale_agent_tasks(
    session: Session,
    storage_service: StorageService | None = None,
    *,
    current_attempt_func: CurrentAttemptFunc | None = None,
) -> int:
    active_current_attempt = current_attempt_func or current_attempt
    settings = get_settings()
    stale_before = utcnow() - timedelta(seconds=settings.worker_lease_timeout_seconds)
    stale_tasks = session.execute(
        select(AgentTask).where(
            AgentTask.status == AgentTaskStatus.PROCESSING.value,
            AgentTask.last_heartbeat_at.is_not(None),
            AgentTask.last_heartbeat_at < stale_before,
        )
    ).scalars()

    updated = 0
    for task in stale_tasks:
        attempt = active_current_attempt(session, task)
        if attempt is not None and attempt.status == "processing":
            attempt.status = "abandoned"
            attempt.completed_at = utcnow()
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
        task.updated_at = utcnow()
        if task.attempts >= settings.worker_max_attempts:
            task.status = AgentTaskStatus.FAILED.value
            task.completed_at = utcnow()
            failure_path = write_failure_artifact(
                storage_service,
                task,
                RuntimeError(task.error_message),
                failure_stage="stale_lease",
            )
            task.failure_artifact_path = str(failure_path) if failure_path is not None else None
        else:
            task.status = AgentTaskStatus.RETRY_WAIT.value
            task.next_attempt_at = utcnow()
        updated += 1

    if updated:
        session.commit()
        logger.info("stale_agent_tasks_requeued", count=updated)

    return updated


def claim_next_agent_task(session: Session, worker_id: str) -> AgentTask | None:
    now = utcnow()
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
    logger.info(
        "agent_task_claimed",
        task_id=str(task.id),
        task_type=task.task_type,
        worker_id=worker_id,
    )
    return task


def heartbeat_agent_task(session: Session, task: AgentTask) -> None:
    task.last_heartbeat_at = utcnow()
    task.updated_at = task.last_heartbeat_at
    session.commit()


@contextmanager
def agent_task_lease_heartbeat(task_id: UUID, *, worker_id: str | None):
    from app.db.session import get_session_factory

    settings = get_settings()
    interval_seconds = settings.worker_heartbeat_seconds
    if worker_id is None or interval_seconds <= 0:
        yield
        return

    session_factory = get_session_factory()
    stop_event = threading.Event()

    def _loop() -> None:
        while not stop_event.wait(interval_seconds):
            try:
                if not _refresh_agent_task_lease(session_factory, task_id, worker_id):
                    return
            except Exception as exc:
                logger.warning(
                    "agent_task_lease_heartbeat_failed",
                    task_id=str(task_id),
                    worker_id=worker_id,
                    error=str(exc),
                )

    heartbeat_thread = threading.Thread(
        target=_loop,
        name=f"agent-task-heartbeat-{task_id}",
        daemon=True,
    )
    heartbeat_thread.start()
    try:
        yield
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=max(1, interval_seconds))


def _refresh_agent_task_lease(session_factory, task_id: UUID, worker_id: str) -> bool:
    now = utcnow()
    with session_factory() as heartbeat_session:
        result = heartbeat_session.execute(
            update(AgentTask)
            .where(
                AgentTask.id == task_id,
                AgentTask.locked_by == worker_id,
                AgentTask.status == AgentTaskStatus.PROCESSING.value,
            )
            .values(last_heartbeat_at=now, updated_at=now)
        )
        heartbeat_session.commit()
        return bool(result.rowcount)
