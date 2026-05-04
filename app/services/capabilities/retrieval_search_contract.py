from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import (
    SearchRequest,
    SearchRequestDetailResponse,
    SearchRequestExplanationResponse,
)
from app.services import search


class RetrievalSearchCapability(Protocol):
    def execute_search(
        self,
        session: Session,
        request: SearchRequest,
        *,
        origin: str,
        run_id: UUID | None = None,
        parent_search_request_id: UUID | None = None,
        evaluation_id: UUID | None = None,
    ) -> search.SearchExecution: ...

    def get_search_request_detail(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestDetailResponse: ...

    def get_search_request_explanation(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestExplanationResponse: ...
