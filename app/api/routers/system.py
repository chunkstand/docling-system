from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.deps import UI_DIR, api_mode_metadata, require_api_capability
from app.services.runtime import get_runtime_status
from app.services.telemetry import snapshot_metrics

router = APIRouter()


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/runtime/status",
    dependencies=[Depends(require_api_capability("system:read"))],
)
def runtime_status() -> dict:
    payload = get_runtime_status(process_identity=f"api:{os.getpid()}")
    payload.update(api_mode_metadata())
    return payload


@router.get("/metrics", dependencies=[Depends(require_api_capability("system:read"))])
def metrics() -> dict[str, float]:
    return snapshot_metrics()
