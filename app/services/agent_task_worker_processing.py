from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

import app.services.agent_task_worker_finalization as finalization_owner
import app.services.agent_task_worker_leases as lease_owner
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import AgentTask
from app.services.agent_task_actions import execute_agent_task_action
from app.services.agent_task_context import write_agent_task_context
from app.services.runtime import (
    get_process_identity,
    runtime_code_is_current,
    runtime_process_heartbeat,
)
from app.services.storage import StorageService

AgentTaskExecutor = Callable[[Session, AgentTask], dict]
logger = get_logger(__name__)


def process_agent_task(
    session: Session,
    task_id: UUID,
    storage_service: StorageService,
    *,
    executor: AgentTaskExecutor | None = None,
    lease_heartbeat_context=lease_owner.agent_task_lease_heartbeat,
    heartbeat_task_func=lease_owner.heartbeat_agent_task,
    execute_action_func=execute_agent_task_action,
    result_has_checkpoint_func=finalization_owner.result_has_applied_promotable_side_effect,
    strip_result_func=finalization_owner.strip_promotable_side_effect_marker,
    checkpoint_result_func=finalization_owner.checkpoint_promotable_task_result,
    write_context_func=write_agent_task_context,
    finalize_success_func=finalization_owner.finalize_agent_task_success,
    finalize_failure_func=finalization_owner.finalize_agent_task_failure,
    logger_override: Any = None,
) -> None:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task {task_id} does not exist.")

    active_logger = logger_override or logger
    with lease_heartbeat_context(task.id, worker_id=task.locked_by):
        try:
            failure_stage = "execute"
            active_logger.info(
                "agent_task_processing_started",
                task_id=str(task.id),
                task_type=task.task_type,
            )
            heartbeat_task_func(session, task)
            if result_has_checkpoint_func(task.result_json):
                result = strip_result_func(task.result_json or {})
            else:
                active_executor = executor or execute_action_func
                result = active_executor(session, task)
                if task.side_effect_level == "promotable":
                    result = checkpoint_result_func(session, task, result)
                    task = session.get(AgentTask, task_id) or task
            heartbeat_task_func(session, task)
            write_context_func(
                session,
                task,
                result,
                storage_service=storage_service,
            )
            failure_stage = "complete"
            finalize_success_func(session, task, result, storage_service=storage_service)
            active_logger.info(
                "agent_task_processing_completed",
                task_id=str(task.id),
                task_type=task.task_type,
            )
        except Exception as exc:
            session.rollback()
            task = session.get(AgentTask, task_id)
            if task is None:
                raise
            finalize_failure_func(
                session,
                task,
                exc,
                failure_stage=failure_stage,
                storage_service=storage_service,
            )
            active_logger.exception(
                "agent_task_processing_failed",
                task_id=str(task.id),
                task_type=task.task_type,
                error=str(exc),
            )


def run_agent_task_worker_loop(
    *,
    executor: AgentTaskExecutor | None = None,
    settings_func=get_settings,
    get_process_identity_func=get_process_identity,
    runtime_process_heartbeat_context=runtime_process_heartbeat,
    runtime_code_is_current_func=runtime_code_is_current,
    storage_service_factory=StorageService,
    unblock_ready_tasks_func=lease_owner.unblock_ready_agent_tasks,
    requeue_stale_tasks_func=lease_owner.requeue_stale_agent_tasks,
    claim_next_task_func=lease_owner.claim_next_agent_task,
    process_task_func=process_agent_task,
    sleep_func=time.sleep,
    logger_override: Any = None,
) -> None:
    from app.db.session import get_session_factory

    settings = settings_func()
    session_factory = get_session_factory()
    storage_service = storage_service_factory()
    worker_id = get_process_identity_func()
    active_logger = logger_override or logger
    with runtime_process_heartbeat_context(
        "agent_worker",
        worker_id,
        heartbeat_interval_seconds=max(getattr(settings, "worker_heartbeat_seconds", 30), 1),
    ) as registration:
        active_logger.info(
            "agent_worker_runtime_registered",
            worker_id=worker_id,
            code_fingerprint=registration.startup_code_fingerprint,
        )

        while True:
            if not runtime_code_is_current_func(registration.startup_code_fingerprint):
                active_logger.warning(
                    "agent_worker_exiting_stale_code",
                    worker_id=worker_id,
                    code_fingerprint=registration.startup_code_fingerprint,
                )
                return
            with session_factory() as session:
                unblock_ready_tasks_func(session)
                requeue_stale_tasks_func(session, storage_service=storage_service)
                task = claim_next_task_func(session, worker_id)
                if task is None:
                    sleep_func(settings.worker_poll_seconds)
                    continue

                process_task_func(
                    session=session,
                    task_id=task.id,
                    storage_service=storage_service,
                    executor=executor,
                )
