from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.db.models import Document, DocumentRun, RunStatus
from app.services.documents import (
    _allowed_ingest_roots,
    _build_duplicate_response,
    _is_pdf,
    _validate_local_ingest_path,
)


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
            assert "page count exceeds local ingest limit" in exc.detail
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
