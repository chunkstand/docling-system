"""add durable search harness evaluations

Revision ID: 0029_search_harness_evaluations
Revises: 0028_semantic_graph_memory
Create Date: 2026-04-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0029_search_harness_evaluations"
down_revision: str | Sequence[str] | None = "0028_semantic_graph_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_harness_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
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
            "harness_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "total_shared_query_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "total_improved_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "total_regressed_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "total_unchanged_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_search_harness_evaluations_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_search_harness_evaluations_baseline_candidate",
        "search_harness_evaluations",
        ["baseline_harness_name", "candidate_harness_name"],
        unique=False,
    )
    op.create_index(
        "ix_search_harness_evaluations_candidate_created_at",
        "search_harness_evaluations",
        ["candidate_harness_name", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_search_harness_evaluations_created_at",
        "search_harness_evaluations",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "search_harness_evaluation_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_harness_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("baseline_replay_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_replay_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_status", sa.Text(), nullable=True),
        sa.Column("candidate_status", sa.Text(), nullable=True),
        sa.Column(
            "baseline_query_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "candidate_query_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "baseline_passed_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "candidate_passed_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "baseline_zero_result_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "candidate_zero_result_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "baseline_table_hit_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "candidate_table_hit_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "baseline_top_result_changes", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "candidate_top_result_changes",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("baseline_mrr", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("candidate_mrr", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "baseline_foreign_top_result_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "candidate_foreign_top_result_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "acceptance_checks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("shared_query_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("improved_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("regressed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ("
            "'evaluation_queries', "
            "'live_search_gaps', "
            "'feedback', "
            "'cross_document_prose_regressions'"
            ")",
            name="ck_search_harness_evaluation_sources_source_type",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_replay_run_id"],
            ["search_replay_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_replay_run_id"],
            ["search_replay_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "search_harness_evaluation_id",
            "source_type",
            name="uq_search_harness_evaluation_sources_eval_source",
        ),
    )
    op.create_index(
        "ix_search_harness_evaluation_sources_baseline_replay",
        "search_harness_evaluation_sources",
        ["baseline_replay_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_search_harness_evaluation_sources_candidate_replay",
        "search_harness_evaluation_sources",
        ["candidate_replay_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_search_harness_evaluation_sources_eval_id",
        "search_harness_evaluation_sources",
        ["search_harness_evaluation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_harness_evaluation_sources_eval_id",
        table_name="search_harness_evaluation_sources",
    )
    op.drop_index(
        "ix_search_harness_evaluation_sources_candidate_replay",
        table_name="search_harness_evaluation_sources",
    )
    op.drop_index(
        "ix_search_harness_evaluation_sources_baseline_replay",
        table_name="search_harness_evaluation_sources",
    )
    op.drop_table("search_harness_evaluation_sources")
    op.drop_index(
        "ix_search_harness_evaluations_created_at",
        table_name="search_harness_evaluations",
    )
    op.drop_index(
        "ix_search_harness_evaluations_candidate_created_at",
        table_name="search_harness_evaluations",
    )
    op.drop_index(
        "ix_search_harness_evaluations_baseline_candidate",
        table_name="search_harness_evaluations",
    )
    op.drop_table("search_harness_evaluations")
