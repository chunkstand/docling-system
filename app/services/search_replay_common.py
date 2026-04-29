from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import SearchFeedback, SearchReplayQuery, SearchReplayRun, SearchRequestRecord
from app.schemas.search import (
    SearchReplayQueryResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunSummaryResponse,
)

RANKING_DATASET_SCHEMA_VERSION = 2
CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE = "cross_document_prose_regressions"
EVALUATION_QUERY_SOURCE_TYPE = "evaluation_queries"
TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE = "technical_report_claim_feedback"
REPLAY_CASE_PAGE_MIN_LIMIT = 50


@dataclass
class ReplayCase:
    query_text: str
    mode: str
    filters: dict
    limit: int
    expected_result_type: str | None = None
    expected_top_n: int | None = None
    source_search_request_id: UUID | None = None
    feedback_id: UUID | None = None
    evaluation_query_id: UUID | None = None
    feedback_type: str | None = None
    target_result_type: str | None = None
    target_result_id: UUID | None = None
    expected_source_filename: str | None = None
    expected_top_result_source_filename: str | None = None
    minimum_top_n_hits_from_expected_document: int | None = None
    maximum_foreign_results_before_first_expected_hit: int | None = None
    source_reason: str | None = None
    source_metadata: dict | None = None


def _replay_run_not_found(replay_run_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "search_replay_run_not_found",
        f"Search replay run not found: {replay_run_id}",
        replay_run_id=str(replay_run_id),
    )


def _filters_key(filters: dict) -> str:
    return json.dumps(filters or {}, sort_keys=True)


def _query_key(query_text: str, mode: str, filters: dict) -> tuple[str, str, str]:
    return query_text, mode, _filters_key(filters)


def _replay_query_comparison_key(
    row: SearchReplayQueryResponse,
) -> tuple[str, str, str] | tuple[str, str]:
    details = row.details or {}
    if details.get("source_reason") == TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE:
        claim_feedback_id = details.get("claim_feedback_id")
        if claim_feedback_id:
            return TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE, str(claim_feedback_id)
    return _query_key(row.query_text, row.mode, row.filters)


def _request_result_key(
    result_type: str | None,
    result_id: UUID | None,
) -> tuple[str | None, UUID | None]:
    return result_type, result_id


def _uuid_str(value: UUID | str | None) -> str | None:
    return str(value) if value is not None else None


def _is_smoke_test_note(note: str | None) -> bool:
    normalized = " ".join((note or "").strip().lower().split())
    return normalized.startswith("smoke test")


def _smoke_test_feedback_request_ids(session: Session) -> set[UUID]:
    feedback_rows = session.execute(select(SearchFeedback)).scalars().all()
    return {
        feedback.search_request_id
        for feedback in feedback_rows
        if _is_smoke_test_note(feedback.note)
    }


def _replay_case_page_limit(limit: int) -> int:
    return max(limit * 4, REPLAY_CASE_PAGE_MIN_LIMIT)


def _is_low_signal_zero_result_gap(row: SearchRequestRecord) -> bool:
    filters = row.filters_json or {}
    if filters or row.tabular_query:
        return False
    token_count = len((row.query_text or "").split())
    return token_count <= 1


def _effective_replay_source_type(row: SearchReplayRun) -> str:
    return (getattr(row, "summary_json", None) or {}).get("source_type") or row.source_type


def _smoke_test_note_expression(note_column):
    return func.lower(
        func.regexp_replace(
            func.btrim(func.coalesce(note_column, literal(""))),
            r"\s+",
            " ",
            "g",
        )
    ).like("smoke test%")


def _to_replay_run_summary(row: SearchReplayRun) -> SearchReplayRunSummaryResponse:
    return SearchReplayRunSummaryResponse(
        replay_run_id=row.id,
        source_type=_effective_replay_source_type(row),
        status=row.status,
        harness_name=row.harness_name,
        reranker_name=row.reranker_name,
        reranker_version=row.reranker_version,
        retrieval_profile_name=row.retrieval_profile_name,
        harness_config=row.harness_config_json or {},
        query_count=row.query_count,
        passed_count=row.passed_count,
        failed_count=row.failed_count,
        zero_result_count=row.zero_result_count,
        table_hit_count=row.table_hit_count,
        top_result_changes=row.top_result_changes,
        max_rank_shift=row.max_rank_shift,
        rank_metrics=(row.summary_json or {}).get("rank_metrics") or {},
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def _to_replay_query_response(row: SearchReplayQuery) -> SearchReplayQueryResponse:
    return SearchReplayQueryResponse(
        replay_query_id=row.id,
        source_search_request_id=row.source_search_request_id,
        replay_search_request_id=row.replay_search_request_id,
        feedback_id=row.feedback_id,
        evaluation_query_id=row.evaluation_query_id,
        query_text=row.query_text,
        mode=row.mode,
        filters=row.filters_json or {},
        expected_result_type=row.expected_result_type,
        expected_top_n=row.expected_top_n,
        passed=row.passed,
        result_count=row.result_count,
        table_hit_count=row.table_hit_count,
        overlap_count=row.overlap_count,
        added_count=row.added_count,
        removed_count=row.removed_count,
        top_result_changed=row.top_result_changed,
        max_rank_shift=row.max_rank_shift,
        details=row.details_json or {},
        created_at=row.created_at,
    )


def _load_replay_run(session: Session, replay_run_id: UUID) -> SearchReplayRun:
    replay_run = session.get(SearchReplayRun, replay_run_id)
    if replay_run is None:
        raise _replay_run_not_found(replay_run_id)
    return replay_run


def list_search_replay_runs(
    session: Session, *, limit: int = 10
) -> list[SearchReplayRunSummaryResponse]:
    rows = (
        session.execute(
            select(SearchReplayRun).order_by(SearchReplayRun.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_replay_run_summary(row) for row in rows]


def get_search_replay_run_detail(
    session: Session, replay_run_id: UUID
) -> SearchReplayRunDetailResponse:
    replay_run = _load_replay_run(session, replay_run_id)
    query_rows = (
        session.execute(
            select(SearchReplayQuery)
            .where(SearchReplayQuery.replay_run_id == replay_run.id)
            .order_by(SearchReplayQuery.created_at.asc(), SearchReplayQuery.query_text.asc())
        )
        .scalars()
        .all()
    )
    summary = _to_replay_run_summary(replay_run)
    return SearchReplayRunDetailResponse(
        **summary.model_dump(),
        summary=replay_run.summary_json or {},
        query_results=[_to_replay_query_response(row) for row in query_rows],
    )
