"""add search feedback and replay runs

Revision ID: 0011_search_feedback_replays
Revises: 0010_search_request_history
Create Date: 2026-04-12 13:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011_search_feedback_replays"
down_revision = "0010_search_request_history"
branch_labels = None
depends_on = None


def _jsonb_type() -> sa.JSON:
    return sa.JSON().with_variant(
        sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
        "postgresql",
    )


def upgrade() -> None:
    op.create_table(
        "search_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("search_request_id", sa.Uuid(), nullable=False),
        sa.Column("search_request_result_id", sa.Uuid(), nullable=True),
        sa.Column("result_rank", sa.Integer(), nullable=True),
        sa.Column("feedback_type", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "feedback_type IN ('relevant', 'irrelevant', 'missing_table', "
            "'missing_chunk', 'no_answer')",
            name="ck_search_feedback_type",
        ),
        sa.ForeignKeyConstraint(["search_request_id"], ["search_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["search_request_result_id"],
            ["search_request_results.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_search_feedback_search_request_id",
        "search_feedback",
        ["search_request_id"],
    )
    op.create_index(
        "ix_search_feedback_search_request_result_id",
        "search_feedback",
        ["search_request_result_id"],
    )
    op.create_index("ix_search_feedback_feedback_type", "search_feedback", ["feedback_type"])
    op.create_index("ix_search_feedback_created_at", "search_feedback", ["created_at"])

    op.create_table(
        "search_replay_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("query_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("zero_result_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("table_hit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "top_result_changes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("max_rank_shift", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("summary", _jsonb_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_type IN ('evaluation_queries', 'live_search_gaps', 'feedback')",
            name="ck_search_replay_runs_source_type",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_search_replay_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_replay_runs_created_at", "search_replay_runs", ["created_at"])
    op.create_index(
        "ix_search_replay_runs_source_type_created_at",
        "search_replay_runs",
        ["source_type", "created_at"],
    )

    op.create_table(
        "search_replay_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("replay_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_search_request_id", sa.Uuid(), nullable=True),
        sa.Column("replay_search_request_id", sa.Uuid(), nullable=True),
        sa.Column("feedback_id", sa.Uuid(), nullable=True),
        sa.Column("evaluation_query_id", sa.Uuid(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("filters", _jsonb_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expected_result_type", sa.Text(), nullable=True),
        sa.Column("expected_top_n", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("table_hit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("overlap_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("added_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("removed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "top_result_changed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("max_rank_shift", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("details", _jsonb_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["replay_run_id"], ["search_replay_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["replay_search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["feedback_id"], ["search_feedback.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["evaluation_query_id"],
            ["document_run_evaluation_queries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_search_replay_queries_replay_run_id",
        "search_replay_queries",
        ["replay_run_id"],
    )
    op.create_index(
        "ix_search_replay_queries_source_search_request_id",
        "search_replay_queries",
        ["source_search_request_id"],
    )
    op.create_index(
        "ix_search_replay_queries_replay_search_request_id",
        "search_replay_queries",
        ["replay_search_request_id"],
    )
    op.create_index(
        "ix_search_replay_queries_feedback_id",
        "search_replay_queries",
        ["feedback_id"],
    )
    op.create_index(
        "ix_search_replay_queries_evaluation_query_id",
        "search_replay_queries",
        ["evaluation_query_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_replay_queries_evaluation_query_id",
        table_name="search_replay_queries",
    )
    op.drop_index("ix_search_replay_queries_feedback_id", table_name="search_replay_queries")
    op.drop_index(
        "ix_search_replay_queries_replay_search_request_id",
        table_name="search_replay_queries",
    )
    op.drop_index(
        "ix_search_replay_queries_source_search_request_id",
        table_name="search_replay_queries",
    )
    op.drop_index("ix_search_replay_queries_replay_run_id", table_name="search_replay_queries")
    op.drop_table("search_replay_queries")
    op.drop_index(
        "ix_search_replay_runs_source_type_created_at",
        table_name="search_replay_runs",
    )
    op.drop_index("ix_search_replay_runs_created_at", table_name="search_replay_runs")
    op.drop_table("search_replay_runs")
    op.drop_index("ix_search_feedback_created_at", table_name="search_feedback")
    op.drop_index("ix_search_feedback_feedback_type", table_name="search_feedback")
    op.drop_index(
        "ix_search_feedback_search_request_result_id",
        table_name="search_feedback",
    )
    op.drop_index("ix_search_feedback_search_request_id", table_name="search_feedback")
    op.drop_table("search_feedback")
