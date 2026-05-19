from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.model_domains.retrieval_interactions import SearchRequestRecord, SearchRequestResult


class TechnicalReportReleaseReadinessDbGate(Base):
    __tablename__ = "technical_report_release_readiness_db_gates"
    __table_args__ = (
        CheckConstraint(
            "check_key = 'release_readiness_assessment_db_integrity'",
            name="ck_tr_readiness_db_gates_check_key",
        ),
        CheckConstraint(
            "source_search_request_count >= 0 "
            "AND verified_request_count >= 0 "
            "AND failure_count >= 0",
            name="ck_tr_readiness_db_gates_nonnegative_counts",
        ),
        CheckConstraint(
            "char_length(gate_payload_sha256) = 64",
            name="ck_tr_readiness_db_gates_payload_sha_length",
        ),
        CheckConstraint(
            "source_search_request_count = jsonb_array_length(source_search_request_ids) "
            "AND verified_request_count = jsonb_array_length(verified_request_ids)",
            name="ck_tr_readiness_db_gates_request_count_consistency",
        ),
        CheckConstraint(
            "NOT complete OR ("
            "passed "
            "AND coverage_complete "
            "AND failure_count = 0 "
            "AND missing_expected_request_ids = '[]'::jsonb "
            "AND unexpected_verified_request_ids = '[]'::jsonb"
            ")",
            name="ck_tr_readiness_db_gates_complete_consistency",
        ),
        UniqueConstraint(
            "technical_report_verification_task_id",
            name="uq_tr_readiness_db_gates_verification_task",
        ),
        Index(
            "ix_tr_readiness_db_gates_verification_task",
            "technical_report_verification_task_id",
        ),
        Index(
            "ix_tr_readiness_db_gates_source_verification",
            "source_verification_id",
        ),
        Index("ix_tr_readiness_db_gates_harness_task", "harness_task_id"),
        Index("ix_tr_readiness_db_gates_manifest", "evidence_manifest_id"),
        Index("ix_tr_readiness_db_gates_prov_artifact", "prov_export_artifact_id"),
        Index("ix_tr_readiness_db_gates_governance", "semantic_governance_event_id"),
        Index("ix_tr_readiness_db_gates_payload_sha", "gate_payload_sha256"),
        Index("ix_tr_readiness_db_gates_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    technical_report_verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_verifications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_verification_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    harness_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="SET NULL"),
    )
    prov_export_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    check_key: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    required: Mapped[bool | None] = mapped_column(Boolean)
    coverage_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_search_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    verified_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    source_search_request_ids_json: Mapped[list] = mapped_column(
        "source_search_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    verified_request_ids_json: Mapped[list] = mapped_column(
        "verified_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    missing_expected_request_ids_json: Mapped[list] = mapped_column(
        "missing_expected_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    unexpected_verified_request_ids_json: Mapped[list] = mapped_column(
        "unexpected_verified_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    gate_payload_json: Mapped[dict] = mapped_column(
        "gate_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    gate_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TechnicalReportClaimRetrievalFeedback(Base):
    __tablename__ = "technical_report_claim_retrieval_feedback"
    __table_args__ = (
        CheckConstraint(
            "support_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_tr_claim_feedback_support_verdict",
        ),
        CheckConstraint(
            "feedback_status IN ('supported', 'weak', 'missing', 'contradicted', 'rejected')",
            name="ck_tr_claim_feedback_status",
        ),
        CheckConstraint(
            "learning_label IN ('positive', 'negative', 'missing')",
            name="ck_tr_claim_feedback_learning_label",
        ),
        CheckConstraint(
            "hard_negative_kind IS NULL OR hard_negative_kind IN ("
            "'explicit_irrelevant', "
            "'missing_expected', "
            "'failed_replay_top_result', "
            "'wrong_result_type', "
            "'no_answer_returned'"
            ")",
            name="ck_tr_claim_feedback_hard_negative_kind",
        ),
        CheckConstraint(
            "char_length(feedback_payload_sha256) = 64",
            name="ck_tr_claim_feedback_payload_sha_length",
        ),
        CheckConstraint(
            "char_length(source_payload_sha256) = 64",
            name="ck_tr_claim_feedback_source_sha_length",
        ),
        UniqueConstraint(
            "technical_report_verification_task_id",
            "claim_id",
            name="uq_tr_claim_feedback_verification_claim",
        ),
        Index(
            "ix_tr_claim_feedback_verification_task",
            "technical_report_verification_task_id",
        ),
        Index("ix_tr_claim_feedback_claim", "claim_id"),
        Index("ix_tr_claim_feedback_derivation", "claim_evidence_derivation_id"),
        Index("ix_tr_claim_feedback_manifest", "evidence_manifest_id"),
        Index("ix_tr_claim_feedback_prov_artifact", "prov_export_artifact_id"),
        Index("ix_tr_claim_feedback_release_gate", "release_readiness_db_gate_id"),
        Index("ix_tr_claim_feedback_governance", "semantic_governance_event_id"),
        Index("ix_tr_claim_feedback_source_request", "source_search_request_id"),
        Index("ix_tr_claim_feedback_search_result", "search_request_result_id"),
        Index("ix_tr_claim_feedback_status_label", "feedback_status", "learning_label"),
        Index("ix_tr_claim_feedback_payload_sha", "feedback_payload_sha256"),
        Index("ix_tr_claim_feedback_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    technical_report_verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_evidence_derivation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_evidence_derivations.id", ondelete="SET NULL"),
    )
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="SET NULL"),
    )
    prov_export_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    release_readiness_db_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technical_report_release_readiness_db_gates.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    claim_id: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str | None] = mapped_column(Text)
    support_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    support_score: Mapped[float | None] = mapped_column(Float)
    feedback_status: Mapped[str] = mapped_column(Text, nullable=False)
    learning_label: Mapped[str] = mapped_column(Text, nullable=False)
    hard_negative_kind: Mapped[str | None] = mapped_column(Text)
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
    )
    source_search_request_ids_json: Mapped[list] = mapped_column(
        "source_search_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_search_request_result_ids_json: Mapped[list] = mapped_column(
        "source_search_request_result_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    search_request_result_span_ids_json: Mapped[list] = mapped_column(
        "search_request_result_span_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    retrieval_evidence_span_ids_json: Mapped[list] = mapped_column(
        "retrieval_evidence_span_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    semantic_ontology_snapshot_ids_json: Mapped[list] = mapped_column(
        "semantic_ontology_snapshot_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    semantic_graph_snapshot_ids_json: Mapped[list] = mapped_column(
        "semantic_graph_snapshot_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    retrieval_reranker_artifact_ids_json: Mapped[list] = mapped_column(
        "retrieval_reranker_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    search_harness_release_ids_json: Mapped[list] = mapped_column(
        "search_harness_release_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    release_audit_bundle_ids_json: Mapped[list] = mapped_column(
        "release_audit_bundle_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    release_validation_receipt_ids_json: Mapped[list] = mapped_column(
        "release_validation_receipt_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    retrieval_context_json: Mapped[dict] = mapped_column(
        "retrieval_context",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    feedback_payload_json: Mapped[dict] = mapped_column(
        "feedback_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    feedback_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload_json: Mapped[dict] = mapped_column(
        "source_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_search_request: Mapped[SearchRequestRecord | None] = relationship(
        "SearchRequestRecord",
        foreign_keys=[source_search_request_id],
    )
    search_request_result: Mapped[SearchRequestResult | None] = relationship(
        "SearchRequestResult",
        foreign_keys=[search_request_result_id],
    )
