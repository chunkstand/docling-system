from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse

import app.api.capabilities as api_capabilities
from app.api.deps import UI_DIR, api_mode_metadata, require_api_capability
from app.api.errors import api_error
from app.services.capabilities import system_governance

router = APIRouter()
get_runtime_status = system_governance.get_runtime_status
snapshot_metrics = system_governance.snapshot_metrics
get_architecture_inspection_report = system_governance.get_architecture_inspection_report
summarize_architecture_measurements = system_governance.summarize_architecture_measurements


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/runtime/status",
    dependencies=[Depends(require_api_capability(api_capabilities.SYSTEM_READ))],
)
def runtime_status() -> dict:
    payload = get_runtime_status(process_identity=f"api:{os.getpid()}")
    payload.update(api_mode_metadata())
    return payload


@router.get(
    "/metrics",
    dependencies=[Depends(require_api_capability(api_capabilities.SYSTEM_READ))],
)
def metrics() -> dict[str, float]:
    return snapshot_metrics()


@router.get(
    "/architecture/inspection",
    dependencies=[Depends(require_api_capability(api_capabilities.SYSTEM_READ))],
)
def architecture_inspection() -> dict[str, Any]:
    try:
        return get_architecture_inspection_report()
    except ValueError as exc:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "architecture_inspection_failed",
            str(exc),
        ) from exc


@router.get(
    "/architecture/measurements/summary",
    dependencies=[Depends(require_api_capability(api_capabilities.SYSTEM_READ))],
)
def architecture_measurement_summary() -> dict[str, Any]:
    try:
        return summarize_architecture_measurements()
    except ValueError as exc:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "architecture_measurement_history_invalid",
            str(exc),
        ) from exc
