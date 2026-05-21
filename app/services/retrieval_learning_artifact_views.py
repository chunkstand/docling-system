from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.retrieval import RetrievalLearningCandidateEvaluation, RetrievalRerankerArtifact
from app.schemas.search import (
    RetrievalRerankerArtifactResponse,
    RetrievalRerankerArtifactSummaryResponse,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
)
from app.services.retrieval_learning_artifact_contracts import (
    reranker_artifact_not_found_error,
)
from app.services.retrieval_learning_candidates import (
    candidate_not_found_error,
    to_candidate_response,
)


def to_reranker_artifact_summary(
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactSummaryResponse:
    return RetrievalRerankerArtifactSummaryResponse(
        artifact_id=row.id,
        retrieval_training_run_id=row.retrieval_training_run_id,
        judgment_set_id=row.judgment_set_id,
        retrieval_learning_candidate_evaluation_id=(
            row.retrieval_learning_candidate_evaluation_id
        ),
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        semantic_governance_event_id=row.semantic_governance_event_id,
        artifact_kind=row.artifact_kind,
        artifact_name=row.artifact_name,
        artifact_version=row.artifact_version,
        status=row.status,
        gate_outcome=row.gate_outcome,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        source_types=list(row.source_types_json or []),
        limit=row.limit,
        training_dataset_sha256=row.training_dataset_sha256,
        training_example_count=row.training_example_count,
        positive_count=row.positive_count,
        negative_count=row.negative_count,
        missing_count=row.missing_count,
        hard_negative_count=row.hard_negative_count,
        thresholds=row.thresholds_json or {},
        metrics=row.metrics_json or {},
        reasons=list(row.reasons_json or []),
        artifact_sha256=row.artifact_sha256,
        change_impact_sha256=row.change_impact_sha256,
        created_by=row.created_by,
        review_note=row.review_note,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def to_reranker_artifact_response(
    session: Session,
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactResponse:
    summary = to_reranker_artifact_summary(row)
    candidate = session.get(
        RetrievalLearningCandidateEvaluation,
        row.retrieval_learning_candidate_evaluation_id,
    )
    if candidate is None:
        raise candidate_not_found_error(row.retrieval_learning_candidate_evaluation_id)
    release = None
    if row.search_harness_release_id is not None and row.release_snapshot_json:
        release = SearchHarnessReleaseResponse.model_validate(row.release_snapshot_json)
    return RetrievalRerankerArtifactResponse(
        **summary.model_dump(),
        feature_weights=row.feature_weights_json or {},
        harness_overrides=row.harness_overrides_json or {},
        artifact=row.artifact_payload_json or {},
        change_impact_report=row.change_impact_report_json or {},
        evaluation=SearchHarnessEvaluationResponse.model_validate(
            row.evaluation_snapshot_json or {}
        ),
        release=release,
        candidate_evaluation=to_candidate_response(candidate),
    )


def list_retrieval_reranker_artifacts(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalRerankerArtifactSummaryResponse]:
    statement = select(RetrievalRerankerArtifact).order_by(
        RetrievalRerankerArtifact.created_at.desc()
    )
    if retrieval_training_run_id is not None:
        statement = statement.where(
            RetrievalRerankerArtifact.retrieval_training_run_id
            == retrieval_training_run_id
        )
    if candidate_harness_name:
        statement = statement.where(
            RetrievalRerankerArtifact.candidate_harness_name == candidate_harness_name
        )
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [to_reranker_artifact_summary(row) for row in rows]


def get_retrieval_reranker_artifact_detail(
    session: Session,
    artifact_id: UUID,
) -> RetrievalRerankerArtifactResponse:
    row = session.get(RetrievalRerankerArtifact, artifact_id)
    if row is None:
        raise reranker_artifact_not_found_error(artifact_id)
    return to_reranker_artifact_response(session, row)
