from __future__ import annotations

import json

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
    def scalars(self):
        return self

    def all(self):
        return []


class _StatementCaptureSession:
    def __init__(self) -> None:
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return _StatementCaptureResult()


def test_search_replay_regression_query_allows_feedback_zero_result_runs() -> None:
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

    assert "search_replay_runs.status = 'failed'" in compiled
    assert "search_replay_runs.failed_count > 0" in compiled
    assert "search_replay_runs.source_type != 'feedback'" in compiled
    assert "search_replay_runs.zero_result_count > 0" in compiled
