from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

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
from app.services import (
    agent_task_artifacts,
    agent_task_context,
    agent_task_verifications,
    agent_tasks,
    evidence,
)
from app.services import agent_task_worker as worker_service
from app.services.storage import StorageService


class AgentOrchestrationCapability(Protocol):
    def list_agent_task_action_definitions(self) -> list[AgentTaskActionDefinitionResponse]: ...

    def list_agent_tasks(
        self,
        session: Session,
        *,
        statuses: list[str] | None = None,
        limit: int = 50,
    ) -> list[AgentTaskSummaryResponse]: ...

    def create_agent_task(
        self,
        session: Session,
        payload: AgentTaskCreateRequest,
    ) -> AgentTaskDetailResponse: ...

    def get_agent_task_detail(self, session: Session, task_id: UUID) -> AgentTaskDetailResponse: ...

    def get_agent_task_context(self, session: Session, task_id: UUID) -> TaskContextEnvelope: ...

    def get_agent_task_audit_bundle(self, session: Session, task_id: UUID) -> dict: ...

    def get_agent_task_evidence_manifest(self, session: Session, task_id: UUID) -> dict: ...

    def get_agent_task_evidence_trace(self, session: Session, task_id: UUID) -> dict: ...

    def get_agent_task_provenance_export(
        self,
        session: Session,
        task_id: UUID,
        *,
        storage_service: StorageService | None = None,
    ) -> dict: ...

    def list_agent_task_outcomes(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskOutcomeResponse]: ...

    def create_agent_task_outcome(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskOutcomeCreateRequest,
    ) -> AgentTaskOutcomeResponse: ...

    def list_agent_task_artifacts(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskArtifactResponse]: ...

    def get_agent_task_artifact(
        self,
        session: Session,
        task_id: UUID,
        artifact_id: UUID,
    ) -> AgentTaskArtifactResponse: ...

    def get_agent_task_verifications(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskVerificationResponse]: ...

    def approve_agent_task(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskApprovalRequest,
    ) -> AgentTaskDetailResponse: ...

    def reject_agent_task(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskRejectionRequest,
    ) -> AgentTaskDetailResponse: ...

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

    def run_worker_loop(self) -> None: ...


class ServicesAgentOrchestrationCapability:
    def list_agent_task_action_definitions(self) -> list[AgentTaskActionDefinitionResponse]:
        return agent_tasks.list_agent_task_action_definitions()

    def list_agent_tasks(
        self,
        session: Session,
        *,
        statuses: list[str] | None = None,
        limit: int = 50,
    ) -> list[AgentTaskSummaryResponse]:
        return agent_tasks.list_agent_tasks(session, statuses=statuses, limit=limit)

    def create_agent_task(
        self,
        session: Session,
        payload: AgentTaskCreateRequest,
    ) -> AgentTaskDetailResponse:
        return agent_tasks.create_agent_task(session, payload)

    def get_agent_task_detail(self, session: Session, task_id: UUID) -> AgentTaskDetailResponse:
        return agent_tasks.get_agent_task_detail(session, task_id)

    def get_agent_task_context(self, session: Session, task_id: UUID) -> TaskContextEnvelope:
        return agent_task_context.get_agent_task_context(session, task_id)

    def get_agent_task_audit_bundle(self, session: Session, task_id: UUID) -> dict:
        return evidence.get_agent_task_audit_bundle(session, task_id)

    def get_agent_task_evidence_manifest(self, session: Session, task_id: UUID) -> dict:
        return evidence.get_agent_task_evidence_manifest(session, task_id)

    def get_agent_task_evidence_trace(self, session: Session, task_id: UUID) -> dict:
        return evidence.get_agent_task_evidence_trace(session, task_id)

    def get_agent_task_provenance_export(
        self,
        session: Session,
        task_id: UUID,
        *,
        storage_service: StorageService | None = None,
    ) -> dict:
        return evidence.get_agent_task_provenance_export(
            session,
            task_id,
            storage_service=storage_service,
        )

    def list_agent_task_outcomes(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskOutcomeResponse]:
        return agent_tasks.list_agent_task_outcomes(session, task_id, limit=limit)

    def create_agent_task_outcome(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskOutcomeCreateRequest,
    ) -> AgentTaskOutcomeResponse:
        return agent_tasks.create_agent_task_outcome(session, task_id, payload)

    def list_agent_task_artifacts(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskArtifactResponse]:
        return agent_task_artifacts.list_agent_task_artifacts(session, task_id, limit=limit)

    def get_agent_task_artifact(
        self,
        session: Session,
        task_id: UUID,
        artifact_id: UUID,
    ) -> AgentTaskArtifactResponse:
        return agent_task_artifacts.get_agent_task_artifact(session, task_id, artifact_id)

    def get_agent_task_verifications(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskVerificationResponse]:
        return agent_task_verifications.get_agent_task_verifications(
            session,
            task_id,
            limit=limit,
        )

    def approve_agent_task(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskApprovalRequest,
    ) -> AgentTaskDetailResponse:
        return agent_tasks.approve_agent_task(session, task_id, payload)

    def reject_agent_task(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskRejectionRequest,
    ) -> AgentTaskDetailResponse:
        return agent_tasks.reject_agent_task(session, task_id, payload)

    def get_agent_task_analytics_summary(
        self,
        session: Session,
    ) -> AgentTaskAnalyticsSummaryResponse:
        return agent_tasks.get_agent_task_analytics_summary(session)

    def get_agent_task_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskTrendResponse:
        return agent_tasks.get_agent_task_trends(
            session,
            bucket=bucket,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_verification_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskVerificationTrendResponse:
        return agent_tasks.get_agent_verification_trends(
            session,
            bucket=bucket,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_approval_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskApprovalTrendResponse:
        return agent_tasks.get_agent_approval_trends(
            session,
            bucket=bucket,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_task_recommendation_summary(
        self,
        session: Session,
        *,
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskRecommendationSummaryResponse:
        return agent_tasks.get_agent_task_recommendation_summary(
            session,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_task_recommendation_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskRecommendationTrendResponse:
        return agent_tasks.get_agent_task_recommendation_trends(
            session,
            bucket=bucket,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_task_cost_summary(
        self,
        session: Session,
        *,
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskCostSummaryResponse:
        return agent_tasks.get_agent_task_cost_summary(
            session,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_task_cost_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskCostTrendResponse:
        return agent_tasks.get_agent_task_cost_trends(
            session,
            bucket=bucket,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_task_performance_summary(
        self,
        session: Session,
        *,
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskPerformanceSummaryResponse:
        return agent_tasks.get_agent_task_performance_summary(
            session,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_task_performance_trends(
        self,
        session: Session,
        *,
        bucket: str = "day",
        task_type: str | None = None,
        workflow_version: str | None = None,
    ) -> AgentTaskPerformanceTrendResponse:
        return agent_tasks.get_agent_task_performance_trends(
            session,
            bucket=bucket,
            task_type=task_type,
            workflow_version=workflow_version,
        )

    def get_agent_task_value_density(
        self,
        session: Session,
    ) -> list[AgentTaskValueDensityRowResponse]:
        return agent_tasks.get_agent_task_value_density(session)

    def get_agent_task_decision_signals(
        self,
        session: Session,
    ) -> list[AgentTaskDecisionSignalResponse]:
        return agent_tasks.get_agent_task_decision_signals(session)

    def list_agent_task_workflow_summaries(
        self,
        session: Session,
    ) -> list[AgentTaskWorkflowVersionSummaryResponse]:
        return agent_tasks.list_agent_task_workflow_summaries(session)

    def export_agent_task_traces(
        self,
        session: Session,
        *,
        limit: int = 50,
        workflow_version: str | None = None,
        task_type: str | None = None,
    ) -> AgentTaskTraceExportResponse:
        return agent_tasks.export_agent_task_traces(
            session,
            limit=limit,
            workflow_version=workflow_version,
            task_type=task_type,
        )

    def run_worker_loop(self) -> None:
        worker_service.run_agent_task_worker_loop()


agent_orchestration: AgentOrchestrationCapability = ServicesAgentOrchestrationCapability()
