from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_reprocess_route_returns_accepted(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    def fake_reprocess_document(session, requested_document_id):
        assert requested_document_id == document_id
        return {
            "document_id": str(document_id),
            "run_id": str(run_id),
            "status": "queued",
            "duplicate": False,
            "recovery_run": False,
            "active_run_id": None,
            "active_run_status": None,
        }

    monkeypatch.setattr("app.api.main.reprocess_document", fake_reprocess_document)

    client = TestClient(app)
    response = client.post(f"/documents/{document_id}/reprocess")

    assert response.status_code == 202
    assert response.json()["run_id"] == str(run_id)
