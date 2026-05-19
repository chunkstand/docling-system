from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequestExplanationResult(BaseModel):
    rank: int
    result_type: str
    score: float
    source_filename: str
    document_id: UUID
    run_id: UUID
    chunk_id: UUID | None = None
    table_id: UUID | None = None
    label: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    base_rank: int | None = None
    rerank_features: dict = Field(default_factory=dict)


class SearchRequestDiagnosis(BaseModel):
    category: str
    summary: str
    contributing_factors: list[str] = Field(default_factory=list)
    evidence: dict = Field(default_factory=dict)


class SearchRequestExplanationResponse(BaseModel):
    schema_name: str = "search_request_explanation"
    schema_version: str = "1.0"
    search_request_id: UUID
    parent_search_request_id: UUID | None = None
    evaluation_id: UUID | None = None
    run_id: UUID | None = None
    origin: str
    query: str
    mode: str
    filters: dict = Field(default_factory=dict)
    requested_mode: str
    served_mode: str
    limit: int
    tabular_query: bool = False
    harness_name: str = "default_v1"
    reranker_name: str
    reranker_version: str = "v1"
    retrieval_profile_name: str = "default_v1"
    harness_config: dict = Field(default_factory=dict)
    embedding_status: str
    embedding_error: str | None = None
    fallback_reason: str | None = None
    keyword_candidate_count: int = 0
    keyword_strict_candidate_count: int = 0
    semantic_candidate_count: int = 0
    metadata_candidate_count: int = 0
    span_candidate_count: int = 0
    context_expansion_count: int = 0
    candidate_count: int = 0
    result_count: int = 0
    table_hit_count: int = 0
    candidate_source_breakdown: dict = Field(default_factory=dict)
    query_understanding: dict = Field(default_factory=dict)
    top_result_snapshot: list[SearchRequestExplanationResult] = Field(default_factory=list)
    diagnosis: SearchRequestDiagnosis
    recommended_next_action: str
    evidence_refs: list[dict] = Field(default_factory=list)
    created_at: datetime


__all__ = [
    "SearchRequestDiagnosis",
    "SearchRequestExplanationResponse",
    "SearchRequestExplanationResult",
]
