from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.db.public.ingest import Document, DocumentRun, RunStatus
from app.services.document_run_queue import (
    _build_duplicate_response,
    _enforce_remote_document_run_backpressure,
    _queue_document_run,
    _resolve_existing_document_upload,
    reprocess_document,
)
from app.services.document_run_views import to_run_summary as _to_run_summary


def test_duplicate_response_prefers_active_run_status() -> None:
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)

    document = Document(
        id=document_id,
        source_filename="report.pdf",
        source_path="/tmp/report.pdf",
        sha256="abc",
        mime_type="application/pdf",
        active_run_id=run_id,
        latest_run_id=run_id,
        created_at=now,
        updated_at=now,
    )
    run = DocumentRun(
        id=run_id,
        document_id=document_id,
        run_number=1,
        status=RunStatus.COMPLETED.value,
        created_at=now,
    )

    response = _build_duplicate_response(
        type("Snapshot", (), {"document": document, "active_run": run, "latest_run": run})()
    )

    assert response.document_id == document_id
    assert response.status == RunStatus.COMPLETED.value
    assert response.active_run_status == RunStatus.COMPLETED.value


def test_enforce_remote_document_run_backpressure_rejects_at_capacity(monkeypatch) -> None:
    class FakeExecuteResult:
        def scalar_one(self):
            return 2

    class FakeSession:
        def execute(self, _statement):
            return FakeExecuteResult()

    monkeypatch.setattr(
        "app.services.document_run_queue.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_key="secret",
            remote_ingest_max_inflight_runs=2,
        ),
    )

    try:
        _enforce_remote_document_run_backpressure(FakeSession())
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.detail["code"] == "rate_limited"
        assert (
            exc.detail["message"]
            == "Remote ingest is at capacity. Try again after existing runs finish."
        )
    else:
        raise AssertionError("Expected remote backpressure to reject the request")


def test_to_run_summary_exposes_live_progress_metadata(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)
    monkeypatch.setattr(
        "app.services.document_run_views.get_settings",
        lambda: SimpleNamespace(worker_lease_timeout_seconds=300),
    )
    monkeypatch.setattr("app.services.document_run_views.utcnow", lambda: now)

    document = Document(
        id=document_id,
        source_filename="report.pdf",
        source_path="/tmp/report.pdf",
        sha256="abc",
        mime_type="application/pdf",
        latest_run_id=run_id,
        created_at=now,
        updated_at=now,
    )
    run = DocumentRun(
        id=run_id,
        document_id=document_id,
        run_number=2,
        status=RunStatus.VALIDATING.value,
        attempts=1,
        locked_at=now,
        locked_by="worker-1",
        last_heartbeat_at=now,
        validation_status="pending",
        chunk_count=12,
        table_count=3,
        figure_count=1,
        validation_results_json={"summary": "Validation passed with warnings.", "warning_count": 2},
        created_at=now,
        started_at=now,
    )

    summary = _to_run_summary(document, run)

    assert summary.current_stage == "validation"
    assert summary.locked_by == "worker-1"
    assert summary.lease_stale is False
    assert summary.validation_warning_count == 2
    assert summary.progress_summary["chunk_count"] == 12
    assert summary.progress_summary["validation_summary"] == "Validation passed with warnings."


def test_resolve_existing_document_upload_uses_locked_state_to_reuse_inflight_run(
    monkeypatch,
) -> None:
    document_id = uuid4()
    stale_run_id = uuid4()
    queued_run_id = uuid4()
    now = datetime.now(UTC)

    stale_document = Document(
        id=document_id,
        source_filename="report.pdf",
        source_path="/tmp/report.pdf",
        sha256="abc",
        mime_type="application/pdf",
        latest_run_id=stale_run_id,
        created_at=now,
        updated_at=now,
    )
    locked_document = Document(
        id=document_id,
        source_filename="report.pdf",
        source_path="/tmp/report.pdf",
        sha256="abc",
        mime_type="application/pdf",
        latest_run_id=queued_run_id,
        created_at=now,
        updated_at=now,
    )
    queued_run = DocumentRun(
        id=queued_run_id,
        document_id=document_id,
        run_number=2,
        status=RunStatus.QUEUED.value,
        created_at=now,
    )

    class FakeSession:
        def get(self, model, value):
            if model is DocumentRun and value == queued_run_id:
                return queued_run
            return None

    monkeypatch.setattr(
        "app.services.document_run_queue._lock_document_row", lambda session, _: locked_document
    )
    monkeypatch.setattr(
        "app.services.document_run_queue._create_run_for_locked_document",
        lambda session, document: (_ for _ in ()).throw(
            AssertionError("new recovery run should not be created")
        ),
    )

    response, status_code = _resolve_existing_document_upload(FakeSession(), stale_document)

    assert status_code == 202
    assert response.run_id == queued_run_id
    assert response.status == RunStatus.QUEUED.value
    assert response.recovery_run is True


def test_queue_document_run_recovers_existing_document_after_sha_conflict(tmp_path: Path) -> None:
    document_id = uuid4()
    run_id = uuid4()
    staged_path = tmp_path / "staged.pdf"
    staged_path.write_bytes(b"%PDF-1.4\n")
    now = datetime.now(UTC)

    existing_document = Document(
        id=document_id,
        source_filename="report.pdf",
        source_path="/tmp/report.pdf",
        sha256="known-sha",
        mime_type="application/pdf",
        active_run_id=run_id,
        latest_run_id=run_id,
        created_at=now,
        updated_at=now,
    )
    active_run = DocumentRun(
        id=run_id,
        document_id=document_id,
        run_number=1,
        status=RunStatus.COMPLETED.value,
        created_at=now,
        completed_at=now,
    )

    class FakeNestedTransaction:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeExecuteResult:
        def scalar_one_or_none(self):
            return existing_document

    class FakeSession:
        def __init__(self) -> None:
            self.flush_count = 0

        def begin_nested(self):
            return FakeNestedTransaction()

        def add(self, _row) -> None:
            return None

        def flush(self) -> None:
            self.flush_count += 1
            if self.flush_count == 1:
                raise IntegrityError("INSERT", {}, Exception("duplicate key"))

        def execute(self, _statement):
            return FakeExecuteResult()

        def get(self, model, value):
            if model is DocumentRun and value == run_id:
                return active_run
            return None

    class FakeStorageService:
        def delete_file_if_exists(self, path: Path) -> None:
            path.unlink(missing_ok=True)

    response, status_code = _queue_document_run(
        FakeSession(),
        FakeStorageService(),
        staged_path=staged_path,
        sha256="known-sha",
        source_filename="report.pdf",
        mime_type="application/pdf",
    )

    assert status_code == 200
    assert response.duplicate is True
    assert response.document_id == document_id
    assert staged_path.exists() is False


def test_reprocess_document_uses_locked_state_to_reject_inflight_run(monkeypatch) -> None:
    document_id = uuid4()
    queued_run_id = uuid4()
    now = datetime.now(UTC)

    locked_document = Document(
        id=document_id,
        source_filename="report.pdf",
        source_path="/tmp/report.pdf",
        sha256="abc",
        mime_type="application/pdf",
        latest_run_id=queued_run_id,
        created_at=now,
        updated_at=now,
    )
    queued_run = DocumentRun(
        id=queued_run_id,
        document_id=document_id,
        run_number=2,
        status=RunStatus.PROCESSING.value,
        created_at=now,
    )

    class FakeSession:
        def get(self, model, value):
            if model is DocumentRun and value == queued_run_id:
                return queued_run
            return None

    monkeypatch.setattr(
        "app.services.document_run_queue._lock_document_row", lambda session, _: locked_document
    )

    try:
        reprocess_document(FakeSession(), document_id)
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "inflight_run_exists"
        assert exc.detail["message"] == "Document already has an in-flight processing run."
    else:
        raise AssertionError("Expected reprocess to reject the in-flight run")


def test_reprocess_document_rejects_when_remote_capacity_reached(monkeypatch) -> None:
    document_id = uuid4()
    now = datetime.now(UTC)

    locked_document = Document(
        id=document_id,
        source_filename="report.pdf",
        source_path="/tmp/report.pdf",
        sha256="abc",
        mime_type="application/pdf",
        latest_run_id=None,
        created_at=now,
        updated_at=now,
    )

    class FakeExecuteResult:
        def scalar_one(self):
            return 1

    class FakeSession:
        def get(self, model, value):
            return None

        def execute(self, _statement):
            return FakeExecuteResult()

    monkeypatch.setattr(
        "app.services.document_run_queue._lock_document_row", lambda session, _: locked_document
    )
    monkeypatch.setattr(
        "app.services.document_run_queue.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_key="secret",
            remote_ingest_max_inflight_runs=1,
        ),
    )
    monkeypatch.setattr(
        "app.services.document_run_queue._create_run_for_locked_document",
        lambda session, document: (_ for _ in ()).throw(
            AssertionError("reprocess should not create a run when remote capacity is exhausted")
        ),
    )

    try:
        reprocess_document(FakeSession(), document_id)
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.detail["code"] == "rate_limited"
        assert (
            exc.detail["message"]
            == "Remote ingest is at capacity. Try again after existing runs finish."
        )
    else:
        raise AssertionError("Expected remote reprocess to reject when capacity is exhausted")


def test_reprocess_document_replays_stored_idempotent_response(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    replay_response = (
        SimpleNamespace(
            document_id=document_id,
            run_id=run_id,
            status=RunStatus.QUEUED.value,
            duplicate=False,
            recovery_run=False,
            active_run_id=None,
            active_run_status=None,
        ),
        202,
    )

    monkeypatch.setattr(
        "app.services.document_run_queue._replay_document_upload_response",
        lambda *args, **kwargs: replay_response,
    )
    monkeypatch.setattr(
        "app.services.document_run_queue._lock_document_row",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("idempotent replay should bypass document locking")
        ),
    )

    payload = reprocess_document(
        SimpleNamespace(),
        document_id,
        idempotency_key="doc-reprocess-1",
    )

    assert payload.document_id == document_id
    assert payload.run_id == run_id
