from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk, DocumentFigure, DocumentRun, DocumentTable, DocumentTableSegment, RunStatus
from app.services.storage import StorageService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cleanup_staging_files(storage_service: StorageService, older_than_seconds: int = 3600) -> int:
    deleted = 0
    cutoff = _utcnow() - timedelta(seconds=older_than_seconds)
    for path in storage_service.staging_root.glob("*"):
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified_at < cutoff:
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def determine_superseded_run_ids(
    successful_runs: list[DocumentRun],
    active_run_id: UUID | None,
    keep_previous_successful: int = 1,
) -> list[UUID]:
    keep_ids: set[UUID] = set()
    if active_run_id is not None:
        keep_ids.add(active_run_id)

    for run in successful_runs:
        if run.id == active_run_id:
            continue
        keep_ids.add(run.id)
        keep_previous_successful -= 1
        if keep_previous_successful <= 0:
            break

    return [run.id for run in successful_runs if run.id not in keep_ids]


def cleanup_superseded_runs(session: Session, storage_service: StorageService) -> int:
    documents = session.execute(select(Document)).scalars().all()
    deleted_runs = 0

    for document in documents:
        successful_runs = session.execute(
            select(DocumentRun)
            .where(
                DocumentRun.document_id == document.id,
                DocumentRun.status == RunStatus.COMPLETED.value,
            )
            .order_by(DocumentRun.completed_at.desc().nullslast(), DocumentRun.created_at.desc())
        ).scalars().all()

        removable_ids = determine_superseded_run_ids(
            successful_runs=successful_runs,
            active_run_id=document.active_run_id,
            keep_previous_successful=1,
        )

        for run_id in removable_ids:
            run = session.get(DocumentRun, run_id)
            if run is None:
                continue
            if run.docling_json_path:
                Path(run.docling_json_path).unlink(missing_ok=True)
            if run.yaml_path:
                Path(run.yaml_path).unlink(missing_ok=True)
            run_dir = storage_service.runs_root / str(document.id) / str(run.id)
            storage_service.delete_tree_if_exists(run_dir)
            session.query(DocumentTableSegment).filter(DocumentTableSegment.run_id == run.id).delete()
            session.query(DocumentTable).filter(DocumentTable.run_id == run.id).delete()
            session.query(DocumentFigure).filter(DocumentFigure.run_id == run.id).delete()
            session.query(DocumentChunk).filter(DocumentChunk.run_id == run.id).delete()
            session.delete(run)
            deleted_runs += 1

    if deleted_runs:
        session.commit()

    return deleted_runs


def cleanup_expired_failed_run_artifacts(
    session: Session,
    storage_service: StorageService,
    older_than_days: int = 7,
) -> int:
    cutoff = _utcnow() - timedelta(days=older_than_days)
    failed_runs = session.execute(
        select(DocumentRun).where(
            DocumentRun.status == RunStatus.FAILED.value,
            DocumentRun.completed_at.is_not(None),
            DocumentRun.completed_at < cutoff,
        )
    ).scalars().all()

    cleaned = 0
    for run in failed_runs:
        run_dir = storage_service.runs_root / str(run.document_id) / str(run.id)
        if run_dir.exists():
            storage_service.delete_tree_if_exists(run_dir)
            cleaned += 1
        if run.docling_json_path:
            run.docling_json_path = None
        if run.yaml_path:
            run.yaml_path = None

    if cleaned:
        session.commit()

    return cleaned
