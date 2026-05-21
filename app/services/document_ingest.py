from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import default_local_ingest_roots, get_settings
from app.db.public.ingest import Document
from app.schemas.documents import DocumentUploadResponse
from app.services import document_run_queue
from app.services.storage import StorageService

PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


def _is_pdf(upload: UploadFile) -> bool:
    filename = upload.filename or ""
    return upload.content_type in PDF_MIME_TYPES or filename.lower().endswith(".pdf")


def allowed_ingest_roots() -> list[Path]:
    settings = get_settings()
    if settings.local_ingest_allowed_roots:
        return [
            Path(item).expanduser().resolve()
            for item in settings.local_ingest_allowed_roots.split(":")
            if item
        ]
    return default_local_ingest_roots()


def _validate_pdf_artifact(
    file_path: Path,
    *,
    enforce_page_limit: bool = True,
    size_limit_detail: str = "File exceeds local ingest size limit.",
    page_limit_detail_prefix: str = "PDF page count exceeds local ingest limit",
) -> Path:
    settings = get_settings()
    if file_path.stat().st_size > settings.local_ingest_max_file_bytes:
        raise api_error(status.HTTP_400_BAD_REQUEST, "file_size_limit_exceeded", size_limit_detail)
    with file_path.open("rb") as source_file:
        if source_file.read(5) != b"%PDF-":
            raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_pdf", "File is not a valid PDF.")
    if not enforce_page_limit:
        return file_path
    page_count = _pdf_page_count(file_path)
    if page_count <= 0 or page_count > settings.local_ingest_max_pages:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "page_limit_exceeded",
            f"{page_limit_detail_prefix} ({settings.local_ingest_max_pages}).",
        )
    return file_path


def _validate_local_ingest_path(file_path: Path, *, enforce_limits: bool = True) -> Path:
    raw_path = file_path.expanduser()
    if raw_path.is_symlink():
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "symlink_ingest_path_not_allowed",
            "Symlink ingest paths are not allowed.",
        )
    resolved_path = raw_path.resolve()
    if not resolved_path.is_file():
        raise api_error(
            status.HTTP_404_NOT_FOUND, "document_not_found", f"File not found: {resolved_path}"
        )
    if resolved_path.suffix.lower() != ".pdf":
        raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_pdf", "Only PDF files are supported.")
    if not any(resolved_path.is_relative_to(root) for root in allowed_ingest_roots()):
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "local_ingest_path_not_allowed",
            "Path is outside allowed local ingest roots.",
        )
    return _validate_pdf_artifact(resolved_path, enforce_page_limit=enforce_limits)


def _pdf_page_count(file_path: Path) -> int:
    import pypdfium2 as pdfium

    try:
        pdf = pdfium.PdfDocument(str(file_path))
    except Exception as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST, "invalid_pdf", "File is not a valid PDF."
        ) from exc
    try:
        return len(pdf)
    finally:
        pdf.close()


def _admit_staged_document(
    session: Session,
    storage_service: StorageService,
    *,
    staged_path: Path,
    sha256: str,
    source_filename: str,
    mime_type: str,
    size_limit_detail: str,
    page_limit_detail_prefix: str,
    check_existing: bool,
    idempotency_key: str | None = None,
    idempotency_scope: str = document_run_queue.CREATE_DOCUMENT_SCOPE,
    idempotency_fingerprint: str | None = None,
) -> tuple[DocumentUploadResponse, int]:
    try:
        if check_existing:
            existing = session.execute(
                select(Document).where(Document.sha256 == sha256)
            ).scalar_one_or_none()
            if existing is not None:
                storage_service.delete_file_if_exists(staged_path)
                response, status_code = document_run_queue._resolve_existing_document_upload(
                    session, existing
                )
                if idempotency_fingerprint is not None:
                    document_run_queue._store_document_upload_response(
                        session,
                        scope=idempotency_scope,
                        idempotency_key=idempotency_key,
                        request_fingerprint=idempotency_fingerprint,
                        response_payload=response,
                        status_code=status_code,
                    )
                    session.commit()
                return response, status_code

        _validate_pdf_artifact(
            staged_path,
            size_limit_detail=size_limit_detail,
            page_limit_detail_prefix=page_limit_detail_prefix,
        )
        document_run_queue._enforce_remote_document_run_backpressure(session)
        return document_run_queue._queue_document_run(
            session=session,
            storage_service=storage_service,
            staged_path=staged_path,
            sha256=sha256,
            source_filename=source_filename,
            mime_type=mime_type,
            idempotency_key=idempotency_key,
            idempotency_scope=idempotency_scope,
            idempotency_fingerprint=idempotency_fingerprint,
        )
    except Exception:
        storage_service.delete_file_if_exists(staged_path)
        session.rollback()
        raise


def ingest_upload(
    session: Session,
    upload: UploadFile,
    storage_service: StorageService,
    *,
    idempotency_key: str | None = None,
) -> tuple[DocumentUploadResponse, int]:
    if not _is_pdf(upload):
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_pdf",
            "Only PDF uploads are supported.",
        )

    settings = get_settings()
    staged_path, sha256 = storage_service.stage_upload(
        upload,
        max_file_bytes=settings.local_ingest_max_file_bytes,
    )
    request_fingerprint = f"sha256:{sha256}"
    try:
        replay = document_run_queue._replay_document_upload_response(
            session,
            scope=document_run_queue.CREATE_DOCUMENT_SCOPE,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
        if replay is not None:
            storage_service.delete_file_if_exists(staged_path)
            return replay
        return _admit_staged_document(
            session=session,
            storage_service=storage_service,
            staged_path=staged_path,
            sha256=sha256,
            source_filename=upload.filename or "document.pdf",
            mime_type=upload.content_type or "application/pdf",
            size_limit_detail="File exceeds upload size limit.",
            page_limit_detail_prefix="PDF page count exceeds upload limit",
            check_existing=True,
            idempotency_key=idempotency_key,
            idempotency_scope=document_run_queue.CREATE_DOCUMENT_SCOPE,
            idempotency_fingerprint=request_fingerprint,
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
    settings = get_settings()

    staged_path, sha256 = storage_service.stage_local_file(
        file_path,
        max_file_bytes=settings.local_ingest_max_file_bytes,
        validate_pdf_header=True,
        size_limit_detail="File exceeds local ingest size limit.",
    )
    return _admit_staged_document(
        session=session,
        storage_service=storage_service,
        staged_path=staged_path,
        sha256=sha256,
        source_filename=file_path.name,
        mime_type="application/pdf",
        size_limit_detail="File exceeds local ingest size limit.",
        page_limit_detail_prefix="PDF page count exceeds local ingest limit",
        check_existing=True,
    )
