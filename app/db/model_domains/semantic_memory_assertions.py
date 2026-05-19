from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SemanticAssertion(Base):
    __tablename__ = "semantic_assertions"
    __table_args__ = (
        CheckConstraint(
            "assertion_kind IN ('concept_mention')",
            name="ck_semantic_assertions_assertion_kind",
        ),
        CheckConstraint(
            "epistemic_status IN ('observed', 'inferred', 'curated')",
            name="ck_semantic_assertions_epistemic_status",
        ),
        CheckConstraint(
            "context_scope IN ('document_run', 'document', 'registry')",
            name="ck_semantic_assertions_context_scope",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_assertions_review_status",
        ),
        UniqueConstraint(
            "semantic_pass_id",
            "concept_id",
            "assertion_kind",
            name="uq_semantic_assertions_pass_concept_kind",
        ),
        Index("ix_semantic_assertions_semantic_pass_id", "semantic_pass_id"),
        Index("ix_semantic_assertions_concept_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    semantic_pass_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_semantic_passes.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    assertion_kind: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="observed",
        server_default=sql_text("'observed'"),
    )
    context_scope: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="document_run",
        server_default=sql_text("'document_run'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="candidate",
        server_default=sql_text("'candidate'"),
    )
    matched_terms_json: Mapped[list] = mapped_column(
        "matched_terms",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticAssertionCategoryBinding(Base):
    __tablename__ = "semantic_assertion_category_bindings"
    __table_args__ = (
        CheckConstraint(
            "binding_type IN ('assertion_category')",
            name="ck_semantic_assertion_category_bindings_binding_type",
        ),
        CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_assertion_category_bindings_created_from",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_assertion_category_bindings_review_status",
        ),
        UniqueConstraint(
            "assertion_id",
            "category_id",
            name="uq_semantic_assertion_category_bindings_assertion_category",
        ),
        Index("ix_semantic_assertion_category_bindings_assertion_id", "assertion_id"),
        Index("ix_semantic_assertion_category_bindings_category_id", "category_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assertion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_category_binding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concept_category_bindings.id", ondelete="SET NULL"),
    )
    binding_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_from: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="derived",
        server_default=sql_text("'derived'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="candidate",
        server_default=sql_text("'candidate'"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticAssertionEvidence(Base):
    __tablename__ = "semantic_assertion_evidence"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table', 'figure')",
            name="ck_semantic_assertion_evidence_source_type",
        ),
        UniqueConstraint(
            "assertion_id",
            "source_type",
            "source_locator",
            name="uq_semantic_assertion_evidence_assertion_source",
        ),
        Index("ix_semantic_assertion_evidence_assertion_id", "assertion_id"),
        Index("ix_semantic_assertion_evidence_run_id", "run_id"),
        Index("ix_semantic_assertion_evidence_source_type", "source_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assertion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_tables.id", ondelete="SET NULL"),
    )
    figure_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_figures.id", ondelete="SET NULL"),
    )
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    matched_terms_json: Mapped[list] = mapped_column(
        "matched_terms",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    excerpt: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str | None] = mapped_column(Text)
    source_artifact_path: Mapped[str | None] = mapped_column(Text)
    source_artifact_sha256: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
