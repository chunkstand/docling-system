"""persist cross-document replay source types directly

Revision ID: 0019_search_replay_source_type
Revises: 0018_task_attempt_analytics
Create Date: 2026-04-13 23:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019_search_replay_source_type"
down_revision: str | Sequence[str] | None = "0018_task_attempt_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        "source_type IN ("
        "'evaluation_queries', "
        "'live_search_gaps', "
        "'feedback', "
        "'cross_document_prose_regressions'"
        ")",
    )
    op.execute(
        sa.text(
            """
            UPDATE search_replay_runs
            SET source_type = 'cross_document_prose_regressions'
            WHERE source_type = 'evaluation_queries'
              AND COALESCE(summary ->> 'source_type', '') = 'cross_document_prose_regressions'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE search_replay_runs
            SET summary = jsonb_set(
                    COALESCE(summary, '{}'::jsonb),
                    '{source_type}',
                    to_jsonb(source_type::text),
                    true
                ),
                source_type = 'evaluation_queries'
            WHERE source_type = 'cross_document_prose_regressions'
            """
        )
    )
    op.drop_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        "source_type IN ('evaluation_queries', 'live_search_gaps', 'feedback')",
    )
