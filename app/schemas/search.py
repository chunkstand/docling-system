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
    harness_name: str | None = None


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


class SearchReplayRunRequest(BaseModel):
    source_type: str = Field(
        pattern="^(evaluation_queries|live_search_gaps|feedback|cross_document_prose_regressions)$"
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


class SearchHarnessResponse(BaseModel):
    harness_name: str
    reranker_name: str
    reranker_version: str
    retrieval_profile_name: str
    harness_config: dict = Field(default_factory=dict)
    is_default: bool = False


class SearchHarnessDescriptorResponse(BaseModel):
    schema_name: str = "search_harness_descriptor"
    schema_version: str = "1.0"
    harness_name: str
    base_harness_name: str | None = None
    is_default: bool = False
    config_fingerprint: str
    reranker_name: str
    reranker_version: str
    retrieval_profile_name: str
    retrieval_stages: list[str] = Field(default_factory=list)
    tunable_knobs: dict = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    intended_query_families: list[str] = Field(default_factory=list)
    known_tradeoffs: list[str] = Field(default_factory=list)
    harness_config: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class SearchHarnessEvaluationRequest(BaseModel):
    candidate_harness_name: str
    baseline_harness_name: str = "default_v1"
    source_types: list[str] = Field(
        default_factory=lambda: [
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ]
    )
    limit: int = Field(default=25, ge=1, le=200)


class SearchHarnessEvaluationSourceResponse(BaseModel):
    source_type: str
    baseline_replay_run_id: UUID
    candidate_replay_run_id: UUID
    baseline_status: str | None = None
    candidate_status: str | None = None
    baseline_query_count: int = 0
    candidate_query_count: int = 0
    baseline_passed_count: int = 0
    candidate_passed_count: int = 0
    baseline_zero_result_count: int = 0
    candidate_zero_result_count: int = 0
    baseline_table_hit_count: int = 0
    candidate_table_hit_count: int = 0
    baseline_top_result_changes: int = 0
    candidate_top_result_changes: int = 0
    baseline_mrr: float = 0.0
    candidate_mrr: float = 0.0
    baseline_foreign_top_result_count: int = 0
    candidate_foreign_top_result_count: int = 0
    acceptance_checks: dict = Field(default_factory=dict)
    shared_query_count: int = 0
    improved_count: int = 0
    regressed_count: int = 0
    unchanged_count: int = 0


class SearchHarnessEvaluationResponse(BaseModel):
    evaluation_id: UUID | None = None
    status: str = "completed"
    baseline_harness_name: str
    candidate_harness_name: str
    limit: int
    source_types: list[str] = Field(default_factory=list)
    harness_overrides: dict = Field(default_factory=dict)
    total_shared_query_count: int = 0
    total_improved_count: int = 0
    total_regressed_count: int = 0
    total_unchanged_count: int = 0
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    sources: list[SearchHarnessEvaluationSourceResponse] = Field(default_factory=list)


class SearchHarnessEvaluationSummaryResponse(BaseModel):
    evaluation_id: UUID
    status: str
    baseline_harness_name: str
    candidate_harness_name: str
    limit: int
    source_types: list[str] = Field(default_factory=list)
    total_shared_query_count: int = 0
    total_improved_count: int = 0
    total_regressed_count: int = 0
    total_unchanged_count: int = 0
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class SearchHarnessOptimizationRequest(BaseModel):
    base_harness_name: str = "default_v1"
    baseline_harness_name: str = "default_v1"
    candidate_harness_name: str
    source_types: list[str] = Field(
        default_factory=lambda: [
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ]
    )
    limit: int = Field(default=25, ge=1, le=200)
    iterations: int = Field(default=2, ge=1, le=20)
    tune_fields: list[str] = Field(default_factory=list)
    max_total_regressed_count: int = Field(default=0, ge=0)
    max_mrr_drop: float = Field(default=0.0, ge=0.0)
    max_zero_result_count_increase: int = Field(default=0, ge=0)
    max_foreign_top_result_count_increase: int = Field(default=0, ge=0)
    min_total_shared_query_count: int = Field(default=1, ge=1)


class SearchHarnessOptimizationAttemptResponse(BaseModel):
    iteration: int = Field(ge=0)
    field_name: str
    direction: str = Field(pattern="^(increase|decrease|baseline)$")
    scope: str = Field(pattern="^(retrieval_profile_overrides|reranker_overrides|baseline)$")
    proposed_value: int | float | None = None
    accepted: bool = False
    score: dict = Field(default_factory=dict)
    evaluation: SearchHarnessEvaluationResponse
    gate: dict = Field(default_factory=dict)
    override_spec: dict = Field(default_factory=dict)


class SearchHarnessOptimizationResponse(BaseModel):
    base_harness_name: str
    baseline_harness_name: str
    candidate_harness_name: str
    source_types: list[str] = Field(default_factory=list)
    limit: int
    iterations_requested: int
    iterations_completed: int = 0
    tuned_fields: list[str] = Field(default_factory=list)
    stopped_reason: str
    artifact_path: str | None = None
    best_override_spec: dict = Field(default_factory=dict)
    best_score: dict = Field(default_factory=dict)
    best_evaluation: SearchHarnessEvaluationResponse
    best_gate: dict = Field(default_factory=dict)
    attempts: list[SearchHarnessOptimizationAttemptResponse] = Field(default_factory=list)
