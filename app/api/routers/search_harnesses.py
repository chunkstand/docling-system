from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
)
from app.api.errors import api_error
from app.api.routers.search_route_services import resolve_search_service
from app.db.session import get_db_session
from app.schemas.search import (
    SearchHarnessDescriptorResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSummaryResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseReadinessAssessmentRequest,
    SearchHarnessReleaseReadinessAssessmentResponse,
    SearchHarnessReleaseReadinessResponse,
    SearchHarnessReleaseResponse,
    SearchHarnessReleaseSummaryResponse,
    SearchHarnessResponse,
)
from app.services.capabilities import evaluation, retrieval

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
HarnessEvaluationLimitQuery = Annotated[int, Query(ge=1, le=200)]

list_search_harness_definitions = retrieval.list_search_harness_definitions
get_search_harness_descriptor = retrieval.get_search_harness_descriptor
list_search_harness_evaluations = retrieval.list_search_harness_evaluations
evaluate_search_harness = retrieval.evaluate_search_harness
get_search_harness_evaluation_detail = retrieval.get_search_harness_evaluation_detail
create_search_harness_release_gate = retrieval.create_search_harness_release_gate
list_search_harness_releases = retrieval.list_search_harness_releases
get_search_harness_release_detail = retrieval.get_search_harness_release_detail
get_search_harness_release_readiness = retrieval.get_search_harness_release_readiness
create_search_harness_release_readiness_assessment = (
    retrieval.create_search_harness_release_readiness_assessment
)
get_latest_search_harness_release_readiness_assessment = (
    retrieval.get_latest_search_harness_release_readiness_assessment
)
get_search_harness_release_readiness_assessment = (
    retrieval.get_search_harness_release_readiness_assessment
)
explain_search_harness_evaluation = evaluation.explain_search_harness_evaluation


@router.get(
    "/search/harnesses",
    response_model=list[SearchHarnessResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harnesses() -> list[SearchHarnessResponse]:
    return resolve_search_service(
        "list_search_harness_definitions",
        list_search_harness_definitions,
    )()


@router.get(
    "/search/harnesses/{harness_name}/descriptor",
    response_model=SearchHarnessDescriptorResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_descriptor(harness_name: str) -> SearchHarnessDescriptorResponse:
    try:
        return resolve_search_service(
            "get_search_harness_descriptor",
            get_search_harness_descriptor,
        )(harness_name)
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_not_found",
            str(exc),
            harness_name=harness_name,
        ) from exc


@router.get(
    "/search/harness-evaluations",
    response_model=list[SearchHarnessEvaluationSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_evaluations(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    candidate_harness_name: str | None = None,
) -> list[SearchHarnessEvaluationSummaryResponse]:
    return resolve_search_service(
        "list_search_harness_evaluations",
        list_search_harness_evaluations,
    )(
        session,
        limit=limit,
        candidate_harness_name=candidate_harness_name,
    )


@router.post(
    "/search/harness-evaluations",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_evaluation(
    response: Response,
    payload: SearchHarnessEvaluationRequest,
    session: DbSession,
) -> SearchHarnessEvaluationResponse:
    try:
        evaluation_response = resolve_search_service(
            "evaluate_search_harness",
            evaluate_search_harness,
        )(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_harness_evaluation",
            str(exc),
        ) from exc
    session.commit()
    evaluation_id = response_field(evaluation_response, "evaluation_id")
    if evaluation_id is not None:
        response.headers["Location"] = f"/search/harness-evaluations/{evaluation_id}"
    return evaluation_response


@router.get(
    "/search/harness-evaluations/{evaluation_id}",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_evaluation(
    evaluation_id: UUID,
    session: DbSession,
) -> SearchHarnessEvaluationResponse:
    return resolve_search_service(
        "get_search_harness_evaluation_detail",
        get_search_harness_evaluation_detail,
    )(session, evaluation_id)


@router.get(
    "/search/harness-evaluations/{evaluation_id}/explain",
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def explain_search_harness_evaluation_route(
    evaluation_id: UUID,
    session: DbSession,
) -> dict:
    return resolve_search_service(
        "explain_search_harness_evaluation",
        explain_search_harness_evaluation,
    )(session, evaluation_id)


@router.get(
    "/search/harness-releases",
    response_model=list[SearchHarnessReleaseSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_releases(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    candidate_harness_name: str | None = None,
    outcome: str | None = Query(default=None, pattern="^(passed|failed|error)$"),
) -> list[SearchHarnessReleaseSummaryResponse]:
    return resolve_search_service(
        "list_search_harness_releases",
        list_search_harness_releases,
    )(
        session,
        limit=limit,
        candidate_harness_name=candidate_harness_name,
        outcome=outcome,
    )


@router.post(
    "/search/harness-releases",
    response_model=SearchHarnessReleaseResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_release(
    response: Response,
    payload: SearchHarnessReleaseGateRequest,
    session: DbSession,
) -> SearchHarnessReleaseResponse:
    release_response = resolve_search_service(
        "create_search_harness_release_gate",
        create_search_harness_release_gate,
    )(session, payload)
    session.commit()
    release_id = response_field(release_response, "release_id")
    response.headers["Location"] = f"/search/harness-releases/{release_id}"
    return release_response


@router.get(
    "/search/harness-releases/{release_id}",
    response_model=SearchHarnessReleaseResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_release(
    release_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseResponse:
    return resolve_search_service(
        "get_search_harness_release_detail",
        get_search_harness_release_detail,
    )(session, release_id)


@router.get(
    "/search/harness-releases/{release_id}/readiness",
    response_model=SearchHarnessReleaseReadinessResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_release_readiness(
    release_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseReadinessResponse:
    return resolve_search_service(
        "get_search_harness_release_readiness",
        get_search_harness_release_readiness,
    )(session, release_id)


@router.post(
    "/search/harness-releases/{release_id}/readiness-assessments",
    response_model=SearchHarnessReleaseReadinessAssessmentResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_release_readiness_assessment_route(
    response: Response,
    release_id: UUID,
    payload: SearchHarnessReleaseReadinessAssessmentRequest,
    session: DbSession,
) -> SearchHarnessReleaseReadinessAssessmentResponse:
    assessment = resolve_search_service(
        "create_search_harness_release_readiness_assessment",
        create_search_harness_release_readiness_assessment,
    )(
        session,
        release_id,
        payload,
    )
    session.commit()
    assessment_id = response_field(assessment, "assessment_id")
    response.headers["Location"] = (
        f"/search/harness-releases/{release_id}/readiness-assessments/{assessment_id}"
    )
    return assessment


@router.get(
    "/search/harness-releases/{release_id}/readiness-assessments/latest",
    response_model=SearchHarnessReleaseReadinessAssessmentResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_search_harness_release_readiness_assessment(
    release_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseReadinessAssessmentResponse:
    return resolve_search_service(
        "get_latest_search_harness_release_readiness_assessment",
        get_latest_search_harness_release_readiness_assessment,
    )(session, release_id)


@router.get(
    "/search/harness-releases/{release_id}/readiness-assessments/{assessment_id}",
    response_model=SearchHarnessReleaseReadinessAssessmentResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_release_readiness_assessment(
    release_id: UUID,
    assessment_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseReadinessAssessmentResponse:
    return resolve_search_service(
        "get_search_harness_release_readiness_assessment",
        get_search_harness_release_readiness_assessment,
    )(
        session,
        release_id,
        assessment_id,
    )


__all__ = ["router"]
