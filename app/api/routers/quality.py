from __future__ import annotations

from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

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
from app.services.eval_workbench import (
    get_eval_failure_case,
    get_eval_workbench,
    inspect_eval_failure_case,
    list_eval_failure_cases,
    list_eval_observations,
    refresh_eval_failure_cases,
)
from app.services.quality import (
    get_quality_failures,
    get_quality_summary,
    get_quality_trends,
    list_quality_eval_candidates,
    list_quality_evaluations,
)

router = APIRouter()


@router.get(
    "/quality/summary",
    response_model=QualitySummaryResponse,
    dependencies=[Depends(require_api_capability("quality:read"))],
)
def read_quality_summary(session: Session = Depends(get_db_session)) -> QualitySummaryResponse:
    return get_quality_summary(session)


@router.get(
    "/quality/failures",
    response_model=QualityFailuresResponse,
    dependencies=[Depends(require_api_capability("quality:read"))],
)
def read_quality_failures(session: Session = Depends(get_db_session)) -> QualityFailuresResponse:
    return get_quality_failures(session)


@router.get(
    "/quality/evaluations",
    response_model=list[QualityEvaluationStatusResponse],
    dependencies=[Depends(require_api_capability("quality:read"))],
)
def read_quality_evaluations(
    session: Session = Depends(get_db_session),
) -> list[QualityEvaluationStatusResponse]:
    return list_quality_evaluations(session)


@router.get(
    "/quality/eval-candidates",
    response_model=list[QualityEvaluationCandidateResponse],
    dependencies=[Depends(require_api_capability("quality:read"))],
)
def read_quality_eval_candidates(
    limit: int = 12,
    include_resolved: bool = False,
    session: Session = Depends(get_db_session),
) -> list[QualityEvaluationCandidateResponse]:
    return list_quality_eval_candidates(
        session,
        limit=limit,
        include_resolved=include_resolved,
    )


@router.get(
    "/quality/trends",
    response_model=QualityTrendsResponse,
    dependencies=[Depends(require_api_capability("quality:read"))],
)
def read_quality_trends(session: Session = Depends(get_db_session)) -> QualityTrendsResponse:
    return get_quality_trends(session)


@router.post(
    "/eval/failure-cases/refresh",
    response_model=EvalFailureCaseRefreshResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("agent_tasks:write")),
    ],
)
def refresh_eval_failure_cases_route(
    limit: int = Query(default=50, ge=1, le=200),
    include_resolved: bool = False,
    session: Session = Depends(get_db_session),
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
    dependencies=[Depends(require_api_capability("agent_tasks:read"))],
)
def read_eval_workbench(
    limit: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_db_session),
) -> EvalWorkbenchResponse:
    return get_eval_workbench(session, limit=limit)


@router.get(
    "/eval/observations",
    response_model=list[EvalObservationResponse],
    dependencies=[Depends(require_api_capability("agent_tasks:read"))],
)
def read_eval_observations(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
) -> list[EvalObservationResponse]:
    return list_eval_observations(session, limit=limit)


@router.get(
    "/eval/failure-cases",
    response_model=list[EvalFailureCaseResponse],
    dependencies=[Depends(require_api_capability("agent_tasks:read"))],
)
def read_eval_failure_cases(
    case_status: list[str] | None = Query(default=None, alias="status"),
    include_resolved: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
) -> list[EvalFailureCaseResponse]:
    return list_eval_failure_cases(
        session,
        status_filter=case_status,
        include_resolved=include_resolved,
        limit=limit,
    )


@router.get(
    "/eval/failure-cases/{case_id}",
    dependencies=[Depends(require_api_capability("agent_tasks:read"))],
)
def read_eval_failure_case(
    case_id: UUID,
    format: str = "json",
    session: Session = Depends(get_db_session),
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
    dependencies=[Depends(require_api_capability("agent_tasks:read"))],
)
def inspect_eval_failure_case_route(
    case_id: UUID,
    session: Session = Depends(get_db_session),
) -> EvalFailureCaseInspectionResponse:
    return inspect_eval_failure_case(session, case_id)
