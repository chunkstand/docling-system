from __future__ import annotations

from typing import Annotated
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import require_api_capability, require_api_key_for_mutations
from app.api.errors import api_error
from app.db.session import get_db_session
from app.schemas.eval_workbench import (
    EvalFailureCaseInspectionResponse,
    EvalFailureCaseRefreshResponse,
    EvalFailureCaseResponse,
    EvalObservationResponse,
    EvalWorkbenchResponse,
)
from app.schemas.quality import (
    QualityEvaluationCandidateResponse,
    QualityEvaluationStatusResponse,
    QualityFailuresResponse,
    QualitySummaryResponse,
    QualityTrendsResponse,
)
from app.services.capabilities import evaluation
from app.services.quality import (
    get_quality_failures,
    get_quality_summary,
    get_quality_trends,
    list_quality_eval_candidates,
    list_quality_evaluations,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
EvalFailureStatusQuery = Annotated[list[str] | None, Query(alias="status")]
EvalLimitQuery = Annotated[int, Query(ge=1, le=200)]
EvalWorkbenchLimitQuery = Annotated[int, Query(ge=1, le=100)]

refresh_eval_failure_cases = evaluation.refresh_eval_failure_cases
get_eval_workbench = evaluation.get_eval_workbench
list_eval_observations = evaluation.list_eval_observations
list_eval_failure_cases = evaluation.list_eval_failure_cases
get_eval_failure_case = evaluation.get_eval_failure_case
inspect_eval_failure_case = evaluation.inspect_eval_failure_case


@router.get(
    "/quality/summary",
    response_model=QualitySummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.QUALITY_READ))],
)
def read_quality_summary(session: DbSession) -> QualitySummaryResponse:
    return get_quality_summary(session)


@router.get(
    "/quality/failures",
    response_model=QualityFailuresResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.QUALITY_READ))],
)
def read_quality_failures(session: DbSession) -> QualityFailuresResponse:
    return get_quality_failures(session)


@router.get(
    "/quality/evaluations",
    response_model=list[QualityEvaluationStatusResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.QUALITY_READ))],
)
def read_quality_evaluations(
    session: DbSession,
) -> list[QualityEvaluationStatusResponse]:
    return list_quality_evaluations(session)


@router.get(
    "/quality/eval-candidates",
    response_model=list[QualityEvaluationCandidateResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.QUALITY_READ))],
)
def read_quality_eval_candidates(
    session: DbSession,
    limit: int = 12,
    include_resolved: bool = False,
) -> list[QualityEvaluationCandidateResponse]:
    return list_quality_eval_candidates(
        session,
        limit=limit,
        include_resolved=include_resolved,
    )


@router.get(
    "/quality/trends",
    response_model=QualityTrendsResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.QUALITY_READ))],
)
def read_quality_trends(session: DbSession) -> QualityTrendsResponse:
    return get_quality_trends(session)


@router.post(
    "/eval/failure-cases/refresh",
    response_model=EvalFailureCaseRefreshResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def refresh_eval_failure_cases_route(
    session: DbSession,
    limit: EvalLimitQuery = 50,
    include_resolved: bool = False,
) -> EvalFailureCaseRefreshResponse:
    response = refresh_eval_failure_cases(
        session,
        limit=limit,
        include_resolved=include_resolved,
    )
    session.commit()
    return response


@router.get(
    "/eval/workbench",
    response_model=EvalWorkbenchResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_eval_workbench(
    session: DbSession,
    limit: EvalWorkbenchLimitQuery = 25,
) -> EvalWorkbenchResponse:
    return get_eval_workbench(session, limit=limit)


@router.get(
    "/eval/observations",
    response_model=list[EvalObservationResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_eval_observations(
    session: DbSession,
    limit: EvalLimitQuery = 50,
) -> list[EvalObservationResponse]:
    return list_eval_observations(session, limit=limit)


@router.get(
    "/eval/failure-cases",
    response_model=list[EvalFailureCaseResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_eval_failure_cases(
    session: DbSession,
    case_status: EvalFailureStatusQuery = None,
    include_resolved: bool = False,
    limit: EvalLimitQuery = 50,
) -> list[EvalFailureCaseResponse]:
    return list_eval_failure_cases(
        session,
        status_filter=case_status,
        include_resolved=include_resolved,
        limit=limit,
    )


@router.get(
    "/eval/failure-cases/{case_id}",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_eval_failure_case(
    case_id: UUID,
    session: DbSession,
    format: str = "json",
):
    case = get_eval_failure_case(session, case_id)
    case_payload = case.model_dump(mode="json") if hasattr(case, "model_dump") else case
    if format == "json":
        return case
    if format == "yaml":
        return Response(
            content=yaml.safe_dump(case_payload, sort_keys=False),
            media_type="application/yaml",
        )
    raise api_error(
        status.HTTP_400_BAD_REQUEST,
        "invalid_eval_failure_case_format",
        "Unsupported eval failure case format. Use 'json' or 'yaml'.",
        requested_format=format,
    )


@router.get(
    "/eval/failure-cases/{case_id}/inspect",
    response_model=EvalFailureCaseInspectionResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def inspect_eval_failure_case_route(
    case_id: UUID,
    session: DbSession,
) -> EvalFailureCaseInspectionResponse:
    return inspect_eval_failure_case(session, case_id)
