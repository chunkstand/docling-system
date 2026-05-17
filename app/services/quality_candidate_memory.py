from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _maybe_uuid
from app.db.models import (
    ChatAnswerFeedback,
    ChatAnswerRecord,
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    SearchRequestRecord,
)
from app.schemas.quality import QualityEvaluationCandidateResponse
from app.services import quality_candidate_core as _quality_candidate_core


def _list_quality_eval_candidates_in_memory(
    session: Session, *, limit: int = 12, include_resolved: bool = False
) -> list[QualityEvaluationCandidateResponse]:
    scan_limit = _quality_candidate_core._candidate_scan_limit(limit)
    evaluation_queries = (
        session.execute(
            select(DocumentRunEvaluationQuery)
            .order_by(DocumentRunEvaluationQuery.created_at.desc())
            .limit(scan_limit)
        )
        .scalars()
        .all()[:scan_limit]
    )
    search_requests = (
        session.execute(
            select(SearchRequestRecord)
            .order_by(SearchRequestRecord.created_at.desc())
            .limit(scan_limit)
        )
        .scalars()
        .all()[:scan_limit]
    )
    answer_feedback_rows = (
        session.execute(
            select(ChatAnswerFeedback)
            .order_by(ChatAnswerFeedback.created_at.desc())
            .limit(scan_limit)
        )
        .scalars()
        .all()[:scan_limit]
    )

    evaluation_ids = {row.evaluation_id for row in evaluation_queries}
    evaluations = [
        row
        for row in session.execute(
            select(DocumentRunEvaluation).where(DocumentRunEvaluation.id.in_(evaluation_ids))
        )
        .scalars()
        .all()
        if row.id in evaluation_ids
    ]
    run_ids = {evaluation.run_id for evaluation in evaluations}
    runs = [
        row
        for row in session.execute(select(DocumentRun).where(DocumentRun.id.in_(run_ids)))
        .scalars()
        .all()
        if row.id in run_ids
    ]

    chat_answer_ids = {feedback.chat_answer_id for feedback in answer_feedback_rows}
    chat_answers = [
        row
        for row in session.execute(
            select(ChatAnswerRecord).where(ChatAnswerRecord.id.in_(chat_answer_ids))
        )
        .scalars()
        .all()
        if row.id in chat_answer_ids
    ]
    search_request_ids = {request.id for request in search_requests} | {
        answer.search_request_id for answer in chat_answers if answer.search_request_id is not None
    }
    search_requests = [
        row
        for row in session.execute(
            select(SearchRequestRecord).where(SearchRequestRecord.id.in_(search_request_ids))
        )
        .scalars()
        .all()
        if row.id in search_request_ids
    ]

    document_ids = {run.document_id for run in runs}
    document_ids.update(
        document_id
        for row in search_requests
        for document_id in [_maybe_uuid((row.filters_json or {}).get("document_id"))]
        if document_id is not None
    )
    document_ids.update(answer.document_id for answer in chat_answers if answer.document_id)
    documents = [
        row
        for row in session.execute(select(Document).where(Document.id.in_(document_ids)))
        .scalars()
        .all()
        if row.id in document_ids
    ]

    documents_by_id = {document.id: document for document in documents}
    runs_by_id = {run.id: run for run in runs}
    evaluations_by_id = {evaluation.id: evaluation for evaluation in evaluations}
    search_requests_by_id = {request.id: request for request in search_requests}
    chat_answers_by_id = {answer.id: answer for answer in chat_answers}

    candidates: dict[
        tuple[str, str, str, str, str, str, str],
        QualityEvaluationCandidateResponse,
    ] = {}

    for row in evaluation_queries:
        if row.passed:
            continue
        evaluation = evaluations_by_id.get(row.evaluation_id)
        run = runs_by_id.get(getattr(evaluation, "run_id", None))
        document = documents_by_id.get(getattr(run, "document_id", None))
        filters = row.filters_json or {}
        evaluation_kind = _quality_candidate_core._evaluation_kind(
            getattr(row, "details_json", None)
        )
        reason = (
            "failed answer evaluation" if evaluation_kind == "answer" else "failed evaluation query"
        )
        key = _quality_candidate_core._candidate_key(
            "evaluation_failure",
            reason,
            row.query_text,
            row.mode,
            filters,
            row.expected_result_type,
            evaluation_kind,
        )
        current = candidates.get(key)
        if current is None:
            current = QualityEvaluationCandidateResponse(
                candidate_type="evaluation_failure",
                reason=reason,
                query_text=row.query_text,
                mode=row.mode,
                filters=filters,
                evaluation_kind=evaluation_kind,
                expected_result_type=row.expected_result_type,
                fixture_name=getattr(evaluation, "fixture_name", None),
                occurrence_count=0,
                latest_seen_at=row.created_at,
                document_id=getattr(document, "id", None),
                source_filename=getattr(document, "source_filename", None),
                evaluation_id=getattr(evaluation, "id", None),
                search_request_id=None,
                chat_answer_id=None,
                harness_name=None,
            )
            candidates[key] = current
        current.occurrence_count += 1
        if row.created_at >= current.latest_seen_at:
            current.latest_seen_at = row.created_at
            current.fixture_name = getattr(evaluation, "fixture_name", None)
            current.document_id = getattr(document, "id", None)
            current.source_filename = getattr(document, "source_filename", None)
            current.evaluation_id = getattr(evaluation, "id", None)

    for row in search_requests:
        if row.origin not in {"api", "chat"}:
            continue

        reason: str | None = None
        expected_result_type: str | None = None
        filters = row.filters_json or {}
        if row.result_count == 0:
            reason = "live search returned no results"
            if not _quality_candidate_core._is_actionable_zero_result_gap(row.query_text, filters):
                continue
        elif (
            row.tabular_query and filters.get("result_type") != "chunk" and row.table_hit_count == 0
        ):
            reason = "tabular search returned no table hits"
            expected_result_type = "table"

        if reason is None:
            continue

        document_id = _maybe_uuid(filters.get("document_id"))
        document = documents_by_id.get(document_id)
        key = _quality_candidate_core._candidate_key(
            "live_search_gap",
            reason,
            row.query_text,
            row.mode,
            filters,
            expected_result_type,
            "retrieval",
        )
        current = candidates.get(key)
        if current is None:
            current = QualityEvaluationCandidateResponse(
                candidate_type="live_search_gap",
                reason=reason,
                query_text=row.query_text,
                mode=row.mode,
                filters=filters,
                evaluation_kind="retrieval",
                expected_result_type=expected_result_type,
                fixture_name=None,
                occurrence_count=0,
                latest_seen_at=row.created_at,
                document_id=document_id,
                source_filename=getattr(document, "source_filename", None),
                evaluation_id=row.evaluation_id,
                search_request_id=row.id,
                chat_answer_id=None,
                harness_name=row.harness_name,
            )
            candidates[key] = current
        current.occurrence_count += 1
        if row.created_at >= current.latest_seen_at:
            current.latest_seen_at = row.created_at
            current.document_id = document_id
            current.source_filename = getattr(document, "source_filename", None)
            current.evaluation_id = row.evaluation_id
            current.search_request_id = row.id
            current.harness_name = row.harness_name

    for feedback in answer_feedback_rows:
        if feedback.feedback_type not in {"unsupported", "incomplete"}:
            continue

        answer = chat_answers_by_id.get(feedback.chat_answer_id)
        if answer is None:
            continue

        request_row = search_requests_by_id.get(answer.search_request_id)
        filters = _quality_candidate_core._filters_for_answer(answer, request_row)

        document_id = answer.document_id or _maybe_uuid(filters.get("document_id"))
        document = documents_by_id.get(document_id)
        reason = (
            "chat answer marked unsupported"
            if feedback.feedback_type == "unsupported"
            else "chat answer marked incomplete"
        )
        key = _quality_candidate_core._candidate_key(
            "answer_feedback_gap",
            reason,
            answer.question_text,
            answer.mode,
            filters,
            None,
            "answer",
        )
        current = candidates.get(key)
        if current is None:
            current = QualityEvaluationCandidateResponse(
                candidate_type="answer_feedback_gap",
                reason=reason,
                query_text=answer.question_text,
                mode=answer.mode,
                filters=filters,
                evaluation_kind="answer",
                expected_result_type=None,
                fixture_name=None,
                occurrence_count=0,
                latest_seen_at=feedback.created_at,
                document_id=document_id,
                source_filename=getattr(document, "source_filename", None),
                evaluation_id=request_row.evaluation_id if request_row is not None else None,
                search_request_id=answer.search_request_id,
                chat_answer_id=answer.id,
                harness_name=answer.harness_name,
            )
            candidates[key] = current
        current.occurrence_count += 1
        if feedback.created_at >= current.latest_seen_at:
            current.latest_seen_at = feedback.created_at
            current.document_id = document_id
            current.source_filename = getattr(document, "source_filename", None)
            current.evaluation_id = request_row.evaluation_id if request_row is not None else None
            current.search_request_id = answer.search_request_id
            current.chat_answer_id = answer.id
            current.harness_name = answer.harness_name

    rows = list(candidates.values())
    for row in rows:
        resolution_status, resolved_at, resolution_reason = (
            _quality_candidate_core._resolve_candidate_status(
                row,
                evaluation_queries=evaluation_queries,
                search_requests=search_requests,
                answer_feedback_rows=answer_feedback_rows,
                chat_answers_by_id=chat_answers_by_id,
                search_requests_by_id=search_requests_by_id,
            )
        )
        row.resolution_status = resolution_status
        row.resolved_at = resolved_at
        row.resolution_reason = resolution_reason

    if not include_resolved:
        rows = [row for row in rows if row.resolution_status != "resolved"]

    rows = sorted(
        rows,
        key=lambda row: (
            row.resolution_status == "resolved",
            -row.occurrence_count,
            -row.latest_seen_at.timestamp(),
            row.query_text.lower(),
        ),
    )
    return rows[:limit]
