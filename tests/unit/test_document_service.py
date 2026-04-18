from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from app.db.models import Document, DocumentRun, RunStatus
from app.services.documents import (
    _allowed_ingest_roots,
    _build_duplicate_response,
    _enforce_remote_document_run_backpressure,
    _is_pdf,
    _queue_document_run,
    _resolve_existing_document_upload,
    _to_run_summary,
    _validate_local_ingest_path,
    ingest_upload,
    ingest_local_file,
    reprocess_document,
)
from app.services.storage import StorageService


def test_is_pdf_accepts_pdf_mime() -> None:
    upload = UploadFile(
        filename="report.bin", file=BytesIO(b"%PDF"), headers={"content-type": "application/pdf"}
    )
    assert _is_pdf(upload) is True


def test_is_pdf_accepts_pdf_filename() -> None:
    upload = UploadFile(filename="report.pdf", file=BytesIO(b"%PDF"))
    assert _is_pdf(upload) is True


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


def test_non_pdf_rejected() -> None:
    upload = UploadFile(
        filename="report.txt", file=BytesIO(b"text"), headers={"content-type": "text/plain"}
    )
    assert _is_pdf(upload) is False


def test_upload_ingest_rejects_invalid_pdf_and_cleans_staged_file() -> None:
    upload = UploadFile(
        filename="report.pdf",
        file=BytesIO(b"not-a-pdf"),
        headers={"content-type": "application/pdf"},
    )

    class FakeSession:
        def rollback(self) -> None:
            return None

    with TemporaryDirectory() as temp_dir:
        storage_service = StorageService(storage_root=Path(temp_dir))
        try:
            ingest_upload(FakeSession(), upload, storage_service)
        except HTTPException as exc:
            assert exc.status_code == 400
            assert exc.detail["code"] == "invalid_pdf"
            assert exc.detail["message"] == "File is not a valid PDF."
        else:
            raise AssertionError("Expected invalid upload to be rejected")

        assert list(storage_service.staging_root.iterdir()) == []
        assert list(storage_service.source_root.iterdir()) == []


def test_upload_ingest_rejects_pdf_over_page_limit_before_queueing(monkeypatch) -> None:
    upload = UploadFile(
        filename="report.pdf",
        file=BytesIO(b"%PDF-1.4\nvalid"),
        headers={"content-type": "application/pdf"},
    )

    class FakeExecuteResult:
        def scalar_one_or_none(self):
            return None

    class FakeSession:
        def __init__(self) -> None:
            self.rolled_back = False

        def execute(self, _statement):
            return FakeExecuteResult()

        def rollback(self) -> None:
            self.rolled_back = True

    monkeypatch.setattr("app.services.documents._pdf_page_count", lambda _: 5000)
    monkeypatch.setattr(
        "app.services.documents._queue_document_run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("_queue_document_run should not be reached")
        ),
    )

    with TemporaryDirectory() as temp_dir:
        storage_service = StorageService(storage_root=Path(temp_dir))
        session = FakeSession()
        try:
            ingest_upload(session, upload, storage_service)
        except HTTPException as exc:
            assert exc.status_code == 400
            assert exc.detail["code"] == "page_limit_exceeded"
            assert "PDF page count exceeds upload limit" in exc.detail["message"]
        else:
            raise AssertionError("Expected page-limit upload to be rejected")

        assert session.rolled_back is True
        assert list(storage_service.staging_root.iterdir()) == []
        assert list(storage_service.source_root.iterdir()) == []


def test_enforce_remote_document_run_backpressure_rejects_at_capacity(monkeypatch) -> None:
    class FakeExecuteResult:
        def scalar_one(self):
            return 2

    class FakeSession:
        def execute(self, _statement):
            return FakeExecuteResult()

    monkeypatch.setattr(
        "app.services.documents.get_settings",
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
        assert exc.detail["message"] == "Remote ingest is at capacity. Try again after existing runs finish."
    else:
        raise AssertionError("Expected remote backpressure to reject the request")


def test_upload_ingest_rejects_when_remote_capacity_reached_and_cleans_staging(
    monkeypatch,
) -> None:
    upload = UploadFile(
        filename="report.pdf",
        file=BytesIO(b"%PDF-1.4\nvalid"),
        headers={"content-type": "application/pdf"},
    )

    class FakeExecuteResult:
        def __init__(self, value) -> None:
            self.value = value

        def scalar_one_or_none(self):
            return self.value

        def scalar_one(self):
            return self.value

    class FakeSession:
        def __init__(self) -> None:
            self.rolled_back = False
            self._results = iter([None, 1])

        def execute(self, _statement):
            return FakeExecuteResult(next(self._results))

        def rollback(self) -> None:
            self.rolled_back = True

    monkeypatch.setattr("app.services.documents._pdf_page_count", lambda _: 1)
    monkeypatch.setattr(
        "app.services.documents.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_key="secret",
            remote_ingest_max_inflight_runs=1,
            local_ingest_max_file_bytes=1024 * 1024,
            local_ingest_max_pages=10,
        ),
    )

    with TemporaryDirectory() as temp_dir:
        storage_service = StorageService(storage_root=Path(temp_dir))
        session = FakeSession()
        try:
            ingest_upload(session, upload, storage_service)
        except HTTPException as exc:
            assert exc.status_code == 429
            assert exc.detail["code"] == "rate_limited"
            assert exc.detail["message"] == "Remote ingest is at capacity. Try again after existing runs finish."
        else:
            raise AssertionError("Expected remote ingest to reject when capacity is exhausted")

        assert session.rolled_back is True
        assert list(storage_service.staging_root.iterdir()) == []
        assert list(storage_service.source_root.iterdir()) == []


def test_upload_ingest_replays_idempotent_response_without_new_queueing(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    upload = UploadFile(
        filename="report.pdf",
        file=BytesIO(b"%PDF-1.4\nvalid"),
        headers={"content-type": "application/pdf"},
    )

    class FakeSession:
        def rollback(self) -> None:
            return None

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
        "app.services.documents._replay_document_upload_response",
        lambda *args, **kwargs: replay_response,
    )
    monkeypatch.setattr(
        "app.services.documents._admit_staged_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("idempotent replay should bypass staged admission")
        ),
    )
    monkeypatch.setattr(
        "app.services.documents.get_settings",
        lambda: SimpleNamespace(local_ingest_max_file_bytes=1024 * 1024, local_ingest_max_pages=10),
    )

    with TemporaryDirectory() as temp_dir:
        storage_service = StorageService(storage_root=Path(temp_dir))
        payload, status_code = ingest_upload(
            FakeSession(),
            upload,
            storage_service,
            idempotency_key="doc-create-1",
        )

        assert payload.document_id == document_id
        assert payload.run_id == run_id
        assert status_code == 202
        assert list(storage_service.staging_root.iterdir()) == []


def test_local_ingest_rejects_symlink(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = root / "doc.pdf"
        target.write_bytes(b"%PDF-1.4")
        link = root / "link.pdf"
        link.symlink_to(target)
        monkeypatch.setattr("app.services.documents._allowed_ingest_roots", lambda: [root])
        try:
            _validate_local_ingest_path(link)
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError("Expected symlink ingest to be rejected")


def test_local_ingest_rejects_path_outside_allowed_roots(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        file_path = root / "doc.pdf"
        file_path.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(
            "app.services.documents._allowed_ingest_roots", lambda: [root / "other"]
        )
        try:
            _validate_local_ingest_path(file_path)
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError("Expected out-of-root ingest to be rejected")


def test_local_ingest_rejects_pdf_over_page_limit(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        file_path = root / "doc.pdf"
        file_path.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(
            "app.services.documents._allowed_ingest_roots", lambda: [root.resolve()]
        )
        monkeypatch.setattr(
            "app.services.documents.get_settings",
            lambda: SimpleNamespace(
                local_ingest_max_file_bytes=1024 * 1024, local_ingest_max_pages=10
            ),
        )
        monkeypatch.setattr("app.services.documents._pdf_page_count", lambda _: 11)
        try:
            _validate_local_ingest_path(file_path)
        except HTTPException as exc:
            assert exc.status_code == 400
            assert exc.detail["code"] == "page_limit_exceeded"
            assert "page count exceeds local ingest limit" in exc.detail["message"]
        else:
            raise AssertionError("Expected page limit ingest check to reject the PDF")


def test_local_ingest_accepts_pdf_within_page_limit(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        file_path = root / "doc.pdf"
        file_path.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(
            "app.services.documents._allowed_ingest_roots", lambda: [root.resolve()]
        )
        monkeypatch.setattr(
            "app.services.documents.get_settings",
            lambda: SimpleNamespace(
                local_ingest_max_file_bytes=1024 * 1024, local_ingest_max_pages=10
            ),
        )
        monkeypatch.setattr("app.services.documents._pdf_page_count", lambda _: 5)
        assert _validate_local_ingest_path(file_path) == file_path.resolve()


def test_allowed_ingest_roots_include_downloads_by_default(monkeypatch) -> None:
    fake_home = Path("/tmp/fake-home")
    fake_cwd = Path("/tmp/fake-cwd")
    monkeypatch.setattr(
        "app.services.documents.get_settings",
        lambda: SimpleNamespace(local_ingest_allowed_roots=None),
    )
    monkeypatch.setattr("app.core.config.Path.home", lambda: fake_home)
    monkeypatch.setattr("app.core.config.Path.cwd", lambda: fake_cwd)

    roots = _allowed_ingest_roots()

    assert roots == [
        fake_cwd.resolve(),
        (fake_home / "Documents").resolve(),
        (fake_home / "Downloads").resolve(),
    ]


def test_local_duplicate_ingest_bypasses_limit_checks_and_staging(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)
    file_path = Path("/tmp/duplicate.pdf")

    document = Document(
        id=document_id,
        source_filename="duplicate.pdf",
        source_path="/tmp/source.pdf",
        sha256="known-sha",
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
        completed_at=now,
    )

    class FakeExecuteResult:
        def scalar_one_or_none(self):
            return document

    class FakeSession:
        def execute(self, _statement):
            return FakeExecuteResult()

        def get(self, model, value):
            if model is DocumentRun and value == run_id:
                return run
            return None

    class FakeStorageService:
        def stage_local_file(self, _source_path):
            raise AssertionError("stage_local_file should not be called for duplicates")

    validate_calls: list[bool] = []

    def fake_validate(path: Path, *, enforce_limits: bool = True) -> Path:
        validate_calls.append(enforce_limits)
        return path

    monkeypatch.setattr("app.services.documents._validate_local_ingest_path", fake_validate)
    monkeypatch.setattr("app.services.documents._sha256_file", lambda _: "known-sha")

    response, status_code = ingest_local_file(FakeSession(), file_path, FakeStorageService())

    assert status_code == 200
    assert response.duplicate is True
    assert response.document_id == document_id
    assert validate_calls == [False]


def test_to_run_summary_exposes_live_progress_metadata(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)
    monkeypatch.setattr(
        "app.services.documents.get_settings",
        lambda: SimpleNamespace(worker_lease_timeout_seconds=300),
    )
    monkeypatch.setattr("app.services.documents.utcnow", lambda: now)

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

    monkeypatch.setattr("app.services.documents._lock_document_row", lambda session, _: locked_document)
    monkeypatch.setattr(
        "app.services.documents._create_run_for_locked_document",
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

    monkeypatch.setattr("app.services.documents._lock_document_row", lambda session, _: locked_document)

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

    monkeypatch.setattr("app.services.documents._lock_document_row", lambda session, _: locked_document)
    monkeypatch.setattr(
        "app.services.documents.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_key="secret",
            remote_ingest_max_inflight_runs=1,
        ),
    )
    monkeypatch.setattr(
        "app.services.documents._create_run_for_locked_document",
        lambda session, document: (_ for _ in ()).throw(
            AssertionError("reprocess should not create a run when remote capacity is exhausted")
        ),
    )

    try:
        reprocess_document(FakeSession(), document_id)
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.detail["code"] == "rate_limited"
        assert exc.detail["message"] == "Remote ingest is at capacity. Try again after existing runs finish."
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
        "app.services.documents._replay_document_upload_response",
        lambda *args, **kwargs: replay_response,
    )
    monkeypatch.setattr(
        "app.services.documents._lock_document_row",
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
