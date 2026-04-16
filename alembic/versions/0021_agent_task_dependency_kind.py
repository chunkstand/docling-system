"""add dependency kinds to agent task dependencies

Revision ID: 0021_agent_task_dependency_kind
Revises: 0020_ingest_batches
Create Date: 2026-04-15 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021_agent_task_dependency_kind"
down_revision: str | Sequence[str] | None = "0020_ingest_batches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_task_dependencies",
        sa.Column(
            "dependency_kind",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'explicit'"),
        ),
    )
    op.create_check_constraint(
        "ck_agent_task_dependencies_dependency_kind",
        "agent_task_dependencies",
        "dependency_kind IN ("
        "'explicit', 'target_task', 'source_task', 'draft_task', 'verification_task'"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_agent_task_dependencies_dependency_kind",
        "agent_task_dependencies",
        type_="check",
    )
    op.drop_column("agent_task_dependencies", "dependency_kind")
