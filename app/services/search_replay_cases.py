from __future__ import annotations

from sqlalchemy import and_, case, cast, func, literal, select
from sqlalchemy.orm import Session

from app.db.public.document_artifacts import DocumentRunEvaluation, DocumentRunEvaluationQuery
from app.db.public.ingest import Document
from app.db.public.retrieval import SearchFeedback, SearchRequestRecord, SearchRequestResult
from app.schemas.search import SearchReplayRunRequest
from app.services import search_replay_claim_feedback_cases as claim_feedback_cases
from app.services import search_replay_common as replay_common
from app.services.session_utils import uses_in_memory_session

ReplayCase = replay_common.ReplayCase
CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE = (
    replay_common.CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE
)
EVALUATION_QUERY_SOURCE_TYPE = replay_common.EVALUATION_QUERY_SOURCE_TYPE
TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE = (
    replay_common.TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE
)
REPLAY_CASE_PAGE_MIN_LIMIT = replay_common.REPLAY_CASE_PAGE_MIN_LIMIT

_filters_key = replay_common._filters_key
_is_low_signal_zero_result_gap = replay_common._is_low_signal_zero_result_gap
_is_smoke_test_note = replay_common._is_smoke_test_note
_query_key = replay_common._query_key
_replay_case_page_limit = replay_common._replay_case_page_limit
_request_result_key = replay_common._request_result_key
_smoke_test_feedback_request_ids = replay_common._smoke_test_feedback_request_ids
_smoke_test_note_expression = replay_common._smoke_test_note_expression


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
    if request.source_type == TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE:
        return claim_feedback_cases.technical_report_claim_feedback_cases(
            session,
            request.limit,
        )
    return _feedback_cases(session, request.limit)
