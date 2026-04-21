from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SemanticBackfillReadiness(BaseModel):
    ready: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class SemanticBackfillRegistryStatus(BaseModel):
    snapshot_id: UUID | None = None
    registry_name: str | None = None
    registry_version: str | None = None
    registry_sha256: str | None = None
    upper_ontology_version: str | None = None
    concept_count: int = 0
    category_count: int = 0
    relation_count: int = 0
    relation_keys: list[str] = Field(default_factory=list)


class SemanticBackfillGraphStatus(BaseModel):
    active_snapshot_id: UUID | None = None
    graph_version: str | None = None
    edge_count: int = 0
    node_count: int = 0
    ontology_snapshot_id: UUID | None = None


class SemanticBackfillStatusResponse(BaseModel):
    schema_name: str = "semantic_backfill_status"
    schema_version: str = "1.0"
    semantics_enabled: bool = False
    active_document_count: int = 0
    active_run_count: int = 0
    current_registry: SemanticBackfillRegistryStatus
    semantic_pass_counts: dict[str, int] = Field(default_factory=dict)
    active_current_pass_count: int = 0
    missing_current_pass_count: int = 0
    stale_or_failed_pass_count: int = 0
    assertion_count: int = 0
    evidence_count: int = 0
    fact_count: int = 0
    entity_count: int = 0
    graph: SemanticBackfillGraphStatus
    readiness: SemanticBackfillReadiness
    sample_missing_documents: list[dict] = Field(default_factory=list)
    updated_at: datetime


class SemanticBackfillRequest(BaseModel):
    document_ids: list[UUID] = Field(default_factory=list, max_length=500)
    limit: int = Field(default=10, ge=1, le=500)
    force: bool = False
    dry_run: bool = False
    initialize_ontology: bool = True
    build_fact_graphs: bool = True
    minimum_review_status: str = Field(default="candidate", pattern="^(candidate|approved)$")


class SemanticBackfillDocumentResult(BaseModel):
    document_id: UUID
    source_filename: str
    run_id: UUID | None = None
    semantic_pass_id: UUID | None = None
    action: str
    status: str
    assertion_count: int = 0
    evidence_count: int = 0
    fact_count: int = 0
    error_message: str | None = None


class SemanticBackfillRunResponse(BaseModel):
    schema_name: str = "semantic_backfill_run"
    schema_version: str = "1.0"
    dry_run: bool = False
    selected_document_count: int = 0
    processed_document_count: int = 0
    skipped_document_count: int = 0
    failed_document_count: int = 0
    semantic_pass_count: int = 0
    fact_graph_count: int = 0
    assertion_count: int = 0
    fact_count: int = 0
    documents: list[SemanticBackfillDocumentResult] = Field(default_factory=list)
    status_after: SemanticBackfillStatusResponse | None = None
    completed_at: datetime
