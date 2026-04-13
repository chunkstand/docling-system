"""add agent task verification records

Revision ID: 0014_agent_task_verifications
Revises: 0013_agent_task_substrate
Create Date: 2026-04-13 00:40:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0014_agent_task_verifications"
down_revision = "0013_agent_task_substrate"
branch_labels = None
depends_on = None


def _jsonb_type() -> sa.JSON:
    return sa.JSON().with_variant(
        sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
        "postgresql",
    )


def upgrade() -> None:
    op.create_table(
        "agent_task_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_task_id", sa.Uuid(), nullable=False),
        sa.Column("verification_task_id", sa.Uuid(), nullable=True),
        sa.Column("verifier_type", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column(
            "metrics",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "reasons",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "details",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('passed', 'failed', 'error')",
            name="ck_agent_task_verifications_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["target_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verification_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_task_verifications_target_task_id",
        "agent_task_verifications",
        ["target_task_id"],
    )
    op.create_index(
        "ix_agent_task_verifications_verification_task_id",
        "agent_task_verifications",
        ["verification_task_id"],
    )
    op.create_index(
        "ix_agent_task_verifications_verifier_type",
        "agent_task_verifications",
        ["verifier_type"],
    )
    op.create_index(
        "ix_agent_task_verifications_created_at",
        "agent_task_verifications",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_task_verifications_created_at",
        table_name="agent_task_verifications",
    )
    op.drop_index(
        "ix_agent_task_verifications_verifier_type",
        table_name="agent_task_verifications",
    )
    op.drop_index(
        "ix_agent_task_verifications_verification_task_id",
        table_name="agent_task_verifications",
    )
    op.drop_index(
        "ix_agent_task_verifications_target_task_id",
        table_name="agent_task_verifications",
    )
    op.drop_table("agent_task_verifications")
