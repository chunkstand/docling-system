from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import (
    SearchReplayComparisonResponse,
    SearchReplayResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
)


class RetrievalReplayCapability(Protocol):
    def replay_search_request(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchReplayResponse: ...

    def list_search_replay_runs(
        self,
        session: Session,
    ) -> list[SearchReplayRunSummaryResponse]: ...

    def run_search_replay_suite(
        self,
        session: Session,
        payload: SearchReplayRunRequest,
    ) -> SearchReplayRunDetailResponse: ...

    def compare_search_replay_runs(
        self,
        session: Session,
        *,
        baseline_replay_run_id: UUID,
        candidate_replay_run_id: UUID,
    ) -> SearchReplayComparisonResponse: ...

    def get_search_replay_run_detail(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> SearchReplayRunDetailResponse: ...

    def explain_search_replay_run(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> dict: ...
