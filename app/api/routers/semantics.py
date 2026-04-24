from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

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
from app.services.semantic_backfill import get_semantic_backfill_status, run_semantic_backfill
from app.services.semantics import (
    get_active_semantic_continuity,
    get_active_semantic_pass_detail,
    get_active_semantic_pass_row,
    review_active_semantic_assertion,
    review_active_semantic_assertion_category_binding,
)

router = APIRouter()


@router.get(
    "/documents/{document_id}/semantics/latest",
    response_model=DocumentSemanticPassResponse,
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_latest_document_semantics(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentSemanticPassResponse:
    ensure_semantics_enabled()
    return get_active_semantic_pass_detail(session, document_id)


@router.get(
    "/semantics/backfill/status",
    response_model=SemanticBackfillStatusResponse,
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_semantic_backfill_status(
    session: Session = Depends(get_db_session),
) -> SemanticBackfillStatusResponse:
    return get_semantic_backfill_status(session)


@router.post(
    "/semantics/backfill",
    response_model=SemanticBackfillRunResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("documents:review")),
    ],
)
def create_semantic_backfill_run(
    request: SemanticBackfillRequest,
    session: Session = Depends(get_db_session),
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
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_latest_document_semantic_continuity(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> SemanticContinuityResponse:
    ensure_semantics_enabled()
    return get_active_semantic_continuity(session, document_id)


@router.post(
    "/documents/{document_id}/semantics/latest/assertions/{assertion_id}/review",
    response_model=SemanticReviewEventResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("documents:review")),
    ],
)
def review_latest_document_semantic_assertion(
    document_id: UUID,
    assertion_id: UUID,
    request: SemanticReviewDecisionRequest,
    session: Session = Depends(get_db_session),
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
        Depends(require_api_capability("documents:review")),
    ],
)
def review_latest_document_semantic_assertion_category_binding(
    document_id: UUID,
    binding_id: UUID,
    request: SemanticReviewDecisionRequest,
    session: Session = Depends(get_db_session),
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
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_latest_semantic_json_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
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
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_latest_semantic_yaml_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
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
