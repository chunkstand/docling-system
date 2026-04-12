from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.db.models import DocumentRun, RunStatus
from app.services.cleanup import backfill_legacy_run_audit_fields, determine_superseded_run_ids


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


def test_backfill_legacy_run_audit_fields_updates_null_counts_and_failure_stage(
    tmp_path: Path,
) -> None:
    run_id = uuid4()
    failure_artifact = tmp_path / "failure.json"
    failure_artifact.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "run_id": str(run_id),
                "failure_stage": "legacy_failure",
                "validation_results": {"failure_stage": "legacy_failure"},
            }
        )
    )
    run = DocumentRun(
        id=run_id,
        document_id=uuid4(),
        run_number=1,
        status=RunStatus.FAILED.value,
        created_at=datetime.now(UTC),
        failure_stage="legacy_failure",
        failure_artifact_path=str(failure_artifact),
        validation_status="failed",
        validation_results_json={"failure_stage": "validation", "failure_type": "ValidationError"},
    )

    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class FakeSession:
        def __init__(self):
            self.committed = False
            self.call_index = 0

        def execute(self, _statement):
            self.call_index += 1
            if self.call_index == 1:
                return FakeScalarResult([run])
            if self.call_index == 2:
                return FakeScalarResult([])
            if self.call_index == 3:
                return FakeScalarResult([])
            if self.call_index == 4:
                return FakeScalarResult([])
            raise AssertionError("unexpected execute call")

        def commit(self):
            self.committed = True

    session = FakeSession()
    summary = backfill_legacy_run_audit_fields(session)

    assert session.committed is True
    assert run.chunk_count == 0
    assert run.table_count == 0
    assert run.figure_count == 0
    assert run.failure_stage == "validation"
    payload = json.loads(failure_artifact.read_text())
    assert payload["failure_stage"] == "validation"
    assert payload["validation_results"]["failure_stage"] == "validation"
    assert summary["failure_stage_backfilled"] == 1
    assert summary["figure_count_backfilled"] == 1
