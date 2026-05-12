from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalLearningCandidateEvaluationResponse,
    RetrievalLearningCandidateEvaluationSummaryResponse,
    RetrievalRerankerArtifactRequest,
    RetrievalRerankerArtifactResponse,
    RetrievalRerankerArtifactSummaryResponse,
)
from app.services import retrieval_learning_artifacts as _retrieval_learning_artifacts
from app.services import retrieval_learning_candidates as _retrieval_learning_candidates
from app.services import retrieval_learning_datasets as _retrieval_learning_datasets
from app.services.search import get_search_harness
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_release_gate import record_search_harness_release_gate

RETRIEVAL_LEARNING_DATASET_SCHEMA = (
    _retrieval_learning_datasets.RETRIEVAL_LEARNING_DATASET_SCHEMA
)
RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION = (
    _retrieval_learning_datasets.RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION
)
RETRIEVAL_LEARNING_SOURCE_FEEDBACK = (
    _retrieval_learning_datasets.RETRIEVAL_LEARNING_SOURCE_FEEDBACK
)
RETRIEVAL_LEARNING_SOURCE_REPLAY = _retrieval_learning_datasets.RETRIEVAL_LEARNING_SOURCE_REPLAY
RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS = (
    _retrieval_learning_datasets.RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS
)
RETRIEVAL_LEARNING_SOURCE_TECHNICAL_REPORT_CLAIM_FEEDBACK = (
    _retrieval_learning_datasets.RETRIEVAL_LEARNING_SOURCE_TECHNICAL_REPORT_CLAIM_FEEDBACK
)
RETRIEVAL_LEARNING_SOURCES = _retrieval_learning_datasets.RETRIEVAL_LEARNING_SOURCES
RETRIEVAL_RERANKER_ARTIFACT_SCHEMA = (
    _retrieval_learning_artifacts.RETRIEVAL_RERANKER_ARTIFACT_SCHEMA
)
RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION = (
    _retrieval_learning_artifacts.RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION
)
RETRIEVAL_RERANKER_ARTIFACT_KIND = (
    _retrieval_learning_artifacts.RETRIEVAL_RERANKER_ARTIFACT_KIND
)


def materialize_retrieval_learning_dataset(
    session: Session,
    *,
    limit: int = 200,
    source_types: list[str] | tuple[str, ...] | None = None,
    set_name: str | None = None,
    created_by: str | None = None,
    search_harness_evaluation_id: UUID | None = None,
    search_harness_release_id: UUID | None = None,
) -> dict[str, object]:
    return _retrieval_learning_datasets.materialize_retrieval_learning_dataset(
        session,
        limit=limit,
        source_types=source_types,
        set_name=set_name,
        created_by=created_by,
        search_harness_evaluation_id=search_harness_evaluation_id,
        search_harness_release_id=search_harness_release_id,
    )


def evaluate_retrieval_learning_candidate(
    session: Session,
    request: RetrievalLearningCandidateEvaluationRequest,
) -> RetrievalLearningCandidateEvaluationResponse:
    return _retrieval_learning_candidates.evaluate_retrieval_learning_candidate(
        session,
        request,
        evaluate_search_harness_fn=evaluate_search_harness,
        record_search_harness_release_gate_fn=record_search_harness_release_gate,
    )


def list_retrieval_learning_candidate_evaluations(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]:
    return _retrieval_learning_candidates.list_retrieval_learning_candidate_evaluations(
        session,
        limit=limit,
        retrieval_training_run_id=retrieval_training_run_id,
        candidate_harness_name=candidate_harness_name,
    )


def get_retrieval_learning_candidate_evaluation_detail(
    session: Session,
    candidate_evaluation_id: UUID,
) -> RetrievalLearningCandidateEvaluationResponse:
    return _retrieval_learning_candidates.get_retrieval_learning_candidate_evaluation_detail(
        session,
        candidate_evaluation_id,
    )


def create_retrieval_reranker_artifact(
    session: Session,
    request: RetrievalRerankerArtifactRequest,
) -> RetrievalRerankerArtifactResponse:
    return _retrieval_learning_artifacts.create_retrieval_reranker_artifact(
        session,
        request,
        get_search_harness_fn=get_search_harness,
        evaluate_search_harness_fn=evaluate_search_harness,
        record_search_harness_release_gate_fn=record_search_harness_release_gate,
    )


def list_retrieval_reranker_artifacts(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalRerankerArtifactSummaryResponse]:
    return _retrieval_learning_artifacts.list_retrieval_reranker_artifacts(
        session,
        limit=limit,
        retrieval_training_run_id=retrieval_training_run_id,
        candidate_harness_name=candidate_harness_name,
    )


def get_retrieval_reranker_artifact_detail(
    session: Session,
    artifact_id: UUID,
) -> RetrievalRerankerArtifactResponse:
    return _retrieval_learning_artifacts.get_retrieval_reranker_artifact_detail(
        session,
        artifact_id,
    )
