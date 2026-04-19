from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.models import DocumentRun
from app.db.session import get_db_session
from app.services.storage import StorageService


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

    monkeypatch.setattr("app.api.main.ingest_upload", fake_ingest_upload)

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

    monkeypatch.setattr("app.api.main.ingest_upload", fake_ingest_upload)
    monkeypatch.setattr(
        "app.api.main.get_settings",
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


def test_document_list_route_requires_api_key_in_remote_mode(monkeypatch) -> None:
    monkeypatch.setattr("app.api.main.list_documents", lambda session: [])
    monkeypatch.setattr(
        "app.api.main.get_settings",
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
    assert unauthorized.json() == {
        "detail": "Valid API key required for remote API access.",
        "error_code": "auth_required",
    }
    assert authorized.status_code == 200
    assert authorized.json() == []


def test_document_chunks_route_requires_inspect_capability_in_remote_mode(monkeypatch) -> None:
    document_id = uuid4()
    monkeypatch.setattr("app.api.main.get_active_chunks", lambda session, requested_document_id: [])
    monkeypatch.setattr(
        "app.api.main.get_settings",
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
    monkeypatch.setattr("app.api.main.get_active_chunks", lambda session, requested_document_id: [])
    monkeypatch.setattr(
        "app.api.main.get_settings",
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

    monkeypatch.setattr("app.api.main.ingest_upload", fake_ingest_upload)

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
        "app.api.main.get_latest_document_evaluation_detail",
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

    monkeypatch.setattr("app.services.documents.get_latest_document_evaluation", lambda *_args: None)
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
        "app.api.main.list_document_runs",
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
        "app.api.main.get_document_run_summary",
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


def test_run_failure_artifact_route_serves_json(monkeypatch, tmp_path: Path) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()
    artifact_path = storage_service.get_failure_artifact_path(document_id, run_id)
    artifact_path.write_text('{"error":"boom"}')

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return SimpleNamespace(
                    id=run_id,
                    document_id=document_id,
                    failure_artifact_path="/tmp/ignored.json",
                )
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.api.main.get_storage_service", lambda: storage_service)
    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/runs/{run_id}/failure-artifact")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"error": "boom"}


def test_document_artifact_routes_return_404_for_missing_storage_owned_paths(
    monkeypatch, tmp_path: Path
) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()
    table_id = uuid4()
    figure_id = uuid4()

    stale_run = SimpleNamespace(
        id=run_id,
        docling_json_path=str(tmp_path / "missing-docling.json"),
        yaml_path=str(tmp_path / "missing-document.yaml"),
    )
    stale_table = SimpleNamespace(
        id=table_id,
        run_id=run_id,
        document_id=document_id,
        table_index=0,
        json_path=str(tmp_path / "missing-table.json"),
        yaml_path=str(tmp_path / "missing-table.yaml"),
    )
    stale_figure = SimpleNamespace(
        id=figure_id,
        run_id=run_id,
        document_id=document_id,
        figure_index=0,
        json_path=str(tmp_path / "missing-figure.json"),
        yaml_path=str(tmp_path / "missing-figure.yaml"),
    )

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return stale_run
            if key == table_id:
                return stale_table
            if key == figure_id:
                return stale_figure
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.api.main.get_document_detail",
        lambda session, requested_document_id: SimpleNamespace(
            id=requested_document_id,
            active_run_id=run_id,
            has_json_artifact=True,
            has_yaml_artifact=True,
        ),
    )
    monkeypatch.setattr("app.api.main.get_storage_service", lambda: storage_service)

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        document_json = client.get(f"/documents/{document_id}/artifacts/json")
        document_yaml = client.get(f"/documents/{document_id}/artifacts/yaml")
        table_json = client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/json")
        table_yaml = client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/yaml")
        figure_json = client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/json")
        figure_yaml = client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/yaml")
    finally:
        app.dependency_overrides.clear()

    assert document_json.status_code == 404
    assert document_json.json()["error_code"] == "document_artifact_not_found"
    assert document_yaml.status_code == 404
    assert document_yaml.json()["error_code"] == "document_artifact_not_found"
    assert table_json.status_code == 404
    assert table_json.json()["error_code"] == "table_artifact_not_found"
    assert table_yaml.status_code == 404
    assert table_yaml.json()["error_code"] == "table_artifact_not_found"
    assert figure_json.status_code == 404
    assert figure_json.json()["error_code"] == "figure_artifact_not_found"
    assert figure_yaml.status_code == 404
    assert figure_yaml.json()["error_code"] == "figure_artifact_not_found"


def test_run_failure_artifact_route_returns_machine_readable_error_when_run_missing() -> None:
    run_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/runs/{run_id}/failure-artifact")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "document_run_not_found"


def test_run_failure_artifact_route_returns_machine_readable_error_when_artifact_missing(
    monkeypatch, tmp_path: Path
) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return SimpleNamespace(id=run_id, document_id=document_id)
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.api.main.get_storage_service", lambda: storage_service)
    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/runs/{run_id}/failure-artifact")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "run_failure_artifact_not_found"


def test_document_artifact_routes_prefer_storage_owned_paths(monkeypatch, tmp_path: Path) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()
    table_id = uuid4()
    figure_id = uuid4()

    storage_service.get_docling_json_path(document_id, run_id).write_text('{"kind":"document"}')
    storage_service.get_yaml_path(document_id, run_id).write_text("kind: document\n")
    storage_service.get_table_json_path(document_id, run_id, 0).write_text('{"kind":"table"}')
    storage_service.get_table_yaml_path(document_id, run_id, 0).write_text("kind: table\n")
    storage_service.get_figure_json_path(document_id, run_id, 0).write_text('{"kind":"figure"}')
    storage_service.get_figure_yaml_path(document_id, run_id, 0).write_text("kind: figure\n")

    run = SimpleNamespace(
        id=run_id,
        document_id=document_id,
        docling_json_path="/tmp/ignored-docling.json",
        yaml_path="/tmp/ignored-document.yaml",
    )
    table = SimpleNamespace(
        id=table_id,
        run_id=run_id,
        document_id=document_id,
        table_index=0,
        json_path="/tmp/ignored-table.json",
        yaml_path="/tmp/ignored-table.yaml",
    )
    figure = SimpleNamespace(
        id=figure_id,
        run_id=run_id,
        document_id=document_id,
        figure_index=0,
        json_path="/tmp/ignored-figure.json",
        yaml_path="/tmp/ignored-figure.yaml",
    )

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return run
            if key == table_id:
                return table
            if key == figure_id:
                return figure
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.api.main.get_document_detail",
        lambda session, requested_document_id: SimpleNamespace(
            id=requested_document_id,
            active_run_id=run_id,
            has_json_artifact=True,
            has_yaml_artifact=True,
        ),
    )
    monkeypatch.setattr("app.api.main.get_storage_service", lambda: storage_service)

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        assert client.get(f"/documents/{document_id}/artifacts/json").json() == {"kind": "document"}
        assert "kind: document" in client.get(f"/documents/{document_id}/artifacts/yaml").text
        assert (
            client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/json").json()
            == {"kind": "table"}
        )
        assert (
            "kind: table"
            in client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/yaml").text
        )
        assert (
            client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/json").json()
            == {"kind": "figure"}
        )
        assert (
            "kind: figure"
            in client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/yaml").text
        )
    finally:
        app.dependency_overrides.clear()
