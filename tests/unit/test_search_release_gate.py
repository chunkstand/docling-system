from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import SearchHarnessRelease, SearchReplayRun
from app.schemas.agent_tasks import VerifySearchHarnessEvaluationTaskInput
from app.schemas.search import (
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSourceResponse,
)
from app.services.search_release_gate import (
    evaluate_search_harness_release_gate,
    record_search_harness_release_gate,
)


def _build_replay_run(*, replay_run_id, status: str = "completed") -> SearchReplayRun:
    now = datetime.now(UTC)
    return SearchReplayRun(
        id=replay_run_id,
        source_type="evaluation_queries",
        status=status,
        harness_name="wide_v2",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="wide_v2",
        harness_config_json={"base_harness_name": "default_v1"},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        created_at=now,
        completed_at=now if status == "completed" else None,
    )


class FakeSession:
    def __init__(self, replay_runs) -> None:
        self.replay_runs = replay_runs
        self.added = []

    def get(self, model, key):
        if model.__name__ == "SearchReplayRun":
            return self.replay_runs.get(key)
        raise AssertionError(f"Unexpected model lookup: {model.__name__}")

    def add(self, row):
        self.added.append(row)

    def flush(self):
        return None


def test_release_gate_uses_structured_error_for_incomplete_replay_run() -> None:
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
    evaluation = SearchHarnessEvaluationResponse(
        baseline_harness_name="default_v1",
        candidate_harness_name="wide_v2",
        limit=3,
        total_shared_query_count=4,
        total_improved_count=1,
        total_regressed_count=0,
        total_unchanged_count=3,
        sources=[
            SearchHarnessEvaluationSourceResponse(
                source_type="evaluation_queries",
                baseline_replay_run_id=baseline_replay_run_id,
                candidate_replay_run_id=candidate_replay_run_id,
                shared_query_count=4,
                improved_count=1,
                regressed_count=0,
                unchanged_count=3,
            )
        ],
    )
    payload = VerifySearchHarnessEvaluationTaskInput(target_task_id=uuid4())

    with pytest.raises(HTTPException) as exc_info:
        evaluate_search_harness_release_gate(
            FakeSession(
                {
                    baseline_replay_run_id: _build_replay_run(
                        replay_run_id=baseline_replay_run_id,
                        status="processing",
                    ),
                    candidate_replay_run_id: _build_replay_run(
                        replay_run_id=candidate_replay_run_id,
                    ),
                }
            ),
            evaluation,
            payload,
        )

    exc = exc_info.value
    assert exc.status_code == 409
    assert exc.detail["code"] == "search_replay_run_not_completed"
    assert exc.detail["context"]["label"] == "evaluation_queries baseline"
    assert exc.detail["context"]["replay_run_status"] == "processing"


def test_release_gate_records_missing_replay_runs_without_exception() -> None:
    candidate_replay_run_id = uuid4()
    evaluation = SearchHarnessEvaluationResponse(
        baseline_harness_name="default_v1",
        candidate_harness_name="wide_v2",
        limit=3,
        total_shared_query_count=4,
        total_improved_count=1,
        total_regressed_count=0,
        total_unchanged_count=3,
        sources=[
            SearchHarnessEvaluationSourceResponse(
                source_type="evaluation_queries",
                baseline_replay_run_id=uuid4(),
                candidate_replay_run_id=candidate_replay_run_id,
                shared_query_count=4,
                improved_count=1,
                regressed_count=0,
                unchanged_count=3,
            )
        ],
    )
    payload = VerifySearchHarnessEvaluationTaskInput(target_task_id=uuid4())

    outcome = evaluate_search_harness_release_gate(
        FakeSession(
            {candidate_replay_run_id: _build_replay_run(replay_run_id=candidate_replay_run_id)}
        ),
        evaluation,
        payload,
    )

    assert outcome.outcome == "failed"
    assert outcome.reasons == ["evaluation_queries: baseline replay run is missing."]


def test_release_gate_records_durable_release_package() -> None:
    evaluation_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
    evaluation = SearchHarnessEvaluationResponse(
        evaluation_id=evaluation_id,
        baseline_harness_name="default_v1",
        candidate_harness_name="wide_v2",
        limit=3,
        source_types=["evaluation_queries"],
        total_shared_query_count=4,
        total_improved_count=1,
        total_regressed_count=0,
        total_unchanged_count=3,
        sources=[
            SearchHarnessEvaluationSourceResponse(
                source_type="evaluation_queries",
                baseline_replay_run_id=baseline_replay_run_id,
                candidate_replay_run_id=candidate_replay_run_id,
                shared_query_count=4,
                improved_count=1,
                regressed_count=0,
                unchanged_count=3,
            )
        ],
    )
    payload = VerifySearchHarnessEvaluationTaskInput(
        target_task_id=uuid4(),
        min_total_shared_query_count=1,
    )
    session = FakeSession(
        {
            baseline_replay_run_id: _build_replay_run(replay_run_id=baseline_replay_run_id),
            candidate_replay_run_id: _build_replay_run(replay_run_id=candidate_replay_run_id),
        }
    )

    release = record_search_harness_release_gate(
        session,
        evaluation,
        payload,
        requested_by="operator",
        review_note="candidate replay package",
    )

    rows = [row for row in session.added if isinstance(row, SearchHarnessRelease)]
    assert len(rows) == 1
    assert rows[0].search_harness_evaluation_id == evaluation_id
    assert rows[0].release_package_sha256 == release.release_package_sha256
    assert release.outcome == "passed"
    assert release.evaluation_id == evaluation_id
    assert release.requested_by == "operator"
    assert release.release_package_sha256
    assert release.evaluation_snapshot["evaluation_id"] == str(evaluation_id)
