from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.db.models import Document, DocumentRun, RunStatus
from app.services.document_ingest import (
    _is_pdf,
    _validate_local_ingest_path,
    allowed_ingest_roots,
    ingest_local_file,
    ingest_upload,
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

    monkeypatch.setattr("app.services.document_ingest._pdf_page_count", lambda _: 5000)
    monkeypatch.setattr(
        "app.services.document_run_queue._queue_document_run",
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

    monkeypatch.setattr("app.services.document_ingest._pdf_page_count", lambda _: 1)
    monkeypatch.setattr(
        "app.services.document_run_queue.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_key="secret",
            remote_ingest_max_inflight_runs=1,
            local_ingest_allowed_roots=None,
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
            assert (
                exc.detail["message"]
                == "Remote ingest is at capacity. Try again after existing runs finish."
            )
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
        "app.services.document_run_queue._replay_document_upload_response",
        lambda *args, **kwargs: replay_response,
    )
    monkeypatch.setattr(
        "app.services.document_ingest._admit_staged_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("idempotent replay should bypass staged admission")
        ),
    )
    monkeypatch.setattr(
        "app.services.document_ingest.get_settings",
        lambda: SimpleNamespace(
            local_ingest_allowed_roots=None,
            local_ingest_max_file_bytes=1024 * 1024,
            local_ingest_max_pages=10,
        ),
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
        monkeypatch.setattr("app.services.document_ingest.allowed_ingest_roots", lambda: [root])
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
            "app.services.document_ingest.allowed_ingest_roots", lambda: [root / "other"]
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
            "app.services.document_ingest.allowed_ingest_roots", lambda: [root.resolve()]
        )
        monkeypatch.setattr(
            "app.services.document_ingest.get_settings",
            lambda: SimpleNamespace(
                local_ingest_allowed_roots=None,
                local_ingest_max_file_bytes=1024 * 1024, local_ingest_max_pages=10
            ),
        )
        monkeypatch.setattr("app.services.document_ingest._pdf_page_count", lambda _: 11)
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
            "app.services.document_ingest.allowed_ingest_roots", lambda: [root.resolve()]
        )
        monkeypatch.setattr(
            "app.services.document_ingest.get_settings",
            lambda: SimpleNamespace(
                local_ingest_allowed_roots=None,
                local_ingest_max_file_bytes=1024 * 1024, local_ingest_max_pages=10
            ),
        )
        monkeypatch.setattr("app.services.document_ingest._pdf_page_count", lambda _: 5)
        assert _validate_local_ingest_path(file_path) == file_path.resolve()


def testallowed_ingest_roots_include_downloads_by_default(monkeypatch) -> None:
    fake_home = Path("/tmp/fake-home")
    fake_cwd = Path("/tmp/fake-cwd")
    monkeypatch.setattr(
        "app.services.document_ingest.get_settings",
        lambda: SimpleNamespace(local_ingest_allowed_roots=None),
    )
    monkeypatch.setattr("app.core.config.Path.home", lambda: fake_home)
    monkeypatch.setattr("app.core.config.Path.cwd", lambda: fake_cwd)

    roots = allowed_ingest_roots()

    assert roots == [
        fake_cwd.resolve(),
        (fake_home / "Documents").resolve(),
        (fake_home / "Downloads").resolve(),
    ]


def test_local_duplicate_ingest_stages_once_and_deletes_staged_copy(monkeypatch) -> None:
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
        def __init__(self):
            self.staged_path = Path("/tmp/staged.pdf")
            self.deleted_paths: list[Path] = []

        def stage_local_file(self, _source_path, **kwargs):
            assert kwargs["max_file_bytes"] == 1024
            assert kwargs["validate_pdf_header"] is True
            return self.staged_path, "known-sha"

        def delete_file_if_exists(self, path):
            self.deleted_paths.append(path)

    validate_calls: list[bool] = []

    def fake_validate(path: Path, *, enforce_limits: bool = True) -> Path:
        validate_calls.append(enforce_limits)
        return path

    monkeypatch.setattr("app.services.document_ingest._validate_local_ingest_path", fake_validate)
    monkeypatch.setattr(
        "app.services.document_ingest.get_settings",
        lambda: SimpleNamespace(local_ingest_allowed_roots=None, local_ingest_max_file_bytes=1024),
    )

    storage_service = FakeStorageService()
    response, status_code = ingest_local_file(FakeSession(), file_path, storage_service)

    assert status_code == 200
    assert response.duplicate is True
    assert response.document_id == document_id
    assert validate_calls == [False]
    assert storage_service.deleted_paths == [storage_service.staged_path]
