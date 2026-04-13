"""add cost and performance payloads to agent task attempts

Revision ID: 0018_task_attempt_analytics
Revises: 0017_task_outcome_dedup
Create Date: 2026-04-13 21:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018_task_attempt_analytics"
down_revision: str | Sequence[str] | None = "0017_task_outcome_dedup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_task_attempts",
        sa.Column(
            "cost",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "agent_task_attempts",
        sa.Column(
            "performance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_task_attempts", "performance")
    op.drop_column("agent_task_attempts", "cost")
