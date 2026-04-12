from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import SearchHarnessEvaluationRequest
from app.services.search_harness_evaluations import (
    evaluate_search_harness,
    list_search_harness_definitions,
)


def test_list_search_harness_definitions_exposes_default() -> None:
    rows = list_search_harness_definitions()

    assert rows
    assert any(row.is_default for row in rows)
    assert rows[0].reranker_name == "linear_feature_reranker"


def test_evaluate_search_harness_aggregates_per_source(monkeypatch) -> None:
    baseline_eval_id = uuid4()
    candidate_eval_id = uuid4()
    baseline_feedback_id = uuid4()
    candidate_feedback_id = uuid4()

    def fake_run_search_replay_suite(session, payload):
        replay_run_id = (
            baseline_eval_id
            if payload.harness_name == "default_v1" and payload.source_type == "evaluation_queries"
            else candidate_eval_id
            if payload.harness_name == "wide_v2" and payload.source_type == "evaluation_queries"
            else baseline_feedback_id
            if payload.harness_name == "default_v1"
            else candidate_feedback_id
        )
        passed_count = 1 if payload.harness_name == "default_v1" else 2
        return SimpleNamespace(
            replay_run_id=replay_run_id,
            query_count=3,
            passed_count=passed_count,
            zero_result_count=0,
            table_hit_count=1,
            top_result_changes=0,
        )

    def fake_compare_search_replay_runs(session, baseline_replay_run_id, candidate_replay_run_id):
        improved_count = int(
            candidate_replay_run_id in {candidate_eval_id, candidate_feedback_id}
        )
        return SimpleNamespace(
            shared_query_count=3,
            improved_count=improved_count,
            regressed_count=0,
            unchanged_count=2,
        )

    monkeypatch.setattr(
        "app.services.search_harness_evaluations.run_search_replay_suite",
        fake_run_search_replay_suite,
    )
    monkeypatch.setattr(
        "app.services.search_harness_evaluations.compare_search_replay_runs",
        fake_compare_search_replay_runs,
    )

    response = evaluate_search_harness(
        None,
        SearchHarnessEvaluationRequest(
            candidate_harness_name="wide_v2",
            baseline_harness_name="default_v1",
            source_types=["evaluation_queries", "feedback"],
            limit=5,
        ),
    )

    assert response.candidate_harness_name == "wide_v2"
    assert response.total_shared_query_count == 6
    assert response.total_improved_count == 2
    assert response.sources[0].source_type == "evaluation_queries"
    assert response.sources[0].baseline_table_hit_count == 1
