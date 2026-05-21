from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.db.public.document_artifacts import DocumentRunEvaluation, DocumentRunEvaluationQuery
from app.db.public.ingest import Document
from app.schemas.evaluations import (
    EvaluationDetailResponse,
    EvaluationQueryResultResponse,
    EvaluationSummaryResponse,
)


def _to_evaluation_summary(evaluation: DocumentRunEvaluation) -> EvaluationSummaryResponse:
    summary = evaluation.summary_json or {}
    baseline_run_id = summary.get("baseline_run_id")
    return EvaluationSummaryResponse(
        evaluation_id=evaluation.id,
        run_id=evaluation.run_id,
        corpus_name=evaluation.corpus_name,
        fixture_name=evaluation.fixture_name,
        status=evaluation.status,
        query_count=summary.get("query_count", 0),
        passed_queries=summary.get("passed_queries", 0),
        failed_queries=summary.get("failed_queries", 0),
        regressed_queries=summary.get("regressed_queries", 0),
        improved_queries=summary.get("improved_queries", 0),
        stable_queries=summary.get("stable_queries", 0),
        baseline_run_id=UUID(baseline_run_id) if baseline_run_id else None,
        error_message=evaluation.error_message,
        created_at=evaluation.created_at,
        completed_at=evaluation.completed_at,
    )


def get_latest_evaluation_summary(
    session: Session, run_id: UUID | None
) -> EvaluationSummaryResponse | None:
    if run_id is None:
        return None
    evaluation = (
        session.execute(
            select(DocumentRunEvaluation)
            .where(DocumentRunEvaluation.run_id == run_id)
            .order_by(DocumentRunEvaluation.created_at.desc())
        )
        .scalars()
        .first()
    )
    if evaluation is None:
        return None
    return _to_evaluation_summary(evaluation)


def get_latest_evaluations_by_run_id(
    session: Session,
    run_ids: list[UUID] | set[UUID],
) -> dict[UUID, DocumentRunEvaluation]:
    run_id_list = list(run_ids)
    if not run_id_list:
        return {}

    ranked_evaluations = (
        select(
            DocumentRunEvaluation.id.label("evaluation_id"),
            func.row_number()
            .over(
                partition_by=DocumentRunEvaluation.run_id,
                order_by=DocumentRunEvaluation.created_at.desc(),
            )
            .label("row_number"),
        )
        .where(DocumentRunEvaluation.run_id.in_(run_id_list))
        .subquery()
    )
    evaluation_alias = aliased(DocumentRunEvaluation)
    rows = (
        session.execute(
            select(evaluation_alias)
            .join(ranked_evaluations, ranked_evaluations.c.evaluation_id == evaluation_alias.id)
            .where(ranked_evaluations.c.row_number == 1)
        )
        .scalars()
        .all()
    )
    return {row.run_id: row for row in rows}


def get_latest_evaluation_summaries(
    session: Session,
    run_ids: list[UUID] | set[UUID],
) -> dict[UUID, EvaluationSummaryResponse]:
    return {
        run_id: _to_evaluation_summary(evaluation)
        for run_id, evaluation in get_latest_evaluations_by_run_id(session, run_ids).items()
    }


def get_latest_document_evaluation(
    session: Session, document: Document
) -> EvaluationDetailResponse | None:
    if document.latest_run_id is None:
        return None
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
        return None
    query_rows = (
        session.execute(
            select(DocumentRunEvaluationQuery)
            .where(DocumentRunEvaluationQuery.evaluation_id == evaluation.id)
            .order_by(
                DocumentRunEvaluationQuery.created_at.asc(),
                DocumentRunEvaluationQuery.query_text.asc(),
            )
        )
        .scalars()
        .all()
    )
    summary = _to_evaluation_summary(evaluation)
    return EvaluationDetailResponse(
        **summary.model_dump(),
        summary=evaluation.summary_json or {},
        query_results=[
            EvaluationQueryResultResponse(
                query_text=row.query_text,
                mode=row.mode,
                evaluation_kind=(row.details_json or {}).get("evaluation_kind", "retrieval"),
                expected_result_type=row.expected_result_type,
                expected_top_n=row.expected_top_n,
                passed=row.passed,
                candidate_rank=row.candidate_rank,
                baseline_rank=row.baseline_rank,
                rank_delta=row.rank_delta,
                candidate_score=row.candidate_score,
                baseline_score=row.baseline_score,
                candidate_result_type=row.candidate_result_type,
                baseline_result_type=row.baseline_result_type,
                candidate_label=row.candidate_label,
                baseline_label=row.baseline_label,
                details=row.details_json,
            )
            for row in query_rows
        ],
    )
