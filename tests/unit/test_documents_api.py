from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.models import DocumentRun
from app.db.session import get_db_session


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


def test_run_failure_artifact_route_serves_json(tmp_path: Path) -> None:
    run_id = uuid4()
    artifact_path = tmp_path / "failure.json"
    artifact_path.write_text('{"error":"boom"}')

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return SimpleNamespace(id=run_id, failure_artifact_path=str(artifact_path))
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/runs/{run_id}/failure-artifact")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"error": "boom"}


def test_document_artifact_routes_return_404_for_stale_paths(monkeypatch, tmp_path: Path) -> None:
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
        json_path=str(tmp_path / "missing-table.json"),
        yaml_path=str(tmp_path / "missing-table.yaml"),
    )
    stale_figure = SimpleNamespace(
        id=figure_id,
        run_id=run_id,
        document_id=document_id,
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

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        assert client.get(f"/documents/{document_id}/artifacts/json").status_code == 404
        assert client.get(f"/documents/{document_id}/artifacts/yaml").status_code == 404
        assert client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/json").status_code == 404
        assert client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/yaml").status_code == 404
        assert client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/json").status_code == 404
        assert client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/yaml").status_code == 404
    finally:
        app.dependency_overrides.clear()
