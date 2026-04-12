from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PageRangeFilter(BaseModel):
    page_from: int
    page_to: int


class SearchFilters(BaseModel):
    document_id: UUID | None = None
    page_range: PageRangeFilter | None = None
    result_type: str | None = Field(default=None, pattern="^(chunk|table)$")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    mode: str = Field(pattern="^(keyword|semantic|hybrid)$")
    filters: SearchFilters | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchScores(BaseModel):
    keyword_score: float | None = None
    semantic_score: float | None = None
    hybrid_score: float | None = None


class SearchResult(BaseModel):
    result_type: str
    document_id: UUID
    run_id: UUID
    score: float
    chunk_id: UUID | None = None
    chunk_text: str | None = None
    heading: str | None = None
    table_id: UUID | None = None
    table_title: str | None = None
    table_heading: str | None = None
    table_preview: str | None = None
    row_count: int | None = None
    col_count: int | None = None
    page_from: int | None
    page_to: int | None
    source_filename: str
    scores: SearchScores


class SearchLoggedResultResponse(SearchResult):
    rank: int
    base_rank: int | None = None
    rerank_features: dict = Field(default_factory=dict)


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
    reranker_name: str
    embedding_status: str
    embedding_error: str | None = None
    candidate_count: int = 0
    result_count: int = 0
    table_hit_count: int = 0
    duration_ms: float | None = None
    created_at: datetime
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
