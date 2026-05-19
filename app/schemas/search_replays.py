from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchReplayRunRequest(BaseModel):
    source_type: str = Field(
        pattern=(
            "^(evaluation_queries|live_search_gaps|feedback|"
            "cross_document_prose_regressions|technical_report_claim_feedback)$"
        )
    )
    limit: int = Field(default=25, ge=1, le=200)
    harness_name: str | None = None


class SearchReplayRunSummaryResponse(BaseModel):
    replay_run_id: UUID
    source_type: str
    status: str
    harness_name: str = "default_v1"
    reranker_name: str = "linear_feature_reranker"
    reranker_version: str = "v1"
    retrieval_profile_name: str = "default_v1"
    harness_config: dict = Field(default_factory=dict)
    query_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    zero_result_count: int = 0
    table_hit_count: int = 0
    top_result_changes: int = 0
    max_rank_shift: int = 0
    rank_metrics: dict = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None


class SearchReplayQueryResponse(BaseModel):
    replay_query_id: UUID
    source_search_request_id: UUID | None = None
    replay_search_request_id: UUID | None = None
    feedback_id: UUID | None = None
    evaluation_query_id: UUID | None = None
    query_text: str
    mode: str
    filters: dict = Field(default_factory=dict)
    expected_result_type: str | None = None
    expected_top_n: int | None = None
    passed: bool
    result_count: int = 0
    table_hit_count: int = 0
    overlap_count: int = 0
    added_count: int = 0
    removed_count: int = 0
    top_result_changed: bool = False
    max_rank_shift: int = 0
    details: dict = Field(default_factory=dict)
    created_at: datetime


class SearchReplayRunDetailResponse(SearchReplayRunSummaryResponse):
    summary: dict = Field(default_factory=dict)
    query_results: list[SearchReplayQueryResponse] = Field(default_factory=list)


class SearchReplayComparisonRowResponse(BaseModel):
    query_text: str
    mode: str
    filters: dict = Field(default_factory=dict)
    baseline_passed: bool
    candidate_passed: bool
    baseline_result_count: int = 0
    candidate_result_count: int = 0
    baseline_top_result_changed: bool = False
    candidate_top_result_changed: bool = False


class SearchReplayComparisonResponse(BaseModel):
    baseline_replay_run_id: UUID
    candidate_replay_run_id: UUID
    shared_query_count: int = 0
    improved_count: int = 0
    regressed_count: int = 0
    unchanged_count: int = 0
    baseline_zero_result_count: int = 0
    candidate_zero_result_count: int = 0
    changed_queries: list[SearchReplayComparisonRowResponse] = Field(default_factory=list)


__all__ = [
    "SearchReplayComparisonResponse",
    "SearchReplayComparisonRowResponse",
    "SearchReplayQueryResponse",
    "SearchReplayRunDetailResponse",
    "SearchReplayRunRequest",
    "SearchReplayRunSummaryResponse",
]
