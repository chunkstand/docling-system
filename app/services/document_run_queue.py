from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import get_settings, resolve_api_mode
from app.core.time import utcnow
from app.db.public.ingest import Document, DocumentRun, RunStatus
from app.schemas.documents import DocumentUploadResponse
from app.services.idempotency import get_idempotent_response, store_idempotent_response
from app.services.storage import StorageService

CREATE_DOCUMENT_SCOPE = "documents.create"
REPROCESS_DOCUMENT_SCOPE = "documents.reprocess"
INFLIGHT_RUN_STATUSES = {
    RunStatus.QUEUED.value,
    RunStatus.PROCESSING.value,
    RunStatus.VALIDATING.value,
    RunStatus.RETRY_WAIT.value,
}


def _get_run_record(session: Session, run_id: UUID | None) -> DocumentRun | None:
    if run_id is None:
        return None
    return session.get(DocumentRun, run_id)


@dataclass
class ExistingRunSnapshot:
    document: Document
    active_run: DocumentRun | None
    latest_run: DocumentRun | None


def _load_existing_snapshot(session: Session, document: Document) -> ExistingRunSnapshot:
    return ExistingRunSnapshot(
        document=document,
        active_run=_get_run_record(session, document.active_run_id),
        latest_run=_get_run_record(session, document.latest_run_id),
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


def _replay_document_upload_response(
    session: Session,
    *,
    scope: str,
    idempotency_key: str | None,
    request_fingerprint: str,
) -> tuple[DocumentUploadResponse, int] | None:
    stored = get_idempotent_response(
        session,
        scope=scope,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    if stored is None:
        return None
    payload, status_code = stored
    return DocumentUploadResponse.model_validate(payload), status_code


def _store_document_upload_response(
    session: Session,
    *,
    scope: str,
    idempotency_key: str | None,
    request_fingerprint: str,
    response_payload: DocumentUploadResponse,
    status_code: int,
) -> None:
    store_idempotent_response(
        session,
        scope=scope,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        response_payload=response_payload.model_dump(mode="json"),
        status_code=status_code,
    )


def _document_run_inflight_count(session: Session) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(DocumentRun)
            .where(DocumentRun.status.in_(INFLIGHT_RUN_STATUSES))
        ).scalar_one()
    )


def _enforce_remote_document_run_backpressure(session: Session) -> None:
    settings = get_settings()
    if resolve_api_mode(settings) != "remote":
        return
    limit = settings.remote_ingest_max_inflight_runs
    if limit is None or limit <= 0:
        return
    if _document_run_inflight_count(session) < limit:
        return
    raise api_error(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "rate_limited",
        "Remote ingest is at capacity. Try again after existing runs finish.",
    )


def _resolve_existing_document_upload(
    session: Session,
    existing: Document,
) -> tuple[DocumentUploadResponse, int]:
    locked_document = _lock_document_row(session, existing.id)
    if locked_document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "document_not_found", "Document not found.")
    snapshot = _load_existing_snapshot(session, locked_document)

    if snapshot.active_run is not None:
        return _build_duplicate_response(snapshot), status.HTTP_200_OK

    if snapshot.latest_run and snapshot.latest_run.status in INFLIGHT_RUN_STATUSES:
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
    idempotency_key: str | None = None,
    idempotency_scope: str = CREATE_DOCUMENT_SCOPE,
    idempotency_fingerprint: str | None = None,
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
        existing = session.execute(
            select(Document).where(Document.sha256 == sha256)
        ).scalar_one_or_none()
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
        response = DocumentUploadResponse(
            document_id=document.id,
            run_id=document_run.id,
            status=document_run.status,
            duplicate=False,
        )
        if idempotency_fingerprint is not None:
            _store_document_upload_response(
                session,
                scope=idempotency_scope,
                idempotency_key=idempotency_key,
                request_fingerprint=idempotency_fingerprint,
                response_payload=response,
                status_code=status.HTTP_202_ACCEPTED,
            )
        session.commit()
    except Exception:
        storage_service.delete_file_if_exists(source_path)
        raise

    return response, status.HTTP_202_ACCEPTED


def create_run_for_existing_document(session: Session, document: Document) -> DocumentRun:
    locked_document = _lock_document_row(session, document.id)
    if locked_document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "document_not_found", "Document not found.")
    return _create_run_for_locked_document(session, locked_document)


def reprocess_document(
    session: Session,
    document_id: UUID,
    *,
    idempotency_key: str | None = None,
) -> DocumentUploadResponse:
    request_fingerprint = f"document:{document_id}"
    replay = _replay_document_upload_response(
        session,
        scope=REPROCESS_DOCUMENT_SCOPE,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    if replay is not None:
        response, _ = replay
        return response

    document = _lock_document_row(session, document_id)
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "document_not_found", "Document not found.")

    latest_run = _get_run_record(session, document.latest_run_id)
    if latest_run and latest_run.status in INFLIGHT_RUN_STATUSES:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "inflight_run_exists",
            "Document already has an in-flight processing run.",
        )

    _enforce_remote_document_run_backpressure(session)
    run = _create_run_for_locked_document(session, document)
    response = DocumentUploadResponse(
        document_id=document.id,
        run_id=run.id,
        status=run.status,
        duplicate=False,
    )
    _store_document_upload_response(
        session,
        scope=REPROCESS_DOCUMENT_SCOPE,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        response_payload=response,
        status_code=status.HTTP_202_ACCEPTED,
    )
    session.commit()
    return response
