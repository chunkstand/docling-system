from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
)
from app.api.routers.search_route_services import resolve_search_service
from app.db.session import get_db_session
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalLearningCandidateEvaluationResponse,
    RetrievalLearningCandidateEvaluationSummaryResponse,
    RetrievalRerankerArtifactRequest,
    RetrievalRerankerArtifactResponse,
    RetrievalRerankerArtifactSummaryResponse,
)
from app.services.capabilities import retrieval

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
HarnessEvaluationLimitQuery = Annotated[int, Query(ge=1, le=200)]

evaluate_retrieval_learning_candidate = retrieval.evaluate_retrieval_learning_candidate
list_retrieval_learning_candidate_evaluations = (
    retrieval.list_retrieval_learning_candidate_evaluations
)
get_retrieval_learning_candidate_evaluation_detail = (
    retrieval.get_retrieval_learning_candidate_evaluation_detail
)
create_retrieval_reranker_artifact = retrieval.create_retrieval_reranker_artifact
list_retrieval_reranker_artifacts = retrieval.list_retrieval_reranker_artifacts
get_retrieval_reranker_artifact_detail = retrieval.get_retrieval_reranker_artifact_detail


@router.get(
    "/search/retrieval-learning/candidate-evaluations",
    response_model=list[RetrievalLearningCandidateEvaluationSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_learning_candidate_evaluations(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]:
    return resolve_search_service(
        "list_retrieval_learning_candidate_evaluations",
        list_retrieval_learning_candidate_evaluations,
    )(
        session,
        limit=limit,
        retrieval_training_run_id=retrieval_training_run_id,
        candidate_harness_name=candidate_harness_name,
    )


@router.post(
    "/search/retrieval-learning/candidate-evaluations",
    response_model=RetrievalLearningCandidateEvaluationResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_retrieval_learning_candidate_evaluation(
    response: Response,
    payload: RetrievalLearningCandidateEvaluationRequest,
    session: DbSession,
) -> RetrievalLearningCandidateEvaluationResponse:
    candidate_response = resolve_search_service(
        "evaluate_retrieval_learning_candidate",
        evaluate_retrieval_learning_candidate,
    )(session, payload)
    session.commit()
    candidate_evaluation_id = response_field(candidate_response, "candidate_evaluation_id")
    response.headers["Location"] = (
        f"/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}"
    )
    return candidate_response


@router.get(
    "/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}",
    response_model=RetrievalLearningCandidateEvaluationResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_learning_candidate_evaluation(
    candidate_evaluation_id: UUID,
    session: DbSession,
) -> RetrievalLearningCandidateEvaluationResponse:
    return resolve_search_service(
        "get_retrieval_learning_candidate_evaluation_detail",
        get_retrieval_learning_candidate_evaluation_detail,
    )(
        session,
        candidate_evaluation_id,
    )


@router.get(
    "/search/retrieval-learning/reranker-artifacts",
    response_model=list[RetrievalRerankerArtifactSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_reranker_artifacts(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalRerankerArtifactSummaryResponse]:
    return resolve_search_service(
        "list_retrieval_reranker_artifacts",
        list_retrieval_reranker_artifacts,
    )(
        session,
        limit=limit,
        retrieval_training_run_id=retrieval_training_run_id,
        candidate_harness_name=candidate_harness_name,
    )


@router.post(
    "/search/retrieval-learning/reranker-artifacts",
    response_model=RetrievalRerankerArtifactResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_retrieval_reranker_artifact_route(
    response: Response,
    payload: RetrievalRerankerArtifactRequest,
    session: DbSession,
) -> RetrievalRerankerArtifactResponse:
    artifact = resolve_search_service(
        "create_retrieval_reranker_artifact",
        create_retrieval_reranker_artifact,
    )(session, payload)
    session.commit()
    artifact_id = response_field(artifact, "artifact_id")
    response.headers["Location"] = f"/search/retrieval-learning/reranker-artifacts/{artifact_id}"
    return artifact


@router.get(
    "/search/retrieval-learning/reranker-artifacts/{artifact_id}",
    response_model=RetrievalRerankerArtifactResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_reranker_artifact(
    artifact_id: UUID,
    session: DbSession,
) -> RetrievalRerankerArtifactResponse:
    return resolve_search_service(
        "get_retrieval_reranker_artifact_detail",
        get_retrieval_reranker_artifact_detail,
    )(session, artifact_id)


__all__ = ["router"]
