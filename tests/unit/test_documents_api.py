from __future__ import annotations

import json
from types import SimpleNamespace
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


def test_document_run_route_allows_inspect_capability_in_remote_mode(monkeypatch) -> None:
    run_id = uuid4()
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
    monkeypatch.setattr(
        "app.api.routers.documents.get_document_run_summary",
        lambda session, requested_run_id: {
            "run_id": str(requested_run_id),
            "run_number": 1,
            "status": "completed",
            "attempts": 1,
            "validation_status": "passed",
            "chunk_count": 1,
            "table_count": 0,
            "figure_count": 0,
            "error_message": None,
            "failure_stage": None,
            "has_failure_artifact": False,
            "current_stage": "completed",
            "stage_started_at": "2026-04-18T00:00:00Z",
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "lease_stale": False,
            "heartbeat_age_seconds": None,
            "validation_warning_count": 0,
            "progress_summary": {},
            "is_active_run": True,
            "created_at": "2026-04-18T00:00:00Z",
            "started_at": "2026-04-18T00:00:01Z",
            "completed_at": "2026-04-18T00:00:02Z",
        },
    )

    client = TestClient(app)
    response = client.get(
        f"/runs/{run_id}",
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == str(run_id)


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


def test_latest_evaluation_route_uses_evaluation_service(monkeypatch) -> None:
    document_id = uuid4()
    evaluation_id = uuid4()
    run_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.documents.get_latest_document_evaluation_detail",
        lambda session, document_id: {
            "evaluation_id": str(evaluation_id),
            "run_id": str(run_id),
            "corpus_name": "default",
            "fixture_name": "fixture",
            "status": "completed",
            "query_count": 1,
            "passed_queries": 1,
            "failed_queries": 0,
            "regressed_queries": 0,
            "improved_queries": 0,
            "stable_queries": 1,
            "baseline_run_id": None,
            "error_message": None,
            "created_at": "2026-04-11T00:00:00Z",
            "completed_at": "2026-04-11T00:00:01Z",
            "summary": {"query_count": 1},
            "query_results": [],
        },
    )

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/evaluations/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_id"] == str(evaluation_id)
    assert body["run_id"] == str(run_id)
    assert body["status"] == "completed"


def test_latest_evaluation_route_returns_machine_readable_error_when_document_missing() -> None:
    document_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/documents/{document_id}/evaluations/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "document_not_found"


def test_latest_evaluation_route_returns_machine_readable_error_when_missing(monkeypatch) -> None:
    document_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return SimpleNamespace(id=document_id)

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.documents.get_latest_document_evaluation",
        lambda *_args: None,
    )
    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/documents/{document_id}/evaluations/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "document_evaluation_not_found"


def test_document_runs_route_uses_run_history_service(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.documents.list_document_runs",
        lambda session, requested_document_id: [
            {
                "run_id": str(run_id),
                "run_number": 2,
                "status": "failed",
                "attempts": 3,
                "validation_status": "failed",
                "chunk_count": 0,
                "table_count": 0,
                "figure_count": 0,
                "error_message": "boom",
                "failure_stage": "parse",
                "has_failure_artifact": True,
                "is_active_run": False,
                "created_at": "2026-04-12T00:00:00Z",
                "started_at": "2026-04-12T00:00:01Z",
                "completed_at": "2026-04-12T00:00:02Z",
            }
        ],
    )

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/runs")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["run_id"] == str(run_id)
    assert body[0]["failure_stage"] == "parse"
    assert body[0]["has_failure_artifact"] is True


def test_document_run_route_uses_run_summary_service(monkeypatch) -> None:
    run_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.documents.get_document_run_summary",
        lambda session, requested_run_id: {
            "run_id": str(requested_run_id),
            "run_number": 2,
            "status": "queued",
            "attempts": 1,
            "validation_status": "pending",
            "chunk_count": None,
            "table_count": None,
            "figure_count": None,
            "error_message": None,
            "failure_stage": None,
            "has_failure_artifact": False,
            "current_stage": "queued",
            "stage_started_at": "2026-04-18T00:00:00Z",
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "lease_stale": False,
            "heartbeat_age_seconds": None,
            "validation_warning_count": 0,
            "progress_summary": {},
            "is_active_run": False,
            "created_at": "2026-04-18T00:00:00Z",
            "started_at": None,
            "completed_at": None,
        },
    )

    client = TestClient(app)
    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["run_id"] == str(run_id)
