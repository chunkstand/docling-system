from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent_task_core import AgentTaskVerificationResponse
from app.schemas.agent_task_semantic_generation import (
    SemanticGenerationFactRef,
    SemanticShadowCandidateConcept,
    SemanticShadowCandidateEvidenceRef,
)
from app.schemas.agent_task_semantics import (
    SemanticRecommendedFollowup,
    SemanticSuccessMetricCheck,
)


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


__all__ = [
    "SemanticSupervisionCorpusRow",
    "SemanticSupervisionCorpusPayload",
    "ExportSemanticSupervisionCorpusTaskInput",
    "ExportSemanticSupervisionCorpusTaskOutput",
    "SemanticBootstrapCandidateEvidenceRef",
    "SemanticBootstrapCandidate",
    "SemanticBootstrapCandidateReport",
    "DiscoverSemanticBootstrapCandidatesTaskInput",
    "DiscoverSemanticBootstrapCandidatesTaskOutput",
    "BuildDocumentFactGraphTaskInput",
    "BuildDocumentFactGraphTaskOutput",
    "SemanticGraphExtractorDescriptor",
    "SemanticGraphNode",
    "SemanticGraphSupportRef",
    "SemanticGraphEdge",
    "SemanticGraphSnapshotPayload",
    "BuildShadowSemanticGraphTaskInput",
    "BuildShadowSemanticGraphTaskOutput",
    "SemanticGraphEvaluationEdgeReport",
    "EvaluateSemanticRelationExtractorTaskInput",
    "EvaluateSemanticRelationExtractorTaskOutput",
    "SemanticGraphDisagreementIssue",
    "SemanticGraphDisagreementFollowup",
    "SemanticGraphDisagreementReport",
    "TriageSemanticGraphDisagreementsTaskInput",
    "TriageSemanticGraphDisagreementsTaskOutput",
    "DraftGraphPromotionsTaskInput",
    "DraftGraphPromotionsPayload",
    "DraftGraphPromotionsTaskOutput",
    "VerifyDraftGraphPromotionsTaskInput",
    "VerifyDraftGraphPromotionsTaskOutput",
    "ApplyGraphPromotionsTaskInput",
    "ApplyGraphPromotionsTaskOutput",
    "SemanticCandidateExtractorDescriptor",
    "SemanticCandidateConceptScore",
    "SemanticCandidateSourcePrediction",
    "SemanticCandidateDocumentReport",
    "EvaluateSemanticCandidateExtractorTaskInput",
    "EvaluateSemanticCandidateExtractorTaskOutput",
    "SemanticCandidateDisagreementIssue",
    "SemanticCandidateDisagreementReport",
    "TriageSemanticCandidateDisagreementsTaskInput",
    "TriageSemanticCandidateDisagreementsTaskOutput",
]
