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


def test_search_request_feedback_route_uses_history_service(monkeypatch) -> None:
    request_id = uuid4()
    feedback_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.record_search_feedback",
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


def test_search_replays_routes_use_replay_service(monkeypatch) -> None:
    replay_run_id = uuid4()
    comparison_baseline_id = uuid4()
    comparison_candidate_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.list_search_replay_runs",
        lambda session: [
            {
                "replay_run_id": str(replay_run_id),
                "source_type": "live_search_gaps",
                "status": "completed",
                "query_count": 3,
                "passed_count": 2,
                "failed_count": 1,
                "zero_result_count": 1,
                "table_hit_count": 1,
                "top_result_changes": 0,
                "max_rank_shift": 0,
                "created_at": "2026-04-12T00:00:00Z",
                "completed_at": "2026-04-12T00:00:01Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.run_search_replay_suite",
        lambda session, payload: {
            "replay_run_id": str(replay_run_id),
            "source_type": payload.source_type,
            "status": "completed",
            "query_count": 3,
            "passed_count": 2,
            "failed_count": 1,
            "zero_result_count": 1,
            "table_hit_count": 1,
            "top_result_changes": 0,
            "max_rank_shift": 0,
            "created_at": "2026-04-12T00:00:00Z",
            "completed_at": "2026-04-12T00:00:01Z",
            "summary": {"source_limit": 3},
            "query_results": [],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_search_replay_run_detail",
        lambda session, replay_run_id: {
            "replay_run_id": str(replay_run_id),
            "source_type": "live_search_gaps",
            "status": "completed",
            "query_count": 3,
            "passed_count": 2,
            "failed_count": 1,
            "zero_result_count": 1,
            "table_hit_count": 1,
            "top_result_changes": 0,
            "max_rank_shift": 0,
            "created_at": "2026-04-12T00:00:00Z",
            "completed_at": "2026-04-12T00:00:01Z",
            "summary": {"source_limit": 3},
            "query_results": [],
        },
    )
    monkeypatch.setattr(
        "app.api.main.compare_search_replay_runs",
        lambda session, baseline_replay_run_id, candidate_replay_run_id: {
            "baseline_replay_run_id": str(baseline_replay_run_id),
            "candidate_replay_run_id": str(candidate_replay_run_id),
            "shared_query_count": 3,
            "improved_count": 1,
            "regressed_count": 0,
            "unchanged_count": 2,
            "baseline_zero_result_count": 1,
            "candidate_zero_result_count": 0,
            "changed_queries": [],
        },
    )

    client = TestClient(app)

    list_response = client.get("/search/replays")
    assert list_response.status_code == 200
    assert list_response.json()[0]["replay_run_id"] == str(replay_run_id)

    create_response = client.post(
        "/search/replays",
        json={"source_type": "live_search_gaps", "limit": 3},
    )
    assert create_response.status_code == 200
    assert create_response.json()["source_type"] == "live_search_gaps"

    detail_response = client.get(f"/search/replays/{replay_run_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["replay_run_id"] == str(replay_run_id)

    compare_response = client.get(
        f"/search/replays/compare?baseline_replay_run_id={comparison_baseline_id}&candidate_replay_run_id={comparison_candidate_id}"
    )
    assert compare_response.status_code == 200
    assert compare_response.json()["improved_count"] == 1


def test_search_harness_routes_use_harness_services(monkeypatch) -> None:
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.list_search_harness_definitions",
        lambda: [
            {
                "harness_name": "default_v1",
                "reranker_name": "linear_feature_reranker",
                "reranker_version": "v1",
                "retrieval_profile_name": "default_v1",
                "harness_config": {},
                "is_default": True,
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.evaluate_search_harness",
        lambda session, payload: {
            "baseline_harness_name": payload.baseline_harness_name,
            "candidate_harness_name": payload.candidate_harness_name,
            "limit": payload.limit,
            "total_shared_query_count": 3,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "total_unchanged_count": 2,
            "sources": [
                {
                    "source_type": "feedback",
                    "baseline_replay_run_id": str(baseline_replay_run_id),
                    "candidate_replay_run_id": str(candidate_replay_run_id),
                    "baseline_query_count": 3,
                    "candidate_query_count": 3,
                    "baseline_passed_count": 1,
                    "candidate_passed_count": 2,
                    "baseline_zero_result_count": 1,
                    "candidate_zero_result_count": 0,
                    "baseline_table_hit_count": 0,
                    "candidate_table_hit_count": 1,
                    "baseline_top_result_changes": 0,
                    "candidate_top_result_changes": 1,
                    "shared_query_count": 3,
                    "improved_count": 1,
                    "regressed_count": 0,
                    "unchanged_count": 2,
                }
            ],
        },
    )

    client = TestClient(app)

    list_response = client.get("/search/harnesses")
    assert list_response.status_code == 200
    assert list_response.json()[0]["harness_name"] == "default_v1"

    eval_response = client.post(
        "/search/harness-evaluations",
        json={
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "source_types": ["feedback"],
            "limit": 5,
        },
    )
    assert eval_response.status_code == 200
    assert eval_response.json()["candidate_harness_name"] == "wide_v2"
