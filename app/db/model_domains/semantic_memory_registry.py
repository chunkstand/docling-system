from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class SemanticConcept(Base):
    __tablename__ = "semantic_concepts"
    __table_args__ = (
        UniqueConstraint(
            "concept_key",
            "registry_version",
            name="uq_semantic_concepts_key_registry_version",
        ),
        Index("ix_semantic_concepts_concept_key", "concept_key"),
        Index("ix_semantic_concepts_registry_version", "registry_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_key: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_label: Mapped[str] = mapped_column(Text, nullable=False)
    scope_note: Mapped[str | None] = mapped_column(Text)
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticCategory(Base):
    __tablename__ = "semantic_categories"
    __table_args__ = (
        UniqueConstraint(
            "category_key",
            "registry_version",
            name="uq_semantic_categories_key_registry_version",
        ),
        Index("ix_semantic_categories_category_key", "category_key"),
        Index("ix_semantic_categories_registry_version", "registry_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_key: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_label: Mapped[str] = mapped_column(Text, nullable=False)
    scope_note: Mapped[str | None] = mapped_column(Text)
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticTerm(Base):
    __tablename__ = "semantic_terms"
    __table_args__ = (
        CheckConstraint(
            "term_kind IN ('preferred_label', 'alias')",
            name="ck_semantic_terms_term_kind",
        ),
        UniqueConstraint(
            "registry_version",
            "normalized_text",
            name="uq_semantic_terms_registry_version_normalized_text",
        ),
        Index("ix_semantic_terms_registry_version", "registry_version"),
        Index("ix_semantic_terms_normalized_text", "normalized_text"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    term_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    term_kind: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticConceptTerm(Base):
    __tablename__ = "semantic_concept_terms"
    __table_args__ = (
        CheckConstraint(
            "mapping_kind IN ('preferred_label', 'alias')",
            name="ck_semantic_concept_terms_mapping_kind",
        ),
        CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_concept_terms_created_from",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_concept_terms_review_status",
        ),
        UniqueConstraint(
            "concept_id",
            "term_id",
            name="uq_semantic_concept_terms_concept_term",
        ),
        Index("ix_semantic_concept_terms_concept_id", "concept_id"),
        Index("ix_semantic_concept_terms_term_id", "term_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_terms.id", ondelete="CASCADE"),
        nullable=False,
    )
    mapping_kind: Mapped[str] = mapped_column(Text, nullable=False)
    created_from: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="registry",
        server_default=sql_text("'registry'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="approved",
        server_default=sql_text("'approved'"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticConceptCategoryBinding(Base):
    __tablename__ = "semantic_concept_category_bindings"
    __table_args__ = (
        CheckConstraint(
            "binding_type IN ('concept_category')",
            name="ck_semantic_concept_category_bindings_binding_type",
        ),
        CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_concept_category_bindings_created_from",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_concept_category_bindings_review_status",
        ),
        UniqueConstraint(
            "concept_id",
            "category_id",
            name="uq_semantic_concept_category_bindings_concept_category",
        ),
        Index("ix_semantic_concept_category_bindings_concept_id", "concept_id"),
        Index("ix_semantic_concept_category_bindings_category_id", "category_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    binding_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_from: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="registry",
        server_default=sql_text("'registry'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="approved",
        server_default=sql_text("'approved'"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
