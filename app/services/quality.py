from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Date, String, and_, case, cast, func, literal, null, or_, select, union_all
from sqlalchemy.orm import Session

from app.db.models import (
    ChatAnswerFeedback,
    ChatAnswerRecord,
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    RunStatus,
    SearchFeedback,
    SearchReplayRun,
    SearchRequestRecord,
)
from app.schemas.quality import (
    QualityEvaluationCandidateResponse,
    QualityEvaluationStatusResponse,
    QualityFailuresResponse,
    QualityFailureStageCountResponse,
    QualityFeedbackTypeCountResponse,
    QualityReplayRunTrendResponse,
    QualityRunFailureResponse,
    QualitySearchTrendPointResponse,
    QualitySummaryResponse,
    QualityTrendsResponse,
)
from app.services.evaluations import get_latest_evaluations_by_run_id
from app.services.session_utils import uses_in_memory_session

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


@dataclass
class QualityContext:
    documents: list[object]
    runs: list[object]
    evaluations: list[object]


def _load_quality_context(session: Session) -> QualityContext:
    return QualityContext(
        documents=session.execute(select(Document)).scalars().all(),
        runs=session.execute(select(DocumentRun)).scalars().all(),
        evaluations=session.execute(select(DocumentRunEvaluation)).scalars().all(),
    )


def _latest_evaluations_by_run(evaluations: list[object]) -> dict[object, object]:
    latest_by_run: dict[object, object] = {}
    for evaluation in evaluations:
        run_id = evaluation.run_id
        current = latest_by_run.get(run_id)
        if current is None or evaluation.created_at > current.created_at:
            latest_by_run[run_id] = evaluation
    return latest_by_run


def _evaluation_summary_value(evaluation: object | None, key: str, default: int = 0) -> int:
    if evaluation is None:
        return default
    return int((getattr(evaluation, "summary_json", None) or {}).get(key, default) or default)


def _evaluation_structural_passed(evaluation: object | None) -> bool | None:
    if evaluation is None:
        return None
    summary = getattr(evaluation, "summary_json", None) or {}
    value = summary.get("structural_passed")
    if value is None:
        return None
    return bool(value)


def _to_quality_evaluation_row(
    document: object,
    latest_run: object | None,
    evaluation: object | None,
) -> QualityEvaluationStatusResponse:
    return QualityEvaluationStatusResponse(
        document_id=document.id,
        source_filename=document.source_filename,
        title=document.title,
        latest_run_id=getattr(document, "latest_run_id", None),
        latest_run_status=getattr(latest_run, "status", None),
        latest_validation_status=getattr(latest_run, "validation_status", None),
        evaluation_id=getattr(evaluation, "id", None),
        evaluation_status=getattr(evaluation, "status", "missing"),
        fixture_name=getattr(evaluation, "fixture_name", None),
        query_count=_evaluation_summary_value(evaluation, "query_count"),
        passed_queries=_evaluation_summary_value(evaluation, "passed_queries"),
        failed_queries=_evaluation_summary_value(evaluation, "failed_queries"),
        regressed_queries=_evaluation_summary_value(evaluation, "regressed_queries"),
        improved_queries=_evaluation_summary_value(evaluation, "improved_queries"),
        stable_queries=_evaluation_summary_value(evaluation, "stable_queries"),
        failed_structural_checks=_evaluation_summary_value(evaluation, "failed_structural_checks"),
        structural_passed=_evaluation_structural_passed(evaluation),
        error_message=getattr(evaluation, "error_message", None),
        updated_at=document.updated_at,
    )


def _latest_quality_evaluation_rows(session: Session) -> list[QualityEvaluationStatusResponse]:
    documents = (
        session.execute(select(Document).order_by(Document.updated_at.desc())).scalars().all()
    )
    latest_run_ids = {
        document.latest_run_id for document in documents if getattr(document, "latest_run_id", None)
    }
    latest_runs = (
        session.execute(select(DocumentRun).where(DocumentRun.id.in_(latest_run_ids)))
        .scalars()
        .all()
        if latest_run_ids
        else []
    )
    latest_runs_by_id = {run.id: run for run in latest_runs}
    latest_evaluations_by_run_id = get_latest_evaluations_by_run_id(session, latest_run_ids)
    return [
        _to_quality_evaluation_row(
            document,
            latest_runs_by_id.get(getattr(document, "latest_run_id", None)),
            latest_evaluations_by_run_id.get(getattr(document, "latest_run_id", None)),
        )
        for document in documents
    ]


def _quality_summary_from_rows(
    rows: list[QualityEvaluationStatusResponse],
    failure_stage_counts: Counter[str],
) -> QualitySummaryResponse:
    return QualitySummaryResponse(
        document_count=len(rows),
        latest_runs_completed=sum(
            1 for row in rows if row.latest_run_status == RunStatus.COMPLETED.value
        ),
        documents_with_latest_evaluation=sum(
            1 for row in rows if row.evaluation_status != "missing"
        ),
        missing_latest_evaluations=sum(1 for row in rows if row.evaluation_status == "missing"),
        completed_latest_evaluations=sum(1 for row in rows if row.evaluation_status == "completed"),
        failed_latest_evaluations=sum(1 for row in rows if row.evaluation_status == "failed"),
        skipped_latest_evaluations=sum(1 for row in rows if row.evaluation_status == "skipped"),
        total_failed_queries=sum(row.failed_queries for row in rows),
        documents_with_failed_queries=sum(1 for row in rows if row.failed_queries > 0),
        total_failed_structural_checks=sum(row.failed_structural_checks for row in rows),
        documents_with_structural_failures=sum(
            1 for row in rows if row.failed_structural_checks > 0
        ),
        failed_run_count=sum(failure_stage_counts.values()),
        failed_runs_by_stage=[
            QualityFailureStageCountResponse(failure_stage=stage, run_count=count)
            for stage, count in sorted(
                failure_stage_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    )


def _evaluation_failures_from_rows(
    rows: list[QualityEvaluationStatusResponse],
) -> list[QualityEvaluationStatusResponse]:
    evaluation_failures = [
        row
        for row in rows
        if row.evaluation_status in {"missing", "failed"}
        or row.failed_queries > 0
        or row.failed_structural_checks > 0
    ]
    evaluation_failures.sort(
        key=lambda row: (
            row.evaluation_status == "completed",
            row.failed_structural_checks == 0,
            row.failed_queries == 0,
            row.source_filename.lower(),
        )
    )
    return evaluation_failures


def build_quality_evaluation_rows(
    context: QualityContext,
) -> list[QualityEvaluationStatusResponse]:
    run_by_id = {run.id: run for run in context.runs}
    latest_evaluation_by_run = _latest_evaluations_by_run(context.evaluations)
    return [
        _to_quality_evaluation_row(
            document,
            run_by_id.get(getattr(document, "latest_run_id", None)),
            latest_evaluation_by_run.get(getattr(document, "latest_run_id", None)),
        )
        for document in sorted(context.documents, key=lambda item: item.updated_at, reverse=True)
    ]


def build_quality_summary(
    context: QualityContext,
    evaluation_rows: list[QualityEvaluationStatusResponse] | None = None,
) -> QualitySummaryResponse:
    rows = evaluation_rows or build_quality_evaluation_rows(context)
    failed_runs = [run for run in context.runs if run.status == RunStatus.FAILED.value]
    return _quality_summary_from_rows(
        rows,
        Counter((getattr(run, "failure_stage", None) or "missing") for run in failed_runs),
    )


def build_quality_failures(
    context: QualityContext,
    evaluation_rows: list[QualityEvaluationStatusResponse] | None = None,
) -> QualityFailuresResponse:
    rows = evaluation_rows or build_quality_evaluation_rows(context)
    documents_by_id = {document.id: document for document in context.documents}
    evaluation_failures = _evaluation_failures_from_rows(rows)

    run_failures: list[QualityRunFailureResponse] = []
    for run in sorted(
        (item for item in context.runs if item.status == RunStatus.FAILED.value),
        key=lambda item: item.completed_at or item.created_at,
        reverse=True,
    ):
        document = documents_by_id.get(run.document_id)
        run_failures.append(
            QualityRunFailureResponse(
                document_id=run.document_id,
                source_filename=getattr(document, "source_filename", "unknown.pdf"),
                title=getattr(document, "title", None),
                run_id=run.id,
                run_number=run.run_number,
                status=run.status,
                failure_stage=run.failure_stage,
                error_message=run.error_message,
                has_failure_artifact=bool(run.failure_artifact_path),
                created_at=run.created_at,
                completed_at=run.completed_at,
            )
        )

    return QualityFailuresResponse(
        evaluation_failures=evaluation_failures,
        run_failures=run_failures,
    )


def list_quality_evaluations(session: Session) -> list[QualityEvaluationStatusResponse]:
    if uses_in_memory_session(session):
        return build_quality_evaluation_rows(_load_quality_context(session))
    return _latest_quality_evaluation_rows(session)


def get_quality_summary(session: Session) -> QualitySummaryResponse:
    if uses_in_memory_session(session):
        context = _load_quality_context(session)
        rows = build_quality_evaluation_rows(context)
        return build_quality_summary(context, rows)

    rows = _latest_quality_evaluation_rows(session)
    failure_stage_rows = session.execute(
        select(DocumentRun.failure_stage, func.count().label("run_count"))
        .where(DocumentRun.status == RunStatus.FAILED.value)
        .group_by(DocumentRun.failure_stage)
    ).all()
    failure_stage_counts = Counter(
        (failure_stage or "missing") for failure_stage, _count in failure_stage_rows
    )
    for failure_stage, count in failure_stage_rows:
        failure_stage_counts[failure_stage or "missing"] = int(count)
    return _quality_summary_from_rows(rows, failure_stage_counts)


def get_quality_failures(session: Session) -> QualityFailuresResponse:
    if uses_in_memory_session(session):
        context = _load_quality_context(session)
        rows = build_quality_evaluation_rows(context)
        return build_quality_failures(context, rows)

    rows = _latest_quality_evaluation_rows(session)
    evaluation_failures = _evaluation_failures_from_rows(rows)
    run_failure_rows = session.execute(
        select(DocumentRun, Document)
        .join(Document, Document.id == DocumentRun.document_id)
        .where(DocumentRun.status == RunStatus.FAILED.value)
        .order_by(func.coalesce(DocumentRun.completed_at, DocumentRun.created_at).desc())
    ).all()
    run_failures = [
        QualityRunFailureResponse(
            document_id=run.document_id,
            source_filename=document.source_filename,
            title=document.title,
            run_id=run.id,
            run_number=run.run_number,
            status=run.status,
            failure_stage=run.failure_stage,
            error_message=run.error_message,
            has_failure_artifact=bool(run.failure_artifact_path),
            created_at=run.created_at,
            completed_at=run.completed_at,
        )
        for run, document in run_failure_rows
    ]
    return QualityFailuresResponse(
        evaluation_failures=evaluation_failures,
        run_failures=run_failures,
    )


def _maybe_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


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


def _list_quality_eval_candidates_in_memory(
    session: Session, *, limit: int = 12, include_resolved: bool = False
) -> list[QualityEvaluationCandidateResponse]:
    scan_limit = _candidate_scan_limit(limit)
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
            select(ChatAnswerFeedback).order_by(ChatAnswerFeedback.created_at.desc()).limit(
                scan_limit
            )
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
        evaluation_kind = _evaluation_kind(getattr(row, "details_json", None))
        reason = (
            "failed answer evaluation" if evaluation_kind == "answer" else "failed evaluation query"
        )
        key = _candidate_key(
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
            if not _is_actionable_zero_result_gap(row.query_text, filters):
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
        key = _candidate_key(
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
        filters = _filters_for_answer(answer, request_row)

        document_id = answer.document_id or _maybe_uuid(filters.get("document_id"))
        document = documents_by_id.get(document_id)
        reason = (
            "chat answer marked unsupported"
            if feedback.feedback_type == "unsupported"
            else "chat answer marked incomplete"
        )
        key = _candidate_key(
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
        resolution_status, resolved_at, resolution_reason = _resolve_candidate_status(
            row,
            evaluation_queries=evaluation_queries,
            search_requests=search_requests,
            answer_feedback_rows=answer_feedback_rows,
            chat_answers_by_id=chat_answers_by_id,
            search_requests_by_id=search_requests_by_id,
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


def _get_quality_trends_in_memory(
    session: Session, *, day_count: int = 7, replay_limit: int = 8
) -> QualityTrendsResponse:
    search_requests = (
        session.execute(
            select(SearchRequestRecord).where(SearchRequestRecord.origin.in_(("api", "chat")))
        )
        .scalars()
        .all()
    )
    feedback_rows = session.execute(select(SearchFeedback)).scalars().all()
    answer_feedback_rows = session.execute(select(ChatAnswerFeedback)).scalars().all()
    replay_runs = (
        session.execute(select(SearchReplayRun).order_by(SearchReplayRun.created_at.desc()))
        .scalars()
        .all()
    )

    today = datetime.now(UTC).date()
    day_buckets = {
        (today - timedelta(days=offset)).isoformat(): {
            "request_count": 0,
            "zero_result_count": 0,
            "table_hit_requests": 0,
        }
        for offset in reversed(range(day_count))
    }

    for row in search_requests:
        bucket_key = row.created_at.date().isoformat()
        bucket = day_buckets.get(bucket_key)
        if bucket is None:
            continue
        bucket["request_count"] += 1
        bucket["zero_result_count"] += int(row.result_count == 0)
        bucket["table_hit_requests"] += int(row.table_hit_count > 0)

    feedback_counts = Counter(row.feedback_type for row in feedback_rows)
    answer_feedback_counts = Counter(row.feedback_type for row in answer_feedback_rows)

    return QualityTrendsResponse(
        search_request_days=[
            QualitySearchTrendPointResponse(
                bucket_date=bucket_date,
                request_count=values["request_count"],
                zero_result_count=values["zero_result_count"],
                table_hit_rate=(
                    values["table_hit_requests"] / values["request_count"]
                    if values["request_count"]
                    else 0.0
                ),
            )
            for bucket_date, values in day_buckets.items()
        ],
        feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=count)
            for feedback_type, count in sorted(
                feedback_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        answer_feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=count)
            for feedback_type, count in sorted(
                answer_feedback_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        recent_replay_runs=[
            QualityReplayRunTrendResponse(
                replay_run_id=row.id,
                source_type=row.source_type,
                status=row.status,
                query_count=row.query_count,
                passed_count=row.passed_count,
                failed_count=row.failed_count,
                created_at=row.created_at,
            )
            for row in replay_runs[:replay_limit]
        ],
    )


def _candidate_scan_limit(limit: int) -> int:
    return max(limit * QUALITY_CANDIDATE_SCAN_FACTOR, QUALITY_CANDIDATE_MIN_SCAN_LIMIT)


def _quality_candidate_page_limit(limit: int) -> int:
    return max(limit * 4, QUALITY_CANDIDATE_PAGE_MIN_LIMIT)


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


def list_quality_eval_candidates(
    session: Session, *, limit: int = 12, include_resolved: bool = False
) -> list[QualityEvaluationCandidateResponse]:
    if uses_in_memory_session(session):
        return _list_quality_eval_candidates_in_memory(
            session,
            limit=limit,
            include_resolved=include_resolved,
        )

    page_limit = _quality_candidate_page_limit(limit)
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
        documents_by_id = _load_documents_by_id(session, document_ids)

        for row in page:
            candidate = _quality_candidate_from_row(row, documents_by_id=documents_by_id)
            if candidate is None:
                continue
            resolution_status, resolved_at, resolution_reason = _resolve_candidate_status_optimized(
                session,
                candidate,
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


def get_quality_trends(
    session: Session, *, day_count: int = 7, replay_limit: int = 8
) -> QualityTrendsResponse:
    if uses_in_memory_session(session):
        return _get_quality_trends_in_memory(
            session,
            day_count=day_count,
            replay_limit=replay_limit,
        )

    today = datetime.now(UTC).date()
    cutoff = datetime.combine(
        today - timedelta(days=day_count - 1),
        datetime.min.time(),
        tzinfo=UTC,
    )
    bucket_date = cast(func.timezone("UTC", SearchRequestRecord.created_at), Date)
    search_request_days = session.execute(
        select(
            bucket_date.label("bucket_date"),
            func.count().label("request_count"),
            func.sum(case((SearchRequestRecord.result_count == 0, 1), else_=0)).label(
                "zero_result_count"
            ),
            func.sum(case((SearchRequestRecord.table_hit_count > 0, 1), else_=0)).label(
                "table_hit_requests"
            ),
        )
        .where(
            SearchRequestRecord.origin.in_(("api", "chat")),
            SearchRequestRecord.created_at >= cutoff,
        )
        .group_by(bucket_date)
    ).all()
    feedback_counts = session.execute(
        select(SearchFeedback.feedback_type, func.count().label("count")).group_by(
            SearchFeedback.feedback_type
        )
    ).all()
    answer_feedback_counts = session.execute(
        select(ChatAnswerFeedback.feedback_type, func.count().label("count")).group_by(
            ChatAnswerFeedback.feedback_type
        )
    ).all()
    replay_runs = (
        session.execute(
            select(SearchReplayRun).order_by(SearchReplayRun.created_at.desc()).limit(replay_limit)
        )
        .scalars()
        .all()
    )

    day_buckets = {
        (today - timedelta(days=offset)).isoformat(): {
            "request_count": 0,
            "zero_result_count": 0,
            "table_hit_requests": 0,
        }
        for offset in reversed(range(day_count))
    }
    for bucket_row in search_request_days:
        bucket = day_buckets.get(bucket_row.bucket_date.isoformat())
        if bucket is None:
            continue
        bucket["request_count"] = int(bucket_row.request_count)
        bucket["zero_result_count"] = int(bucket_row.zero_result_count or 0)
        bucket["table_hit_requests"] = int(bucket_row.table_hit_requests or 0)

    return QualityTrendsResponse(
        search_request_days=[
            QualitySearchTrendPointResponse(
                bucket_date=bucket_date,
                request_count=values["request_count"],
                zero_result_count=values["zero_result_count"],
                table_hit_rate=(
                    values["table_hit_requests"] / values["request_count"]
                    if values["request_count"]
                    else 0.0
                ),
            )
            for bucket_date, values in day_buckets.items()
        ],
        feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=int(count))
            for feedback_type, count in sorted(
                feedback_counts,
                key=lambda item: (-int(item[1]), item[0]),
            )
        ],
        answer_feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=int(count))
            for feedback_type, count in sorted(
                answer_feedback_counts,
                key=lambda item: (-int(item[1]), item[0]),
            )
        ],
        recent_replay_runs=[
            QualityReplayRunTrendResponse(
                replay_run_id=row.id,
                source_type=row.source_type,
                status=row.status,
                query_count=row.query_count,
                passed_count=row.passed_count,
                failed_count=row.failed_count,
                created_at=row.created_at,
            )
            for row in replay_runs
        ],
    )
