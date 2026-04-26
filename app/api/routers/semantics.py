from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    ensure_semantics_enabled,
    get_storage_service,
    require_api_capability,
    require_api_key_for_mutations,
    storage_file_response,
)
from app.api.errors import api_error
from app.db.session import get_db_session
from app.schemas.semantic_backfill import (
    SemanticBackfillRequest,
    SemanticBackfillRunResponse,
    SemanticBackfillStatusResponse,
)
from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticContinuityResponse,
    SemanticReviewDecisionRequest,
    SemanticReviewEventResponse,
)
from app.services.capabilities import semantics

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]

get_active_semantic_pass_detail = semantics.get_active_semantic_pass_detail
get_active_semantic_pass_row = semantics.get_active_semantic_pass_row
get_active_semantic_continuity = semantics.get_active_semantic_continuity
get_semantic_backfill_status = semantics.get_semantic_backfill_status
run_semantic_backfill = semantics.run_semantic_backfill
review_active_semantic_assertion = semantics.review_active_semantic_assertion
review_active_semantic_assertion_category_binding = (
    semantics.review_active_semantic_assertion_category_binding
)


@router.get(
    "/documents/{document_id}/semantics/latest",
    response_model=DocumentSemanticPassResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.DOCUMENTS_INSPECT))],
)
def read_latest_document_semantics(
    document_id: UUID,
    session: DbSession,
) -> DocumentSemanticPassResponse:
    ensure_semantics_enabled()
    return get_active_semantic_pass_detail(session, document_id)


@router.get(
    "/semantics/backfill/status",
    response_model=SemanticBackfillStatusResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.DOCUMENTS_INSPECT))],
)
def read_semantic_backfill_status(
    session: DbSession,
) -> SemanticBackfillStatusResponse:
    return get_semantic_backfill_status(session)


@router.post(
    "/semantics/backfill",
    response_model=SemanticBackfillRunResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.DOCUMENTS_REVIEW)),
    ],
)
def create_semantic_backfill_run(
    request: SemanticBackfillRequest,
    session: DbSession,
) -> SemanticBackfillRunResponse:
    ensure_semantics_enabled()
    try:
        return run_semantic_backfill(
            session,
            request,
            storage_service=get_storage_service(),
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_semantic_backfill_request",
            str(exc),
        ) from exc


@router.get(
    "/documents/{document_id}/semantics/latest/continuity",
    response_model=SemanticContinuityResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.DOCUMENTS_INSPECT))],
)
def read_latest_document_semantic_continuity(
    document_id: UUID,
    session: DbSession,
) -> SemanticContinuityResponse:
    ensure_semantics_enabled()
    return get_active_semantic_continuity(session, document_id)


@router.post(
    "/documents/{document_id}/semantics/latest/assertions/{assertion_id}/review",
    response_model=SemanticReviewEventResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.DOCUMENTS_REVIEW)),
    ],
)
def review_latest_document_semantic_assertion(
    document_id: UUID,
    assertion_id: UUID,
    request: SemanticReviewDecisionRequest,
    session: DbSession,
) -> SemanticReviewEventResponse:
    ensure_semantics_enabled()
    return review_active_semantic_assertion(
        session,
        document_id,
        assertion_id,
        review_status=request.review_status,
        review_note=request.review_note,
        reviewed_by=request.reviewed_by,
        storage_service=get_storage_service(),
    )


@router.post(
    "/documents/{document_id}/semantics/latest/assertion-category-bindings/{binding_id}/review",
    response_model=SemanticReviewEventResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.DOCUMENTS_REVIEW)),
    ],
)
def review_latest_document_semantic_assertion_category_binding(
    document_id: UUID,
    binding_id: UUID,
    request: SemanticReviewDecisionRequest,
    session: DbSession,
) -> SemanticReviewEventResponse:
    ensure_semantics_enabled()
    return review_active_semantic_assertion_category_binding(
        session,
        document_id,
        binding_id,
        review_status=request.review_status,
        review_note=request.review_note,
        reviewed_by=request.reviewed_by,
        storage_service=get_storage_service(),
    )


@router.get(
    "/documents/{document_id}/semantics/latest/artifacts/json",
    dependencies=[Depends(require_api_capability(api_capabilities.DOCUMENTS_INSPECT))],
)
def read_latest_semantic_json_artifact(
    document_id: UUID,
    session: DbSession,
):
    ensure_semantics_enabled()
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )
    return storage_file_response(
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


@router.get(
    "/documents/{document_id}/semantics/latest/artifacts/yaml",
    dependencies=[Depends(require_api_capability(api_capabilities.DOCUMENTS_INSPECT))],
)
def read_latest_semantic_yaml_artifact(
    document_id: UUID,
    session: DbSession,
):
    ensure_semantics_enabled()
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )
    return storage_file_response(
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
