from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
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
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SearchRequestRecord(Base):
    __tablename__ = "search_requests"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('keyword', 'semantic', 'hybrid')",
            name="ck_search_requests_mode",
        ),
        Index("ix_search_requests_created_at", "created_at"),
        Index("ix_search_requests_origin_created_at", "origin", "created_at"),
        Index("ix_search_requests_evaluation_id", "evaluation_id"),
        Index("ix_search_requests_parent_request_id", "parent_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluations.id", ondelete="SET NULL"),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    tabular_query: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    harness_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    reranker_name: Mapped[str] = mapped_column(Text, nullable=False)
    reranker_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="v1",
        server_default=sql_text("'v1'"),
    )
    retrieval_profile_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    harness_config_json: Mapped[dict] = mapped_column(
        "harness_config",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    embedding_status: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_error: Mapped[str | None] = mapped_column(Text)
    candidate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchRequestResult(Base):
    __tablename__ = "search_request_results"
    __table_args__ = (
        CheckConstraint(
            "result_type IN ('chunk', 'table')",
            name="ck_search_request_results_result_type",
        ),
        UniqueConstraint(
            "search_request_id",
            "rank",
            name="uq_search_request_results_request_rank",
        ),
        Index("ix_search_request_results_search_request_id", "search_request_id"),
        Index("ix_search_request_results_result_type", "result_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    base_rank: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    table_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    keyword_score: Mapped[float | None] = mapped_column(Float)
    semantic_score: Mapped[float | None] = mapped_column(Float)
    hybrid_score: Mapped[float | None] = mapped_column(Float)
    rerank_features_json: Mapped[dict] = mapped_column(
        "rerank_features",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    preview_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalEvidenceSpan(Base):
    __tablename__ = "retrieval_evidence_spans"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_retrieval_evidence_spans_source_type",
        ),
        CheckConstraint(
            "("
            "source_type = 'chunk' AND chunk_id IS NOT NULL AND table_id IS NULL"
            ") OR ("
            "source_type = 'table' AND table_id IS NOT NULL AND chunk_id IS NULL"
            ")",
            name="ck_retrieval_evidence_spans_source_ref",
        ),
        UniqueConstraint(
            "run_id",
            "source_type",
            "source_id",
            "span_index",
            name="uq_retrieval_evidence_spans_run_source_span",
        ),
        Index("ix_retrieval_evidence_spans_document_id", "document_id"),
        Index("ix_retrieval_evidence_spans_run_id", "run_id"),
        Index("ix_retrieval_evidence_spans_source", "source_type", "source_id"),
        Index("ix_retrieval_evidence_spans_chunk_id", "chunk_id"),
        Index("ix_retrieval_evidence_spans_table_id", "table_id"),
        Index("ix_retrieval_evidence_spans_page_from", "page_from"),
        Index("ix_retrieval_evidence_spans_page_to", "page_to"),
        Index("ix_retrieval_evidence_spans_content_sha256", "content_sha256"),
        Index(
            "ix_retrieval_evidence_spans_textsearch",
            "textsearch",
            postgresql_using="gin",
        ),
        Index(
            "ix_retrieval_evidence_spans_embedding_hnsw",
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
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE")
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_tables.id", ondelete="CASCADE")
    )
    span_index: Mapped[int] = mapped_column(Integer, nullable=False)
    span_text: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_sha256: Mapped[str] = mapped_column(Text, nullable=False)
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
            "to_tsvector('english', coalesce(span_text, ''))",
            persisted=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalEvidenceSpanMultiVector(Base):
    __tablename__ = "retrieval_evidence_span_multivectors"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_retrieval_span_multivectors_source_type",
        ),
        CheckConstraint(
            "token_start >= 0 AND token_end > token_start",
            name="ck_retrieval_span_multivectors_token_range",
        ),
        CheckConstraint(
            "embedding_dim = 1536",
            name="ck_retrieval_span_multivectors_embedding_dim",
        ),
        UniqueConstraint(
            "retrieval_evidence_span_id",
            "vector_index",
            name="uq_retrieval_span_multivectors_span_vector",
        ),
        Index(
            "ix_retrieval_span_multivectors_span_id",
            "retrieval_evidence_span_id",
        ),
        Index("ix_retrieval_span_multivectors_document_id", "document_id"),
        Index("ix_retrieval_span_multivectors_run_id", "run_id"),
        Index(
            "ix_retrieval_span_multivectors_source",
            "source_type",
            "source_id",
        ),
        Index(
            "ix_retrieval_span_multivectors_model",
            "embedding_model",
        ),
        Index(
            "ix_retrieval_span_multivectors_content_sha256",
            "content_sha256",
        ),
        Index(
            "ix_retrieval_span_multivectors_embedding_sha256",
            "embedding_sha256",
        ),
        Index(
            "ix_retrieval_span_multivectors_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_evidence_span_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_evidence_spans.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vector_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_start: Mapped[int] = mapped_column(Integer, nullable=False)
    token_end: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchRequestResultSpan(Base):
    __tablename__ = "search_request_result_spans"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_search_request_result_spans_source_type",
        ),
        UniqueConstraint(
            "search_request_result_id",
            "span_rank",
            name="uq_search_request_result_spans_result_rank",
        ),
        Index("ix_search_request_result_spans_request_id", "search_request_id"),
        Index("ix_search_request_result_spans_result_id", "search_request_result_id"),
        Index("ix_search_request_result_spans_span_id", "retrieval_evidence_span_id"),
        Index("ix_search_request_result_spans_source", "source_type", "source_id"),
        Index("ix_search_request_result_spans_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_request_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    retrieval_evidence_span_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_evidence_spans.id", ondelete="SET NULL"),
    )
    span_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score_kind: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    span_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    text_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_sha256: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchFeedback(Base):
    __tablename__ = "search_feedback"
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('relevant', 'irrelevant', 'missing_table', "
            "'missing_chunk', 'no_answer')",
            name="ck_search_feedback_type",
        ),
        Index("ix_search_feedback_search_request_id", "search_request_id"),
        Index("ix_search_feedback_search_request_result_id", "search_request_result_id"),
        Index("ix_search_feedback_feedback_type", "feedback_type"),
        Index("ix_search_feedback_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
    )
    result_rank: Mapped[int | None] = mapped_column(Integer)
    feedback_type: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatAnswerRecord(Base):
    __tablename__ = "chat_answer_records"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('keyword', 'semantic', 'hybrid')",
            name="ck_chat_answer_records_mode",
        ),
        Index("ix_chat_answer_records_search_request_id", "search_request_id"),
        Index("ix_chat_answer_records_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    used_fallback: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    warning: Mapped[str | None] = mapped_column(Text)
    citations_json: Mapped[list] = mapped_column(
        "citations",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    harness_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    reranker_name: Mapped[str] = mapped_column(Text, nullable=False)
    reranker_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="v1",
        server_default=sql_text("'v1'"),
    )
    retrieval_profile_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatAnswerFeedback(Base):
    __tablename__ = "chat_answer_feedback"
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('helpful', 'unhelpful', 'unsupported', 'incomplete')",
            name="ck_chat_answer_feedback_type",
        ),
        Index("ix_chat_answer_feedback_answer_id", "chat_answer_id"),
        Index("ix_chat_answer_feedback_feedback_type", "feedback_type"),
        Index("ix_chat_answer_feedback_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_answer_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
