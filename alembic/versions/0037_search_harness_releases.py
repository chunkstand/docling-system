"""add search harness release gates

Revision ID: 0037_search_harness_releases
Revises: 0036_retrieval_evidence_spans
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0037_search_harness_releases"
down_revision: str | Sequence[str] | None = "0036_retrieval_evidence_spans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_harness_releases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_harness_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("baseline_harness_name", sa.Text(), nullable=False),
        sa.Column("candidate_harness_name", sa.Text(), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column(
            "source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "thresholds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("release_package_sha256", sa.Text(), nullable=False),
        sa.Column("requested_by", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('passed', 'failed', 'error')",
            name="ck_search_harness_releases_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_search_harness_releases_candidate_created_at",
        "search_harness_releases",
        ["candidate_harness_name", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_search_harness_releases_created_at",
        "search_harness_releases",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_search_harness_releases_evaluation_id",
        "search_harness_releases",
        ["search_harness_evaluation_id"],
        unique=False,
    )
    op.create_index(
        "ix_search_harness_releases_outcome_created_at",
        "search_harness_releases",
        ["outcome", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_harness_releases_outcome_created_at",
        table_name="search_harness_releases",
    )
    op.drop_index(
        "ix_search_harness_releases_evaluation_id",
        table_name="search_harness_releases",
    )
    op.drop_index(
        "ix_search_harness_releases_created_at",
        table_name="search_harness_releases",
    )
    op.drop_index(
        "ix_search_harness_releases_candidate_created_at",
        table_name="search_harness_releases",
    )
    op.drop_table("search_harness_releases")
