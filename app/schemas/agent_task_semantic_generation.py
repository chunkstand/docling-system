from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent_task_core import AgentTaskVerificationResponse
from app.schemas.agent_task_semantics import SemanticSuccessMetricCheck


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


__all__ = [
    "DraftSemanticGroundedDocumentTaskInput",
    "DraftSemanticGroundedDocumentTaskOutput",
    "GroundedDocumentClaim",
    "GroundedDocumentDraftPayload",
    "GroundedDocumentSection",
    "PrepareSemanticGenerationBriefTaskInput",
    "PrepareSemanticGenerationBriefTaskOutput",
    "SemanticDossierConceptEntry",
    "SemanticGenerationAssertionRef",
    "SemanticGenerationBriefPayload",
    "SemanticGenerationClaimCandidate",
    "SemanticGenerationDocumentRef",
    "SemanticGenerationEvidenceRef",
    "SemanticGenerationFactRef",
    "SemanticGenerationGraphEdgeRef",
    "SemanticGenerationSectionPlan",
    "SemanticShadowCandidateConcept",
    "SemanticShadowCandidateEvidenceRef",
    "VerifySemanticGroundedDocumentTaskInput",
    "VerifySemanticGroundedDocumentTaskOutput",
]
