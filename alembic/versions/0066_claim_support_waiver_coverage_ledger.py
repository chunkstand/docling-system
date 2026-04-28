"""Add claim support replay waiver coverage ledger.

Revision ID: 0066_claim_waiver_ledger
Revises: 0065_claim_waiver_closures
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0066_claim_waiver_ledger"
down_revision: str | Sequence[str] | None = "0065_claim_waiver_closures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("waiver_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verification_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fixture_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waiver_sha256", sa.Text(), nullable=False),
        sa.Column("waiver_severity", sa.Text(), nullable=True),
        sa.Column("waived_by", sa.Text(), nullable=True),
        sa.Column("waiver_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waiver_review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waiver_remediation_owner", sa.Text(), nullable=True),
        sa.Column(
            "waived_escalation_event_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "covered_escalation_event_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "coverage_complete",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "coverage_status",
            sa.Text(),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column("waived_escalation_set_sha256", sa.Text(), nullable=True),
        sa.Column("covered_escalation_set_sha256", sa.Text(), nullable=True),
        sa.Column(
            "source_change_impact_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_verification_task_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("closure_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closure_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closure_receipt_sha256", sa.Text(), nullable=True),
        sa.Column(
            "promotion_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "promotion_artifact_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "promotion_receipt_sha256s",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("ledger_payload_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "coverage_status IN ('open', 'partially_covered', 'closed', 'no_action_required')",
            name="ck_cs_waiver_ledgers_status",
        ),
        sa.ForeignKeyConstraint(
            ["closure_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["closure_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["fixture_set_id"],
            ["claim_support_fixture_sets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["claim_support_calibration_policies.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["verification_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["waiver_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "waiver_artifact_id",
            "waiver_sha256",
            name="uq_cs_waiver_ledgers_artifact_sha",
        ),
    )
    op.create_index(
        "ix_cs_waiver_ledgers_artifact",
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers",
        ["waiver_artifact_id"],
    )
    op.create_index(
        "ix_cs_waiver_ledgers_closure",
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers",
        ["closure_event_id"],
    )
    op.create_index(
        "ix_cs_waiver_ledgers_status",
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers",
        ["coverage_status", "created_at"],
    )
    op.create_index(
        "ix_cs_waiver_ledgers_task",
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers",
        ["verification_task_id"],
    )

    op.create_table(
        "claim_support_replay_alert_fixture_coverage_waiver_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("waiver_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escalation_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_impact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_event_hash", sa.Text(), nullable=True),
        sa.Column("escalation_receipt_sha256", sa.Text(), nullable=True),
        sa.Column("alert_kind", sa.Text(), nullable=True),
        sa.Column("replay_status", sa.Text(), nullable=True),
        sa.Column(
            "covered",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("covered_by_promotion_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("covered_by_promotion_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("covered_by_promotion_receipt_sha256", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("covered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["change_impact_id"],
            ["claim_support_policy_change_impacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["covered_by_promotion_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["covered_by_promotion_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["escalation_event_id"],
            ["semantic_governance_events.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ledger_id"],
            ["claim_support_replay_alert_fixture_coverage_waiver_ledgers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["waiver_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ledger_id",
            "escalation_event_id",
            name="uq_cs_waiver_escalations_ledger_event",
        ),
    )
    op.create_index(
        "ix_cs_waiver_escalations_covered",
        "claim_support_replay_alert_fixture_coverage_waiver_escalations",
        ["ledger_id", "covered"],
    )
    op.create_index(
        "ix_cs_waiver_escalations_event",
        "claim_support_replay_alert_fixture_coverage_waiver_escalations",
        ["escalation_event_id"],
    )
    op.create_index(
        "ix_cs_waiver_escalations_impact",
        "claim_support_replay_alert_fixture_coverage_waiver_escalations",
        ["change_impact_id"],
    )
    op.create_index(
        "ix_cs_waiver_escalations_ledger",
        "claim_support_replay_alert_fixture_coverage_waiver_escalations",
        ["ledger_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_waiver_escalations_ledger",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_escalations",
    )
    op.drop_index(
        "ix_cs_waiver_escalations_impact",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_escalations",
    )
    op.drop_index(
        "ix_cs_waiver_escalations_event",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_escalations",
    )
    op.drop_index(
        "ix_cs_waiver_escalations_covered",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_escalations",
    )
    op.drop_table("claim_support_replay_alert_fixture_coverage_waiver_escalations")
    op.drop_index(
        "ix_cs_waiver_ledgers_task",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_ledgers",
    )
    op.drop_index(
        "ix_cs_waiver_ledgers_status",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_ledgers",
    )
    op.drop_index(
        "ix_cs_waiver_ledgers_closure",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_ledgers",
    )
    op.drop_index(
        "ix_cs_waiver_ledgers_artifact",
        table_name="claim_support_replay_alert_fixture_coverage_waiver_ledgers",
    )
    op.drop_table("claim_support_replay_alert_fixture_coverage_waiver_ledgers")
