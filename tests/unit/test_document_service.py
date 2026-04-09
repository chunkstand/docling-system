from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from fastapi import UploadFile

from app.db.models import Document, DocumentRun, RunStatus
from app.services.documents import _build_duplicate_response, _is_pdf


def test_is_pdf_accepts_pdf_mime() -> None:
    upload = UploadFile(filename="report.bin", file=BytesIO(b"%PDF"), headers={"content-type": "application/pdf"})
    assert _is_pdf(upload) is True


def test_is_pdf_accepts_pdf_filename() -> None:
    upload = UploadFile(filename="report.pdf", file=BytesIO(b"%PDF"))
    assert _is_pdf(upload) is True


def test_duplicate_response_prefers_active_run_status() -> None:
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(timezone.utc)

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

    response = _build_duplicate_response(type("Snapshot", (), {"document": document, "active_run": run, "latest_run": run})())

    assert response.document_id == document_id
    assert response.status == RunStatus.COMPLETED.value
    assert response.active_run_status == RunStatus.COMPLETED.value


def test_non_pdf_rejected() -> None:
    upload = UploadFile(filename="report.txt", file=BytesIO(b"text"), headers={"content-type": "text/plain"})
    assert _is_pdf(upload) is False
