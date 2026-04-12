"""add search request history

Revision ID: 0010_search_request_history
Revises: 0009_run_failure_artifacts
Create Date: 2026-04-12 12:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010_search_request_history"
down_revision = "0009_run_failure_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_request_id", sa.Uuid(), nullable=True),
        sa.Column("evaluation_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column(
            "filters",
            sa.JSON().with_variant(
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "details",
            sa.JSON().with_variant(
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("tabular_query", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reranker_name", sa.Text(), nullable=False),
        sa.Column("embedding_status", sa.Text(), nullable=False),
        sa.Column("embedding_error", sa.Text(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("table_hit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode IN ('keyword', 'semantic', 'hybrid')",
            name="ck_search_requests_mode",
        ),
        sa.ForeignKeyConstraint(["parent_request_id"], ["search_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["document_run_evaluations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_requests_created_at", "search_requests", ["created_at"])
    op.create_index(
        "ix_search_requests_origin_created_at",
        "search_requests",
        ["origin", "created_at"],
    )
    op.create_index(
        "ix_search_requests_evaluation_id",
        "search_requests",
        ["evaluation_id"],
    )
    op.create_index(
        "ix_search_requests_parent_request_id",
        "search_requests",
        ["parent_request_id"],
    )

    op.create_table(
        "search_request_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("search_request_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("base_rank", sa.Integer(), nullable=True),
        sa.Column("result_type", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("table_id", sa.Uuid(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("keyword_score", sa.Float(), nullable=True),
        sa.Column("semantic_score", sa.Float(), nullable=True),
        sa.Column("hybrid_score", sa.Float(), nullable=True),
        sa.Column(
            "rerank_features",
            sa.JSON().with_variant(
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "result_type IN ('chunk', 'table')",
            name="ck_search_request_results_result_type",
        ),
        sa.ForeignKeyConstraint(["search_request_id"], ["search_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "search_request_id",
            "rank",
            name="uq_search_request_results_request_rank",
        ),
    )
    op.create_index(
        "ix_search_request_results_search_request_id",
        "search_request_results",
        ["search_request_id"],
    )
    op.create_index(
        "ix_search_request_results_result_type",
        "search_request_results",
        ["result_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_search_request_results_result_type", table_name="search_request_results")
    op.drop_index(
        "ix_search_request_results_search_request_id",
        table_name="search_request_results",
    )
    op.drop_table("search_request_results")
    op.drop_index("ix_search_requests_parent_request_id", table_name="search_requests")
    op.drop_index("ix_search_requests_evaluation_id", table_name="search_requests")
    op.drop_index("ix_search_requests_origin_created_at", table_name="search_requests")
    op.drop_index("ix_search_requests_created_at", table_name="search_requests")
    op.drop_table("search_requests")
