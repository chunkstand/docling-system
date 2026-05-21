from __future__ import annotations

from app.api.main import app


def test_search_harness_route_surface_smoke_contract_is_registered_on_main_app() -> None:
    paths = app.openapi()["paths"]
    assert {"get"} <= set(paths["/search/harnesses"])
    assert {"get"} <= set(paths["/search/harnesses/{harness_name}/descriptor"])
    assert {"get", "post"} <= set(paths["/search/harness-evaluations"])
    assert {"get"} <= set(paths["/search/harness-evaluations/{evaluation_id}"])
    assert {"get"} <= set(paths["/search/harness-evaluations/{evaluation_id}/explain"])
    assert {"get", "post"} <= set(paths["/search/harness-releases"])
    assert {"get"} <= set(paths["/search/harness-releases/{release_id}"])
    assert {"get"} <= set(paths["/search/harness-releases/{release_id}/readiness"])
    assert {"post"} <= set(paths["/search/harness-releases/{release_id}/readiness-assessments"])
    assert {"get"} <= set(
        paths["/search/harness-releases/{release_id}/readiness-assessments/latest"]
    )
    assert {"get"} <= set(
        paths["/search/harness-releases/{release_id}/readiness-assessments/{assessment_id}"]
    )
    assert {"get", "post"} <= set(paths["/search/retrieval-learning/candidate-evaluations"])
    assert {"get"} <= set(
        paths["/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}"]
    )
    assert {"get", "post"} <= set(paths["/search/retrieval-learning/reranker-artifacts"])
    assert {"get"} <= set(paths["/search/retrieval-learning/reranker-artifacts/{artifact_id}"])
    assert {"post"} <= set(paths["/search/harness-releases/{release_id}/audit-bundles"])
    assert {"get"} <= set(paths["/search/harness-releases/{release_id}/audit-bundles/latest"])
    assert {"post"} <= set(paths["/search/retrieval-training-runs/{training_run_id}/audit-bundles"])
    assert {"get"} <= set(
        paths["/search/retrieval-training-runs/{training_run_id}/audit-bundles/latest"]
    )
    assert {"get"} <= set(paths["/search/audit-bundles/{bundle_id}"])
    assert {"get", "post"} <= set(paths["/search/audit-bundles/{bundle_id}/validation-receipts"])
    assert {"get"} <= set(paths["/search/audit-bundles/{bundle_id}/validation-receipts/latest"])
    assert {"get"} <= set(
        paths["/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}"]
    )
