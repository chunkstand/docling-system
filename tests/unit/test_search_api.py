from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_search_route_uses_search_service(monkeypatch) -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()

    def fake_execute_search(session, request, origin="api"):
        assert origin == "api"
        return SimpleNamespace(
            request_id=uuid4(),
            results=[
                {
                    "result_type": "chunk",
                    "chunk_id": str(chunk_id),
                    "document_id": str(document_id),
                    "run_id": str(run_id),
                    "score": 0.9,
                    "chunk_text": "hello",
                    "heading": "Heading",
                    "page_from": 1,
                    "page_to": 1,
                    "source_filename": "report.pdf",
                    "scores": {
                        "keyword_score": 0.4,
                        "semantic_score": 0.8,
                        "hybrid_score": 0.9,
                    },
                }
            ],
        )

    monkeypatch.setattr("app.api.routers.search.execute_search", fake_execute_search)

    client = TestClient(app)
    response = client.post("/search", json={"query": "hello", "mode": "hybrid", "limit": 5})

    assert response.status_code == 200
    assert response.headers["X-Search-Request-Id"]
    body = response.json()
    assert body[0]["chunk_id"] == str(chunk_id)
    assert body[0]["scores"]["hybrid_score"] == 0.9


def test_search_execution_route_returns_agent_legible_envelope(monkeypatch) -> None:
    request_id = uuid4()
    chunk_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()

    class ResultStub:
        def model_dump(self, *, mode="json"):
            return {
                "result_type": "chunk",
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "run_id": str(run_id),
                "score": 0.9,
                "chunk_text": "hello",
            }

    monkeypatch.setattr(
        "app.api.routers.search.execute_search",
        lambda session, request, origin="api": SimpleNamespace(
            request_id=request_id,
            results=[ResultStub()],
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/search/executions",
        json={"query": "hello", "mode": "keyword", "limit": 5},
    )

    assert response.status_code == 200
    assert response.headers["X-Search-Request-Id"] == str(request_id)
    body = response.json()
    assert body["schema_name"] == "search_execution"
    assert body["schema_version"] == "1.0"
    assert body["explanation_api_path"] == f"/search/requests/{request_id}/explain"
    assert body["results"][0]["chunk_id"] == str(chunk_id)


def test_search_route_is_allowed_in_remote_mode_by_default(monkeypatch) -> None:
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
        "app.api.routers.search.execute_search",
        lambda session, request, origin="api": SimpleNamespace(request_id=None, results=[]),
    )

    client = TestClient(app)
    response = client.post(
        "/search",
        json={"query": "hello", "mode": "keyword", "limit": 5},
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_route_returns_machine_readable_error_code(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.search.execute_search",
        lambda session, request, origin="api": (_ for _ in ()).throw(
            ValueError("bad search request")
        ),
    )

    client = TestClient(app)
    response = client.post("/search", json={"query": "hello", "mode": "keyword", "limit": 5})

    assert response.status_code == 400
    assert response.json() == {
        "detail": "bad search request",
        "error_code": "invalid_search_request",
    }


def test_search_route_returns_structured_rate_limit_error(monkeypatch) -> None:
    monkeypatch.setattr("app.api.deps.SEARCH_RATE_LIMIT", 1)
    monkeypatch.setattr("app.api.deps.SEARCH_RATE_WINDOW_SECONDS", 60.0)
    monkeypatch.setattr(
        "app.api.routers.search.execute_search",
        lambda session, request, origin="api": SimpleNamespace(request_id=None, results=[]),
    )
    from app.api import deps

    deps._search_request_times.clear()

    client = TestClient(app)
    first_response = client.post(
        "/search",
        json={"query": "hello", "mode": "keyword", "limit": 5},
    )
    second_response = client.post(
        "/search",
        json={"query": "hello", "mode": "keyword", "limit": 5},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["error_code"] == "rate_limited"
