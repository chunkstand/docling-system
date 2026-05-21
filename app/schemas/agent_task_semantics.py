from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.agent_task_core import AgentTaskVerificationResponse, TriageRecommendationPayload
from app.schemas.evaluations import EvaluationDetailResponse
from app.schemas.semantics import DocumentSemanticPassResponse


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


class OntologySlicePayload(BaseModel):
    slice_key: str
    status: str = "unspecified"
    layer_keys: list[str] = Field(default_factory=list)
    entity_type_keys: list[str] = Field(default_factory=list)
    relation_keys: list[str] = Field(default_factory=list)
    entity_type_count: int = 0
    relation_count: int = 0
    slice_sha256: str | None = None


class OntologyCompetencyFamilyPayload(BaseModel):
    family_key: str
    status: str = "unspecified"
    slice_keys: list[str] = Field(default_factory=list)


class OntologyContractRuntimePayload(BaseModel):
    contract_path: str | None = None
    contract_schema_name: str | None = None
    contract_schema_version: str | None = None
    contract_version: str | None = None
    contract_upper_ontology_version: str | None = None
    contract_sha256: str | None = None
    contract_layer_count: int = 0
    layer_versions: dict[str, str] = Field(default_factory=dict)
    layer_kind_versions: dict[str, str] = Field(default_factory=dict)
    ontology_slice_count: int = 0
    ontology_slices: list[OntologySlicePayload] = Field(default_factory=list)
    competency_family_count: int = 0
    competency_families: list[OntologyCompetencyFamilyPayload] = Field(default_factory=list)


class ActiveOntologySnapshotPayload(OntologyContractRuntimePayload):
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


SemanticRegistryOperationType = Literal[
    "add_concept",
    "add_alias",
    "add_category_binding",
    "split_concept",
    "merge_concept",
    "deprecate_concept",
    "replace_concept",
    "migrate_concept",
]


class SemanticRegistryLifecycleSuccessorConcept(BaseModel):
    concept_key: str
    preferred_label: str | None = None
    aliases: list[str] = Field(default_factory=list)
    category_keys: list[str] = Field(default_factory=list)
    scope_note: str | None = None


class SemanticRegistryUpdateOperation(BaseModel):
    operation_id: str
    operation_type: SemanticRegistryOperationType
    concept_key: str
    preferred_label: str | None = None
    alias_text: str | None = None
    category_key: str | None = None
    source_issue_ids: list[str] = Field(default_factory=list)
    rationale: str | None = None
    source_concept_keys: list[str] = Field(default_factory=list)
    successor_concepts: list[SemanticRegistryLifecycleSuccessorConcept] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_operation_shape(self) -> SemanticRegistryUpdateOperation:
        if self.operation_type == "add_alias":
            if not self.alias_text:
                raise ValueError("add_alias operations require alias_text.")
            if self.source_concept_keys or self.successor_concepts:
                raise ValueError(
                    "add_alias operations do not accept lifecycle source or successor fields."
                )
        elif self.operation_type == "add_category_binding":
            if not self.category_key:
                raise ValueError("add_category_binding operations require category_key.")
            if self.source_concept_keys or self.successor_concepts:
                raise ValueError(
                    "add_category_binding operations do not accept lifecycle source or "
                    "successor fields."
                )
        elif self.operation_type == "split_concept":
            if len(self.successor_concepts) < 2:
                raise ValueError(
                    "split_concept operations require at least two successor_concepts."
                )
            if self.source_concept_keys:
                raise ValueError(
                    "split_concept operations use concept_key as the source and do not accept "
                    "source_concept_keys."
                )
        elif self.operation_type == "merge_concept":
            source_concept_keys = {
                concept_key.strip()
                for concept_key in self.source_concept_keys
                if concept_key.strip()
            }
            if len(source_concept_keys) < 2:
                raise ValueError(
                    "merge_concept operations require at least two source_concept_keys."
                )
            if self.concept_key in source_concept_keys:
                raise ValueError(
                    "merge_concept operations cannot list concept_key as one of the merged "
                    "source_concept_keys."
                )
            if self.successor_concepts:
                raise ValueError(
                    "merge_concept operations use concept_key as the surviving target and do "
                    "not accept successor_concepts."
                )
        elif self.operation_type == "deprecate_concept":
            if not self.successor_concepts:
                raise ValueError(
                    "deprecate_concept operations require successor_concepts so replacement "
                    "lineage stays machine-readable."
                )
            if self.source_concept_keys:
                raise ValueError(
                    "deprecate_concept operations use concept_key as the deprecated source and "
                    "do not accept source_concept_keys."
                )
        elif self.operation_type == "replace_concept":
            if len(self.successor_concepts) != 1:
                raise ValueError(
                    "replace_concept operations require exactly one successor_concept."
                )
            if self.successor_concepts[0].concept_key == self.concept_key:
                raise ValueError(
                    "replace_concept operations require a successor concept distinct from the "
                    "replaced concept_key."
                )
            if self.source_concept_keys:
                raise ValueError(
                    "replace_concept operations use concept_key as the replaced source and do "
                    "not accept source_concept_keys."
                )
        elif self.operation_type == "migrate_concept":
            if not self.successor_concepts:
                raise ValueError(
                    "migrate_concept operations require successor_concepts so migration intent "
                    "stays machine-readable."
                )
            if self.source_concept_keys:
                raise ValueError(
                    "migrate_concept operations use concept_key as the migrated source and do "
                    "not accept source_concept_keys."
                )
        return self


class SemanticRegistryDraftPayload(BaseModel):
    base_registry_version: str
    proposed_registry_version: str
    source_task_id: UUID
    source_task_type: str | None = None
    rationale: str | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    operation_contract_version: str | None = None
    operations: list[SemanticRegistryUpdateOperation] = Field(default_factory=list)
    effective_registry: dict = Field(default_factory=dict)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)


class DraftSemanticRegistryUpdateTaskOutput(BaseModel):
    draft: SemanticRegistryDraftPayload
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class DraftOntologyExtensionTaskInput(BaseModel):
    source_task_id: UUID | None = None
    proposed_ontology_version: str | None = Field(default=None, min_length=1)
    rationale: str | None = None
    candidate_ids: list[str] = Field(default_factory=list, max_length=50)
    operations: list[SemanticRegistryUpdateOperation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ontology_draft_input(self) -> DraftOntologyExtensionTaskInput:
        if self.source_task_id is None and not self.operations:
            raise ValueError(
                "Ontology extension drafts require source_task_id or explicit operations."
            )
        if self.operations and self.source_task_id is not None:
            raise ValueError(
                "Explicit ontology lifecycle operations cannot be combined with source_task_id "
                "in the current lifecycle draft contract."
            )
        if self.operations and self.candidate_ids:
            raise ValueError(
                "Explicit ontology lifecycle operations cannot be combined with candidate_ids."
            )
        return self


class OntologyExtensionDraftPayload(OntologyContractRuntimePayload):
    base_snapshot_id: UUID
    base_ontology_version: str
    proposed_ontology_version: str
    upper_ontology_version: str
    source_task_id: UUID | None = None
    source_task_type: str | None = None
    rationale: str | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    operation_contract_version: str | None = None
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


class ApplyOntologyExtensionTaskOutput(OntologyContractRuntimePayload):
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


__all__ = [
    "LatestEvaluationTaskInput",
    "LatestEvaluationTaskOutput",
    "SemanticSuccessMetricCheck",
    "LatestSemanticPassTaskInput",
    "LatestSemanticPassTaskOutput",
    "OntologySlicePayload",
    "OntologyCompetencyFamilyPayload",
    "OntologyContractRuntimePayload",
    "ActiveOntologySnapshotPayload",
    "InitializeWorkspaceOntologyTaskInput",
    "InitializeWorkspaceOntologyTaskOutput",
    "GetActiveOntologySnapshotTaskInput",
    "GetActiveOntologySnapshotTaskOutput",
    "SemanticRegistryUpdateHint",
    "SemanticIssueEvidenceRef",
    "SemanticGapIssue",
    "SemanticRecommendedFollowup",
    "SemanticGapReport",
    "TriageSemanticPassTaskInput",
    "TriageSemanticPassTaskOutput",
    "DraftSemanticRegistryUpdateTaskInput",
    "SemanticRegistryLifecycleSuccessorConcept",
    "SemanticRegistryUpdateOperation",
    "SemanticRegistryDraftPayload",
    "DraftSemanticRegistryUpdateTaskOutput",
    "DraftOntologyExtensionTaskInput",
    "OntologyExtensionDraftPayload",
    "DraftOntologyExtensionTaskOutput",
    "VerifyDraftSemanticRegistryUpdateTaskInput",
    "SemanticRegistryDocumentDelta",
    "VerifyDraftSemanticRegistryUpdateTaskOutput",
    "VerifyDraftOntologyExtensionTaskInput",
    "VerifyDraftOntologyExtensionTaskOutput",
    "ApplySemanticRegistryUpdateTaskInput",
    "ApplySemanticRegistryUpdateTaskOutput",
    "ApplyOntologyExtensionTaskInput",
    "ApplyOntologyExtensionTaskOutput",
]
