from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


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
