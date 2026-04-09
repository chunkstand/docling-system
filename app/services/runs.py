from __future__ import annotations

import os
import socket
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, DocumentRun, RunStatus
from app.schemas.chunks import DocumentChunkResponse
from app.services.docling_parser import DoclingParser, ParsedDocument
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.storage import StorageService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


logger = get_logger(__name__)


def is_retryable_error(exc: Exception) -> bool:
    return not isinstance(exc, ValueError)


def requeue_stale_runs(session: Session) -> int:
    settings = get_settings()
    stale_before = _utcnow() - timedelta(seconds=settings.worker_lease_timeout_seconds)
    stale_runs = session.execute(
        select(DocumentRun).where(
            DocumentRun.status == RunStatus.PROCESSING.value,
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
            run.completed_at = _utcnow()
            run.error_message = run.error_message or "Run exceeded max attempts after stale lease."
        else:
            run.status = RunStatus.RETRY_WAIT.value
            run.next_attempt_at = _utcnow()
        updated += 1

    if updated:
        session.commit()
        logger.info("stale_runs_requeued", count=updated)

    return updated


def claim_next_run(session: Session, worker_id: str) -> DocumentRun | None:
    now = _utcnow()
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
    run.attempts += 1
    session.commit()
    session.refresh(run)
    logger.info("run_claimed", run_id=str(run.id), document_id=str(run.document_id), worker_id=worker_id)
    return run


def heartbeat_run(session: Session, run: DocumentRun) -> None:
    run.last_heartbeat_at = _utcnow()
    session.commit()


def _persist_parsed_artifacts(
    storage_service: StorageService,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
) -> tuple[Path, Path]:
    json_path = storage_service.get_docling_json_path(document.id, run.id)
    markdown_path = storage_service.get_markdown_path(document.id, run.id)
    json_path.write_text(parsed.docling_json)
    markdown_path.write_text(parsed.markdown)
    return json_path, markdown_path


def _replace_run_chunks(session: Session, document: Document, run: DocumentRun, parsed: ParsedDocument) -> None:
    for chunk in parsed.chunks:
        session.add(
            DocumentChunk(
                document_id=document.id,
                run_id=run.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                heading=chunk.heading,
                page_from=chunk.page_from,
                page_to=chunk.page_to,
                metadata_json=chunk.metadata,
                embedding=chunk.embedding,
                created_at=_utcnow(),
            )
        )


def finalize_run_success(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
    json_path: Path,
    markdown_path: Path,
) -> None:
    now = _utcnow()
    run.locked_at = None
    run.locked_by = None
    run.last_heartbeat_at = None
    run.next_attempt_at = None
    run.docling_json_path = str(json_path)
    run.markdown_path = str(markdown_path)
    run.chunk_count = len(parsed.chunks)
    run.completed_at = now
    run.status = RunStatus.COMPLETED.value
    document.active_run_id = run.id
    document.latest_run_id = run.id
    document.title = parsed.title
    document.page_count = parsed.page_count
    document.updated_at = now
    session.commit()


def finalize_run_failure(session: Session, run: DocumentRun, exc: Exception) -> None:
    settings = get_settings()
    now = _utcnow()
    run.locked_at = None
    run.locked_by = None
    run.last_heartbeat_at = None
    run.error_message = str(exc)

    if is_retryable_error(exc) and run.attempts < settings.worker_max_attempts:
        backoff_seconds = min(60, 2 ** max(run.attempts - 1, 0))
        run.status = RunStatus.RETRY_WAIT.value
        run.next_attempt_at = now + timedelta(seconds=backoff_seconds)
    else:
        run.status = RunStatus.FAILED.value
        run.completed_at = now

    session.commit()


def process_run(
    session: Session,
    run_id: UUID,
    storage_service: StorageService,
    parser: DoclingParser,
    embedding_provider: EmbeddingProvider | None = None,
) -> None:
    run = session.get(DocumentRun, run_id)
    if run is None:
        raise ValueError(f"Run {run_id} does not exist.")

    document = session.get(Document, run.document_id)
    if document is None:
        raise ValueError(f"Document {run.document_id} does not exist.")

    try:
        logger.info("run_processing_started", run_id=str(run.id), document_id=str(document.id))
        heartbeat_run(session, run)
        parsed = parser.parse_pdf(Path(document.source_path))
        heartbeat_run(session, run)
        provider = embedding_provider or get_embedding_provider()
        embeddings = provider.embed_texts([chunk.text for chunk in parsed.chunks])
        for chunk, embedding in zip(parsed.chunks, embeddings, strict=True):
            chunk.embedding = embedding

        json_path, markdown_path = _persist_parsed_artifacts(storage_service, document, run, parsed)
        _replace_run_chunks(session, document, run, parsed)
        finalize_run_success(session, document, run, parsed, json_path, markdown_path)
        logger.info(
            "run_processing_completed",
            run_id=str(run.id),
            document_id=str(document.id),
            chunk_count=len(parsed.chunks),
            page_count=parsed.page_count,
        )
    except Exception as exc:
        session.rollback()
        run = session.get(DocumentRun, run_id)
        if run is None:
            raise
        finalize_run_failure(session, run, exc)
        logger.exception("run_processing_failed", run_id=str(run.id), document_id=str(document.id), error=str(exc))


def get_active_chunks(session: Session, document_id: UUID) -> list[DocumentChunkResponse]:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.active_run_id is None:
        return []

    rows = session.execute(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.run_id == document.active_run_id,
        )
        .order_by(DocumentChunk.chunk_index)
    ).scalars()

    return [
        DocumentChunkResponse(
            chunk_id=row.id,
            document_id=row.document_id,
            run_id=row.run_id,
            chunk_index=row.chunk_index,
            text=row.text,
            heading=row.heading,
            page_from=row.page_from,
            page_to=row.page_to,
            metadata=row.metadata_json,
            created_at=row.created_at,
        )
        for row in rows
    ]


def run_worker_loop() -> None:
    from app.db.session import get_session_factory

    settings = get_settings()
    session_factory = get_session_factory()
    storage_service = StorageService()
    parser = DoclingParser()
    embedding_provider = get_embedding_provider()
    worker_id = get_worker_identity()

    while True:
        with session_factory() as session:
            requeue_stale_runs(session)
            run = claim_next_run(session, worker_id)
            if run is None:
                time.sleep(settings.worker_poll_seconds)
                continue

            process_run(
                session=session,
                run_id=run.id,
                storage_service=storage_service,
                parser=parser,
                embedding_provider=embedding_provider,
            )
