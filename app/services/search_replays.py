from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, case, cast, func, literal, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.files import source_filename_matches
from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    SearchFeedback,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.schemas.search import (
    SearchReplayComparisonResponse,
    SearchReplayComparisonRowResponse,
    SearchReplayQueryResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
    SearchRequest,
)
from app.services.search import execute_search, get_search_harness
from app.services.search_history import (
    build_search_replay_diff,
    get_search_request_detail,
)
from app.services.session_utils import uses_in_memory_session

RANKING_DATASET_SCHEMA_VERSION = 2
CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE = "cross_document_prose_regressions"
EVALUATION_QUERY_SOURCE_TYPE = "evaluation_queries"
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


def _request_result_key(
    result_type: str | None,
    result_id: UUID | None,
) -> tuple[str | None, UUID | None]:
    return result_type, result_id


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


def _matching_rank(
    results,
    expected_result_type: str | None,
    *,
    expected_source_filename: str | None = None,
) -> int | None:
    if expected_result_type is None:
        return None
    for idx, result in enumerate(results, start=1):
        if result.result_type == expected_result_type and source_filename_matches(
            result.source_filename,
            expected_source_filename,
        ):
            return idx
    return None


def _top_n_source_hit_count(
    results,
    expected_source_filename: str | None,
    top_n: int | None,
) -> int | None:
    if expected_source_filename is None or top_n is None:
        return None
    return sum(
        1
        for result in results[:top_n]
        if source_filename_matches(result.source_filename, expected_source_filename)
    )


def _foreign_results_before_first_expected_hit(
    results,
    expected_result_type: str | None,
    *,
    expected_source_filename: str | None = None,
) -> int | None:
    rank = _matching_rank(
        results,
        expected_result_type,
        expected_source_filename=expected_source_filename,
    )
    if rank is None or expected_source_filename is None:
        return None
    return sum(
        1
        for result in results[: rank - 1]
        if not source_filename_matches(result.source_filename, expected_source_filename)
    )


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


def _empty_replay_rank_metrics() -> dict:
    return {
        "query_count": 0,
        "mrr": 0.0,
        "foreign_top_result_count": 0,
        "source_constrained_query_count": 0,
    }


def _finalize_replay_rank_metrics(metrics: dict) -> dict:
    query_count = int(metrics.get("query_count") or 0)
    reciprocal_rank_sum = float(metrics.pop("reciprocal_rank_sum", 0.0) or 0.0)
    metrics["mrr"] = reciprocal_rank_sum / query_count if query_count else 0.0
    return metrics


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


def _cross_document_prose_replay_case(
    row: DocumentRunEvaluationQuery,
    details: dict,
) -> ReplayCase | None:
    evaluation_kind = details.get("evaluation_kind")
    if evaluation_kind == "retrieval":
        if not any(
            details.get(key) is not None
            for key in (
                "expected_source_filename",
                "expected_top_result_source_filename",
                "minimum_top_n_hits_from_expected_document",
                "maximum_foreign_results_before_first_expected_hit",
            )
        ):
            return None
        return ReplayCase(
            query_text=row.query_text,
            mode=row.mode,
            filters=row.filters_json or {},
            limit=max(row.expected_top_n or 3, 10),
            expected_result_type=row.expected_result_type,
            expected_top_n=row.expected_top_n,
            evaluation_query_id=row.id,
            expected_source_filename=details.get("expected_source_filename"),
            expected_top_result_source_filename=details.get("expected_top_result_source_filename"),
            minimum_top_n_hits_from_expected_document=details.get(
                "minimum_top_n_hits_from_expected_document"
            ),
            maximum_foreign_results_before_first_expected_hit=details.get(
                "maximum_foreign_results_before_first_expected_hit"
            ),
            source_reason="cross_document_prose_regression",
        )
    expected_citation_source_filename = details.get("expected_citation_source_filename")
    if evaluation_kind == "answer" and expected_citation_source_filename:
        return ReplayCase(
            query_text=row.query_text,
            mode=row.mode,
            filters=row.filters_json or {},
            limit=10,
            expected_result_type=details.get("expected_result_type") or "chunk",
            expected_top_n=3,
            evaluation_query_id=row.id,
            expected_source_filename=expected_citation_source_filename,
            expected_top_result_source_filename=expected_citation_source_filename,
            minimum_top_n_hits_from_expected_document=1,
            maximum_foreign_results_before_first_expected_hit=0,
            source_reason="cross_document_prose_regression",
        )
    return None


def _latest_evaluation_queries(
    session: Session,
    limit: int,
    *,
    source_type: str = EVALUATION_QUERY_SOURCE_TYPE,
) -> list[ReplayCase]:
    if uses_in_memory_session(session):
        return _latest_evaluation_queries_in_memory(
            session,
            limit,
            source_type=source_type,
        )

    cases: list[ReplayCase] = []
    offset = 0
    page_limit = _replay_case_page_limit(limit)

    while True:
        query_rows = _latest_evaluation_query_rows_page(
            session,
            limit=page_limit,
            offset=offset,
            source_type=source_type,
        )
        if not query_rows:
            return cases

        for row in query_rows:
            details = row.details_json or {}
            if source_type == CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE:
                replay_case = _cross_document_prose_replay_case(row, details)
                if replay_case is None:
                    continue
                cases.append(replay_case)
            else:
                if details.get("evaluation_kind") == "answer":
                    continue
                cases.append(
                    ReplayCase(
                        query_text=row.query_text,
                        mode=row.mode,
                        filters=row.filters_json or {},
                        limit=max(row.expected_top_n or 3, 10),
                        expected_result_type=row.expected_result_type,
                        expected_top_n=row.expected_top_n,
                        evaluation_query_id=row.id,
                        source_reason="evaluation_query",
                    )
                )
            if len(cases) >= limit:
                return cases

        offset += page_limit


def _latest_evaluation_query_rows_page(
    session: Session,
    *,
    limit: int,
    offset: int,
    source_type: str,
) -> list[DocumentRunEvaluationQuery]:
    evaluation_kind = func.coalesce(
        DocumentRunEvaluationQuery.details_json["evaluation_kind"].astext,
        literal("retrieval"),
    )
    latest_evaluations = select(
        DocumentRunEvaluation.id.label("evaluation_id"),
        DocumentRunEvaluation.run_id.label("run_id"),
        func.row_number()
        .over(
            partition_by=DocumentRunEvaluation.run_id,
            order_by=(
                DocumentRunEvaluation.created_at.desc(),
                DocumentRunEvaluation.id.desc(),
            ),
        )
        .label("row_number"),
    ).subquery()
    statement = (
        select(DocumentRunEvaluationQuery)
        .join(
            latest_evaluations,
            and_(
                latest_evaluations.c.evaluation_id == DocumentRunEvaluationQuery.evaluation_id,
                latest_evaluations.c.row_number == 1,
            ),
        )
        .join(Document, Document.latest_run_id == latest_evaluations.c.run_id)
        .order_by(
            Document.updated_at.desc(),
            DocumentRunEvaluationQuery.query_text.asc(),
            DocumentRunEvaluationQuery.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    if source_type == EVALUATION_QUERY_SOURCE_TYPE:
        statement = statement.where(evaluation_kind != "answer")
    return session.execute(statement).scalars().all()


def _latest_evaluation_queries_in_memory(
    session: Session,
    limit: int,
    *,
    source_type: str = EVALUATION_QUERY_SOURCE_TYPE,
) -> list[ReplayCase]:
    documents = session.execute(select(Document)).scalars().all()
    cases: list[ReplayCase] = []

    for document in sorted(documents, key=lambda item: item.updated_at, reverse=True):
        if document.latest_run_id is None:
            continue
        evaluation = (
            session.execute(
                select(DocumentRunEvaluation)
                .where(DocumentRunEvaluation.run_id == document.latest_run_id)
                .order_by(DocumentRunEvaluation.created_at.desc())
            )
            .scalars()
            .first()
        )
        if evaluation is None:
            continue
        query_rows = (
            session.execute(
                select(DocumentRunEvaluationQuery)
                .where(DocumentRunEvaluationQuery.evaluation_id == evaluation.id)
                .order_by(DocumentRunEvaluationQuery.query_text.asc())
            )
            .scalars()
            .all()
        )
        for row in query_rows:
            details = row.details_json or {}
            if source_type == CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE:
                replay_case = _cross_document_prose_replay_case(row, details)
                if replay_case is None:
                    continue
                cases.append(replay_case)
            else:
                if details.get("evaluation_kind") == "answer":
                    continue
                cases.append(
                    ReplayCase(
                        query_text=row.query_text,
                        mode=row.mode,
                        filters=row.filters_json or {},
                        limit=max(row.expected_top_n or 3, 10),
                        expected_result_type=row.expected_result_type,
                        expected_top_n=row.expected_top_n,
                        evaluation_query_id=row.id,
                        source_reason="evaluation_query",
                    )
                )
            if len(cases) >= limit:
                return cases
    return cases


def _live_search_gap_cases(session: Session, limit: int) -> list[ReplayCase]:
    if uses_in_memory_session(session):
        return _live_search_gap_cases_in_memory(session, limit)

    empty_filters = cast(literal("{}"), SearchRequestRecord.filters_json.type)
    smoke_test_feedback_exists = (
        select(SearchFeedback.id)
        .where(
            SearchFeedback.search_request_id == SearchRequestRecord.id,
            _smoke_test_note_expression(SearchFeedback.note),
        )
        .exists()
    )
    token_count = case(
        (
            func.length(func.btrim(SearchRequestRecord.query_text)) == 0,
            0,
        ),
        else_=func.array_length(
            func.regexp_split_to_array(func.btrim(SearchRequestRecord.query_text), r"\s+"),
            1,
        ),
    )
    live_result_type = SearchRequestRecord.filters_json["result_type"].astext
    source_reason = case(
        (
            SearchRequestRecord.result_count == 0,
            literal("zero_result_gap"),
        ),
        else_=literal("missing_table_gap"),
    )
    ranked_rows = (
        select(
            SearchRequestRecord.id.label("source_search_request_id"),
            SearchRequestRecord.query_text.label("query_text"),
            SearchRequestRecord.mode.label("mode"),
            SearchRequestRecord.filters_json.label("filters_json"),
            SearchRequestRecord.limit.label("limit"),
            source_reason.label("source_reason"),
            SearchRequestRecord.created_at.label("created_at"),
            func.row_number()
            .over(
                partition_by=(
                    SearchRequestRecord.query_text,
                    SearchRequestRecord.mode,
                    SearchRequestRecord.filters_json,
                ),
                order_by=(
                    SearchRequestRecord.created_at.desc(),
                    SearchRequestRecord.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(
            SearchRequestRecord.origin.in_(("api", "chat")),
            ~smoke_test_feedback_exists,
            ~and_(
                SearchRequestRecord.result_count == 0,
                SearchRequestRecord.filters_json == empty_filters,
                SearchRequestRecord.tabular_query.is_(False),
                token_count <= 1,
            ),
            case(
                (
                    SearchRequestRecord.result_count == 0,
                    literal(True),
                ),
                else_=and_(
                    SearchRequestRecord.tabular_query.is_(True),
                    func.coalesce(live_result_type, literal("")) != "chunk",
                    SearchRequestRecord.table_hit_count == 0,
                ),
            ),
        )
        .subquery()
    )
    rows = session.execute(
        select(ranked_rows)
        .where(ranked_rows.c.row_number == 1)
        .order_by(ranked_rows.c.created_at.desc())
        .limit(limit)
    ).all()
    cases: list[ReplayCase] = []
    for row in rows:
        cases.append(
            ReplayCase(
                query_text=row.query_text,
                mode=row.mode,
                filters=row.filters_json or {},
                limit=row.limit,
                source_search_request_id=row.source_search_request_id,
                source_reason=row.source_reason,
            )
        )
    return cases


def _live_search_gap_cases_in_memory(session: Session, limit: int) -> list[ReplayCase]:
    rows = (
        session.execute(
            select(SearchRequestRecord)
            .where(SearchRequestRecord.origin.in_(("api", "chat")))
            .order_by(SearchRequestRecord.created_at.desc())
        )
        .scalars()
        .all()
    )
    smoke_test_request_ids = _smoke_test_feedback_request_ids(session)
    cases: list[ReplayCase] = []
    seen: set[tuple[str, str, str]] = set()

    for row in rows:
        filters = row.filters_json or {}
        request_key = _query_key(row.query_text, row.mode, filters)
        if request_key in seen:
            continue

        reason = None
        if row.result_count == 0:
            reason = "zero_result_gap"
        elif (
            row.tabular_query and filters.get("result_type") != "chunk" and row.table_hit_count == 0
        ):
            reason = "missing_table_gap"

        if reason is None:
            continue
        if row.id in smoke_test_request_ids:
            continue
        if reason == "zero_result_gap" and _is_low_signal_zero_result_gap(row):
            continue

        seen.add(request_key)
        cases.append(
            ReplayCase(
                query_text=row.query_text,
                mode=row.mode,
                filters=filters,
                limit=row.limit,
                source_search_request_id=row.id,
                source_reason=reason,
            )
        )
        if len(cases) >= limit:
            break
    return cases


def _feedback_cases(session: Session, limit: int) -> list[ReplayCase]:
    if uses_in_memory_session(session):
        return _feedback_cases_in_memory(session, limit)

    feedback_rows = session.execute(
        select(SearchFeedback, SearchRequestRecord, SearchRequestResult)
        .join(SearchRequestRecord, SearchRequestRecord.id == SearchFeedback.search_request_id)
        .outerjoin(
            SearchRequestResult,
            SearchRequestResult.id == SearchFeedback.search_request_result_id,
        )
        .where(~_smoke_test_note_expression(SearchFeedback.note))
        .order_by(SearchFeedback.created_at.desc())
        .limit(limit)
    ).all()
    cases: list[ReplayCase] = []

    for feedback, request_row, result_row in feedback_rows:
        if _is_smoke_test_note(feedback.note):
            continue

        target_result_type = None
        target_result_id = None
        if result_row is not None:
            target_result_type = result_row.result_type
            target_result_id = result_row.table_id or result_row.chunk_id

        cases.append(
            ReplayCase(
                query_text=request_row.query_text,
                mode=request_row.mode,
                filters=request_row.filters_json or {},
                limit=request_row.limit,
                source_search_request_id=request_row.id,
                feedback_id=feedback.id,
                feedback_type=feedback.feedback_type,
                target_result_type=target_result_type,
                target_result_id=target_result_id,
                source_reason="feedback_label",
            )
        )
        if len(cases) >= limit:
            break
    return cases


def _feedback_cases_in_memory(session: Session, limit: int) -> list[ReplayCase]:
    feedback_rows = (
        session.execute(select(SearchFeedback).order_by(SearchFeedback.created_at.desc()))
        .scalars()
        .all()
    )
    cases: list[ReplayCase] = []

    for feedback in feedback_rows:
        if _is_smoke_test_note(feedback.note):
            continue
        request_row = session.get(SearchRequestRecord, feedback.search_request_id)
        if request_row is None:
            continue

        target_result_type = None
        target_result_id = None
        if feedback.search_request_result_id is not None:
            result_row = session.get(SearchRequestResult, feedback.search_request_result_id)
            if result_row is not None:
                target_result_type = result_row.result_type
                target_result_id = result_row.table_id or result_row.chunk_id

        cases.append(
            ReplayCase(
                query_text=request_row.query_text,
                mode=request_row.mode,
                filters=request_row.filters_json or {},
                limit=request_row.limit,
                source_search_request_id=request_row.id,
                feedback_id=feedback.id,
                feedback_type=feedback.feedback_type,
                target_result_type=target_result_type,
                target_result_id=target_result_id,
                source_reason="feedback_label",
            )
        )
        if len(cases) >= limit:
            break
    return cases


def _build_replay_cases(session: Session, request: SearchReplayRunRequest) -> list[ReplayCase]:
    if request.source_type in {
        EVALUATION_QUERY_SOURCE_TYPE,
        CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
    }:
        return _latest_evaluation_queries(
            session,
            request.limit,
            source_type=request.source_type,
        )
    if request.source_type == "live_search_gaps":
        return _live_search_gap_cases(session, request.limit)
    return _feedback_cases(session, request.limit)


def _evaluate_case_passed(case: ReplayCase, execution) -> tuple[bool, dict]:
    if case.evaluation_query_id is not None:
        matching_rank = _matching_rank(
            execution.results,
            case.expected_result_type,
            expected_source_filename=case.expected_source_filename,
        )
        top_result_source_filename = (
            execution.results[0].source_filename if execution.results else None
        )
        expected_source_hit_count = _top_n_source_hit_count(
            execution.results,
            case.expected_source_filename,
            case.expected_top_n,
        )
        foreign_results_before_first_expected_hit = _foreign_results_before_first_expected_hit(
            execution.results,
            case.expected_result_type,
            expected_source_filename=case.expected_source_filename,
        )
        passed = matching_rank is not None and matching_rank <= (case.expected_top_n or 0)
        if case.expected_top_result_source_filename is not None:
            passed = passed and source_filename_matches(
                top_result_source_filename,
                case.expected_top_result_source_filename,
            )
        if case.minimum_top_n_hits_from_expected_document is not None:
            passed = passed and (
                (expected_source_hit_count or 0) >= case.minimum_top_n_hits_from_expected_document
            )
        if case.maximum_foreign_results_before_first_expected_hit is not None:
            passed = passed and (
                foreign_results_before_first_expected_hit is not None
                and foreign_results_before_first_expected_hit
                <= case.maximum_foreign_results_before_first_expected_hit
            )
        return passed, {
            "matching_rank": matching_rank,
            "expected_source_filename": case.expected_source_filename,
            "expected_top_result_source_filename": case.expected_top_result_source_filename,
            "minimum_top_n_hits_from_expected_document": (
                case.minimum_top_n_hits_from_expected_document
            ),
            "maximum_foreign_results_before_first_expected_hit": (
                case.maximum_foreign_results_before_first_expected_hit
            ),
            "top_result_source_filename": top_result_source_filename,
            "expected_source_hit_count": expected_source_hit_count,
            "foreign_results_before_first_expected_hit": (
                foreign_results_before_first_expected_hit
            ),
        }

    if case.feedback_type is not None:
        replay_keys = {
            _request_result_key(
                result.result_type,
                result.table_id if result.result_type == "table" else result.chunk_id,
            )
            for result in execution.results
        }
        target_key = _request_result_key(case.target_result_type, case.target_result_id)
        if case.feedback_type == "relevant":
            return target_key in replay_keys, {
                "target_key": [str(target_key[0]), str(target_key[1])]
            }
        if case.feedback_type == "irrelevant":
            return target_key not in replay_keys, {
                "target_key": [str(target_key[0]), str(target_key[1])]
            }
        if case.feedback_type == "missing_table":
            return execution.table_hit_count > 0, {"table_hit_count": execution.table_hit_count}
        if case.feedback_type == "missing_chunk":
            chunk_hit_count = sum(
                1 for result in execution.results if result.result_type == "chunk"
            )
            return any(result.result_type == "chunk" for result in execution.results), {
                "chunk_hit_count": chunk_hit_count
            }
        if case.feedback_type == "no_answer":
            return len(execution.results) == 0, {"result_count": len(execution.results)}

    if case.source_reason == "zero_result_gap":
        return len(execution.results) > 0, {"result_count": len(execution.results)}
    if case.source_reason == "missing_table_gap":
        return execution.table_hit_count > 0, {"table_hit_count": execution.table_hit_count}
    return False, {}


def run_search_replay_suite(
    session: Session,
    request: SearchReplayRunRequest,
    *,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchReplayRunDetailResponse:
    harness = get_search_harness(request.harness_name, harness_overrides)
    replay_run = SearchReplayRun(
        id=uuid.uuid4(),
        source_type=request.source_type,
        status="failed",
        harness_name=harness.name,
        created_at=utcnow(),
        summary_json={},
    )
    session.add(replay_run)
    session.flush()

    try:
        cases = _build_replay_cases(session, request)
        created_at = utcnow()
        summary_counter: Counter[str] = Counter()
        rank_metrics = _empty_replay_rank_metrics()
        last_execution = None

        for case in cases:
            filters = SearchRequest.model_validate(
                {
                    "query": case.query_text,
                    "mode": case.mode,
                    "filters": case.filters,
                    "limit": case.limit,
                    "harness_name": request.harness_name,
                }
            )
            execution = execute_search(
                session,
                filters,
                origin="replay_suite",
                parent_request_id=case.source_search_request_id,
                harness_overrides=harness_overrides,
            )
            last_execution = execution
            replay_detail = (
                get_search_request_detail(session, execution.request_id)
                if execution.request_id is not None
                else None
            )
            diff = None
            if case.source_search_request_id is not None and replay_detail is not None:
                original_detail = get_search_request_detail(session, case.source_search_request_id)
                diff = build_search_replay_diff(original_detail, replay_detail)

            passed, pass_details = _evaluate_case_passed(case, execution)
            summary_counter["query_count"] += 1
            summary_counter["passed_count"] += int(passed)
            summary_counter["failed_count"] += int(not passed)
            summary_counter["zero_result_count"] += int(len(execution.results) == 0)
            summary_counter["table_hit_count"] += int(execution.table_hit_count > 0)
            summary_counter["top_result_changes"] += int(bool(diff and diff.top_result_changed))
            summary_counter["max_rank_shift"] = max(
                summary_counter["max_rank_shift"],
                diff.max_rank_shift if diff else 0,
            )
            if case.evaluation_query_id is not None:
                rank_metrics["query_count"] += 1
                matching_rank = pass_details.get("matching_rank")
                if matching_rank:
                    rank_metrics["reciprocal_rank_sum"] = float(
                        rank_metrics.get("reciprocal_rank_sum") or 0.0
                    ) + (1.0 / matching_rank)
                if any(
                    (
                        case.expected_source_filename,
                        case.expected_top_result_source_filename,
                        case.minimum_top_n_hits_from_expected_document,
                        case.maximum_foreign_results_before_first_expected_hit,
                    )
                ):
                    rank_metrics["source_constrained_query_count"] += 1
                if case.expected_top_result_source_filename is not None:
                    rank_metrics["foreign_top_result_count"] += int(
                        not source_filename_matches(
                            pass_details.get("top_result_source_filename"),
                            case.expected_top_result_source_filename,
                        )
                    )

            session.add(
                SearchReplayQuery(
                    id=uuid.uuid4(),
                    replay_run_id=replay_run.id,
                    source_search_request_id=case.source_search_request_id,
                    replay_search_request_id=execution.request_id,
                    feedback_id=case.feedback_id,
                    evaluation_query_id=case.evaluation_query_id,
                    query_text=case.query_text,
                    mode=case.mode,
                    filters_json=case.filters,
                    expected_result_type=case.expected_result_type,
                    expected_top_n=case.expected_top_n,
                    passed=passed,
                    result_count=len(execution.results),
                    table_hit_count=execution.table_hit_count,
                    overlap_count=diff.overlap_count if diff else 0,
                    added_count=diff.added_count if diff else 0,
                    removed_count=diff.removed_count if diff else 0,
                    top_result_changed=diff.top_result_changed if diff else False,
                    max_rank_shift=diff.max_rank_shift if diff else 0,
                    details_json={
                        "source_reason": case.source_reason,
                        "feedback_type": case.feedback_type,
                        "embedding_status": execution.embedding_status,
                        "harness_name": execution.harness_name,
                        "reranker_name": execution.reranker_name,
                        "reranker_version": execution.reranker_version,
                        "retrieval_profile_name": execution.retrieval_profile_name,
                        **pass_details,
                    },
                    created_at=created_at,
                )
            )

        replay_run.status = "completed"
        replay_run.harness_name = harness.name
        if last_execution is not None:
            replay_run.reranker_name = last_execution.reranker_name
            replay_run.reranker_version = last_execution.reranker_version
            replay_run.retrieval_profile_name = last_execution.retrieval_profile_name
            replay_run.harness_config_json = last_execution.harness_config
        else:
            replay_run.reranker_name = harness.reranker_name
            replay_run.reranker_version = harness.reranker_version
            replay_run.retrieval_profile_name = harness.retrieval_profile_name
            replay_run.harness_config_json = harness.config_snapshot
        replay_run.query_count = summary_counter["query_count"]
        replay_run.passed_count = summary_counter["passed_count"]
        replay_run.failed_count = summary_counter["failed_count"]
        replay_run.zero_result_count = summary_counter["zero_result_count"]
        replay_run.table_hit_count = summary_counter["table_hit_count"]
        replay_run.top_result_changes = summary_counter["top_result_changes"]
        replay_run.max_rank_shift = summary_counter["max_rank_shift"]
        replay_run.summary_json = {
            "source_type": request.source_type,
            "source_limit": request.limit,
            "harness_name": replay_run.harness_name,
            "reranker_name": replay_run.reranker_name,
            "reranker_version": replay_run.reranker_version,
            "retrieval_profile_name": replay_run.retrieval_profile_name,
            "query_count": replay_run.query_count,
            "passed_count": replay_run.passed_count,
            "failed_count": replay_run.failed_count,
            "zero_result_count": replay_run.zero_result_count,
            "table_hit_count": replay_run.table_hit_count,
            "top_result_changes": replay_run.top_result_changes,
            "max_rank_shift": replay_run.max_rank_shift,
            "rank_metrics": _finalize_replay_rank_metrics(rank_metrics),
        }
        replay_run.completed_at = utcnow()
        session.flush()
        return get_search_replay_run_detail(session, replay_run.id)
    except Exception as exc:
        replay_run.status = "failed"
        replay_run.error_message = str(exc)
        replay_run.summary_json = {
            "source_type": request.source_type,
            "source_limit": request.limit,
            "harness_name": request.harness_name or "default_v1",
            "error": str(exc),
        }
        replay_run.completed_at = utcnow()
        session.flush()
        return get_search_replay_run_detail(session, replay_run.id)


def compare_search_replay_runs(
    session: Session,
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
) -> SearchReplayComparisonResponse:
    baseline = get_search_replay_run_detail(session, baseline_replay_run_id)
    candidate = get_search_replay_run_detail(session, candidate_replay_run_id)

    baseline_rows = {
        _query_key(row.query_text, row.mode, row.filters): row for row in baseline.query_results
    }
    candidate_rows = {
        _query_key(row.query_text, row.mode, row.filters): row for row in candidate.query_results
    }
    shared_keys = baseline_rows.keys() & candidate_rows.keys()

    improved_count = 0
    regressed_count = 0
    unchanged_count = 0
    changed_queries: list[SearchReplayComparisonRowResponse] = []

    for key in sorted(shared_keys):
        baseline_row = baseline_rows[key]
        candidate_row = candidate_rows[key]
        if not baseline_row.passed and candidate_row.passed:
            improved_count += 1
        elif baseline_row.passed and not candidate_row.passed:
            regressed_count += 1
        else:
            unchanged_count += 1

        if (
            baseline_row.passed != candidate_row.passed
            or baseline_row.result_count != candidate_row.result_count
            or baseline_row.top_result_changed != candidate_row.top_result_changed
        ):
            changed_queries.append(
                SearchReplayComparisonRowResponse(
                    query_text=baseline_row.query_text,
                    mode=baseline_row.mode,
                    filters=baseline_row.filters,
                    baseline_passed=baseline_row.passed,
                    candidate_passed=candidate_row.passed,
                    baseline_result_count=baseline_row.result_count,
                    candidate_result_count=candidate_row.result_count,
                    baseline_top_result_changed=baseline_row.top_result_changed,
                    candidate_top_result_changed=candidate_row.top_result_changed,
                )
            )

    return SearchReplayComparisonResponse(
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
        shared_query_count=len(shared_keys),
        improved_count=improved_count,
        regressed_count=regressed_count,
        unchanged_count=unchanged_count,
        baseline_zero_result_count=baseline.zero_result_count,
        candidate_zero_result_count=candidate.zero_result_count,
        changed_queries=changed_queries[:20],
    )


def export_ranking_dataset(session: Session, *, limit: int = 200) -> list[dict]:
    feedback_rows = (
        session.execute(
            select(SearchFeedback).order_by(SearchFeedback.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    replay_rows = (
        session.execute(
            select(SearchReplayQuery).order_by(SearchReplayQuery.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )

    dataset: list[dict] = []

    def metadata_era(harness_config: dict | None) -> str:
        return "harness_v1" if harness_config else "legacy_pre_harness"

    if uses_in_memory_session(session):
        request_rows_by_id = {
            feedback.search_request_id: session.get(SearchRequestRecord, feedback.search_request_id)
            for feedback in feedback_rows
        }
        result_rows_by_id = {
            feedback.search_request_result_id: session.get(
                SearchRequestResult,
                feedback.search_request_result_id,
            )
            for feedback in feedback_rows
            if feedback.search_request_result_id is not None
        }
        replay_runs_by_id = {
            row.replay_run_id: session.get(SearchReplayRun, row.replay_run_id)
            for row in replay_rows
        }
    else:
        request_ids = {feedback.search_request_id for feedback in feedback_rows}
        result_ids = {
            feedback.search_request_result_id
            for feedback in feedback_rows
            if feedback.search_request_result_id is not None
        }
        replay_run_ids = {row.replay_run_id for row in replay_rows}
        request_rows_by_id = {
            row.id: row
            for row in session.execute(
                select(SearchRequestRecord).where(SearchRequestRecord.id.in_(request_ids))
            )
            .scalars()
            .all()
        }
        result_rows_by_id = {
            row.id: row
            for row in session.execute(
                select(SearchRequestResult).where(SearchRequestResult.id.in_(result_ids))
            )
            .scalars()
            .all()
        }
        replay_runs_by_id = {
            row.id: row
            for row in session.execute(
                select(SearchReplayRun).where(SearchReplayRun.id.in_(replay_run_ids))
            )
            .scalars()
            .all()
        }

    for feedback in feedback_rows:
        request_row = request_rows_by_id.get(feedback.search_request_id)
        result_row = result_rows_by_id.get(feedback.search_request_result_id)
        if request_row is None:
            continue
        harness_config = getattr(request_row, "harness_config_json", {}) or {}
        dataset.append(
            {
                "dataset_type": "feedback",
                "row_schema_version": RANKING_DATASET_SCHEMA_VERSION,
                "metadata_era": metadata_era(harness_config),
                "feedback_id": str(feedback.id),
                "feedback_type": feedback.feedback_type,
                "search_request_id": str(request_row.id),
                "harness_name": request_row.harness_name,
                "reranker_name": request_row.reranker_name,
                "reranker_version": request_row.reranker_version,
                "retrieval_profile_name": request_row.retrieval_profile_name,
                "harness_config": harness_config,
                "query_text": request_row.query_text,
                "mode": request_row.mode,
                "filters": request_row.filters_json or {},
                "note": feedback.note,
                "created_at": feedback.created_at.isoformat(),
                "result_rank": feedback.result_rank,
                "result_type": getattr(result_row, "result_type", None),
                "result_id": str(
                    getattr(result_row, "table_id", None) or getattr(result_row, "chunk_id", None)
                )
                if result_row is not None
                else None,
                "rerank_features": (
                    getattr(result_row, "rerank_features_json", {}) if result_row else {}
                ),
            }
        )

    for row in replay_rows:
        replay_run = replay_runs_by_id.get(row.replay_run_id)
        harness_config = getattr(replay_run, "harness_config_json", {}) or {}
        dataset.append(
            {
                "dataset_type": "replay",
                "row_schema_version": RANKING_DATASET_SCHEMA_VERSION,
                "metadata_era": metadata_era(harness_config),
                "replay_query_id": str(row.id),
                "replay_run_id": str(row.replay_run_id),
                "source_type": (
                    _effective_replay_source_type(replay_run) if replay_run is not None else None
                ),
                "harness_name": getattr(replay_run, "harness_name", None),
                "reranker_name": getattr(replay_run, "reranker_name", None),
                "reranker_version": getattr(replay_run, "reranker_version", None),
                "retrieval_profile_name": getattr(replay_run, "retrieval_profile_name", None),
                "harness_config": harness_config,
                "query_text": row.query_text,
                "mode": row.mode,
                "filters": row.filters_json or {},
                "expected_result_type": row.expected_result_type,
                "expected_top_n": row.expected_top_n,
                "passed": row.passed,
                "result_count": row.result_count,
                "table_hit_count": row.table_hit_count,
                "overlap_count": row.overlap_count,
                "added_count": row.added_count,
                "removed_count": row.removed_count,
                "top_result_changed": row.top_result_changed,
                "max_rank_shift": row.max_rank_shift,
                "details": row.details_json or {},
                "created_at": row.created_at.isoformat(),
            }
        )

    return dataset
