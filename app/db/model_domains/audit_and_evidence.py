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


class AuditBundleExport(Base):
    __tablename__ = "audit_bundle_exports"
    __table_args__ = (
        CheckConstraint(
            "bundle_kind IN ("
            "'search_harness_release_provenance', "
            "'retrieval_training_run_provenance'"
            ")",
            name="ck_audit_bundle_exports_bundle_kind",
        ),
        CheckConstraint(
            "source_table IN ('search_harness_releases', 'retrieval_training_runs')",
            name="ck_audit_bundle_exports_source_table",
        ),
        CheckConstraint(
            "export_status IN ('completed', 'failed')",
            name="ck_audit_bundle_exports_status",
        ),
        CheckConstraint(
            "("
            "bundle_kind = 'search_harness_release_provenance' "
            "AND source_table = 'search_harness_releases' "
            "AND search_harness_release_id IS NOT NULL "
            "AND search_harness_release_id = source_id "
            "AND retrieval_training_run_id IS NULL"
            ") OR ("
            "bundle_kind = 'retrieval_training_run_provenance' "
            "AND source_table = 'retrieval_training_runs' "
            "AND retrieval_training_run_id IS NOT NULL "
            "AND retrieval_training_run_id = source_id"
            ")",
            name="ck_audit_bundle_exports_source_consistency",
        ),
        Index("ix_audit_bundle_exports_bundle_kind_created_at", "bundle_kind", "created_at"),
        Index("ix_audit_bundle_exports_source", "source_table", "source_id"),
        Index(
            "ix_audit_bundle_exports_release_created_at",
            "search_harness_release_id",
            "created_at",
        ),
        Index(
            "ix_audit_bundle_exports_training_run_created_at",
            "retrieval_training_run_id",
            "created_at",
        ),
        Index("ix_audit_bundle_exports_payload_sha256", "payload_sha256"),
        Index("ix_audit_bundle_exports_bundle_sha256", "bundle_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="RESTRICT"),
    )
    retrieval_training_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_training_runs.id", ondelete="RESTRICT"),
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_payload_json: Mapped[dict] = mapped_column(
        "bundle_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    integrity_json: Mapped[dict] = mapped_column(
        "integrity",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    export_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditBundleValidationReceipt(Base):
    __tablename__ = "audit_bundle_validation_receipts"
    __table_args__ = (
        CheckConstraint(
            "bundle_kind IN ("
            "'search_harness_release_provenance', "
            "'retrieval_training_run_provenance'"
            ")",
            name="ck_audit_bundle_validation_receipts_bundle_kind",
        ),
        CheckConstraint(
            "source_table IN ('search_harness_releases', 'retrieval_training_runs')",
            name="ck_audit_bundle_validation_receipts_source_table",
        ),
        CheckConstraint(
            "validation_status IN ('passed', 'failed')",
            name="ck_audit_bundle_validation_receipts_status",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_bundle_created",
            "audit_bundle_export_id",
            "created_at",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_source",
            "source_table",
            "source_id",
            "created_at",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_receipt_sha",
            "receipt_sha256",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_prov_jsonld_sha",
            "prov_jsonld_sha256",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_status_created",
            "validation_status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_bundle_export_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_bundle_exports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bundle_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    validation_profile: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[str] = mapped_column(Text, nullable=False)
    payload_schema_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prov_graph_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    bundle_integrity_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_integrity_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    semantic_governance_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    receipt_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    prov_jsonld_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    prov_jsonld_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    validation_errors_json: Mapped[list] = mapped_column(
        "validation_errors",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    receipt_payload_json: Mapped[dict] = mapped_column(
        "receipt_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    prov_jsonld_json: Mapped[dict] = mapped_column(
        "prov_jsonld",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidencePackageExport(Base):
    __tablename__ = "evidence_package_exports"
    __table_args__ = (
        CheckConstraint(
            "package_kind IN ('search_request', 'technical_report_claims')",
            name="ck_evidence_package_exports_package_kind",
        ),
        CheckConstraint(
            "export_status IN ('completed', 'failed')",
            name="ck_evidence_package_exports_export_status",
        ),
        Index("ix_evidence_package_exports_created_at", "created_at"),
        Index("ix_evidence_package_exports_search_request_id", "search_request_id"),
        Index("ix_evidence_package_exports_agent_task_id", "agent_task_id"),
        Index("ix_evidence_package_exports_package_sha256", "package_sha256"),
        Index("ix_evidence_package_exports_trace_sha256", "trace_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_kind: Mapped[str] = mapped_column(Text, nullable=False)
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    agent_task_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    trace_sha256: Mapped[str | None] = mapped_column(Text)
    package_payload_json: Mapped[dict] = mapped_column(
        "package_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_snapshot_sha256s_json: Mapped[list] = mapped_column(
        "source_snapshot_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    operator_run_ids_json: Mapped[list] = mapped_column(
        "operator_run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    document_ids_json: Mapped[list] = mapped_column(
        "document_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    run_ids_json: Mapped[list] = mapped_column(
        "run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    claim_ids_json: Mapped[list] = mapped_column(
        "claim_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    export_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceManifest(Base):
    __tablename__ = "evidence_manifests"
    __table_args__ = (
        CheckConstraint(
            "manifest_kind IN ('technical_report_court_evidence')",
            name="ck_evidence_manifests_manifest_kind",
        ),
        CheckConstraint(
            "manifest_status IN ('completed', 'failed')",
            name="ck_evidence_manifests_manifest_status",
        ),
        UniqueConstraint(
            "verification_task_id",
            "manifest_kind",
            name="uq_evidence_manifests_verification_task_kind",
        ),
        Index("ix_evidence_manifests_agent_task_id", "agent_task_id"),
        Index("ix_evidence_manifests_draft_task_id", "draft_task_id"),
        Index("ix_evidence_manifests_verification_task_id", "verification_task_id"),
        Index("ix_evidence_manifests_export_id", "evidence_package_export_id"),
        Index("ix_evidence_manifests_manifest_sha256", "manifest_sha256"),
        Index("ix_evidence_manifests_trace_sha256", "trace_sha256"),
        Index("ix_evidence_manifests_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifest_kind: Mapped[str] = mapped_column(Text, nullable=False)
    agent_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    draft_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="SET NULL"),
    )
    manifest_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    trace_sha256: Mapped[str | None] = mapped_column(Text)
    manifest_payload_json: Mapped[dict] = mapped_column(
        "manifest_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_snapshot_sha256s_json: Mapped[list] = mapped_column(
        "source_snapshot_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    document_ids_json: Mapped[list] = mapped_column(
        "document_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    run_ids_json: Mapped[list] = mapped_column(
        "run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    claim_ids_json: Mapped[list] = mapped_column(
        "claim_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    search_request_ids_json: Mapped[list] = mapped_column(
        "search_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    operator_run_ids_json: Mapped[list] = mapped_column(
        "operator_run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    manifest_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class EvidenceTraceNode(Base):
    __tablename__ = "evidence_trace_nodes"
    __table_args__ = (
        CheckConstraint(
            "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
            "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
            name="ck_evidence_trace_nodes_single_owner",
        ),
        UniqueConstraint(
            "evidence_manifest_id",
            "node_key",
            name="uq_evidence_trace_nodes_manifest_node_key",
        ),
        UniqueConstraint(
            "evidence_package_export_id",
            "node_key",
            name="uq_evidence_trace_nodes_export_node_key",
        ),
        Index("ix_evidence_trace_nodes_manifest_id", "evidence_manifest_id"),
        Index("ix_evidence_trace_nodes_export_id", "evidence_package_export_id"),
        Index("ix_evidence_trace_nodes_node_kind", "node_kind"),
        Index("ix_evidence_trace_nodes_source", "source_table", "source_id"),
        Index("ix_evidence_trace_nodes_source_ref", "source_table", "source_ref"),
        Index("ix_evidence_trace_nodes_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="CASCADE"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
    )
    node_key: Mapped[str] = mapped_column(Text, nullable=False)
    node_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_ref: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceTraceEdge(Base):
    __tablename__ = "evidence_trace_edges"
    __table_args__ = (
        CheckConstraint(
            "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
            "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
            name="ck_evidence_trace_edges_single_owner",
        ),
        UniqueConstraint(
            "evidence_manifest_id",
            "edge_key",
            name="uq_evidence_trace_edges_manifest_edge_key",
        ),
        UniqueConstraint(
            "evidence_package_export_id",
            "edge_key",
            name="uq_evidence_trace_edges_export_edge_key",
        ),
        Index("ix_evidence_trace_edges_manifest_id", "evidence_manifest_id"),
        Index("ix_evidence_trace_edges_export_id", "evidence_package_export_id"),
        Index("ix_evidence_trace_edges_edge_kind", "edge_kind"),
        Index("ix_evidence_trace_edges_from_node_id", "from_node_id"),
        Index("ix_evidence_trace_edges_to_node_id", "to_node_id"),
        Index("ix_evidence_trace_edges_derivation_sha256", "derivation_sha256"),
        Index("ix_evidence_trace_edges_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="CASCADE"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
    )
    edge_key: Mapped[str] = mapped_column(Text, nullable=False)
    edge_kind: Mapped[str] = mapped_column(Text, nullable=False)
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_trace_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_trace_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_node_key: Mapped[str] = mapped_column(Text, nullable=False)
    to_node_key: Mapped[str] = mapped_column(Text, nullable=False)
    derivation_sha256: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimEvidenceDerivation(Base):
    __tablename__ = "claim_evidence_derivations"
    __table_args__ = (
        CheckConstraint(
            "support_verdict IS NULL OR support_verdict IN "
            "('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_evidence_derivations_support_verdict",
        ),
        Index("ix_claim_evidence_derivations_export_id", "evidence_package_export_id"),
        Index("ix_claim_evidence_derivations_agent_task_id", "agent_task_id"),
        Index("ix_claim_evidence_derivations_claim_id", "claim_id"),
        Index("ix_claim_evidence_derivations_derivation_sha256", "derivation_sha256"),
        Index("ix_claim_evidence_derivations_support_verdict", "support_verdict"),
        Index("ix_claim_evidence_derivations_support_judge_run_id", "support_judge_run_id"),
        Index(
            "ix_claim_evidence_derivations_provenance_lock_sha",
            "provenance_lock_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_package_export_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    claim_id: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str | None] = mapped_column(Text)
    derivation_rule: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_card_ids_json: Mapped[list] = mapped_column(
        "evidence_card_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    graph_edge_ids_json: Mapped[list] = mapped_column(
        "graph_edge_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    fact_ids_json: Mapped[list] = mapped_column(
        "fact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    assertion_ids_json: Mapped[list] = mapped_column(
        "assertion_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_document_ids_json: Mapped[list] = mapped_column(
        "source_document_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_snapshot_sha256s_json: Mapped[list] = mapped_column(
        "source_snapshot_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
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
    source_evidence_package_export_ids_json: Mapped[list] = mapped_column(
        "source_evidence_package_export_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_package_sha256s_json: Mapped[list] = mapped_column(
        "source_evidence_package_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_trace_sha256s_json: Mapped[list] = mapped_column(
        "source_evidence_trace_sha256s",
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
    provenance_lock_json: Mapped[dict] = mapped_column(
        "provenance_lock",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    provenance_lock_sha256: Mapped[str | None] = mapped_column(Text)
    support_verdict: Mapped[str | None] = mapped_column(Text)
    support_score: Mapped[float | None] = mapped_column(Float)
    support_judge_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="SET NULL"),
    )
    support_judgment_json: Mapped[dict] = mapped_column(
        "support_judgment",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    support_judgment_sha256: Mapped[str | None] = mapped_column(Text)
    evidence_package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    derivation_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
