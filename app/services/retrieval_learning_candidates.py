from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.json_utils import canonical_json_value as _json_payload
from app.core.time import utcnow
from app.db.public.retrieval import (
    RetrievalLearningCandidateEvaluation,
    RetrievalLearningCandidateStatus,
    RetrievalTrainingRun,
    RetrievalTrainingRunStatus,
)
from app.db.public.semantic_memory import SemanticGovernanceEventKind
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalLearningCandidateEvaluationResponse,
    RetrievalLearningCandidateEvaluationSummaryResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseResponse,
)
from app.services.semantic_governance import record_semantic_governance_event


def candidate_not_found_error(candidate_evaluation_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_learning_candidate_evaluation_not_found",
        "Retrieval learning candidate evaluation not found.",
        candidate_evaluation_id=str(candidate_evaluation_id),
    )


def thresholds_from_candidate_request(
    request: RetrievalLearningCandidateEvaluationRequest,
) -> dict[str, Any]:
    return {
        "max_total_regressed_count": request.max_total_regressed_count,
        "max_mrr_drop": request.max_mrr_drop,
        "max_zero_result_count_increase": request.max_zero_result_count_increase,
        "max_foreign_top_result_count_increase": (
            request.max_foreign_top_result_count_increase
        ),
        "min_total_shared_query_count": request.min_total_shared_query_count,
    }


def _latest_completed_training_run(session: Session) -> RetrievalTrainingRun | None:
    return session.scalar(
        select(RetrievalTrainingRun)
        .where(RetrievalTrainingRun.status == RetrievalTrainingRunStatus.COMPLETED.value)
        .order_by(RetrievalTrainingRun.created_at.desc())
        .limit(1)
    )


def resolve_training_run(
    session: Session,
    retrieval_training_run_id: UUID | None,
) -> RetrievalTrainingRun:
    if retrieval_training_run_id is not None:
        training_run = session.get(RetrievalTrainingRun, retrieval_training_run_id)
    else:
        training_run = _latest_completed_training_run(session)
    if training_run is None:
        context = {}
        if retrieval_training_run_id is not None:
            context["retrieval_training_run_id"] = str(retrieval_training_run_id)
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "retrieval_training_run_not_found",
            "Retrieval training run not found.",
            **context,
        )
    if training_run.status != RetrievalTrainingRunStatus.COMPLETED.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "retrieval_training_run_not_completed",
            "Retrieval training run is not completed.",
            retrieval_training_run_id=str(training_run.id),
            status=training_run.status,
        )
    if training_run.example_count <= 0:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "retrieval_training_run_empty",
            "Retrieval training run has no examples.",
            retrieval_training_run_id=str(training_run.id),
        )
    return training_run


def learning_candidate_package(
    *,
    training_run: RetrievalTrainingRun,
    evaluation: SearchHarnessEvaluationResponse,
    release: SearchHarnessReleaseResponse,
    request: RetrievalLearningCandidateEvaluationRequest,
) -> dict[str, Any]:
    return _json_payload(
        {
            "schema_name": "retrieval_learning_candidate_package",
            "schema_version": "1.0",
            "retrieval_training_run": {
                "retrieval_training_run_id": training_run.id,
                "judgment_set_id": training_run.judgment_set_id,
                "training_dataset_sha256": training_run.training_dataset_sha256,
                "training_example_count": training_run.example_count,
                "positive_count": training_run.positive_count,
                "negative_count": training_run.negative_count,
                "missing_count": training_run.missing_count,
                "hard_negative_count": training_run.hard_negative_count,
                "summary": training_run.summary_json or {},
            },
            "candidate_request": {
                "candidate_harness_name": request.candidate_harness_name,
                "baseline_harness_name": request.baseline_harness_name,
                "source_types": list(request.source_types),
                "limit": request.limit,
                "thresholds": thresholds_from_candidate_request(request),
                "requested_by": request.requested_by,
                "review_note": request.review_note,
            },
            "evaluation": evaluation.model_dump(mode="json"),
            "release": release.model_dump(mode="json"),
        }
    )


def record_candidate_governance_event(
    session: Session,
    *,
    row: RetrievalLearningCandidateEvaluation,
    training_run: RetrievalTrainingRun,
) -> None:
    event = record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.RETRIEVAL_LEARNING_CANDIDATE_EVALUATED.value,
        governance_scope=f"retrieval_learning:{training_run.id}",
        subject_table="retrieval_learning_candidate_evaluations",
        subject_id=row.id,
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        event_payload={
            "retrieval_learning_candidate_evaluation": {
                "candidate_evaluation_id": str(row.id),
                "retrieval_training_run_id": str(training_run.id),
                "judgment_set_id": str(training_run.judgment_set_id),
                "training_dataset_sha256": row.training_dataset_sha256,
                "training_example_count": row.training_example_count,
                "search_harness_evaluation_id": str(row.search_harness_evaluation_id),
                "search_harness_release_id": (
                    str(row.search_harness_release_id)
                    if row.search_harness_release_id is not None
                    else None
                ),
                "baseline_harness_name": row.baseline_harness_name,
                "candidate_harness_name": row.candidate_harness_name,
                "source_types": list(row.source_types_json or []),
                "limit": row.limit,
                "status": row.status,
                "gate_outcome": row.gate_outcome,
                "metrics": row.metrics_json or {},
                "thresholds": row.thresholds_json or {},
                "learning_package_sha256": row.learning_package_sha256,
            }
        },
        deduplication_key=(
            f"retrieval_learning_candidate_evaluated:{row.id}:"
            f"{row.learning_package_sha256}"
        ),
        created_by=row.created_by,
    )
    row.semantic_governance_event_id = event.id
    session.flush()


def create_candidate_evaluation_row(
    session: Session,
    *,
    training_run: RetrievalTrainingRun,
    evaluation: SearchHarnessEvaluationResponse,
    release: SearchHarnessReleaseResponse,
    baseline_harness_name: str,
    candidate_harness_name: str,
    source_types: list[str],
    limit: int,
    thresholds: dict[str, Any],
    details: dict[str, Any],
    learning_package_sha256: str,
    created_by: str | None,
    review_note: str | None,
    created_at: datetime | None = None,
) -> RetrievalLearningCandidateEvaluation:
    created_at = created_at or utcnow()
    status_value = (
        RetrievalLearningCandidateStatus.COMPLETED.value
        if evaluation.status == "completed"
        else RetrievalLearningCandidateStatus.FAILED.value
    )
    row = RetrievalLearningCandidateEvaluation(
        id=uuid.uuid4(),
        retrieval_training_run_id=training_run.id,
        judgment_set_id=training_run.judgment_set_id,
        search_harness_evaluation_id=evaluation.evaluation_id,
        search_harness_release_id=release.release_id,
        training_dataset_sha256=training_run.training_dataset_sha256,
        training_example_count=training_run.example_count,
        positive_count=training_run.positive_count,
        negative_count=training_run.negative_count,
        missing_count=training_run.missing_count,
        hard_negative_count=training_run.hard_negative_count,
        baseline_harness_name=baseline_harness_name,
        candidate_harness_name=candidate_harness_name,
        source_types_json=list(source_types),
        limit=limit,
        status=status_value,
        gate_outcome=release.outcome,
        thresholds_json=thresholds,
        metrics_json=release.metrics,
        reasons_json=list(release.reasons),
        evaluation_snapshot_json=evaluation.model_dump(mode="json"),
        release_snapshot_json=release.model_dump(mode="json"),
        details_json=details,
        learning_package_sha256=learning_package_sha256,
        created_by=created_by,
        review_note=review_note,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(row)
    session.flush()
    if training_run.search_harness_evaluation_id is None:
        training_run.search_harness_evaluation_id = evaluation.evaluation_id
    if training_run.search_harness_release_id is None:
        training_run.search_harness_release_id = release.release_id
    record_candidate_governance_event(
        session,
        row=row,
        training_run=training_run,
    )
    return row


def to_candidate_summary(
    row: RetrievalLearningCandidateEvaluation,
) -> RetrievalLearningCandidateEvaluationSummaryResponse:
    return RetrievalLearningCandidateEvaluationSummaryResponse(
        candidate_evaluation_id=row.id,
        retrieval_training_run_id=row.retrieval_training_run_id,
        judgment_set_id=row.judgment_set_id,
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        semantic_governance_event_id=row.semantic_governance_event_id,
        training_dataset_sha256=row.training_dataset_sha256,
        training_example_count=row.training_example_count,
        positive_count=row.positive_count,
        negative_count=row.negative_count,
        missing_count=row.missing_count,
        hard_negative_count=row.hard_negative_count,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        source_types=list(row.source_types_json or []),
        limit=row.limit,
        status=row.status,
        gate_outcome=row.gate_outcome,
        thresholds=row.thresholds_json or {},
        metrics=row.metrics_json or {},
        reasons=list(row.reasons_json or []),
        learning_package_sha256=row.learning_package_sha256,
        created_by=row.created_by,
        review_note=row.review_note,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def to_candidate_response(
    row: RetrievalLearningCandidateEvaluation,
) -> RetrievalLearningCandidateEvaluationResponse:
    summary = to_candidate_summary(row)
    release = None
    if row.search_harness_release_id is not None and row.release_snapshot_json:
        release = SearchHarnessReleaseResponse.model_validate(row.release_snapshot_json)
    return RetrievalLearningCandidateEvaluationResponse(
        **summary.model_dump(),
        details=row.details_json or {},
        evaluation=SearchHarnessEvaluationResponse.model_validate(
            row.evaluation_snapshot_json or {}
        ),
        release=release,
    )


def evaluate_retrieval_learning_candidate(
    session: Session,
    request: RetrievalLearningCandidateEvaluationRequest,
    *,
    evaluate_search_harness_fn: Callable[..., SearchHarnessEvaluationResponse],
    record_search_harness_release_gate_fn: Callable[..., SearchHarnessReleaseResponse],
) -> RetrievalLearningCandidateEvaluationResponse:
    training_run = resolve_training_run(session, request.retrieval_training_run_id)
    evaluation = evaluate_search_harness_fn(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=request.candidate_harness_name,
            baseline_harness_name=request.baseline_harness_name,
            source_types=request.source_types,
            limit=request.limit,
        ),
    )
    if evaluation.evaluation_id is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "search_harness_evaluation_missing_id",
            "Learning candidates require a durable search harness evaluation.",
        )
    gate_request = SearchHarnessReleaseGateRequest(
        evaluation_id=evaluation.evaluation_id,
        max_total_regressed_count=request.max_total_regressed_count,
        max_mrr_drop=request.max_mrr_drop,
        max_zero_result_count_increase=request.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=request.max_foreign_top_result_count_increase,
        min_total_shared_query_count=request.min_total_shared_query_count,
        requested_by=request.requested_by,
        review_note=request.review_note,
    )
    release = record_search_harness_release_gate_fn(
        session,
        evaluation,
        gate_request,
        requested_by=request.requested_by,
        review_note=request.review_note,
    )
    package = learning_candidate_package(
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        request=request,
    )
    row = create_candidate_evaluation_row(
        session,
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types=list(request.source_types),
        limit=request.limit,
        thresholds=thresholds_from_candidate_request(request),
        details={
            "schema_name": "retrieval_learning_candidate_evaluation_details",
            "schema_version": "1.0",
            "learning_loop_stage": "training_dataset_to_harness_release_gate",
            "training_dataset_summary": training_run.summary_json or {},
            "release_gate": {
                "outcome": release.outcome,
                "metrics": release.metrics,
                "reasons": release.reasons,
                "details": release.details,
            },
        },
        learning_package_sha256=_payload_sha256(package),
        created_by=request.requested_by,
        review_note=request.review_note,
    )
    return to_candidate_response(row)


def list_retrieval_learning_candidate_evaluations(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]:
    statement = select(RetrievalLearningCandidateEvaluation).order_by(
        RetrievalLearningCandidateEvaluation.created_at.desc()
    )
    if retrieval_training_run_id is not None:
        statement = statement.where(
            RetrievalLearningCandidateEvaluation.retrieval_training_run_id
            == retrieval_training_run_id
        )
    if candidate_harness_name:
        statement = statement.where(
            RetrievalLearningCandidateEvaluation.candidate_harness_name
            == candidate_harness_name
        )
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [to_candidate_summary(row) for row in rows]


def get_retrieval_learning_candidate_evaluation_detail(
    session: Session,
    candidate_evaluation_id: UUID,
) -> RetrievalLearningCandidateEvaluationResponse:
    row = session.get(RetrievalLearningCandidateEvaluation, candidate_evaluation_id)
    if row is None:
        raise candidate_not_found_error(candidate_evaluation_id)
    return to_candidate_response(row)
