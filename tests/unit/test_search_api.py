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

    monkeypatch.setattr("app.api.main.execute_search", fake_execute_search)

    client = TestClient(app)
    response = client.post("/search", json={"query": "hello", "mode": "hybrid", "limit": 5})

    assert response.status_code == 200
    assert response.headers["X-Search-Request-Id"]
    body = response.json()
    assert body[0]["chunk_id"] == str(chunk_id)
    assert body[0]["scores"]["hybrid_score"] == 0.9


def test_search_request_detail_route_uses_history_service(monkeypatch) -> None:
    request_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.get_search_request_detail",
        lambda session, search_request_id: {
            "search_request_id": str(search_request_id),
            "parent_search_request_id": None,
            "evaluation_id": None,
            "run_id": None,
            "origin": "api",
            "query": "vent stack",
            "mode": "hybrid",
            "filters": {},
            "details": {"served_mode": "hybrid"},
            "limit": 8,
            "tabular_query": False,
            "reranker_name": "heuristic_v1",
            "embedding_status": "completed",
            "embedding_error": None,
            "candidate_count": 12,
            "result_count": 3,
            "table_hit_count": 1,
            "duration_ms": 14.5,
            "created_at": "2026-04-12T00:00:00Z",
            "results": [],
        },
    )

    client = TestClient(app)
    response = client.get(f"/search/requests/{request_id}")

    assert response.status_code == 200
    assert response.json()["search_request_id"] == str(request_id)


def test_search_request_replay_route_uses_history_service(monkeypatch) -> None:
    request_id = uuid4()
    replay_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.replay_search_request",
        lambda session, search_request_id: {
            "original_request": {
                "search_request_id": str(search_request_id),
                "parent_search_request_id": None,
                "evaluation_id": None,
                "run_id": None,
                "origin": "api",
                "query": "vent stack",
                "mode": "hybrid",
                "filters": {},
                "details": {"served_mode": "hybrid"},
                "limit": 8,
                "tabular_query": False,
                "reranker_name": "heuristic_v1",
                "embedding_status": "completed",
                "embedding_error": None,
                "candidate_count": 12,
                "result_count": 3,
                "table_hit_count": 1,
                "duration_ms": 14.5,
                "created_at": "2026-04-12T00:00:00Z",
                "results": [],
            },
            "replay_request": {
                "search_request_id": str(replay_id),
                "parent_search_request_id": str(search_request_id),
                "evaluation_id": None,
                "run_id": None,
                "origin": "replay",
                "query": "vent stack",
                "mode": "hybrid",
                "filters": {},
                "details": {"served_mode": "hybrid"},
                "limit": 8,
                "tabular_query": False,
                "reranker_name": "heuristic_v1",
                "embedding_status": "completed",
                "embedding_error": None,
                "candidate_count": 12,
                "result_count": 4,
                "table_hit_count": 2,
                "duration_ms": 13.1,
                "created_at": "2026-04-12T00:00:01Z",
                "results": [],
            },
            "diff": {
                "overlap_count": 2,
                "added_count": 1,
                "removed_count": 0,
                "top_result_changed": False,
                "max_rank_shift": 1,
            },
        },
    )

    client = TestClient(app)
    response = client.post(f"/search/requests/{request_id}/replay")

    assert response.status_code == 200
    assert response.json()["replay_request"]["parent_search_request_id"] == str(request_id)
