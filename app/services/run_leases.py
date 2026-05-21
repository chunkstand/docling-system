from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.time import utcnow
from app.db.public.ingest import DocumentRun, RunStatus
from app.services.run_failure_artifacts import write_failure_artifact
from app.services.storage import StorageService

logger = get_logger(__name__)


def is_retryable_error(exc: Exception) -> bool:
    return not isinstance(exc, ValueError)


def requeue_stale_runs(session: Session, storage_service: StorageService | None = None) -> int:
    settings = get_settings()
    stale_before = utcnow() - timedelta(seconds=settings.worker_lease_timeout_seconds)
    stale_runs = session.execute(
        select(DocumentRun).where(
            DocumentRun.status.in_([RunStatus.PROCESSING.value, RunStatus.VALIDATING.value]),
            DocumentRun.last_heartbeat_at.is_not(None),
            DocumentRun.last_heartbeat_at < stale_before,
        )
    ).scalars()

    updated = 0
    for run in stale_runs:
        run.locked_at = None
        run.locked_by = None
        run.last_heartbeat_at = None
        if run.attempts >= settings.worker_max_attempts:
            run.status = RunStatus.FAILED.value
            run.completed_at = utcnow()
            run.validation_status = "failed"
            run.error_message = run.error_message or "Run exceeded max attempts after stale lease."
            run.failure_stage = run.failure_stage or "stale_lease"
            failure_path = write_failure_artifact(
                storage_service,
                None,
                run,
                RuntimeError(run.error_message),
                failure_stage=run.failure_stage,
            )
            run.failure_artifact_path = str(failure_path) if failure_path is not None else None
        else:
            run.status = RunStatus.RETRY_WAIT.value
            run.next_attempt_at = utcnow()
        updated += 1

    if updated:
        session.commit()
        logger.info("stale_runs_requeued", count=updated)

    return updated


def claim_next_run(session: Session, worker_id: str) -> DocumentRun | None:
    now = utcnow()
    eligible_query: Select[tuple[DocumentRun]] = (
        select(DocumentRun)
        .where(
            or_(
                DocumentRun.status == RunStatus.QUEUED.value,
                and_(
                    DocumentRun.status == RunStatus.RETRY_WAIT.value,
                    or_(DocumentRun.next_attempt_at.is_(None), DocumentRun.next_attempt_at <= now),
                ),
            )
        )
        .order_by(DocumentRun.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    run = session.execute(eligible_query).scalar_one_or_none()
    if run is None:
        session.rollback()
        return None

    run.status = RunStatus.PROCESSING.value
    run.locked_at = now
    run.locked_by = worker_id
    run.last_heartbeat_at = now
    run.started_at = run.started_at or now
    run.next_attempt_at = None
    run.validation_status = "pending"
    run.validation_results_json = {}
    run.failure_stage = None
    run.attempts += 1
    session.commit()
    session.refresh(run)
    logger.info(
        "run_claimed", run_id=str(run.id), document_id=str(run.document_id), worker_id=worker_id
    )
    return run


def heartbeat_run(session: Session, run: DocumentRun) -> None:
    run.last_heartbeat_at = utcnow()
    session.commit()


def _refresh_run_lease(session_factory, run_id: UUID, worker_id: str) -> bool:
    with session_factory() as heartbeat_session:
        result = heartbeat_session.execute(
            update(DocumentRun)
            .where(
                DocumentRun.id == run_id,
                DocumentRun.locked_by == worker_id,
                DocumentRun.status.in_([RunStatus.PROCESSING.value, RunStatus.VALIDATING.value]),
            )
            .values(last_heartbeat_at=utcnow())
        )
        heartbeat_session.commit()
        return bool(result.rowcount)


@contextmanager
def run_lease_heartbeat(run_id: UUID, *, worker_id: str | None):
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
                if not _refresh_run_lease(session_factory, run_id, worker_id):
                    return
            except Exception as exc:
                logger.warning(
                    "run_lease_heartbeat_failed",
                    run_id=str(run_id),
                    worker_id=worker_id,
                    error=str(exc),
                )

    heartbeat_thread = threading.Thread(
        target=_loop,
        name=f"run-heartbeat-{run_id}",
        daemon=True,
    )
    heartbeat_thread.start()
    try:
        yield
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=max(1, interval_seconds))
