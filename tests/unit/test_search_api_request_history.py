from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.errors import api_error
from app.api.main import app


def test_search_request_detail_route_uses_history_service(monkeypatch) -> None:
    request_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.get_search_request_detail",
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


def test_search_request_explain_route_uses_legibility_service(monkeypatch) -> None:
    request_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.get_search_request_explanation",
        lambda session, search_request_id: {
            "schema_name": "search_request_explanation",
            "schema_version": "1.0",
            "search_request_id": str(search_request_id),
            "parent_search_request_id": None,
            "evaluation_id": None,
            "run_id": None,
            "origin": "api",
            "query": "vent stack",
            "mode": "hybrid",
            "filters": {},
            "requested_mode": "hybrid",
            "served_mode": "hybrid",
            "limit": 8,
            "tabular_query": False,
            "harness_name": "default_v1",
            "reranker_name": "linear_feature_reranker",
            "reranker_version": "v1",
            "retrieval_profile_name": "default_v1",
            "harness_config": {},
            "embedding_status": "completed",
            "embedding_error": None,
            "fallback_reason": None,
            "keyword_candidate_count": 4,
            "keyword_strict_candidate_count": 2,
            "semantic_candidate_count": 4,
            "metadata_candidate_count": 0,
            "context_expansion_count": 0,
            "candidate_count": 8,
            "result_count": 3,
            "table_hit_count": 1,
            "candidate_source_breakdown": {"keyword": 4, "semantic": 4},
            "query_understanding": {"query_intent": "prose_lookup"},
            "top_result_snapshot": [],
            "diagnosis": {
                "category": "healthy",
                "summary": "healthy",
                "contributing_factors": [],
                "evidence": {},
            },
            "recommended_next_action": "No action.",
            "evidence_refs": [],
            "created_at": "2026-04-12T00:00:00Z",
        },
    )

    client = TestClient(app)
    response = client.get(f"/search/requests/{request_id}/explain")

    assert response.status_code == 200
    assert response.json()["search_request_id"] == str(request_id)
    assert response.json()["diagnosis"]["category"] == "healthy"


def test_search_request_explain_route_returns_machine_readable_error(monkeypatch) -> None:
    request_id = uuid4()

    def raise_not_found(session, search_request_id):
        raise api_error(
            404,
            "search_request_not_found",
            "Search request not found.",
            search_request_id=str(search_request_id),
        )

    monkeypatch.setattr("app.api.routers.search.get_search_request_explanation", raise_not_found)

    client = TestClient(app)
    response = client.get(f"/search/requests/{request_id}/explain")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_request_not_found"


def test_search_request_feedback_route_uses_history_service(monkeypatch) -> None:
    request_id = uuid4()
    feedback_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.record_search_feedback",
        lambda session, search_request_id, payload: {
            "feedback_id": str(feedback_id),
            "search_request_id": str(search_request_id),
            "search_request_result_id": None,
            "result_rank": None,
            "feedback_type": payload.feedback_type,
            "note": payload.note,
            "created_at": "2026-04-12T00:00:00Z",
        },
    )

    client = TestClient(app)
    response = client.post(
        f"/search/requests/{request_id}/feedback",
        json={"feedback_type": "missing_table"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["feedback_id"] == str(feedback_id)
    assert body["feedback_type"] == "missing_table"
