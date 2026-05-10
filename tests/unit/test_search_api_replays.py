from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_search_replay_list_route_requires_remote_replay_capability(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routers.search.list_search_replay_runs", lambda session: [])
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
    response = client.get("/search/replays", headers={"X-API-Key": "operator-secret"})

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_search_replay_list_route_allows_remote_replay_capability(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routers.search.list_search_replay_runs", lambda session: [])
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
            remote_api_capabilities="search:replay",
        ),
    )

    client = TestClient(app)
    response = client.get("/search/replays", headers={"X-API-Key": "operator-secret"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_request_replay_route_uses_history_service(monkeypatch) -> None:
    request_id = uuid4()
    replay_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.replay_search_request",
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


def test_search_request_replay_route_requires_remote_capability(monkeypatch) -> None:
    request_id = uuid4()

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
        "app.api.routers.search.replay_search_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("remote capability gate should block before replay runs")
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/search/requests/{request_id}/replay",
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_search_replays_routes_use_replay_service(monkeypatch) -> None:
    replay_run_id = uuid4()
    comparison_baseline_id = uuid4()
    comparison_candidate_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.list_search_replay_runs",
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
        "app.api.routers.search.run_search_replay_suite",
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
        "app.api.routers.search.get_search_replay_run_detail",
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
        "app.api.routers.search.compare_search_replay_runs",
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
        json={"source_type": "cross_document_prose_regressions", "limit": 3},
    )
    assert create_response.status_code == 200
    assert create_response.headers["Location"] == f"/search/replays/{replay_run_id}"
    assert create_response.json()["source_type"] == "cross_document_prose_regressions"

    detail_response = client.get(f"/search/replays/{replay_run_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["replay_run_id"] == str(replay_run_id)

    compare_response = client.get(
        f"/search/replays/compare?baseline_replay_run_id={comparison_baseline_id}&candidate_replay_run_id={comparison_candidate_id}"
    )
    assert compare_response.status_code == 200
    assert compare_response.json()["improved_count"] == 1
