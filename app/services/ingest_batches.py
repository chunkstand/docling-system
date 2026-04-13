from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentRun, IngestBatch, IngestBatchItem, RunStatus
from app.schemas.ingest_batches import (
    IngestBatchDetailResponse,
    IngestBatchItemResponse,
    IngestBatchSummaryResponse,
)
from app.services.documents import _allowed_ingest_roots, ingest_local_file
from app.services.storage import StorageService


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _validate_local_ingest_directory(directory_path: Path) -> Path:
    raw_path = directory_path.expanduser()
    if raw_path.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symlink ingest directories are not allowed.",
        )
    resolved_path = raw_path.resolve()
    if not resolved_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {resolved_path}",
        )
    if not any(resolved_path.is_relative_to(root) for root in _allowed_ingest_roots()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Directory is outside allowed local ingest roots.",
        )
    return resolved_path


def _iter_directory_children(directory_path: Path) -> list[Path]:
    return sorted(directory_path.iterdir(), key=lambda path: str(path).lower())


def _iter_local_pdf_files(directory_path: Path, *, recursive: bool) -> list[Path]:
    pdf_paths: list[Path] = []
    pending_directories = [directory_path]

    while pending_directories:
        current_directory = pending_directories.pop()
        for path in _iter_directory_children(current_directory):
            if path.is_symlink():
                if path.suffix.lower() == ".pdf" and path.exists():
                    pdf_paths.append(path)
                continue
            if path.is_dir():
                if recursive:
                    pending_directories.append(path)
                continue
            if path.is_file() and path.suffix.lower() == ".pdf":
                pdf_paths.append(path)

    return sorted(pdf_paths, key=lambda path: str(path).lower())


def _derive_batch_status(batch: IngestBatch, run_status_counts: dict[str, int]) -> str:
    if batch.status == "failed":
        return "failed"

    if any(
        run_status_counts.get(run_status, 0) > 0
        for run_status in (
            RunStatus.QUEUED.value,
            RunStatus.PROCESSING.value,
            RunStatus.VALIDATING.value,
            RunStatus.RETRY_WAIT.value,
        )
    ):
        return "running"

    if batch.failed_count > 0 or run_status_counts.get(RunStatus.FAILED.value, 0) > 0:
        return "completed_with_errors"

    return "completed"


def _load_batch_rows(
    session: Session,
    batch_id: UUID,
) -> list[tuple[IngestBatchItem, DocumentRun | None]]:
    return (
        session.execute(
            select(IngestBatchItem, DocumentRun)
            .outerjoin(DocumentRun, IngestBatchItem.run_id == DocumentRun.id)
            .where(IngestBatchItem.batch_id == batch_id)
            .order_by(IngestBatchItem.created_at.asc(), IngestBatchItem.relative_path.asc())
        )
        .all()
    )


def _batch_run_status_counts(
    rows: list[tuple[IngestBatchItem, DocumentRun | None]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item, run in rows:
        if run is not None:
            counts[run.status] += 1
        elif item.status == "duplicate":
            counts["duplicate_existing"] += 1
        elif item.status == "failed":
            counts["batch_failed"] += 1
    return dict(sorted(counts.items()))


def _derive_batch_completed_at(
    batch: IngestBatch,
    rows: list[tuple[IngestBatchItem, DocumentRun | None]],
    derived_status: str,
) -> datetime | None:
    if derived_status == "running":
        return None

    run_completed_at_values = [
        run.completed_at
        for _, run in rows
        if run is not None and run.completed_at
    ]
    if run_completed_at_values:
        if batch.completed_at is None:
            return max(run_completed_at_values)
        return max([batch.completed_at, *run_completed_at_values])

    return batch.completed_at


def _to_batch_summary(
    session: Session,
    batch: IngestBatch,
    *,
    rows: list[tuple[IngestBatchItem, DocumentRun | None]] | None = None,
) -> IngestBatchSummaryResponse:
    loaded_rows = rows if rows is not None else _load_batch_rows(session, batch.id)
    run_status_counts = _batch_run_status_counts(loaded_rows)
    derived_status = _derive_batch_status(batch, run_status_counts)
    return IngestBatchSummaryResponse(
        batch_id=batch.id,
        source_type=batch.source_type,
        status=derived_status,
        root_path=batch.root_path,
        recursive=batch.recursive,
        file_count=batch.file_count,
        queued_count=batch.queued_count,
        recovery_queued_count=batch.recovery_queued_count,
        duplicate_count=batch.duplicate_count,
        failed_count=batch.failed_count,
        run_status_counts=run_status_counts,
        error_message=batch.error_message,
        created_at=batch.created_at,
        completed_at=_derive_batch_completed_at(batch, loaded_rows, derived_status),
    )


def _to_batch_item_response(
    item: IngestBatchItem,
    *,
    current_run_status: str | None,
) -> IngestBatchItemResponse:
    return IngestBatchItemResponse(
        batch_item_id=item.id,
        relative_path=item.relative_path,
        source_filename=item.source_filename,
        source_path=item.source_path,
        file_size_bytes=item.file_size_bytes,
        sha256=item.sha256,
        status=item.status,
        status_code=item.status_code,
        document_id=item.document_id,
        run_id=item.run_id,
        current_run_status=current_run_status,
        duplicate=item.duplicate,
        recovery_run=item.recovery_run,
        error_message=item.error_message,
        created_at=item.created_at,
    )


def get_ingest_batch_detail(session: Session, batch_id: UUID) -> IngestBatchDetailResponse:
    batch = session.get(IngestBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingest batch not found: {batch_id}",
        )

    rows = _load_batch_rows(session, batch.id)
    summary = _to_batch_summary(session, batch, rows=rows)
    return IngestBatchDetailResponse(
        **summary.model_dump(),
        items=[
            _to_batch_item_response(
                item,
                current_run_status=run.status if run is not None else None,
            )
            for item, run in rows
        ],
    )


def list_ingest_batches(session: Session, *, limit: int = 20) -> list[IngestBatchSummaryResponse]:
    rows = (
        session.execute(
            select(IngestBatch).order_by(IngestBatch.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_batch_summary(session, row) for row in rows]


def _record_batch_item_success(
    session: Session,
    batch: IngestBatch,
    file_path: Path,
    root_path: Path,
    *,
    payload,
    status_code: int,
) -> None:
    created_at = _utcnow()
    relative_path = str(file_path.relative_to(root_path))
    document = session.get(Document, payload.document_id)
    session.add(
        IngestBatchItem(
            id=uuid.uuid4(),
            batch_id=batch.id,
            relative_path=relative_path,
            source_filename=file_path.name,
            source_path=str(file_path),
            file_size_bytes=file_path.stat().st_size,
            sha256=document.sha256 if document is not None else None,
            status=(
                "queued_recovery"
                if payload.recovery_run and payload.run_id is not None
                else "duplicate"
                if payload.duplicate and not payload.run_id
                else "queued"
            ),
            status_code=status_code,
            document_id=payload.document_id,
            run_id=payload.run_id,
            duplicate=payload.duplicate,
            recovery_run=payload.recovery_run,
            created_at=created_at,
        )
    )
    batch.file_count += 1
    if payload.recovery_run and payload.run_id is not None:
        batch.recovery_queued_count += 1
    elif payload.duplicate and not payload.run_id:
        batch.duplicate_count += 1
    else:
        batch.queued_count += 1
    session.commit()


def _record_batch_item_failure(
    session: Session,
    batch: IngestBatch,
    file_path: Path,
    root_path: Path,
    *,
    status_code: int,
    error_message: str,
) -> None:
    session.add(
        IngestBatchItem(
            id=uuid.uuid4(),
            batch_id=batch.id,
            relative_path=str(file_path.relative_to(root_path)),
            source_filename=file_path.name,
            source_path=str(file_path),
            file_size_bytes=file_path.stat().st_size if file_path.exists() else None,
            status="failed",
            status_code=status_code,
            error_message=error_message,
            created_at=_utcnow(),
        )
    )
    batch.file_count += 1
    batch.failed_count += 1
    session.commit()


def queue_local_ingest_directory(
    session: Session,
    directory_path: Path,
    storage_service: StorageService,
    *,
    recursive: bool = False,
) -> IngestBatchDetailResponse:
    resolved_directory = _validate_local_ingest_directory(directory_path)
    batch = IngestBatch(
        id=uuid.uuid4(),
        source_type="local_directory",
        status="running",
        root_path=str(resolved_directory),
        recursive=recursive,
        created_at=_utcnow(),
    )
    session.add(batch)
    session.commit()

    try:
        pdf_paths = _iter_local_pdf_files(resolved_directory, recursive=recursive)
    except Exception as exc:
        session.rollback()
        batch = session.get(IngestBatch, batch.id)
        if batch is None:
            raise
        batch.status = "failed"
        batch.error_message = f"Directory scan failed: {exc}"
        batch.completed_at = _utcnow()
        session.commit()
        return get_ingest_batch_detail(session, batch.id)

    if not pdf_paths:
        batch.status = "failed"
        batch.error_message = "No PDF files found in the directory."
        batch.completed_at = _utcnow()
        session.commit()
        return get_ingest_batch_detail(session, batch.id)

    for file_path in pdf_paths:
        try:
            payload, status_code = ingest_local_file(session, file_path, storage_service)
            _record_batch_item_success(
                session,
                batch,
                file_path,
                resolved_directory,
                payload=payload,
                status_code=status_code,
            )
        except HTTPException as exc:
            _record_batch_item_failure(
                session,
                batch,
                file_path,
                resolved_directory,
                status_code=exc.status_code,
                error_message=str(exc.detail),
            )
        except Exception as exc:
            session.rollback()
            _record_batch_item_failure(
                session,
                batch,
                file_path,
                resolved_directory,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_message=str(exc),
            )

    batch.status = "completed_with_errors" if batch.failed_count else "completed"
    batch.completed_at = _utcnow()
    session.commit()
    return get_ingest_batch_detail(session, batch.id)
