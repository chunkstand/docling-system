"""add agent task rejection fields

Revision ID: 0015_agent_task_rejections
Revises: 0014_agent_task_verifications
Create Date: 2026-04-13 13:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015_agent_task_rejections"
down_revision: str | Sequence[str] | None = "0014_agent_task_verifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_tasks",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("agent_tasks", sa.Column("rejected_by", sa.Text(), nullable=True))
    op.add_column("agent_tasks", sa.Column("rejection_note", sa.Text(), nullable=True))
    op.drop_constraint("ck_agent_tasks_status", "agent_tasks", type_="check")
    op.create_check_constraint(
        "ck_agent_tasks_status",
        "agent_tasks",
        (
            "status IN ("
            "'blocked', 'awaiting_approval', 'rejected', 'queued', 'processing', "
            "'retry_wait', 'completed', 'failed'"
            ")"
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_agent_tasks_status", "agent_tasks", type_="check")
    op.create_check_constraint(
        "ck_agent_tasks_status",
        "agent_tasks",
        (
            "status IN ("
            "'blocked', 'awaiting_approval', 'queued', 'processing', "
            "'retry_wait', 'completed', 'failed'"
            ")"
        ),
    )
    op.drop_column("agent_tasks", "rejection_note")
    op.drop_column("agent_tasks", "rejected_by")
    op.drop_column("agent_tasks", "rejected_at")
