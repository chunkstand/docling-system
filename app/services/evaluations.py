from __future__ import annotations

import uuid
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.config import get_settings as _get_settings
from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
)
from app.schemas.evaluations import (
    EvaluationDetailResponse,
    EvaluationQueryResultResponse,
    EvaluationSummaryResponse,
)
from app.services import evaluation_fixtures as fixture_owners
from app.services import evaluation_scoring as scoring_owners
from app.services.chat import answer_question as _answer_question
from app.services.evaluation_execution import (
    EvaluationBatchResult,
    build_completed_evaluation_summary,
    execute_answer_queries,
    execute_retrieval_queries,
)
from app.services.search import search_documents

EVAL_VERSION = 1
DEFAULT_CORPUS_NAME = "default"
get_settings = _get_settings
answer_question = _answer_question
DEFAULT_CORPUS_PATH = fixture_owners.DEFAULT_CORPUS_PATH
AUTO_CORPUS_FILENAME = fixture_owners.AUTO_CORPUS_FILENAME
AUTO_FIXTURE_KIND = fixture_owners.AUTO_FIXTURE_KIND
EvaluationFixture = fixture_owners.EvaluationFixture
EvaluationQueryCase = fixture_owners.EvaluationQueryCase
EvaluationAnswerCase = fixture_owners.EvaluationAnswerCase
EvaluationMergeExpectation = fixture_owners.EvaluationMergeExpectation
EvaluationThresholds = fixture_owners.EvaluationThresholds
_auto_corpus_path = fixture_owners._auto_corpus_path
_configured_manual_corpus_path = fixture_owners._configured_manual_corpus_path
_matching_rank = fixture_owners._matching_rank
_metadata_for_row = fixture_owners._metadata_for_row
_normalized_caption_text = fixture_owners._normalized_caption_text
build_auto_evaluation_fixture_document = fixture_owners.build_auto_evaluation_fixture_document
ensure_auto_evaluation_fixture = fixture_owners.ensure_auto_evaluation_fixture
fixture_for_document = fixture_owners.fixture_for_document
load_evaluation_fixtures = fixture_owners.load_evaluation_fixtures
_run_label = scoring_owners._run_label
_top_result_details = scoring_owners._top_result_details
_result_at_rank = scoring_owners._result_at_rank
_result_matches_expected = scoring_owners._result_matches_expected
_rank_delta = scoring_owners._rank_delta
_classify_delta = scoring_owners._classify_delta
_table_label = scoring_owners._table_label
_source_segment_count = scoring_owners._source_segment_count
_text_contains = scoring_owners._text_contains
_table_matches_merge_expectation = scoring_owners._table_matches_merge_expectation
_answer_excerpt = scoring_owners._answer_excerpt
_missing_answer_substrings = scoring_owners._missing_answer_substrings
_top_n_source_hit_count = scoring_owners._top_n_source_hit_count
_foreign_results_before_first_expected_hit = (
    scoring_owners._foreign_results_before_first_expected_hit
)
_expected_hit_count_in_window = scoring_owners._expected_hit_count_in_window
_reciprocal_rank = scoring_owners._reciprocal_rank
_has_foreign_top_result = scoring_owners._has_foreign_top_result
_retrieval_failure_kind = scoring_owners._retrieval_failure_kind
_empty_retrieval_rank_metrics = scoring_owners._empty_retrieval_rank_metrics
_increment_failure_kind = scoring_owners._increment_failure_kind
_summarize_retrieval_rank_metrics = scoring_owners._summarize_retrieval_rank_metrics
_evaluate_retrieval_case = scoring_owners._evaluate_retrieval_case
_evaluate_answer_case = scoring_owners._evaluate_answer_case
_summarize_structural_checks = scoring_owners._summarize_structural_checks
_evaluate_structural_checks = scoring_owners._evaluate_structural_checks


def resolve_baseline_run_id(
    candidate_run_id: UUID,
    active_run_id: UUID | None,
    *,
    explicit_baseline_run_id: UUID | None = None,
) -> UUID | None:
    if explicit_baseline_run_id is not None:
        return None if explicit_baseline_run_id == candidate_run_id else explicit_baseline_run_id
    if active_run_id is None or active_run_id == candidate_run_id:
        return None
    return active_run_id


def _upsert_evaluation_row(
    session: Session,
    run: DocumentRun,
    *,
    corpus_name: str,
    fixture_name: str | None,
) -> DocumentRunEvaluation:
    existing = session.execute(
        select(DocumentRunEvaluation).where(
            DocumentRunEvaluation.run_id == run.id,
            DocumentRunEvaluation.corpus_name == corpus_name,
            DocumentRunEvaluation.eval_version == EVAL_VERSION,
        )
    ).scalar_one_or_none()
    if existing is not None:
        session.query(DocumentRunEvaluationQuery).filter(
            DocumentRunEvaluationQuery.evaluation_id == existing.id
        ).delete()
        session.delete(existing)
        session.flush()

    evaluation = DocumentRunEvaluation(
        id=uuid.uuid4(),
        run_id=run.id,
        corpus_name=corpus_name,
        fixture_name=fixture_name,
        eval_version=EVAL_VERSION,
        status="pending",
        summary_json={},
        created_at=utcnow(),
    )
    session.add(evaluation)
    session.flush()
    return evaluation


def evaluate_run(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None = None,
    corpus_path: Path | None = None,
    corpus_name: str = DEFAULT_CORPUS_NAME,
    refresh_auto_fixture: bool = True,
) -> DocumentRunEvaluation:
    active_corpus_path = corpus_path or _configured_manual_corpus_path() or _auto_corpus_path()
    baseline_run_id = resolve_baseline_run_id(
        run.id,
        document.active_run_id,
        explicit_baseline_run_id=baseline_run_id,
    )
    if baseline_run_id is not None:
        baseline_run = session.get(DocumentRun, baseline_run_id)
        if baseline_run is None:
            raise ValueError(f"Baseline run {baseline_run_id} does not exist.")
        if baseline_run.document_id != document.id:
            raise ValueError("Baseline run must belong to the same document as the candidate run.")

    evaluation = _upsert_evaluation_row(session, run, corpus_name=corpus_name, fixture_name=None)
    now = utcnow()
    fixture = None
    try:
        fixture = fixture_for_document(document, active_corpus_path)
        if fixture is None or (refresh_auto_fixture and fixture.kind == AUTO_FIXTURE_KIND):
            ensure_auto_evaluation_fixture(session, document, run)
            fixture = fixture_for_document(document, active_corpus_path)

        if fixture is None:
            evaluation.fixture_name = None
            evaluation.status = "skipped"
            evaluation.summary_json = {
                "status": "skipped",
                "reason": "No evaluation fixture matches the document identity.",
                "query_count": 0,
                "retrieval_query_count": 0,
                "answer_query_count": 0,
                "passed_queries": 0,
                "failed_queries": 0,
                "passed_retrieval_queries": 0,
                "failed_retrieval_queries": 0,
                "passed_answer_queries": 0,
                "failed_answer_queries": 0,
                "regressed_queries": 0,
                "improved_queries": 0,
                "stable_queries": 0,
                "retrieval_rank_metrics": _empty_retrieval_rank_metrics(),
                "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
            }
            evaluation.completed_at = now
            session.commit()
            return evaluation

        evaluation.fixture_name = fixture.name
        retrieval_batch = execute_retrieval_queries(
            session,
            document=document,
            run=run,
            evaluation_id=evaluation.id,
            baseline_run_id=baseline_run_id,
            queries=fixture.queries,
            created_at=now,
            search_documents_fn=search_documents,
            evaluate_retrieval_case_fn=_evaluate_retrieval_case,
        )
        answer_batch = execute_answer_queries(
            session,
            document=document,
            run=run,
            evaluation_id=evaluation.id,
            baseline_run_id=baseline_run_id,
            queries=fixture.answer_queries,
            created_at=now,
            evaluate_answer_case_fn=_evaluate_answer_case,
        )
        batch = EvaluationBatchResult().merge(retrieval_batch).merge(answer_batch)
        structural_summary = _evaluate_structural_checks(session, run, fixture.thresholds)
        retrieval_rank_metrics = _summarize_retrieval_rank_metrics(
            retrieval_batch.retrieval_outcomes
        )
        evaluation.status = "completed"
        evaluation.summary_json = build_completed_evaluation_summary(
            fixture_name=fixture.name,
            batch=batch,
            structural_summary=structural_summary,
            retrieval_rank_metrics=retrieval_rank_metrics,
            baseline_run_id=baseline_run_id,
        )
        evaluation.completed_at = now
        session.commit()
        return evaluation
    except Exception as exc:
        session.rollback()
        evaluation = _upsert_evaluation_row(
            session,
            run,
            corpus_name=corpus_name,
            fixture_name=getattr(fixture, "name", None),
        )
        evaluation.status = "failed"
        evaluation.error_message = str(exc)
        evaluation.summary_json = {
            "status": "failed",
            "fixture_name": getattr(fixture, "name", None),
            "reason": str(exc),
            "query_count": 0,
            "retrieval_query_count": 0,
            "answer_query_count": 0,
            "passed_queries": 0,
            "failed_queries": 0,
            "passed_retrieval_queries": 0,
            "failed_retrieval_queries": 0,
            "passed_answer_queries": 0,
            "failed_answer_queries": 0,
            "regressed_queries": 0,
            "improved_queries": 0,
            "stable_queries": 0,
            "retrieval_rank_metrics": _empty_retrieval_rank_metrics(),
            "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
        }
        evaluation.completed_at = now
        session.commit()
        return evaluation


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
