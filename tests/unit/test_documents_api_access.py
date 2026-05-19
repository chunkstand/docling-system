from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_create_document_route_requires_api_key_when_configured(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    def fake_ingest_upload(session, upload, storage_service, *, idempotency_key=None):
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

    monkeypatch.setattr("app.api.routers.documents.ingest_upload", fake_ingest_upload)
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
        ),
    )

    client = TestClient(app)

    unauthorized = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    authorized = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"X-API-Key": "operator-secret"},
    )

    assert unauthorized.status_code == 401
    assert unauthorized.json()["detail"] == "Valid API key required for mutating API access."
    assert unauthorized.json()["error_code"] == "auth_required"
    assert authorized.status_code == 202


def test_create_document_route_enforces_actor_scoped_capabilities(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    def fake_ingest_upload(session, upload, storage_service, *, idempotency_key=None):
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

    monkeypatch.setattr("app.api.routers.documents.ingest_upload", fake_ingest_upload)
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key=None,
            api_credentials_json=json.dumps(
                [
                    {
                        "actor": "reader",
                        "key": "reader-secret",
                        "capabilities": ["documents:inspect"],
                    },
                    {
                        "actor": "uploader",
                        "key": "upload-secret",
                        "capabilities": ["documents:upload"],
                    },
                ]
            ),
            remote_api_capabilities=None,
        ),
    )

    client = TestClient(app)
    forbidden = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"X-API-Key": "reader-secret"},
    )
    allowed = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"X-API-Key": "upload-secret"},
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["error_code"] == "capability_not_allowed"
    assert forbidden.json()["error_context"]["actor"] == "reader"
    assert allowed.status_code == 202


def test_document_list_route_requires_inspect_capability_in_remote_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
            remote_api_capabilities=None,
        ),
    )

    client = TestClient(app)

    unauthorized = client.get("/documents")
    authorized = client.get("/documents", headers={"X-API-Key": "operator-secret"})

    assert unauthorized.status_code == 401
    assert unauthorized.json()["error_code"] == "auth_required"
    assert authorized.status_code == 403
    assert authorized.json()["error_code"] == "capability_not_allowed"


def test_document_list_route_accepts_actor_scoped_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routers.documents.list_documents", lambda session, limit=50: [])
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key=None,
            api_credentials_json=json.dumps(
                [
                    {
                        "actor": "inspector",
                        "key": "inspect-secret",
                        "capabilities": ["documents:inspect"],
                    }
                ]
            ),
            remote_api_capabilities=None,
        ),
    )

    client = TestClient(app)
    response = client.get("/documents", headers={"Authorization": "Bearer inspect-secret"})

    assert response.status_code == 200
    assert response.json() == []


def test_document_detail_route_requires_inspect_capability_in_remote_mode(monkeypatch) -> None:
    document_id = uuid4()
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
            remote_api_capabilities=None,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.documents.get_document_detail",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("remote capability gate should block before document detail runs")
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/documents/{document_id}",
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_document_chunks_route_requires_inspect_capability_in_remote_mode(monkeypatch) -> None:
    document_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.documents.get_active_chunks",
        lambda session, requested_document_id: [],
    )
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
            remote_api_capabilities=None,
        ),
    )

    client = TestClient(app)
    forbidden = client.get(
        f"/documents/{document_id}/chunks",
        headers={"X-API-Key": "operator-secret"},
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["error_code"] == "capability_not_allowed"


def test_document_chunks_route_allows_inspect_capability_in_remote_mode(monkeypatch) -> None:
    document_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.documents.get_active_chunks",
        lambda session, requested_document_id: [],
    )
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
            remote_api_capabilities="documents:inspect",
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/documents/{document_id}/chunks",
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 200
    assert response.json() == []
