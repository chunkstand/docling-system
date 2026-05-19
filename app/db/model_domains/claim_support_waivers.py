from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClaimSupportReplayAlertFixtureCoverageWaiverLedger(Base):
    __tablename__ = "claim_support_replay_alert_fixture_coverage_waiver_ledgers"
    __table_args__ = (
        CheckConstraint(
            "coverage_status IN ('open', 'partially_covered', 'closed', 'no_action_required')",
            name="ck_cs_waiver_ledgers_status",
        ),
        UniqueConstraint(
            "waiver_artifact_id",
            "waiver_sha256",
            name="uq_cs_waiver_ledgers_artifact_sha",
        ),
        Index("ix_cs_waiver_ledgers_artifact", "waiver_artifact_id"),
        Index("ix_cs_waiver_ledgers_task", "verification_task_id"),
        Index("ix_cs_waiver_ledgers_status", "coverage_status", "created_at"),
        Index("ix_cs_waiver_ledgers_closure", "closure_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waiver_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    target_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    fixture_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claim_support_fixture_sets.id", ondelete="SET NULL")
    )
    waiver_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    waiver_severity: Mapped[str | None] = mapped_column(Text)
    waived_by: Mapped[str | None] = mapped_column(Text)
    waiver_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waiver_review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waiver_remediation_owner: Mapped[str | None] = mapped_column(Text)
    waived_escalation_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    covered_escalation_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    coverage_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    coverage_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="open",
        server_default=sql_text("'open'"),
    )
    waived_escalation_set_sha256: Mapped[str | None] = mapped_column(Text)
    covered_escalation_set_sha256: Mapped[str | None] = mapped_column(Text)
    source_change_impact_ids_json: Mapped[list] = mapped_column(
        "source_change_impact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_verification_task_ids_json: Mapped[list] = mapped_column(
        "source_verification_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    closure_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    closure_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    closure_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    promotion_event_ids_json: Mapped[list] = mapped_column(
        "promotion_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    promotion_artifact_ids_json: Mapped[list] = mapped_column(
        "promotion_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    promotion_receipt_sha256s_json: Mapped[list] = mapped_column(
        "promotion_receipt_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    ledger_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportReplayAlertFixtureCoverageWaiverEscalation(Base):
    __tablename__ = "claim_support_replay_alert_fixture_coverage_waiver_escalations"
    __table_args__ = (
        UniqueConstraint(
            "ledger_id",
            "escalation_event_id",
            name="uq_cs_waiver_escalations_ledger_event",
        ),
        Index("ix_cs_waiver_escalations_ledger", "ledger_id"),
        Index("ix_cs_waiver_escalations_event", "escalation_event_id"),
        Index("ix_cs_waiver_escalations_covered", "ledger_id", "covered"),
        Index("ix_cs_waiver_escalations_impact", "change_impact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claim_support_replay_alert_fixture_coverage_waiver_ledgers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    waiver_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    escalation_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    change_impact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_policy_change_impacts.id", ondelete="SET NULL"),
    )
    escalation_event_hash: Mapped[str | None] = mapped_column(Text)
    escalation_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    alert_kind: Mapped[str | None] = mapped_column(Text)
    replay_status: Mapped[str | None] = mapped_column(Text)
    covered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    covered_by_promotion_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    covered_by_promotion_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    covered_by_promotion_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    covered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
