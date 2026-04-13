from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.db.models import DocumentFigure, DocumentRun, DocumentTable
from app.db.session import get_db_session
from app.schemas.agent_tasks import (
    AgentTaskActionDefinitionResponse,
    AgentTaskAnalyticsSummaryResponse,
    AgentTaskApprovalRequest,
    AgentTaskArtifactResponse,
    AgentTaskCreateRequest,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskRejectionRequest,
    AgentTaskSummaryResponse,
    AgentTaskTraceExportResponse,
    AgentTaskVerificationResponse,
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
from app.services.agent_task_verifications import get_agent_task_verifications
from app.services.agent_tasks import (
    approve_agent_task,
    create_agent_task,
    create_agent_task_outcome,
    export_agent_task_traces,
    get_agent_task_analytics_summary,
    get_agent_task_detail,
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

app = FastAPI(title="Docling System", version="0.1.0")
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


@app.get("/agent-tasks/{task_id}/outcomes", response_model=list[AgentTaskOutcomeResponse])
def read_agent_task_outcomes(
    task_id: UUID,
    limit: int = 20,
    session: Session = Depends(get_db_session),
) -> list[AgentTaskOutcomeResponse]:
    return list_agent_task_outcomes(session, task_id, limit=limit)


@app.post("/agent-tasks/{task_id}/outcomes", response_model=AgentTaskOutcomeResponse)
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
    if artifact.storage_path and Path(artifact.storage_path).exists():
        return FileResponse(Path(artifact.storage_path), media_type="application/json")
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
    if not failure_artifact_path or not Path(failure_artifact_path).exists():
        return Response(status_code=404)
    return FileResponse(Path(failure_artifact_path), media_type="application/json")


@app.post("/agent-tasks/{task_id}/approve", response_model=AgentTaskDetailResponse)
def approve_agent_task_route(
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return approve_agent_task(session, task_id, payload)


@app.post("/agent-tasks/{task_id}/reject", response_model=AgentTaskDetailResponse)
def reject_agent_task_route(
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
    session: Session = Depends(get_db_session),
) -> AgentTaskDetailResponse:
    return reject_agent_task(session, task_id, payload)


@app.get("/documents", response_model=list[DocumentSummaryResponse])
def read_documents(session: Session = Depends(get_db_session)) -> list[DocumentSummaryResponse]:
    return list_documents(session)


@app.post("/documents", response_model=DocumentUploadResponse)
async def create_document(
    response: Response,
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    payload, status_code = await ingest_upload(
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


@app.post("/documents/{document_id}/reprocess", response_model=DocumentUploadResponse)
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
    if run is None or not run.failure_artifact_path or not Path(run.failure_artifact_path).exists():
        return Response(status_code=404)
    return FileResponse(Path(run.failure_artifact_path), media_type="application/json")


@app.get("/documents/{document_id}/artifacts/json")
def read_docling_json_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_json_artifact or document.active_run_id is None:
        return Response(status_code=404)
    run = session.get(DocumentRun, document.active_run_id)
    if run is None or not run.docling_json_path:
        return Response(status_code=404)
    return FileResponse(Path(run.docling_json_path))


@app.get("/documents/{document_id}/artifacts/yaml")
def read_yaml_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_yaml_artifact or document.active_run_id is None:
        return Response(status_code=404)
    run = session.get(DocumentRun, document.active_run_id)
    if run is None or not run.yaml_path:
        return Response(status_code=404)
    return FileResponse(Path(run.yaml_path))


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
    if table is None or not table.json_path:
        return Response(status_code=404)
    return FileResponse(Path(table.json_path))


@app.get("/documents/{document_id}/tables/{table_id}/artifacts/yaml")
def read_table_yaml_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None or not table.yaml_path:
        return Response(status_code=404)
    return FileResponse(Path(table.yaml_path))


@app.get("/documents/{document_id}/figures/{figure_id}/artifacts/json")
def read_figure_json_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None or not figure.json_path:
        return Response(status_code=404)
    return FileResponse(Path(figure.json_path))


@app.get("/documents/{document_id}/figures/{figure_id}/artifacts/yaml")
def read_figure_yaml_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None or not figure.yaml_path:
        return Response(status_code=404)
    return FileResponse(Path(figure.yaml_path))


@app.post("/search", response_model=list[SearchResult])
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
)
def create_search_feedback(
    search_request_id: UUID,
    payload: SearchFeedbackCreateRequest,
    session: Session = Depends(get_db_session),
) -> SearchFeedbackResponse:
    feedback = record_search_feedback(session, search_request_id, payload)
    session.commit()
    return feedback


@app.post("/search/requests/{search_request_id}/replay", response_model=SearchReplayResponse)
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


@app.post("/search/harness-evaluations", response_model=SearchHarnessEvaluationResponse)
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


@app.post("/search/replays", response_model=SearchReplayRunDetailResponse)
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


@app.post("/chat", response_model=ChatResponse)
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
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
