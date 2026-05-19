from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    pass


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
