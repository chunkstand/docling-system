from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.time import utcnow
from app.db.public.document_artifacts import DocumentFigure, DocumentTable
from app.db.public.ingest import Document, DocumentRun, RunStatus
from app.services.run_failure_artifacts import write_failure_artifact
from app.services.run_leases import is_retryable_error
from app.services.storage import StorageService
from app.services.validation import ValidationReport

logger = get_logger(__name__)


def finalize_run_success(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed,
    report: ValidationReport,
    *,
    storage_service: StorageService | None = None,
) -> None:
    now = utcnow()
    run.locked_at = None
    run.locked_by = None
    run.last_heartbeat_at = None
    run.next_attempt_at = None
    run.chunk_count = len(parsed.chunks)
    run.table_count = len(parsed.tables)
    run.figure_count = len(parsed.figures)
    run.validation_status = "passed"
    run.validation_results_json = report.details
    run.failure_stage = None
    run.completed_at = now
    run.status = RunStatus.COMPLETED.value
    run.error_message = None
    if run.failure_artifact_path and storage_service is not None:
        storage_service.delete_file_if_exists(Path(run.failure_artifact_path))
    run.failure_artifact_path = None
    session.query(DocumentTable).filter(DocumentTable.run_id == run.id).update(
        {"status": "validated"}
    )
    session.query(DocumentFigure).filter(DocumentFigure.run_id == run.id).update(
        {"status": "validated"}
    )

    document.active_run_id = run.id
    document.latest_run_id = run.id
    document.title = parsed.title
    document.page_count = parsed.page_count
    document.updated_at = now
    session.commit()


def finalize_run_failure(
    session: Session,
    run: DocumentRun,
    exc: Exception,
    report: ValidationReport | None = None,
    failure_stage: str | None = None,
    *,
    storage_service: StorageService | None = None,
    document: Document | None = None,
) -> None:
    settings = get_settings()
    now = utcnow()
    run.locked_at = None
    run.locked_by = None
    run.last_heartbeat_at = None
    run.error_message = str(exc)
    run.failure_stage = failure_stage
    run.validation_results_json = getattr(run, "validation_results_json", None) or {}
    run.validation_results_json["failure_type"] = exc.__class__.__name__
    if failure_stage:
        run.validation_results_json["failure_stage"] = failure_stage
    if report is not None:
        run.validation_status = "failed"
        run.validation_results_json = {**report.details, **run.validation_results_json}
        session.query(DocumentTable).filter(DocumentTable.run_id == run.id).update(
            {"status": "rejected"}
        )
        session.query(DocumentFigure).filter(DocumentFigure.run_id == run.id).update(
            {"status": "rejected"}
        )

    attempts = int(getattr(run, "attempts", settings.worker_max_attempts))
    if is_retryable_error(exc) and attempts < settings.worker_max_attempts:
        backoff_seconds = min(60, 2 ** max(attempts - 1, 0))
        run.status = RunStatus.RETRY_WAIT.value
        run.next_attempt_at = now + timedelta(seconds=backoff_seconds)
    else:
        run.status = RunStatus.FAILED.value
        run.validation_status = "failed"
        run.completed_at = now

    failure_path = write_failure_artifact(
        storage_service,
        document,
        run,
        exc,
        failure_stage=failure_stage,
        report=report,
    )
    run.failure_artifact_path = str(failure_path) if failure_path is not None else None

    session.commit()


def evaluate_promoted_run(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None,
    evaluate_run_fn,
) -> None:
    try:
        evaluation = evaluate_run_fn(
            session,
            document,
            run,
            baseline_run_id=baseline_run_id,
        )
    except Exception:
        logger.exception(
            "run_post_promotion_evaluation_failed",
            run_id=str(run.id),
            document_id=str(document.id),
        )
        return

    logger.info(
        "run_evaluation_completed",
        run_id=str(run.id),
        document_id=str(document.id),
        evaluation_status=evaluation.status,
        fixture_name=evaluation.fixture_name,
    )


def run_post_promotion_semantics(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None,
    storage_service: StorageService,
    execute_semantic_pass_fn,
) -> None:
    try:
        execute_semantic_pass_fn(
            session,
            document,
            run,
            baseline_run_id=baseline_run_id,
            storage_service=storage_service,
        )
    except Exception:
        session.rollback()
        logger.exception(
            "run_post_promotion_semantics_failed",
            run_id=str(run.id),
            document_id=str(document.id),
        )
