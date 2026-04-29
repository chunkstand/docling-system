from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api import deps as api_deps
from app.api.deps import require_api_capability, require_api_key_for_mutations, response_field
from app.api.routers.search_route_services import resolve_search_service
from app.db.session import get_db_session
from app.schemas.search import (
    AuditBundleExportResponse,
    AuditBundleValidationReceiptRequest,
    AuditBundleValidationReceiptResponse,
    AuditBundleValidationReceiptSummaryResponse,
    RetrievalTrainingRunAuditBundleRequest,
    SearchHarnessReleaseAuditBundleRequest,
)
from app.services.capabilities import retrieval
from app.services.storage import StorageService

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]

get_storage_service = api_deps.get_storage_service


def _search_audit_storage_service_dep() -> StorageService:
    return resolve_search_service("get_storage_service", get_storage_service)()


StorageDep = Annotated[StorageService, Depends(_search_audit_storage_service_dep)]

create_search_harness_release_audit_bundle = retrieval.create_search_harness_release_audit_bundle
get_latest_search_harness_release_audit_bundle = (
    retrieval.get_latest_search_harness_release_audit_bundle
)
create_retrieval_training_run_audit_bundle = retrieval.create_retrieval_training_run_audit_bundle
get_latest_retrieval_training_run_audit_bundle = (
    retrieval.get_latest_retrieval_training_run_audit_bundle
)
get_audit_bundle_export = retrieval.get_audit_bundle_export
create_audit_bundle_validation_receipt = retrieval.create_audit_bundle_validation_receipt
list_audit_bundle_validation_receipts = retrieval.list_audit_bundle_validation_receipts
get_audit_bundle_validation_receipt = retrieval.get_audit_bundle_validation_receipt
get_latest_audit_bundle_validation_receipt = retrieval.get_latest_audit_bundle_validation_receipt


@router.post(
    "/search/harness-releases/{release_id}/audit-bundles",
    response_model=AuditBundleExportResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_release_audit_bundle_route(
    response: Response,
    release_id: UUID,
    payload: SearchHarnessReleaseAuditBundleRequest,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    bundle = resolve_search_service(
        "create_search_harness_release_audit_bundle",
        create_search_harness_release_audit_bundle,
    )(
        session,
        release_id,
        payload,
        storage_service=storage_service,
    )
    session.commit()
    bundle_id = response_field(bundle, "bundle_id")
    response.headers["Location"] = f"/search/audit-bundles/{bundle_id}"
    return bundle


@router.get(
    "/search/harness-releases/{release_id}/audit-bundles/latest",
    response_model=AuditBundleExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_search_harness_release_audit_bundle(
    release_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    return resolve_search_service(
        "get_latest_search_harness_release_audit_bundle",
        get_latest_search_harness_release_audit_bundle,
    )(
        session,
        release_id,
        storage_service=storage_service,
    )


@router.post(
    "/search/retrieval-training-runs/{training_run_id}/audit-bundles",
    response_model=AuditBundleExportResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_retrieval_training_run_audit_bundle_route(
    response: Response,
    training_run_id: UUID,
    payload: RetrievalTrainingRunAuditBundleRequest,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    bundle = resolve_search_service(
        "create_retrieval_training_run_audit_bundle",
        create_retrieval_training_run_audit_bundle,
    )(
        session,
        training_run_id,
        payload,
        storage_service=storage_service,
    )
    session.commit()
    bundle_id = response_field(bundle, "bundle_id")
    response.headers["Location"] = f"/search/audit-bundles/{bundle_id}"
    return bundle


@router.get(
    "/search/retrieval-training-runs/{training_run_id}/audit-bundles/latest",
    response_model=AuditBundleExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_retrieval_training_run_audit_bundle(
    training_run_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    return resolve_search_service(
        "get_latest_retrieval_training_run_audit_bundle",
        get_latest_retrieval_training_run_audit_bundle,
    )(
        session,
        training_run_id,
        storage_service=storage_service,
    )


@router.get(
    "/search/audit-bundles/{bundle_id}",
    response_model=AuditBundleExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_audit_bundle_export(
    bundle_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    return resolve_search_service("get_audit_bundle_export", get_audit_bundle_export)(
        session,
        bundle_id,
        storage_service=storage_service,
    )


@router.post(
    "/search/audit-bundles/{bundle_id}/validation-receipts",
    response_model=AuditBundleValidationReceiptResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_audit_bundle_validation_receipt_route(
    response: Response,
    bundle_id: UUID,
    payload: AuditBundleValidationReceiptRequest,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleValidationReceiptResponse:
    receipt = resolve_search_service(
        "create_audit_bundle_validation_receipt",
        create_audit_bundle_validation_receipt,
    )(
        session,
        bundle_id,
        payload,
        storage_service=storage_service,
    )
    session.commit()
    receipt_id = response_field(receipt, "receipt_id")
    response.headers["Location"] = (
        f"/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}"
    )
    return receipt


@router.get(
    "/search/audit-bundles/{bundle_id}/validation-receipts",
    response_model=list[AuditBundleValidationReceiptSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def list_audit_bundle_validation_receipts_route(
    bundle_id: UUID,
    session: DbSession,
) -> list[AuditBundleValidationReceiptSummaryResponse]:
    return resolve_search_service(
        "list_audit_bundle_validation_receipts",
        list_audit_bundle_validation_receipts,
    )(session, bundle_id)


@router.get(
    "/search/audit-bundles/{bundle_id}/validation-receipts/latest",
    response_model=AuditBundleValidationReceiptResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_audit_bundle_validation_receipt(
    bundle_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleValidationReceiptResponse:
    return resolve_search_service(
        "get_latest_audit_bundle_validation_receipt",
        get_latest_audit_bundle_validation_receipt,
    )(
        session,
        bundle_id,
        storage_service=storage_service,
    )


@router.get(
    "/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}",
    response_model=AuditBundleValidationReceiptResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_audit_bundle_validation_receipt(
    bundle_id: UUID,
    receipt_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleValidationReceiptResponse:
    return resolve_search_service(
        "get_audit_bundle_validation_receipt",
        get_audit_bundle_validation_receipt,
    )(
        session,
        bundle_id,
        receipt_id,
        storage_service=storage_service,
    )


__all__ = ["router"]
