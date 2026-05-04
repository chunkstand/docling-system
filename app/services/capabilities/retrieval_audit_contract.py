from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import (
    AuditBundleExportResponse,
    AuditBundleValidationReceiptRequest,
    AuditBundleValidationReceiptResponse,
    AuditBundleValidationReceiptSummaryResponse,
    RetrievalTrainingRunAuditBundleRequest,
    SearchHarnessReleaseAuditBundleRequest,
)
from app.services.storage import StorageService


class RetrievalAuditCapability(Protocol):
    def create_search_harness_release_audit_bundle(
        self,
        session: Session,
        release_id: UUID,
        payload: SearchHarnessReleaseAuditBundleRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def get_latest_search_harness_release_audit_bundle(
        self,
        session: Session,
        release_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def create_retrieval_training_run_audit_bundle(
        self,
        session: Session,
        training_run_id: UUID,
        payload: RetrievalTrainingRunAuditBundleRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def get_latest_retrieval_training_run_audit_bundle(
        self,
        session: Session,
        training_run_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def get_audit_bundle_export(
        self,
        session: Session,
        bundle_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def create_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        payload: AuditBundleValidationReceiptRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse: ...

    def list_audit_bundle_validation_receipts(
        self,
        session: Session,
        bundle_id: UUID,
    ) -> list[AuditBundleValidationReceiptSummaryResponse]: ...

    def get_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        receipt_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse: ...

    def get_latest_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse: ...
