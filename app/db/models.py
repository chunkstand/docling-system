from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RunStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    VALIDATING = "validating"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    active_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL", use_alter=True, name="fk_documents_active_run_id"),
    )
    latest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL", use_alter=True, name="fk_documents_latest_run_id"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentRun(Base):
    __tablename__ = "document_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'validating', 'retry_wait', 'completed', 'failed')",
            name="ck_document_runs_status",
        ),
        UniqueConstraint("document_id", "run_number", name="uq_document_runs_doc_run_number"),
        Index("ix_document_runs_status_next_attempt_at", "status", "next_attempt_at"),
        Index("ix_document_runs_locked_at", "locked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sql_text("0"))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    docling_json_path: Mapped[str | None] = mapped_column(Text)
    yaml_path: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int | None] = mapped_column(Integer)
    table_count: Mapped[int | None] = mapped_column(Integer)
    figure_count: Mapped[int | None] = mapped_column(Integer)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    embedding_dim: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str | None] = mapped_column(Text)
    validation_results_json: Mapped[dict] = mapped_column(
        "validation_results",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentRunEvaluation(Base):
    __tablename__ = "document_run_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'skipped')",
            name="ck_document_run_evaluations_status",
        ),
        UniqueConstraint("run_id", "corpus_name", "eval_version", name="uq_document_run_evaluations_run_corpus_version"),
        Index("ix_document_run_evaluations_run_id", "run_id"),
        Index("ix_document_run_evaluations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    corpus_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_name: Mapped[str | None] = mapped_column(Text)
    eval_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=sql_text("1"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending", server_default=sql_text("'pending'"))
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentRunEvaluationQuery(Base):
    __tablename__ = "document_run_evaluation_queries"
    __table_args__ = (
        Index("ix_document_run_evaluation_queries_evaluation_id", "evaluation_id"),
        Index("ix_document_run_evaluation_queries_query_text", "query_text"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluations.id", ondelete="CASCADE"), nullable=False
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    expected_result_type: Mapped[str | None] = mapped_column(Text)
    expected_top_n: Mapped[int | None] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=sql_text("false"))
    candidate_rank: Mapped[int | None] = mapped_column(Integer)
    baseline_rank: Mapped[int | None] = mapped_column(Integer)
    rank_delta: Mapped[int | None] = mapped_column(Integer)
    candidate_score: Mapped[float | None] = mapped_column(Float)
    baseline_score: Mapped[float | None] = mapped_column(Float)
    candidate_result_type: Mapped[str | None] = mapped_column(Text)
    baseline_result_type: Mapped[str | None] = mapped_column(Text)
    candidate_label: Mapped[str | None] = mapped_column(Text)
    baseline_label: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("run_id", "chunk_index", name="uq_document_chunks_run_chunk_index"),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_page_from", "page_from"),
        Index("ix_document_chunks_page_to", "page_to"),
        Index("ix_document_chunks_textsearch", "textsearch", postgresql_using="gin"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    textsearch: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(heading, '')), 'A') || "
            "to_tsvector('english', coalesce(text, ''))",
            persisted=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentTable(Base):
    __tablename__ = "document_tables"
    __table_args__ = (
        UniqueConstraint("run_id", "table_index", name="uq_document_tables_run_table_index"),
        Index("ix_document_tables_document_id", "document_id"),
        Index("ix_document_tables_page_from", "page_from"),
        Index("ix_document_tables_page_to", "page_to"),
        Index("ix_document_tables_textsearch", "textsearch", postgresql_using="gin"),
        Index(
            "ix_document_tables_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    logical_table_key: Mapped[str | None] = mapped_column(Text)
    table_version: Mapped[int | None] = mapped_column(Integer)
    supersedes_table_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lineage_group: Mapped[str | None] = mapped_column(Text)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    row_count: Mapped[int | None] = mapped_column(Integer)
    col_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="persisted", server_default=sql_text("'persisted'"))
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    preview_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    json_path: Mapped[str | None] = mapped_column(Text)
    yaml_path: Mapped[str | None] = mapped_column(Text)
    textsearch: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(heading, '')), 'B') || "
            "to_tsvector('english', coalesce(search_text, ''))",
            persisted=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentTableSegment(Base):
    __tablename__ = "document_table_segments"
    __table_args__ = (
        UniqueConstraint("table_id", "segment_index", name="uq_document_table_segments_table_segment_index"),
        Index("ix_document_table_segments_run_id", "run_id"),
        Index("ix_document_table_segments_page_from", "page_from"),
        Index("ix_document_table_segments_page_to", "page_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_tables.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_table_ref: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    segment_order: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentFigure(Base):
    __tablename__ = "document_figures"
    __table_args__ = (
        UniqueConstraint("run_id", "figure_index", name="uq_document_figures_run_figure_index"),
        Index("ix_document_figures_document_id", "document_id"),
        Index("ix_document_figures_run_id", "run_id"),
        Index("ix_document_figures_page_from", "page_from"),
        Index("ix_document_figures_page_to", "page_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    figure_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_figure_ref: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="persisted", server_default=sql_text("'persisted'"))
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    json_path: Mapped[str | None] = mapped_column(Text)
    yaml_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
