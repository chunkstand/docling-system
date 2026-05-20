from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from app.agent_trace_review import (
    AGENT_TRACE_REVIEW_REPORT_SCHEMA_NAME,
    _collect_search_replay_regression_observations,
    build_agent_trace_review_report,
)
from app.services.improvement_cases import ImprovementCaseObservation


def _observation(source_type: str, source_ref: str) -> ImprovementCaseObservation:
    return ImprovementCaseObservation(
        title="Trace finding",
        observed_failure="A trace failed.",
        cause_class="missing_context",
        source_type=source_type,
        source_ref=source_ref,
    )


def test_agent_trace_review_report_groups_observations(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent_trace_review.collect_failed_agent_task_observations",
        lambda session, *, limit, workflow_version: [_observation("agent_task", "task:1")],
    )
    monkeypatch.setattr(
        "app.agent_trace_review.collect_failed_agent_verification_observations",
        lambda session, *, limit, workflow_version: [
            _observation("agent_verification", "verification:1")
        ],
    )
    monkeypatch.setattr(
        "app.agent_trace_review.collect_eval_failure_case_observations",
        lambda session, *, limit, workflow_version: [
            _observation("eval_failure", "eval:1")
        ],
    )
    monkeypatch.setattr(
        "app.agent_trace_review._collect_search_replay_regression_observations",
        lambda session, *, limit, workflow_version: [
            _observation("search_replay", "replay:1")
        ],
    )
    monkeypatch.setattr(
        "app.agent_trace_review._collect_stale_approval_observations",
        lambda session, *, limit, workflow_version: [],
    )

    report = build_agent_trace_review_report(
        object(),
        include_workspace=False,
        limit=10,
    )

    assert report["schema_name"] == AGENT_TRACE_REVIEW_REPORT_SCHEMA_NAME
    assert report["observation_count"] == 4
    assert report["improvement_case_intake"]["source"] == "agent-trace-review-report"
    assert {row["category"] for row in report["observations"]} == {
        "failed_agent_tasks",
        "failed_agent_verifications",
        "eval_failure_cases",
        "search_replay_regressions",
    }
    json.dumps(report)


class _StatementCaptureResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _StatementCaptureSession:
    def __init__(self) -> None:
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return _StatementCaptureResult()


def test_search_replay_regression_query_orders_recent_runs() -> None:
    session = _StatementCaptureSession()

    _collect_search_replay_regression_observations(
        session,
        limit=5,
        workflow_version="improvement_v1",
    )

    compiled = str(
        session.statement.compile(
            compile_kwargs={"literal_binds": True}
        )
    )

    assert "FROM search_replay_runs" in compiled
    assert "ORDER BY search_replay_runs.created_at DESC" in compiled
    assert "LIMIT 50" in compiled


class _ReplayObservationSession:
    def __init__(self, replay_runs, replay_queries) -> None:
        self.replay_runs = replay_runs
        self.replay_queries = replay_queries

    def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"].__name__
        if entity == "SearchReplayRun":
            return _StatementCaptureResult(self.replay_runs)
        if entity == "SearchReplayQuery":
            params = statement.compile().params
            replay_run_id = next(value for value in params.values() if value is not False)
            rows = [row for row in self.replay_queries if row.replay_run_id == replay_run_id]
            return _StatementCaptureResult(rows)
        raise AssertionError(f"unexpected entity {entity}")


def test_search_replay_regression_observations_skip_intentional_learning_suite_failures() -> None:
    intentional_feedback_run = SimpleNamespace(
        id=uuid4(),
        source_type="feedback",
        status="completed",
        failed_count=2,
        zero_result_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        created_at=None,
    )
    actionable_eval_run = SimpleNamespace(
        id=uuid4(),
        source_type="evaluation_queries",
        status="completed",
        failed_count=1,
        zero_result_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        created_at=None,
    )
    replay_queries = [
        SimpleNamespace(
            replay_run_id=intentional_feedback_run.id,
            passed=False,
            details_json={
                "source_reason": "feedback_label",
                "feedback_type": "no_answer",
            },
            created_at=None,
        ),
        SimpleNamespace(
            replay_run_id=intentional_feedback_run.id,
            passed=False,
            details_json={
                "source_reason": "feedback_label",
                "feedback_type": "irrelevant",
            },
            created_at=None,
        ),
        SimpleNamespace(
            replay_run_id=actionable_eval_run.id,
            passed=False,
            details_json={
                "source_reason": "evaluation_query",
                "feedback_type": None,
            },
            created_at=None,
        ),
    ]
    session = _ReplayObservationSession(
        [intentional_feedback_run, actionable_eval_run],
        replay_queries,
    )

    observations = _collect_search_replay_regression_observations(
        session,
        limit=5,
        workflow_version="improvement_v1",
    )

    assert len(observations) == 1
    assert observations[0].source_ref == f"search_replay_run:{actionable_eval_run.id}"


def test_search_replay_regression_observations_skip_intentional_negative_claim_feedback() -> None:
    run = SimpleNamespace(
        id=uuid4(),
        source_type="technical_report_claim_feedback",
        status="completed",
        failed_count=1,
        zero_result_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        created_at=None,
    )
    session = _ReplayObservationSession(
        [run],
        [
            SimpleNamespace(
                replay_run_id=run.id,
                passed=False,
                details_json={
                    "learning_label": "negative",
                    "claim_feedback_replay_verdict": "negative_target_still_prominent",
                    "claim_feedback_traceability_complete": True,
                },
                created_at=None,
            )
        ],
    )

    observations = _collect_search_replay_regression_observations(
        session,
        limit=5,
        workflow_version="improvement_v1",
    )

    assert observations == []


def test_search_replay_regression_observations_ignore_superseded_failed_runs() -> None:
    source_signature = {
        "source_type": "evaluation_queries",
        "harness_name": "default_v1",
        "reranker_name": "linear_feature_reranker",
        "reranker_version": "v1",
        "retrieval_profile_name": "default_v1",
    }
    older_failed = SimpleNamespace(
        id=uuid4(),
        status="completed",
        failed_count=1,
        zero_result_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=1,
        **source_signature,
    )
    newer_passed = SimpleNamespace(
        id=uuid4(),
        status="completed",
        failed_count=0,
        zero_result_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=2,
        **source_signature,
    )
    session = _ReplayObservationSession(
        [newer_passed, older_failed],
        [
            SimpleNamespace(
                replay_run_id=older_failed.id,
                passed=False,
                details_json={"source_reason": "evaluation_query"},
                created_at=None,
            )
        ],
    )

    observations = _collect_search_replay_regression_observations(
        session,
        limit=5,
        workflow_version="improvement_v1",
    )

    assert observations == []
