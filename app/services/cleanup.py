from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentFigure,
    DocumentRun,
    DocumentTable,
    DocumentTableSegment,
    RunStatus,
)
from app.services.audit import KNOWN_FAILURE_STAGES
from app.services.storage import StorageService
def cleanup_staging_files(storage_service: StorageService, older_than_seconds: int = 3600) -> int:
    deleted = 0
    cutoff = utcnow() - timedelta(seconds=older_than_seconds)
    for path in storage_service.staging_root.glob("*"):
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
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
        successful_runs = (
            session.execute(
                select(DocumentRun)
                .where(
                    DocumentRun.document_id == document.id,
                    DocumentRun.status == RunStatus.COMPLETED.value,
                )
                .order_by(
                    DocumentRun.completed_at.desc().nullslast(), DocumentRun.created_at.desc()
                )
            )
            .scalars()
            .all()
        )

        removable_ids = determine_superseded_run_ids(
            successful_runs=successful_runs,
            active_run_id=document.active_run_id,
            keep_previous_successful=1,
        )

        for run_id in removable_ids:
            run = session.get(DocumentRun, run_id)
            if run is None:
                continue
            if run.failure_artifact_path:
                Path(run.failure_artifact_path).unlink(missing_ok=True)
            if run.docling_json_path:
                Path(run.docling_json_path).unlink(missing_ok=True)
            if run.yaml_path:
                Path(run.yaml_path).unlink(missing_ok=True)
            run_dir = storage_service.runs_root / str(document.id) / str(run.id)
            storage_service.delete_tree_if_exists(run_dir)
            session.query(DocumentTableSegment).filter(
                DocumentTableSegment.run_id == run.id
            ).delete()
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
    cutoff = utcnow() - timedelta(days=older_than_days)
    failed_runs = (
        session.execute(
            select(DocumentRun).where(
                DocumentRun.status == RunStatus.FAILED.value,
                DocumentRun.completed_at.is_not(None),
                DocumentRun.completed_at < cutoff,
            )
        )
        .scalars()
        .all()
    )

    cleaned = 0
    for run in failed_runs:
        run_dir = storage_service.runs_root / str(run.document_id) / str(run.id)
        if run_dir.exists():
            storage_service.delete_tree_if_exists(run_dir)
            cleaned += 1
        if run.failure_artifact_path:
            run.failure_artifact_path = None
        if run.docling_json_path:
            run.docling_json_path = None
        if run.yaml_path:
            run.yaml_path = None

    if cleaned:
        session.commit()

    return cleaned


def _normalized_failure_stage(run: DocumentRun) -> str | None:
    if run.failure_stage in KNOWN_FAILURE_STAGES:
        return run.failure_stage

    validation_results = run.validation_results_json or {}
    candidate = validation_results.get("failure_stage")
    if candidate in KNOWN_FAILURE_STAGES:
        return str(candidate)

    if (
        run.failure_stage == "legacy_failure"
        and validation_results.get("failure_type") == "ValidationError"
    ):
        return "validation"

    return None


def _rewrite_failure_artifact_stage(path_value: str | None, *, failure_stage: str) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    payload["failure_stage"] = failure_stage
    validation_results = payload.get("validation_results")
    if isinstance(validation_results, dict):
        validation_results["failure_stage"] = failure_stage
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return True


def backfill_legacy_run_audit_fields(session: Session) -> dict[str, int]:
    runs = session.execute(select(DocumentRun)).scalars().all()
    chunk_counts = Counter(
        run_id
        for run_id in session.execute(select(DocumentChunk.run_id)).scalars().all()
        if run_id is not None
    )
    table_counts = Counter(
        run_id
        for run_id in session.execute(select(DocumentTable.run_id)).scalars().all()
        if run_id is not None
    )
    figure_counts = Counter(
        run_id
        for run_id in session.execute(select(DocumentFigure.run_id)).scalars().all()
        if run_id is not None
    )

    chunk_count_backfilled = 0
    table_count_backfilled = 0
    figure_count_backfilled = 0
    failure_stage_backfilled = 0
    failure_artifacts_updated = 0

    for run in runs:
        if run.chunk_count is None:
            run.chunk_count = chunk_counts.get(run.id, 0)
            chunk_count_backfilled += 1
        if run.table_count is None:
            run.table_count = table_counts.get(run.id, 0)
            table_count_backfilled += 1
        if run.figure_count is None:
            run.figure_count = figure_counts.get(run.id, 0)
            figure_count_backfilled += 1

        normalized_failure_stage = _normalized_failure_stage(run)
        if normalized_failure_stage is not None and run.failure_stage != normalized_failure_stage:
            run.failure_stage = normalized_failure_stage
            validation_results = run.validation_results_json or {}
            validation_results["failure_stage"] = normalized_failure_stage
            run.validation_results_json = validation_results
            failure_stage_backfilled += 1
            if _rewrite_failure_artifact_stage(
                run.failure_artifact_path, failure_stage=normalized_failure_stage
            ):
                failure_artifacts_updated += 1

    session.commit()
    return {
        "runs_scanned": len(runs),
        "chunk_count_backfilled": chunk_count_backfilled,
        "table_count_backfilled": table_count_backfilled,
        "figure_count_backfilled": figure_count_backfilled,
        "failure_stage_backfilled": failure_stage_backfilled,
        "failure_artifacts_updated": failure_artifacts_updated,
    }
