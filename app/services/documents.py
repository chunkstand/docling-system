from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pypdfium2 as pdfium
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import default_local_ingest_roots, get_settings
from app.core.time import utcnow
from app.db.models import Document, DocumentFigure, DocumentRun, DocumentTable, RunStatus
from app.schemas.documents import (
    DocumentDetailResponse,
    DocumentRunSummaryResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from app.services.evaluations import (
    get_latest_document_evaluation,
    get_latest_evaluation_summaries,
    get_latest_evaluation_summary,
)
from app.services.storage import StorageService

PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


@dataclass
class ExistingRunSnapshot:
    document: Document
    active_run: DocumentRun | None
    latest_run: DocumentRun | None


def get_document_or_404(session: Session, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


def _is_pdf(upload: UploadFile) -> bool:
    filename = upload.filename or ""
    return upload.content_type in PDF_MIME_TYPES or filename.lower().endswith(".pdf")


def _allowed_ingest_roots() -> list[Path]:
    settings = get_settings()
    if settings.local_ingest_allowed_roots:
        return [
            Path(item).expanduser().resolve()
            for item in settings.local_ingest_allowed_roots.split(":")
            if item
        ]
    return default_local_ingest_roots()


def _sha256_file(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as source_file:
        while chunk := source_file.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _validate_pdf_artifact(
    file_path: Path,
    *,
    enforce_page_limit: bool = True,
    size_limit_detail: str = "File exceeds local ingest size limit.",
    page_limit_detail_prefix: str = "PDF page count exceeds local ingest limit",
) -> Path:
    settings = get_settings()
    if file_path.stat().st_size > settings.local_ingest_max_file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=size_limit_detail,
        )
    with file_path.open("rb") as source_file:
        if source_file.read(5) != b"%PDF-":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a valid PDF.",
            )
    if not enforce_page_limit:
        return file_path
    page_count = _pdf_page_count(file_path)
    if page_count <= 0 or page_count > settings.local_ingest_max_pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{page_limit_detail_prefix} ({settings.local_ingest_max_pages}).",
        )
    return file_path


def _validate_local_ingest_path(file_path: Path, *, enforce_limits: bool = True) -> Path:
    raw_path = file_path.expanduser()
    if raw_path.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Symlink ingest paths are not allowed."
        )
    resolved_path = raw_path.resolve()
    if not resolved_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {resolved_path}"
        )
    if resolved_path.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported."
        )
    if not any(resolved_path.is_relative_to(root) for root in _allowed_ingest_roots()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is outside allowed local ingest roots.",
        )
    return _validate_pdf_artifact(resolved_path, enforce_page_limit=enforce_limits)


def _pdf_page_count(file_path: Path) -> int:
    try:
        pdf = pdfium.PdfDocument(str(file_path))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid PDF.",
        ) from exc
    try:
        return len(pdf)
    finally:
        pdf.close()


def _get_run(session: Session, run_id: UUID | None) -> DocumentRun | None:
    if run_id is None:
        return None
    return session.get(DocumentRun, run_id)


def _runs_by_id(
    session: Session,
    run_ids: set[UUID],
) -> dict[UUID, DocumentRun]:
    if not run_ids:
        return {}
    rows = (
        session.execute(select(DocumentRun).where(DocumentRun.id.in_(run_ids)))
        .scalars()
        .all()
    )
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


def _to_run_summary(document: Document, run: DocumentRun) -> DocumentRunSummaryResponse:
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


def _load_existing_snapshot(session: Session, document: Document) -> ExistingRunSnapshot:
    return ExistingRunSnapshot(
        document=document,
        active_run=_get_run(session, document.active_run_id),
        latest_run=_get_run(session, document.latest_run_id),
    )


def _next_run_number(session: Session, document_id: UUID) -> int:
    query: Select[tuple[int | None]] = select(func.max(DocumentRun.run_number)).where(
        DocumentRun.document_id == document_id
    )
    current_max = session.execute(query).scalar_one()
    return 1 if current_max is None else current_max + 1


def _lock_document_row(session: Session, document_id: UUID) -> Document | None:
    statement = select(Document).where(Document.id == document_id).with_for_update()
    return session.execute(statement).scalar_one_or_none()


def _build_duplicate_response(snapshot: ExistingRunSnapshot) -> DocumentUploadResponse:
    active_status = snapshot.active_run.status if snapshot.active_run else None
    latest_status = snapshot.latest_run.status if snapshot.latest_run else RunStatus.FAILED.value
    return DocumentUploadResponse(
        document_id=snapshot.document.id,
        status=active_status or latest_status,
        duplicate=True,
        recovery_run=False,
        active_run_id=snapshot.document.active_run_id,
        active_run_status=active_status,
    )


def _build_recovery_response(document_id: UUID, run_id: UUID) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        document_id=document_id,
        run_id=run_id,
        status=RunStatus.QUEUED.value,
        duplicate=True,
        recovery_run=True,
    )


def _resolve_existing_document_upload(
    session: Session,
    existing: Document,
) -> tuple[DocumentUploadResponse, int]:
    locked_document = _lock_document_row(session, existing.id)
    if locked_document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    snapshot = _load_existing_snapshot(session, locked_document)

    if snapshot.active_run is not None:
        return _build_duplicate_response(snapshot), status.HTTP_200_OK

    if snapshot.latest_run and snapshot.latest_run.status in {
        RunStatus.QUEUED.value,
        RunStatus.PROCESSING.value,
        RunStatus.VALIDATING.value,
        RunStatus.RETRY_WAIT.value,
    }:
        return (
            DocumentUploadResponse(
                document_id=locked_document.id,
                run_id=snapshot.latest_run.id,
                status=snapshot.latest_run.status,
                duplicate=True,
                recovery_run=True,
            ),
            status.HTTP_202_ACCEPTED,
        )

    recovery_run = _create_run_for_locked_document(session=session, document=locked_document)
    session.commit()
    return _build_recovery_response(locked_document.id, recovery_run.id), status.HTTP_202_ACCEPTED


def _create_run_for_locked_document(session: Session, document: Document) -> DocumentRun:
    now = utcnow()
    run = DocumentRun(
        document_id=document.id,
        run_number=_next_run_number(session, document.id),
        status=RunStatus.QUEUED.value,
        created_at=now,
        next_attempt_at=now,
        validation_status="pending",
    )
    session.add(run)
    session.flush()
    document.latest_run_id = run.id
    document.updated_at = now
    return run


def _queue_document_run(
    session: Session,
    storage_service: StorageService,
    *,
    staged_path: Path,
    sha256: str,
    source_filename: str,
    mime_type: str,
) -> tuple[DocumentUploadResponse, int]:
    now = utcnow()
    document = Document(
        source_filename=Path(source_filename).name,
        source_path="",
        sha256=sha256,
        mime_type=mime_type,
        created_at=now,
        updated_at=now,
    )
    try:
        with session.begin_nested():
            session.add(document)
            session.flush()
    except IntegrityError:
        existing = session.execute(select(Document).where(Document.sha256 == sha256)).scalar_one_or_none()
        if existing is None:
            raise
        storage_service.delete_file_if_exists(staged_path)
        return _resolve_existing_document_upload(session, existing)

    source_path = storage_service.move_source_file(document.id, staged_path)
    try:
        document.source_path = str(source_path)

        document_run = DocumentRun(
            document_id=document.id,
            run_number=1,
            status=RunStatus.QUEUED.value,
            created_at=now,
            next_attempt_at=now,
            validation_status="pending",
        )
        session.add(document_run)
        session.flush()

        document.latest_run_id = document_run.id
        document.updated_at = now
        session.commit()
    except Exception:
        storage_service.delete_file_if_exists(source_path)
        raise

    return (
        DocumentUploadResponse(
            document_id=document.id,
            run_id=document_run.id,
            status=document_run.status,
            duplicate=False,
        ),
        status.HTTP_202_ACCEPTED,
    )


def ingest_upload(
    session: Session,
    upload: UploadFile,
    storage_service: StorageService,
) -> tuple[DocumentUploadResponse, int]:
    if not _is_pdf(upload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF uploads are supported."
        )

    settings = get_settings()
    staged_path, sha256 = storage_service.stage_upload(
        upload,
        max_file_bytes=settings.local_ingest_max_file_bytes,
    )

    try:
        existing = session.execute(select(Document).where(Document.sha256 == sha256)).scalar_one_or_none()
        if existing is not None:
            storage_service.delete_file_if_exists(staged_path)
            return _resolve_existing_document_upload(session, existing)

        _validate_pdf_artifact(
            staged_path,
            size_limit_detail="File exceeds upload size limit.",
            page_limit_detail_prefix="PDF page count exceeds upload limit",
        )
        return _queue_document_run(
            session=session,
            storage_service=storage_service,
            staged_path=staged_path,
            sha256=sha256,
            source_filename=upload.filename or "document.pdf",
            mime_type=upload.content_type or "application/pdf",
        )
    except Exception:
        storage_service.delete_file_if_exists(staged_path)
        session.rollback()
        raise


def ingest_local_file(
    session: Session,
    file_path: Path,
    storage_service: StorageService,
) -> tuple[DocumentUploadResponse, int]:
    file_path = _validate_local_ingest_path(file_path, enforce_limits=False)
    sha256 = _sha256_file(file_path)
    existing = session.execute(select(Document).where(Document.sha256 == sha256)).scalar_one_or_none()
    if existing is not None:
        return _resolve_existing_document_upload(session, existing)
    file_path = _validate_local_ingest_path(file_path)

    staged_path, sha256 = storage_service.stage_local_file(file_path)
    try:
        return _queue_document_run(
            session=session,
            storage_service=storage_service,
            staged_path=staged_path,
            sha256=sha256,
            source_filename=file_path.name,
            mime_type="application/pdf",
        )
    except Exception:
        storage_service.delete_file_if_exists(staged_path)
        session.rollback()
        raise


def create_run_for_existing_document(session: Session, document: Document) -> DocumentRun:
    locked_document = _lock_document_row(session, document.id)
    if locked_document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return _create_run_for_locked_document(session, locked_document)


def get_document_detail(session: Session, document_id: UUID) -> DocumentDetailResponse:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    active_run = _get_run(session, document.active_run_id)
    latest_run = _get_run(session, document.latest_run_id)
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


def reprocess_document(session: Session, document_id: UUID) -> DocumentUploadResponse:
    document = _lock_document_row(session, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    latest_run = _get_run(session, document.latest_run_id)
    if latest_run and latest_run.status in {
        RunStatus.QUEUED.value,
        RunStatus.PROCESSING.value,
        RunStatus.VALIDATING.value,
        RunStatus.RETRY_WAIT.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already has an in-flight processing run.",
        )

    run = _create_run_for_locked_document(session, document)
    session.commit()

    return DocumentUploadResponse(
        document_id=document.id,
        run_id=run.id,
        status=run.status,
        duplicate=False,
    )


def list_document_runs(
    session: Session, document_id: UUID, limit: int = 20
) -> list[DocumentRunSummaryResponse]:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

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

    return [_to_run_summary(document, run) for run in runs]


def get_latest_document_evaluation_detail(session: Session, document_id: UUID):
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    evaluation = get_latest_document_evaluation(session, document)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No evaluation found for the document."
        )
    return evaluation
