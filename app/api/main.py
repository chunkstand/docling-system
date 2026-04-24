from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import app.api.deps as deps
from app.api.deps import (
    PUBLIC_REMOTE_PATHS,
    UI_DIR,
    api_auth_is_configured,
    get_storage_service,
    resolve_api_credential,
)
from app.api.errors import api_error, structured_http_exception_handler
from app.api.routers import agent_tasks, documents, quality, search, semantics, system
from app.core.config import get_settings, is_loopback_host, resolve_api_mode
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
from app.services.runtime import register_runtime_process
from app.services.documents import (
    get_document_detail,
    get_document_run_summary,
    get_latest_document_evaluation_detail,
    ingest_upload,
    list_document_runs,
    list_documents,
    reprocess_document,
)
from app.services.eval_workbench import (
    get_eval_failure_case,
    get_eval_workbench,
    list_eval_failure_cases,
    refresh_eval_failure_cases,
    explain_latest_document_evaluation,
    explain_search_harness_evaluation,
    explain_search_replay_run,
)
from app.services.figures import get_active_figure_detail, get_active_figures
from app.services.quality import (
    get_quality_failures,
    get_quality_summary,
    get_quality_trends,
    list_quality_eval_candidates,
    list_quality_evaluations,
)
from app.services.runtime import get_runtime_status
from app.services.search import execute_search
from app.services.search_harness_evaluations import (
    evaluate_search_harness,
    get_search_harness_evaluation_detail,
    list_search_harness_definitions,
    list_search_harness_evaluations,
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
from app.services.semantic_backfill import get_semantic_backfill_status, run_semantic_backfill
from app.services.semantics import (
    get_active_semantic_continuity,
    get_active_semantic_pass_detail,
    get_active_semantic_pass_row,
    review_active_semantic_assertion,
    review_active_semantic_assertion_category_binding,
)
from app.services.tables import get_active_table_detail, get_active_tables

SEARCH_RATE_LIMIT = deps.SEARCH_RATE_LIMIT
SEARCH_RATE_WINDOW_SECONDS = deps.SEARCH_RATE_WINDOW_SECONDS
_search_request_times = deps._search_request_times


def _proxy_to_main(name: str):
    def caller(*args, **kwargs):
        return globals()[name](*args, **kwargs)

    return caller


def _bind_proxy_targets(module, names: list[str]) -> None:
    for name in names:
        setattr(module, name, _proxy_to_main(name))


deps.get_settings = _proxy_to_main("get_settings")
deps.get_storage_service = _proxy_to_main("get_storage_service")

_bind_proxy_targets(system, ["get_runtime_status"])
_bind_proxy_targets(
    quality,
    [
        "get_eval_workbench",
        "get_eval_failure_case",
        "list_eval_failure_cases",
        "refresh_eval_failure_cases",
        "get_quality_summary",
        "get_quality_failures",
        "list_quality_evaluations",
        "list_quality_eval_candidates",
        "get_quality_trends",
    ],
)
_bind_proxy_targets(
    agent_tasks,
    [
        "list_agent_task_action_definitions",
        "list_agent_tasks",
        "create_agent_task",
        "get_agent_task_analytics_summary",
        "get_agent_task_trends",
        "get_agent_verification_trends",
        "get_agent_approval_trends",
        "get_agent_task_recommendation_summary",
        "get_agent_task_recommendation_trends",
        "get_agent_task_cost_summary",
        "get_agent_task_cost_trends",
        "get_agent_task_performance_summary",
        "get_agent_task_performance_trends",
        "get_agent_task_value_density",
        "get_agent_task_decision_signals",
        "list_agent_task_workflow_summaries",
        "export_agent_task_traces",
        "get_agent_task_detail",
        "get_agent_task_context",
        "list_agent_task_outcomes",
        "create_agent_task_outcome",
        "list_agent_task_artifacts",
        "get_agent_task_artifact",
        "get_storage_service",
        "get_agent_task_verifications",
        "approve_agent_task",
        "reject_agent_task",
    ],
)
_bind_proxy_targets(
    documents,
    [
        "ingest_upload",
        "list_documents",
        "get_document_detail",
        "get_document_run_summary",
        "get_latest_document_evaluation_detail",
        "list_document_runs",
        "get_active_chunks",
        "get_active_tables",
        "get_active_table_detail",
        "get_active_figures",
        "get_active_figure_detail",
        "reprocess_document",
        "explain_latest_document_evaluation",
        "get_storage_service",
    ],
)
_bind_proxy_targets(
    semantics,
    [
        "get_semantic_backfill_status",
        "run_semantic_backfill",
        "get_active_semantic_pass_detail",
        "get_active_semantic_continuity",
        "review_active_semantic_assertion",
        "review_active_semantic_assertion_category_binding",
        "get_active_semantic_pass_row",
        "get_storage_service",
    ],
)
_bind_proxy_targets(
    search,
    [
        "execute_search",
        "get_search_request_detail",
        "get_search_request_explanation",
        "record_search_feedback",
        "replay_search_request",
        "list_search_replay_runs",
        "list_search_harness_definitions",
        "get_search_harness_descriptor",
        "list_search_harness_evaluations",
        "evaluate_search_harness",
        "get_search_harness_evaluation_detail",
        "run_search_replay_suite",
        "compare_search_replay_runs",
        "get_search_replay_run_detail",
        "explain_search_harness_evaluation",
        "explain_search_replay_run",
        "answer_question",
        "record_chat_answer_feedback",
    ],
)


def _validate_runtime_bind_settings() -> tuple[str, int]:
    settings = get_settings()
    resolved_mode = resolve_api_mode(settings)
    auth_is_configured = api_auth_is_configured(settings)
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


def create_app() -> FastAPI:
    app = FastAPI(title="Docling System", version="0.1.0", lifespan=lifespan)
    app.add_exception_handler(HTTPException, structured_http_exception_handler)
    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

    @app.middleware("http")
    async def require_remote_api_key_for_reads(request: Request, call_next):
        settings = get_settings()
        if resolve_api_mode(settings) != "remote":
            return await call_next(request)
        if request.method not in {"GET", "HEAD"}:
            return await call_next(request)
        if request.url.path in PUBLIC_REMOTE_PATHS:
            return await call_next(request)
        credential = resolve_api_credential(
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

    app.include_router(system.router)
    app.include_router(quality.router)
    app.include_router(agent_tasks.router)
    app.include_router(documents.router)
    app.include_router(semantics.router)
    app.include_router(search.router)
    return app


app = create_app()


def run() -> None:
    host, port = _validate_runtime_bind_settings()
    uvicorn.run("app.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
