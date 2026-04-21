from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import SearchHarnessEvaluation, SearchHarnessEvaluationSource
from app.schemas.search import (
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSourceResponse,
    SearchHarnessEvaluationSummaryResponse,
    SearchHarnessResponse,
    SearchReplayRunRequest,
)
from app.services.search import DEFAULT_SEARCH_HARNESS_NAME, list_search_harnesses
from app.services.search_replays import (
    CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
    compare_search_replay_runs,
    run_search_replay_suite,
)

VALID_SOURCE_TYPES = {
    "evaluation_queries",
    "feedback",
    "live_search_gaps",
    CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
}


def _search_harness_evaluation_not_found(evaluation_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "search_harness_evaluation_not_found",
        "Search harness evaluation not found.",
        evaluation_id=str(evaluation_id),
    )


def _rank_metrics(detail) -> dict:
    return getattr(detail, "rank_metrics", None) or getattr(detail, "summary", {}).get(
        "rank_metrics",
        {},
    )


def _normalize_source_types(source_types: list[str]) -> list[str]:
    normalized: list[str] = []
    for source_type in source_types:
        if source_type not in VALID_SOURCE_TYPES:
            msg = f"Unsupported replay source type: {source_type}"
            raise ValueError(msg)
        if source_type not in normalized:
            normalized.append(source_type)
    return normalized


def _to_source_response(
    row: SearchHarnessEvaluationSource,
) -> SearchHarnessEvaluationSourceResponse:
    return SearchHarnessEvaluationSourceResponse(
        source_type=row.source_type,
        baseline_replay_run_id=row.baseline_replay_run_id,
        candidate_replay_run_id=row.candidate_replay_run_id,
        baseline_status=row.baseline_status,
        candidate_status=row.candidate_status,
        baseline_query_count=row.baseline_query_count,
        candidate_query_count=row.candidate_query_count,
        baseline_passed_count=row.baseline_passed_count,
        candidate_passed_count=row.candidate_passed_count,
        baseline_zero_result_count=row.baseline_zero_result_count,
        candidate_zero_result_count=row.candidate_zero_result_count,
        baseline_table_hit_count=row.baseline_table_hit_count,
        candidate_table_hit_count=row.candidate_table_hit_count,
        baseline_top_result_changes=row.baseline_top_result_changes,
        candidate_top_result_changes=row.candidate_top_result_changes,
        baseline_mrr=row.baseline_mrr,
        candidate_mrr=row.candidate_mrr,
        baseline_foreign_top_result_count=row.baseline_foreign_top_result_count,
        candidate_foreign_top_result_count=row.candidate_foreign_top_result_count,
        acceptance_checks=row.acceptance_checks_json,
        shared_query_count=row.shared_query_count,
        improved_count=row.improved_count,
        regressed_count=row.regressed_count,
        unchanged_count=row.unchanged_count,
    )


def _to_evaluation_summary(row: SearchHarnessEvaluation) -> SearchHarnessEvaluationSummaryResponse:
    return SearchHarnessEvaluationSummaryResponse(
        evaluation_id=row.id,
        status=row.status,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        limit=row.limit,
        source_types=list(row.source_types_json or []),
        total_shared_query_count=row.total_shared_query_count,
        total_improved_count=row.total_improved_count,
        total_regressed_count=row.total_regressed_count,
        total_unchanged_count=row.total_unchanged_count,
        error_message=row.error_message,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def _to_evaluation_response(
    row: SearchHarnessEvaluation,
    sources: list[SearchHarnessEvaluationSourceResponse],
) -> SearchHarnessEvaluationResponse:
    return SearchHarnessEvaluationResponse(
        evaluation_id=row.id,
        status=row.status,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        limit=row.limit,
        source_types=list(row.source_types_json or []),
        harness_overrides=row.harness_overrides_json or {},
        total_shared_query_count=row.total_shared_query_count,
        total_improved_count=row.total_improved_count,
        total_regressed_count=row.total_regressed_count,
        total_unchanged_count=row.total_unchanged_count,
        error_message=row.error_message,
        created_at=row.created_at,
        completed_at=row.completed_at,
        sources=sources,
    )


def list_search_harness_definitions() -> list[SearchHarnessResponse]:
    return [
        SearchHarnessResponse(
            harness_name=harness.name,
            reranker_name=harness.reranker_name,
            reranker_version=harness.reranker_version,
            retrieval_profile_name=harness.retrieval_profile_name,
            harness_config=harness.config_snapshot,
            is_default=harness.name == DEFAULT_SEARCH_HARNESS_NAME,
        )
        for harness in list_search_harnesses()
    ]


def list_search_harness_evaluations(
    session: Session,
    *,
    limit: int = 20,
    candidate_harness_name: str | None = None,
) -> list[SearchHarnessEvaluationSummaryResponse]:
    statement = select(SearchHarnessEvaluation).order_by(SearchHarnessEvaluation.created_at.desc())
    if candidate_harness_name:
        statement = statement.where(
            SearchHarnessEvaluation.candidate_harness_name == candidate_harness_name
        )
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [_to_evaluation_summary(row) for row in rows]


def get_search_harness_evaluation_detail(
    session: Session,
    evaluation_id: UUID,
) -> SearchHarnessEvaluationResponse:
    evaluation = session.get(SearchHarnessEvaluation, evaluation_id)
    if evaluation is None:
        raise _search_harness_evaluation_not_found(evaluation_id)
    source_rows = (
        session.execute(
            select(SearchHarnessEvaluationSource)
            .where(SearchHarnessEvaluationSource.search_harness_evaluation_id == evaluation.id)
            .order_by(SearchHarnessEvaluationSource.source_index.asc())
        )
        .scalars()
        .all()
    )
    return _to_evaluation_response(evaluation, [_to_source_response(row) for row in source_rows])


def evaluate_search_harness(
    session: Session,
    request: SearchHarnessEvaluationRequest,
    *,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchHarnessEvaluationResponse:
    source_types = _normalize_source_types(request.source_types)
    created_at = utcnow()
    evaluation = SearchHarnessEvaluation(
        id=uuid.uuid4(),
        status="failed",
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        limit=request.limit,
        source_types_json=source_types,
        harness_overrides_json=harness_overrides or {},
        summary_json={},
        created_at=created_at,
    )
    session.add(evaluation)
    session.flush()

    source_summaries: list[SearchHarnessEvaluationSourceResponse] = []
    total_shared_query_count = 0
    total_improved_count = 0
    total_regressed_count = 0
    total_unchanged_count = 0
    replay_failed = False

    try:
        for source_index, source_type in enumerate(source_types):
            baseline_request = SearchReplayRunRequest(
                source_type=source_type,
                limit=request.limit,
                harness_name=request.baseline_harness_name,
            )
            candidate_request = SearchReplayRunRequest(
                source_type=source_type,
                limit=request.limit,
                harness_name=request.candidate_harness_name,
            )
            if harness_overrides is None:
                baseline = run_search_replay_suite(session, baseline_request)
                candidate = run_search_replay_suite(session, candidate_request)
            else:
                baseline = run_search_replay_suite(
                    session,
                    baseline_request,
                    harness_overrides=harness_overrides,
                )
                candidate = run_search_replay_suite(
                    session,
                    candidate_request,
                    harness_overrides=harness_overrides,
                )
            replay_failed = replay_failed or baseline.status != "completed"
            replay_failed = replay_failed or candidate.status != "completed"
            comparison = compare_search_replay_runs(
                session,
                baseline.replay_run_id,
                candidate.replay_run_id,
            )
            baseline_rank_metrics = _rank_metrics(baseline)
            candidate_rank_metrics = _rank_metrics(candidate)
            acceptance_checks = {
                "no_regressions": comparison.regressed_count == 0,
                "mrr_not_lower": float(candidate_rank_metrics.get("mrr") or 0.0)
                >= float(baseline_rank_metrics.get("mrr") or 0.0),
                "foreign_top_result_count_not_higher": int(
                    candidate_rank_metrics.get("foreign_top_result_count") or 0
                )
                <= int(baseline_rank_metrics.get("foreign_top_result_count") or 0),
                "zero_result_count_not_higher": candidate.zero_result_count
                <= baseline.zero_result_count,
            }
            source_row = SearchHarnessEvaluationSource(
                id=uuid.uuid4(),
                search_harness_evaluation_id=evaluation.id,
                source_index=source_index,
                source_type=source_type,
                baseline_replay_run_id=baseline.replay_run_id,
                candidate_replay_run_id=candidate.replay_run_id,
                baseline_status=baseline.status,
                candidate_status=candidate.status,
                baseline_query_count=baseline.query_count,
                candidate_query_count=candidate.query_count,
                baseline_passed_count=baseline.passed_count,
                candidate_passed_count=candidate.passed_count,
                baseline_zero_result_count=baseline.zero_result_count,
                candidate_zero_result_count=candidate.zero_result_count,
                baseline_table_hit_count=baseline.table_hit_count,
                candidate_table_hit_count=candidate.table_hit_count,
                baseline_top_result_changes=baseline.top_result_changes,
                candidate_top_result_changes=candidate.top_result_changes,
                baseline_mrr=float(baseline_rank_metrics.get("mrr") or 0.0),
                candidate_mrr=float(candidate_rank_metrics.get("mrr") or 0.0),
                baseline_foreign_top_result_count=int(
                    baseline_rank_metrics.get("foreign_top_result_count") or 0
                ),
                candidate_foreign_top_result_count=int(
                    candidate_rank_metrics.get("foreign_top_result_count") or 0
                ),
                acceptance_checks_json=acceptance_checks,
                shared_query_count=comparison.shared_query_count,
                improved_count=comparison.improved_count,
                regressed_count=comparison.regressed_count,
                unchanged_count=comparison.unchanged_count,
                created_at=utcnow(),
            )
            session.add(source_row)
            source_summaries.append(_to_source_response(source_row))
            total_shared_query_count += comparison.shared_query_count
            total_improved_count += comparison.improved_count
            total_regressed_count += comparison.regressed_count
            total_unchanged_count += comparison.unchanged_count

        evaluation.status = "failed" if replay_failed else "completed"
        evaluation.error_message = (
            "One or more source replay runs failed." if replay_failed else None
        )
        evaluation.total_shared_query_count = total_shared_query_count
        evaluation.total_improved_count = total_improved_count
        evaluation.total_regressed_count = total_regressed_count
        evaluation.total_unchanged_count = total_unchanged_count
        evaluation.completed_at = utcnow()
        evaluation.summary_json = {
            "schema_name": "search_harness_evaluation",
            "schema_version": "1.0",
            "evaluation_id": str(evaluation.id),
            "status": evaluation.status,
            "baseline_harness_name": evaluation.baseline_harness_name,
            "candidate_harness_name": evaluation.candidate_harness_name,
            "source_types": source_types,
            "source_count": len(source_summaries),
            "total_shared_query_count": total_shared_query_count,
            "total_improved_count": total_improved_count,
            "total_regressed_count": total_regressed_count,
            "total_unchanged_count": total_unchanged_count,
            "error_message": evaluation.error_message,
        }
        session.flush()
        return _to_evaluation_response(evaluation, source_summaries)
    except Exception as exc:
        evaluation.status = "failed"
        evaluation.error_message = str(exc)
        evaluation.completed_at = utcnow()
        evaluation.summary_json = {
            "schema_name": "search_harness_evaluation",
            "schema_version": "1.0",
            "evaluation_id": str(evaluation.id),
            "status": "failed",
            "baseline_harness_name": evaluation.baseline_harness_name,
            "candidate_harness_name": evaluation.candidate_harness_name,
            "source_types": source_types,
            "error_message": str(exc),
        }
        session.flush()
        raise
