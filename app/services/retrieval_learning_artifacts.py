from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

import app.services.retrieval_learning_artifact_contracts as _contracts
import app.services.retrieval_learning_artifact_impacts as _impacts
import app.services.retrieval_learning_artifact_lifecycle as _lifecycle
import app.services.retrieval_learning_artifact_views as _views
import app.services.retrieval_learning_artifact_weights as _weights
from app.db.public.retrieval import RetrievalRerankerArtifact, RetrievalTrainingRun
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
    RetrievalRerankerArtifactResponse,
    RetrievalRerankerArtifactSummaryResponse,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
)

RETRIEVAL_RERANKER_ARTIFACT_SCHEMA = _contracts.RETRIEVAL_RERANKER_ARTIFACT_SCHEMA
RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION = (
    _contracts.RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION
)
RETRIEVAL_RERANKER_ARTIFACT_KIND = _contracts.RETRIEVAL_RERANKER_ARTIFACT_KIND


def reranker_artifact_not_found_error(artifact_id: UUID) -> HTTPException:
    return _contracts.reranker_artifact_not_found_error(artifact_id)


def candidate_request_from_artifact_request(
    request: RetrievalRerankerArtifactRequest,
) -> RetrievalLearningCandidateEvaluationRequest:
    return _weights.candidate_request_from_artifact_request(request)


def feature_weight_candidate(
    *,
    training_run: RetrievalTrainingRun,
    base_harness_name: str,
    candidate_harness_name: str,
    artifact_name: str,
    get_search_harness_fn: Callable[[str], Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return _weights.feature_weight_candidate(
        training_run=training_run,
        base_harness_name=base_harness_name,
        candidate_harness_name=candidate_harness_name,
        artifact_name=artifact_name,
        get_search_harness_fn=get_search_harness_fn,
    )


def change_impact_report(
    session: Session,
    *,
    artifact_id: UUID,
    artifact_payload: dict[str, Any],
    artifact_sha256: str,
    training_run: RetrievalTrainingRun,
    evaluation: SearchHarnessEvaluationResponse,
    release: SearchHarnessReleaseResponse,
) -> dict[str, Any]:
    return _impacts.change_impact_report(
        session,
        artifact_id=artifact_id,
        artifact_payload=artifact_payload,
        artifact_sha256=artifact_sha256,
        training_run=training_run,
        evaluation=evaluation,
        release=release,
    )


def to_reranker_artifact_summary(
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactSummaryResponse:
    return _views.to_reranker_artifact_summary(row)


def to_reranker_artifact_response(
    session: Session,
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactResponse:
    return _views.to_reranker_artifact_response(session, row)


def create_retrieval_reranker_artifact(
    session: Session,
    request: RetrievalRerankerArtifactRequest,
    *,
    get_search_harness_fn: Callable[[str], Any],
    evaluate_search_harness_fn: Callable[..., SearchHarnessEvaluationResponse],
    record_search_harness_release_gate_fn: Callable[..., SearchHarnessReleaseResponse],
) -> RetrievalRerankerArtifactResponse:
    return _lifecycle.create_retrieval_reranker_artifact(
        session,
        request,
        get_search_harness_fn=get_search_harness_fn,
        evaluate_search_harness_fn=evaluate_search_harness_fn,
        record_search_harness_release_gate_fn=record_search_harness_release_gate_fn,
    )


def list_retrieval_reranker_artifacts(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalRerankerArtifactSummaryResponse]:
    return _views.list_retrieval_reranker_artifacts(
        session,
        limit=limit,
        retrieval_training_run_id=retrieval_training_run_id,
        candidate_harness_name=candidate_harness_name,
    )


def get_retrieval_reranker_artifact_detail(
    session: Session,
    artifact_id: UUID,
) -> RetrievalRerankerArtifactResponse:
    return _views.get_retrieval_reranker_artifact_detail(session, artifact_id)
