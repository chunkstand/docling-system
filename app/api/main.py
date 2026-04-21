from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from uuid import UUID

import uvicorn
import yaml
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.errors import api_error, structured_http_exception_handler
from app.api.file_delivery import file_response_if_exists
from app.core.config import (
    get_settings,
    is_loopback_host,
    resolve_api_credentials,
    resolve_api_mode,
    resolve_remote_api_capabilities,
    semantics_feature_enabled,
)
from app.db.models import DocumentFigure, DocumentRun, DocumentTable
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
from app.schemas.chat import (
    ChatAnswerFeedbackCreateRequest,
    ChatAnswerFeedbackResponse,
    ChatRequest,
    ChatResponse,
)
from app.schemas.chunks import DocumentChunkResponse
from app.schemas.documents import (
    DocumentDetailResponse,
    DocumentRunSummaryResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from app.schemas.evaluations import EvaluationDetailResponse
from app.schemas.figures import DocumentFigureDetailResponse, DocumentFigureSummaryResponse
from app.schemas.quality import (
    QualityEvaluationCandidateResponse,
    QualityEvaluationStatusResponse,
    QualityFailuresResponse,
    QualitySummaryResponse,
    QualityTrendsResponse,
)
from app.schemas.search import (
    SearchFeedbackCreateRequest,
    SearchFeedbackResponse,
    SearchHarnessDescriptorResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessResponse,
    SearchReplayComparisonResponse,
    SearchReplayResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
    SearchRequest,
    SearchRequestDetailResponse,
    SearchRequestExplanationResponse,
    SearchResult,
)
from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticContinuityResponse,
    SemanticReviewDecisionRequest,
    SemanticReviewEventResponse,
)
from app.schemas.tables import DocumentTableDetailResponse, DocumentTableSummaryResponse
from app.services.agent_task_artifacts import get_agent_task_artifact, list_agent_task_artifacts
from app.services.agent_task_context import get_agent_task_context
from app.services.agent_task_verifications import get_agent_task_verifications
from app.services.agent_tasks import (
    approve_agent_task,
    create_agent_task,
    create_agent_task_outcome,
    export_agent_task_traces,
    get_agent_approval_trends,
    get_agent_task_analytics_summary,
    get_agent_task_cost_summary,
    get_agent_task_cost_trends,
    get_agent_task_decision_signals,
    get_agent_task_detail,
    get_agent_task_performance_summary,
    get_agent_task_performance_trends,
    get_agent_task_recommendation_summary,
    get_agent_task_recommendation_trends,
    get_agent_task_trends,
    get_agent_task_value_density,
    get_agent_verification_trends,
    list_agent_task_action_definitions,
    list_agent_task_outcomes,
    list_agent_task_workflow_summaries,
    list_agent_tasks,
    reject_agent_task,
)
from app.services.chat import answer_question, record_chat_answer_feedback
from app.services.chunks import get_active_chunks
from app.services.documents import (
    get_document_detail,
    get_document_run_summary,
    get_latest_document_evaluation_detail,
    ingest_upload,
    list_document_runs,
    list_documents,
    reprocess_document,
)
from app.services.figures import get_active_figure_detail, get_active_figures
from app.services.quality import (
    get_quality_failures,
    get_quality_summary,
    get_quality_trends,
    list_quality_eval_candidates,
    list_quality_evaluations,
)
from app.services.runtime import get_runtime_status, register_runtime_process
from app.services.search import execute_search
from app.services.search_harness_evaluations import (
    evaluate_search_harness,
    list_search_harness_definitions,
)
from app.services.search_history import (
    get_search_request_detail,
    record_search_feedback,
    replay_search_request,
)
from app.services.search_legibility import (
    get_search_harness_descriptor,
    get_search_request_explanation,
)
from app.services.search_replays import (
    compare_search_replay_runs,
    get_search_replay_run_detail,
    list_search_replay_runs,
    run_search_replay_suite,
)
from app.services.semantics import (
    get_active_semantic_continuity,
    get_active_semantic_pass_detail,
    get_active_semantic_pass_row,
    review_active_semantic_assertion,
    review_active_semantic_assertion_category_binding,
)
from app.services.storage import StorageService
from app.services.tables import get_active_table_detail, get_active_tables
from app.services.telemetry import snapshot_metrics


def _api_mode_metadata() -> dict[str, object]:
    settings = get_settings()
    resolved_mode = resolve_api_mode(settings)
    resolved_credentials = resolve_api_credentials(settings)
    payload = {
        "api_mode": resolved_mode,
        "api_mode_explicit": settings.api_mode is not None,
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "semantics_enabled": semantics_feature_enabled(settings),
    }
    if resolved_mode == "remote":
        payload["remote_api_auth_mode"] = (
            "actor_scoped"
            if getattr(settings, "api_credentials_json", None)
            else "legacy_single_key"
        )
        payload["remote_api_principals"] = [
            {"actor": credential.actor, "capabilities": sorted(credential.capabilities)}
            for credential in resolved_credentials
        ]
        if not getattr(settings, "api_credentials_json", None):
            payload["remote_api_capabilities"] = sorted(resolve_remote_api_capabilities(settings))
    return payload


def _ensure_semantics_enabled() -> None:
    settings = get_settings()
    if semantics_feature_enabled(settings):
        return
    raise api_error(
        status.HTTP_409_CONFLICT,
        "semantics_disabled",
        "Semantic layer is disabled. Set DOCLING_SYSTEM_SEMANTICS_ENABLED=1 to enable it.",
    )


def _require_api_key_for_mutations(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    settings = get_settings()
    if resolve_api_mode(settings) != "remote" and not _api_auth_is_configured(settings):
        return

    credential = _resolve_api_credential(
        settings=settings,
        x_api_key=x_api_key,
        authorization=authorization,
    )
    if credential is not None:
        request.state.api_credential = credential
        return

    raise api_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="auth_required",
        message="Valid API key required for mutating API access.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _require_api_capability(capability: str):
    def dependency(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> None:
        settings = get_settings()
        if resolve_api_mode(settings) != "remote":
            return
        credential = getattr(request.state, "api_credential", None) or _resolve_api_credential(
            settings=settings,
            x_api_key=x_api_key,
            authorization=authorization,
        )
        if credential is None:
            raise api_error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="auth_required",
                message="Valid API key required for remote API access.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        request.state.api_credential = credential
        allowed_capabilities = credential.capabilities
        if "*" in allowed_capabilities or capability in allowed_capabilities:
            return
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "capability_not_allowed",
            f"Remote API capability '{capability}' is not enabled.",
            capability=capability,
            actor=credential.actor,
        )

    return dependency


def _bearer_token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    return None


def _api_auth_is_configured(settings) -> bool:
    return bool(resolve_api_credentials(settings))


def _resolve_api_credential(
    *,
    settings,
    x_api_key: str | None,
    authorization: str | None,
) -> object | None:
    bearer_token = _bearer_token_from_header(authorization)
    provided_values = [value for value in (x_api_key, bearer_token) if value]
    for credential in resolve_api_credentials(settings):
        if any(secrets.compare_digest(value, credential.key) for value in provided_values):
            return credential
    return None


def _validate_runtime_bind_settings() -> tuple[str, int]:
    settings = get_settings()
    resolved_mode = resolve_api_mode(settings)
    auth_is_configured = _api_auth_is_configured(settings)
    if resolved_mode == "local" and not is_loopback_host(settings.api_host):
        raise ValueError(
            "DOCLING_SYSTEM_API_MODE=local requires DOCLING_SYSTEM_API_HOST to remain loopback."
        )
    if (
        settings.api_mode is None
        and not is_loopback_host(settings.api_host)
        and not auth_is_configured
    ):
        raise ValueError(
            "DOCLING_SYSTEM_API_KEY or DOCLING_SYSTEM_API_CREDENTIALS_JSON must be set "
            "when binding the API to a non-loopback host."
        )
    if resolved_mode == "remote" and not auth_is_configured:
        raise ValueError(
            "DOCLING_SYSTEM_API_MODE=remote requires DOCLING_SYSTEM_API_KEY or "
            "DOCLING_SYSTEM_API_CREDENTIALS_JSON to be set."
        )
    return settings.api_host, settings.api_port


@asynccontextmanager
async def lifespan(_app: FastAPI):
    register_runtime_process("api", f"api:{os.getpid()}", pid=os.getpid())
    yield


app = FastAPI(title="Docling System", version="0.1.0", lifespan=lifespan)
app.add_exception_handler(HTTPException, structured_http_exception_handler)
UI_DIR = Path(__file__).resolve().parent.parent / "ui"
app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

PUBLIC_REMOTE_PATHS = frozenset({"/health"})


@app.middleware("http")
async def require_remote_api_key_for_reads(request: Request, call_next):
    settings = get_settings()
    if resolve_api_mode(settings) != "remote":
        return await call_next(request)
    if request.method not in {"GET", "HEAD"}:
        return await call_next(request)
    if request.url.path in PUBLIC_REMOTE_PATHS:
        return await call_next(request)
    credential = _resolve_api_credential(
        settings=settings,
        x_api_key=request.headers.get("X-API-Key"),
        authorization=request.headers.get("Authorization"),
    )
    if credential is not None:
        request.state.api_credential = credential
        return await call_next(request)
    return await structured_http_exception_handler(
        request,
        api_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="auth_required",
            message="Valid API key required for remote API access.",
            headers={"WWW-Authenticate": "Bearer"},
        ),
    )


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return StorageService()


def _storage_file_response(
    path_value: str | Path | None,
    *,
    media_type: str | None = None,
    not_found_detail: str | None = None,
    not_found_error_code: str | None = None,
    not_found_context: dict[str, object] | None = None,
):
    return file_response_if_exists(
        get_storage_service().resolve_existing_path(path_value),
        media_type=media_type,
        response_factory=FileResponse,
        not_found_detail=not_found_detail,
        not_found_error_code=not_found_error_code,
        not_found_context=not_found_context,
    )


def _response_field(payload, field_name: str):
    value = getattr(payload, field_name, None)
    if value is None and isinstance(payload, dict):
        value = payload.get(field_name)
    return value


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/runtime/status",
    dependencies=[Depends(_require_api_capability("system:read"))],
)
def runtime_status() -> dict:
    payload = get_runtime_status(process_identity=f"api:{os.getpid()}")
    payload.update(_api_mode_metadata())
    return payload


@app.get("/metrics", dependencies=[Depends(_require_api_capability("system:read"))])
def metrics() -> dict[str, float]:
    return snapshot_metrics()


@app.get(
    "/quality/summary",
    response_model=QualitySummaryResponse,
    dependencies=[Depends(_require_api_capability("quality:read"))],
)
def read_quality_summary(session: Session = Depends(get_db_session)) -> QualitySummaryResponse:
    return get_quality_summary(session)


@app.get(
    "/quality/failures",
    response_model=QualityFailuresResponse,
    dependencies=[Depends(_require_api_capability("quality:read"))],
)
def read_quality_failures(session: Session = Depends(get_db_session)) -> QualityFailuresResponse:
    return get_quality_failures(session)


@app.get(
    "/quality/evaluations",
    response_model=list[QualityEvaluationStatusResponse],
    dependencies=[Depends(_require_api_capability("quality:read"))],
)
def read_quality_evaluations(
    session: Session = Depends(get_db_session),
) -> list[QualityEvaluationStatusResponse]:
    return list_quality_evaluations(session)


@app.get(
    "/quality/eval-candidates",
    response_model=list[QualityEvaluationCandidateResponse],
    dependencies=[Depends(_require_api_capability("quality:read"))],
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


@app.get(
    "/quality/trends",
    response_model=QualityTrendsResponse,
    dependencies=[Depends(_require_api_capability("quality:read"))],
)
def read_quality_trends(session: Session = Depends(get_db_session)) -> QualityTrendsResponse:
    return get_quality_trends(session)


@app.get(
    "/agent-tasks/actions",
    response_model=list[AgentTaskActionDefinitionResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_actions() -> list[AgentTaskActionDefinitionResponse]:
    return list_agent_task_action_definitions()


@app.get(
    "/agent-tasks",
    response_model=list[AgentTaskSummaryResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_tasks(
    status: list[str] | None = None,
    limit: int = 50,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskSummaryResponse]:
    return list_agent_tasks(session, statuses=status, limit=limit)


@app.post(
    "/agent-tasks",
    response_model=AgentTaskDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("agent_tasks:write")),
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
    task_id = _response_field(task_response, "task_id")
    if task_id is not None:
        response.headers["Location"] = f"/agent-tasks/{task_id}"
    return task_response


@app.get(
    "/agent-tasks/analytics/summary",
    response_model=AgentTaskAnalyticsSummaryResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_analytics_summary(
    session: Session = Depends(get_db_session),
) -> AgentTaskAnalyticsSummaryResponse:
    return get_agent_task_analytics_summary(session)


@app.get(
    "/agent-tasks/analytics/trends",
    response_model=AgentTaskTrendResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/verifications",
    response_model=AgentTaskVerificationTrendResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/approvals",
    response_model=AgentTaskApprovalTrendResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/recommendations",
    response_model=AgentTaskRecommendationSummaryResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/recommendations/trends",
    response_model=AgentTaskRecommendationTrendResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/costs",
    response_model=AgentTaskCostSummaryResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/costs/trends",
    response_model=AgentTaskCostTrendResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/performance",
    response_model=AgentTaskPerformanceSummaryResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/performance/trends",
    response_model=AgentTaskPerformanceTrendResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/analytics/value-density",
    response_model=list[AgentTaskValueDensityRowResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_value_density(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskValueDensityRowResponse]:
    return get_agent_task_value_density(session)


@app.get(
    "/agent-tasks/analytics/decision-signals",
    response_model=list[AgentTaskDecisionSignalResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_decision_signals(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskDecisionSignalResponse]:
    return get_agent_task_decision_signals(session)


@app.get(
    "/agent-tasks/analytics/workflow-versions",
    response_model=list[AgentTaskWorkflowVersionSummaryResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_workflow_summaries(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskWorkflowVersionSummaryResponse]:
    return list_agent_task_workflow_summaries(session)


@app.get(
    "/agent-tasks/traces/export",
    response_model=AgentTaskTraceExportResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
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


@app.get(
    "/agent-tasks/{task_id}",
    response_model=AgentTaskDetailResponse,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_detail(
    task_id: UUID,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return get_agent_task_detail(session, task_id)


@app.get(
    "/agent-tasks/{task_id}/context",
    response_model=TaskContextEnvelope,
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_context(
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


@app.get(
    "/agent-tasks/{task_id}/outcomes",
    response_model=list[AgentTaskOutcomeResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_outcomes(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskOutcomeResponse]:
    return list_agent_task_outcomes(session, task_id, limit=limit)


@app.post(
    "/agent-tasks/{task_id}/outcomes",
    response_model=AgentTaskOutcomeResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("agent_tasks:write")),
    ],
)
def create_agent_task_outcome_route(
    task_id: UUID,
    payload: AgentTaskOutcomeCreateRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskOutcomeResponse:
    return create_agent_task_outcome(session, task_id, payload)


@app.get(
    "/agent-tasks/{task_id}/artifacts",
    response_model=list[AgentTaskArtifactResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_artifacts(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskArtifactResponse]:
    return list_agent_task_artifacts(session, task_id, limit=limit)


@app.get(
    "/agent-tasks/{task_id}/artifacts/{artifact_id}",
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_artifact(
    task_id: UUID,
    artifact_id: UUID,
    session: Session = Depends(get_db_session),
):
    artifact = get_agent_task_artifact(session, task_id, artifact_id)
    file_response = _storage_file_response(artifact.storage_path, media_type="application/json")
    if file_response.status_code != 404:
        return file_response
    return JSONResponse(artifact.payload_json or {})


@app.get(
    "/agent-tasks/{task_id}/verifications",
    response_model=list[AgentTaskVerificationResponse],
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_verifications(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskVerificationResponse]:
    return get_agent_task_verifications(session, task_id, limit=limit)


@app.get(
    "/agent-tasks/{task_id}/failure-artifact",
    dependencies=[Depends(_require_api_capability("agent_tasks:read"))],
)
def read_agent_task_failure_artifact(
    task_id: UUID,
    session: Session = Depends(get_db_session),
):
    get_agent_task_detail(session, task_id)
    return _storage_file_response(
        get_storage_service().build_agent_task_failure_artifact_path(task_id),
        media_type="application/json",
        not_found_detail="Agent task failure artifact not found.",
        not_found_error_code="agent_task_failure_artifact_not_found",
        not_found_context={"task_id": str(task_id)},
    )


@app.post(
    "/agent-tasks/{task_id}/approve",
    response_model=AgentTaskDetailResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("agent_tasks:write")),
    ],
)
def approve_agent_task_route(
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return approve_agent_task(session, task_id, payload)


@app.post(
    "/agent-tasks/{task_id}/reject",
    response_model=AgentTaskDetailResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("agent_tasks:write")),
    ],
)
def reject_agent_task_route(
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return reject_agent_task(session, task_id, payload)


@app.get(
    "/documents",
    response_model=list[DocumentSummaryResponse],
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_documents(
    limit: int = Query(default=50, ge=1, le=10000),
    session: Session = Depends(get_db_session),
) -> list[DocumentSummaryResponse]:
    return list_documents(session, limit=limit)


@app.post(
    "/documents",
    response_model=DocumentUploadResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("documents:upload")),
    ],
)
def create_document(
    response: Response,
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    payload, status_code = ingest_upload(
        session=session,
        upload=file,
        storage_service=get_storage_service(),
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    run_id = _response_field(payload, "run_id")
    if run_id is not None:
        response.headers["Location"] = f"/runs/{run_id}"
    return payload


@app.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentDetailResponse:
    return get_document_detail(session, document_id)


@app.get(
    "/documents/{document_id}/runs",
    response_model=list[DocumentRunSummaryResponse],
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document_runs(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentRunSummaryResponse]:
    return list_document_runs(session, document_id)


@app.get(
    "/runs/{run_id}",
    response_model=DocumentRunSummaryResponse,
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document_run(
    run_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentRunSummaryResponse:
    return get_document_run_summary(session, run_id)


@app.get(
    "/documents/{document_id}/evaluations/latest",
    response_model=EvaluationDetailResponse,
    dependencies=[Depends(_require_api_capability("quality:read"))],
)
def read_latest_document_evaluation(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> EvaluationDetailResponse:
    return get_latest_document_evaluation_detail(session, document_id)


@app.get(
    "/documents/{document_id}/semantics/latest",
    response_model=DocumentSemanticPassResponse,
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_latest_document_semantics(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentSemanticPassResponse:
    _ensure_semantics_enabled()
    return get_active_semantic_pass_detail(session, document_id)


@app.get(
    "/documents/{document_id}/semantics/latest/continuity",
    response_model=SemanticContinuityResponse,
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_latest_document_semantic_continuity(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> SemanticContinuityResponse:
    _ensure_semantics_enabled()
    return get_active_semantic_continuity(session, document_id)


@app.post(
    "/documents/{document_id}/semantics/latest/assertions/{assertion_id}/review",
    response_model=SemanticReviewEventResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("documents:review")),
    ],
)
def review_latest_document_semantic_assertion(
    document_id: UUID,
    assertion_id: UUID,
    request: SemanticReviewDecisionRequest,
    session: Session = Depends(get_db_session),
) -> SemanticReviewEventResponse:
    _ensure_semantics_enabled()
    return review_active_semantic_assertion(
        session,
        document_id,
        assertion_id,
        review_status=request.review_status,
        review_note=request.review_note,
        reviewed_by=request.reviewed_by,
        storage_service=get_storage_service(),
    )


@app.post(
    "/documents/{document_id}/semantics/latest/assertion-category-bindings/{binding_id}/review",
    response_model=SemanticReviewEventResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("documents:review")),
    ],
)
def review_latest_document_semantic_assertion_category_binding(
    document_id: UUID,
    binding_id: UUID,
    request: SemanticReviewDecisionRequest,
    session: Session = Depends(get_db_session),
) -> SemanticReviewEventResponse:
    _ensure_semantics_enabled()
    return review_active_semantic_assertion_category_binding(
        session,
        document_id,
        binding_id,
        review_status=request.review_status,
        review_note=request.review_note,
        reviewed_by=request.reviewed_by,
        storage_service=get_storage_service(),
    )


@app.get(
    "/documents/{document_id}/chunks",
    response_model=list[DocumentChunkResponse],
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document_chunks(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentChunkResponse]:
    return get_active_chunks(session, document_id)


@app.get(
    "/documents/{document_id}/tables",
    response_model=list[DocumentTableSummaryResponse],
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document_tables(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentTableSummaryResponse]:
    return get_active_tables(session, document_id)


@app.get(
    "/documents/{document_id}/tables/{table_id}",
    response_model=DocumentTableDetailResponse,
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document_table(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentTableDetailResponse:
    return get_active_table_detail(session, document_id, table_id)


@app.get(
    "/documents/{document_id}/figures",
    response_model=list[DocumentFigureSummaryResponse],
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document_figures(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentFigureSummaryResponse]:
    return get_active_figures(session, document_id)


@app.get(
    "/documents/{document_id}/figures/{figure_id}",
    response_model=DocumentFigureDetailResponse,
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_document_figure(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentFigureDetailResponse:
    return get_active_figure_detail(session, document_id, figure_id)


@app.post(
    "/documents/{document_id}/reprocess",
    response_model=DocumentUploadResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("documents:reprocess")),
    ],
)
def reprocess_existing_document(
    document_id: UUID,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    payload = reprocess_document(session, document_id, idempotency_key=idempotency_key)
    response.status_code = 202
    run_id = _response_field(payload, "run_id")
    if run_id is not None:
        response.headers["Location"] = f"/runs/{run_id}"
    return payload


@app.get(
    "/runs/{run_id}/failure-artifact",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_run_failure_artifact(
    run_id: UUID,
    session: Session = Depends(get_db_session),
):
    run = session.get(DocumentRun, run_id)
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_run_not_found",
            "Document run not found.",
            run_id=str(run_id),
        )
    return _storage_file_response(
        get_storage_service().build_failure_artifact_path(run.document_id, run.id),
        media_type="application/json",
        not_found_detail="Run failure artifact not found.",
        not_found_error_code="run_failure_artifact_not_found",
        not_found_context={"run_id": str(run_id), "document_id": str(run.document_id)},
    )


@app.get(
    "/documents/{document_id}/artifacts/json",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_docling_json_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_json_artifact or document.active_run_id is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document JSON artifact not found.",
            document_id=str(document_id),
            artifact_format="json",
        )
    run = session.get(DocumentRun, document.active_run_id)
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document JSON artifact not found.",
            document_id=str(document_id),
            artifact_format="json",
        )
    return _storage_file_response(
        get_storage_service().build_docling_json_path(document_id, run.id),
        not_found_detail="Document JSON artifact not found.",
        not_found_error_code="document_artifact_not_found",
        not_found_context={"document_id": str(document_id), "artifact_format": "json"},
    )


@app.get(
    "/documents/{document_id}/artifacts/yaml",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_yaml_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_yaml_artifact or document.active_run_id is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document YAML artifact not found.",
            document_id=str(document_id),
            artifact_format="yaml",
        )
    run = session.get(DocumentRun, document.active_run_id)
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document YAML artifact not found.",
            document_id=str(document_id),
            artifact_format="yaml",
        )
    return _storage_file_response(
        get_storage_service().build_yaml_path(document_id, run.id),
        not_found_detail="Document YAML artifact not found.",
        not_found_error_code="document_artifact_not_found",
        not_found_context={"document_id": str(document_id), "artifact_format": "yaml"},
    )


@app.get(
    "/documents/{document_id}/semantics/latest/artifacts/json",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_latest_semantic_json_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    _ensure_semantics_enabled()
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )
    return _storage_file_response(
        get_storage_service().build_semantic_json_path(
            document_id,
            semantic_pass.run_id,
            semantic_pass.artifact_schema_version,
        ),
        media_type="application/json",
        not_found_detail="Semantic JSON artifact not found.",
        not_found_error_code="semantic_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "run_id": str(semantic_pass.run_id),
            "artifact_format": "json",
        },
    )


@app.get(
    "/documents/{document_id}/semantics/latest/artifacts/yaml",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_latest_semantic_yaml_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    _ensure_semantics_enabled()
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )
    return _storage_file_response(
        get_storage_service().build_semantic_yaml_path(
            document_id,
            semantic_pass.run_id,
            semantic_pass.artifact_schema_version,
        ),
        not_found_detail="Semantic YAML artifact not found.",
        not_found_error_code="semantic_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "run_id": str(semantic_pass.run_id),
            "artifact_format": "yaml",
        },
    )


def _get_active_table_row(
    session: Session, document_id: UUID, table_id: UUID
) -> DocumentTable | None:
    document = get_document_detail(session, document_id)
    if document.active_run_id is None:
        return None
    table = session.get(DocumentTable, table_id)
    if table is None or table.run_id != document.active_run_id or table.document_id != document_id:
        return None
    return table


def _get_active_figure_row(
    session: Session, document_id: UUID, figure_id: UUID
) -> DocumentFigure | None:
    document = get_document_detail(session, document_id)
    if document.active_run_id is None:
        return None
    figure = session.get(DocumentFigure, figure_id)
    if (
        figure is None
        or figure.run_id != document.active_run_id
        or figure.document_id != document_id
    ):
        return None
    return figure


@app.get(
    "/documents/{document_id}/tables/{table_id}/artifacts/json",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_table_json_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "table_not_found",
            "Table not found.",
            document_id=str(document_id),
            table_id=str(table_id),
        )
    return _storage_file_response(
        get_storage_service().build_table_json_path(document_id, table.run_id, table.table_index),
        not_found_detail="Table JSON artifact not found.",
        not_found_error_code="table_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "table_id": str(table_id),
            "artifact_format": "json",
        },
    )


@app.get(
    "/documents/{document_id}/tables/{table_id}/artifacts/yaml",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_table_yaml_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "table_not_found",
            "Table not found.",
            document_id=str(document_id),
            table_id=str(table_id),
        )
    return _storage_file_response(
        get_storage_service().build_table_yaml_path(document_id, table.run_id, table.table_index),
        not_found_detail="Table YAML artifact not found.",
        not_found_error_code="table_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "table_id": str(table_id),
            "artifact_format": "yaml",
        },
    )


@app.get(
    "/documents/{document_id}/figures/{figure_id}/artifacts/json",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_figure_json_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "figure_not_found",
            "Figure not found.",
            document_id=str(document_id),
            figure_id=str(figure_id),
        )
    return _storage_file_response(
        get_storage_service().build_figure_json_path(
            document_id,
            figure.run_id,
            figure.figure_index,
        ),
        not_found_detail="Figure JSON artifact not found.",
        not_found_error_code="figure_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "figure_id": str(figure_id),
            "artifact_format": "json",
        },
    )


@app.get(
    "/documents/{document_id}/figures/{figure_id}/artifacts/yaml",
    dependencies=[Depends(_require_api_capability("documents:inspect"))],
)
def read_figure_yaml_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "figure_not_found",
            "Figure not found.",
            document_id=str(document_id),
            figure_id=str(figure_id),
        )
    return _storage_file_response(
        get_storage_service().build_figure_yaml_path(
            document_id,
            figure.run_id,
            figure.figure_index,
        ),
        not_found_detail="Figure YAML artifact not found.",
        not_found_error_code="figure_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "figure_id": str(figure_id),
            "artifact_format": "yaml",
        },
    )


@app.post(
    "/search",
    response_model=list[SearchResult],
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("search:query")),
    ],
)
def search_corpus(
    request: SearchRequest,
    response: Response,
    session: Session = Depends(get_db_session),
) -> list[SearchResult]:
    try:
        execution = execute_search(session, request, origin="api")
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_request",
            str(exc),
        ) from exc
    session.commit()
    if execution.request_id is not None:
        response.headers["X-Search-Request-Id"] = str(execution.request_id)
    return execution.results


@app.get(
    "/search/requests/{search_request_id}",
    response_model=SearchRequestDetailResponse,
    dependencies=[Depends(_require_api_capability("search:history:read"))],
)
def read_search_request(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchRequestDetailResponse:
    return get_search_request_detail(session, search_request_id)


@app.get(
    "/search/requests/{search_request_id}/explain",
    response_model=SearchRequestExplanationResponse,
    dependencies=[Depends(_require_api_capability("search:history:read"))],
)
def explain_search_request(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchRequestExplanationResponse:
    return get_search_request_explanation(session, search_request_id)


@app.post(
    "/search/requests/{search_request_id}/feedback",
    response_model=SearchFeedbackResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("search:feedback")),
    ],
)
def create_search_feedback(
    search_request_id: UUID,
    payload: SearchFeedbackCreateRequest,
    session: Session = Depends(get_db_session),
) -> SearchFeedbackResponse:
    feedback = record_search_feedback(session, search_request_id, payload)
    session.commit()
    return feedback


@app.post(
    "/search/requests/{search_request_id}/replay",
    response_model=SearchReplayResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("search:replay")),
    ],
)
def replay_logged_search(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayResponse:
    replay = replay_search_request(session, search_request_id)
    session.commit()
    return replay


@app.get(
    "/search/replays",
    response_model=list[SearchReplayRunSummaryResponse],
    dependencies=[Depends(_require_api_capability("search:replay"))],
)
def read_search_replays(
    session: Session = Depends(get_db_session),
) -> list[SearchReplayRunSummaryResponse]:
    return list_search_replay_runs(session)


@app.get(
    "/search/harnesses",
    response_model=list[SearchHarnessResponse],
    dependencies=[Depends(_require_api_capability("search:evaluate"))],
)
def read_search_harnesses() -> list[SearchHarnessResponse]:
    return list_search_harness_definitions()


@app.get(
    "/search/harnesses/{harness_name}/descriptor",
    response_model=SearchHarnessDescriptorResponse,
    dependencies=[Depends(_require_api_capability("search:evaluate"))],
)
def read_search_harness_descriptor(harness_name: str) -> SearchHarnessDescriptorResponse:
    try:
        return get_search_harness_descriptor(harness_name)
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_not_found",
            str(exc),
            harness_name=harness_name,
        ) from exc


@app.post(
    "/search/harness-evaluations",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("search:evaluate")),
    ],
)
def create_search_harness_evaluation(
    payload: SearchHarnessEvaluationRequest,
    session: Session = Depends(get_db_session),
) -> SearchHarnessEvaluationResponse:
    try:
        evaluation = evaluate_search_harness(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_harness_evaluation",
            str(exc),
        ) from exc
    session.commit()
    return evaluation


@app.post(
    "/search/replays",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("search:replay")),
    ],
)
def create_search_replay_run(
    response: Response,
    payload: SearchReplayRunRequest,
    session: Session = Depends(get_db_session),
) -> SearchReplayRunDetailResponse:
    try:
        replay_run = run_search_replay_suite(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_replay_request",
            str(exc),
        ) from exc
    session.commit()
    replay_run_id = _response_field(replay_run, "replay_run_id")
    if replay_run_id is not None:
        response.headers["Location"] = f"/search/replays/{replay_run_id}"
    return replay_run


@app.get(
    "/search/replays/compare",
    response_model=SearchReplayComparisonResponse,
    dependencies=[Depends(_require_api_capability("search:replay"))],
)
def read_search_replay_comparison(
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayComparisonResponse:
    return compare_search_replay_runs(
        session,
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
    )


@app.get(
    "/search/replays/{replay_run_id}",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[Depends(_require_api_capability("search:replay"))],
)
def read_search_replay_run(
    replay_run_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayRunDetailResponse:
    return get_search_replay_run_detail(session, replay_run_id)


@app.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("chat:query")),
    ],
)
def chat_with_corpus(
    request: ChatRequest,
    session: Session = Depends(get_db_session),
) -> ChatResponse:
    try:
        response = answer_question(session, request)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_chat_request",
            str(exc),
        ) from exc
    session.commit()
    return response


@app.post(
    "/chat/answers/{chat_answer_id}/feedback",
    response_model=ChatAnswerFeedbackResponse,
    dependencies=[
        Depends(_require_api_key_for_mutations),
        Depends(_require_api_capability("chat:feedback")),
    ],
)
def create_chat_answer_feedback(
    chat_answer_id: UUID,
    payload: ChatAnswerFeedbackCreateRequest,
    session: Session = Depends(get_db_session),
) -> ChatAnswerFeedbackResponse:
    response = record_chat_answer_feedback(session, chat_answer_id, payload)
    session.commit()
    return response


def run() -> None:
    host, port = _validate_runtime_bind_settings()
    uvicorn.run("app.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
