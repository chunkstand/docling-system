from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentRun, DocumentRunEvaluation, RunStatus
from app.schemas.quality import (
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
