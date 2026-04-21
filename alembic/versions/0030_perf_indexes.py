"""add performance indexes

Revision ID: 0030_perf_indexes
Revises: 0029_search_harness_evaluations
Create Date: 2026-04-21 00:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0030_perf_indexes"
down_revision: str | Sequence[str] | None = "0029_search_harness_evaluations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_documents_updated_at", "documents", ["updated_at"], unique=False)
    op.create_index(
        "ix_search_replay_queries_created_at",
        "search_replay_queries",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_search_replay_queries_created_at", table_name="search_replay_queries")
    op.drop_index("ix_documents_updated_at", table_name="documents")
