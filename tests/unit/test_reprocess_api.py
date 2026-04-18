from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.main import app


def test_reprocess_route_returns_accepted(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    def fake_reprocess_document(session, requested_document_id, *, idempotency_key=None):
        assert requested_document_id == document_id
        assert idempotency_key is None
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
    assert response.headers["Location"] == f"/runs/{run_id}"
    assert response.json()["run_id"] == str(run_id)


def test_reprocess_route_passes_idempotency_key(monkeypatch) -> None:
    document_id = uuid4()
    captured: dict = {}

    def fake_reprocess_document(session, requested_document_id, *, idempotency_key=None):
        assert requested_document_id == document_id
        captured["idempotency_key"] = idempotency_key
        return {
            "document_id": str(document_id),
            "run_id": str(uuid4()),
            "status": "queued",
            "duplicate": False,
            "recovery_run": False,
            "active_run_id": None,
            "active_run_status": None,
        }

    monkeypatch.setattr("app.api.main.reprocess_document", fake_reprocess_document)

    client = TestClient(app)
    response = client.post(
        f"/documents/{document_id}/reprocess",
        headers={"Idempotency-Key": "doc-reprocess-1"},
    )

    assert response.status_code == 202
    assert captured["idempotency_key"] == "doc-reprocess-1"


def test_reprocess_route_returns_machine_readable_error_code(monkeypatch) -> None:
    document_id = uuid4()

    def fake_reprocess_document(session, requested_document_id, *, idempotency_key=None):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "Remote ingest is at capacity. Try again after existing runs finish.",
            },
        )

    monkeypatch.setattr("app.api.main.reprocess_document", fake_reprocess_document)

    client = TestClient(app)
    response = client.post(f"/documents/{document_id}/reprocess")

    assert response.status_code == 429
    assert response.json() == {
        "detail": "Remote ingest is at capacity. Try again after existing runs finish.",
        "error_code": "rate_limited",
    }


def test_reprocess_route_requires_remote_capability(monkeypatch) -> None:
    document_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "api_mode": "remote",
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "api_key": "operator-secret",
                "remote_api_capabilities": None,
            },
        )(),
    )
    monkeypatch.setattr(
        "app.api.main.reprocess_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("remote capability gate should block before reprocess service runs")
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/documents/{document_id}/reprocess",
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"
