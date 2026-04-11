from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.services.cleanup import (
    cleanup_expired_failed_run_artifacts,
    cleanup_staging_files,
    cleanup_superseded_runs,
)
from app.services.storage import StorageService

logger = get_logger(__name__)


def run_cleanup() -> None:
    storage_service = StorageService()
    session_factory = get_session_factory()

    staged_deleted = cleanup_staging_files(storage_service)
    with session_factory() as session:
        failed_cleaned = cleanup_expired_failed_run_artifacts(session, storage_service)
        superseded_deleted = cleanup_superseded_runs(session, storage_service)

    logger.info(
        "cleanup_complete",
        staged_deleted=staged_deleted,
        failed_artifacts_cleaned=failed_cleaned,
        superseded_runs_deleted=superseded_deleted,
    )
