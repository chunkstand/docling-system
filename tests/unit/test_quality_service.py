from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.services.quality import (
    QualityContext,
    build_quality_evaluation_rows,
    build_quality_failures,
    build_quality_summary,
    get_quality_trends,
    list_quality_eval_candidates,
)


def _timestamp(minutes: int = 0) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=minutes)


def test_quality_summary_and_failures_aggregate_latest_eval_state() -> None:
    doc_one_id = uuid4()
    doc_two_id = uuid4()
    run_one_id = uuid4()
    run_two_id = uuid4()
    documents = [
        SimpleNamespace(
            id=doc_one_id,
            source_filename="chapter-1.pdf",
            title="Chapter 1",
            latest_run_id=run_one_id,
            updated_at=_timestamp(2),
        ),
        SimpleNamespace(
            id=doc_two_id,
            source_filename="chapter-2.pdf",
            title="Chapter 2",
            latest_run_id=run_two_id,
            updated_at=_timestamp(1),
        ),
    ]
    runs = [
        SimpleNamespace(
            id=run_one_id,
            document_id=doc_one_id,
            run_number=3,
            status="completed",
            validation_status="passed",
            failure_stage=None,
            failure_artifact_path=None,
            error_message=None,
            created_at=_timestamp(),
            completed_at=_timestamp(3),
        ),
        SimpleNamespace(
            id=run_two_id,
            document_id=doc_two_id,
            run_number=4,
            status="failed",
            validation_status="failed",
            failure_stage="validation",
            failure_artifact_path="/tmp/failure.json",
            error_message="validation failed",
            created_at=_timestamp(),
            completed_at=_timestamp(4),
        ),
    ]
    evaluations = [
        SimpleNamespace(
            id=uuid4(),
            run_id=run_one_id,
            status="completed",
            fixture_name="fixture-one",
            error_message=None,
            summary_json={
                "query_count": 4,
                "passed_queries": 2,
                "failed_queries": 2,
                "regressed_queries": 1,
                "improved_queries": 0,
                "stable_queries": 1,
                "failed_structural_checks": 1,
                "structural_passed": False,
            },
            created_at=_timestamp(5),
        )
    ]
    context = QualityContext(documents=documents, runs=runs, evaluations=evaluations)

    rows = build_quality_evaluation_rows(context)
    summary = build_quality_summary(context, rows)
    failures = build_quality_failures(context, rows)

    assert len(rows) == 2
    assert rows[0].source_filename == "chapter-1.pdf"
    assert rows[1].evaluation_status == "missing"
    assert summary.documents_with_latest_evaluation == 1
    assert summary.missing_latest_evaluations == 1
    assert summary.total_failed_queries == 2
    assert summary.documents_with_structural_failures == 1
    assert summary.failed_run_count == 1
    assert summary.failed_runs_by_stage[0].failure_stage == "validation"
    assert {row.source_filename for row in failures.evaluation_failures} == {
        "chapter-1.pdf",
        "chapter-2.pdf",
    }
    assert failures.run_failures[0].run_id == run_two_id


def test_list_quality_eval_candidates_mines_eval_failures_and_live_search_gaps() -> None:
    document_id = uuid4()
    run_id = uuid4()
    evaluation_id = uuid4()
    search_request_id = uuid4()
    now = _timestamp()

    documents = [
        SimpleNamespace(
            id=document_id,
            source_filename="chapter-5.pdf",
            title="Chapter 5",
        )
    ]
    runs = [SimpleNamespace(id=run_id, document_id=document_id)]
    evaluations = [SimpleNamespace(id=evaluation_id, run_id=run_id, fixture_name="fixture-one")]
    evaluation_queries = [
        SimpleNamespace(
            evaluation_id=evaluation_id,
            query_text="vent stack",
            mode="hybrid",
            filters_json={"document_id": str(document_id)},
            expected_result_type="table",
            passed=False,
            created_at=now,
        )
    ]
    search_requests = [
        SimpleNamespace(
            id=search_request_id,
            origin="api",
            query_text="table 701.2",
            mode="hybrid",
            filters_json={"document_id": str(document_id)},
            tabular_query=True,
            table_hit_count=0,
            result_count=3,
            created_at=now + timedelta(minutes=1),
            evaluation_id=None,
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
                "Document": documents,
                "DocumentRun": runs,
                "DocumentRunEvaluation": evaluations,
                "DocumentRunEvaluationQuery": evaluation_queries,
                "SearchRequestRecord": search_requests,
            }
            return FakeScalarResult(mapping[entity_name])

    rows = list_quality_eval_candidates(FakeSession(), limit=10)

    assert len(rows) == 2
    assert {row.candidate_type for row in rows} == {"evaluation_failure", "live_search_gap"}
    assert {row.expected_result_type for row in rows} == {"table"}


def test_get_quality_trends_aggregates_search_feedback_and_replays() -> None:
    now = _timestamp()
    search_requests = [
        SimpleNamespace(
            created_at=now,
            result_count=0,
            table_hit_count=0,
        ),
        SimpleNamespace(
            created_at=now,
            result_count=2,
            table_hit_count=1,
        ),
    ]
    feedback_rows = [
        SimpleNamespace(feedback_type="missing_table"),
        SimpleNamespace(feedback_type="missing_table"),
        SimpleNamespace(feedback_type="relevant"),
    ]
    answer_feedback_rows = [
        SimpleNamespace(feedback_type="helpful"),
        SimpleNamespace(feedback_type="unsupported"),
    ]
    replay_run_id = uuid4()
    replay_runs = [
        SimpleNamespace(
            id=replay_run_id,
            source_type="feedback",
            status="completed",
            query_count=3,
            passed_count=2,
            failed_count=1,
            created_at=now,
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
                "SearchRequestRecord": search_requests,
                "SearchFeedback": feedback_rows,
                "ChatAnswerFeedback": answer_feedback_rows,
                "SearchReplayRun": replay_runs,
            }
            return FakeScalarResult(mapping[entity_name])

    trends = get_quality_trends(FakeSession(), day_count=2, replay_limit=5)

    assert trends.search_request_days[-1].request_count == 2
    assert trends.search_request_days[-1].zero_result_count == 1
    assert trends.feedback_counts[0].feedback_type == "missing_table"
    assert trends.answer_feedback_counts[0].feedback_type == "helpful"
    assert trends.recent_replay_runs[0].replay_run_id == replay_run_id
