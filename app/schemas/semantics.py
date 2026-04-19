from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SemanticAssertionEvidenceResponse(BaseModel):
    evidence_id: UUID
    source_type: str
    chunk_id: UUID | None = None
    table_id: UUID | None = None
    figure_id: UUID | None = None
    page_from: int | None = None
    page_to: int | None = None
    matched_terms: list[str]
    excerpt: str | None = None
    source_label: str | None = None
    source_artifact_api_path: str | None = None
    source_artifact_sha256: str | None = None
    details: dict


class SemanticConceptCategoryBindingResponse(BaseModel):
    binding_id: UUID
    concept_key: str
    category_key: str
    category_label: str
    binding_type: str
    created_from: str
    review_status: str
    details: dict


class SemanticAssertionCategoryBindingResponse(BaseModel):
    binding_id: UUID
    category_key: str
    category_label: str
    binding_type: str
    created_from: str
    review_status: str
    details: dict


class SemanticReviewDecisionRequest(BaseModel):
    review_status: str = Field(pattern="^(candidate|approved|rejected)$")
    review_note: str | None = None
    reviewed_by: str | None = None


class SemanticReviewEventResponse(BaseModel):
    review_id: UUID
    scope: str
    document_id: UUID
    semantic_pass_id: UUID
    assertion_id: UUID | None = None
    binding_id: UUID | None = None
    concept_key: str
    category_key: str | None = None
    review_status: str
    review_note: str | None = None
    reviewed_by: str | None = None
    created_at: datetime


class SemanticContinuityResponse(BaseModel):
    semantic_pass_id: UUID
    document_id: UUID
    run_id: UUID
    baseline_run_id: UUID | None = None
    baseline_semantic_pass_id: UUID | None = None
    summary: dict


class SemanticAssertionResponse(BaseModel):
    assertion_id: UUID
    concept_key: str
    preferred_label: str
    scope_note: str | None = None
    assertion_kind: str
    epistemic_status: str
    context_scope: str
    review_status: str
    matched_terms: list[str]
    source_types: list[str]
    evidence_count: int
    confidence: float | None = None
    details: dict
    category_bindings: list[SemanticAssertionCategoryBindingResponse]
    evidence: list[SemanticAssertionEvidenceResponse]


class DocumentSemanticPassResponse(BaseModel):
    semantic_pass_id: UUID
    document_id: UUID
    run_id: UUID
    status: str
    registry_version: str
    registry_sha256: str
    extractor_version: str
    artifact_schema_version: str
    baseline_run_id: UUID | None = None
    baseline_semantic_pass_id: UUID | None = None
    has_json_artifact: bool = False
    has_yaml_artifact: bool = False
    artifact_json_sha256: str | None = None
    artifact_yaml_sha256: str | None = None
    assertion_count: int = 0
    evidence_count: int = 0
    summary: dict
    evaluation_status: str
    evaluation_fixture_name: str | None = None
    evaluation_version: int
    evaluation_summary: dict
    continuity_summary: dict
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    concept_category_bindings: list[SemanticConceptCategoryBindingResponse]
    assertions: list[SemanticAssertionResponse]
