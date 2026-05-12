from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
)
from app.services.retrieval_learning_candidates import (
    learning_candidate_package,
    thresholds_from_candidate_request,
)


def test_thresholds_from_candidate_request_preserves_gate_fields() -> None:
    request = RetrievalLearningCandidateEvaluationRequest(
        retrieval_training_run_id=uuid4(),
        candidate_harness_name="candidate_v2",
        baseline_harness_name="default_v1",
        source_types=["feedback"],
        limit=5,
        max_total_regressed_count=1,
        max_mrr_drop=0.05,
        max_zero_result_count_increase=2,
        max_foreign_top_result_count_increase=3,
        min_total_shared_query_count=7,
        requested_by="operator",
        review_note="fixture",
    )

    assert thresholds_from_candidate_request(request) == {
        "max_total_regressed_count": 1,
        "max_mrr_drop": 0.05,
        "max_zero_result_count_increase": 2,
        "max_foreign_top_result_count_increase": 3,
        "min_total_shared_query_count": 7,
    }


def test_learning_candidate_package_embeds_training_and_gate_state() -> None:
    training_run = SimpleNamespace(
        id=uuid4(),
        judgment_set_id=uuid4(),
        training_dataset_sha256="training-sha",
        example_count=12,
        positive_count=6,
        negative_count=3,
        missing_count=2,
        hard_negative_count=1,
        summary_json={"training_example_count": 12},
    )
    request = RetrievalLearningCandidateEvaluationRequest(
        retrieval_training_run_id=training_run.id,
        candidate_harness_name="candidate_v2",
        baseline_harness_name="default_v1",
        source_types=["feedback"],
        limit=5,
        requested_by="operator",
        review_note="fixture",
    )
    evaluation = SearchHarnessEvaluationResponse(
        evaluation_id=uuid4(),
        status="completed",
        baseline_harness_name="default_v1",
        candidate_harness_name="candidate_v2",
        source_types=["feedback"],
        limit=5,
        total_shared_query_count=9,
        total_improved_count=4,
        total_regressed_count=1,
        total_unchanged_count=4,
        created_at="2026-05-11T00:00:00Z",
        completed_at="2026-05-11T00:00:01Z",
        sources=[],
    )
    release = SearchHarnessReleaseResponse(
        release_id=uuid4(),
        evaluation_id=evaluation.evaluation_id,
        outcome="passed",
        baseline_harness_name="default_v1",
        candidate_harness_name="candidate_v2",
        limit=5,
        source_types=["feedback"],
        thresholds={"max_total_regressed_count": 0},
        metrics={"total_shared_query_count": 9},
        reasons=[],
        release_package_sha256="release-sha",
        requested_by="operator",
        review_note="fixture",
        created_at="2026-05-11T00:00:02Z",
        details={},
        evaluation_snapshot=evaluation.model_dump(mode="json"),
    )

    package = learning_candidate_package(
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        request=request,
    )

    assert package["schema_name"] == "retrieval_learning_candidate_package"
    assert package["retrieval_training_run"]["training_dataset_sha256"] == "training-sha"
    assert package["candidate_request"]["thresholds"]["min_total_shared_query_count"] == 1
    assert package["release"]["outcome"] == "passed"
