from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClaimSupportPolicyChangeImpact(Base):
    __tablename__ = "claim_support_policy_change_impacts"
    __table_args__ = (
        CheckConstraint(
            "affected_support_judgment_count >= 0",
            name="ck_claim_support_policy_change_impacts_support_count",
        ),
        CheckConstraint(
            "affected_generated_document_count >= 0",
            name="ck_claim_support_policy_change_impacts_document_count",
        ),
        CheckConstraint(
            "affected_verification_count >= 0",
            name="ck_claim_support_policy_change_impacts_verification_count",
        ),
        CheckConstraint(
            "replay_recommended_count >= 0",
            name="ck_claim_support_policy_change_impacts_replay_count",
        ),
        CheckConstraint(
            "replay_status IN "
            "('no_action_required', 'pending', 'queued', 'in_progress', 'blocked', 'closed')",
            name="ck_claim_support_policy_change_impacts_replay_status",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_activation_task",
            "activation_task_id",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_policy",
            "activated_policy_id",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_governance_event",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_governance_artifact",
            "governance_artifact_id",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_scope_created",
            "impact_scope",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_payload_sha",
            "impact_payload_sha256",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_replay_status",
            "replay_status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activation_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    activated_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    previous_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    governance_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    impact_scope: Mapped[str] = mapped_column(Text, nullable=False)
    policy_name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    activated_policy_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    previous_policy_sha256: Mapped[str | None] = mapped_column(Text)
    affected_support_judgment_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    affected_generated_document_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    affected_verification_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    replay_recommended_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    replay_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=sql_text("'pending'"),
    )
    impacted_claim_derivation_ids_json: Mapped[list] = mapped_column(
        "impacted_claim_derivation_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impacted_task_ids_json: Mapped[list] = mapped_column(
        "impacted_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impacted_verification_task_ids_json: Mapped[list] = mapped_column(
        "impacted_verification_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impact_payload_json: Mapped[dict] = mapped_column(
        "impact_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    impact_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    replay_task_ids_json: Mapped[list] = mapped_column(
        "replay_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    replay_task_plan_json: Mapped[dict] = mapped_column(
        "replay_task_plan",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    replay_closure_json: Mapped[dict] = mapped_column(
        "replay_closure",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    replay_closure_sha256: Mapped[str | None] = mapped_column(Text)
    replay_status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replay_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
