from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import DocumentRun, RunStatus
from app.services.cleanup import determine_superseded_run_ids


def _completed_run() -> DocumentRun:
    now = datetime.now(UTC)
    return DocumentRun(
        id=uuid4(),
        document_id=uuid4(),
        run_number=1,
        status=RunStatus.COMPLETED.value,
        created_at=now,
        completed_at=now,
    )


def test_cleanup_keeps_active_and_previous_successful_run() -> None:
    first = _completed_run()
    second = _completed_run()
    third = _completed_run()

    removable = determine_superseded_run_ids(
        successful_runs=[first, second, third],
        active_run_id=first.id,
        keep_previous_successful=1,
    )

    assert removable == [third.id]
