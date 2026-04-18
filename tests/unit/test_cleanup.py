from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.db.models import Document, DocumentRun, RunStatus
from app.services.cleanup import (
    backfill_legacy_run_audit_fields,
    cleanup_expired_failed_run_artifacts,
    determine_superseded_run_ids,
)
from app.services.storage import StorageService


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


def test_cleanup_expired_failed_run_artifacts_deletes_never_active_failed_document_source(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    document_id = uuid4()
    run_id = uuid4()
    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"%PDF-1.4\n")

    storage_service = StorageService(storage_root=tmp_path / "storage")
    run_dir = storage_service.runs_root / str(document_id) / str(run_id)
    run_dir.mkdir(parents=True)
    (run_dir / "failure.json").write_text("{}")

    document = Document(
        id=document_id,
        source_filename="source.pdf",
        source_path=str(source_path),
        sha256="abc",
        mime_type="application/pdf",
        active_run_id=None,
        latest_run_id=run_id,
        created_at=now,
        updated_at=now,
    )
    run = DocumentRun(
        id=run_id,
        document_id=document_id,
        run_number=1,
        status=RunStatus.FAILED.value,
        created_at=now,
        completed_at=now.replace(year=now.year - 1),
        failure_artifact_path=str(run_dir / "failure.json"),
        docling_json_path=str(run_dir / "docling.json"),
        yaml_path=str(run_dir / "document.yaml"),
    )

    class FakeScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeSession:
        def __init__(self) -> None:
            self.committed = False
            self.deleted: list[object] = []
            self.call_index = 0

        def execute(self, _statement):
            self.call_index += 1
            if self.call_index == 1:
                return FakeScalarResult([run])
            if self.call_index == 2:
                return FakeScalarResult([run])
            raise AssertionError("unexpected execute call")

        def get(self, model, key):
            if model is Document and key == document_id:
                return document
            return None

        def delete(self, obj) -> None:
            self.deleted.append(obj)

        def commit(self) -> None:
            self.committed = True

    session = FakeSession()
    cleaned = cleanup_expired_failed_run_artifacts(session, storage_service, older_than_days=7)

    assert cleaned == 1
    assert session.committed is True
    assert document in session.deleted
    assert source_path.exists() is False
