from __future__ import annotations

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
