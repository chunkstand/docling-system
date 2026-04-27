from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskAttempt, AgentTaskDependency, AgentTaskStatus
from app.services.agent_task_actions import execute_agent_task_action
from app.services.agent_task_context import write_agent_task_context
from app.services.evidence import (
    persist_agent_task_provenance_export,
    refresh_technical_report_evidence_manifest,
)
from app.services.runtime import (
    get_process_identity,
    register_runtime_process,
    runtime_code_is_current,
)
from app.services.storage import StorageService

AgentTaskExecutor = Callable[[Session, AgentTask], dict]
logger = get_logger(__name__)
PROMOTABLE_SIDE_EFFECT_APPLIED_KEY = "_side_effect_status"
PROMOTABLE_SIDE_EFFECT_APPLIED_VALUE = "applied"
PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY = "_checkpointed_result"


def is_retryable_agent_task_error(exc: Exception) -> bool:
    return not isinstance(exc, (HTTPException, ValueError, ValidationError))


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
        "created_at": utcnow().isoformat(),
    }
    failure_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return failure_path


def _duration_ms(started_at: datetime | None, completed_at: datetime | None) -> float | None:
    if started_at is None or completed_at is None:
        return None
    return max(0.0, (completed_at - started_at).total_seconds() * 1000.0)


def _technical_report_verification_passed(result: dict) -> bool:
    if result.get("task_type") != "verify_technical_report":
        return False
    payload = result.get("payload")
    if not isinstance(payload, dict):
        return False
    verification = payload.get("verification")
    return isinstance(verification, dict) and verification.get("outcome") == "passed"


def _evaluation_query_count_from_evaluation(evaluation: dict) -> int:
    return int(evaluation.get("total_shared_query_count") or 0)


def _replay_query_count_from_evaluation(evaluation: dict) -> int:
    return sum(
        int(source.get("baseline_query_count") or 0) + int(source.get("candidate_query_count") or 0)
        for source in (evaluation.get("sources") or [])
        if isinstance(source, dict)
    )


def _derive_attempt_cost(task: AgentTask, result: dict) -> dict:
    payload = (result or {}).get("payload") or result or {}
    evaluation = payload.get("evaluation") or {}
    verification = payload.get("verification") or {}
    replay_run = payload.get("replay_run") or {}
    replay = payload.get("replay") or {}

    replay_query_count = 0
    evaluation_query_count = 0
    embedding_count = 0
    call_count = 0

    if task.task_type == "run_search_replay_suite":
        replay_query_count = int(replay_run.get("query_count") or 0)
        call_count = 1
    elif task.task_type == "evaluate_search_harness":
        replay_query_count = _replay_query_count_from_evaluation(evaluation)
        evaluation_query_count = _evaluation_query_count_from_evaluation(evaluation)
        call_count = max(len(evaluation.get("sources") or []), 1)
    elif task.task_type == "triage_replay_regression":
        replay_query_count = _replay_query_count_from_evaluation(evaluation)
        evaluation_query_count = _evaluation_query_count_from_evaluation(evaluation)
        call_count = max(len(evaluation.get("sources") or []), 1)
    elif task.task_type == "triage_semantic_pass":
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("issue_count") or 0)
        call_count = 1 if verification else 0
    elif task.task_type == "export_semantic_supervision_corpus":
        corpus = payload.get("corpus") or {}
        evaluation_query_count = int(corpus.get("row_count") or 0)
        call_count = 1
    elif task.task_type == "evaluate_semantic_candidate_extractor":
        summary = payload.get("summary") or {}
        evaluation_query_count = int(summary.get("expected_concept_count") or 0)
        call_count = max(int(summary.get("document_count") or 0), 1)
    elif task.task_type == "build_shadow_semantic_graph":
        graph_payload = payload.get("shadow_graph") or {}
        evaluation_query_count = int(graph_payload.get("edge_count") or 0)
        call_count = max(int(graph_payload.get("document_count") or 0), 1)
    elif task.task_type == "evaluate_semantic_relation_extractor":
        summary = payload.get("summary") or {}
        evaluation_query_count = int(summary.get("expected_edge_count") or 0)
        call_count = max(int(summary.get("document_count") or 0), 1)
    elif task.task_type == "triage_semantic_candidate_disagreements":
        report = payload.get("disagreement_report") or {}
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("issue_count") or report.get("issue_count") or 0)
        call_count = 1 if report or verification else 0
    elif task.task_type == "triage_semantic_graph_disagreements":
        report = payload.get("disagreement_report") or {}
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("issue_count") or report.get("issue_count") or 0)
        call_count = 1 if report or verification else 0
    elif task.task_type == "prepare_semantic_generation_brief":
        brief = payload.get("brief") or {}
        evaluation_query_count = int(len(brief.get("claim_candidates") or []))
        call_count = 1
    elif task.task_type == "plan_technical_report":
        plan = payload.get("plan") or {}
        evaluation_query_count = int(len(plan.get("expected_claims") or []))
        call_count = 1
    elif task.task_type == "build_report_evidence_cards":
        evidence_bundle = payload.get("evidence_bundle") or {}
        evaluation_query_count = int(len(evidence_bundle.get("evidence_cards") or []))
        call_count = 1
    elif task.task_type == "prepare_report_agent_harness":
        harness = payload.get("harness") or {}
        evaluation_query_count = int(len(harness.get("claim_contract") or []))
        call_count = 1
    elif task.task_type == "initialize_workspace_ontology":
        snapshot = payload.get("snapshot") or {}
        evaluation_query_count = int(snapshot.get("concept_count") or 0)
        call_count = 1
    elif task.task_type == "get_active_ontology_snapshot":
        snapshot = payload.get("snapshot") or {}
        evaluation_query_count = int(snapshot.get("concept_count") or 0)
        call_count = 1 if snapshot else 0
    elif task.task_type == "draft_ontology_extension":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("operations") or []))
        call_count = 1
    elif task.task_type == "draft_graph_promotions":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("promoted_edges") or []))
        call_count = 1
    elif task.task_type == "verify_draft_ontology_extension":
        verification = payload.get("verification") or {}
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("document_count") or 0)
        call_count = max(int(metrics.get("document_count") or 0), 1) if metrics else 0
    elif task.task_type == "verify_draft_graph_promotions":
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("promoted_edge_count") or 0)
        call_count = max(int(metrics.get("promoted_edge_count") or 0), 1) if metrics else 0
    elif task.task_type == "apply_ontology_extension":
        apply_payload = payload
        evaluation_query_count = int(len(apply_payload.get("applied_operations") or []))
        call_count = 1
    elif task.task_type == "apply_graph_promotions":
        apply_payload = payload
        evaluation_query_count = int(apply_payload.get("applied_edge_count") or 0)
        call_count = 1
    elif task.task_type == "build_document_fact_graph":
        evaluation_query_count = int(payload.get("fact_count") or 0)
        call_count = 1
    elif task.task_type == "draft_semantic_grounded_document":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("claims") or []))
        call_count = 1
    elif task.task_type == "draft_technical_report":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("claims") or []))
        call_count = 1
    elif task.task_type in {
        "verify_search_harness_evaluation",
        "verify_draft_harness_config",
        "verify_draft_semantic_registry_update",
        "verify_semantic_grounded_document",
        "verify_technical_report",
    }:
        metrics = verification.get("metrics") or {}
        if task.task_type == "verify_draft_semantic_registry_update":
            evaluation_query_count = int(metrics.get("document_count") or 0)
            call_count = max(int(metrics.get("document_count") or 0), 1) if metrics else 0
        elif task.task_type == "verify_semantic_grounded_document":
            evaluation_query_count = int(metrics.get("claim_count") or 0)
            call_count = 1 if metrics else 0
        elif task.task_type == "verify_technical_report":
            evaluation_query_count = int(metrics.get("claim_count") or 0)
            call_count = 1 if metrics else 0
        else:
            evaluation_query_count = int(metrics.get("total_shared_query_count") or 0)
            call_count = max(int(metrics.get("source_count") or 0), 1) if metrics else 0
    elif task.task_type == "replay_search_request":
        replay_query_count = 1 if replay else 0
        call_count = 1 if replay else 0

    return {
        "provider": None,
        "model": task.model,
        "billing_status": "model_pricing_not_integrated",
        "call_count": call_count,
        "input_tokens": None,
        "output_tokens": None,
        "embedding_count": embedding_count,
        "replay_query_count": replay_query_count,
        "evaluation_query_count": evaluation_query_count,
        "estimated_usd": 0.0,
    }


def _derive_attempt_performance(
    task: AgentTask,
    attempt: AgentTaskAttempt,
    completed_at: datetime,
) -> dict:
    queue_latency_ms = _duration_ms(task.created_at, attempt.started_at)
    execution_latency_ms = _duration_ms(attempt.started_at, completed_at)
    approval_latency_ms = _duration_ms(task.created_at, task.approved_at)
    end_to_end_latency_ms = _duration_ms(task.created_at, completed_at)
    verification_latency_ms = (
        execution_latency_ms
        if task.task_type.startswith("verify_")
        or task.task_type
        in {
            "triage_replay_regression",
            "triage_semantic_pass",
            "triage_semantic_candidate_disagreements",
        }
        else None
    )
    return {
        "queue_latency_ms": queue_latency_ms,
        "execution_latency_ms": execution_latency_ms,
        "approval_latency_ms": approval_latency_ms,
        "verification_latency_ms": verification_latency_ms,
        "end_to_end_latency_ms": end_to_end_latency_ms,
    }


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
) -> int:
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
        attempt = _current_attempt(session, task)
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
            failure_path = _write_failure_artifact(
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


def _result_has_applied_promotable_side_effect(result: dict | None) -> bool:
    return (
        isinstance(result, dict)
        and result.get(PROMOTABLE_SIDE_EFFECT_APPLIED_KEY) == PROMOTABLE_SIDE_EFFECT_APPLIED_VALUE
        and isinstance(result.get(PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY), dict)
    )


def _checkpoint_promotable_task_result(session: Session, task: AgentTask, result: dict) -> dict:
    checkpoint = {
        PROMOTABLE_SIDE_EFFECT_APPLIED_KEY: PROMOTABLE_SIDE_EFFECT_APPLIED_VALUE,
        PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY: dict(result or {}),
    }
    task.result_json = checkpoint
    task.updated_at = utcnow()
    session.commit()
    return dict(result or {})


def _strip_promotable_side_effect_marker(result: dict) -> dict:
    if _result_has_applied_promotable_side_effect(result):
        return dict(result.get(PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY) or {})
    sanitized = dict(result or {})
    sanitized.pop(PROMOTABLE_SIDE_EFFECT_APPLIED_KEY, None)
    sanitized.pop(PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY, None)
    return sanitized


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


def finalize_agent_task_success(
    session: Session,
    task: AgentTask,
    result: dict,
    *,
    storage_service: StorageService | None = None,
) -> None:
    now = utcnow()
    sanitized_result = _strip_promotable_side_effect_marker(result)
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
        evidence_manifest = refresh_technical_report_evidence_manifest(
            session,
            task_id=task.id,
        )
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

    attempt = _current_attempt(session, task)
    if attempt is not None:
        attempt.status = "completed"
        attempt.result_json = sanitized_result
        attempt.cost_json = _derive_attempt_cost(task, sanitized_result)
        attempt.performance_json = _derive_attempt_performance(task, attempt, now)
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

    attempt = _current_attempt(session, task)
    if attempt is not None:
        attempt.status = "failed"
        attempt.error_message = str(exc)
        attempt.result_json = {
            **(attempt.result_json or {}),
            "failure_type": exc.__class__.__name__,
            "failure_stage": failure_stage,
        }
        attempt.cost_json = _derive_attempt_cost(task, attempt.result_json)
        attempt.performance_json = _derive_attempt_performance(task, attempt, now)
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

    with agent_task_lease_heartbeat(task.id, worker_id=task.locked_by):
        try:
            failure_stage = "execute"
            logger.info(
                "agent_task_processing_started",
                task_id=str(task.id),
                task_type=task.task_type,
            )
            heartbeat_agent_task(session, task)
            if _result_has_applied_promotable_side_effect(task.result_json):
                result = _strip_promotable_side_effect_marker(task.result_json or {})
            else:
                active_executor = executor or execute_agent_task_action
                result = active_executor(session, task)
                if task.side_effect_level == "promotable":
                    result = _checkpoint_promotable_task_result(session, task, result)
                    task = session.get(AgentTask, task_id) or task
            heartbeat_agent_task(session, task)
            write_agent_task_context(
                session,
                task,
                result,
                storage_service=storage_service,
            )
            failure_stage = "complete"
            finalize_agent_task_success(session, task, result, storage_service=storage_service)
            logger.info(
                "agent_task_processing_completed",
                task_id=str(task.id),
                task_type=task.task_type,
            )
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
    worker_id = get_process_identity()
    registration = register_runtime_process("agent_worker", worker_id)
    logger.info(
        "agent_worker_runtime_registered",
        worker_id=worker_id,
        code_fingerprint=registration.startup_code_fingerprint,
    )

    while True:
        if not runtime_code_is_current(registration.startup_code_fingerprint):
            logger.warning(
                "agent_worker_exiting_stale_code",
                worker_id=worker_id,
                code_fingerprint=registration.startup_code_fingerprint,
            )
            return
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
