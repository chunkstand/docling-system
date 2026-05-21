from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import get_settings
from app.core.time import utcnow
from app.db.public.document_artifacts import DocumentFigure, DocumentTable
from app.db.public.ingest import Document, DocumentRun, RunStatus
from app.schemas.documents import (
    DocumentDetailResponse,
    DocumentRunSummaryResponse,
    DocumentSummaryResponse,
)
from app.services.evaluations import (
    get_latest_evaluation_summaries,
    get_latest_evaluation_summary,
)


def get_document_or_404(session: Session, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "document_not_found", "Document not found.")
    return document


def get_run_record(session: Session, run_id: UUID | None) -> DocumentRun | None:
    if run_id is None:
        return None
    return session.get(DocumentRun, run_id)


def _runs_by_id(session: Session, run_ids: set[UUID]) -> dict[UUID, DocumentRun]:
    if not run_ids:
        return {}
    rows = session.execute(select(DocumentRun).where(DocumentRun.id.in_(run_ids))).scalars().all()
    return {row.id: row for row in rows}


def _run_entity_counts(
    session: Session,
    entity,
    run_ids: set[UUID],
) -> dict[UUID, int]:
    if not run_ids:
        return {}
    rows = session.execute(
        select(entity.run_id, func.count().label("entity_count"))
        .where(entity.run_id.in_(run_ids))
        .group_by(entity.run_id)
    ).all()
    return {run_id: int(count) for run_id, count in rows}


def _run_current_stage(run: DocumentRun) -> str:
    if run.status == RunStatus.FAILED.value:
        return run.failure_stage or RunStatus.FAILED.value
    if run.status == RunStatus.VALIDATING.value:
        return "validation"
    if run.status == RunStatus.PROCESSING.value:
        if run.docling_json_path or run.yaml_path:
            return "persisted_outputs"
        return "parse_and_persist"
    return run.status


def _run_stage_started_at(run: DocumentRun, current_stage: str) -> datetime | None:
    if current_stage in {"parse_and_persist", "persisted_outputs", "validation"}:
        return run.locked_at or run.started_at or run.created_at
    if current_stage in {RunStatus.QUEUED.value, RunStatus.RETRY_WAIT.value}:
        return run.created_at
    if current_stage == RunStatus.COMPLETED.value:
        return run.completed_at or run.started_at or run.created_at
    if current_stage == RunStatus.FAILED.value or current_stage == (run.failure_stage or ""):
        return run.completed_at or run.started_at or run.created_at
    return run.started_at or run.created_at


def _run_heartbeat_age_seconds(run: DocumentRun) -> int | None:
    if run.last_heartbeat_at is None:
        return None
    return max(int((utcnow() - run.last_heartbeat_at).total_seconds()), 0)


def _run_lease_stale(run: DocumentRun) -> bool:
    heartbeat_age_seconds = _run_heartbeat_age_seconds(run)
    if heartbeat_age_seconds is None:
        return False
    return heartbeat_age_seconds > get_settings().worker_lease_timeout_seconds


def _run_validation_warning_count(run: DocumentRun) -> int:
    validation_results = run.validation_results_json or {}
    return int(validation_results.get("warning_count") or 0)


def _run_progress_summary(run: DocumentRun) -> dict:
    validation_results = run.validation_results_json or {}
    return {
        "artifacts_persisted": bool(run.docling_json_path and run.yaml_path),
        "content_counts_recorded": any(
            value is not None for value in (run.chunk_count, run.table_count, run.figure_count)
        ),
        "chunk_count": run.chunk_count,
        "table_count": run.table_count,
        "figure_count": run.figure_count,
        "validation_summary": validation_results.get("summary"),
        "validation_warning_count": int(validation_results.get("warning_count") or 0),
    }


def to_run_summary(document: Document, run: DocumentRun) -> DocumentRunSummaryResponse:
    current_stage = _run_current_stage(run)
    return DocumentRunSummaryResponse(
        run_id=run.id,
        run_number=run.run_number,
        status=run.status,
        attempts=run.attempts,
        validation_status=run.validation_status,
        chunk_count=run.chunk_count,
        table_count=run.table_count,
        figure_count=run.figure_count,
        error_message=run.error_message,
        failure_stage=run.failure_stage,
        has_failure_artifact=bool(run.failure_artifact_path),
        current_stage=current_stage,
        stage_started_at=_run_stage_started_at(run, current_stage),
        locked_at=run.locked_at,
        locked_by=run.locked_by,
        last_heartbeat_at=run.last_heartbeat_at,
        lease_stale=_run_lease_stale(run),
        heartbeat_age_seconds=_run_heartbeat_age_seconds(run),
        validation_warning_count=_run_validation_warning_count(run),
        progress_summary=_run_progress_summary(run),
        is_active_run=run.id == document.active_run_id,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )
def get_document_detail(session: Session, document_id: UUID) -> DocumentDetailResponse:
    document = get_document_or_404(session, document_id)

    active_run = get_run_record(session, document.active_run_id)
    latest_run = get_run_record(session, document.latest_run_id)
    table_count = 0
    figure_count = 0
    if document.active_run_id is not None:
        table_count = session.execute(
            select(func.count())
            .select_from(DocumentTable)
            .where(
                DocumentTable.document_id == document.id,
                DocumentTable.run_id == document.active_run_id,
            )
        ).scalar_one()
        figure_count = session.execute(
            select(func.count())
            .select_from(DocumentFigure)
            .where(
                DocumentFigure.document_id == document.id,
                DocumentFigure.run_id == document.active_run_id,
            )
        ).scalar_one()

    return DocumentDetailResponse(
        document_id=document.id,
        source_filename=document.source_filename,
        title=document.title,
        active_run_id=document.active_run_id,
        active_run_status=active_run.status if active_run else None,
        latest_run_id=document.latest_run_id,
        latest_run_status=latest_run.status if latest_run else None,
        latest_validation_status=latest_run.validation_status if latest_run else None,
        latest_run_promoted=bool(latest_run and latest_run.id == document.active_run_id),
        is_searchable=document.active_run_id is not None,
        has_json_artifact=bool(active_run and active_run.docling_json_path),
        has_yaml_artifact=bool(active_run and active_run.yaml_path),
        table_count=table_count,
        has_table_artifacts=table_count > 0,
        figure_count=figure_count,
        has_figure_artifacts=figure_count > 0,
        latest_evaluation=get_latest_evaluation_summary(session, document.latest_run_id),
        created_at=document.created_at,
        updated_at=document.updated_at,
        latest_error_message=latest_run.error_message if latest_run else None,
    )


def list_documents(session: Session, limit: int = 50) -> list[DocumentSummaryResponse]:
    documents = (
        session.execute(select(Document).order_by(Document.updated_at.desc()).limit(limit))
        .scalars()
        .all()
    )
    run_ids = {
        run_id
        for document in documents
        for run_id in (document.active_run_id, document.latest_run_id)
        if run_id is not None
    }
    active_run_ids = {
        document.active_run_id for document in documents if document.active_run_id is not None
    }
    runs_by_id = _runs_by_id(session, run_ids)
    table_counts_by_run = _run_entity_counts(session, DocumentTable, active_run_ids)
    figure_counts_by_run = _run_entity_counts(session, DocumentFigure, active_run_ids)
    evaluation_summaries = get_latest_evaluation_summaries(session, run_ids)
    summaries: list[DocumentSummaryResponse] = []

    for document in documents:
        active_run = runs_by_id.get(document.active_run_id)
        latest_run = runs_by_id.get(document.latest_run_id)
        table_count = int(table_counts_by_run.get(document.active_run_id, 0))
        figure_count = int(figure_counts_by_run.get(document.active_run_id, 0))

        summaries.append(
            DocumentSummaryResponse(
                document_id=document.id,
                source_filename=document.source_filename,
                title=document.title,
                active_run_id=document.active_run_id,
                active_run_status=active_run.status if active_run else None,
                latest_run_id=document.latest_run_id,
                latest_run_status=latest_run.status if latest_run else None,
                latest_validation_status=latest_run.validation_status if latest_run else None,
                latest_run_promoted=bool(latest_run and latest_run.id == document.active_run_id),
                table_count=table_count,
                has_table_artifacts=table_count > 0,
                figure_count=figure_count,
                has_figure_artifacts=figure_count > 0,
                latest_evaluation=evaluation_summaries.get(document.latest_run_id),
                updated_at=document.updated_at,
            )
        )

    return summaries


def list_document_runs(
    session: Session,
    document_id: UUID,
    limit: int = 20,
) -> list[DocumentRunSummaryResponse]:
    document = get_document_or_404(session, document_id)
    runs = (
        session.execute(
            select(DocumentRun)
            .where(DocumentRun.document_id == document_id)
            .order_by(DocumentRun.run_number.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [to_run_summary(document, run) for run in runs]


def get_document_run_summary(session: Session, run_id: UUID) -> DocumentRunSummaryResponse:
    run = session.get(DocumentRun, run_id)
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_run_not_found",
            "Document run not found.",
        )
    document = session.get(Document, run.document_id)
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "document_not_found", "Document not found.")
    return to_run_summary(document, run)
