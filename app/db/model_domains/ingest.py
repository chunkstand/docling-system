from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
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
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestBatch(Base):
    __tablename__ = "ingest_batches"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('local_directory', 'zip_upload')",
            name="ck_ingest_batches_source_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_errors', 'failed')",
            name="ck_ingest_batches_status",
        ),
        Index("ix_ingest_batches_created_at", "created_at"),
        Index("ix_ingest_batches_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    root_path: Mapped[str | None] = mapped_column(Text)
    recursive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    file_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    queued_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    recovery_queued_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    duplicate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestBatchItem(Base):
    __tablename__ = "ingest_batch_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'queued_recovery', 'duplicate', 'failed')",
            name="ck_ingest_batch_items_status",
        ),
        UniqueConstraint(
            "batch_id",
            "relative_path",
            name="uq_ingest_batch_items_batch_relative_path",
        ),
        Index("ix_ingest_batch_items_batch_id", "batch_id"),
        Index("ix_ingest_batch_items_document_id", "document_id"),
        Index("ix_ingest_batch_items_run_id", "run_id"),
        Index("ix_ingest_batch_items_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingest_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    duplicate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    recovery_run: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


DOCUMENT_METADATA_NORMALIZE_SQL = """
trim(
    regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        coalesce(title, '') || ' ' ||
                        regexp_replace(coalesce(source_filename, ''), '\\.[^.]+$', '', 'g'),
                        '([A-Z]+)([A-Z][a-z])', '\\1 \\2', 'g'
                    ),
                    '([a-z0-9])([A-Z])', '\\1 \\2', 'g'
                ),
                '([A-Za-z])([0-9])', '\\1 \\2', 'g'
            ),
            '([0-9])([A-Za-z])', '\\1 \\2', 'g'
        ),
        '[^A-Za-z0-9]+', ' ', 'g'
    )
)
""".strip()
DOCUMENT_METADATA_TEXTSEARCH_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    f"setweight(to_tsvector('simple', {DOCUMENT_METADATA_NORMALIZE_SQL}), 'A')"
)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_updated_at", "updated_at"),
        Index("ix_documents_metadata_textsearch", "metadata_textsearch", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    metadata_textsearch: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(DOCUMENT_METADATA_TEXTSEARCH_SQL, persisted=True),
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    active_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_documents_active_run_id",
        ),
    )
    latest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_documents_latest_run_id",
        ),
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
        Index("ix_document_runs_status_completed_at", "status", "completed_at"),
        Index("ix_document_runs_locked_at", "locked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    failure_stage: Mapped[str | None] = mapped_column(Text)
    failure_artifact_path: Mapped[str | None] = mapped_column(Text)
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
