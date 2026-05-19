from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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


class SearchHarnessReleaseGateRequest(BaseModel):
    evaluation_id: UUID
    max_total_regressed_count: int = Field(default=0, ge=0)
    max_mrr_drop: float = Field(default=0.0, ge=0.0)
    max_zero_result_count_increase: int = Field(default=0, ge=0)
    max_foreign_top_result_count_increase: int = Field(default=0, ge=0)
    min_total_shared_query_count: int = Field(default=1, ge=0)
    requested_by: str | None = Field(default=None, min_length=1)
    review_note: str | None = None


class SearchHarnessReleaseSummaryResponse(BaseModel):
    schema_name: str = "search_harness_release_gate"
    schema_version: str = "1.0"
    release_id: UUID
    evaluation_id: UUID
    outcome: str
    baseline_harness_name: str
    candidate_harness_name: str
    limit: int
    source_types: list[str] = Field(default_factory=list)
    thresholds: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    release_package_sha256: str
    requested_by: str | None = None
    review_note: str | None = None
    created_at: datetime


class SearchHarnessReleaseResponse(SearchHarnessReleaseSummaryResponse):
    details: dict = Field(default_factory=dict)
    evaluation_snapshot: dict = Field(default_factory=dict)


class SearchHarnessReleaseReadinessAssessmentRequest(BaseModel):
    created_by: str | None = Field(default=None, min_length=1)
    review_note: str | None = None


class SearchHarnessReleaseReadinessAssessmentSummaryResponse(BaseModel):
    schema_name: str = "search_harness_release_readiness_assessment_summary"
    schema_version: str = "1.0"
    assessment_id: UUID
    release_id: UUID
    readiness_profile: str
    readiness_status: str
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    latest_release_audit_bundle_id: UUID | None = None
    latest_release_validation_receipt_id: UUID | None = None
    semantic_governance_event_id: UUID | None = None
    readiness_payload_sha256: str
    assessment_payload_sha256: str
    created_by: str | None = None
    review_note: str | None = None
    created_at: datetime


class SearchHarnessReleaseReadinessAssessmentResponse(
    SearchHarnessReleaseReadinessAssessmentSummaryResponse
):
    schema_name: str = "search_harness_release_readiness_assessment"
    schema_version: str = "1.1"
    blocker_details: list[dict] = Field(default_factory=list)
    checks: dict = Field(default_factory=dict)
    diagnostics: dict = Field(default_factory=dict)
    lineage_remediation: dict = Field(default_factory=dict)
    readiness: dict = Field(default_factory=dict)
    assessment: dict = Field(default_factory=dict)
    integrity: dict = Field(default_factory=dict)


class SearchHarnessReleaseReadinessResponse(BaseModel):
    schema_name: str = "search_harness_release_readiness"
    schema_version: str = "1.3"
    release_id: UUID
    readiness_profile: str
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    blocker_details: list[dict] = Field(default_factory=list)
    retrieval: dict = Field(default_factory=dict)
    provenance: dict = Field(default_factory=dict)
    semantic_governance: dict = Field(default_factory=dict)
    validation_receipts: dict = Field(default_factory=dict)
    diagnostics: dict = Field(default_factory=dict)
    lineage_remediation: dict = Field(default_factory=dict)
    checks: dict = Field(default_factory=dict)
    latest_readiness_assessment: SearchHarnessReleaseReadinessAssessmentSummaryResponse | None = (
        None
    )
    generated_at: datetime


__all__ = [
    "SearchHarnessDescriptorResponse",
    "SearchHarnessEvaluationRequest",
    "SearchHarnessEvaluationResponse",
    "SearchHarnessEvaluationSourceResponse",
    "SearchHarnessEvaluationSummaryResponse",
    "SearchHarnessReleaseGateRequest",
    "SearchHarnessReleaseReadinessAssessmentRequest",
    "SearchHarnessReleaseReadinessAssessmentResponse",
    "SearchHarnessReleaseReadinessAssessmentSummaryResponse",
    "SearchHarnessReleaseReadinessResponse",
    "SearchHarnessReleaseResponse",
    "SearchHarnessReleaseSummaryResponse",
    "SearchHarnessResponse",
]
