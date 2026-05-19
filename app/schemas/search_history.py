from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.search_core import SearchLoggedResultResponse


class SearchFeedbackCreateRequest(BaseModel):
    feedback_type: str = Field(
        pattern="^(relevant|irrelevant|missing_table|missing_chunk|no_answer)$"
    )
    result_rank: int | None = Field(default=None, ge=1)
    note: str | None = None


class SearchFeedbackResponse(BaseModel):
    feedback_id: UUID
    search_request_id: UUID
    search_request_result_id: UUID | None = None
    result_rank: int | None = None
    feedback_type: str
    note: str | None = None
    created_at: datetime


class SearchRequestDetailResponse(BaseModel):
    search_request_id: UUID
    parent_search_request_id: UUID | None = None
    evaluation_id: UUID | None = None
    run_id: UUID | None = None
    origin: str
    query: str
    mode: str
    filters: dict = Field(default_factory=dict)
    details: dict = Field(default_factory=dict)
    limit: int
    tabular_query: bool = False
    harness_name: str = "default_v1"
    reranker_name: str
    reranker_version: str = "v1"
    retrieval_profile_name: str = "default_v1"
    harness_config: dict = Field(default_factory=dict)
    embedding_status: str
    embedding_error: str | None = None
    candidate_count: int = 0
    result_count: int = 0
    table_hit_count: int = 0
    duration_ms: float | None = None
    created_at: datetime
    feedback: list[SearchFeedbackResponse] = Field(default_factory=list)
    results: list[SearchLoggedResultResponse] = Field(default_factory=list)


class SearchReplayDiffResponse(BaseModel):
    overlap_count: int = 0
    added_count: int = 0
    removed_count: int = 0
    top_result_changed: bool = False
    max_rank_shift: int = 0


class SearchReplayResponse(BaseModel):
    original_request: SearchRequestDetailResponse
    replay_request: SearchRequestDetailResponse
    diff: SearchReplayDiffResponse


__all__ = [
    "SearchFeedbackCreateRequest",
    "SearchFeedbackResponse",
    "SearchReplayDiffResponse",
    "SearchReplayResponse",
    "SearchRequestDetailResponse",
]
