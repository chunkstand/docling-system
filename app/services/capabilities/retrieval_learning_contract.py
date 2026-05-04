from __future__ import annotations

from typing import Protocol
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


class RetrievalLearningCapability(Protocol):
    def evaluate_retrieval_learning_candidate(
        self,
        session: Session,
        payload: RetrievalLearningCandidateEvaluationRequest,
    ) -> RetrievalLearningCandidateEvaluationResponse: ...

    def list_retrieval_learning_candidate_evaluations(
        self,
        session: Session,
        *,
        limit: int,
        retrieval_training_run_id: UUID | None = None,
        candidate_harness_name: str | None = None,
    ) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]: ...

    def get_retrieval_learning_candidate_evaluation_detail(
        self,
        session: Session,
        candidate_evaluation_id: UUID,
    ) -> RetrievalLearningCandidateEvaluationResponse: ...

    def create_retrieval_reranker_artifact(
        self,
        session: Session,
        payload: RetrievalRerankerArtifactRequest,
    ) -> RetrievalRerankerArtifactResponse: ...

    def list_retrieval_reranker_artifacts(
        self,
        session: Session,
        *,
        limit: int,
        retrieval_training_run_id: UUID | None = None,
        candidate_harness_name: str | None = None,
    ) -> list[RetrievalRerankerArtifactSummaryResponse]: ...

    def get_retrieval_reranker_artifact_detail(
        self,
        session: Session,
        artifact_id: UUID,
    ) -> RetrievalRerankerArtifactResponse: ...
