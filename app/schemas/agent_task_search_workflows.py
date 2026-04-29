from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent_task_core import AgentTaskVerificationResponse, TriageRecommendationPayload
from app.schemas.documents import DocumentUploadResponse
from app.schemas.eval_workbench import (
    EvalFailureCaseInspectionResponse,
    EvalFailureCaseRefreshResponse,
    EvalFailureCaseResponse,
    EvalFailureCaseTriageResponse,
)
from app.schemas.quality import QualityEvaluationCandidateResponse
from app.schemas.search import (
    SearchHarnessDescriptorResponse,
    SearchHarnessEvaluationResponse,
    SearchHarnessOptimizationResponse,
    SearchHarnessReleaseResponse,
    SearchReplayResponse,
    SearchReplayRunDetailResponse,
    SearchRequestExplanationResponse,
)


class ReplaySearchRequestTaskInput(BaseModel):
    search_request_id: UUID


class ReplaySearchRequestTaskOutput(BaseModel):
    search_request_id: UUID
    replay: SearchReplayResponse


class QualityEvalCandidatesTaskInput(BaseModel):
    limit: int = Field(default=12, ge=1, le=200)
    include_resolved: bool = False


class QualityEvalCandidatesTaskOutput(BaseModel):
    limit: int
    include_resolved: bool
    candidate_count: int = 0
    candidates: list[QualityEvaluationCandidateResponse] = Field(default_factory=list)


class RefreshEvalFailureCasesTaskInput(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    include_resolved: bool = False


class RefreshEvalFailureCasesTaskOutput(BaseModel):
    refresh: EvalFailureCaseRefreshResponse


class InspectEvalFailureCaseTaskInput(BaseModel):
    case_id: UUID


class InspectEvalFailureCaseTaskOutput(BaseModel):
    inspection: EvalFailureCaseInspectionResponse


class TriageEvalFailureCaseTaskInput(BaseModel):
    case_id: UUID


class TriageEvalFailureCaseTaskOutput(BaseModel):
    triage: EvalFailureCaseTriageResponse


class OptimizeSearchHarnessFromCaseTaskInput(BaseModel):
    case_id: UUID
    base_harness_name: str = Field(default="wide_v2", min_length=1)
    baseline_harness_name: str = Field(default="wide_v2", min_length=1)
    candidate_harness_name: str | None = Field(default=None, min_length=1)
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


class OptimizeSearchHarnessFromCaseTaskOutput(BaseModel):
    case: EvalFailureCaseResponse
    optimization: SearchHarnessOptimizationResponse
    recommendation: dict = Field(default_factory=dict)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class DraftHarnessConfigFromOptimizationTaskInput(BaseModel):
    source_task_id: UUID
    draft_harness_name: str = Field(min_length=1)
    rationale: str | None = None


class DraftHarnessConfigFromOptimizationTaskOutput(BaseModel):
    draft: DraftHarnessConfigPayload
    source_case: EvalFailureCaseResponse | None = None
    optimization_summary: dict = Field(default_factory=dict)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


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


class EnqueueDocumentReprocessTaskOutput(BaseModel):
    document_id: UUID
    source_task_id: UUID | None = None
    reason: str | None = None
    reprocess: DocumentUploadResponse


class RunSearchReplaySuiteTaskOutput(BaseModel):
    source_type: str
    harness_name: str | None = None
    replay_run: SearchReplayRunDetailResponse


class DraftHarnessConfigUpdateTaskInput(BaseModel):
    draft_harness_name: str = Field(min_length=1)
    base_harness_name: str = Field(default="default_v1", min_length=1)
    source_task_id: UUID | None = None
    rationale: str | None = None
    retrieval_profile_overrides: dict[str, int] = Field(default_factory=dict)
    reranker_overrides: dict[str, float] = Field(default_factory=dict)


class DraftHarnessOverrideSpec(BaseModel):
    base_harness_name: str
    retrieval_profile_overrides: dict[str, int] = Field(default_factory=dict)
    reranker_overrides: dict[str, float] = Field(default_factory=dict)
    override_type: str
    override_source: str
    draft_task_id: UUID
    source_task_id: UUID | None = None
    rationale: str | None = None


class DraftHarnessConfigPayload(BaseModel):
    draft_harness_name: str
    base_harness_name: str
    source_task_id: UUID | None = None
    source_task_type: str | None = None
    rationale: str | None = None
    override_spec: DraftHarnessOverrideSpec
    effective_harness_config: dict = Field(default_factory=dict)


class DraftHarnessConfigUpdateTaskOutput(BaseModel):
    draft: DraftHarnessConfigPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class EvaluateSearchHarnessTaskOutput(BaseModel):
    candidate_harness_name: str
    baseline_harness_name: str
    evaluation: SearchHarnessEvaluationResponse


class VerifySearchHarnessEvaluationTaskOutput(BaseModel):
    evaluation: SearchHarnessEvaluationResponse
    verification: AgentTaskVerificationResponse
    release: SearchHarnessReleaseResponse | None = None


class RepairCaseExamplePayload(BaseModel):
    source_type: str
    query_text: str
    mode: str
    filters: dict = Field(default_factory=dict)
    baseline_passed: bool | None = None
    candidate_passed: bool | None = None
    baseline_result_count: int | None = None
    candidate_result_count: int | None = None
    baseline_search_request_id: UUID | None = None
    candidate_search_request_id: UUID | None = None
    baseline_explanation: SearchRequestExplanationResponse | None = None
    candidate_explanation: SearchRequestExplanationResponse | None = None


class RepairCasePayload(BaseModel):
    schema_name: str = "search_harness_repair_case"
    schema_version: str = "1.0"
    candidate_harness_name: str
    baseline_harness_name: str
    failure_classification: str
    problem_statement: str
    observed_metric_delta: dict = Field(default_factory=dict)
    affected_result_types: list[str] = Field(default_factory=list)
    likely_root_cause: str | None = None
    allowed_repair_surface: list[str] = Field(default_factory=list)
    blocked_repair_surfaces: list[str] = Field(default_factory=list)
    recommended_next_action: str
    diagnostic_examples: list[RepairCaseExamplePayload] = Field(default_factory=list)
    evidence_refs: list[dict] = Field(default_factory=list)


class TriageReplayRegressionTaskOutput(BaseModel):
    shadow_mode: bool = True
    triage_kind: str
    candidate_harness_name: str
    baseline_harness_name: str
    quality_candidate_count: int = 0
    top_quality_candidates: list[dict] = Field(default_factory=list)
    evaluation: SearchHarnessEvaluationResponse
    verification: AgentTaskVerificationResponse
    recommendation: TriageRecommendationPayload
    repair_case: RepairCasePayload | None = None
    repair_case_artifact_id: UUID | None = None
    repair_case_artifact_kind: str | None = None
    repair_case_artifact_path: str | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class HarnessComprehensionGatePayload(BaseModel):
    comprehension_passed: bool
    claim_evidence_alignment: str
    change_justification: str
    predicted_blast_radius: dict = Field(default_factory=dict)
    rollback_condition: str
    follow_up_plan: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    harness_descriptor: SearchHarnessDescriptorResponse | None = None
    repair_case: RepairCasePayload | None = None


class VerifyDraftHarnessConfigTaskOutput(BaseModel):
    draft: DraftHarnessConfigPayload
    evaluation: dict = Field(default_factory=dict)
    comprehension_gate: HarnessComprehensionGatePayload | None = None
    follow_up_plan: dict = Field(default_factory=dict)
    verification: AgentTaskVerificationResponse
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class ApplyHarnessConfigUpdateTaskOutput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    draft_harness_name: str
    reason: str | None = None
    config_path: str
    applied_override: dict = Field(default_factory=dict)
    effective_harness_config: dict = Field(default_factory=dict)
    follow_up_plan: dict = Field(default_factory=dict)
    follow_up_evaluation: dict = Field(default_factory=dict)
    follow_up_summary: dict = Field(default_factory=dict)
    follow_up_artifact_id: UUID | None = None
    follow_up_artifact_kind: str | None = None
    follow_up_artifact_path: str | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


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


__all__ = [
    "ReplaySearchRequestTaskInput",
    "ReplaySearchRequestTaskOutput",
    "QualityEvalCandidatesTaskInput",
    "QualityEvalCandidatesTaskOutput",
    "RefreshEvalFailureCasesTaskInput",
    "RefreshEvalFailureCasesTaskOutput",
    "InspectEvalFailureCaseTaskInput",
    "InspectEvalFailureCaseTaskOutput",
    "TriageEvalFailureCaseTaskInput",
    "TriageEvalFailureCaseTaskOutput",
    "OptimizeSearchHarnessFromCaseTaskInput",
    "OptimizeSearchHarnessFromCaseTaskOutput",
    "DraftHarnessConfigFromOptimizationTaskInput",
    "DraftHarnessConfigFromOptimizationTaskOutput",
    "VerifySearchHarnessEvaluationTaskInput",
    "TriageReplayRegressionTaskInput",
    "EnqueueDocumentReprocessTaskInput",
    "EnqueueDocumentReprocessTaskOutput",
    "RunSearchReplaySuiteTaskOutput",
    "DraftHarnessConfigUpdateTaskInput",
    "DraftHarnessOverrideSpec",
    "DraftHarnessConfigPayload",
    "DraftHarnessConfigUpdateTaskOutput",
    "EvaluateSearchHarnessTaskOutput",
    "VerifySearchHarnessEvaluationTaskOutput",
    "RepairCaseExamplePayload",
    "RepairCasePayload",
    "TriageReplayRegressionTaskOutput",
    "HarnessComprehensionGatePayload",
    "VerifyDraftHarnessConfigTaskOutput",
    "ApplyHarnessConfigUpdateTaskOutput",
    "VerifyDraftHarnessConfigTaskInput",
    "ApplyHarnessConfigUpdateTaskInput",
]
