from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_create_document_route_uses_ingest_service(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    async def fake_ingest_upload(session, upload, storage_service):
        return (
            {
                "document_id": str(document_id),
                "run_id": str(run_id),
                "status": "queued",
                "duplicate": False,
                "recovery_run": False,
                "active_run_id": None,
                "active_run_status": None,
            },
            202,
        )

    monkeypatch.setattr("app.api.main.ingest_upload", fake_ingest_upload)

    client = TestClient(app)
    response = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["document_id"] == str(document_id)
    assert body["run_id"] == str(run_id)
    assert body["status"] == "queued"
