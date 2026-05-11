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


class RetrievalJudgmentSet(Base):
    __tablename__ = "retrieval_judgment_sets"
    __table_args__ = (
        CheckConstraint(
            "set_kind IN ("
            "'feedback', "
            "'replay', "
            "'mixed', "
            "'training', "
            "'claim_support_replay_alert_corpus', "
            "'technical_report_claim_feedback'"
            ")",
            name="ck_retrieval_judgment_sets_set_kind",
        ),
        UniqueConstraint("set_name", name="uq_retrieval_judgment_sets_set_name"),
        Index("ix_retrieval_judgment_sets_created_at", "created_at"),
        Index("ix_retrieval_judgment_sets_set_kind_created", "set_kind", "created_at"),
        Index("ix_retrieval_judgment_sets_payload_sha", "payload_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    set_name: Mapped[str] = mapped_column(Text, nullable=False)
    set_kind: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="mixed",
        server_default=sql_text("'mixed'"),
    )
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    criteria_json: Mapped[dict] = mapped_column(
        "criteria",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    judgment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalJudgment(Base):
    __tablename__ = "retrieval_judgments"
    __table_args__ = (
        CheckConstraint(
            "judgment_kind IN ('positive', 'negative', 'missing')",
            name="ck_retrieval_judgments_kind",
        ),
        CheckConstraint(
            "source_type IN ("
            "'feedback', "
            "'replay', "
            "'claim_support_replay_alert_corpus', "
            "'technical_report_claim_feedback'"
            ")",
            name="ck_retrieval_judgments_source_type",
        ),
        CheckConstraint(
            "result_type IS NULL OR result_type IN ('chunk', 'table')",
            name="ck_retrieval_judgments_result_type",
        ),
        UniqueConstraint(
            "deduplication_key",
            name="uq_retrieval_judgments_dedup_key",
        ),
        Index("ix_retrieval_judgments_set_kind", "judgment_set_id", "judgment_kind"),
        Index("ix_retrieval_judgments_source", "source_type", "source_ref_id"),
        Index("ix_retrieval_judgments_search_request", "search_request_id"),
        Index("ix_retrieval_judgments_source_request", "source_search_request_id"),
        Index("ix_retrieval_judgments_search_result", "search_request_result_id"),
        Index("ix_retrieval_judgments_feedback", "search_feedback_id"),
        Index("ix_retrieval_judgments_replay_query", "search_replay_query_id"),
        Index("ix_retrieval_judgments_result", "result_type", "result_id"),
        Index("ix_retrieval_judgments_source_payload_sha", "source_payload_sha256"),
        Index("ix_retrieval_judgments_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    judgment_kind: Mapped[str] = mapped_column(Text, nullable=False)
    judgment_label: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    search_feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_feedback.id", ondelete="SET NULL"),
    )
    search_replay_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_queries.id", ondelete="SET NULL"),
    )
    search_replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="SET NULL"),
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL"),
    )
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
    )
    result_rank: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str | None] = mapped_column(Text)
    result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    score: Mapped[float | None] = mapped_column(Float)
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
    harness_name: Mapped[str | None] = mapped_column(Text)
    reranker_name: Mapped[str | None] = mapped_column(Text)
    reranker_version: Mapped[str | None] = mapped_column(Text)
    retrieval_profile_name: Mapped[str | None] = mapped_column(Text)
    rerank_features_json: Mapped[dict] = mapped_column(
        "rerank_features",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_payload_sha256: Mapped[str | None] = mapped_column(Text)
    deduplication_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalHardNegative(Base):
    __tablename__ = "retrieval_hard_negatives"
    __table_args__ = (
        CheckConstraint(
            "hard_negative_kind IN ("
            "'explicit_irrelevant', "
            "'missing_expected', "
            "'failed_replay_top_result', "
            "'wrong_result_type', "
            "'no_answer_returned'"
            ")",
            name="ck_retrieval_hard_negatives_kind",
        ),
        CheckConstraint(
            "source_type IN ("
            "'feedback', "
            "'replay', "
            "'claim_support_replay_alert_corpus', "
            "'technical_report_claim_feedback'"
            ")",
            name="ck_retrieval_hard_negatives_source_type",
        ),
        CheckConstraint(
            "result_type IS NULL OR result_type IN ('chunk', 'table')",
            name="ck_retrieval_hard_negatives_result_type",
        ),
        UniqueConstraint(
            "deduplication_key",
            name="uq_retrieval_hard_negatives_dedup_key",
        ),
        Index("ix_retrieval_hard_negatives_set_kind", "judgment_set_id", "hard_negative_kind"),
        Index("ix_retrieval_hard_negatives_judgment", "judgment_id"),
        Index("ix_retrieval_hard_negatives_positive_judgment", "positive_judgment_id"),
        Index("ix_retrieval_hard_negatives_source", "source_type", "source_ref_id"),
        Index("ix_retrieval_hard_negatives_feedback", "search_feedback_id"),
        Index("ix_retrieval_hard_negatives_replay_query", "search_replay_query_id"),
        Index("ix_retrieval_hard_negatives_source_request", "source_search_request_id"),
        Index("ix_retrieval_hard_negatives_request", "search_request_id"),
        Index("ix_retrieval_hard_negatives_search_result", "search_request_result_id"),
        Index("ix_retrieval_hard_negatives_result", "result_type", "result_id"),
        Index("ix_retrieval_hard_negatives_source_payload_sha", "source_payload_sha256"),
        Index("ix_retrieval_hard_negatives_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    judgment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgments.id", ondelete="CASCADE"),
        nullable=False,
    )
    positive_judgment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgments.id", ondelete="SET NULL"),
    )
    hard_negative_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    search_feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_feedback.id", ondelete="SET NULL"),
    )
    search_replay_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_queries.id", ondelete="SET NULL"),
    )
    search_replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="SET NULL"),
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL"),
    )
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
    )
    result_rank: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str | None] = mapped_column(Text)
    result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    score: Mapped[float | None] = mapped_column(Float)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    rerank_features_json: Mapped[dict] = mapped_column(
        "rerank_features",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    expected_result_type: Mapped[str | None] = mapped_column(Text)
    expected_top_n: Mapped[int | None] = mapped_column(Integer)
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_payload_sha256: Mapped[str | None] = mapped_column(Text)
    deduplication_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
