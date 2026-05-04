from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

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


class AgentOrchestrationAnalyticsCapability(Protocol):
    def get_agent_task_analytics_summary(
        self,
        session: Session,
    ) -> AgentTaskAnalyticsSummaryResponse: ...

    def get_agent_task_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskTrendResponse: ...

    def get_agent_verification_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskVerificationTrendResponse: ...

    def get_agent_approval_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskApprovalTrendResponse: ...

    def get_agent_task_recommendation_summary(
        self,
        session: Session,
        *,
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskRecommendationSummaryResponse: ...

    def get_agent_task_recommendation_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskRecommendationTrendResponse: ...

    def get_agent_task_cost_summary(
        self,
        session: Session,
        *,
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskCostSummaryResponse: ...

    def get_agent_task_cost_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskCostTrendResponse: ...

    def get_agent_task_performance_summary(
        self,
        session: Session,
        *,
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskPerformanceSummaryResponse: ...

    def get_agent_task_performance_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskPerformanceTrendResponse: ...

    def get_agent_task_value_density(
        self,
        session: Session,
    ) -> list[AgentTaskValueDensityRowResponse]: ...

    def get_agent_task_decision_signals(
        self,
        session: Session,
    ) -> list[AgentTaskDecisionSignalResponse]: ...

    def list_agent_task_workflow_summaries(
        self,
        session: Session,
    ) -> list[AgentTaskWorkflowVersionSummaryResponse]: ...

    def export_agent_task_traces(
        self,
        session: Session,
        *,
        limit: int = 50,
        workflow_version: str | None = None,
        task_type: str | None = None,
    ) -> AgentTaskTraceExportResponse: ...
