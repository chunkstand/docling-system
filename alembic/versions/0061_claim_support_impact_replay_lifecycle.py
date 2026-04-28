"""Add claim support impact replay lifecycle columns.

Revision ID: 0061_claim_impact_replay
Revises: 0060_claim_policy_impacts
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0061_claim_impact_replay"
down_revision: str | Sequence[str] | None = "0060_claim_policy_impacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "claim_support_policy_change_impacts",
        sa.Column(
            "replay_status",
            sa.Text(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
    )
    op.add_column(
        "claim_support_policy_change_impacts",
        sa.Column(
            "replay_task_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "claim_support_policy_change_impacts",
        sa.Column(
            "replay_task_plan",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "claim_support_policy_change_impacts",
        sa.Column(
            "replay_closure",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "claim_support_policy_change_impacts",
        sa.Column("replay_closure_sha256", sa.Text(), nullable=True),
    )
    op.add_column(
        "claim_support_policy_change_impacts",
        sa.Column("replay_status_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "claim_support_policy_change_impacts",
        sa.Column("replay_closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_claim_support_policy_change_impacts_replay_status",
        "claim_support_policy_change_impacts",
        (
            "replay_status IN "
            "('no_action_required', 'pending', 'queued', 'in_progress', 'blocked', 'closed')"
        ),
    )
    op.execute(
        """
        UPDATE claim_support_policy_change_impacts
        SET replay_status = CASE
            WHEN replay_recommended_count = 0 THEN 'no_action_required'
            ELSE 'pending'
        END,
            replay_status_updated_at = created_at
        """
    )
    op.create_index(
        "ix_claim_support_policy_change_impacts_replay_status",
        "claim_support_policy_change_impacts",
        ["replay_status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_support_policy_change_impacts_replay_status",
        table_name="claim_support_policy_change_impacts",
    )
    op.drop_constraint(
        "ck_claim_support_policy_change_impacts_replay_status",
        "claim_support_policy_change_impacts",
        type_="check",
    )
    op.drop_column("claim_support_policy_change_impacts", "replay_closed_at")
    op.drop_column("claim_support_policy_change_impacts", "replay_status_updated_at")
    op.drop_column("claim_support_policy_change_impacts", "replay_closure_sha256")
    op.drop_column("claim_support_policy_change_impacts", "replay_closure")
    op.drop_column("claim_support_policy_change_impacts", "replay_task_plan")
    op.drop_column("claim_support_policy_change_impacts", "replay_task_ids")
    op.drop_column("claim_support_policy_change_impacts", "replay_status")
