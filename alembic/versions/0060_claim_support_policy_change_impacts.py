"""Add claim support policy change impact ledger.

Revision ID: 0060_claim_policy_impacts
Revises: 0059_claim_policy_governance
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0060_claim_policy_impacts"
down_revision: str | Sequence[str] | None = "0059_claim_policy_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_support_policy_change_impacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activation_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "semantic_governance_event_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("governance_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("impact_scope", sa.Text(), nullable=False),
        sa.Column("policy_name", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("activated_policy_sha256", sa.Text(), nullable=False),
        sa.Column("previous_policy_sha256", sa.Text(), nullable=True),
        sa.Column(
            "affected_support_judgment_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "affected_generated_document_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "affected_verification_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "replay_recommended_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "impacted_claim_derivation_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "impacted_task_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "impacted_verification_task_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "impact_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("impact_payload_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "affected_support_judgment_count >= 0",
            name="ck_claim_support_policy_change_impacts_support_count",
        ),
        sa.CheckConstraint(
            "affected_generated_document_count >= 0",
            name="ck_claim_support_policy_change_impacts_document_count",
        ),
        sa.CheckConstraint(
            "affected_verification_count >= 0",
            name="ck_claim_support_policy_change_impacts_verification_count",
        ),
        sa.CheckConstraint(
            "replay_recommended_count >= 0",
            name="ck_claim_support_policy_change_impacts_replay_count",
        ),
        sa.ForeignKeyConstraint(
            ["activation_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["activated_policy_id"],
            ["claim_support_calibration_policies.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["previous_policy_id"],
            ["claim_support_calibration_policies.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_governance_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["governance_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claim_support_policy_change_impacts_activation_task",
        "claim_support_policy_change_impacts",
        ["activation_task_id", "created_at"],
    )
    op.create_index(
        "ix_claim_support_policy_change_impacts_policy",
        "claim_support_policy_change_impacts",
        ["activated_policy_id", "created_at"],
    )
    op.create_index(
        "ix_claim_support_policy_change_impacts_governance_event",
        "claim_support_policy_change_impacts",
        ["semantic_governance_event_id"],
    )
    op.create_index(
        "ix_claim_support_policy_change_impacts_governance_artifact",
        "claim_support_policy_change_impacts",
        ["governance_artifact_id"],
    )
    op.create_index(
        "ix_claim_support_policy_change_impacts_scope_created",
        "claim_support_policy_change_impacts",
        ["impact_scope", "created_at"],
    )
    op.create_index(
        "ix_claim_support_policy_change_impacts_payload_sha",
        "claim_support_policy_change_impacts",
        ["impact_payload_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_support_policy_change_impacts_payload_sha",
        table_name="claim_support_policy_change_impacts",
    )
    op.drop_index(
        "ix_claim_support_policy_change_impacts_scope_created",
        table_name="claim_support_policy_change_impacts",
    )
    op.drop_index(
        "ix_claim_support_policy_change_impacts_governance_artifact",
        table_name="claim_support_policy_change_impacts",
    )
    op.drop_index(
        "ix_claim_support_policy_change_impacts_governance_event",
        table_name="claim_support_policy_change_impacts",
    )
    op.drop_index(
        "ix_claim_support_policy_change_impacts_policy",
        table_name="claim_support_policy_change_impacts",
    )
    op.drop_index(
        "ix_claim_support_policy_change_impacts_activation_task",
        table_name="claim_support_policy_change_impacts",
    )
    op.drop_table("claim_support_policy_change_impacts")
