from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import SearchReplayQueryResponse, SearchReplayRunDetailResponse
from app.services.search_replays import compare_search_replay_runs, export_ranking_dataset


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
                )
            if model.__name__ == "SearchRequestResult" and key == result_id:
                return SimpleNamespace(
                    id=result_id,
                    result_type="chunk",
                    table_id=None,
                    chunk_id=uuid4(),
                    rerank_features_json={"base_score": 0.2},
                )
            return None

    rows = export_ranking_dataset(FakeSession(), limit=10)

    assert rows[0]["dataset_type"] == "feedback"
    assert rows[0]["feedback_type"] == "relevant"
    assert rows[1]["dataset_type"] == "replay"
    assert rows[1]["passed"] is True
