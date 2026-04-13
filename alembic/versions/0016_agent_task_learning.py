"""add agent task learning surfaces

Revision ID: 0016_agent_task_learning
Revises: 0015_agent_task_rejections
Create Date: 2026-04-13 15:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016_agent_task_learning"
down_revision: str | Sequence[str] | None = "0015_agent_task_rejections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_task_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome_label", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome_label IN ('useful', 'not_useful', 'correct', 'incorrect')",
            name="ck_agent_task_outcomes_outcome_label",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_task_outcomes_task_id",
        "agent_task_outcomes",
        ["task_id"],
    )
    op.create_index(
        "ix_agent_task_outcomes_outcome_label",
        "agent_task_outcomes",
        ["outcome_label"],
    )
    op.create_index(
        "ix_agent_task_outcomes_created_at",
        "agent_task_outcomes",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_task_outcomes_created_at", table_name="agent_task_outcomes")
    op.drop_index("ix_agent_task_outcomes_outcome_label", table_name="agent_task_outcomes")
    op.drop_index("ix_agent_task_outcomes_task_id", table_name="agent_task_outcomes")
    op.drop_table("agent_task_outcomes")
