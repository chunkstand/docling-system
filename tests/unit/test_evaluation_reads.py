from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services import evaluations
from app.services.evaluation_reads import (
    _to_evaluation_summary,
    get_latest_document_evaluation,
    get_latest_evaluation_summaries,
    get_latest_evaluation_summary,
    get_latest_evaluations_by_run_id,
)


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = list(rows)

    def scalars(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *results):
        self._results = list(results)

    def execute(self, _statement):
        return self._results.pop(0)


def _timestamp(seconds: int = 0) -> datetime:
    return datetime(2026, 5, 13, 23, 0, seconds, tzinfo=UTC)


def _evaluation_row(*, run_id=None, summary_json=None):
    return SimpleNamespace(
        id=uuid4(),
        run_id=run_id or uuid4(),
        corpus_name="default",
        fixture_name="fixture",
        status="completed",
        error_message=None,
        summary_json=summary_json
        or {
            "query_count": 2,
            "passed_queries": 2,
            "failed_queries": 0,
            "regressed_queries": 0,
            "improved_queries": 0,
            "stable_queries": 2,
            "baseline_run_id": None,
        },
        created_at=_timestamp(),
        completed_at=_timestamp(1),
    )


def test_evaluations_facade_forwards_read_helpers(monkeypatch) -> None:
    run_id = uuid4()
    document = SimpleNamespace(latest_run_id=uuid4())
    expected_summary = {"summary": "ok"}
    expected_detail = {"detail": "ok"}
    expected_rows = {run_id: "row"}
    expected_summaries = {run_id: "summary"}

    monkeypatch.setattr(
        "app.services.evaluations._evaluation_reads.get_latest_evaluation_summary",
        lambda session, requested_run_id: (
            expected_summary if requested_run_id == run_id else None
        ),
    )
    monkeypatch.setattr(
        "app.services.evaluations._evaluation_reads.get_latest_evaluations_by_run_id",
        lambda session, run_ids: expected_rows,
    )
    monkeypatch.setattr(
        "app.services.evaluations._evaluation_reads.get_latest_evaluation_summaries",
        lambda session, run_ids: expected_summaries,
    )
    monkeypatch.setattr(
        "app.services.evaluations._evaluation_reads.get_latest_document_evaluation",
        lambda session, requested_document: (
            expected_detail if requested_document is document else None
        ),
    )

    assert evaluations.get_latest_evaluation_summary(None, run_id) == expected_summary
    assert evaluations.get_latest_evaluations_by_run_id(None, {run_id}) == expected_rows
    assert evaluations.get_latest_evaluation_summaries(None, {run_id}) == expected_summaries
    assert evaluations.get_latest_document_evaluation(None, document) == expected_detail


def test_to_evaluation_summary_converts_baseline_run_id() -> None:
    baseline_run_id = uuid4()
    evaluation = _evaluation_row(
        summary_json={
            "query_count": 3,
            "passed_queries": 2,
            "failed_queries": 1,
            "regressed_queries": 1,
            "improved_queries": 0,
            "stable_queries": 2,
            "baseline_run_id": str(baseline_run_id),
        }
    )

    summary = _to_evaluation_summary(evaluation)

    assert summary.evaluation_id == evaluation.id
    assert summary.baseline_run_id == baseline_run_id
    assert summary.failed_queries == 1


def test_get_latest_evaluation_summary_returns_none_for_missing_run_id() -> None:
    assert get_latest_evaluation_summary(FakeSession(), None) is None


def test_get_latest_evaluation_summary_returns_latest_row() -> None:
    run_id = uuid4()
    evaluation = _evaluation_row(run_id=run_id)

    summary = get_latest_evaluation_summary(FakeSession(FakeScalarResult([evaluation])), run_id)

    assert summary is not None
    assert summary.run_id == run_id
    assert summary.query_count == 2


def test_get_latest_evaluations_by_run_id_returns_mapping() -> None:
    run_one_id = uuid4()
    run_two_id = uuid4()
    rows = [
        _evaluation_row(run_id=run_one_id),
        _evaluation_row(run_id=run_two_id),
    ]

    evaluation_map = get_latest_evaluations_by_run_id(
        FakeSession(FakeScalarResult(rows)),
        {run_one_id, run_two_id},
    )

    assert evaluation_map == {row.run_id: row for row in rows}


def test_get_latest_evaluation_summaries_returns_empty_for_empty_run_ids() -> None:
    assert get_latest_evaluation_summaries(FakeSession(), []) == {}


def test_get_latest_document_evaluation_returns_none_without_latest_run() -> None:
    document = SimpleNamespace(latest_run_id=None)

    assert get_latest_document_evaluation(FakeSession(), document) is None


def test_get_latest_document_evaluation_builds_detail_response() -> None:
    run_id = uuid4()
    evaluation = _evaluation_row(run_id=run_id)
    query_rows = [
        SimpleNamespace(
            query_text="vent stack",
            mode="hybrid",
            details_json={"evaluation_kind": "answer", "candidate_rank": 1},
            expected_result_type="table",
            expected_top_n=3,
            passed=True,
            candidate_rank=1,
            baseline_rank=None,
            rank_delta=None,
            candidate_score=0.98,
            baseline_score=None,
            candidate_result_type="table",
            baseline_result_type=None,
            candidate_label="Vent stack sizing",
            baseline_label=None,
        )
    ]
    document = SimpleNamespace(latest_run_id=run_id)

    detail = get_latest_document_evaluation(
        FakeSession(
            FakeScalarResult([evaluation]),
            FakeScalarResult(query_rows),
        ),
        document,
    )

    assert detail is not None
    assert detail.run_id == run_id
    assert detail.summary["query_count"] == 2
    assert detail.query_results[0].evaluation_kind == "answer"
    assert detail.query_results[0].candidate_label == "Vent stack sizing"
