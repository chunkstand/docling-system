from __future__ import annotations

from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    get_storage_service,
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
    storage_file_response,
)
from app.api.errors import api_error
from app.db.session import get_db_session
from app.schemas.agent_tasks import (
    AgentTaskActionDefinitionResponse,
    AgentTaskAnalyticsSummaryResponse,
    AgentTaskApprovalRequest,
    AgentTaskApprovalTrendResponse,
    AgentTaskArtifactResponse,
    AgentTaskCostSummaryResponse,
    AgentTaskCostTrendResponse,
    AgentTaskCreateRequest,
    AgentTaskDecisionSignalResponse,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskPerformanceSummaryResponse,
    AgentTaskPerformanceTrendResponse,
    AgentTaskRecommendationSummaryResponse,
    AgentTaskRecommendationTrendResponse,
    AgentTaskRejectionRequest,
    AgentTaskSummaryResponse,
    AgentTaskTraceExportResponse,
    AgentTaskTrendResponse,
    AgentTaskValueDensityRowResponse,
    AgentTaskVerificationResponse,
    AgentTaskVerificationTrendResponse,
    AgentTaskWorkflowVersionSummaryResponse,
    TaskContextEnvelope,
)
from app.services.capabilities import agent_orchestration

router = APIRouter()

list_agent_task_action_definitions = agent_orchestration.list_agent_task_action_definitions
list_agent_tasks = agent_orchestration.list_agent_tasks
create_agent_task = agent_orchestration.create_agent_task
get_agent_task_detail = agent_orchestration.get_agent_task_detail
get_agent_task_context = agent_orchestration.get_agent_task_context
list_agent_task_outcomes = agent_orchestration.list_agent_task_outcomes
create_agent_task_outcome = agent_orchestration.create_agent_task_outcome
list_agent_task_artifacts = agent_orchestration.list_agent_task_artifacts
get_agent_task_artifact = agent_orchestration.get_agent_task_artifact
get_agent_task_verifications = agent_orchestration.get_agent_task_verifications
approve_agent_task = agent_orchestration.approve_agent_task
reject_agent_task = agent_orchestration.reject_agent_task
get_agent_task_analytics_summary = agent_orchestration.get_agent_task_analytics_summary
get_agent_task_trends = agent_orchestration.get_agent_task_trends
get_agent_verification_trends = agent_orchestration.get_agent_verification_trends
get_agent_approval_trends = agent_orchestration.get_agent_approval_trends
get_agent_task_recommendation_summary = agent_orchestration.get_agent_task_recommendation_summary
get_agent_task_recommendation_trends = agent_orchestration.get_agent_task_recommendation_trends
get_agent_task_cost_summary = agent_orchestration.get_agent_task_cost_summary
get_agent_task_cost_trends = agent_orchestration.get_agent_task_cost_trends
get_agent_task_performance_summary = agent_orchestration.get_agent_task_performance_summary
get_agent_task_performance_trends = agent_orchestration.get_agent_task_performance_trends
get_agent_task_value_density = agent_orchestration.get_agent_task_value_density
get_agent_task_decision_signals = agent_orchestration.get_agent_task_decision_signals
list_agent_task_workflow_summaries = agent_orchestration.list_agent_task_workflow_summaries
export_agent_task_traces = agent_orchestration.export_agent_task_traces


@router.get(
    "/agent-tasks/actions",
    response_model=list[AgentTaskActionDefinitionResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_actions() -> list[AgentTaskActionDefinitionResponse]:
    return list_agent_task_action_definitions()


@router.get(
    "/agent-tasks",
    response_model=list[AgentTaskSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_tasks(
    task_status: list[str] | None = Query(default=None, alias="status"),
    limit: int = 50,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskSummaryResponse]:
    return list_agent_tasks(session, statuses=task_status, limit=limit)


@router.post(
    "/agent-tasks",
    response_model=AgentTaskDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def create_agent_task_route(
    response: Response,
    payload: AgentTaskCreateRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    try:
        task_response = create_agent_task(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_agent_task_request",
            str(exc),
        ) from exc
    task_id = response_field(task_response, "task_id")
    if task_id is not None:
        response.headers["Location"] = f"/agent-tasks/{task_id}"
    return task_response


@router.get(
    "/agent-tasks/analytics/summary",
    response_model=AgentTaskAnalyticsSummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_analytics_summary(
    session: Session = Depends(get_db_session),
) -> AgentTaskAnalyticsSummaryResponse:
    return get_agent_task_analytics_summary(session)


@router.get(
    "/agent-tasks/analytics/trends",
    response_model=AgentTaskTrendResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_trends(
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskTrendResponse:
    return get_agent_task_trends(
        session,
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/verifications",
    response_model=AgentTaskVerificationTrendResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_verification_trends(
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskVerificationTrendResponse:
    return get_agent_verification_trends(
        session,
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/approvals",
    response_model=AgentTaskApprovalTrendResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_approval_trends(
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskApprovalTrendResponse:
    return get_agent_approval_trends(
        session,
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/recommendations",
    response_model=AgentTaskRecommendationSummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_recommendation_summary(
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskRecommendationSummaryResponse:
    return get_agent_task_recommendation_summary(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/recommendations/trends",
    response_model=AgentTaskRecommendationTrendResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_recommendation_trends(
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskRecommendationTrendResponse:
    return get_agent_task_recommendation_trends(
        session,
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/costs",
    response_model=AgentTaskCostSummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_cost_summary(
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskCostSummaryResponse:
    return get_agent_task_cost_summary(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/costs/trends",
    response_model=AgentTaskCostTrendResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_cost_trends(
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskCostTrendResponse:
    return get_agent_task_cost_trends(
        session,
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/performance",
    response_model=AgentTaskPerformanceSummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_performance_summary(
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskPerformanceSummaryResponse:
    return get_agent_task_performance_summary(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/performance/trends",
    response_model=AgentTaskPerformanceTrendResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_performance_trends(
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskPerformanceTrendResponse:
    return get_agent_task_performance_trends(
        session,
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
    )


@router.get(
    "/agent-tasks/analytics/value-density",
    response_model=list[AgentTaskValueDensityRowResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_value_density(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskValueDensityRowResponse]:
    return get_agent_task_value_density(session)


@router.get(
    "/agent-tasks/analytics/decision-signals",
    response_model=list[AgentTaskDecisionSignalResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_decision_signals(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskDecisionSignalResponse]:
    return get_agent_task_decision_signals(session)


@router.get(
    "/agent-tasks/analytics/workflow-versions",
    response_model=list[AgentTaskWorkflowVersionSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_workflow_summaries(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskWorkflowVersionSummaryResponse]:
    return list_agent_task_workflow_summaries(session)


@router.get(
    "/agent-tasks/traces/export",
    response_model=AgentTaskTraceExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_trace_export(
    limit: int = 50,
    workflow_version: str | None = None,
    task_type: str | None = None,
    session: Session = Depends(get_db_session),
) -> AgentTaskTraceExportResponse:
    return export_agent_task_traces(
        session,
        limit=limit,
        workflow_version=workflow_version,
        task_type=task_type,
    )


@router.get(
    "/agent-tasks/{task_id}",
    response_model=AgentTaskDetailResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_detail_route(
    task_id: UUID,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return get_agent_task_detail(session, task_id)


@router.get(
    "/agent-tasks/{task_id}/context",
    response_model=TaskContextEnvelope,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_context_route(
    task_id: UUID,
    format: str = "json",
    session: Session = Depends(get_db_session),
):
    context = get_agent_task_context(session, task_id)
    context_payload = context.model_dump(mode="json") if hasattr(context, "model_dump") else context
    if format == "json":
        return context
    if format == "yaml":
        return Response(
            content=yaml.safe_dump(context_payload, sort_keys=False, allow_unicode=True),
            media_type="application/yaml",
        )
    raise api_error(
        status.HTTP_400_BAD_REQUEST,
        "invalid_context_format",
        "Unsupported context format. Use 'json' or 'yaml'.",
        requested_format=format,
    )


@router.get(
    "/agent-tasks/{task_id}/outcomes",
    response_model=list[AgentTaskOutcomeResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_outcomes(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskOutcomeResponse]:
    return list_agent_task_outcomes(session, task_id, limit=limit)


@router.post(
    "/agent-tasks/{task_id}/outcomes",
    response_model=AgentTaskOutcomeResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def create_agent_task_outcome_route(
    task_id: UUID,
    payload: AgentTaskOutcomeCreateRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskOutcomeResponse:
    return create_agent_task_outcome(session, task_id, payload)


@router.get(
    "/agent-tasks/{task_id}/artifacts",
    response_model=list[AgentTaskArtifactResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_artifacts(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskArtifactResponse]:
    return list_agent_task_artifacts(session, task_id, limit=limit)


@router.get(
    "/agent-tasks/{task_id}/artifacts/{artifact_id}",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_artifact_route(
    task_id: UUID,
    artifact_id: UUID,
    session: Session = Depends(get_db_session),
):
    artifact = get_agent_task_artifact(session, task_id, artifact_id)
    file_response = storage_file_response(artifact.storage_path, media_type="application/json")
    if file_response.status_code != 404:
        return file_response
    return JSONResponse(artifact.payload_json or {})


@router.get(
    "/agent-tasks/{task_id}/verifications",
    response_model=list[AgentTaskVerificationResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_verifications_route(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskVerificationResponse]:
    return get_agent_task_verifications(session, task_id, limit=limit)


@router.get(
    "/agent-tasks/{task_id}/failure-artifact",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_failure_artifact(
    task_id: UUID,
    session: Session = Depends(get_db_session),
):
    get_agent_task_detail(session, task_id)
    return storage_file_response(
        get_storage_service().build_agent_task_failure_artifact_path(task_id),
        media_type="application/json",
        not_found_detail="Agent task failure artifact not found.",
        not_found_error_code="agent_task_failure_artifact_not_found",
        not_found_context={"task_id": str(task_id)},
    )


@router.post(
    "/agent-tasks/{task_id}/approve",
    response_model=AgentTaskDetailResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def approve_agent_task_route(
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return approve_agent_task(session, task_id, payload)


@router.post(
    "/agent-tasks/{task_id}/reject",
    response_model=AgentTaskDetailResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def reject_agent_task_route(
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return reject_agent_task(session, task_id, payload)
