from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.errors import api_error
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


def test_search_request_evidence_package_route_uses_evidence_service(monkeypatch) -> None:
    request_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.get_search_evidence_package",
        lambda session, search_request_id: {
            "schema_name": "search_evidence_package",
            "schema_version": "1.0",
            "search_request": {"id": str(search_request_id), "query_text": "vent stack"},
            "operator_runs": [{"operator_kind": "retrieve"}],
            "results": [],
            "audit_checklist": {"has_retrieve_run": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/search/requests/{request_id}/evidence-package")

    assert response.status_code == 200
    assert response.json()["search_request"]["id"] == str(request_id)
    assert response.json()["operator_runs"][0]["operator_kind"] == "retrieve"


def test_search_request_evidence_package_route_returns_structured_404(monkeypatch) -> None:
    request_id = uuid4()

    def raise_not_found(session, search_request_id):
        raise ValueError(f"Search request '{search_request_id}' was not found.")

    monkeypatch.setattr("app.api.routers.search.get_search_evidence_package", raise_not_found)

    client = TestClient(app)
    response = client.get(f"/search/requests/{request_id}/evidence-package")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_request_not_found"
    assert response.json()["error_context"]["search_request_id"] == str(request_id)


def test_search_evidence_package_export_route_uses_evidence_service(monkeypatch) -> None:
    request_id = uuid4()
    export_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.export_search_evidence_package",
        lambda session, search_request_id: {
            "schema_name": "search_evidence_package_export",
            "schema_version": "1.0",
            "evidence_package_export_id": str(export_id),
            "search_request_id": str(search_request_id),
            "package_kind": "search_request",
            "package_sha256": "a" * 64,
            "trace_sha256": "b" * 64,
            "node_count": 3,
            "edge_count": 2,
            "trace_integrity": {"complete": True},
        },
    )

    client = TestClient(app)
    response = client.post(f"/search/requests/{request_id}/evidence-package/export")

    assert response.status_code == 200
    assert response.json()["evidence_package_export_id"] == str(export_id)
    assert response.json()["trace_integrity"]["complete"] is True


def test_search_evidence_package_export_route_returns_structured_404(monkeypatch) -> None:
    request_id = uuid4()

    def raise_not_found(session, search_request_id):
        raise ValueError(f"Search request '{search_request_id}' was not found.")

    monkeypatch.setattr("app.api.routers.search.export_search_evidence_package", raise_not_found)

    client = TestClient(app)
    response = client.post(f"/search/requests/{request_id}/evidence-package/export")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_request_not_found"
    assert response.json()["error_context"]["search_request_id"] == str(request_id)


def test_search_evidence_trace_route_uses_trace_service(monkeypatch) -> None:
    export_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.get_search_evidence_package_export_trace",
        lambda session, evidence_package_export_id: {
            "schema_name": "search_evidence_package_trace",
            "schema_version": "1.0",
            "evidence_package_export_id": str(evidence_package_export_id),
            "trace_sha256": "b" * 64,
            "node_count": 3,
            "edge_count": 2,
            "nodes": [],
            "edges": [],
            "trace_integrity": {"complete": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/search/evidence-package-exports/{export_id}/trace-graph")

    assert response.status_code == 200
    assert response.json()["evidence_package_export_id"] == str(export_id)
    assert response.json()["trace_integrity"]["complete"] is True


def test_search_evidence_trace_route_returns_structured_404(monkeypatch) -> None:
    export_id = uuid4()

    def raise_not_found(session, evidence_package_export_id):
        raise ValueError(
            f"Search evidence package export '{evidence_package_export_id}' was not found."
        )

    monkeypatch.setattr(
        "app.api.routers.search.get_search_evidence_package_export_trace",
        raise_not_found,
    )

    client = TestClient(app)
    response = client.get(f"/search/evidence-package-exports/{export_id}/trace-graph")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_evidence_package_export_not_found"
    assert response.json()["error_context"]["evidence_package_export_id"] == str(export_id)


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


def test_search_harness_routes_use_harness_services(monkeypatch) -> None:
    evaluation_id = uuid4()
    release_id = uuid4()
    learning_candidate_id = uuid4()
    reranker_artifact_id = uuid4()
    retrieval_training_run_id = uuid4()
    judgment_set_id = uuid4()
    semantic_governance_event_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
    training_audit_bundle_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.list_search_harness_definitions",
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
        "app.api.routers.search.evaluate_search_harness",
        lambda session, payload: {
            "evaluation_id": str(evaluation_id),
            "status": "completed",
            "baseline_harness_name": payload.baseline_harness_name,
            "candidate_harness_name": payload.candidate_harness_name,
            "limit": payload.limit,
            "source_types": payload.source_types,
            "total_shared_query_count": 3,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "total_unchanged_count": 2,
            "created_at": "2026-04-21T00:00:00Z",
            "completed_at": "2026-04-21T00:00:01Z",
            "sources": [
                {
                    "source_type": "cross_document_prose_regressions",
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
    monkeypatch.setattr(
        "app.api.routers.search.list_search_harness_evaluations",
        lambda session, limit=20, candidate_harness_name=None: [
            {
                "evaluation_id": str(evaluation_id),
                "status": "completed",
                "baseline_harness_name": "default_v1",
                "candidate_harness_name": "wide_v2",
                "limit": 5,
                "source_types": ["cross_document_prose_regressions"],
                "total_shared_query_count": 3,
                "total_improved_count": 1,
                "total_regressed_count": 0,
                "total_unchanged_count": 2,
                "created_at": "2026-04-21T00:00:00Z",
                "completed_at": "2026-04-21T00:00:01Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_evaluation_detail",
        lambda session, lookup_evaluation_id: {
            "evaluation_id": str(lookup_evaluation_id),
            "status": "completed",
            "baseline_harness_name": "default_v1",
            "candidate_harness_name": "wide_v2",
            "limit": 5,
            "source_types": ["cross_document_prose_regressions"],
            "total_shared_query_count": 3,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "total_unchanged_count": 2,
            "created_at": "2026-04-21T00:00:00Z",
            "completed_at": "2026-04-21T00:00:01Z",
            "sources": [
                {
                    "source_type": "cross_document_prose_regressions",
                    "baseline_replay_run_id": str(baseline_replay_run_id),
                    "candidate_replay_run_id": str(candidate_replay_run_id),
                    "shared_query_count": 3,
                    "improved_count": 1,
                    "regressed_count": 0,
                    "unchanged_count": 2,
                }
            ],
        },
    )
    release_payload = {
        "schema_name": "search_harness_release_gate",
        "schema_version": "1.0",
        "release_id": str(release_id),
        "evaluation_id": str(evaluation_id),
        "outcome": "passed",
        "baseline_harness_name": "default_v1",
        "candidate_harness_name": "wide_v2",
        "limit": 5,
        "source_types": ["cross_document_prose_regressions"],
        "thresholds": {"max_total_regressed_count": 0},
        "metrics": {"total_shared_query_count": 3},
        "reasons": [],
        "details": {"evaluation_id": str(evaluation_id)},
        "evaluation_snapshot": {"evaluation_id": str(evaluation_id)},
        "release_package_sha256": "abc123",
        "requested_by": "operator",
        "review_note": "release gate",
        "created_at": "2026-04-21T00:00:02Z",
    }
    release_readiness_payload = {
        "schema_name": "search_harness_release_readiness",
        "schema_version": "1.0",
        "release_id": str(release_id),
        "readiness_profile": "search_harness_release_readiness_v1",
        "ready": True,
        "blockers": [],
        "retrieval": {"release_passed": True},
        "provenance": {"release_audit_bundle_present": True},
        "semantic_governance": {
            "policy_profile": "release_semantic_governance_v1",
            "complete": True,
        },
        "validation_receipts": {"release_validation_receipt_passed": True},
        "checks": {"ready": True},
        "generated_at": "2026-04-21T00:00:06Z",
    }
    learning_candidate_payload = {
        "schema_name": "retrieval_learning_candidate_evaluation",
        "schema_version": "1.0",
        "candidate_evaluation_id": str(learning_candidate_id),
        "retrieval_training_run_id": str(retrieval_training_run_id),
        "judgment_set_id": str(judgment_set_id),
        "search_harness_evaluation_id": str(evaluation_id),
        "search_harness_release_id": str(release_id),
        "semantic_governance_event_id": str(semantic_governance_event_id),
        "training_dataset_sha256": "training-sha",
        "training_example_count": 7,
        "positive_count": 2,
        "negative_count": 2,
        "missing_count": 1,
        "hard_negative_count": 2,
        "baseline_harness_name": "default_v1",
        "candidate_harness_name": "wide_v2",
        "source_types": ["cross_document_prose_regressions"],
        "limit": 5,
        "status": "completed",
        "gate_outcome": "passed",
        "thresholds": {"max_total_regressed_count": 0},
        "metrics": {"total_shared_query_count": 3},
        "reasons": [],
        "learning_package_sha256": "learning-package-sha",
        "created_by": "operator",
        "review_note": "learning gate",
        "created_at": "2026-04-21T00:00:04Z",
        "completed_at": "2026-04-21T00:00:04Z",
        "details": {"learning_loop_stage": "training_dataset_to_harness_release_gate"},
        "evaluation": {
            "evaluation_id": str(evaluation_id),
            "status": "completed",
            "baseline_harness_name": "default_v1",
            "candidate_harness_name": "wide_v2",
            "limit": 5,
            "source_types": ["cross_document_prose_regressions"],
            "total_shared_query_count": 3,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "total_unchanged_count": 2,
            "created_at": "2026-04-21T00:00:00Z",
            "completed_at": "2026-04-21T00:00:01Z",
            "sources": [],
        },
        "release": release_payload,
    }
    reranker_artifact_payload = {
        "schema_name": "retrieval_reranker_artifact",
        "schema_version": "1.0",
        "artifact_id": str(reranker_artifact_id),
        "retrieval_training_run_id": str(retrieval_training_run_id),
        "judgment_set_id": str(judgment_set_id),
        "retrieval_learning_candidate_evaluation_id": str(learning_candidate_id),
        "search_harness_evaluation_id": str(evaluation_id),
        "search_harness_release_id": str(release_id),
        "semantic_governance_event_id": str(semantic_governance_event_id),
        "artifact_kind": "linear_feature_weight_candidate",
        "artifact_name": "learned-reranker",
        "artifact_version": "wide_v2+training-sha",
        "status": "evaluated",
        "gate_outcome": "passed",
        "baseline_harness_name": "default_v1",
        "candidate_harness_name": "wide_v2",
        "source_types": ["cross_document_prose_regressions"],
        "limit": 5,
        "training_dataset_sha256": "training-sha",
        "training_example_count": 7,
        "positive_count": 2,
        "negative_count": 2,
        "missing_count": 1,
        "hard_negative_count": 2,
        "thresholds": {"max_total_regressed_count": 0},
        "metrics": {"total_shared_query_count": 3},
        "reasons": [],
        "artifact_sha256": "artifact-sha",
        "change_impact_sha256": "impact-sha",
        "created_by": "operator",
        "review_note": "reranker artifact",
        "created_at": "2026-04-21T00:00:07Z",
        "completed_at": "2026-04-21T00:00:07Z",
        "feature_weights": {
            "proposed_reranker_overrides": {"result_type_priority_bonus": 0.009}
        },
        "harness_overrides": {
            "wide_v2": {
                "base_harness_name": "default_v1",
                "override_type": "retrieval_reranker_artifact",
                "reranker_overrides": {"result_type_priority_bonus": 0.009},
            }
        },
        "artifact": {"artifact_name": "learned-reranker"},
        "change_impact_report": {
            "affected_trace_summary": {"affected_claim_count": 1}
        },
        "evaluation": learning_candidate_payload["evaluation"],
        "release": release_payload,
        "candidate_evaluation": learning_candidate_payload,
    }
    audit_bundle_id = uuid4()
    audit_bundle_validation_receipt_id = uuid4()
    audit_bundle_payload = {
        "schema_name": "audit_bundle_export",
        "schema_version": "1.0",
        "bundle_id": str(audit_bundle_id),
        "bundle_kind": "search_harness_release_provenance",
        "source_table": "search_harness_releases",
        "source_id": str(release_id),
        "payload_sha256": "payload-sha",
        "bundle_sha256": "bundle-sha",
        "signature": "sig",
        "signature_algorithm": "hmac-sha256",
        "signing_key_id": "test-key",
        "created_by": "operator",
        "export_status": "completed",
        "created_at": "2026-04-21T00:00:03Z",
        "bundle": {
            "schema_name": "audit_bundle_export",
            "payload": {
                "schema_name": "search_harness_release_audit_payload",
                "prov": {"wasDerivedFrom": []},
            },
        },
        "integrity": {"complete": True},
    }
    audit_bundle_validation_receipt_payload = {
        "schema_name": "audit_bundle_validation_receipt",
        "schema_version": "1.0",
        "receipt_id": str(audit_bundle_validation_receipt_id),
        "audit_bundle_export_id": str(audit_bundle_id),
        "bundle_kind": "search_harness_release_provenance",
        "source_table": "search_harness_releases",
        "source_id": str(release_id),
        "validation_profile": "audit_bundle_validation_v1",
        "validation_status": "passed",
        "payload_schema_valid": True,
        "prov_graph_valid": True,
        "bundle_integrity_valid": True,
        "source_integrity_valid": True,
        "semantic_governance_valid": True,
        "receipt_sha256": "receipt-sha",
        "prov_jsonld_sha256": "prov-jsonld-sha",
        "signature": "receipt-sig",
        "signature_algorithm": "hmac-sha256",
        "signing_key_id": "test-key",
        "created_by": "operator",
        "created_at": "2026-04-21T00:00:05Z",
        "receipt": {
            "schema_name": "audit_bundle_validation_receipt",
            "validation_status": "passed",
        },
        "prov_jsonld": {
            "@context": {"prov": "http://www.w3.org/ns/prov#"},
            "@graph": [{"@id": "docling:audit_bundle_export:test"}],
        },
        "validation_errors": [],
        "integrity": {"complete": True},
    }
    training_audit_bundle_payload = {
        **audit_bundle_payload,
        "bundle_id": str(training_audit_bundle_id),
        "bundle_kind": "retrieval_training_run_provenance",
        "source_table": "retrieval_training_runs",
        "source_id": str(retrieval_training_run_id),
        "payload_sha256": "training-payload-sha",
        "bundle_sha256": "training-bundle-sha",
        "bundle": {
            "schema_name": "audit_bundle_export",
            "payload": {
                "schema_name": "retrieval_training_run_audit_payload",
                "retrieval_judgments": [],
                "retrieval_hard_negatives": [],
                "prov": {"wasDerivedFrom": []},
            },
        },
    }
    monkeypatch.setattr(
        "app.api.routers.search.create_search_harness_release_gate",
        lambda session, payload: release_payload,
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_search_harness_releases",
        lambda session, limit=20, candidate_harness_name=None, outcome=None: [release_payload],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_release_detail",
        lambda session, lookup_release_id: {
            **release_payload,
            "release_id": str(lookup_release_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_release_readiness",
        lambda session, lookup_release_id: {
            **release_readiness_payload,
            "release_id": str(lookup_release_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.evaluate_retrieval_learning_candidate",
        lambda session, payload: {
            **learning_candidate_payload,
            "candidate_harness_name": payload.candidate_harness_name,
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_retrieval_learning_candidate_evaluations",
        lambda session,
        limit=20,
        retrieval_training_run_id=None,
        candidate_harness_name=None: [learning_candidate_payload],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_learning_candidate_evaluation_detail",
        lambda session, lookup_candidate_id: {
            **learning_candidate_payload,
            "candidate_evaluation_id": str(lookup_candidate_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.create_retrieval_reranker_artifact",
        lambda session, payload: {
            **reranker_artifact_payload,
            "candidate_harness_name": payload.candidate_harness_name,
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_retrieval_reranker_artifacts",
        lambda session,
        limit=20,
        retrieval_training_run_id=None,
        candidate_harness_name=None: [reranker_artifact_payload],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_reranker_artifact_detail",
        lambda session, lookup_artifact_id: {
            **reranker_artifact_payload,
            "artifact_id": str(lookup_artifact_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.create_search_harness_release_audit_bundle",
        lambda session, lookup_release_id, payload, *, storage_service: audit_bundle_payload,
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_search_harness_release_audit_bundle",
        lambda session, lookup_release_id, *, storage_service: audit_bundle_payload,
    )
    monkeypatch.setattr(
        "app.api.routers.search.create_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, payload, *, storage_service: {
            **training_audit_bundle_payload,
            "source_id": str(lookup_training_run_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, *, storage_service: {
            **training_audit_bundle_payload,
            "source_id": str(lookup_training_run_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_export",
        lambda session, lookup_bundle_id, *, storage_service: {
            **audit_bundle_payload,
            "bundle_id": str(lookup_bundle_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.create_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, payload, *, storage_service: {
            **audit_bundle_validation_receipt_payload,
            "audit_bundle_export_id": str(lookup_bundle_id),
            "created_by": payload.created_by,
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_audit_bundle_validation_receipts",
        lambda session, lookup_bundle_id: [
            {
                key: value
                for key, value in audit_bundle_validation_receipt_payload.items()
                if key
                not in {
                    "receipt",
                    "prov_jsonld",
                    "validation_errors",
                    "integrity",
                }
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, lookup_receipt_id, *, storage_service: {
            **audit_bundle_validation_receipt_payload,
            "audit_bundle_export_id": str(lookup_bundle_id),
            "receipt_id": str(lookup_receipt_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, *, storage_service: {
            **audit_bundle_validation_receipt_payload,
            "audit_bundle_export_id": str(lookup_bundle_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_descriptor",
        lambda harness_name: {
            "schema_name": "search_harness_descriptor",
            "schema_version": "1.0",
            "harness_name": harness_name,
            "base_harness_name": None,
            "is_default": harness_name == "default_v1",
            "config_fingerprint": "abc123",
            "reranker_name": "linear_feature_reranker",
            "reranker_version": "v1",
            "retrieval_profile_name": harness_name,
            "retrieval_stages": ["keyword_candidates"],
            "tunable_knobs": {"retrieval_profile_overrides": []},
            "constraints": [],
            "intended_query_families": [],
            "known_tradeoffs": [],
            "harness_config": {},
            "metadata": {},
        },
    )

    client = TestClient(app)

    list_response = client.get("/search/harnesses")
    assert list_response.status_code == 200
    assert list_response.json()[0]["harness_name"] == "default_v1"

    descriptor_response = client.get("/search/harnesses/default_v1/descriptor")
    assert descriptor_response.status_code == 200
    assert descriptor_response.json()["schema_name"] == "search_harness_descriptor"

    eval_response = client.post(
        "/search/harness-evaluations",
        json={
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "source_types": ["cross_document_prose_regressions"],
            "limit": 5,
        },
    )
    assert eval_response.status_code == 200
    assert eval_response.headers["Location"] == f"/search/harness-evaluations/{evaluation_id}"
    assert eval_response.json()["evaluation_id"] == str(evaluation_id)
    assert eval_response.json()["candidate_harness_name"] == "wide_v2"
    assert eval_response.json()["sources"][0]["source_type"] == "cross_document_prose_regressions"

    evaluation_list_response = client.get("/search/harness-evaluations")
    assert evaluation_list_response.status_code == 200
    assert evaluation_list_response.json()[0]["evaluation_id"] == str(evaluation_id)

    evaluation_detail_response = client.get(f"/search/harness-evaluations/{evaluation_id}")
    assert evaluation_detail_response.status_code == 200
    assert evaluation_detail_response.json()["sources"][0]["candidate_replay_run_id"] == str(
        candidate_replay_run_id
    )

    release_response = client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "requested_by": "operator",
            "review_note": "release gate",
        },
    )
    assert release_response.status_code == 200
    assert release_response.headers["Location"] == f"/search/harness-releases/{release_id}"
    assert release_response.json()["release_id"] == str(release_id)
    assert release_response.json()["outcome"] == "passed"

    release_list_response = client.get("/search/harness-releases")
    assert release_list_response.status_code == 200
    assert release_list_response.json()[0]["release_package_sha256"] == "abc123"

    release_detail_response = client.get(f"/search/harness-releases/{release_id}")
    assert release_detail_response.status_code == 200
    assert release_detail_response.json()["evaluation_snapshot"]["evaluation_id"] == str(
        evaluation_id
    )

    release_readiness_response = client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert release_readiness_response.status_code == 200
    assert release_readiness_response.json()["ready"] is True
    assert release_readiness_response.json()["semantic_governance"]["complete"] is True

    learning_response = client.post(
        "/search/retrieval-learning/candidate-evaluations",
        json={
            "retrieval_training_run_id": str(retrieval_training_run_id),
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "source_types": ["cross_document_prose_regressions"],
            "limit": 5,
            "requested_by": "operator",
            "review_note": "learning gate",
        },
    )
    assert learning_response.status_code == 200
    assert learning_response.headers["Location"] == (
        f"/search/retrieval-learning/candidate-evaluations/{learning_candidate_id}"
    )
    assert learning_response.json()["training_dataset_sha256"] == "training-sha"
    assert learning_response.json()["release"]["release_id"] == str(release_id)

    learning_list_response = client.get("/search/retrieval-learning/candidate-evaluations")
    assert learning_list_response.status_code == 200
    assert learning_list_response.json()[0]["candidate_evaluation_id"] == str(
        learning_candidate_id
    )

    learning_detail_response = client.get(
        f"/search/retrieval-learning/candidate-evaluations/{learning_candidate_id}"
    )
    assert learning_detail_response.status_code == 200
    assert learning_detail_response.json()["semantic_governance_event_id"] == str(
        semantic_governance_event_id
    )

    artifact_response = client.post(
        "/search/retrieval-learning/reranker-artifacts",
        json={
            "retrieval_training_run_id": str(retrieval_training_run_id),
            "artifact_name": "learned-reranker",
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "source_types": ["cross_document_prose_regressions"],
            "limit": 5,
            "requested_by": "operator",
            "review_note": "reranker artifact",
        },
    )
    assert artifact_response.status_code == 200
    assert artifact_response.headers["Location"] == (
        f"/search/retrieval-learning/reranker-artifacts/{reranker_artifact_id}"
    )
    assert artifact_response.json()["artifact_sha256"] == "artifact-sha"
    assert artifact_response.json()["change_impact_report"][
        "affected_trace_summary"
    ]["affected_claim_count"] == 1

    artifact_list_response = client.get("/search/retrieval-learning/reranker-artifacts")
    assert artifact_list_response.status_code == 200
    assert artifact_list_response.json()[0]["artifact_id"] == str(reranker_artifact_id)

    artifact_detail_response = client.get(
        f"/search/retrieval-learning/reranker-artifacts/{reranker_artifact_id}"
    )
    assert artifact_detail_response.status_code == 200
    assert artifact_detail_response.json()["candidate_evaluation"]["candidate_evaluation_id"] == (
        str(learning_candidate_id)
    )

    audit_response = client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "operator"},
    )
    assert audit_response.status_code == 200
    assert audit_response.headers["Location"] == f"/search/audit-bundles/{audit_bundle_id}"
    assert audit_response.json()["bundle_kind"] == "search_harness_release_provenance"

    latest_audit_response = client.get(
        f"/search/harness-releases/{release_id}/audit-bundles/latest"
    )
    assert latest_audit_response.status_code == 200
    assert latest_audit_response.json()["integrity"]["complete"] is True

    training_audit_response = client.post(
        f"/search/retrieval-training-runs/{retrieval_training_run_id}/audit-bundles",
        json={"created_by": "operator"},
    )
    assert training_audit_response.status_code == 200
    assert training_audit_response.headers["Location"] == (
        f"/search/audit-bundles/{training_audit_bundle_id}"
    )
    assert training_audit_response.json()["bundle_kind"] == "retrieval_training_run_provenance"

    latest_training_audit_response = client.get(
        f"/search/retrieval-training-runs/{retrieval_training_run_id}/audit-bundles/latest"
    )
    assert latest_training_audit_response.status_code == 200
    assert latest_training_audit_response.json()["bundle_sha256"] == "training-bundle-sha"

    audit_detail_response = client.get(f"/search/audit-bundles/{audit_bundle_id}")
    assert audit_detail_response.status_code == 200
    assert audit_detail_response.json()["bundle_id"] == str(audit_bundle_id)

    receipt_response = client.post(
        f"/search/audit-bundles/{audit_bundle_id}/validation-receipts",
        json={"created_by": "operator"},
    )
    assert receipt_response.status_code == 200
    assert receipt_response.headers["Location"] == (
        f"/search/audit-bundles/{audit_bundle_id}/validation-receipts/"
        f"{audit_bundle_validation_receipt_id}"
    )
    assert receipt_response.json()["validation_status"] == "passed"
    assert receipt_response.json()["created_by"] == "operator"

    receipt_list_response = client.get(
        f"/search/audit-bundles/{audit_bundle_id}/validation-receipts"
    )
    assert receipt_list_response.status_code == 200
    assert receipt_list_response.json()[0]["receipt_id"] == str(
        audit_bundle_validation_receipt_id
    )

    receipt_detail_response = client.get(receipt_response.headers["Location"])
    assert receipt_detail_response.status_code == 200
    assert receipt_detail_response.json()["receipt_id"] == str(
        audit_bundle_validation_receipt_id
    )

    latest_receipt_response = client.get(
        f"/search/audit-bundles/{audit_bundle_id}/validation-receipts/latest"
    )
    assert latest_receipt_response.status_code == 200
    assert latest_receipt_response.json()["receipt_id"] == str(
        audit_bundle_validation_receipt_id
    )


def test_search_harness_descriptor_route_returns_machine_readable_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_descriptor",
        lambda harness_name: (_ for _ in ()).throw(ValueError("Unknown search harness")),
    )

    client = TestClient(app)
    response = client.get("/search/harnesses/missing_v1/descriptor")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_harness_not_found"


def test_search_harness_evaluation_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    evaluation_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_evaluation_detail",
        lambda session, lookup_evaluation_id: (_ for _ in ()).throw(
            api_error(
                404,
                "search_harness_evaluation_not_found",
                "Search harness evaluation not found.",
                evaluation_id=str(lookup_evaluation_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/harness-evaluations/{evaluation_id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_harness_evaluation_not_found"
    assert response.json()["error_context"]["evaluation_id"] == str(evaluation_id)


def test_search_harness_release_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    release_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_release_detail",
        lambda session, lookup_release_id: (_ for _ in ()).throw(
            api_error(
                404,
                "search_harness_release_not_found",
                "Search harness release gate not found.",
                release_id=str(lookup_release_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/harness-releases/{release_id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_harness_release_not_found"
    assert response.json()["error_context"]["release_id"] == str(release_id)


def test_search_harness_release_readiness_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    release_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_release_readiness",
        lambda session, lookup_release_id: (_ for _ in ()).throw(
            api_error(
                404,
                "search_harness_release_not_found",
                "Search harness release gate not found.",
                release_id=str(lookup_release_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/harness-releases/{release_id}/readiness")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_harness_release_not_found"
    assert response.json()["error_context"]["release_id"] == str(release_id)


def test_retrieval_learning_candidate_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    candidate_evaluation_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_learning_candidate_evaluation_detail",
        lambda session, lookup_candidate_id: (_ for _ in ()).throw(
            api_error(
                404,
                "retrieval_learning_candidate_evaluation_not_found",
                "Retrieval learning candidate evaluation not found.",
                candidate_evaluation_id=str(lookup_candidate_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "retrieval_learning_candidate_evaluation_not_found"
    assert response.json()["error_context"]["candidate_evaluation_id"] == str(
        candidate_evaluation_id
    )


def test_retrieval_reranker_artifact_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    artifact_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_reranker_artifact_detail",
        lambda session, lookup_artifact_id: (_ for _ in ()).throw(
            api_error(
                404,
                "retrieval_reranker_artifact_not_found",
                "Retrieval reranker artifact not found.",
                artifact_id=str(lookup_artifact_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/retrieval-learning/reranker-artifacts/{artifact_id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "retrieval_reranker_artifact_not_found"
    assert response.json()["error_context"]["artifact_id"] == str(artifact_id)


def test_search_audit_bundle_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    bundle_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_export",
        lambda session, lookup_bundle_id, *, storage_service: (_ for _ in ()).throw(
            api_error(
                404,
                "audit_bundle_export_not_found",
                "Audit bundle export not found.",
                bundle_id=str(lookup_bundle_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/audit-bundles/{bundle_id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "audit_bundle_export_not_found"
    assert response.json()["error_context"]["bundle_id"] == str(bundle_id)


def test_search_audit_bundle_create_route_returns_machine_readable_signing_key_error(
    monkeypatch,
) -> None:
    release_id = uuid4()

    def raise_signing_key_missing(session, lookup_release_id, payload, *, storage_service):
        raise api_error(
            409,
            "audit_bundle_signing_key_missing",
            "DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY is required to export signed audit bundles.",
            release_id=str(lookup_release_id),
        )

    monkeypatch.setattr(
        "app.api.routers.search.create_search_harness_release_audit_bundle",
        raise_signing_key_missing,
    )

    client = TestClient(app)
    response = client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "operator"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "audit_bundle_signing_key_missing"
    assert response.json()["error_context"]["release_id"] == str(release_id)


def test_search_audit_bundle_validation_receipt_latest_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    bundle_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, *, storage_service: (_ for _ in ()).throw(
            api_error(
                404,
                "audit_bundle_validation_receipt_not_found",
                "Audit bundle validation receipt not found.",
                bundle_id=str(lookup_bundle_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/audit-bundles/{bundle_id}/validation-receipts/latest")

    assert response.status_code == 404
    assert response.json()["error_code"] == "audit_bundle_validation_receipt_not_found"
    assert response.json()["error_context"]["bundle_id"] == str(bundle_id)


def test_search_audit_bundle_validation_receipt_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    bundle_id = uuid4()
    receipt_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, lookup_receipt_id, *, storage_service: (
            _ for _ in ()
        ).throw(
            api_error(
                404,
                "audit_bundle_validation_receipt_not_found",
                "Audit bundle validation receipt not found.",
                bundle_id=str(lookup_bundle_id),
                receipt_id=str(lookup_receipt_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "audit_bundle_validation_receipt_not_found"
    assert response.json()["error_context"]["bundle_id"] == str(bundle_id)
    assert response.json()["error_context"]["receipt_id"] == str(receipt_id)


def test_retrieval_training_audit_bundle_latest_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    training_run_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, *, storage_service: (_ for _ in ()).throw(
            api_error(
                404,
                "retrieval_training_run_audit_bundle_not_found",
                "Retrieval training run audit bundle not found.",
                retrieval_training_run_id=str(lookup_training_run_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles/latest"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "retrieval_training_run_audit_bundle_not_found"
    assert response.json()["error_context"]["retrieval_training_run_id"] == str(
        training_run_id
    )


def test_retrieval_training_audit_bundle_create_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    training_run_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.create_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, payload, *, storage_service: (
            _ for _ in ()
        ).throw(
            api_error(
                409,
                "retrieval_training_run_not_completed",
                "Retrieval training run must be completed before exporting an audit bundle.",
                retrieval_training_run_id=str(lookup_training_run_id),
                status="failed",
            )
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles",
        json={"created_by": "operator"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "retrieval_training_run_not_completed"
    assert response.json()["error_context"]["retrieval_training_run_id"] == str(
        training_run_id
    )
