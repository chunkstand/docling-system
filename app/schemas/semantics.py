from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
    source_artifact_path: str | None = None
    source_artifact_sha256: str | None = None
    details: dict


class SemanticAssertionResponse(BaseModel):
    assertion_id: UUID
    concept_key: str
    preferred_label: str
    scope_note: str | None = None
    assertion_kind: str
    matched_terms: list[str]
    source_types: list[str]
    evidence_count: int
    confidence: float | None = None
    details: dict
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
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    assertions: list[SemanticAssertionResponse]
