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
