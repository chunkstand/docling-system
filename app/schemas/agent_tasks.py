from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.documents import DocumentUploadResponse
from app.schemas.eval_workbench import (
    EvalFailureCaseInspectionResponse,
    EvalFailureCaseRefreshResponse,
    EvalFailureCaseResponse,
    EvalFailureCaseTriageResponse,
)
from app.schemas.evaluations import EvaluationDetailResponse
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
from app.schemas.semantics import DocumentSemanticPassResponse


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
    capability: str
    definition_kind: str = "action"
    description: str
    side_effect_level: str
    requires_approval: bool
    context_builder_name: str
    input_schema: dict = Field(default_factory=dict)
    output_schema_name: str | None = None
    output_schema_version: str | None = None
    output_schema: dict | None = None
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


class ContextFreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    SCHEMA_MISMATCH = "schema_mismatch"


class AgentTaskDependencyResponse(BaseModel):
    task_id: UUID
    dependency_kind: str


class ContextRef(BaseModel):
    ref_key: str
    ref_kind: str
    summary: str | None = None
    task_id: UUID | None = None
    artifact_id: UUID | None = None
    verification_id: UUID | None = None
    replay_run_id: UUID | None = None
    search_harness_evaluation_id: UUID | None = None
    artifact_kind: str | None = None
    schema_name: str | None = None
    schema_version: str | None = None
    observed_sha256: str | None = None
    source_updated_at: datetime | None = None
    checked_at: datetime | None = None
    freshness_status: ContextFreshnessStatus | None = None


class TaskContextSummary(BaseModel):
    headline: str | None = None
    goal: str | None = None
    decision: str | None = None
    next_action: str | None = None
    approval_state: str | None = None
    verification_state: str | None = None
    problem: str | None = None
    evidence: str | None = None
    proposed_change: str | None = None
    predicted_risk: str | None = None
    follow_up_status: str | None = None
    metrics: dict = Field(default_factory=dict)


class TaskContextEnvelope(BaseModel):
    schema_name: str = "agent_task_context"
    schema_version: str = "1.0"
    task_id: UUID
    task_type: str
    task_status: str
    workflow_version: str
    generated_at: datetime
    task_updated_at: datetime
    output_schema_name: str | None = None
    output_schema_version: str | None = None
    freshness_status: ContextFreshnessStatus | None = None
    summary: TaskContextSummary = Field(default_factory=TaskContextSummary)
    refs: list[ContextRef] = Field(default_factory=list)
    output: dict = Field(default_factory=dict)


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
    dependency_edges: list[AgentTaskDependencyResponse] = Field(default_factory=list)
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
    context_summary: TaskContextSummary | None = None
    context_refs: list[ContextRef] = Field(default_factory=list)
    context_artifact_id: UUID | None = None
    context_freshness_status: ContextFreshnessStatus | None = None
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


class LatestEvaluationTaskOutput(BaseModel):
    document_id: UUID
    evaluation: EvaluationDetailResponse


class SemanticSuccessMetricCheck(BaseModel):
    metric_key: str
    stakeholder: str
    passed: bool
    summary: str
    details: dict = Field(default_factory=dict)


class LatestSemanticPassTaskInput(BaseModel):
    document_id: UUID


class LatestSemanticPassTaskOutput(BaseModel):
    document_id: UUID
    semantic_pass: DocumentSemanticPassResponse
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class ActiveOntologySnapshotPayload(BaseModel):
    snapshot_id: UUID
    ontology_name: str
    ontology_version: str
    upper_ontology_version: str
    sha256: str
    source_kind: str
    source_task_id: UUID | None = None
    source_task_type: str | None = None
    concept_count: int = 0
    category_count: int = 0
    relation_count: int = 0
    relation_keys: list[str] = Field(default_factory=list)
    created_at: datetime
    activated_at: datetime | None = None


class InitializeWorkspaceOntologyTaskInput(BaseModel):
    pass


class InitializeWorkspaceOntologyTaskOutput(BaseModel):
    snapshot: ActiveOntologySnapshotPayload
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class GetActiveOntologySnapshotTaskInput(BaseModel):
    pass


class GetActiveOntologySnapshotTaskOutput(BaseModel):
    snapshot: ActiveOntologySnapshotPayload
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class SemanticRegistryUpdateHint(BaseModel):
    update_type: str
    concept_key: str
    alias_text: str | None = None
    category_key: str | None = None
    reason: str


class SemanticIssueEvidenceRef(BaseModel):
    evidence_id: UUID | None = None
    source_type: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    excerpt: str | None = None
    source_artifact_api_path: str | None = None
    matched_terms: list[str] = Field(default_factory=list)


class SemanticGapIssue(BaseModel):
    issue_id: str
    issue_type: str
    severity: str
    concept_key: str | None = None
    category_key: str | None = None
    assertion_id: UUID | None = None
    binding_id: UUID | None = None
    summary: str
    details: dict = Field(default_factory=dict)
    evidence_refs: list[SemanticIssueEvidenceRef] = Field(default_factory=list)
    registry_update_hints: list[SemanticRegistryUpdateHint] = Field(default_factory=list)


class SemanticRecommendedFollowup(BaseModel):
    followup_type: str
    priority: str
    summary: str
    target_task_type: str | None = None
    details: dict = Field(default_factory=dict)


class SemanticGapReport(BaseModel):
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    registry_version: str
    registry_sha256: str
    evaluation_status: str
    evaluation_fixture_name: str | None = None
    evaluation_version: int
    continuity_summary: dict = Field(default_factory=dict)
    issue_count: int = 0
    issues: list[SemanticGapIssue] = Field(default_factory=list)
    recommended_followups: list[SemanticRecommendedFollowup] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class TriageSemanticPassTaskInput(BaseModel):
    target_task_id: UUID
    low_evidence_threshold: int = Field(default=2, ge=1, le=100)


class TriageSemanticPassTaskOutput(BaseModel):
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    registry_version: str
    evaluation_fixture_name: str | None = None
    evaluation_status: str
    gap_report: SemanticGapReport
    verification: AgentTaskVerificationResponse
    recommendation: TriageRecommendationPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class DraftSemanticRegistryUpdateTaskInput(BaseModel):
    source_task_id: UUID
    proposed_registry_version: str | None = Field(default=None, min_length=1)
    rationale: str | None = None
    candidate_ids: list[str] = Field(default_factory=list, max_length=50)


class SemanticRegistryUpdateOperation(BaseModel):
    operation_id: str
    operation_type: str
    concept_key: str
    preferred_label: str | None = None
    alias_text: str | None = None
    category_key: str | None = None
    source_issue_ids: list[str] = Field(default_factory=list)
    rationale: str | None = None


class SemanticRegistryDraftPayload(BaseModel):
    base_registry_version: str
    proposed_registry_version: str
    source_task_id: UUID
    source_task_type: str | None = None
    rationale: str | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    operations: list[SemanticRegistryUpdateOperation] = Field(default_factory=list)
    effective_registry: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class DraftSemanticRegistryUpdateTaskOutput(BaseModel):
    draft: SemanticRegistryDraftPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class DraftOntologyExtensionTaskInput(BaseModel):
    source_task_id: UUID
    proposed_ontology_version: str | None = Field(default=None, min_length=1)
    rationale: str | None = None
    candidate_ids: list[str] = Field(default_factory=list, max_length=50)


class OntologyExtensionDraftPayload(BaseModel):
    base_snapshot_id: UUID
    base_ontology_version: str
    proposed_ontology_version: str
    upper_ontology_version: str
    source_task_id: UUID
    source_task_type: str | None = None
    rationale: str | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    operations: list[SemanticRegistryUpdateOperation] = Field(default_factory=list)
    effective_ontology: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class DraftOntologyExtensionTaskOutput(BaseModel):
    draft: OntologyExtensionDraftPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class VerifyDraftSemanticRegistryUpdateTaskInput(BaseModel):
    target_task_id: UUID
    document_ids: list[UUID] = Field(default_factory=list)
    max_regressed_document_count: int = Field(default=0, ge=0)
    max_failed_expectation_increase: int = Field(default=0, ge=0)
    min_improved_document_count: int = Field(default=1, ge=0)


class SemanticRegistryDocumentDelta(BaseModel):
    document_id: UUID
    run_id: UUID
    evaluation_fixture_name: str | None = None
    before_all_expectations_passed: bool
    after_all_expectations_passed: bool
    before_failed_expectations: int = 0
    after_failed_expectations: int = 0
    before_assertion_count: int = 0
    after_assertion_count: int = 0
    added_concept_keys: list[str] = Field(default_factory=list)
    removed_concept_keys: list[str] = Field(default_factory=list)
    introduced_expected_concepts: list[str] = Field(default_factory=list)
    regressed_expected_concepts: list[str] = Field(default_factory=list)


class VerifyDraftSemanticRegistryUpdateTaskOutput(BaseModel):
    draft: SemanticRegistryDraftPayload
    document_deltas: list[SemanticRegistryDocumentDelta] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    verification: AgentTaskVerificationResponse
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class VerifyDraftOntologyExtensionTaskInput(BaseModel):
    target_task_id: UUID
    document_ids: list[UUID] = Field(default_factory=list)
    max_regressed_document_count: int = Field(default=0, ge=0)
    max_failed_expectation_increase: int = Field(default=0, ge=0)
    min_improved_document_count: int = Field(default=1, ge=0)


class VerifyDraftOntologyExtensionTaskOutput(BaseModel):
    draft: OntologyExtensionDraftPayload
    document_deltas: list[SemanticRegistryDocumentDelta] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    verification: AgentTaskVerificationResponse
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class ApplySemanticRegistryUpdateTaskInput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str | None = None


class ApplySemanticRegistryUpdateTaskOutput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    applied_registry_version: str
    applied_registry_sha256: str
    reason: str | None = None
    config_path: str
    applied_operations: list[SemanticRegistryUpdateOperation] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class ApplyOntologyExtensionTaskInput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str | None = None


class ApplyOntologyExtensionTaskOutput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    applied_snapshot_id: UUID
    applied_ontology_version: str
    applied_ontology_sha256: str
    upper_ontology_version: str
    reason: str | None = None
    applied_operations: list[SemanticRegistryUpdateOperation] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticGenerationDocumentRef(BaseModel):
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    source_filename: str
    title: str | None = None
    registry_version: str
    registry_sha256: str
    evaluation_fixture_name: str | None = None
    evaluation_status: str
    assertion_count: int = 0
    evidence_count: int = 0
    all_expectations_passed: bool = False


class SemanticGenerationAssertionRef(BaseModel):
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    assertion_id: UUID
    concept_key: str
    preferred_label: str
    review_status: str
    support_level: str
    source_types: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    category_keys: list[str] = Field(default_factory=list)
    category_labels: list[str] = Field(default_factory=list)


class SemanticGenerationEvidenceRef(BaseModel):
    citation_label: str
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    assertion_id: UUID
    evidence_id: UUID
    concept_key: str
    preferred_label: str
    review_status: str
    source_filename: str
    source_type: str
    source_locator: str | None = None
    chunk_id: UUID | None = None
    table_id: UUID | None = None
    figure_id: UUID | None = None
    page_from: int | None = None
    page_to: int | None = None
    excerpt: str | None = None
    source_artifact_api_path: str | None = None
    source_artifact_sha256: str | None = None
    matched_terms: list[str] = Field(default_factory=list)


class SemanticGenerationFactRef(BaseModel):
    fact_id: UUID
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    relation_key: str
    relation_label: str
    subject_entity_key: str
    subject_label: str
    object_entity_key: str | None = None
    object_label: str | None = None
    object_value_text: str | None = None
    review_status: str
    assertion_id: UUID | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)


class SemanticGenerationGraphEdgeRef(BaseModel):
    edge_id: str
    graph_snapshot_id: UUID
    graph_version: str
    relation_key: str
    relation_label: str
    subject_entity_key: str
    subject_label: str
    object_entity_key: str
    object_label: str
    review_status: str
    support_level: str
    extractor_score: float
    supporting_document_ids: list[UUID] = Field(default_factory=list)
    support_ref_ids: list[str] = Field(default_factory=list)


class SemanticDossierConceptEntry(BaseModel):
    concept_key: str
    preferred_label: str
    category_keys: list[str] = Field(default_factory=list)
    category_labels: dict[str, str] = Field(default_factory=dict)
    document_ids: list[UUID] = Field(default_factory=list)
    document_count: int = 0
    evidence_count: int = 0
    source_types: list[str] = Field(default_factory=list)
    support_level: str
    review_policy_status: str
    disclosure_note: str | None = None
    facts: list[SemanticGenerationFactRef] = Field(default_factory=list)
    assertions: list[SemanticGenerationAssertionRef] = Field(default_factory=list)
    evidence_refs: list[SemanticGenerationEvidenceRef] = Field(default_factory=list)


class SemanticGenerationSectionPlan(BaseModel):
    section_id: str
    title: str
    summary: str
    focus_concept_keys: list[str] = Field(default_factory=list)
    focus_category_keys: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class SemanticGenerationClaimCandidate(BaseModel):
    claim_id: str
    section_id: str
    summary: str
    concept_keys: list[str] = Field(default_factory=list)
    graph_edge_ids: list[str] = Field(default_factory=list)
    fact_ids: list[UUID] = Field(default_factory=list)
    assertion_ids: list[UUID] = Field(default_factory=list)
    evidence_labels: list[str] = Field(default_factory=list)
    source_document_ids: list[UUID] = Field(default_factory=list)
    support_level: str
    review_policy_status: str
    disclosure_note: str | None = None


class SemanticShadowCandidateEvidenceRef(BaseModel):
    source_type: str
    source_locator: str
    page_from: int | None = None
    page_to: int | None = None
    excerpt: str | None = None
    source_artifact_api_path: str | None = None
    source_artifact_sha256: str | None = None
    score: float


class SemanticShadowCandidateConcept(BaseModel):
    concept_key: str
    preferred_label: str
    max_score: float
    source_count: int = 0
    source_types: list[str] = Field(default_factory=list)
    category_keys: list[str] = Field(default_factory=list)
    expected_by_evaluation: bool = False
    evidence_refs: list[SemanticShadowCandidateEvidenceRef] = Field(default_factory=list)
    note: str | None = None


class SemanticGenerationBriefPayload(BaseModel):
    document_kind: str = "knowledge_brief"
    title: str
    goal: str
    audience: str | None = None
    review_policy: str
    target_length: str
    document_refs: list[SemanticGenerationDocumentRef] = Field(default_factory=list)
    required_concept_keys: list[str] = Field(default_factory=list)
    selected_concept_keys: list[str] = Field(default_factory=list)
    selected_category_keys: list[str] = Field(default_factory=list)
    semantic_dossier: list[SemanticDossierConceptEntry] = Field(default_factory=list)
    graph_index: list[SemanticGenerationGraphEdgeRef] = Field(default_factory=list)
    graph_summary: dict = Field(default_factory=dict)
    sections: list[SemanticGenerationSectionPlan] = Field(default_factory=list)
    claim_candidates: list[SemanticGenerationClaimCandidate] = Field(default_factory=list)
    evidence_pack: list[SemanticGenerationEvidenceRef] = Field(default_factory=list)
    shadow_mode: bool = False
    shadow_candidate_extractor_name: str | None = None
    shadow_candidate_summary: dict = Field(default_factory=dict)
    shadow_candidates: list[SemanticShadowCandidateConcept] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class PrepareSemanticGenerationBriefTaskInput(BaseModel):
    title: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    audience: str | None = None
    document_ids: list[UUID] = Field(min_length=1, max_length=25)
    concept_keys: list[str] = Field(default_factory=list, max_length=100)
    category_keys: list[str] = Field(default_factory=list, max_length=100)
    target_length: str = Field(default="medium", pattern="^(short|medium|long)$")
    review_policy: str = Field(
        default="allow_candidate_with_disclosure",
        pattern="^(approved_only|allow_candidate_with_disclosure)$",
    )
    include_shadow_candidates: bool = False
    candidate_extractor_name: str = Field(
        default="concept_ranker_v1",
        pattern="^(registry_lexical_v1|concept_ranker_v1)$",
    )
    candidate_score_threshold: float = Field(default=0.34, ge=0.0, le=1.0)
    max_shadow_candidates: int = Field(default=8, ge=1, le=50)


class PrepareSemanticGenerationBriefTaskOutput(BaseModel):
    brief: SemanticGenerationBriefPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class GroundedDocumentClaim(BaseModel):
    claim_id: str
    section_id: str
    rendered_text: str
    concept_keys: list[str] = Field(default_factory=list)
    graph_edge_ids: list[str] = Field(default_factory=list)
    fact_ids: list[UUID] = Field(default_factory=list)
    assertion_ids: list[UUID] = Field(default_factory=list)
    evidence_labels: list[str] = Field(default_factory=list)
    source_document_ids: list[UUID] = Field(default_factory=list)
    support_level: str
    review_policy_status: str
    disclosure_note: str | None = None


class GroundedDocumentSection(BaseModel):
    section_id: str
    title: str
    body_markdown: str
    claim_ids: list[str] = Field(default_factory=list)


class GroundedDocumentDraftPayload(BaseModel):
    document_kind: str = "knowledge_brief"
    title: str
    goal: str
    audience: str | None = None
    review_policy: str
    target_length: str
    brief_task_id: UUID
    generator_name: str
    generator_model: str | None = None
    used_fallback: bool = True
    required_concept_keys: list[str] = Field(default_factory=list)
    document_refs: list[SemanticGenerationDocumentRef] = Field(default_factory=list)
    graph_index: list[SemanticGenerationGraphEdgeRef] = Field(default_factory=list)
    fact_index: list[SemanticGenerationFactRef] = Field(default_factory=list)
    assertion_index: list[SemanticGenerationAssertionRef] = Field(default_factory=list)
    sections: list[GroundedDocumentSection] = Field(default_factory=list)
    claims: list[GroundedDocumentClaim] = Field(default_factory=list)
    evidence_pack: list[SemanticGenerationEvidenceRef] = Field(default_factory=list)
    markdown: str
    markdown_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class DraftSemanticGroundedDocumentTaskInput(BaseModel):
    target_task_id: UUID


class DraftSemanticGroundedDocumentTaskOutput(BaseModel):
    draft: GroundedDocumentDraftPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class VerifySemanticGroundedDocumentTaskInput(BaseModel):
    target_task_id: UUID
    max_unsupported_claim_count: int = Field(default=0, ge=0)
    require_full_claim_traceability: bool = True
    require_full_concept_coverage: bool = True


class VerifySemanticGroundedDocumentTaskOutput(BaseModel):
    draft: GroundedDocumentDraftPayload
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    verification: AgentTaskVerificationResponse
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class TechnicalReportSectionPlan(BaseModel):
    section_id: str
    title: str
    purpose: str
    focus_concept_keys: list[str] = Field(default_factory=list)
    focus_category_keys: list[str] = Field(default_factory=list)
    expected_claim_ids: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    required_graph_edge_ids: list[str] = Field(default_factory=list)


class TechnicalReportPlanPayload(BaseModel):
    document_kind: str = "technical_report_plan"
    report_type: str = "technical_report"
    title: str
    goal: str
    audience: str | None = None
    review_policy: str
    target_length: str
    document_refs: list[SemanticGenerationDocumentRef] = Field(default_factory=list)
    required_concept_keys: list[str] = Field(default_factory=list)
    selected_concept_keys: list[str] = Field(default_factory=list)
    selected_category_keys: list[str] = Field(default_factory=list)
    sections: list[TechnicalReportSectionPlan] = Field(default_factory=list)
    expected_claims: list[SemanticGenerationClaimCandidate] = Field(default_factory=list)
    expected_graph_edge_ids: list[str] = Field(default_factory=list)
    retrieval_plan: list[dict] = Field(default_factory=list)
    semantic_brief: SemanticGenerationBriefPayload
    warnings: list[str] = Field(default_factory=list)
    expert_alignment: list[dict] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class PlanTechnicalReportTaskInput(BaseModel):
    title: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    audience: str | None = None
    document_ids: list[UUID] = Field(min_length=1, max_length=25)
    concept_keys: list[str] = Field(default_factory=list, max_length=100)
    category_keys: list[str] = Field(default_factory=list, max_length=100)
    target_length: str = Field(default="medium", pattern="^(short|medium|long)$")
    review_policy: str = Field(
        default="allow_candidate_with_disclosure",
        pattern="^(approved_only|allow_candidate_with_disclosure)$",
    )
    include_shadow_candidates: bool = False
    candidate_extractor_name: str = Field(
        default="concept_ranker_v1",
        pattern="^(registry_lexical_v1|concept_ranker_v1)$",
    )
    candidate_score_threshold: float = Field(default=0.34, ge=0.0, le=1.0)
    max_shadow_candidates: int = Field(default=8, ge=1, le=50)


class PlanTechnicalReportTaskOutput(BaseModel):
    plan: TechnicalReportPlanPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class TechnicalReportEvidenceCard(BaseModel):
    evidence_card_id: str
    evidence_kind: str
    source_type: str | None = None
    source_locator: str | None = None
    chunk_id: UUID | None = None
    table_id: UUID | None = None
    figure_id: UUID | None = None
    citation_label: str | None = None
    document_id: UUID | None = None
    run_id: UUID | None = None
    semantic_pass_id: UUID | None = None
    source_document_ids: list[UUID] = Field(default_factory=list)
    source_filename: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    excerpt: str | None = None
    source_artifact_api_path: str | None = None
    source_artifact_sha256: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    fact_ids: list[UUID] = Field(default_factory=list)
    assertion_ids: list[UUID] = Field(default_factory=list)
    graph_edge_ids: list[str] = Field(default_factory=list)
    concept_keys: list[str] = Field(default_factory=list)
    support_level: str | None = None
    review_status: str | None = None
    relation_key: str | None = None
    source_search_request_ids: list[UUID] = Field(default_factory=list)
    source_search_request_result_ids: list[UUID] = Field(default_factory=list)
    source_evidence_package_export_ids: list[UUID] = Field(default_factory=list)
    source_evidence_package_sha256s: list[str] = Field(default_factory=list)
    source_evidence_trace_sha256s: list[str] = Field(default_factory=list)
    source_evidence_match_keys: list[str] = Field(default_factory=list)
    source_evidence_match_status: str | None = None
    evidence_package_export_id: UUID | None = None
    evidence_package_sha256: str | None = None
    source_snapshot_sha256s: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class TechnicalReportEvidenceBundlePayload(BaseModel):
    document_kind: str = "technical_report_evidence_cards"
    plan_task_id: UUID
    plan: TechnicalReportPlanPayload
    evidence_cards: list[TechnicalReportEvidenceCard] = Field(default_factory=list)
    claim_evidence_map: list[dict] = Field(default_factory=list)
    retrieval_index: list[dict] = Field(default_factory=list)
    search_evidence_package_exports: list[dict] = Field(default_factory=list)
    graph_context: list[SemanticGenerationGraphEdgeRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    expert_alignment: list[dict] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class BuildReportEvidenceCardsTaskInput(BaseModel):
    target_task_id: UUID


class BuildReportEvidenceCardsTaskOutput(BaseModel):
    evidence_bundle: TechnicalReportEvidenceBundlePayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None
    search_evidence_package_export_count: int = 0


class TechnicalReportToolContract(BaseModel):
    tool_name: str
    purpose: str
    access_pattern: str
    input_contract: dict = Field(default_factory=dict)
    output_contract: dict = Field(default_factory=dict)
    required_capability: str | None = None


class TechnicalReportSkillContract(BaseModel):
    skill_name: str
    purpose: str
    instructions: list[str] = Field(default_factory=list)


class DocumentGenerationContextPackPayload(BaseModel):
    schema_name: str = "document_generation_context_pack"
    schema_version: str = "1.0"
    context_pack_id: str
    harness_task_id: UUID
    evidence_task_id: UUID
    plan_task_id: UUID
    report_request: dict = Field(default_factory=dict)
    workflow_state: dict = Field(default_factory=dict)
    context_refs: list[ContextRef] = Field(default_factory=list)
    retrieval_plan: list[dict] = Field(default_factory=list)
    evidence_cards: list[TechnicalReportEvidenceCard] = Field(default_factory=list)
    search_evidence_package_exports: list[dict] = Field(default_factory=list)
    graph_context: list[SemanticGenerationGraphEdgeRef] = Field(default_factory=list)
    claim_contract: list[dict] = Field(default_factory=list)
    freshness_summary: dict = Field(default_factory=dict)
    quality_contract: dict = Field(default_factory=dict)
    audit_refs: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    expert_alignment: list[dict] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    context_pack_sha256: str | None = None


class DocumentGenerationContextPackEvaluationPayload(BaseModel):
    schema_name: str = "document_generation_context_pack_evaluation"
    schema_version: str = "1.0"
    target_task_id: UUID
    context_pack_id: str
    context_pack_sha256: str
    evaluated_at: datetime
    gate_outcome: str = Field(pattern="^(passed|failed)$")
    thresholds: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)
    checks: list[dict] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class ReportAgentHarnessPayload(BaseModel):
    schema_name: str = "report_agent_harness"
    schema_version: str = "1.0"
    report_request: dict = Field(default_factory=dict)
    workflow_state: dict = Field(default_factory=dict)
    context_refs: list[ContextRef] = Field(default_factory=list)
    document_generation_context_pack: DocumentGenerationContextPackPayload | None = None
    allowed_tools: list[TechnicalReportToolContract] = Field(default_factory=list)
    required_skills: list[TechnicalReportSkillContract] = Field(default_factory=list)
    retrieval_plan: list[dict] = Field(default_factory=list)
    evidence_cards: list[TechnicalReportEvidenceCard] = Field(default_factory=list)
    search_evidence_package_exports: list[dict] = Field(default_factory=list)
    graph_context: list[SemanticGenerationGraphEdgeRef] = Field(default_factory=list)
    claim_contract: list[dict] = Field(default_factory=list)
    failure_policy: dict = Field(default_factory=dict)
    verification_gate: dict = Field(default_factory=dict)
    llm_adapter_contract: dict = Field(default_factory=dict)
    source_plan: TechnicalReportPlanPayload
    warnings: list[str] = Field(default_factory=list)
    expert_alignment: list[dict] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class PrepareReportAgentHarnessTaskInput(BaseModel):
    target_task_id: UUID


class PrepareReportAgentHarnessTaskOutput(BaseModel):
    harness: ReportAgentHarnessPayload
    context_pack: DocumentGenerationContextPackPayload | None = None
    context_pack_artifact_id: UUID | None = None
    context_pack_artifact_kind: str | None = None
    context_pack_artifact_path: str | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class EvaluateDocumentGenerationContextPackTaskInput(BaseModel):
    target_task_id: UUID
    min_traceable_claim_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    min_context_ref_count: int = Field(default=1, ge=0)
    max_blocked_step_count: int = Field(default=0, ge=0)
    require_source_evidence_packages: bool = True
    require_fresh_context: bool = False


class EvaluateDocumentGenerationContextPackTaskOutput(BaseModel):
    harness: ReportAgentHarnessPayload
    context_pack: DocumentGenerationContextPackPayload
    evaluation: DocumentGenerationContextPackEvaluationPayload
    verification: AgentTaskVerificationResponse
    context_pack_artifact_id: UUID | None = None
    context_pack_artifact_kind: str | None = None
    context_pack_artifact_path: str | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None
    operator_run_id: UUID | None = None


class TechnicalReportDraftSection(BaseModel):
    section_id: str
    title: str
    body_markdown: str
    claim_ids: list[str] = Field(default_factory=list)


class TechnicalReportClaim(BaseModel):
    claim_id: str
    section_id: str
    rendered_text: str
    concept_keys: list[str] = Field(default_factory=list)
    evidence_card_ids: list[str] = Field(default_factory=list)
    graph_edge_ids: list[str] = Field(default_factory=list)
    fact_ids: list[UUID] = Field(default_factory=list)
    assertion_ids: list[UUID] = Field(default_factory=list)
    source_document_ids: list[UUID] = Field(default_factory=list)
    support_level: str | None = None
    review_policy_status: str | None = None
    disclosure_note: str | None = None
    source_search_request_ids: list[UUID] = Field(default_factory=list)
    source_search_request_result_ids: list[UUID] = Field(default_factory=list)
    source_evidence_package_export_ids: list[UUID] = Field(default_factory=list)
    source_evidence_package_sha256s: list[str] = Field(default_factory=list)
    source_evidence_trace_sha256s: list[str] = Field(default_factory=list)
    source_evidence_match_keys: list[str] = Field(default_factory=list)
    source_evidence_match_status: str | None = None
    semantic_ontology_snapshot_ids: list[UUID] = Field(default_factory=list)
    semantic_graph_snapshot_ids: list[UUID] = Field(default_factory=list)
    retrieval_reranker_artifact_ids: list[UUID] = Field(default_factory=list)
    search_harness_release_ids: list[UUID] = Field(default_factory=list)
    release_audit_bundle_ids: list[UUID] = Field(default_factory=list)
    release_validation_receipt_ids: list[UUID] = Field(default_factory=list)
    provenance_lock: dict = Field(default_factory=dict)
    provenance_lock_sha256: str | None = None
    support_verdict: str | None = Field(
        default=None,
        pattern="^(supported|unsupported|insufficient_evidence)$",
    )
    support_score: float | None = Field(default=None, ge=0.0, le=1.0)
    support_judge_run_id: UUID | None = None
    support_judgment: dict = Field(default_factory=dict)
    support_judgment_sha256: str | None = None
    derivation_rule: str | None = None
    evidence_package_export_id: UUID | None = None
    evidence_package_sha256: str | None = None
    derivation_sha256: str | None = None
    source_snapshot_sha256s: list[str] = Field(default_factory=list)


class TechnicalReportDraftPayload(BaseModel):
    document_kind: str = "technical_report"
    title: str
    goal: str
    audience: str | None = None
    target_length: str
    harness_task_id: UUID
    generator_mode: str
    generator_model: str | None = None
    used_fallback: bool = True
    llm_adapter_contract: dict = Field(default_factory=dict)
    document_refs: list[SemanticGenerationDocumentRef] = Field(default_factory=list)
    required_concept_keys: list[str] = Field(default_factory=list)
    sections: list[TechnicalReportDraftSection] = Field(default_factory=list)
    claims: list[TechnicalReportClaim] = Field(default_factory=list)
    blocked_claims: list[dict] = Field(default_factory=list)
    evidence_cards: list[TechnicalReportEvidenceCard] = Field(default_factory=list)
    source_evidence_package_exports: list[dict] = Field(default_factory=list)
    graph_context: list[SemanticGenerationGraphEdgeRef] = Field(default_factory=list)
    evidence_package_export_id: UUID | None = None
    evidence_package_sha256: str | None = None
    source_snapshot_sha256s: list[str] = Field(default_factory=list)
    semantic_ontology_snapshot_ids: list[UUID] = Field(default_factory=list)
    semantic_graph_snapshot_ids: list[UUID] = Field(default_factory=list)
    retrieval_reranker_artifact_ids: list[UUID] = Field(default_factory=list)
    search_harness_release_ids: list[UUID] = Field(default_factory=list)
    release_audit_bundle_ids: list[UUID] = Field(default_factory=list)
    release_validation_receipt_ids: list[UUID] = Field(default_factory=list)
    provenance_lock_sha256s: list[str] = Field(default_factory=list)
    provenance_lock_summary: dict = Field(default_factory=dict)
    support_judge_run_id: UUID | None = None
    support_judgment_sha256s: list[str] = Field(default_factory=list)
    claim_support_summary: dict = Field(default_factory=dict)
    claim_derivations: list[dict] = Field(default_factory=list)
    markdown: str
    markdown_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class DraftTechnicalReportTaskInput(BaseModel):
    target_task_id: UUID
    generator_mode: str = Field(
        default="structured_fallback",
        pattern="^(structured_fallback|llm_adapter)$",
    )
    generator_model: str | None = None
    llm_draft_markdown: str | None = None


class DraftTechnicalReportTaskOutput(BaseModel):
    draft: TechnicalReportDraftPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None
    evidence_package_export_id: UUID | None = None
    evidence_package_sha256: str | None = None
    operator_run_id: UUID | None = None
    support_judge_run_id: UUID | None = None
    context_pack_evaluation_task_id: UUID | None = None
    context_pack_verification_id: UUID | None = None
    context_pack_sha256: str | None = None


class VerifyTechnicalReportTaskInput(BaseModel):
    target_task_id: UUID
    max_unsupported_claim_count: int = Field(default=0, ge=0)
    require_full_claim_traceability: bool = True
    require_full_concept_coverage: bool = True
    require_graph_edges_approved: bool = True
    require_frozen_source_evidence: bool = True
    block_stale_context: bool = False
    require_claim_support_judgments: bool = True
    min_claim_support_score: float = Field(default=0.34, ge=0.0, le=1.0)


class VerifyTechnicalReportTaskOutput(BaseModel):
    draft: TechnicalReportDraftPayload
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    verification: AgentTaskVerificationResponse
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None
    operator_run_id: UUID | None = None
    evidence_manifest_id: UUID | None = None
    evidence_manifest_sha256: str | None = None


class ClaimSupportEvaluationFixture(BaseModel):
    case_id: str = Field(min_length=1)
    expected_verdict: str = Field(pattern="^(supported|unsupported|insufficient_evidence)$")
    draft_payload: dict
    claim_id: str | None = None
    description: str | None = None
    hard_case_kind: str | None = None


class ClaimSupportEvaluationCaseResult(BaseModel):
    case_index: int
    case_id: str
    description: str | None = None
    hard_case_kind: str | None = None
    expected_verdict: str
    predicted_verdict: str
    support_score: float | None = None
    passed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    claim_payload: dict = Field(default_factory=dict)
    support_judgment: dict = Field(default_factory=dict)


class EvaluateClaimSupportJudgeTaskInput(BaseModel):
    evaluation_name: str = Field(default="claim_support_judge_calibration", min_length=1)
    fixture_set_name: str = Field(default="default_claim_support_v1", min_length=1)
    fixture_set_version: str = Field(default="v1", min_length=1)
    policy_name: str = Field(default="claim_support_judge_calibration_policy", min_length=1)
    policy_version: str | None = Field(default=None, min_length=1)
    fixtures: list[ClaimSupportEvaluationFixture] = Field(default_factory=list, max_length=100)
    min_support_score: float = Field(default=0.34, ge=0.0, le=1.0)
    min_overall_accuracy: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_precision: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_recall: float = Field(default=1.0, ge=0.0, le=1.0)


class DraftClaimSupportCalibrationPolicyTaskInput(BaseModel):
    policy_name: str = Field(default="claim_support_judge_calibration_policy", min_length=1)
    policy_version: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    owner: str = Field(default="docling-system", min_length=1)
    source: str = Field(default="operator_draft", min_length=1)
    min_support_score: float = Field(default=0.34, ge=0.0, le=1.0)
    min_overall_accuracy: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_precision: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_recall: float = Field(default=1.0, ge=0.0, le=1.0)
    min_hard_case_kind_count: int = Field(default=4, ge=0, le=100)
    required_hard_case_kinds: list[str] = Field(default_factory=list, max_length=100)
    required_verdicts: list[str] = Field(
        default_factory=lambda: ["supported", "unsupported", "insufficient_evidence"],
        max_length=3,
    )


class DraftClaimSupportCalibrationPolicyTaskOutput(BaseModel):
    policy_id: UUID
    policy_name: str
    policy_version: str
    policy_sha256: str
    policy_payload: dict = Field(default_factory=dict)
    active_policy_id: UUID | None = None
    active_policy_sha256: str | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class VerifyClaimSupportCalibrationPolicyTaskInput(BaseModel):
    target_task_id: UUID
    fixture_set_name: str = Field(default="default_claim_support_v1", min_length=1)
    fixture_set_version: str = Field(default="v1", min_length=1)
    fixtures: list[ClaimSupportEvaluationFixture] = Field(default_factory=list, max_length=100)
    include_mined_failures: bool = True
    mined_failure_limit: int = Field(default=20, ge=0, le=100)


class VerifyClaimSupportCalibrationPolicyTaskOutput(BaseModel):
    draft_policy: dict = Field(default_factory=dict)
    evaluation: dict = Field(default_factory=dict)
    verification: AgentTaskVerificationResponse
    mined_failure_summary: dict = Field(default_factory=dict)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class ApplyClaimSupportCalibrationPolicyTaskInput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str = Field(min_length=1)


class ApplyClaimSupportCalibrationPolicyTaskOutput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_note: str | None = None
    previous_active_policy_id: UUID | None = None
    previous_active_policy_sha256: str | None = None
    activated_policy_id: UUID
    activated_policy_sha256: str
    policy_name: str
    policy_version: str
    draft_policy_sha256: str
    verification_id: UUID
    verification_outcome: str
    verification_reasons: list[str] = Field(default_factory=list)
    verification_evaluation_id: UUID | None = None
    verification_fixture_set_id: UUID | None = None
    verification_fixture_set_sha256: str | None = None
    verification_policy_sha256: str
    verification_mined_failure_summary: dict = Field(default_factory=dict)
    operator_run_id: UUID | None = None
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None
    activation_governance_artifact_id: UUID | None = None
    activation_governance_artifact_kind: str | None = None
    activation_governance_artifact_path: str | None = None
    activation_governance_payload_sha256: str | None = None
    activation_governance_receipt_sha256: str | None = None
    activation_governance_signature_status: str | None = None
    activation_governance_prov_jsonld_sha256: str | None = None
    activation_governance_event_id: UUID | None = None
    activation_governance_event_hash: str | None = None
    activation_change_impact_id: UUID | None = None
    activation_change_impact_payload_sha256: str | None = None
    activation_change_impact_summary: dict = Field(default_factory=dict)
    activation_change_impact_replay_recommended_count: int | None = None


class EvaluateClaimSupportJudgeTaskOutput(BaseModel):
    evaluation_id: UUID
    evaluation_name: str
    fixture_set_id: UUID | None = None
    fixture_set_name: str
    fixture_set_version: str = "v1"
    fixture_set_sha256: str
    policy_id: UUID | None = None
    policy_name: str | None = None
    policy_version: str | None = None
    policy_sha256: str | None = None
    calibration_policy: dict = Field(default_factory=dict)
    judge_name: str
    judge_version: str
    thresholds: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)
    verdict_metrics: dict = Field(default_factory=dict)
    case_results: list[ClaimSupportEvaluationCaseResult] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    operator_run_id: UUID | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticSupervisionCorpusRow(BaseModel):
    row_id: str
    row_type: str
    label_type: str
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID | None = None
    source_ref: str
    concept_key: str | None = None
    category_key: str | None = None
    review_status: str | None = None
    registry_version: str | None = None
    registry_sha256: str | None = None
    evidence_span: dict = Field(default_factory=dict)
    verification_outcome: str | None = None
    details: dict = Field(default_factory=dict)


class SemanticSupervisionCorpusPayload(BaseModel):
    corpus_name: str
    document_count: int = 0
    row_count: int = 0
    row_type_counts: dict[str, int] = Field(default_factory=dict)
    label_type_counts: dict[str, int] = Field(default_factory=dict)
    rows: list[SemanticSupervisionCorpusRow] = Field(default_factory=list)
    jsonl_path: str | None = None
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class ExportSemanticSupervisionCorpusTaskInput(BaseModel):
    document_ids: list[UUID] = Field(default_factory=list, max_length=25)
    reviewed_only: bool = True
    include_generation_verifications: bool = True


class ExportSemanticSupervisionCorpusTaskOutput(BaseModel):
    corpus: SemanticSupervisionCorpusPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticBootstrapCandidateEvidenceRef(BaseModel):
    document_id: UUID
    run_id: UUID
    source_type: str
    source_locator: str
    page_from: int | None = None
    page_to: int | None = None
    excerpt: str | None = None
    source_artifact_api_path: str | None = None
    source_artifact_sha256: str | None = None


class SemanticBootstrapCandidate(BaseModel):
    candidate_id: str
    concept_key: str
    preferred_label: str
    normalized_phrase: str
    phrase_tokens: list[str] = Field(default_factory=list)
    epistemic_status: str = "candidate_bootstrap"
    document_ids: list[UUID] = Field(default_factory=list)
    document_count: int = 0
    source_count: int = 0
    source_types: list[str] = Field(default_factory=list)
    score: float
    evidence_refs: list[SemanticBootstrapCandidateEvidenceRef] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class SemanticBootstrapCandidateReport(BaseModel):
    report_name: str = "semantic_bootstrap_candidate_report"
    extraction_strategy: str
    input_document_ids: list[UUID] = Field(default_factory=list)
    document_count: int = 0
    total_source_count: int = 0
    existing_registry_term_exclusion: bool = True
    candidate_count: int = 0
    candidates: list[SemanticBootstrapCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class DiscoverSemanticBootstrapCandidatesTaskInput(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=25)
    max_candidates: int = Field(default=12, ge=1, le=50)
    min_document_count: int = Field(default=1, ge=1, le=25)
    min_source_count: int = Field(default=2, ge=1, le=100)
    min_phrase_tokens: int = Field(default=2, ge=1, le=4)
    max_phrase_tokens: int = Field(default=4, ge=1, le=6)
    exclude_existing_registry_terms: bool = True


class DiscoverSemanticBootstrapCandidatesTaskOutput(BaseModel):
    report: SemanticBootstrapCandidateReport
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class BuildDocumentFactGraphTaskInput(BaseModel):
    document_id: UUID
    minimum_review_status: str = Field(
        default="approved",
        pattern="^(candidate|approved)$",
    )


class BuildDocumentFactGraphTaskOutput(BaseModel):
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    ontology_snapshot_id: UUID | None = None
    ontology_version: str
    fact_count: int = 0
    approved_fact_count: int = 0
    entity_count: int = 0
    relation_counts: dict[str, int] = Field(default_factory=dict)
    facts: list[SemanticGenerationFactRef] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticGraphExtractorDescriptor(BaseModel):
    extractor_name: str
    backing_model: str
    match_strategy: str
    shadow_mode: bool = True
    provider_name: str | None = None


class SemanticGraphNode(BaseModel):
    entity_key: str
    concept_key: str
    preferred_label: str
    category_keys: list[str] = Field(default_factory=list)
    document_ids: list[UUID] = Field(default_factory=list)
    document_count: int = 0
    source_types: list[str] = Field(default_factory=list)
    review_status_counts: dict[str, int] = Field(default_factory=dict)
    assertion_count: int = 0
    evidence_count: int = 0


class SemanticGraphSupportRef(BaseModel):
    support_ref_id: str
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    assertion_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    concept_keys: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    shared_category_keys: list[str] = Field(default_factory=list)
    score: float


class SemanticGraphEdge(BaseModel):
    edge_id: str
    relation_key: str
    relation_label: str
    subject_entity_key: str
    subject_label: str
    object_entity_key: str
    object_label: str
    epistemic_status: str
    review_status: str
    support_level: str
    extractor_name: str
    extractor_score: float
    supporting_document_ids: list[UUID] = Field(default_factory=list)
    supporting_document_count: int = 0
    supporting_assertion_count: int = 0
    supporting_evidence_count: int = 0
    shared_category_keys: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    support_refs: list[SemanticGraphSupportRef] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class SemanticGraphSnapshotPayload(BaseModel):
    graph_name: str
    graph_version: str
    ontology_snapshot_id: UUID
    ontology_version: str
    ontology_sha256: str
    upper_ontology_version: str
    extractor: SemanticGraphExtractorDescriptor
    shadow_mode: bool = True
    minimum_review_status: str
    document_ids: list[UUID] = Field(default_factory=list)
    document_count: int = 0
    document_refs: list[dict] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    nodes: list[SemanticGraphNode] = Field(default_factory=list)
    edges: list[SemanticGraphEdge] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class BuildShadowSemanticGraphTaskInput(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=25)
    relation_extractor_name: str = Field(
        default="relation_ranker_v1",
        pattern="^(cooccurrence_v1|relation_ranker_v1)$",
    )
    minimum_review_status: str = Field(
        default="candidate",
        pattern="^(candidate|approved)$",
    )
    min_shared_documents: int = Field(default=2, ge=1, le=25)
    score_threshold: float = Field(default=0.45, ge=0.0, le=1.0)


class BuildShadowSemanticGraphTaskOutput(BaseModel):
    shadow_graph: SemanticGraphSnapshotPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticGraphEvaluationEdgeReport(BaseModel):
    edge_id: str
    relation_key: str
    subject_entity_key: str
    subject_label: str
    object_entity_key: str
    object_label: str
    expected_edge: bool = False
    in_live_graph: bool = False
    baseline_found: bool = False
    candidate_found: bool = False
    baseline_score: float = 0.0
    candidate_score: float = 0.0
    supporting_document_ids: list[UUID] = Field(default_factory=list)
    support_refs: list[SemanticGraphSupportRef] = Field(default_factory=list)


class EvaluateSemanticRelationExtractorTaskInput(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=25)
    baseline_extractor_name: str = Field(
        default="cooccurrence_v1",
        pattern="^(cooccurrence_v1|relation_ranker_v1)$",
    )
    candidate_extractor_name: str = Field(
        default="relation_ranker_v1",
        pattern="^(cooccurrence_v1|relation_ranker_v1)$",
    )
    minimum_review_status: str = Field(
        default="candidate",
        pattern="^(candidate|approved)$",
    )
    baseline_min_shared_documents: int = Field(default=2, ge=1, le=25)
    candidate_score_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    expected_min_shared_documents: int = Field(default=1, ge=1, le=25)


class EvaluateSemanticRelationExtractorTaskOutput(BaseModel):
    baseline_extractor: SemanticGraphExtractorDescriptor
    candidate_extractor: SemanticGraphExtractorDescriptor
    ontology_snapshot_id: UUID
    ontology_version: str
    document_refs: list[dict] = Field(default_factory=list)
    edge_reports: list[SemanticGraphEvaluationEdgeReport] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticGraphDisagreementIssue(BaseModel):
    issue_id: str
    edge_id: str
    relation_key: str
    subject_entity_key: str
    subject_label: str
    object_entity_key: str
    object_label: str
    severity: str
    expected_edge: bool = False
    in_live_graph: bool = False
    baseline_found: bool = False
    candidate_found: bool = False
    candidate_score: float
    supporting_document_ids: list[UUID] = Field(default_factory=list)
    support_refs: list[SemanticGraphSupportRef] = Field(default_factory=list)
    summary: str
    details: dict = Field(default_factory=dict)


class SemanticGraphDisagreementFollowup(BaseModel):
    followup_kind: str
    reason: str
    edge_id: str


class SemanticGraphDisagreementReport(BaseModel):
    issue_count: int = 0
    issues: list[SemanticGraphDisagreementIssue] = Field(default_factory=list)
    recommended_followups: list[SemanticGraphDisagreementFollowup] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class TriageSemanticGraphDisagreementsTaskInput(BaseModel):
    target_task_id: UUID
    min_score: float = Field(default=0.45, ge=0.0, le=1.0)
    expected_only: bool = True


class TriageSemanticGraphDisagreementsTaskOutput(BaseModel):
    evaluation_task_id: UUID
    disagreement_report: SemanticGraphDisagreementReport
    verification: AgentTaskVerificationResponse
    recommendation: dict = Field(default_factory=dict)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class DraftGraphPromotionsTaskInput(BaseModel):
    source_task_id: UUID
    edge_ids: list[str] = Field(default_factory=list, max_length=200)
    proposed_graph_version: str | None = None
    rationale: str | None = None
    min_score: float = Field(default=0.45, ge=0.0, le=1.0)


class DraftGraphPromotionsPayload(BaseModel):
    base_snapshot_id: UUID | None = None
    base_graph_version: str | None = None
    proposed_graph_version: str
    ontology_snapshot_id: UUID
    ontology_version: str
    ontology_sha256: str
    source_task_id: UUID
    source_task_type: str
    rationale: str | None = None
    promoted_edges: list[SemanticGraphEdge] = Field(default_factory=list)
    effective_graph: SemanticGraphSnapshotPayload
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class DraftGraphPromotionsTaskOutput(BaseModel):
    draft: DraftGraphPromotionsPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class VerifyDraftGraphPromotionsTaskInput(BaseModel):
    target_task_id: UUID
    min_supporting_document_count: int = Field(default=2, ge=1, le=25)
    max_conflict_count: int = Field(default=0, ge=0, le=100)
    require_current_ontology_snapshot: bool = True


class VerifyDraftGraphPromotionsTaskOutput(BaseModel):
    draft: DraftGraphPromotionsPayload
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    verification: AgentTaskVerificationResponse
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class ApplyGraphPromotionsTaskInput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str | None = None


class ApplyGraphPromotionsTaskOutput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    applied_snapshot_id: UUID
    applied_graph_version: str
    applied_graph_sha256: str
    ontology_snapshot_id: UUID | None = None
    reason: str | None = None
    applied_edge_count: int = 0
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticCandidateExtractorDescriptor(BaseModel):
    extractor_name: str
    backing_model: str
    match_strategy: str
    shadow_mode: bool = True
    provider_name: str | None = None


class SemanticCandidateConceptScore(BaseModel):
    concept_key: str
    preferred_label: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)
    category_keys: list[str] = Field(default_factory=list)


class SemanticCandidateSourcePrediction(BaseModel):
    source_key: str
    source_type: str
    source_locator: str
    page_from: int | None = None
    page_to: int | None = None
    excerpt: str | None = None
    source_artifact_api_path: str | None = None
    source_artifact_sha256: str | None = None
    candidates: list[SemanticCandidateConceptScore] = Field(default_factory=list)


class SemanticCandidateDocumentReport(BaseModel):
    document_id: UUID
    run_id: UUID
    semantic_pass_id: UUID
    registry_version: str
    registry_sha256: str
    evaluation_fixture_name: str | None = None
    expected_concept_keys: list[str] = Field(default_factory=list)
    live_concept_keys: list[str] = Field(default_factory=list)
    baseline_predicted_concept_keys: list[str] = Field(default_factory=list)
    candidate_predicted_concept_keys: list[str] = Field(default_factory=list)
    improved_expected_concept_keys: list[str] = Field(default_factory=list)
    regressed_expected_concept_keys: list[str] = Field(default_factory=list)
    candidate_only_concept_keys: list[str] = Field(default_factory=list)
    shadow_candidates: list[SemanticShadowCandidateConcept] = Field(default_factory=list)
    source_predictions: list[SemanticCandidateSourcePrediction] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class EvaluateSemanticCandidateExtractorTaskInput(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=25)
    candidate_extractor_name: str = Field(
        default="concept_ranker_v1",
        pattern="^(registry_lexical_v1|concept_ranker_v1)$",
    )
    baseline_extractor_name: str = Field(
        default="registry_lexical_v1",
        pattern="^(registry_lexical_v1|concept_ranker_v1)$",
    )
    max_candidates_per_source: int = Field(default=3, ge=1, le=10)
    score_threshold: float = Field(default=0.34, ge=0.0, le=1.0)


class EvaluateSemanticCandidateExtractorTaskOutput(BaseModel):
    baseline_extractor: SemanticCandidateExtractorDescriptor
    candidate_extractor: SemanticCandidateExtractorDescriptor
    document_reports: list[SemanticCandidateDocumentReport] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class SemanticCandidateDisagreementIssue(BaseModel):
    issue_id: str
    document_id: UUID
    concept_key: str
    severity: str
    expected_by_evaluation: bool = False
    in_live_semantics: bool = False
    baseline_found: bool = False
    max_score: float
    summary: str
    evidence_refs: list[SemanticShadowCandidateEvidenceRef] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class SemanticCandidateDisagreementReport(BaseModel):
    baseline_extractor_name: str
    candidate_extractor_name: str
    issue_count: int = 0
    issues: list[SemanticCandidateDisagreementIssue] = Field(default_factory=list)
    recommended_followups: list[SemanticRecommendedFollowup] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class TriageSemanticCandidateDisagreementsTaskInput(BaseModel):
    target_task_id: UUID
    min_score: float = Field(default=0.34, ge=0.0, le=1.0)
    include_expected_only: bool = False


class TriageSemanticCandidateDisagreementsTaskOutput(BaseModel):
    evaluation_task_id: UUID
    disagreement_report: SemanticCandidateDisagreementReport
    verification: AgentTaskVerificationResponse
    recommendation: dict = Field(default_factory=dict)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


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


class TriageRecommendationPayload(BaseModel):
    next_action: str
    confidence: str
    summary: str


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
