from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.db.models import Document, DocumentRun, DocumentRunEvaluationQuery
from app.schemas.search import SearchFilters, SearchRequest


@dataclass
class EvaluationBatchResult:
    query_count: int = 0
    retrieval_query_count: int = 0
    answer_query_count: int = 0
    passed_queries: int = 0
    failed_queries: int = 0
    passed_retrieval_queries: int = 0
    failed_retrieval_queries: int = 0
    passed_answer_queries: int = 0
    failed_answer_queries: int = 0
    regressed_queries: int = 0
    improved_queries: int = 0
    stable_queries: int = 0
    retrieval_outcomes: list[dict[str, Any]] = field(default_factory=list)

    def record_retrieval_outcome(self, outcome: dict[str, Any]) -> None:
        self.query_count += 1
        self.retrieval_query_count += 1
        self.passed_queries += int(outcome["passed"])
        self.failed_queries += int(not outcome["passed"])
        self.passed_retrieval_queries += int(outcome["passed"])
        self.failed_retrieval_queries += int(not outcome["passed"])
        self.regressed_queries += int(outcome["delta_kind"] == "regressed")
        self.improved_queries += int(outcome["delta_kind"] == "improved")
        self.stable_queries += int(outcome["delta_kind"] == "stable")
        self.retrieval_outcomes.append(outcome)

    def record_answer_outcome(self, outcome: dict[str, Any]) -> None:
        self.query_count += 1
        self.answer_query_count += 1
        self.passed_queries += int(outcome["passed"])
        self.failed_queries += int(not outcome["passed"])
        self.passed_answer_queries += int(outcome["passed"])
        self.failed_answer_queries += int(not outcome["passed"])
        self.regressed_queries += int(outcome["delta_kind"] == "regressed")
        self.improved_queries += int(outcome["delta_kind"] == "improved")
        self.stable_queries += int(outcome["delta_kind"] == "stable")

    def merge(self, other: EvaluationBatchResult) -> EvaluationBatchResult:
        return EvaluationBatchResult(
            query_count=self.query_count + other.query_count,
            retrieval_query_count=self.retrieval_query_count + other.retrieval_query_count,
            answer_query_count=self.answer_query_count + other.answer_query_count,
            passed_queries=self.passed_queries + other.passed_queries,
            failed_queries=self.failed_queries + other.failed_queries,
            passed_retrieval_queries=(
                self.passed_retrieval_queries + other.passed_retrieval_queries
            ),
            failed_retrieval_queries=(
                self.failed_retrieval_queries + other.failed_retrieval_queries
            ),
            passed_answer_queries=self.passed_answer_queries + other.passed_answer_queries,
            failed_answer_queries=self.failed_answer_queries + other.failed_answer_queries,
            regressed_queries=self.regressed_queries + other.regressed_queries,
            improved_queries=self.improved_queries + other.improved_queries,
            stable_queries=self.stable_queries + other.stable_queries,
            retrieval_outcomes=[*self.retrieval_outcomes, *other.retrieval_outcomes],
        )


def _persist_evaluation_query_row(
    session,
    *,
    evaluation_id: UUID,
    outcome: dict[str, Any],
    created_at: datetime,
) -> None:
    session.add(
        DocumentRunEvaluationQuery(
            evaluation_id=evaluation_id,
            query_text=outcome["query_text"],
            mode=outcome["mode"],
            filters_json=outcome["filters_json"],
            expected_result_type=outcome["expected_result_type"],
            expected_top_n=outcome["expected_top_n"],
            passed=outcome["passed"],
            candidate_rank=outcome["candidate_rank"],
            baseline_rank=outcome["baseline_rank"],
            rank_delta=outcome["rank_delta"],
            candidate_score=outcome["candidate_score"],
            baseline_score=outcome["baseline_score"],
            candidate_result_type=outcome["candidate_result_type"],
            baseline_result_type=outcome["baseline_result_type"],
            candidate_label=outcome["candidate_label"],
            baseline_label=outcome["baseline_label"],
            details_json=outcome["details_json"],
            created_at=created_at,
        )
    )


def execute_retrieval_queries(
    session,
    *,
    document: Document,
    run: DocumentRun,
    evaluation_id: UUID,
    baseline_run_id: UUID | None,
    queries: list[Any],
    created_at: datetime,
    search_documents_fn: Callable[..., list[Any]],
    evaluate_retrieval_case_fn: Callable[..., dict[str, Any]],
) -> EvaluationBatchResult:
    batch = EvaluationBatchResult()
    for case in queries:
        filters_payload = dict(case.filters)
        if case.include_document_filter:
            filters_payload["document_id"] = str(document.id)
        candidate_run_id = run.id if case.include_document_filter else None
        baseline_search_run_id = baseline_run_id if case.include_document_filter else None
        filters = SearchFilters.model_validate(filters_payload)
        request = SearchRequest(
            query=case.query,
            mode=case.mode,
            filters=filters,
            limit=max(case.expected_top_n, 10),
        )
        candidate_results = search_documents_fn(
            session,
            request,
            run_id=candidate_run_id,
            origin="evaluation_candidate",
            evaluation_id=evaluation_id,
        )
        baseline_results = (
            search_documents_fn(
                session,
                request,
                run_id=baseline_search_run_id,
                origin="evaluation_baseline",
                evaluation_id=evaluation_id,
            )
            if baseline_search_run_id
            else []
        )
        outcome = evaluate_retrieval_case_fn(
            case=case,
            filters_payload=filters.model_dump(mode="json", exclude_none=True),
            candidate_results=candidate_results,
            baseline_results=baseline_results,
        )
        batch.record_retrieval_outcome(outcome)
        _persist_evaluation_query_row(
            session,
            evaluation_id=evaluation_id,
            outcome=outcome,
            created_at=created_at,
        )
    return batch


def execute_answer_queries(
    session,
    *,
    document: Document,
    run: DocumentRun,
    evaluation_id: UUID,
    baseline_run_id: UUID | None,
    queries: list[Any],
    created_at: datetime,
    evaluate_answer_case_fn: Callable[..., dict[str, Any]],
) -> EvaluationBatchResult:
    batch = EvaluationBatchResult()
    for case in queries:
        outcome = evaluate_answer_case_fn(
            session,
            document=document,
            run_id=run.id,
            baseline_run_id=baseline_run_id,
            evaluation_id=evaluation_id,
            case=case,
        )
        batch.record_answer_outcome(outcome)
        _persist_evaluation_query_row(
            session,
            evaluation_id=evaluation_id,
            outcome=outcome,
            created_at=created_at,
        )
    return batch


def build_completed_evaluation_summary(
    *,
    fixture_name: str,
    batch: EvaluationBatchResult,
    structural_summary: dict[str, Any],
    retrieval_rank_metrics: dict[str, Any],
    baseline_run_id: UUID | None,
) -> dict[str, Any]:
    return {
        "status": "completed",
        "fixture_name": fixture_name,
        "query_count": batch.query_count,
        "retrieval_query_count": batch.retrieval_query_count,
        "answer_query_count": batch.answer_query_count,
        "passed_queries": batch.passed_queries,
        "failed_queries": batch.failed_queries,
        "passed_retrieval_queries": batch.passed_retrieval_queries,
        "failed_retrieval_queries": batch.failed_retrieval_queries,
        "passed_answer_queries": batch.passed_answer_queries,
        "failed_answer_queries": batch.failed_answer_queries,
        "regressed_queries": batch.regressed_queries,
        "improved_queries": batch.improved_queries,
        "stable_queries": batch.stable_queries,
        "retrieval_rank_metrics": retrieval_rank_metrics,
        "structural_check_count": structural_summary["check_count"],
        "passed_structural_checks": structural_summary["passed_checks"],
        "failed_structural_checks": structural_summary["failed_checks"],
        "structural_passed": structural_summary["passed"],
        "structural_checks": structural_summary["checks"],
        "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
    }
