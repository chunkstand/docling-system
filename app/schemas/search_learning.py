from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.search_harness import (
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
)


class RetrievalLearningCandidateEvaluationRequest(BaseModel):
    retrieval_training_run_id: UUID | None = None
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
    max_total_regressed_count: int = Field(default=0, ge=0)
    max_mrr_drop: float = Field(default=0.0, ge=0.0)
    max_zero_result_count_increase: int = Field(default=0, ge=0)
    max_foreign_top_result_count_increase: int = Field(default=0, ge=0)
    min_total_shared_query_count: int = Field(default=1, ge=0)
    requested_by: str | None = Field(default=None, min_length=1)
    review_note: str | None = None


class RetrievalLearningCandidateEvaluationSummaryResponse(BaseModel):
    schema_name: str = "retrieval_learning_candidate_evaluation"
    schema_version: str = "1.0"
    candidate_evaluation_id: UUID
    retrieval_training_run_id: UUID
    judgment_set_id: UUID
    search_harness_evaluation_id: UUID
    search_harness_release_id: UUID | None = None
    semantic_governance_event_id: UUID | None = None
    training_dataset_sha256: str
    training_example_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    missing_count: int = 0
    hard_negative_count: int = 0
    baseline_harness_name: str
    candidate_harness_name: str
    source_types: list[str] = Field(default_factory=list)
    limit: int
    status: str
    gate_outcome: str | None = None
    thresholds: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    learning_package_sha256: str
    created_by: str | None = None
    review_note: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class RetrievalLearningCandidateEvaluationResponse(
    RetrievalLearningCandidateEvaluationSummaryResponse
):
    details: dict = Field(default_factory=dict)
    evaluation: SearchHarnessEvaluationResponse
    release: SearchHarnessReleaseResponse | None = None


class RetrievalRerankerArtifactRequest(BaseModel):
    retrieval_training_run_id: UUID | None = None
    artifact_name: str | None = Field(default=None, min_length=1)
    candidate_harness_name: str
    baseline_harness_name: str = "default_v1"
    base_harness_name: str = "default_v1"
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
    requested_by: str | None = Field(default=None, min_length=1)
    review_note: str | None = None


class RetrievalRerankerArtifactSummaryResponse(BaseModel):
    schema_name: str = "retrieval_reranker_artifact"
    schema_version: str = "1.0"
    artifact_id: UUID
    retrieval_training_run_id: UUID
    judgment_set_id: UUID
    retrieval_learning_candidate_evaluation_id: UUID
    search_harness_evaluation_id: UUID
    search_harness_release_id: UUID | None = None
    semantic_governance_event_id: UUID | None = None
    artifact_kind: str
    artifact_name: str
    artifact_version: str
    status: str
    gate_outcome: str | None = None
    baseline_harness_name: str
    candidate_harness_name: str
    source_types: list[str] = Field(default_factory=list)
    limit: int
    training_dataset_sha256: str
    training_example_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    missing_count: int = 0
    hard_negative_count: int = 0
    thresholds: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    artifact_sha256: str
    change_impact_sha256: str
    created_by: str | None = None
    review_note: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class RetrievalRerankerArtifactResponse(RetrievalRerankerArtifactSummaryResponse):
    feature_weights: dict = Field(default_factory=dict)
    harness_overrides: dict = Field(default_factory=dict)
    artifact: dict = Field(default_factory=dict)
    change_impact_report: dict = Field(default_factory=dict)
    evaluation: SearchHarnessEvaluationResponse
    release: SearchHarnessReleaseResponse | None = None
    candidate_evaluation: RetrievalLearningCandidateEvaluationResponse


class SearchHarnessReleaseAuditBundleRequest(BaseModel):
    created_by: str | None = Field(default=None, min_length=1)


class RetrievalTrainingRunAuditBundleRequest(BaseModel):
    created_by: str | None = Field(default=None, min_length=1)


class AuditBundleValidationReceiptRequest(BaseModel):
    created_by: str | None = Field(default=None, min_length=1)


class AuditBundleExportSummaryResponse(BaseModel):
    schema_name: str = "audit_bundle_export"
    schema_version: str = "1.0"
    bundle_id: UUID
    bundle_kind: str
    source_table: str
    source_id: UUID
    payload_sha256: str
    bundle_sha256: str
    signature: str
    signature_algorithm: str
    signing_key_id: str
    created_by: str | None = None
    export_status: str
    created_at: datetime


class AuditBundleExportResponse(AuditBundleExportSummaryResponse):
    bundle: dict = Field(default_factory=dict)
    integrity: dict = Field(default_factory=dict)


class AuditBundleValidationReceiptSummaryResponse(BaseModel):
    schema_name: str = "audit_bundle_validation_receipt"
    schema_version: str = "1.0"
    receipt_id: UUID
    audit_bundle_export_id: UUID
    bundle_kind: str
    source_table: str
    source_id: UUID
    validation_profile: str
    validation_status: str
    payload_schema_valid: bool
    prov_graph_valid: bool
    bundle_integrity_valid: bool
    source_integrity_valid: bool
    semantic_governance_valid: bool
    receipt_sha256: str
    prov_jsonld_sha256: str
    signature: str
    signature_algorithm: str
    signing_key_id: str
    created_by: str | None = None
    created_at: datetime


class AuditBundleValidationReceiptResponse(AuditBundleValidationReceiptSummaryResponse):
    receipt: dict = Field(default_factory=dict)
    prov_jsonld: dict = Field(default_factory=dict)
    validation_errors: list[dict] = Field(default_factory=list)
    integrity: dict = Field(default_factory=dict)


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
