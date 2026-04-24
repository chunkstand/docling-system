from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import DocumentRunSemanticPass
from app.schemas.semantic_backfill import (
    SemanticBackfillRequest,
    SemanticBackfillRunResponse,
    SemanticBackfillStatusResponse,
)
from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticContinuityResponse,
    SemanticReviewEventResponse,
)
from app.services import semantic_backfill
from app.services import semantics as semantic_service
from app.services.storage import StorageService


class SemanticsCapability(Protocol):
    def get_active_semantic_pass_detail(
        self,
        session: Session,
        document_id: UUID,
    ) -> DocumentSemanticPassResponse: ...

    def get_active_semantic_pass_row(
        self,
        session: Session,
        document_id: UUID,
    ) -> DocumentRunSemanticPass | None: ...

    def get_active_semantic_continuity(
        self,
        session: Session,
        document_id: UUID,
    ) -> SemanticContinuityResponse: ...

    def get_semantic_backfill_status(self, session: Session) -> SemanticBackfillStatusResponse: ...

    def run_semantic_backfill(
        self,
        session: Session,
        request: SemanticBackfillRequest,
        *,
        storage_service: StorageService | None = None,
    ) -> SemanticBackfillRunResponse: ...

    def review_active_semantic_assertion(
        self,
        session: Session,
        document_id: UUID,
        assertion_id: UUID,
        *,
        review_status: str,
        review_note: str | None,
        reviewed_by: str | None,
        storage_service: StorageService,
    ) -> SemanticReviewEventResponse: ...

    def review_active_semantic_assertion_category_binding(
        self,
        session: Session,
        document_id: UUID,
        binding_id: UUID,
        *,
        review_status: str,
        review_note: str | None,
        reviewed_by: str | None,
        storage_service: StorageService,
    ) -> SemanticReviewEventResponse: ...


class ServicesSemanticsCapability:
    def get_active_semantic_pass_detail(
        self,
        session: Session,
        document_id: UUID,
    ) -> DocumentSemanticPassResponse:
        return semantic_service.get_active_semantic_pass_detail(session, document_id)

    def get_active_semantic_pass_row(
        self,
        session: Session,
        document_id: UUID,
    ) -> DocumentRunSemanticPass | None:
        return semantic_service.get_active_semantic_pass_row(session, document_id)

    def get_active_semantic_continuity(
        self,
        session: Session,
        document_id: UUID,
    ) -> SemanticContinuityResponse:
        return semantic_service.get_active_semantic_continuity(session, document_id)

    def get_semantic_backfill_status(self, session: Session) -> SemanticBackfillStatusResponse:
        return semantic_backfill.get_semantic_backfill_status(session)

    def run_semantic_backfill(
        self,
        session: Session,
        request: SemanticBackfillRequest,
        *,
        storage_service: StorageService | None = None,
    ) -> SemanticBackfillRunResponse:
        return semantic_backfill.run_semantic_backfill(
            session,
            request,
            storage_service=storage_service,
        )

    def review_active_semantic_assertion(
        self,
        session: Session,
        document_id: UUID,
        assertion_id: UUID,
        *,
        review_status: str,
        review_note: str | None,
        reviewed_by: str | None,
        storage_service: StorageService,
    ) -> SemanticReviewEventResponse:
        return semantic_service.review_active_semantic_assertion(
            session,
            document_id,
            assertion_id,
            review_status=review_status,
            review_note=review_note,
            reviewed_by=reviewed_by,
            storage_service=storage_service,
        )

    def review_active_semantic_assertion_category_binding(
        self,
        session: Session,
        document_id: UUID,
        binding_id: UUID,
        *,
        review_status: str,
        review_note: str | None,
        reviewed_by: str | None,
        storage_service: StorageService,
    ) -> SemanticReviewEventResponse:
        return semantic_service.review_active_semantic_assertion_category_binding(
            session,
            document_id,
            binding_id,
            review_status=review_status,
            review_note=review_note,
            reviewed_by=reviewed_by,
            storage_service=storage_service,
        )


semantics: SemanticsCapability = ServicesSemanticsCapability()
