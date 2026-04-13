from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentTaskCreateRequest(BaseModel):
    task_type: str = Field(min_length=1)
    priority: int = Field(default=100, ge=0, le=1000)
    side_effect_level: str | None = Field(
        default=None,
        pattern="^(read_only|draft_change|promotable)$",
    )
    requires_approval: bool | None = None
    parent_task_id: UUID | None = None
    dependency_task_ids: list[UUID] = Field(default_factory=list)
    input: dict = Field(default_factory=dict)
    workflow_version: str = Field(default="v1", min_length=1)
    tool_version: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    model_settings: dict = Field(default_factory=dict)


class AgentTaskApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=1)
    approval_note: str | None = None


class AgentTaskRejectionRequest(BaseModel):
    rejected_by: str = Field(min_length=1)
    rejection_note: str | None = None


class AgentTaskOutcomeCreateRequest(BaseModel):
    outcome_label: str = Field(pattern="^(useful|not_useful|correct|incorrect)$")
    created_by: str = Field(min_length=1)
    note: str | None = None


class AgentTaskActionDefinitionResponse(BaseModel):
    task_type: str
    definition_kind: str = "action"
    description: str
    side_effect_level: str
    requires_approval: bool
    input_schema: dict = Field(default_factory=dict)
    input_example: dict = Field(default_factory=dict)


class AgentTaskSummaryResponse(BaseModel):
    task_id: UUID
    task_type: str
    status: str
    priority: int
    side_effect_level: str
    requires_approval: bool
    parent_task_id: UUID | None = None
    workflow_version: str
    tool_version: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AgentTaskVerificationResponse(BaseModel):
    verification_id: UUID
    target_task_id: UUID
    verification_task_id: UUID | None = None
    verifier_type: str
    outcome: str
    metrics: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None


class AgentTaskArtifactResponse(BaseModel):
    artifact_id: UUID
    task_id: UUID
    attempt_id: UUID | None = None
    artifact_kind: str
    storage_path: str | None = None
    payload: dict = Field(default_factory=dict)
    created_at: datetime


class AgentTaskOutcomeResponse(BaseModel):
    outcome_id: UUID
    task_id: UUID
    outcome_label: str
    created_by: str
    note: str | None = None
    created_at: datetime


class AgentTaskTrendPointResponse(BaseModel):
    bucket_start: datetime
    task_type: str | None = None
    workflow_version: str | None = None
    created_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    rejected_count: int = 0
    awaiting_approval_count: int = 0
    median_queue_latency_ms: float | None = None
    p95_queue_latency_ms: float | None = None
    median_execution_latency_ms: float | None = None
    p95_execution_latency_ms: float | None = None


class AgentTaskTrendResponse(BaseModel):
    bucket: str
    task_type: str | None = None
    workflow_version: str | None = None
    series: list[AgentTaskTrendPointResponse] = Field(default_factory=list)


class AgentTaskVerificationTrendPointResponse(BaseModel):
    bucket_start: datetime
    task_type: str | None = None
    workflow_version: str | None = None
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0


class AgentTaskVerificationTrendResponse(BaseModel):
    bucket: str
    task_type: str | None = None
    workflow_version: str | None = None
    series: list[AgentTaskVerificationTrendPointResponse] = Field(default_factory=list)


class AgentTaskApprovalTrendPointResponse(BaseModel):
    bucket_start: datetime
    task_type: str | None = None
    workflow_version: str | None = None
    approval_count: int = 0
    rejection_count: int = 0


class AgentTaskApprovalTrendResponse(BaseModel):
    bucket: str
    task_type: str | None = None
    workflow_version: str | None = None
    series: list[AgentTaskApprovalTrendPointResponse] = Field(default_factory=list)


class AgentTaskAnalyticsSummaryResponse(BaseModel):
    task_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    rejected_count: int = 0
    awaiting_approval_count: int = 0
    processing_count: int = 0
    approval_required_count: int = 0
    approved_task_count: int = 0
    rejected_task_count: int = 0
    labeled_task_count: int = 0
    outcome_label_counts: dict[str, int] = Field(default_factory=dict)
    verification_outcome_counts: dict[str, int] = Field(default_factory=dict)
    avg_terminal_duration_seconds: float | None = None


class AgentTaskWorkflowVersionSummaryResponse(BaseModel):
    workflow_version: str
    task_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    rejected_count: int = 0
    approved_task_count: int = 0
    rejected_task_count: int = 0
    labeled_task_count: int = 0
    outcome_label_counts: dict[str, int] = Field(default_factory=dict)
    verification_outcome_counts: dict[str, int] = Field(default_factory=dict)
    avg_terminal_duration_seconds: float | None = None


class AgentTaskRecommendationSummaryResponse(BaseModel):
    task_type: str | None = None
    workflow_version: str | None = None
    recommendation_task_count: int = 0
    draft_count: int = 0
    verified_draft_count: int = 0
    passed_verification_count: int = 0
    approved_apply_count: int = 0
    rejected_apply_count: int = 0
    applied_count: int = 0
    useful_label_count: int = 0
    correct_label_count: int = 0
    downstream_improved_count: int = 0
    downstream_regressed_count: int = 0
    triage_to_draft_rate: float | None = None
    verification_pass_rate: float | None = None
    apply_rate: float | None = None
    downstream_improvement_rate: float | None = None


class AgentTaskRecommendationTrendPointResponse(BaseModel):
    bucket_start: datetime
    task_type: str | None = None
    workflow_version: str | None = None
    recommendation_task_count: int = 0
    draft_count: int = 0
    applied_count: int = 0
    downstream_improved_count: int = 0
    downstream_regressed_count: int = 0


class AgentTaskRecommendationTrendResponse(BaseModel):
    bucket: str
    task_type: str | None = None
    workflow_version: str | None = None
    series: list[AgentTaskRecommendationTrendPointResponse] = Field(default_factory=list)


class AgentTaskCostSummaryResponse(BaseModel):
    task_type: str | None = None
    workflow_version: str | None = None
    attempt_count: int = 0
    instrumented_attempt_count: int = 0
    estimated_usd_total: float = 0.0
    model_call_count: int = 0
    embedding_count: int = 0
    replay_query_count: int = 0
    evaluation_query_count: int = 0


class AgentTaskCostTrendPointResponse(BaseModel):
    bucket_start: datetime
    task_type: str | None = None
    workflow_version: str | None = None
    attempt_count: int = 0
    estimated_usd_total: float = 0.0
    replay_query_count: int = 0
    evaluation_query_count: int = 0
    embedding_count: int = 0


class AgentTaskCostTrendResponse(BaseModel):
    bucket: str
    task_type: str | None = None
    workflow_version: str | None = None
    series: list[AgentTaskCostTrendPointResponse] = Field(default_factory=list)


class AgentTaskPerformanceSummaryResponse(BaseModel):
    task_type: str | None = None
    workflow_version: str | None = None
    attempt_count: int = 0
    instrumented_attempt_count: int = 0
    median_queue_latency_ms: float | None = None
    p95_queue_latency_ms: float | None = None
    median_execution_latency_ms: float | None = None
    p95_execution_latency_ms: float | None = None
    median_end_to_end_latency_ms: float | None = None
    p95_end_to_end_latency_ms: float | None = None


class AgentTaskPerformanceTrendPointResponse(BaseModel):
    bucket_start: datetime
    task_type: str | None = None
    workflow_version: str | None = None
    attempt_count: int = 0
    median_queue_latency_ms: float | None = None
    p95_queue_latency_ms: float | None = None
    median_execution_latency_ms: float | None = None
    p95_execution_latency_ms: float | None = None


class AgentTaskPerformanceTrendResponse(BaseModel):
    bucket: str
    task_type: str | None = None
    workflow_version: str | None = None
    series: list[AgentTaskPerformanceTrendPointResponse] = Field(default_factory=list)


class AgentTaskValueDensityRowResponse(BaseModel):
    task_type: str
    workflow_version: str
    recommendation_task_count: int = 0
    downstream_improved_count: int = 0
    estimated_usd_total: float = 0.0
    median_end_to_end_latency_ms: float | None = None
    useful_recommendation_rate: float | None = None
    downstream_improvement_rate: float | None = None
    improvements_per_dollar: float | None = None
    improvements_per_hour: float | None = None


class AgentTaskDecisionSignalResponse(BaseModel):
    task_type: str
    workflow_version: str
    status: str
    reason: str
    threshold_crossed: str
    recommended_action: str


class AgentTaskDetailResponse(AgentTaskSummaryResponse):
    dependency_task_ids: list[UUID] = Field(default_factory=list)
    input: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    model_settings: dict = Field(default_factory=dict)
    error_message: str | None = None
    failure_artifact_path: str | None = None
    attempts: int = 0
    locked_at: datetime | None = None
    locked_by: str | None = None
    last_heartbeat_at: datetime | None = None
    next_attempt_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    approval_note: str | None = None
    rejected_at: datetime | None = None
    rejected_by: str | None = None
    rejection_note: str | None = None
    artifact_count: int = 0
    attempt_count: int = 0
    verification_count: int = 0
    outcome_count: int = 0
    artifacts: list[AgentTaskArtifactResponse] = Field(default_factory=list)
    verifications: list[AgentTaskVerificationResponse] = Field(default_factory=list)
    outcomes: list[AgentTaskOutcomeResponse] = Field(default_factory=list)


class AgentTaskTraceExportResponse(BaseModel):
    export_count: int = 0
    workflow_version: str | None = None
    task_type: str | None = None
    traces: list[AgentTaskDetailResponse] = Field(default_factory=list)


class LatestEvaluationTaskInput(BaseModel):
    document_id: UUID


class ReplaySearchRequestTaskInput(BaseModel):
    search_request_id: UUID


class QualityEvalCandidatesTaskInput(BaseModel):
    limit: int = Field(default=12, ge=1, le=200)
    include_resolved: bool = False


class VerifySearchHarnessEvaluationTaskInput(BaseModel):
    target_task_id: UUID
    max_total_regressed_count: int = Field(default=0, ge=0)
    max_mrr_drop: float = Field(default=0.0, ge=0.0)
    max_zero_result_count_increase: int = Field(default=0, ge=0)
    max_foreign_top_result_count_increase: int = Field(default=0, ge=0)
    min_total_shared_query_count: int = Field(default=1, ge=0)


class TriageReplayRegressionTaskInput(BaseModel):
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
    replay_limit: int = Field(default=12, ge=1, le=200)
    quality_candidate_limit: int = Field(default=12, ge=1, le=200)
    include_resolved_candidates: bool = False
    max_total_regressed_count: int = Field(default=0, ge=0)
    max_mrr_drop: float = Field(default=0.0, ge=0.0)
    max_zero_result_count_increase: int = Field(default=0, ge=0)
    max_foreign_top_result_count_increase: int = Field(default=0, ge=0)
    min_total_shared_query_count: int = Field(default=1, ge=0)


class EnqueueDocumentReprocessTaskInput(BaseModel):
    document_id: UUID
    source_task_id: UUID | None = None
    reason: str | None = None


class DraftHarnessConfigUpdateTaskInput(BaseModel):
    draft_harness_name: str = Field(min_length=1)
    base_harness_name: str = Field(default="default_v1", min_length=1)
    source_task_id: UUID | None = None
    rationale: str | None = None
    retrieval_profile_overrides: dict[str, int] = Field(default_factory=dict)
    reranker_overrides: dict[str, float] = Field(default_factory=dict)


class VerifyDraftHarnessConfigTaskInput(BaseModel):
    target_task_id: UUID
    baseline_harness_name: str | None = Field(default=None, min_length=1)
    source_types: list[str] = Field(
        default_factory=lambda: [
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ]
    )
    limit: int = Field(default=25, ge=1, le=200)
    max_total_regressed_count: int = Field(default=0, ge=0)
    max_mrr_drop: float = Field(default=0.0, ge=0.0)
    max_zero_result_count_increase: int = Field(default=0, ge=0)
    max_foreign_top_result_count_increase: int = Field(default=0, ge=0)
    min_total_shared_query_count: int = Field(default=1, ge=0)


class ApplyHarnessConfigUpdateTaskInput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str | None = None
