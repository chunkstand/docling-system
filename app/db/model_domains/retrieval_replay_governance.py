from __future__ import annotations

import uuid
from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SearchReplayRun(Base):
    __tablename__ = "search_replay_runs"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ("
            "'evaluation_queries', "
            "'live_search_gaps', "
            "'feedback', "
            "'cross_document_prose_regressions', "
            "'technical_report_claim_feedback'"
            ")",
            name="ck_search_replay_runs_source_type",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_search_replay_runs_status",
        ),
        Index("ix_search_replay_runs_created_at", "created_at"),
        Index("ix_search_replay_runs_source_type_created_at", "source_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    harness_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    reranker_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="linear_feature_reranker",
        server_default=sql_text("'linear_feature_reranker'"),
    )
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
    query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    passed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    zero_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    top_result_changes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    max_rank_shift: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
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


class SearchReplayQuery(Base):
    __tablename__ = "search_replay_queries"
    __table_args__ = (
        Index("ix_search_replay_queries_replay_run_id", "replay_run_id"),
        Index("ix_search_replay_queries_source_search_request_id", "source_search_request_id"),
        Index("ix_search_replay_queries_replay_search_request_id", "replay_search_request_id"),
        Index("ix_search_replay_queries_feedback_id", "feedback_id"),
        Index("ix_search_replay_queries_evaluation_query_id", "evaluation_query_id"),
        Index("ix_search_replay_queries_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    replay_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    replay_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_feedback.id", ondelete="SET NULL"),
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL"),
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
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    overlap_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    added_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    removed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    top_result_changed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    max_rank_shift: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchHarnessEvaluation(Base):
    __tablename__ = "search_harness_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_search_harness_evaluations_status",
        ),
        Index("ix_search_harness_evaluations_created_at", "created_at"),
        Index(
            "ix_search_harness_evaluations_candidate_created_at",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_search_harness_evaluations_baseline_candidate",
            "baseline_harness_name",
            "candidate_harness_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    harness_overrides_json: Mapped[dict] = mapped_column(
        "harness_overrides",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    total_shared_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    total_improved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    total_regressed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    total_unchanged_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
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


class SearchHarnessEvaluationSource(Base):
    __tablename__ = "search_harness_evaluation_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ("
            "'evaluation_queries', "
            "'live_search_gaps', "
            "'feedback', "
            "'cross_document_prose_regressions', "
            "'technical_report_claim_feedback'"
            ")",
            name="ck_search_harness_evaluation_sources_source_type",
        ),
        UniqueConstraint(
            "search_harness_evaluation_id",
            "source_type",
            name="uq_search_harness_evaluation_sources_eval_source",
        ),
        Index(
            "ix_search_harness_evaluation_sources_eval_id",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_search_harness_evaluation_sources_baseline_replay",
            "baseline_replay_run_id",
        ),
        Index(
            "ix_search_harness_evaluation_sources_candidate_replay",
            "candidate_replay_run_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_replay_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_replay_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    baseline_status: Mapped[str | None] = mapped_column(Text)
    candidate_status: Mapped[str | None] = mapped_column(Text)
    baseline_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_passed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_passed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_zero_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_zero_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_top_result_changes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_top_result_changes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_mrr: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=sql_text("0")
    )
    candidate_mrr: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=sql_text("0")
    )
    baseline_foreign_top_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_foreign_top_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    acceptance_checks_json: Mapped[dict] = mapped_column(
        "acceptance_checks",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    shared_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    improved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    regressed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    unchanged_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchHarnessRelease(Base):
    __tablename__ = "search_harness_releases"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('passed', 'failed', 'error')",
            name="ck_search_harness_releases_outcome",
        ),
        Index("ix_search_harness_releases_created_at", "created_at"),
        Index(
            "ix_search_harness_releases_candidate_created_at",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_search_harness_releases_evaluation_id",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_search_harness_releases_outcome_created_at",
            "outcome",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_snapshot_json: Mapped[dict] = mapped_column(
        "evaluation_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    release_package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchHarnessReleaseReadinessAssessment(Base):
    __tablename__ = "search_harness_release_readiness_assessments"
    __table_args__ = (
        CheckConstraint(
            "readiness_status IN ('ready', 'blocked')",
            name="ck_search_harness_release_readiness_assessments_status",
        ),
        Index(
            "ix_shr_readiness_assessments_release_created",
            "search_harness_release_id",
            "created_at",
        ),
        Index(
            "ix_shr_readiness_assessments_status_created",
            "readiness_status",
            "created_at",
        ),
        Index(
            "ix_shr_readiness_assessments_bundle_created",
            "release_audit_bundle_id",
            "created_at",
        ),
        Index(
            "ix_shr_readiness_assessments_receipt_created",
            "release_validation_receipt_id",
            "created_at",
        ),
        Index(
            "ix_shr_readiness_assessments_governance",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_shr_readiness_assessments_payload_sha",
            "assessment_payload_sha256",
        ),
        Index(
            "ix_shr_readiness_assessments_readiness_sha",
            "readiness_payload_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_harness_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    release_audit_bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_bundle_exports.id", ondelete="RESTRICT"),
    )
    release_validation_receipt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_bundle_validation_receipts.id", ondelete="RESTRICT"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    readiness_profile: Mapped[str] = mapped_column(Text, nullable=False)
    readiness_status: Mapped[str] = mapped_column(Text, nullable=False)
    ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[list] = mapped_column(
        "blockers",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    blocker_details_json: Mapped[list] = mapped_column(
        "blocker_details",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    checks_json: Mapped[dict] = mapped_column(
        "checks",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    diagnostics_json: Mapped[dict] = mapped_column(
        "diagnostics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    lineage_remediation_json: Mapped[dict] = mapped_column(
        "lineage_remediation",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    readiness_payload_json: Mapped[dict] = mapped_column(
        "readiness_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    assessment_payload_json: Mapped[dict] = mapped_column(
        "assessment_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    readiness_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    assessment_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
