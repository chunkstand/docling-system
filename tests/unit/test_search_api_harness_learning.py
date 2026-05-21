from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def _evaluation_response(evaluation_id) -> dict:
    return {
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


def _candidate_response(
    candidate_evaluation_id,
    retrieval_training_run_id,
    judgment_set_id,
    evaluation_id,
    release_id,
    semantic_governance_event_id,
) -> dict:
    return {
        "schema_name": "retrieval_learning_candidate_evaluation",
        "schema_version": "1.0",
        "candidate_evaluation_id": str(candidate_evaluation_id),
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
        "evaluation": _evaluation_response(evaluation_id),
        "release": _release_response(release_id, evaluation_id),
    }


def _reranker_artifact_response(
    artifact_id,
    retrieval_training_run_id,
    judgment_set_id,
    candidate_evaluation_id,
    evaluation_id,
    release_id,
    semantic_governance_event_id,
) -> dict:
    candidate_response = _candidate_response(
        candidate_evaluation_id,
        retrieval_training_run_id,
        judgment_set_id,
        evaluation_id,
        release_id,
        semantic_governance_event_id,
    )
    return {
        "schema_name": "retrieval_reranker_artifact",
        "schema_version": "1.0",
        "artifact_id": str(artifact_id),
        "retrieval_training_run_id": str(retrieval_training_run_id),
        "judgment_set_id": str(judgment_set_id),
        "retrieval_learning_candidate_evaluation_id": str(candidate_evaluation_id),
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
        "change_impact_report": {"affected_trace_summary": {"affected_claim_count": 1}},
        "evaluation": _evaluation_response(evaluation_id),
        "release": _release_response(release_id, evaluation_id),
        "candidate_evaluation": candidate_response,
    }


def test_retrieval_learning_candidate_routes_return_harness_payloads(monkeypatch) -> None:
    candidate_evaluation_id = uuid4()
    retrieval_training_run_id = uuid4()
    expected_training_run_id = retrieval_training_run_id
    judgment_set_id = uuid4()
    evaluation_id = uuid4()
    release_id = uuid4()
    semantic_governance_event_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.evaluate_retrieval_learning_candidate",
        lambda session, payload: _candidate_response(
            candidate_evaluation_id,
            payload.retrieval_training_run_id,
            judgment_set_id,
            evaluation_id,
            release_id,
            semantic_governance_event_id,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_retrieval_learning_candidate_evaluations",
        lambda session,
        limit=20,
        retrieval_training_run_id=None,
        candidate_harness_name=None: [
            _candidate_response(
                candidate_evaluation_id,
                expected_training_run_id,
                judgment_set_id,
                evaluation_id,
                release_id,
                semantic_governance_event_id,
            )
        ],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_learning_candidate_evaluation_detail",
        lambda session, lookup_candidate_id: {
            **_candidate_response(
                lookup_candidate_id,
                retrieval_training_run_id,
                judgment_set_id,
                evaluation_id,
                release_id,
                semantic_governance_event_id,
            ),
            "candidate_evaluation_id": str(lookup_candidate_id),
        },
    )

    client = TestClient(app)
    create_response = client.post(
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

    assert create_response.status_code == 200
    assert create_response.headers["Location"] == (
        f"/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}"
    )
    assert create_response.json()["training_dataset_sha256"] == "training-sha"
    assert create_response.json()["release"]["release_id"] == str(release_id)

    list_response = client.get("/search/retrieval-learning/candidate-evaluations")
    assert list_response.status_code == 200
    assert list_response.json()[0]["candidate_evaluation_id"] == str(candidate_evaluation_id)

    detail_response = client.get(
        f"/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["semantic_governance_event_id"] == str(
        semantic_governance_event_id
    )


def test_retrieval_reranker_artifact_routes_return_harness_payloads(monkeypatch) -> None:
    artifact_id = uuid4()
    retrieval_training_run_id = uuid4()
    expected_training_run_id = retrieval_training_run_id
    judgment_set_id = uuid4()
    candidate_evaluation_id = uuid4()
    evaluation_id = uuid4()
    release_id = uuid4()
    semantic_governance_event_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.create_retrieval_reranker_artifact",
        lambda session, payload: _reranker_artifact_response(
            artifact_id,
            payload.retrieval_training_run_id,
            judgment_set_id,
            candidate_evaluation_id,
            evaluation_id,
            release_id,
            semantic_governance_event_id,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_retrieval_reranker_artifacts",
        lambda session,
        limit=20,
        retrieval_training_run_id=None,
        candidate_harness_name=None: [
            _reranker_artifact_response(
                artifact_id,
                expected_training_run_id,
                judgment_set_id,
                candidate_evaluation_id,
                evaluation_id,
                release_id,
                semantic_governance_event_id,
            )
        ],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_reranker_artifact_detail",
        lambda session, lookup_artifact_id: {
            **_reranker_artifact_response(
                lookup_artifact_id,
                retrieval_training_run_id,
                judgment_set_id,
                candidate_evaluation_id,
                evaluation_id,
                release_id,
                semantic_governance_event_id,
            ),
            "artifact_id": str(lookup_artifact_id),
        },
    )

    client = TestClient(app)
    create_response = client.post(
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

    assert create_response.status_code == 200
    assert create_response.headers["Location"] == (
        f"/search/retrieval-learning/reranker-artifacts/{artifact_id}"
    )
    assert create_response.json()["artifact_sha256"] == "artifact-sha"
    assert create_response.json()["change_impact_report"]["affected_trace_summary"][
        "affected_claim_count"
    ] == 1

    list_response = client.get("/search/retrieval-learning/reranker-artifacts")
    assert list_response.status_code == 200
    assert list_response.json()[0]["artifact_id"] == str(artifact_id)

    detail_response = client.get(f"/search/retrieval-learning/reranker-artifacts/{artifact_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["candidate_evaluation"]["candidate_evaluation_id"] == str(
        candidate_evaluation_id
    )
