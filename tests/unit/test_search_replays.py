from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import SearchReplayQueryResponse, SearchReplayRunDetailResponse
from app.services.search_replays import (
    CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
    ReplayCase,
    _evaluate_case_passed,
    _finalize_replay_rank_metrics,
    _to_replay_run_summary,
    compare_search_replay_runs,
    export_ranking_dataset,
)


def _timestamp() -> datetime:
    return datetime.now(UTC)


def test_compare_search_replay_runs_reports_improvements(monkeypatch) -> None:
    baseline_id = uuid4()
    candidate_id = uuid4()
    shared_filters = {"document_id": str(uuid4())}

    baseline = SearchReplayRunDetailResponse(
        replay_run_id=baseline_id,
        source_type="feedback",
        status="completed",
        query_count=2,
        passed_count=0,
        failed_count=2,
        zero_result_count=1,
        table_hit_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        summary={},
        query_results=[
            SearchReplayQueryResponse(
                replay_query_id=uuid4(),
                query_text="vent stack",
                mode="hybrid",
                filters=shared_filters,
                passed=False,
                result_count=0,
                created_at=_timestamp(),
            )
        ],
    )
    candidate = SearchReplayRunDetailResponse(
        replay_run_id=candidate_id,
        source_type="feedback",
        status="completed",
        query_count=2,
        passed_count=1,
        failed_count=1,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        summary={},
        query_results=[
            SearchReplayQueryResponse(
                replay_query_id=uuid4(),
                query_text="vent stack",
                mode="hybrid",
                filters=shared_filters,
                passed=True,
                result_count=2,
                created_at=_timestamp(),
            )
        ],
    )

    monkeypatch.setattr(
        "app.services.search_replays.get_search_replay_run_detail",
        lambda session, replay_run_id: baseline if replay_run_id == baseline_id else candidate,
    )

    response = compare_search_replay_runs(None, baseline_id, candidate_id)

    assert response.shared_query_count == 1
    assert response.improved_count == 1
    assert response.regressed_count == 0
    assert response.baseline_zero_result_count == 1
    assert response.candidate_zero_result_count == 0


def test_export_ranking_dataset_includes_feedback_and_replay_rows() -> None:
    request_id = uuid4()
    feedback_id = uuid4()
    result_id = uuid4()
    replay_query_id = uuid4()
    replay_run_id = uuid4()

    feedback_rows = [
        SimpleNamespace(
            id=feedback_id,
            search_request_id=request_id,
            search_request_result_id=result_id,
            feedback_type="relevant",
            note="good hit",
            created_at=_timestamp(),
            result_rank=1,
        )
    ]
    replay_rows = [
        SimpleNamespace(
            id=replay_query_id,
            replay_run_id=replay_run_id,
            query_text="vent stack",
            mode="hybrid",
            filters_json={},
            expected_result_type="chunk",
            expected_top_n=3,
            passed=True,
            result_count=2,
            table_hit_count=0,
            overlap_count=1,
            added_count=0,
            removed_count=0,
            top_result_changed=False,
            max_rank_shift=0,
            details_json={"source_reason": "feedback_label"},
            created_at=_timestamp(),
        )
    ]

    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class FakeSession:
        def execute(self, statement):
            entity_name = statement.column_descriptions[0]["entity"].__name__
            mapping = {
                "SearchFeedback": feedback_rows,
                "SearchReplayQuery": replay_rows,
            }
            return FakeScalarResult(mapping[entity_name])

        def get(self, model, key):
            if model.__name__ == "SearchRequestRecord" and key == request_id:
                return SimpleNamespace(
                    id=request_id,
                    query_text="vent stack",
                    mode="hybrid",
                    filters_json={},
                    harness_name="default_v1",
                    reranker_name="linear_feature_reranker",
                    reranker_version="v1",
                    retrieval_profile_name="default_v1",
                    harness_config_json={"harness_name": "default_v1"},
                )
            if model.__name__ == "SearchRequestResult" and key == result_id:
                return SimpleNamespace(
                    id=result_id,
                    result_type="chunk",
                    table_id=None,
                    chunk_id=uuid4(),
                    rerank_features_json={"base_score": 0.2},
                )
            if model.__name__ == "SearchReplayRun" and key == replay_run_id:
                return SimpleNamespace(
                    id=replay_run_id,
                    source_type="feedback",
                    harness_name="wide_v2",
                    reranker_name="linear_feature_reranker",
                    reranker_version="v2",
                    retrieval_profile_name="wide_v2",
                    harness_config_json={"harness_name": "wide_v2"},
                )
            return None

    rows = export_ranking_dataset(FakeSession(), limit=10)

    assert rows[0]["dataset_type"] == "feedback"
    assert rows[0]["row_schema_version"] == 2
    assert rows[0]["metadata_era"] == "harness_v1"
    assert rows[0]["feedback_type"] == "relevant"
    assert rows[1]["dataset_type"] == "replay"
    assert rows[1]["source_type"] == "feedback"
    assert rows[1]["reranker_version"] == "v2"
    assert rows[1]["metadata_era"] == "harness_v1"
    assert rows[1]["passed"] is True


def test_replay_run_summary_prefers_external_source_type_from_summary() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        source_type="evaluation_queries",
        status="completed",
        harness_name="prose_v3",
        reranker_name="linear_feature_reranker",
        reranker_version="v3",
        retrieval_profile_name="prose_v3",
        harness_config_json={},
        query_count=2,
        passed_count=2,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        completed_at=_timestamp(),
        summary_json={"source_type": CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE},
    )

    summary = _to_replay_run_summary(row)

    assert summary.source_type == CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE


def test_evaluate_case_passed_enforces_source_purity_constraints() -> None:
    execution = SimpleNamespace(
        results=[
            SimpleNamespace(result_type="chunk", source_filename="wrong.pdf"),
            SimpleNamespace(result_type="chunk", source_filename="expected.pdf"),
        ],
        table_hit_count=0,
    )

    passed, details = _evaluate_case_passed(
        ReplayCase(
            query_text="main claim",
            mode="keyword",
            filters={},
            limit=10,
            evaluation_query_id=uuid4(),
            expected_result_type="chunk",
            expected_top_n=3,
            expected_source_filename="expected.pdf",
            expected_top_result_source_filename="expected.pdf",
            minimum_top_n_hits_from_expected_document=1,
            maximum_foreign_results_before_first_expected_hit=0,
        ),
        execution,
    )

    assert passed is False
    assert details["matching_rank"] == 2
    assert details["top_result_source_filename"] == "wrong.pdf"
    assert details["foreign_results_before_first_expected_hit"] == 1


def test_finalize_replay_rank_metrics_computes_mrr() -> None:
    metrics = _finalize_replay_rank_metrics(
        {
            "query_count": 2,
            "reciprocal_rank_sum": 1.5,
            "foreign_top_result_count": 1,
            "source_constrained_query_count": 1,
        }
    )

    assert metrics["mrr"] == 0.75
    assert metrics["foreign_top_result_count"] == 1
