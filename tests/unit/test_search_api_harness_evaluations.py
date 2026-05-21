from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.errors import api_error
from app.api.main import app


def _evaluation_response(
    evaluation_id,
    baseline_replay_run_id,
    candidate_replay_run_id,
    *,
    candidate_harness_name: str = "wide_v2",
) -> dict:
    return {
        "evaluation_id": str(evaluation_id),
        "status": "completed",
        "baseline_harness_name": "default_v1",
        "candidate_harness_name": candidate_harness_name,
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
    }


def _release_response(release_id, evaluation_id) -> dict:
    return {
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


def _release_readiness_response(release_id) -> dict:
    return {
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


def test_search_harness_evaluation_routes_return_focused_payloads(monkeypatch) -> None:
    evaluation_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.evaluate_search_harness",
        lambda session, payload: _evaluation_response(
            evaluation_id,
            baseline_replay_run_id,
            candidate_replay_run_id,
            candidate_harness_name=payload.candidate_harness_name,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_search_harness_evaluations",
        lambda session, limit=20, candidate_harness_name=None: [
            _evaluation_response(
                evaluation_id,
                baseline_replay_run_id,
                candidate_replay_run_id,
            )
        ],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_evaluation_detail",
        lambda session, lookup_evaluation_id: _evaluation_response(
            lookup_evaluation_id,
            baseline_replay_run_id,
            candidate_replay_run_id,
        ),
    )

    client = TestClient(app)
    create_response = client.post(
        "/search/harness-evaluations",
        json={
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "source_types": ["cross_document_prose_regressions"],
            "limit": 5,
        },
    )

    assert create_response.status_code == 200
    assert create_response.headers["Location"] == f"/search/harness-evaluations/{evaluation_id}"
    assert create_response.json()["candidate_harness_name"] == "wide_v2"
    assert create_response.json()["sources"][0]["candidate_replay_run_id"] == str(
        candidate_replay_run_id
    )

    list_response = client.get("/search/harness-evaluations")
    assert list_response.status_code == 200
    assert list_response.json()[0]["evaluation_id"] == str(evaluation_id)

    detail_response = client.get(f"/search/harness-evaluations/{evaluation_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["sources"][0]["baseline_replay_run_id"] == str(
        baseline_replay_run_id
    )


def test_search_harness_release_routes_return_focused_payloads(monkeypatch) -> None:
    evaluation_id = uuid4()
    release_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.create_search_harness_release_gate",
        lambda session, payload: _release_response(release_id, payload.evaluation_id),
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_search_harness_releases",
        lambda session, limit=20, candidate_harness_name=None, outcome=None: [
            _release_response(release_id, evaluation_id)
        ],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_release_detail",
        lambda session, lookup_release_id: _release_response(
            lookup_release_id,
            evaluation_id,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_release_readiness",
        lambda session, lookup_release_id: _release_readiness_response(lookup_release_id),
    )

    client = TestClient(app)
    create_response = client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "requested_by": "operator",
            "review_note": "release gate",
        },
    )

    assert create_response.status_code == 200
    assert create_response.headers["Location"] == f"/search/harness-releases/{release_id}"
    assert create_response.json()["release_id"] == str(release_id)
    assert create_response.json()["outcome"] == "passed"

    list_response = client.get("/search/harness-releases")
    assert list_response.status_code == 200
    assert list_response.json()[0]["release_package_sha256"] == "abc123"

    detail_response = client.get(f"/search/harness-releases/{release_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["evaluation_snapshot"]["evaluation_id"] == str(
        evaluation_id
    )

    readiness_response = client.get(f"/search/harness-releases/{release_id}/readiness")
    assert readiness_response.status_code == 200
    assert readiness_response.json()["ready"] is True
    assert readiness_response.json()["semantic_governance"]["complete"] is True


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
