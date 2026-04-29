from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent_task_core import AgentTaskVerificationResponse, ContextRef
from app.schemas.agent_task_semantic_generation import (
    SemanticGenerationBriefPayload,
    SemanticGenerationClaimCandidate,
    SemanticGenerationDocumentRef,
    SemanticGenerationGraphEdgeRef,
)
from app.schemas.agent_task_semantics import (
    SemanticSuccessMetricCheck,
)


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
    release_readiness_assessments: list[dict] = Field(default_factory=list)
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
    require_release_readiness_assessments: bool = True
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


__all__ = [
    "TechnicalReportSectionPlan",
    "TechnicalReportPlanPayload",
    "PlanTechnicalReportTaskInput",
    "PlanTechnicalReportTaskOutput",
    "TechnicalReportEvidenceCard",
    "TechnicalReportEvidenceBundlePayload",
    "BuildReportEvidenceCardsTaskInput",
    "BuildReportEvidenceCardsTaskOutput",
    "TechnicalReportToolContract",
    "TechnicalReportSkillContract",
    "DocumentGenerationContextPackPayload",
    "DocumentGenerationContextPackEvaluationPayload",
    "ReportAgentHarnessPayload",
    "PrepareReportAgentHarnessTaskInput",
    "PrepareReportAgentHarnessTaskOutput",
    "EvaluateDocumentGenerationContextPackTaskInput",
    "EvaluateDocumentGenerationContextPackTaskOutput",
    "TechnicalReportDraftSection",
    "TechnicalReportClaim",
    "TechnicalReportDraftPayload",
    "DraftTechnicalReportTaskInput",
    "DraftTechnicalReportTaskOutput",
    "VerifyTechnicalReportTaskInput",
    "VerifyTechnicalReportTaskOutput",
]
