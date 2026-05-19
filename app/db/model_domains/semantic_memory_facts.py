from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SemanticEntity(Base):
    __tablename__ = "semantic_entities"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('document', 'concept', 'literal')",
            name="ck_semantic_entities_entity_type",
        ),
        UniqueConstraint("entity_key", name="uq_semantic_entities_entity_key"),
        Index("ix_semantic_entities_document_id", "document_id"),
        Index("ix_semantic_entities_concept_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_key: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_label: Mapped[str] = mapped_column(Text, nullable=False)
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="SET NULL"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticFact(Base):
    __tablename__ = "semantic_facts"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_facts_review_status",
        ),
        Index("ix_semantic_facts_document_id", "document_id"),
        Index("ix_semantic_facts_run_id", "run_id"),
        Index("ix_semantic_facts_semantic_pass_id", "semantic_pass_id"),
        Index("ix_semantic_facts_relation_key", "relation_key"),
        Index("ix_semantic_facts_subject_entity_id", "subject_entity_id"),
        Index("ix_semantic_facts_object_entity_id", "object_entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    semantic_pass_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_semantic_passes.id", ondelete="CASCADE"),
        nullable=False,
    )
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    subject_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_key: Mapped[str] = mapped_column(Text, nullable=False)
    relation_label: Mapped[str] = mapped_column(Text, nullable=False)
    object_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_entities.id", ondelete="SET NULL"),
    )
    object_value_text: Mapped[str | None] = mapped_column(Text)
    source_assertion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="SET NULL"),
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticFactEvidence(Base):
    __tablename__ = "semantic_fact_evidence"
    __table_args__ = (
        Index("ix_semantic_fact_evidence_fact_id", "fact_id"),
        Index("ix_semantic_fact_evidence_assertion_id", "assertion_id"),
        Index("ix_semantic_fact_evidence_evidence_id", "assertion_evidence_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_facts.id", ondelete="CASCADE"),
        nullable=False,
    )
    assertion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="SET NULL"),
    )
    assertion_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertion_evidence.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
