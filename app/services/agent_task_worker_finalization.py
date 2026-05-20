from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskAttempt, AgentTaskStatus
from app.services.agent_task_attempt_metrics import derive_attempt_cost, derive_attempt_performance
from app.services.claim_support_policy_impacts import (
    refresh_claim_support_policy_change_impacts_for_replay_task,
)
from app.services.evidence import (
    persist_agent_task_provenance_export,
    refresh_technical_report_evidence_manifest,
)
from app.services.storage import StorageService

PROMOTABLE_SIDE_EFFECT_APPLIED_KEY = "_side_effect_status"
PROMOTABLE_SIDE_EFFECT_APPLIED_VALUE = "applied"
PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY = "_checkpointed_result"

CurrentAttemptFunc = Callable[[Session, AgentTask], AgentTaskAttempt | None]


def current_attempt(session: Session, task: AgentTask) -> AgentTaskAttempt | None:
    return session.execute(
        select(AgentTaskAttempt).where(
            AgentTaskAttempt.task_id == task.id,
            AgentTaskAttempt.attempt_number == task.attempts,
        )
    ).scalar_one_or_none()


def write_failure_artifact(
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
        "created_at": utcnow().isoformat(),
    }
    failure_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return failure_path


def is_retryable_agent_task_error(exc: Exception) -> bool:
    return not isinstance(exc, (HTTPException, ValueError, ValidationError))


def result_has_applied_promotable_side_effect(result: dict | None) -> bool:
    return (
        isinstance(result, dict)
        and result.get(PROMOTABLE_SIDE_EFFECT_APPLIED_KEY) == PROMOTABLE_SIDE_EFFECT_APPLIED_VALUE
        and isinstance(result.get(PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY), dict)
    )


def checkpoint_promotable_task_result(session: Session, task: AgentTask, result: dict) -> dict:
    checkpoint = {
        PROMOTABLE_SIDE_EFFECT_APPLIED_KEY: PROMOTABLE_SIDE_EFFECT_APPLIED_VALUE,
        PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY: dict(result or {}),
    }
    task.result_json = checkpoint
    task.updated_at = utcnow()
    session.commit()
    return dict(result or {})


def strip_promotable_side_effect_marker(result: dict) -> dict:
    if result_has_applied_promotable_side_effect(result):
        return dict(result.get(PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY) or {})
    sanitized = dict(result or {})
    sanitized.pop(PROMOTABLE_SIDE_EFFECT_APPLIED_KEY, None)
    sanitized.pop(PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY, None)
    return sanitized


def finalize_agent_task_success(
    session: Session,
    task: AgentTask,
    result: dict,
    *,
    storage_service: StorageService | None = None,
    current_attempt_func: CurrentAttemptFunc | None = None,
) -> None:
    active_current_attempt = current_attempt_func or current_attempt
    now = utcnow()
    sanitized_result = strip_promotable_side_effect_marker(result)
    task.locked_at = None
    task.locked_by = None
    task.last_heartbeat_at = None
    task.next_attempt_at = None
    task.status = AgentTaskStatus.COMPLETED.value
    task.result_json = sanitized_result
    task.error_message = None
    task.completed_at = now
    task.updated_at = now
    if task.failure_artifact_path and storage_service is not None:
        storage_service.delete_file_if_exists(Path(task.failure_artifact_path))
    task.failure_artifact_path = None

    if _technical_report_verification_passed(sanitized_result):
        evidence_manifest = refresh_technical_report_evidence_manifest(session, task_id=task.id)
        provenance_artifact = persist_agent_task_provenance_export(
            session,
            task_id=task.id,
            storage_service=storage_service,
        )
        payload = sanitized_result.get("payload")
        if isinstance(payload, dict):
            payload["evidence_manifest_id"] = str(evidence_manifest.id)
            payload["evidence_manifest_sha256"] = evidence_manifest.manifest_sha256
            payload["provenance_export_artifact_id"] = str(provenance_artifact.id)
            payload["provenance_export_sha256"] = (
                (provenance_artifact.payload_json or {}).get("frozen_export") or {}
            ).get("export_payload_sha256")
            task.result_json = sanitized_result

    _refresh_claim_support_replay_impacts_after_task_finalization(
        session,
        task_id=task.id,
        storage_service=storage_service,
    )

    attempt = active_current_attempt(session, task)
    if attempt is not None:
        attempt.status = "completed"
        attempt.result_json = sanitized_result
        attempt.cost_json = derive_attempt_cost(task, sanitized_result)
        attempt.performance_json = derive_attempt_performance(task, attempt, now)
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
    current_attempt_func: CurrentAttemptFunc | None = None,
) -> None:
    active_current_attempt = current_attempt_func or current_attempt
    settings = get_settings()
    now = utcnow()
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

    attempt = active_current_attempt(session, task)
    if attempt is not None:
        attempt.status = "failed"
        attempt.error_message = str(exc)
        attempt.result_json = {
            **(attempt.result_json or {}),
            "failure_type": exc.__class__.__name__,
            "failure_stage": failure_stage,
        }
        attempt.cost_json = derive_attempt_cost(task, attempt.result_json)
        attempt.performance_json = derive_attempt_performance(task, attempt, now)
        attempt.completed_at = now

    if is_retryable_agent_task_error(exc) and task.attempts < settings.worker_max_attempts:
        backoff_seconds = min(60, 2 ** max(task.attempts - 1, 0))
        task.status = AgentTaskStatus.RETRY_WAIT.value
        task.next_attempt_at = now + timedelta(seconds=backoff_seconds)
    else:
        task.status = AgentTaskStatus.FAILED.value
        task.completed_at = now

    failure_path = write_failure_artifact(
        storage_service,
        task,
        exc,
        failure_stage=failure_stage,
    )
    task.failure_artifact_path = str(failure_path) if failure_path is not None else None
    _refresh_claim_support_replay_impacts_after_task_finalization(
        session,
        task_id=task.id,
        storage_service=storage_service,
    )
    session.commit()


def _technical_report_verification_passed(result: dict) -> bool:
    if result.get("task_type") != "verify_technical_report":
        return False
    payload = result.get("payload")
    if not isinstance(payload, dict):
        return False
    verification = payload.get("verification")
    return isinstance(verification, dict) and verification.get("outcome") == "passed"


def _refresh_claim_support_replay_impacts_after_task_finalization(
    session: Session,
    *,
    task_id,
    storage_service: StorageService | None,
) -> None:
    if not hasattr(session, "execute"):
        return
    session.flush()
    refresh_claim_support_policy_change_impacts_for_replay_task(
        session,
        task_id,
        storage_service=storage_service,
        commit=False,
    )
