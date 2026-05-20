from __future__ import annotations

import time
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

import app.services.agent_task_worker_finalization as finalization_owner
import app.services.agent_task_worker_leases as lease_owner
import app.services.agent_task_worker_processing as processing_owner
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
PROMOTABLE_SIDE_EFFECT_APPLIED_KEY = finalization_owner.PROMOTABLE_SIDE_EFFECT_APPLIED_KEY
PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY = finalization_owner.PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY
is_retryable_agent_task_error = finalization_owner.is_retryable_agent_task_error
unblock_ready_agent_tasks = lease_owner.unblock_ready_agent_tasks
requeue_stale_agent_tasks = lease_owner.requeue_stale_agent_tasks
claim_next_agent_task = lease_owner.claim_next_agent_task
heartbeat_agent_task = lease_owner.heartbeat_agent_task
agent_task_lease_heartbeat = lease_owner.agent_task_lease_heartbeat
finalize_agent_task_success = finalization_owner.finalize_agent_task_success
finalize_agent_task_failure = finalization_owner.finalize_agent_task_failure


def process_agent_task(
    session: Session,
    task_id: UUID,
    storage_service: StorageService,
    *,
    executor: AgentTaskExecutor | None = None,
) -> None:
    return processing_owner.process_agent_task(
        session,
        task_id,
        storage_service,
        executor=executor,
        lease_heartbeat_context=agent_task_lease_heartbeat,
        heartbeat_task_func=heartbeat_agent_task,
        execute_action_func=execute_agent_task_action,
        result_has_checkpoint_func=finalization_owner.result_has_applied_promotable_side_effect,
        strip_result_func=finalization_owner.strip_promotable_side_effect_marker,
        checkpoint_result_func=finalization_owner.checkpoint_promotable_task_result,
        write_context_func=write_agent_task_context,
        finalize_success_func=finalize_agent_task_success,
        finalize_failure_func=finalize_agent_task_failure,
        logger_override=logger,
    )


def run_agent_task_worker_loop(*, executor: AgentTaskExecutor | None = None) -> None:
    return processing_owner.run_agent_task_worker_loop(
        executor=executor,
        settings_func=get_settings,
        get_process_identity_func=get_process_identity,
        runtime_process_heartbeat_context=runtime_process_heartbeat,
        runtime_code_is_current_func=runtime_code_is_current,
        storage_service_factory=StorageService,
        unblock_ready_tasks_func=unblock_ready_agent_tasks,
        requeue_stale_tasks_func=requeue_stale_agent_tasks,
        claim_next_task_func=claim_next_agent_task,
        process_task_func=process_agent_task,
        sleep_func=time.sleep,
        logger_override=logger,
    )
