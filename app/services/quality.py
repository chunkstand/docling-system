from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    RunStatus,
    SearchRequestRecord,
)
from app.schemas.quality import (
    QualityEvaluationCandidateResponse,
    QualityEvaluationStatusResponse,
    QualityFailuresResponse,
    QualityFailureStageCountResponse,
    QualityRunFailureResponse,
    QualitySummaryResponse,
)


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


def build_quality_evaluation_rows(
    context: QualityContext,
) -> list[QualityEvaluationStatusResponse]:
    run_by_id = {run.id: run for run in context.runs}
    latest_evaluation_by_run = _latest_evaluations_by_run(context.evaluations)
    rows: list[QualityEvaluationStatusResponse] = []

    for document in sorted(context.documents, key=lambda item: item.updated_at, reverse=True):
        latest_run = run_by_id.get(getattr(document, "latest_run_id", None))
        evaluation = latest_evaluation_by_run.get(getattr(document, "latest_run_id", None))
        rows.append(
            QualityEvaluationStatusResponse(
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
                failed_structural_checks=_evaluation_summary_value(
                    evaluation, "failed_structural_checks"
                ),
                structural_passed=_evaluation_structural_passed(evaluation),
                error_message=getattr(evaluation, "error_message", None),
                updated_at=document.updated_at,
            )
        )

    return rows


def build_quality_summary(
    context: QualityContext,
    evaluation_rows: list[QualityEvaluationStatusResponse] | None = None,
) -> QualitySummaryResponse:
    rows = evaluation_rows or build_quality_evaluation_rows(context)
    failed_runs = [run for run in context.runs if run.status == RunStatus.FAILED.value]
    failure_stage_counts = Counter(
        (getattr(run, "failure_stage", None) or "missing") for run in failed_runs
    )

    return QualitySummaryResponse(
        document_count=len(rows),
        latest_runs_completed=sum(
            1 for row in rows if row.latest_run_status == RunStatus.COMPLETED.value
        ),
        documents_with_latest_evaluation=sum(
            1 for row in rows if row.evaluation_status != "missing"
        ),
        missing_latest_evaluations=sum(1 for row in rows if row.evaluation_status == "missing"),
        completed_latest_evaluations=sum(
            1 for row in rows if row.evaluation_status == "completed"
        ),
        failed_latest_evaluations=sum(1 for row in rows if row.evaluation_status == "failed"),
        skipped_latest_evaluations=sum(1 for row in rows if row.evaluation_status == "skipped"),
        total_failed_queries=sum(row.failed_queries for row in rows),
        documents_with_failed_queries=sum(1 for row in rows if row.failed_queries > 0),
        total_failed_structural_checks=sum(row.failed_structural_checks for row in rows),
        documents_with_structural_failures=sum(
            1 for row in rows if row.failed_structural_checks > 0
        ),
        failed_run_count=len(failed_runs),
        failed_runs_by_stage=[
            QualityFailureStageCountResponse(failure_stage=stage, run_count=count)
            for stage, count in sorted(
                failure_stage_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    )


def build_quality_failures(
    context: QualityContext,
    evaluation_rows: list[QualityEvaluationStatusResponse] | None = None,
) -> QualityFailuresResponse:
    rows = evaluation_rows or build_quality_evaluation_rows(context)
    documents_by_id = {document.id: document for document in context.documents}
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

    run_failures: list[QualityRunFailureResponse] = []
    for run in sorted(
        (item for item in context.runs if item.status == RunStatus.FAILED.value),
        key=lambda item: (item.completed_at or item.created_at),
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
    return build_quality_evaluation_rows(_load_quality_context(session))


def get_quality_summary(session: Session) -> QualitySummaryResponse:
    context = _load_quality_context(session)
    rows = build_quality_evaluation_rows(context)
    return build_quality_summary(context, rows)


def get_quality_failures(session: Session) -> QualityFailuresResponse:
    context = _load_quality_context(session)
    rows = build_quality_evaluation_rows(context)
    return build_quality_failures(context, rows)


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
) -> tuple[str, str, str, str, str, str]:
    return (
        candidate_type,
        reason,
        query_text,
        mode,
        json.dumps(filters or {}, sort_keys=True),
        expected_result_type or "",
    )


def list_quality_eval_candidates(
    session: Session, *, limit: int = 12
) -> list[QualityEvaluationCandidateResponse]:
    documents = session.execute(select(Document)).scalars().all()
    runs = session.execute(select(DocumentRun)).scalars().all()
    evaluations = session.execute(select(DocumentRunEvaluation)).scalars().all()
    evaluation_queries = session.execute(select(DocumentRunEvaluationQuery)).scalars().all()
    search_requests = session.execute(select(SearchRequestRecord)).scalars().all()

    documents_by_id = {document.id: document for document in documents}
    runs_by_id = {run.id: run for run in runs}
    evaluations_by_id = {evaluation.id: evaluation for evaluation in evaluations}

    candidates: dict[tuple[str, str, str, str, str, str], QualityEvaluationCandidateResponse] = {}

    for row in evaluation_queries:
        if row.passed:
            continue
        evaluation = evaluations_by_id.get(row.evaluation_id)
        run = runs_by_id.get(getattr(evaluation, "run_id", None))
        document = documents_by_id.get(getattr(run, "document_id", None))
        filters = row.filters_json or {}
        key = _candidate_key(
            "evaluation_failure",
            "failed evaluation query",
            row.query_text,
            row.mode,
            filters,
            row.expected_result_type,
        )
        current = candidates.get(key)
        if current is None:
            current = QualityEvaluationCandidateResponse(
                candidate_type="evaluation_failure",
                reason="failed evaluation query",
                query_text=row.query_text,
                mode=row.mode,
                filters=filters,
                expected_result_type=row.expected_result_type,
                fixture_name=getattr(evaluation, "fixture_name", None),
                occurrence_count=0,
                latest_seen_at=row.created_at,
                document_id=getattr(document, "id", None),
                source_filename=getattr(document, "source_filename", None),
                evaluation_id=getattr(evaluation, "id", None),
                search_request_id=None,
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
        elif (
            row.tabular_query
            and filters.get("result_type") != "chunk"
            and row.table_hit_count == 0
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
        )
        current = candidates.get(key)
        if current is None:
            current = QualityEvaluationCandidateResponse(
                candidate_type="live_search_gap",
                reason=reason,
                query_text=row.query_text,
                mode=row.mode,
                filters=filters,
                expected_result_type=expected_result_type,
                fixture_name=None,
                occurrence_count=0,
                latest_seen_at=row.created_at,
                document_id=document_id,
                source_filename=getattr(document, "source_filename", None),
                evaluation_id=row.evaluation_id,
                search_request_id=row.id,
            )
            candidates[key] = current
        current.occurrence_count += 1
        if row.created_at >= current.latest_seen_at:
            current.latest_seen_at = row.created_at
            current.document_id = document_id
            current.source_filename = getattr(document, "source_filename", None)
            current.evaluation_id = row.evaluation_id
            current.search_request_id = row.id

    rows = sorted(
        candidates.values(),
        key=lambda row: (
            -row.occurrence_count,
            -row.latest_seen_at.timestamp(),
            row.query_text.lower(),
        ),
    )
    return rows[:limit]
