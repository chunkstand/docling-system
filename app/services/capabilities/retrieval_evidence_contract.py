from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session


class RetrievalEvidenceCapability(Protocol):
    def get_search_evidence_package(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> dict: ...

    def export_search_evidence_package(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> dict: ...

    def get_search_evidence_package_export_trace(
        self,
        session: Session,
        evidence_package_export_id: UUID,
    ) -> dict: ...
