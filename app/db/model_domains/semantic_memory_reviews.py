from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class DocumentSemanticConceptReview(Base):
    __tablename__ = "document_semantic_concept_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_document_semantic_concept_reviews_review_status",
        ),
        Index("ix_document_semantic_concept_reviews_document_id", "document_id"),
        Index("ix_document_semantic_concept_reviews_concept_id", "concept_id"),
        Index(
            "ix_doc_sem_concept_reviews_doc_concept_created_at",
            "document_id",
            "concept_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentSemanticCategoryReview(Base):
    __tablename__ = "document_semantic_category_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_document_semantic_category_reviews_review_status",
        ),
        Index("ix_document_semantic_category_reviews_document_id", "document_id"),
        Index("ix_document_semantic_category_reviews_concept_id", "concept_id"),
        Index("ix_document_semantic_category_reviews_category_id", "category_id"),
        Index(
            "ix_doc_sem_category_reviews_doc_binding_created_at",
            "document_id",
            "concept_id",
            "category_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentRunSemanticPass(Base):
    __tablename__ = "document_run_semantic_passes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_document_run_semantic_passes_status",
        ),
        CheckConstraint(
            "evaluation_status IN ('pending', 'completed', 'failed', 'skipped')",
            name="ck_document_run_semantic_passes_evaluation_status",
        ),
        UniqueConstraint(
            "run_id",
            "registry_version",
            "extractor_version",
            "artifact_schema_version",
            name="uq_document_run_semantic_passes_run_version_tuple",
        ),
        Index("ix_document_run_semantic_passes_document_id", "document_id"),
        Index("ix_document_run_semantic_passes_run_id", "run_id"),
        Index("ix_document_run_semantic_passes_baseline_run_id", "baseline_run_id"),
        Index("ix_document_run_semantic_passes_ontology_snapshot_id", "ontology_snapshot_id"),
        Index("ix_document_run_semantic_passes_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    baseline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    baseline_semantic_pass_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_semantic_passes.id", ondelete="SET NULL"),
    )
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    upper_ontology_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default=sql_text("'pending'")
    )
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    registry_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    extractor_version: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=sql_text("'pending'"),
    )
    evaluation_fixture_name: Mapped[str | None] = mapped_column(Text)
    evaluation_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=sql_text("1"),
    )
    evaluation_summary_json: Mapped[dict] = mapped_column(
        "evaluation_summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    continuity_summary_json: Mapped[dict] = mapped_column(
        "continuity_summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    artifact_json_path: Mapped[str | None] = mapped_column(Text)
    artifact_yaml_path: Mapped[str | None] = mapped_column(Text)
    artifact_json_sha256: Mapped[str | None] = mapped_column(Text)
    artifact_yaml_sha256: Mapped[str | None] = mapped_column(Text)
    assertion_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
