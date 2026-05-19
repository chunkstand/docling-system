from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


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
