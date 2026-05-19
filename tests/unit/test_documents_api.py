from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.session import get_db_session


def test_create_document_route_uses_ingest_service(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    def fake_ingest_upload(session, upload, storage_service, *, idempotency_key=None):
        assert idempotency_key is None
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

    client = TestClient(app)
    response = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 202
    assert response.headers["Location"] == f"/runs/{run_id}"
    body = response.json()
    assert body["document_id"] == str(document_id)
    assert body["run_id"] == str(run_id)
    assert body["status"] == "queued"


def test_document_list_route_forwards_limit_query_param(monkeypatch) -> None:
    captured: dict[str, int] = {}

    def fake_list_documents(session, limit=50):
        captured["limit"] = limit
        return []

    monkeypatch.setattr("app.api.routers.documents.list_documents", fake_list_documents)

    client = TestClient(app)
    response = client.get("/documents?limit=125")

    assert response.status_code == 200
    assert response.json() == []
    assert captured == {"limit": 125}


def test_document_detail_route_returns_machine_readable_error_when_missing() -> None:
    document_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/documents/{document_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "document_not_found"


def test_document_runs_route_returns_machine_readable_error_when_document_missing() -> None:
    document_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/documents/{document_id}/runs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "document_not_found"


def test_document_chunks_route_returns_machine_readable_error_when_document_missing() -> None:
    document_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/documents/{document_id}/chunks")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "document_not_found"


def test_create_document_route_passes_idempotency_key(monkeypatch) -> None:
    captured: dict = {}

    def fake_ingest_upload(session, upload, storage_service, *, idempotency_key=None):
        captured["idempotency_key"] = idempotency_key
        return (
            {
                "document_id": str(uuid4()),
                "run_id": str(uuid4()),
                "status": "queued",
                "duplicate": False,
                "recovery_run": False,
                "active_run_id": None,
                "active_run_status": None,
            },
            202,
        )

    monkeypatch.setattr("app.api.routers.documents.ingest_upload", fake_ingest_upload)

    client = TestClient(app)
    response = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"Idempotency-Key": "doc-create-1"},
    )

    assert response.status_code == 202
    assert captured["idempotency_key"] == "doc-create-1"
