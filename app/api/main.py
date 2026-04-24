from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles

import app.api.deps as deps
from app.api.errors import api_error, structured_http_exception_handler
from app.api.routers import agent_tasks, documents, quality, search, semantics, system
from app.core.config import is_loopback_host, resolve_api_mode
from app.services.runtime import register_runtime_process


def _validate_runtime_bind_settings() -> tuple[str, int]:
    settings = deps.get_settings()
    resolved_mode = resolve_api_mode(settings)
    auth_is_configured = deps.api_auth_is_configured(settings)
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
    app.mount("/ui", StaticFiles(directory=deps.UI_DIR), name="ui")

    @app.middleware("http")
    async def require_remote_api_key_for_reads(request: Request, call_next):
        settings = deps.get_settings()
        if resolve_api_mode(settings) != "remote":
            return await call_next(request)
        if request.method not in {"GET", "HEAD"}:
            return await call_next(request)
        if request.url.path in deps.PUBLIC_REMOTE_PATHS:
            return await call_next(request)
        credential = deps.resolve_api_credential(
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
