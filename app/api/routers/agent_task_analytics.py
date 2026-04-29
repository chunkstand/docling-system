from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import require_api_capability
from app.api.routers.agent_task_route_services import service_from_parent
from app.db.session import get_db_session
from app.schemas.agent_tasks import (
    AgentTaskAnalyticsSummaryResponse,
    AgentTaskApprovalTrendResponse,
    AgentTaskCostSummaryResponse,
    AgentTaskCostTrendResponse,
    AgentTaskDecisionSignalResponse,
    AgentTaskPerformanceSummaryResponse,
    AgentTaskPerformanceTrendResponse,
    AgentTaskRecommendationSummaryResponse,
    AgentTaskRecommendationTrendResponse,
    AgentTaskTraceExportResponse,
    AgentTaskTrendResponse,
    AgentTaskValueDensityRowResponse,
    AgentTaskVerificationTrendResponse,
    AgentTaskWorkflowVersionSummaryResponse,
)
from app.services.capabilities import agent_orchestration

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]

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
    "/agent-tasks/analytics/summary",
    response_model=AgentTaskAnalyticsSummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_analytics_summary(
    session: DbSession,
) -> AgentTaskAnalyticsSummaryResponse:
    return service_from_parent(
        "get_agent_task_analytics_summary",
        get_agent_task_analytics_summary,
    )(session)


@router.get(
    "/agent-tasks/analytics/trends",
    response_model=AgentTaskTrendResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_trends(
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskTrendResponse:
    return service_from_parent("get_agent_task_trends", get_agent_task_trends)(
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskVerificationTrendResponse:
    return service_from_parent("get_agent_verification_trends", get_agent_verification_trends)(
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskApprovalTrendResponse:
    return service_from_parent("get_agent_approval_trends", get_agent_approval_trends)(
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
    session: DbSession,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskRecommendationSummaryResponse:
    return service_from_parent(
        "get_agent_task_recommendation_summary",
        get_agent_task_recommendation_summary,
    )(
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskRecommendationTrendResponse:
    return service_from_parent(
        "get_agent_task_recommendation_trends",
        get_agent_task_recommendation_trends,
    )(
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
    session: DbSession,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskCostSummaryResponse:
    return service_from_parent("get_agent_task_cost_summary", get_agent_task_cost_summary)(
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskCostTrendResponse:
    return service_from_parent("get_agent_task_cost_trends", get_agent_task_cost_trends)(
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
    session: DbSession,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskPerformanceSummaryResponse:
    return service_from_parent(
        "get_agent_task_performance_summary",
        get_agent_task_performance_summary,
    )(
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskPerformanceTrendResponse:
    return service_from_parent(
        "get_agent_task_performance_trends",
        get_agent_task_performance_trends,
    )(
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
    session: DbSession,
) -> list[AgentTaskValueDensityRowResponse]:
    return service_from_parent(
        "get_agent_task_value_density",
        get_agent_task_value_density,
    )(session)


@router.get(
    "/agent-tasks/analytics/decision-signals",
    response_model=list[AgentTaskDecisionSignalResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_decision_signals(
    session: DbSession,
) -> list[AgentTaskDecisionSignalResponse]:
    return service_from_parent(
        "get_agent_task_decision_signals",
        get_agent_task_decision_signals,
    )(session)


@router.get(
    "/agent-tasks/analytics/workflow-versions",
    response_model=list[AgentTaskWorkflowVersionSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_workflow_summaries(
    session: DbSession,
) -> list[AgentTaskWorkflowVersionSummaryResponse]:
    return service_from_parent(
        "list_agent_task_workflow_summaries",
        list_agent_task_workflow_summaries,
    )(session)


@router.get(
    "/agent-tasks/traces/export",
    response_model=AgentTaskTraceExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_trace_export(
    session: DbSession,
    limit: int = 50,
    workflow_version: str | None = None,
    task_type: str | None = None,
) -> AgentTaskTraceExportResponse:
    return service_from_parent("export_agent_task_traces", export_agent_task_traces)(
        session,
        limit=limit,
        workflow_version=workflow_version,
        task_type=task_type,
    )


__all__ = ["router"]
