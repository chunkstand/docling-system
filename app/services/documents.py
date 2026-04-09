from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentRun, RunStatus
from app.schemas.documents import DocumentDetailResponse, DocumentUploadResponse
from app.services.storage import StorageService


PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


@dataclass
class ExistingRunSnapshot:
    document: Document
    active_run: DocumentRun | None
    latest_run: DocumentRun | None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_pdf(upload: UploadFile) -> bool:
    filename = upload.filename or ""
    return upload.content_type in PDF_MIME_TYPES or filename.lower().endswith(".pdf")


def _get_run(session: Session, run_id: UUID | None) -> DocumentRun | None:
    if run_id is None:
        return None
    return session.get(DocumentRun, run_id)


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


async def ingest_upload(
    session: Session,
    upload: UploadFile,
    storage_service: StorageService,
) -> tuple[DocumentUploadResponse, int]:
    if not _is_pdf(upload):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF uploads are supported.")

    staged_path, sha256 = await storage_service.stage_upload(upload)

    try:
        existing = session.execute(select(Document).where(Document.sha256 == sha256)).scalar_one_or_none()
        if existing is not None:
            snapshot = _load_existing_snapshot(session, existing)

            if snapshot.active_run is not None:
                storage_service.delete_file_if_exists(staged_path)
                return _build_duplicate_response(snapshot), status.HTTP_200_OK

            if snapshot.latest_run and snapshot.latest_run.status in {
                RunStatus.QUEUED.value,
                RunStatus.PROCESSING.value,
                RunStatus.RETRY_WAIT.value,
            }:
                storage_service.delete_file_if_exists(staged_path)
                return DocumentUploadResponse(
                    document_id=existing.id,
                    run_id=snapshot.latest_run.id,
                    status=snapshot.latest_run.status,
                    duplicate=True,
                    recovery_run=True,
                ), status.HTTP_202_ACCEPTED

            recovery_run = create_run_for_existing_document(session=session, document=existing)
            session.commit()
            storage_service.delete_file_if_exists(staged_path)
            return _build_recovery_response(existing.id, recovery_run.id), status.HTTP_202_ACCEPTED

        now = _utcnow()
        document = Document(
            source_filename=Path(upload.filename or "document.pdf").name,
            source_path="",
            sha256=sha256,
            mime_type=upload.content_type or "application/pdf",
            created_at=now,
            updated_at=now,
        )
        session.add(document)
        session.flush()

        source_path = storage_service.move_source_file(document.id, staged_path)
        document.source_path = str(source_path)

        document_run = DocumentRun(
            document_id=document.id,
            run_number=1,
            status=RunStatus.QUEUED.value,
            created_at=now,
            next_attempt_at=now,
        )
        session.add(document_run)
        session.flush()

        document.latest_run_id = document_run.id
        document.updated_at = now
        session.commit()

        return (
            DocumentUploadResponse(
                document_id=document.id,
                run_id=document_run.id,
                status=document_run.status,
                duplicate=False,
            ),
            status.HTTP_202_ACCEPTED,
        )
    except Exception:
        storage_service.delete_file_if_exists(staged_path)
        session.rollback()
        raise


def create_run_for_existing_document(session: Session, document: Document) -> DocumentRun:
    now = _utcnow()
    run = DocumentRun(
        document_id=document.id,
        run_number=_next_run_number(session, document.id),
        status=RunStatus.QUEUED.value,
        created_at=now,
        next_attempt_at=now,
    )
    session.add(run)
    session.flush()
    document.latest_run_id = run.id
    document.updated_at = now
    return run


def get_document_detail(session: Session, document_id: UUID) -> DocumentDetailResponse:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    active_run = _get_run(session, document.active_run_id)
    latest_run = _get_run(session, document.latest_run_id)

    return DocumentDetailResponse(
        document_id=document.id,
        source_filename=document.source_filename,
        title=document.title,
        active_run_id=document.active_run_id,
        active_run_status=active_run.status if active_run else None,
        latest_run_id=document.latest_run_id,
        latest_run_status=latest_run.status if latest_run else None,
        is_searchable=document.active_run_id is not None,
        has_json_artifact=bool(active_run and active_run.docling_json_path),
        has_markdown_artifact=bool(active_run and active_run.markdown_path),
        created_at=document.created_at,
        updated_at=document.updated_at,
        latest_error_message=latest_run.error_message if latest_run else None,
    )


def reprocess_document(session: Session, document_id: UUID) -> DocumentUploadResponse:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    latest_run = _get_run(session, document.latest_run_id)
    if latest_run and latest_run.status in {
        RunStatus.QUEUED.value,
        RunStatus.PROCESSING.value,
        RunStatus.RETRY_WAIT.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already has an in-flight processing run.",
        )

    run = create_run_for_existing_document(session, document)
    session.commit()

    return DocumentUploadResponse(
        document_id=document.id,
        run_id=run.id,
        status=run.status,
        duplicate=False,
    )
