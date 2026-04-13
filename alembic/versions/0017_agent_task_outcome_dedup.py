"""deduplicate agent task outcomes by task label and actor

Revision ID: 0017_task_outcome_dedup
Revises: 0016_agent_task_learning
Create Date: 2026-04-13 18:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017_task_outcome_dedup"
down_revision: str | Sequence[str] | None = "0016_agent_task_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM agent_task_outcomes
        WHERE id IN (
            SELECT id
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY task_id, outcome_label, created_by
                        ORDER BY created_at ASC, id ASC
                    ) AS row_number
                FROM agent_task_outcomes
            ) ranked
            WHERE ranked.row_number > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_agent_task_outcomes_task_label_actor",
        "agent_task_outcomes",
        ["task_id", "outcome_label", "created_by"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_agent_task_outcomes_task_label_actor",
        "agent_task_outcomes",
        type_="unique",
    )
