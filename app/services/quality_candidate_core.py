from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _maybe_uuid
from app.db.public.document_artifacts import DocumentRunEvaluationQuery
from app.db.public.ingest import Document
from app.db.public.retrieval import ChatAnswerFeedback, ChatAnswerRecord, SearchRequestRecord
from app.schemas.quality import QualityEvaluationCandidateResponse

QUALITY_CANDIDATE_SCAN_FACTOR = 25
QUALITY_CANDIDATE_MIN_SCAN_LIMIT = 100
QUALITY_CANDIDATE_RESOLUTION_SCAN_LIMIT = 25
QUALITY_CANDIDATE_PAGE_MIN_LIMIT = 50

QUALITY_CANDIDATE_REASON_BY_CODE = {
    "failed_answer_evaluation": "failed answer evaluation",
    "failed_evaluation_query": "failed evaluation query",
    "live_search_no_results": "live search returned no results",
    "live_search_no_table_hits": "tabular search returned no table hits",
    "answer_feedback_incomplete": "chat answer marked incomplete",
    "answer_feedback_unsupported": "chat answer marked unsupported",
}


def _candidate_key(
    candidate_type: str,
    reason: str,
    query_text: str,
    mode: str,
    filters: dict,
    expected_result_type: str | None,
    evaluation_kind: str,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        candidate_type,
        reason,
        query_text,
        mode,
        json.dumps(filters or {}, sort_keys=True),
        expected_result_type or "",
        evaluation_kind,
    )


def _evaluation_kind(details: dict | None) -> str:
    return (details or {}).get("evaluation_kind", "retrieval")


def _is_actionable_zero_result_gap(query_text: str, filters: dict) -> bool:
    if (filters or {}).get("document_id") is not None:
        return True
    tokens = [token for token in re.findall(r"[A-Za-z0-9]+", query_text.lower()) if len(token) > 2]
    return len(tokens) >= 2


def _normalize_answer_gap_filters(filters: dict | None) -> dict:
    normalized = dict(filters or {})
    if normalized.get("result_type") == "chunk":
        normalized.pop("result_type", None)
    return normalized


def _filters_for_answer(
    answer: ChatAnswerRecord,
    request_row: SearchRequestRecord | None,
) -> dict:
    filters = request_row.filters_json if request_row is not None else {}
    if not filters and answer.document_id is not None:
        filters = {"document_id": str(answer.document_id)}
    return _normalize_answer_gap_filters(filters)


def _resolve_candidate_status(
    candidate: QualityEvaluationCandidateResponse,
    *,
    evaluation_queries: list[DocumentRunEvaluationQuery],
    search_requests: list[SearchRequestRecord],
    answer_feedback_rows: list[ChatAnswerFeedback],
    chat_answers_by_id: dict[UUID, ChatAnswerRecord],
    search_requests_by_id: dict[UUID, SearchRequestRecord],
) -> tuple[str, datetime | None, str | None]:
    candidate_filters_key = json.dumps(candidate.filters or {}, sort_keys=True)
    resolution_options: list[tuple[datetime, str]] = []

    if candidate.candidate_type == "evaluation_failure":
        for row in evaluation_queries:
            if row.created_at <= candidate.latest_seen_at or not row.passed:
                continue
            if row.query_text != candidate.query_text or row.mode != candidate.mode:
                continue
            if json.dumps(row.filters_json or {}, sort_keys=True) != candidate_filters_key:
                continue
            if row.expected_result_type != candidate.expected_result_type:
                continue
            if _evaluation_kind(getattr(row, "details_json", None)) != candidate.evaluation_kind:
                continue
            resolution_options.append(
                (
                    row.created_at,
                    "later answer evaluation passed"
                    if candidate.evaluation_kind == "answer"
                    else "later retrieval evaluation passed",
                )
            )
    elif candidate.candidate_type == "live_search_gap":
        for row in search_requests:
            if row.origin not in {"api", "chat"} or row.created_at <= candidate.latest_seen_at:
                continue
            if row.query_text != candidate.query_text or row.mode != candidate.mode:
                continue
            if json.dumps(row.filters_json or {}, sort_keys=True) != candidate_filters_key:
                continue
            if candidate.expected_result_type == "table":
                if row.table_hit_count > 0:
                    resolution_options.append(
                        (row.created_at, "later live search returned table hits")
                    )
            elif row.result_count > 0:
                resolution_options.append((row.created_at, "later live search returned results"))
    elif candidate.candidate_type == "answer_feedback_gap":
        for feedback in answer_feedback_rows:
            if (
                feedback.created_at <= candidate.latest_seen_at
                or feedback.feedback_type != "helpful"
            ):
                continue
            answer = chat_answers_by_id.get(feedback.chat_answer_id)
            if answer is None:
                continue
            request_row = search_requests_by_id.get(answer.search_request_id)
            filters = _filters_for_answer(answer, request_row)
            if answer.question_text != candidate.query_text or answer.mode != candidate.mode:
                continue
            if json.dumps(filters or {}, sort_keys=True) != candidate_filters_key:
                continue
            resolution_options.append(
                (feedback.created_at, "later chat answer feedback marked helpful")
            )
        for row in evaluation_queries:
            if row.created_at <= candidate.latest_seen_at or not row.passed:
                continue
            if _evaluation_kind(getattr(row, "details_json", None)) != "answer":
                continue
            if row.query_text != candidate.query_text or row.mode != candidate.mode:
                continue
            if json.dumps(row.filters_json or {}, sort_keys=True) != candidate_filters_key:
                continue
            resolution_options.append((row.created_at, "later answer evaluation passed"))

    if not resolution_options:
        return "unresolved", None, None
    resolved_at, resolution_reason = min(resolution_options, key=lambda item: item[0])
    return "resolved", resolved_at, resolution_reason

def _candidate_scan_limit(limit: int) -> int:
    return max(limit * QUALITY_CANDIDATE_SCAN_FACTOR, QUALITY_CANDIDATE_MIN_SCAN_LIMIT)


def _quality_candidate_page_limit(limit: int) -> int:
    return max(limit * 4, QUALITY_CANDIDATE_PAGE_MIN_LIMIT)

def _load_documents_by_id(session: Session, document_ids: set[UUID]) -> dict[UUID, Document]:
    if not document_ids:
        return {}
    return {
        document.id: document
        for document in session.execute(select(Document).where(Document.id.in_(document_ids)))
        .scalars()
        .all()
    }


def _quality_candidate_from_row(
    row,
    *,
    documents_by_id: dict[UUID, Document],
) -> QualityEvaluationCandidateResponse | None:
    filters = row.filters_json or {}
    if row.reason_code == "live_search_no_results" and not _is_actionable_zero_result_gap(
        row.query_text,
        filters,
    ):
        return None

    document_id = row.document_id or _maybe_uuid(filters.get("document_id"))
    document = documents_by_id.get(document_id) if document_id is not None else None
    return QualityEvaluationCandidateResponse(
        candidate_type=row.candidate_type,
        reason=QUALITY_CANDIDATE_REASON_BY_CODE[row.reason_code],
        query_text=row.query_text,
        mode=row.mode,
        filters=filters,
        evaluation_kind=row.evaluation_kind,
        expected_result_type=row.expected_result_type,
        fixture_name=row.fixture_name,
        occurrence_count=int(row.occurrence_count),
        latest_seen_at=row.latest_seen_at,
        document_id=document_id,
        source_filename=row.source_filename or getattr(document, "source_filename", None),
        evaluation_id=row.evaluation_id,
        search_request_id=row.search_request_id,
        chat_answer_id=row.chat_answer_id,
        harness_name=row.harness_name,
    )


def _resolve_candidate_status_optimized(
    session: Session,
    candidate: QualityEvaluationCandidateResponse,
) -> tuple[str, datetime | None, str | None]:
    candidate_filters_key = json.dumps(candidate.filters or {}, sort_keys=True)

    if candidate.candidate_type == "evaluation_failure":
        statement = (
            select(DocumentRunEvaluationQuery)
            .where(
                DocumentRunEvaluationQuery.passed.is_(True),
                DocumentRunEvaluationQuery.created_at > candidate.latest_seen_at,
                DocumentRunEvaluationQuery.query_text == candidate.query_text,
                DocumentRunEvaluationQuery.mode == candidate.mode,
            )
            .order_by(DocumentRunEvaluationQuery.created_at.asc())
            .limit(QUALITY_CANDIDATE_RESOLUTION_SCAN_LIMIT)
        )
        if candidate.expected_result_type is None:
            statement = statement.where(DocumentRunEvaluationQuery.expected_result_type.is_(None))
        else:
            statement = statement.where(
                DocumentRunEvaluationQuery.expected_result_type == candidate.expected_result_type
            )
        rows = session.execute(statement).scalars().all()
        for row in rows:
            if json.dumps(row.filters_json or {}, sort_keys=True) != candidate_filters_key:
                continue
            if _evaluation_kind(getattr(row, "details_json", None)) != candidate.evaluation_kind:
                continue
            reason = (
                "later answer evaluation passed"
                if candidate.evaluation_kind == "answer"
                else "later retrieval evaluation passed"
            )
            return "resolved", row.created_at, reason
        return "unresolved", None, None

    if candidate.candidate_type == "live_search_gap":
        rows = (
            session.execute(
                select(SearchRequestRecord)
                .where(
                    SearchRequestRecord.origin.in_(("api", "chat")),
                    SearchRequestRecord.created_at > candidate.latest_seen_at,
                    SearchRequestRecord.query_text == candidate.query_text,
                    SearchRequestRecord.mode == candidate.mode,
                )
                .order_by(SearchRequestRecord.created_at.asc())
                .limit(QUALITY_CANDIDATE_RESOLUTION_SCAN_LIMIT)
            )
            .scalars()
            .all()
        )
        for row in rows:
            if json.dumps(row.filters_json or {}, sort_keys=True) != candidate_filters_key:
                continue
            if candidate.expected_result_type == "table":
                if row.table_hit_count > 0:
                    return "resolved", row.created_at, "later live search returned table hits"
                continue
            if row.result_count > 0:
                return "resolved", row.created_at, "later live search returned results"
        return "unresolved", None, None

    helpful_feedback_rows = session.execute(
        select(ChatAnswerFeedback, ChatAnswerRecord, SearchRequestRecord)
        .join(ChatAnswerRecord, ChatAnswerRecord.id == ChatAnswerFeedback.chat_answer_id)
        .outerjoin(
            SearchRequestRecord,
            SearchRequestRecord.id == ChatAnswerRecord.search_request_id,
        )
        .where(
            ChatAnswerFeedback.feedback_type == "helpful",
            ChatAnswerFeedback.created_at > candidate.latest_seen_at,
            ChatAnswerRecord.question_text == candidate.query_text,
            ChatAnswerRecord.mode == candidate.mode,
        )
        .order_by(ChatAnswerFeedback.created_at.asc())
        .limit(QUALITY_CANDIDATE_RESOLUTION_SCAN_LIMIT)
    ).all()
    for feedback, answer, request_row in helpful_feedback_rows:
        filters = _filters_for_answer(answer, request_row)
        if json.dumps(filters or {}, sort_keys=True) != candidate_filters_key:
            continue
        return "resolved", feedback.created_at, "later chat answer feedback marked helpful"

    answer_eval_rows = (
        session.execute(
            select(DocumentRunEvaluationQuery)
            .where(
                DocumentRunEvaluationQuery.passed.is_(True),
                DocumentRunEvaluationQuery.created_at > candidate.latest_seen_at,
                DocumentRunEvaluationQuery.query_text == candidate.query_text,
                DocumentRunEvaluationQuery.mode == candidate.mode,
            )
            .order_by(DocumentRunEvaluationQuery.created_at.asc())
            .limit(QUALITY_CANDIDATE_RESOLUTION_SCAN_LIMIT)
        )
        .scalars()
        .all()
    )
    for row in answer_eval_rows:
        if _evaluation_kind(getattr(row, "details_json", None)) != "answer":
            continue
        if json.dumps(row.filters_json or {}, sort_keys=True) != candidate_filters_key:
            continue
        return "resolved", row.created_at, "later answer evaluation passed"
    return "unresolved", None, None
