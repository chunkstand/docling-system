from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
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


IN_FLIGHT_RUN_STATUSES = {
    RunStatus.QUEUED.value,
    RunStatus.PROCESSING.value,
    RunStatus.VALIDATING.value,
    RunStatus.RETRY_WAIT.value,
}


@dataclass(frozen=True)
class BatchItemResolution:
    resolved_status: str
    resolution_reason: str | None
    resolved_document_id: UUID | None
    resolved_run_id: UUID | None
    resolved_at: datetime | None


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


def _derive_batch_status(
    batch: IngestBatch,
    run_status_counts: dict[str, int],
    resolution_counts: dict[str, int] | None = None,
) -> str:
    if batch.status == "failed":
        return "failed"

    if resolution_counts is not None:
        if resolution_counts.get("running", 0) > 0:
            return "running"
        if resolution_counts.get("failed", 0) > 0:
            return "completed_with_errors"
        return "completed"

    if any(run_status_counts.get(run_status, 0) > 0 for run_status in IN_FLIGHT_RUN_STATUSES):
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


def _batch_resolution_counts(resolutions: list[BatchItemResolution]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for resolution in resolutions:
        counts[resolution.resolved_status] += 1
    return dict(sorted(counts.items()))


def _load_referenced_documents(
    session: Session,
    rows: list[tuple[IngestBatchItem, DocumentRun | None]],
) -> dict[UUID, Document]:
    document_ids = {item.document_id for item, _ in rows if item.document_id is not None}
    if not document_ids:
        return {}
    documents = (
        session.execute(select(Document).where(Document.id.in_(document_ids))).scalars().all()
    )
    return {document.id: document for document in documents}


def _load_referenced_runs(
    session: Session,
    documents: dict[UUID, Document],
) -> dict[UUID, DocumentRun]:
    run_ids = {
        run_id
        for document in documents.values()
        for run_id in (document.active_run_id, document.latest_run_id)
        if run_id is not None
    }
    if not run_ids:
        return {}
    runs = session.execute(select(DocumentRun).where(DocumentRun.id.in_(run_ids))).scalars().all()
    return {run.id: run for run in runs}


def _resolve_batch_item(
    item: IngestBatchItem,
    *,
    current_run: DocumentRun | None,
    document: Document | None,
    active_run: DocumentRun | None,
    latest_run: DocumentRun | None,
) -> BatchItemResolution:
    if item.status == "failed":
        return BatchItemResolution(
            resolved_status="failed",
            resolution_reason="ingest_rejected",
            resolved_document_id=None,
            resolved_run_id=None,
            resolved_at=None,
        )

    if item.duplicate and item.run_id is None:
        resolved_run = active_run or latest_run
        return BatchItemResolution(
            resolved_status="duplicate",
            resolution_reason="existing_document_reused",
            resolved_document_id=item.document_id,
            resolved_run_id=resolved_run.id if resolved_run is not None else None,
            resolved_at=resolved_run.completed_at if resolved_run is not None else None,
        )

    if current_run is not None and current_run.status in IN_FLIGHT_RUN_STATUSES:
        return BatchItemResolution(
            resolved_status="running",
            resolution_reason="run_in_progress",
            resolved_document_id=item.document_id,
            resolved_run_id=current_run.id,
            resolved_at=None,
        )

    if current_run is not None and current_run.status == RunStatus.COMPLETED.value:
        return BatchItemResolution(
            resolved_status="recovered" if item.recovery_run else "completed",
            resolution_reason="run_completed",
            resolved_document_id=item.document_id,
            resolved_run_id=current_run.id,
            resolved_at=current_run.completed_at,
        )

    if latest_run is not None and latest_run.status in IN_FLIGHT_RUN_STATUSES:
        return BatchItemResolution(
            resolved_status="running",
            resolution_reason="followup_run_in_progress",
            resolved_document_id=document.id if document is not None else item.document_id,
            resolved_run_id=latest_run.id,
            resolved_at=None,
        )

    if current_run is not None and current_run.status == RunStatus.FAILED.value:
        winning_run = None
        if active_run is not None and active_run.id != current_run.id:
            winning_run = active_run
        elif latest_run is not None and latest_run.id != current_run.id:
            winning_run = latest_run
        if winning_run is not None and winning_run.status == RunStatus.COMPLETED.value:
            return BatchItemResolution(
                resolved_status="recovered",
                resolution_reason="superseded_by_later_successful_run",
                resolved_document_id=document.id if document is not None else item.document_id,
                resolved_run_id=winning_run.id,
                resolved_at=winning_run.completed_at,
            )

    if active_run is not None and active_run.status == RunStatus.COMPLETED.value:
        return BatchItemResolution(
            resolved_status="recovered" if item.recovery_run else "completed",
            resolution_reason="active_run_available",
            resolved_document_id=document.id if document is not None else item.document_id,
            resolved_run_id=active_run.id,
            resolved_at=active_run.completed_at,
        )

    return BatchItemResolution(
        resolved_status="failed",
        resolution_reason="run_failed_without_successor",
        resolved_document_id=item.document_id,
        resolved_run_id=current_run.id if current_run is not None else None,
        resolved_at=current_run.completed_at if current_run is not None else None,
    )


def _derive_batch_completed_at(
    batch: IngestBatch,
    rows: list[tuple[IngestBatchItem, DocumentRun | None]],
    resolutions: list[BatchItemResolution],
    derived_status: str,
) -> datetime | None:
    if derived_status == "running":
        return None

    run_completed_at_values = [
        run.completed_at
        for _, run in rows
        if run is not None and run.completed_at
    ]
    resolution_completed_at_values = [
        resolution.resolved_at for resolution in resolutions if resolution.resolved_at is not None
    ]
    if run_completed_at_values:
        if batch.completed_at is None:
            return max([*run_completed_at_values, *resolution_completed_at_values])
        return max([batch.completed_at, *run_completed_at_values, *resolution_completed_at_values])

    if resolution_completed_at_values:
        if batch.completed_at is None:
            return max(resolution_completed_at_values)
        return max([batch.completed_at, *resolution_completed_at_values])

    return batch.completed_at


def _to_batch_summary(
    session: Session,
    batch: IngestBatch,
    *,
    rows: list[tuple[IngestBatchItem, DocumentRun | None]] | None = None,
) -> IngestBatchSummaryResponse:
    loaded_rows = rows if rows is not None else _load_batch_rows(session, batch.id)
    run_status_counts = _batch_run_status_counts(loaded_rows)
    documents_by_id = _load_referenced_documents(session, loaded_rows)
    referenced_runs = _load_referenced_runs(session, documents_by_id)
    resolutions = [
        _resolve_batch_item(
            item,
            current_run=run,
            document=documents_by_id.get(item.document_id) if item.document_id is not None else None,
            active_run=referenced_runs.get(documents_by_id[item.document_id].active_run_id)
            if item.document_id is not None
            and item.document_id in documents_by_id
            and documents_by_id[item.document_id].active_run_id is not None
            else None,
            latest_run=referenced_runs.get(documents_by_id[item.document_id].latest_run_id)
            if item.document_id is not None
            and item.document_id in documents_by_id
            and documents_by_id[item.document_id].latest_run_id is not None
            else None,
        )
        for item, run in loaded_rows
    ]
    resolution_counts = _batch_resolution_counts(resolutions)
    derived_status = _derive_batch_status(batch, run_status_counts, resolution_counts)
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
        resolution_counts=resolution_counts,
        error_message=batch.error_message,
        created_at=batch.created_at,
        completed_at=_derive_batch_completed_at(batch, loaded_rows, resolutions, derived_status),
    )


def _to_batch_item_response(
    item: IngestBatchItem,
    *,
    current_run_status: str | None,
    resolution: BatchItemResolution,
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
        resolved_status=resolution.resolved_status,
        resolution_reason=resolution.resolution_reason,
        resolved_document_id=resolution.resolved_document_id,
        resolved_run_id=resolution.resolved_run_id,
        resolved_at=resolution.resolved_at,
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
    documents_by_id = _load_referenced_documents(session, rows)
    referenced_runs = _load_referenced_runs(session, documents_by_id)
    return IngestBatchDetailResponse(
        **summary.model_dump(),
        items=[
            _to_batch_item_response(
                item,
                current_run_status=run.status if run is not None else None,
                resolution=_resolve_batch_item(
                    item,
                    current_run=run,
                    document=(
                        documents_by_id.get(item.document_id) if item.document_id is not None else None
                    ),
                    active_run=referenced_runs.get(documents_by_id[item.document_id].active_run_id)
                    if item.document_id is not None
                    and item.document_id in documents_by_id
                    and documents_by_id[item.document_id].active_run_id is not None
                    else None,
                    latest_run=referenced_runs.get(documents_by_id[item.document_id].latest_run_id)
                    if item.document_id is not None
                    and item.document_id in documents_by_id
                    and documents_by_id[item.document_id].latest_run_id is not None
                    else None,
                ),
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
