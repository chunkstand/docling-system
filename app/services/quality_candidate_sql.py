from __future__ import annotations

from sqlalchemy import String, and_, case, cast, func, literal, null, or_, select, union_all
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _maybe_uuid
from app.db.public.document_artifacts import DocumentRunEvaluation, DocumentRunEvaluationQuery
from app.db.public.ingest import Document, DocumentRun
from app.db.public.retrieval import ChatAnswerFeedback, ChatAnswerRecord, SearchRequestRecord
from app.schemas.quality import QualityEvaluationCandidateResponse
from app.services import quality_candidate_core as _quality_candidate_core
from app.services import quality_candidate_memory as _quality_candidate_memory
from app.services.session_utils import uses_in_memory_session


def _normalized_answer_filters_sql():
    empty_filters = cast(literal("{}"), SearchRequestRecord.filters_json.type)
    fallback_filters = case(
        (
            ChatAnswerRecord.document_id.is_not(None),
            func.jsonb_build_object("document_id", cast(ChatAnswerRecord.document_id, String)),
        ),
        else_=empty_filters,
    )
    request_filters = case(
        (
            and_(
                SearchRequestRecord.id.is_not(None),
                SearchRequestRecord.filters_json != empty_filters,
            ),
            SearchRequestRecord.filters_json,
        ),
        else_=fallback_filters,
    )
    return case(
        (
            request_filters.op("->>")("result_type") == "chunk",
            request_filters.op("-")("result_type"),
        ),
        else_=request_filters,
    )


def _quality_candidate_rows_page(session: Session, *, limit: int, offset: int):
    null_uuid = cast(null(), Document.id.type)
    null_text = cast(null(), Document.source_filename.type)
    null_search_request_id = cast(null(), SearchRequestRecord.id.type)
    null_chat_answer_id = cast(null(), ChatAnswerRecord.id.type)
    evaluation_kind = func.coalesce(
        DocumentRunEvaluationQuery.details_json["evaluation_kind"].astext,
        literal("retrieval"),
    )

    evaluation_partition = (
        DocumentRunEvaluationQuery.query_text,
        DocumentRunEvaluationQuery.mode,
        DocumentRunEvaluationQuery.filters_json,
        DocumentRunEvaluationQuery.expected_result_type,
        evaluation_kind,
    )
    evaluation_ranked = (
        select(
            literal("evaluation_failure").label("candidate_type"),
            case(
                (
                    evaluation_kind == "answer",
                    literal("failed_answer_evaluation"),
                ),
                else_=literal("failed_evaluation_query"),
            ).label("reason_code"),
            DocumentRunEvaluationQuery.query_text.label("query_text"),
            DocumentRunEvaluationQuery.mode.label("mode"),
            DocumentRunEvaluationQuery.filters_json.label("filters_json"),
            evaluation_kind.label("evaluation_kind"),
            DocumentRunEvaluationQuery.expected_result_type.label("expected_result_type"),
            DocumentRunEvaluation.fixture_name.label("fixture_name"),
            DocumentRunEvaluationQuery.created_at.label("latest_seen_at"),
            Document.id.label("document_id"),
            Document.source_filename.label("source_filename"),
            DocumentRunEvaluation.id.label("evaluation_id"),
            null_search_request_id.label("search_request_id"),
            null_chat_answer_id.label("chat_answer_id"),
            null_text.label("harness_name"),
            func.count().over(partition_by=evaluation_partition).label("occurrence_count"),
            func.row_number()
            .over(
                partition_by=evaluation_partition,
                order_by=(
                    DocumentRunEvaluationQuery.created_at.desc(),
                    DocumentRunEvaluationQuery.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .join(
            DocumentRunEvaluation,
            DocumentRunEvaluation.id == DocumentRunEvaluationQuery.evaluation_id,
        )
        .join(DocumentRun, DocumentRun.id == DocumentRunEvaluation.run_id)
        .join(Document, Document.id == DocumentRun.document_id)
        .where(DocumentRunEvaluationQuery.passed.is_(False))
        .subquery()
    )
    evaluation_candidates = select(
        evaluation_ranked.c.candidate_type,
        evaluation_ranked.c.reason_code,
        evaluation_ranked.c.query_text,
        evaluation_ranked.c.mode,
        evaluation_ranked.c.filters_json,
        evaluation_ranked.c.evaluation_kind,
        evaluation_ranked.c.expected_result_type,
        evaluation_ranked.c.fixture_name,
        evaluation_ranked.c.latest_seen_at,
        evaluation_ranked.c.document_id,
        evaluation_ranked.c.source_filename,
        evaluation_ranked.c.evaluation_id,
        evaluation_ranked.c.search_request_id,
        evaluation_ranked.c.chat_answer_id,
        evaluation_ranked.c.harness_name,
        evaluation_ranked.c.occurrence_count,
    ).where(evaluation_ranked.c.row_number == 1)

    live_result_type = SearchRequestRecord.filters_json["result_type"].astext
    live_expected_result_type = case(
        (
            and_(
                SearchRequestRecord.tabular_query.is_(True),
                func.coalesce(live_result_type, literal("")) != "chunk",
                SearchRequestRecord.table_hit_count == 0,
            ),
            literal("table"),
        ),
        else_=cast(null(), SearchRequestRecord.mode.type),
    )
    live_reason_code = case(
        (
            SearchRequestRecord.result_count == 0,
            literal("live_search_no_results"),
        ),
        else_=literal("live_search_no_table_hits"),
    )
    live_partition = (
        SearchRequestRecord.query_text,
        SearchRequestRecord.mode,
        SearchRequestRecord.filters_json,
        live_expected_result_type,
    )
    live_ranked = (
        select(
            literal("live_search_gap").label("candidate_type"),
            live_reason_code.label("reason_code"),
            SearchRequestRecord.query_text.label("query_text"),
            SearchRequestRecord.mode.label("mode"),
            SearchRequestRecord.filters_json.label("filters_json"),
            literal("retrieval").label("evaluation_kind"),
            live_expected_result_type.label("expected_result_type"),
            null_text.label("fixture_name"),
            SearchRequestRecord.created_at.label("latest_seen_at"),
            null_uuid.label("document_id"),
            null_text.label("source_filename"),
            SearchRequestRecord.evaluation_id.label("evaluation_id"),
            SearchRequestRecord.id.label("search_request_id"),
            null_chat_answer_id.label("chat_answer_id"),
            SearchRequestRecord.harness_name.label("harness_name"),
            func.count().over(partition_by=live_partition).label("occurrence_count"),
            func.row_number()
            .over(
                partition_by=live_partition,
                order_by=(SearchRequestRecord.created_at.desc(), SearchRequestRecord.id.desc()),
            )
            .label("row_number"),
        )
        .where(
            SearchRequestRecord.origin.in_(("api", "chat")),
            or_(
                SearchRequestRecord.result_count == 0,
                and_(
                    SearchRequestRecord.tabular_query.is_(True),
                    func.coalesce(live_result_type, literal("")) != "chunk",
                    SearchRequestRecord.table_hit_count == 0,
                ),
            ),
        )
        .subquery()
    )
    live_candidates = select(
        live_ranked.c.candidate_type,
        live_ranked.c.reason_code,
        live_ranked.c.query_text,
        live_ranked.c.mode,
        live_ranked.c.filters_json,
        live_ranked.c.evaluation_kind,
        live_ranked.c.expected_result_type,
        live_ranked.c.fixture_name,
        live_ranked.c.latest_seen_at,
        live_ranked.c.document_id,
        live_ranked.c.source_filename,
        live_ranked.c.evaluation_id,
        live_ranked.c.search_request_id,
        live_ranked.c.chat_answer_id,
        live_ranked.c.harness_name,
        live_ranked.c.occurrence_count,
    ).where(live_ranked.c.row_number == 1)

    answer_filters = _normalized_answer_filters_sql()
    answer_partition = (
        ChatAnswerRecord.question_text,
        ChatAnswerRecord.mode,
        answer_filters,
        ChatAnswerFeedback.feedback_type,
    )
    answer_ranked = (
        select(
            literal("answer_feedback_gap").label("candidate_type"),
            case(
                (
                    ChatAnswerFeedback.feedback_type == "unsupported",
                    literal("answer_feedback_unsupported"),
                ),
                else_=literal("answer_feedback_incomplete"),
            ).label("reason_code"),
            ChatAnswerRecord.question_text.label("query_text"),
            ChatAnswerRecord.mode.label("mode"),
            answer_filters.label("filters_json"),
            literal("answer").label("evaluation_kind"),
            null_text.label("expected_result_type"),
            null_text.label("fixture_name"),
            ChatAnswerFeedback.created_at.label("latest_seen_at"),
            ChatAnswerRecord.document_id.label("document_id"),
            null_text.label("source_filename"),
            SearchRequestRecord.evaluation_id.label("evaluation_id"),
            ChatAnswerRecord.search_request_id.label("search_request_id"),
            ChatAnswerRecord.id.label("chat_answer_id"),
            ChatAnswerRecord.harness_name.label("harness_name"),
            func.count().over(partition_by=answer_partition).label("occurrence_count"),
            func.row_number()
            .over(
                partition_by=answer_partition,
                order_by=(ChatAnswerFeedback.created_at.desc(), ChatAnswerFeedback.id.desc()),
            )
            .label("row_number"),
        )
        .join(ChatAnswerRecord, ChatAnswerRecord.id == ChatAnswerFeedback.chat_answer_id)
        .outerjoin(
            SearchRequestRecord,
            SearchRequestRecord.id == ChatAnswerRecord.search_request_id,
        )
        .where(ChatAnswerFeedback.feedback_type.in_(("unsupported", "incomplete")))
        .subquery()
    )
    answer_candidates = select(
        answer_ranked.c.candidate_type,
        answer_ranked.c.reason_code,
        answer_ranked.c.query_text,
        answer_ranked.c.mode,
        answer_ranked.c.filters_json,
        answer_ranked.c.evaluation_kind,
        answer_ranked.c.expected_result_type,
        answer_ranked.c.fixture_name,
        answer_ranked.c.latest_seen_at,
        answer_ranked.c.document_id,
        answer_ranked.c.source_filename,
        answer_ranked.c.evaluation_id,
        answer_ranked.c.search_request_id,
        answer_ranked.c.chat_answer_id,
        answer_ranked.c.harness_name,
        answer_ranked.c.occurrence_count,
    ).where(answer_ranked.c.row_number == 1)

    unioned_candidates = union_all(
        evaluation_candidates,
        live_candidates,
        answer_candidates,
    ).subquery()
    return session.execute(
        select(unioned_candidates)
        .order_by(
            unioned_candidates.c.occurrence_count.desc(),
            unioned_candidates.c.latest_seen_at.desc(),
            func.lower(unioned_candidates.c.query_text).asc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()


def list_quality_eval_candidates(
    session: Session, *, limit: int = 12, include_resolved: bool = False
) -> list[QualityEvaluationCandidateResponse]:
    if uses_in_memory_session(session):
        return _quality_candidate_memory._list_quality_eval_candidates_in_memory(
            session,
            limit=limit,
            include_resolved=include_resolved,
        )

    page_limit = _quality_candidate_core._quality_candidate_page_limit(limit)
    unresolved_rows: list[QualityEvaluationCandidateResponse] = []
    resolved_rows: list[QualityEvaluationCandidateResponse] = []
    offset = 0

    while True:
        page = _quality_candidate_rows_page(session, limit=page_limit, offset=offset)
        if not page:
            break
        document_ids = {
            document_id
            for row in page
            for document_id in [
                row.document_id or _maybe_uuid((row.filters_json or {}).get("document_id"))
            ]
            if document_id is not None
        }
        documents_by_id = _quality_candidate_core._load_documents_by_id(session, document_ids)

        for row in page:
            candidate = _quality_candidate_core._quality_candidate_from_row(
                row, documents_by_id=documents_by_id
            )
            if candidate is None:
                continue
            resolution_status, resolved_at, resolution_reason = (
                _quality_candidate_core._resolve_candidate_status_optimized(
                    session,
                    candidate,
                )
            )
            candidate.resolution_status = resolution_status
            candidate.resolved_at = resolved_at
            candidate.resolution_reason = resolution_reason
            if resolution_status == "resolved":
                resolved_rows.append(candidate)
            else:
                unresolved_rows.append(candidate)

        offset += page_limit
        if len(unresolved_rows) >= limit:
            break
        if not include_resolved:
            continue

    if not include_resolved:
        return unresolved_rows[:limit]

    if len(unresolved_rows) >= limit:
        return unresolved_rows[:limit]
    return unresolved_rows + resolved_rows[: max(limit - len(unresolved_rows), 0)]
