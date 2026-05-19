from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.session import get_db_session


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
