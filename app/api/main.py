from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
import os
from pathlib import Path
import secrets
from uuid import UUID

import uvicorn
import yaml
from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.file_delivery import file_response_if_exists
from app.core.config import get_settings
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
    TaskContextEnvelope,
    AgentTaskTraceExportResponse,
    AgentTaskTrendResponse,
    AgentTaskValueDensityRowResponse,
    AgentTaskVerificationResponse,
    AgentTaskVerificationTrendResponse,
    AgentTaskWorkflowVersionSummaryResponse,
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
    SearchResult,
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
from app.services.search_replays import (
    compare_search_replay_runs,
    get_search_replay_run_detail,
    list_search_replay_runs,
    run_search_replay_suite,
)
from app.services.storage import StorageService
from app.services.tables import get_active_table_detail, get_active_tables
from app.services.telemetry import snapshot_metrics


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def _require_api_key_for_mutations(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    configured_api_key = get_settings().api_key
    if not configured_api_key:
        return

    bearer_token: str | None = None
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            bearer_token = token

    provided_values = [value for value in (x_api_key, bearer_token) if value]
    if any(secrets.compare_digest(value, configured_api_key) for value in provided_values):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid API key required for mutating API access.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _validate_runtime_bind_settings() -> tuple[str, int]:
    settings = get_settings()
    if not _is_loopback_host(settings.api_host) and not settings.api_key:
        raise ValueError(
            "DOCLING_SYSTEM_API_KEY must be set when binding the API to a non-loopback host."
        )
    return settings.api_host, settings.api_port


@asynccontextmanager
async def lifespan(_app: FastAPI):
    register_runtime_process("api", f"api:{os.getpid()}", pid=os.getpid())
    yield


app = FastAPI(title="Docling System", version="0.1.0", lifespan=lifespan)
UI_DIR = Path(__file__).resolve().parent.parent / "ui"
app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return StorageService()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runtime/status")
def runtime_status() -> dict:
    return get_runtime_status(process_identity=f"api:{os.getpid()}")


@app.get("/metrics")
def metrics() -> dict[str, float]:
    return snapshot_metrics()


@app.get("/quality/summary", response_model=QualitySummaryResponse)
def read_quality_summary(session: Session = Depends(get_db_session)) -> QualitySummaryResponse:
    return get_quality_summary(session)


@app.get("/quality/failures", response_model=QualityFailuresResponse)
def read_quality_failures(session: Session = Depends(get_db_session)) -> QualityFailuresResponse:
    return get_quality_failures(session)


@app.get("/quality/evaluations", response_model=list[QualityEvaluationStatusResponse])
def read_quality_evaluations(
    session: Session = Depends(get_db_session),
) -> list[QualityEvaluationStatusResponse]:
    return list_quality_evaluations(session)


@app.get("/quality/eval-candidates", response_model=list[QualityEvaluationCandidateResponse])
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


@app.get("/quality/trends", response_model=QualityTrendsResponse)
def read_quality_trends(session: Session = Depends(get_db_session)) -> QualityTrendsResponse:
    return get_quality_trends(session)


@app.get("/agent-tasks/actions", response_model=list[AgentTaskActionDefinitionResponse])
def read_agent_task_actions() -> list[AgentTaskActionDefinitionResponse]:
    return list_agent_task_action_definitions()


@app.get("/agent-tasks", response_model=list[AgentTaskSummaryResponse])
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
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def create_agent_task_route(
    payload: AgentTaskCreateRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    try:
        response = create_agent_task(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return response


@app.get("/agent-tasks/analytics/summary", response_model=AgentTaskAnalyticsSummaryResponse)
def read_agent_task_analytics_summary(
    session: Session = Depends(get_db_session),
) -> AgentTaskAnalyticsSummaryResponse:
    return get_agent_task_analytics_summary(session)


@app.get("/agent-tasks/analytics/trends", response_model=AgentTaskTrendResponse)
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


@app.get("/agent-tasks/analytics/approvals", response_model=AgentTaskApprovalTrendResponse)
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


@app.get("/agent-tasks/analytics/costs", response_model=AgentTaskCostSummaryResponse)
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


@app.get("/agent-tasks/analytics/costs/trends", response_model=AgentTaskCostTrendResponse)
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
)
def read_agent_task_value_density(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskValueDensityRowResponse]:
    return get_agent_task_value_density(session)


@app.get(
    "/agent-tasks/analytics/decision-signals",
    response_model=list[AgentTaskDecisionSignalResponse],
)
def read_agent_task_decision_signals(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskDecisionSignalResponse]:
    return get_agent_task_decision_signals(session)


@app.get(
    "/agent-tasks/analytics/workflow-versions",
    response_model=list[AgentTaskWorkflowVersionSummaryResponse],
)
def read_agent_task_workflow_summaries(
    session: Session = Depends(get_db_session),
) -> list[AgentTaskWorkflowVersionSummaryResponse]:
    return list_agent_task_workflow_summaries(session)


@app.get("/agent-tasks/traces/export", response_model=AgentTaskTraceExportResponse)
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


@app.get("/agent-tasks/{task_id}", response_model=AgentTaskDetailResponse)
def read_agent_task_detail(
    task_id: UUID,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return get_agent_task_detail(session, task_id)


@app.get("/agent-tasks/{task_id}/context", response_model=TaskContextEnvelope)
def read_agent_task_context(
    task_id: UUID,
    format: str = "json",
    session: Session = Depends(get_db_session),
):
    context = get_agent_task_context(session, task_id)
    context_payload = (
        context.model_dump(mode="json") if hasattr(context, "model_dump") else context
    )
    if format == "json":
        return context
    if format == "yaml":
        return Response(
            content=yaml.safe_dump(context_payload, sort_keys=False, allow_unicode=True),
            media_type="application/yaml",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported context format. Use 'json' or 'yaml'.",
    )


@app.get("/agent-tasks/{task_id}/outcomes", response_model=list[AgentTaskOutcomeResponse])
def read_agent_task_outcomes(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskOutcomeResponse]:
    return list_agent_task_outcomes(session, task_id, limit=limit)


@app.post(
    "/agent-tasks/{task_id}/outcomes",
    response_model=AgentTaskOutcomeResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def create_agent_task_outcome_route(
    task_id: UUID,
    payload: AgentTaskOutcomeCreateRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskOutcomeResponse:
    return create_agent_task_outcome(session, task_id, payload)


@app.get("/agent-tasks/{task_id}/artifacts", response_model=list[AgentTaskArtifactResponse])
def read_agent_task_artifacts(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskArtifactResponse]:
    return list_agent_task_artifacts(session, task_id, limit=limit)


@app.get("/agent-tasks/{task_id}/artifacts/{artifact_id}")
def read_agent_task_artifact(
    task_id: UUID,
    artifact_id: UUID,
    session: Session = Depends(get_db_session),
):
    artifact = get_agent_task_artifact(session, task_id, artifact_id)
    file_response = file_response_if_exists(
        artifact.storage_path,
        media_type="application/json",
        path_type=Path,
        response_factory=FileResponse,
    )
    if file_response.status_code != 404:
        return file_response
    return JSONResponse(artifact.payload_json or {})


@app.get("/agent-tasks/{task_id}/verifications", response_model=list[AgentTaskVerificationResponse])
def read_agent_task_verifications(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskVerificationResponse]:
    return get_agent_task_verifications(session, task_id, limit=limit)


@app.get("/agent-tasks/{task_id}/failure-artifact")
def read_agent_task_failure_artifact(
    task_id: UUID,
    session: Session = Depends(get_db_session),
):
    task = get_agent_task_detail(session, task_id)
    failure_artifact_path = getattr(task, "failure_artifact_path", None)
    if failure_artifact_path is None and isinstance(task, dict):
        failure_artifact_path = task.get("failure_artifact_path")
    return file_response_if_exists(
        failure_artifact_path,
        media_type="application/json",
        path_type=Path,
        response_factory=FileResponse,
    )


@app.post(
    "/agent-tasks/{task_id}/approve",
    response_model=AgentTaskDetailResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
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
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def reject_agent_task_route(
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return reject_agent_task(session, task_id, payload)


@app.get("/documents", response_model=list[DocumentSummaryResponse])
def read_documents(session: Session = Depends(get_db_session)) -> list[DocumentSummaryResponse]:
    return list_documents(session)


@app.post(
    "/documents",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def create_document(
    response: Response,
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    payload, status_code = ingest_upload(
        session=session,
        upload=file,
        storage_service=get_storage_service(),
    )
    response.status_code = status_code
    return payload


@app.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def read_document(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentDetailResponse:
    return get_document_detail(session, document_id)


@app.get("/documents/{document_id}/runs", response_model=list[DocumentRunSummaryResponse])
def read_document_runs(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentRunSummaryResponse]:
    return list_document_runs(session, document_id)


@app.get("/documents/{document_id}/evaluations/latest", response_model=EvaluationDetailResponse)
def read_latest_document_evaluation(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> EvaluationDetailResponse:
    return get_latest_document_evaluation_detail(session, document_id)


@app.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkResponse])
def read_document_chunks(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentChunkResponse]:
    return get_active_chunks(session, document_id)


@app.get("/documents/{document_id}/tables", response_model=list[DocumentTableSummaryResponse])
def read_document_tables(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentTableSummaryResponse]:
    return get_active_tables(session, document_id)


@app.get("/documents/{document_id}/tables/{table_id}", response_model=DocumentTableDetailResponse)
def read_document_table(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentTableDetailResponse:
    return get_active_table_detail(session, document_id, table_id)


@app.get("/documents/{document_id}/figures", response_model=list[DocumentFigureSummaryResponse])
def read_document_figures(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentFigureSummaryResponse]:
    return get_active_figures(session, document_id)


@app.get(
    "/documents/{document_id}/figures/{figure_id}", response_model=DocumentFigureDetailResponse
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
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def reprocess_existing_document(
    document_id: UUID,
    response: Response,
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    response.status_code = 202
    return reprocess_document(session, document_id)


@app.get("/runs/{run_id}/failure-artifact")
def read_run_failure_artifact(
    run_id: UUID,
    session: Session = Depends(get_db_session),
):
    run = session.get(DocumentRun, run_id)
    if run is None:
        return Response(status_code=404)
    return file_response_if_exists(
        run.failure_artifact_path,
        media_type="application/json",
        path_type=Path,
        response_factory=FileResponse,
    )


@app.get("/documents/{document_id}/artifacts/json")
def read_docling_json_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_json_artifact or document.active_run_id is None:
        return Response(status_code=404)
    run = session.get(DocumentRun, document.active_run_id)
    if run is None:
        return Response(status_code=404)
    return file_response_if_exists(
        run.docling_json_path,
        path_type=Path,
        response_factory=FileResponse,
    )


@app.get("/documents/{document_id}/artifacts/yaml")
def read_yaml_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_yaml_artifact or document.active_run_id is None:
        return Response(status_code=404)
    run = session.get(DocumentRun, document.active_run_id)
    if run is None:
        return Response(status_code=404)
    return file_response_if_exists(
        run.yaml_path,
        path_type=Path,
        response_factory=FileResponse,
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


@app.get("/documents/{document_id}/tables/{table_id}/artifacts/json")
def read_table_json_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None:
        return Response(status_code=404)
    return file_response_if_exists(
        table.json_path,
        path_type=Path,
        response_factory=FileResponse,
    )


@app.get("/documents/{document_id}/tables/{table_id}/artifacts/yaml")
def read_table_yaml_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None:
        return Response(status_code=404)
    return file_response_if_exists(
        table.yaml_path,
        path_type=Path,
        response_factory=FileResponse,
    )


@app.get("/documents/{document_id}/figures/{figure_id}/artifacts/json")
def read_figure_json_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None:
        return Response(status_code=404)
    return file_response_if_exists(
        figure.json_path,
        path_type=Path,
        response_factory=FileResponse,
    )


@app.get("/documents/{document_id}/figures/{figure_id}/artifacts/yaml")
def read_figure_yaml_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None:
        return Response(status_code=404)
    return file_response_if_exists(
        figure.yaml_path,
        path_type=Path,
        response_factory=FileResponse,
    )


@app.post(
    "/search",
    response_model=list[SearchResult],
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def search_corpus(
    request: SearchRequest,
    response: Response,
    session: Session = Depends(get_db_session),
) -> list[SearchResult]:
    try:
        execution = execute_search(session, request, origin="api")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    if execution.request_id is not None:
        response.headers["X-Search-Request-Id"] = str(execution.request_id)
    return execution.results


@app.get("/search/requests/{search_request_id}", response_model=SearchRequestDetailResponse)
def read_search_request(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchRequestDetailResponse:
    return get_search_request_detail(session, search_request_id)


@app.post(
    "/search/requests/{search_request_id}/feedback",
    response_model=SearchFeedbackResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
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
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def replay_logged_search(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayResponse:
    replay = replay_search_request(session, search_request_id)
    session.commit()
    return replay


@app.get("/search/replays", response_model=list[SearchReplayRunSummaryResponse])
def read_search_replays(
    session: Session = Depends(get_db_session),
) -> list[SearchReplayRunSummaryResponse]:
    return list_search_replay_runs(session)


@app.get("/search/harnesses", response_model=list[SearchHarnessResponse])
def read_search_harnesses() -> list[SearchHarnessResponse]:
    return list_search_harness_definitions()


@app.post(
    "/search/harness-evaluations",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def create_search_harness_evaluation(
    payload: SearchHarnessEvaluationRequest,
    session: Session = Depends(get_db_session),
) -> SearchHarnessEvaluationResponse:
    try:
        evaluation = evaluate_search_harness(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return evaluation


@app.post(
    "/search/replays",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def create_search_replay_run(
    payload: SearchReplayRunRequest,
    session: Session = Depends(get_db_session),
) -> SearchReplayRunDetailResponse:
    try:
        replay_run = run_search_replay_suite(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return replay_run


@app.get("/search/replays/compare", response_model=SearchReplayComparisonResponse)
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


@app.get("/search/replays/{replay_run_id}", response_model=SearchReplayRunDetailResponse)
def read_search_replay_run(
    replay_run_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayRunDetailResponse:
    return get_search_replay_run_detail(session, replay_run_id)


@app.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
)
def chat_with_corpus(
    request: ChatRequest,
    session: Session = Depends(get_db_session),
) -> ChatResponse:
    try:
        response = answer_question(session, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return response


@app.post(
    "/chat/answers/{chat_answer_id}/feedback",
    response_model=ChatAnswerFeedbackResponse,
    dependencies=[Depends(_require_api_key_for_mutations)],
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
