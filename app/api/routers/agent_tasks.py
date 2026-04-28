from __future__ import annotations

import hashlib
import json
from typing import Annotated
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
    ClaimSupportPolicyChangeImpactReplayRequest,
    ClaimSupportPolicyChangeImpactReplayResponse,
    ClaimSupportPolicyChangeImpactResponse,
    ClaimSupportPolicyChangeImpactSummaryResponse,
    TaskContextEnvelope,
)
from app.services.capabilities import agent_orchestration
from app.services.claim_support_policy_impacts import (
    get_claim_support_policy_change_impact,
    list_claim_support_policy_change_impacts,
    queue_claim_support_policy_change_impact_replay_tasks,
    refresh_claim_support_policy_change_impact_replay_status,
    summarize_claim_support_policy_change_impacts,
)
from app.services.storage import StorageService

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
TaskStatusQuery = Annotated[list[str] | None, Query(alias="status")]
TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND = "technical_report_prov_export"

list_agent_task_action_definitions = agent_orchestration.list_agent_task_action_definitions
list_agent_tasks = agent_orchestration.list_agent_tasks
create_agent_task = agent_orchestration.create_agent_task
get_agent_task_detail = agent_orchestration.get_agent_task_detail
get_agent_task_context = agent_orchestration.get_agent_task_context
get_agent_task_audit_bundle = agent_orchestration.get_agent_task_audit_bundle
get_agent_task_evidence_manifest = agent_orchestration.get_agent_task_evidence_manifest
get_agent_task_evidence_trace = agent_orchestration.get_agent_task_evidence_trace
get_agent_task_provenance_export = agent_orchestration.get_agent_task_provenance_export
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


def _storage_service_dep() -> StorageService:
    return get_storage_service()


StorageDep = Annotated[StorageService, Depends(_storage_service_dep)]


def _artifact_payload_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_artifact_payload(payload: dict | None) -> dict:
    return json.loads(json.dumps(payload or {}, sort_keys=True, default=str))


def _frozen_prov_artifact_response(artifact, storage_service: StorageService):
    storage_path = getattr(artifact, "storage_path", None)
    if not storage_path:
        return JSONResponse(artifact.payload_json or {})
    resolved_path = storage_service.resolve_existing_path(storage_path)
    if resolved_path is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_artifact_file_not_found",
            "Agent task artifact file was not found under the configured storage root.",
            task_id=str(artifact.task_id),
            artifact_id=str(artifact.id),
            artifact_kind=artifact.artifact_kind,
            storage_path=storage_path,
        )
    try:
        storage_payload = json.loads(resolved_path.read_text())
    except json.JSONDecodeError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "agent_task_artifact_storage_invalid_json",
            "Agent task artifact file is not valid JSON.",
            task_id=str(artifact.task_id),
            artifact_id=str(artifact.id),
            artifact_kind=artifact.artifact_kind,
            storage_path=str(resolved_path),
        ) from exc

    database_payload = _canonical_artifact_payload(artifact.payload_json)
    storage_payload = _canonical_artifact_payload(storage_payload)
    if storage_payload != database_payload:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "agent_task_artifact_integrity_mismatch",
            "Agent task artifact file does not match the frozen database payload.",
            task_id=str(artifact.task_id),
            artifact_id=str(artifact.id),
            artifact_kind=artifact.artifact_kind,
            storage_path=str(resolved_path),
            database_payload_sha256=_artifact_payload_sha256(database_payload),
            storage_payload_sha256=_artifact_payload_sha256(storage_payload),
        )
    return JSONResponse(storage_payload)


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
    session: DbSession,
    task_status: TaskStatusQuery = None,
    limit: int = 50,
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
    session: DbSession,
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
    session: DbSession,
) -> AgentTaskAnalyticsSummaryResponse:
    return get_agent_task_analytics_summary(session)


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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
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
    session: DbSession,
) -> list[AgentTaskValueDensityRowResponse]:
    return get_agent_task_value_density(session)


@router.get(
    "/agent-tasks/analytics/decision-signals",
    response_model=list[AgentTaskDecisionSignalResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_decision_signals(
    session: DbSession,
) -> list[AgentTaskDecisionSignalResponse]:
    return get_agent_task_decision_signals(session)


@router.get(
    "/agent-tasks/analytics/workflow-versions",
    response_model=list[AgentTaskWorkflowVersionSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_workflow_summaries(
    session: DbSession,
) -> list[AgentTaskWorkflowVersionSummaryResponse]:
    return list_agent_task_workflow_summaries(session)


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
    return export_agent_task_traces(
        session,
        limit=limit,
        workflow_version=workflow_version,
        task_type=task_type,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts",
    response_model=list[ClaimSupportPolicyChangeImpactResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impacts(
    session: DbSession,
    policy_name: str | None = None,
    replay_status: str | None = None,
    limit: int = 50,
) -> list[ClaimSupportPolicyChangeImpactResponse]:
    return list_claim_support_policy_change_impacts(
        session,
        policy_name=policy_name,
        replay_status=replay_status,
        limit=limit,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts/summary",
    response_model=ClaimSupportPolicyChangeImpactSummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impact_summary(
    session: DbSession,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
) -> ClaimSupportPolicyChangeImpactSummaryResponse:
    return summarize_claim_support_policy_change_impacts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}",
    response_model=ClaimSupportPolicyChangeImpactResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impact(
    session: DbSession,
    change_impact_id: UUID,
) -> ClaimSupportPolicyChangeImpactResponse:
    return get_claim_support_policy_change_impact(session, change_impact_id)


@router.post(
    "/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-tasks",
    response_model=ClaimSupportPolicyChangeImpactReplayResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def create_claim_support_policy_change_impact_replay_tasks(
    session: DbSession,
    change_impact_id: UUID,
    payload: ClaimSupportPolicyChangeImpactReplayRequest,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    return queue_claim_support_policy_change_impact_replay_tasks(
        session,
        change_impact_id,
        requested_by=payload.requested_by,
    )


@router.post(
    "/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-status",
    response_model=ClaimSupportPolicyChangeImpactReplayResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def refresh_claim_support_policy_change_impact_replay_status_route(
    session: DbSession,
    change_impact_id: UUID,
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    return refresh_claim_support_policy_change_impact_replay_status(
        session,
        change_impact_id,
        storage_service=storage_service,
    )


@router.get(
    "/agent-tasks/{task_id}",
    response_model=AgentTaskDetailResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_detail_route(
    task_id: UUID,
    session: DbSession,
) -> AgentTaskDetailResponse:
    return get_agent_task_detail(session, task_id)


@router.get(
    "/agent-tasks/{task_id}/context",
    response_model=TaskContextEnvelope,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_context_route(
    task_id: UUID,
    session: DbSession,
    format: str = "json",
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
    "/agent-tasks/{task_id}/audit-bundle",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_audit_bundle_route(
    task_id: UUID,
    session: DbSession,
) -> dict:
    try:
        return get_agent_task_audit_bundle(session, task_id)
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_audit_bundle_not_found",
            str(exc),
            task_id=str(task_id),
        ) from exc


@router.get(
    "/agent-tasks/{task_id}/evidence-manifest",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_evidence_manifest_route(
    task_id: UUID,
    session: DbSession,
) -> dict:
    try:
        response = get_agent_task_evidence_manifest(session, task_id)
        session.commit()
        return response
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_evidence_manifest_not_found",
            str(exc),
            task_id=str(task_id),
        ) from exc


@router.get(
    "/agent-tasks/{task_id}/evidence-trace",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_evidence_trace_route(
    task_id: UUID,
    session: DbSession,
) -> dict:
    try:
        response = get_agent_task_evidence_trace(session, task_id)
        session.commit()
        return response
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_evidence_trace_not_found",
            str(exc),
            task_id=str(task_id),
        ) from exc


@router.get(
    "/agent-tasks/{task_id}/provenance",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_provenance_route(
    task_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> dict:
    try:
        response = get_agent_task_provenance_export(
            session,
            task_id,
            storage_service=storage_service,
        )
        session.commit()
        return response
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_provenance_not_found",
            str(exc),
            task_id=str(task_id),
        ) from exc


@router.get(
    "/agent-tasks/{task_id}/outcomes",
    response_model=list[AgentTaskOutcomeResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_outcomes(
    task_id: UUID,
    session: DbSession,
    limit: int = 20,
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
    session: DbSession,
) -> AgentTaskOutcomeResponse:
    return create_agent_task_outcome(session, task_id, payload)


@router.get(
    "/agent-tasks/{task_id}/artifacts",
    response_model=list[AgentTaskArtifactResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_artifacts(
    task_id: UUID,
    session: DbSession,
    limit: int = 20,
) -> list[AgentTaskArtifactResponse]:
    return list_agent_task_artifacts(session, task_id, limit=limit)


@router.get(
    "/agent-tasks/{task_id}/artifacts/{artifact_id}",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_artifact_route(
    task_id: UUID,
    artifact_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
):
    artifact = get_agent_task_artifact(session, task_id, artifact_id)
    if getattr(artifact, "artifact_kind", None) == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND:
        return _frozen_prov_artifact_response(artifact, storage_service)
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
    session: DbSession,
    limit: int = 20,
) -> list[AgentTaskVerificationResponse]:
    return get_agent_task_verifications(session, task_id, limit=limit)


@router.get(
    "/agent-tasks/{task_id}/failure-artifact",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_failure_artifact(
    task_id: UUID,
    session: DbSession,
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
    session: DbSession,
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
    session: DbSession,
) -> AgentTaskDetailResponse:
    return reject_agent_task(session, task_id, payload)
