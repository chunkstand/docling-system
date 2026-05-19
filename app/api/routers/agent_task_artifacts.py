from __future__ import annotations

import hashlib
import json
from typing import Annotated
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import get_storage_service, require_api_capability, storage_file_response
from app.api.errors import api_error
from app.api.routers.agent_task_route_services import service_from_parent
from app.db.session import get_db_session
from app.schemas.agent_task_core import AgentTaskArtifactResponse, TaskContextEnvelope
from app.services.capabilities import agent_orchestration
from app.services.storage import StorageService

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND = "technical_report_prov_export"

get_agent_task_context = agent_orchestration.get_agent_task_context
get_agent_task_audit_bundle = agent_orchestration.get_agent_task_audit_bundle
get_agent_task_evidence_manifest = agent_orchestration.get_agent_task_evidence_manifest
get_agent_task_evidence_trace = agent_orchestration.get_agent_task_evidence_trace
get_agent_task_provenance_export = agent_orchestration.get_agent_task_provenance_export
list_agent_task_artifacts = agent_orchestration.list_agent_task_artifacts
get_agent_task_artifact = agent_orchestration.get_agent_task_artifact
get_agent_task_detail = agent_orchestration.get_agent_task_detail


def _storage_service_dep() -> StorageService:
    return service_from_parent("get_storage_service", get_storage_service)()


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
    "/agent-tasks/{task_id}/context",
    response_model=TaskContextEnvelope,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_context_route(
    task_id: UUID,
    session: DbSession,
    format: str = "json",
):
    context = service_from_parent("get_agent_task_context", get_agent_task_context)(
        session,
        task_id,
    )
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
        return service_from_parent("get_agent_task_audit_bundle", get_agent_task_audit_bundle)(
            session,
            task_id,
        )
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
        response = service_from_parent(
            "get_agent_task_evidence_manifest",
            get_agent_task_evidence_manifest,
        )(session, task_id)
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
        response = service_from_parent(
            "get_agent_task_evidence_trace",
            get_agent_task_evidence_trace,
        )(session, task_id)
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
        response = service_from_parent(
            "get_agent_task_provenance_export",
            get_agent_task_provenance_export,
        )(
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
    "/agent-tasks/{task_id}/artifacts",
    response_model=list[AgentTaskArtifactResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_artifacts(
    task_id: UUID,
    session: DbSession,
    limit: int = 20,
) -> list[AgentTaskArtifactResponse]:
    return service_from_parent("list_agent_task_artifacts", list_agent_task_artifacts)(
        session,
        task_id,
        limit=limit,
    )


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
    artifact = service_from_parent("get_agent_task_artifact", get_agent_task_artifact)(
        session,
        task_id,
        artifact_id,
    )
    if getattr(artifact, "artifact_kind", None) == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND:
        return _frozen_prov_artifact_response(artifact, storage_service)
    file_response = storage_file_response(artifact.storage_path, media_type="application/json")
    if file_response.status_code != 404:
        return file_response
    return JSONResponse(artifact.payload_json or {})


@router.get(
    "/agent-tasks/{task_id}/failure-artifact",
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_failure_artifact(
    task_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
):
    service_from_parent("get_agent_task_detail", get_agent_task_detail)(session, task_id)
    return storage_file_response(
        storage_service.build_agent_task_failure_artifact_path(task_id),
        media_type="application/json",
        not_found_detail="Agent task failure artifact not found.",
        not_found_error_code="agent_task_failure_artifact_not_found",
        not_found_context={"task_id": str(task_id)},
    )
