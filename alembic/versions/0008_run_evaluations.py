"""add run evaluations

Revision ID: 0008_run_evaluations
Revises: 0007_document_figures
Create Date: 2026-04-11 18:50:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_run_evaluations"
down_revision = "0007_document_figures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_run_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("corpus_name", sa.Text(), nullable=False),
        sa.Column("fixture_name", sa.Text(), nullable=True),
        sa.Column("eval_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "summary",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'skipped')",
            name="ck_document_run_evaluations_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "corpus_name", "eval_version", name="uq_document_run_evaluations_run_corpus_version"),
    )
    op.create_index("ix_document_run_evaluations_run_id", "document_run_evaluations", ["run_id"])
    op.create_index("ix_document_run_evaluations_status", "document_run_evaluations", ["status"])

    op.create_table(
        "document_run_evaluation_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column(
            "filters",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("expected_result_type", sa.Text(), nullable=True),
        sa.Column("expected_top_n", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("candidate_rank", sa.Integer(), nullable=True),
        sa.Column("baseline_rank", sa.Integer(), nullable=True),
        sa.Column("rank_delta", sa.Integer(), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column("candidate_result_type", sa.Text(), nullable=True),
        sa.Column("baseline_result_type", sa.Text(), nullable=True),
        sa.Column("candidate_label", sa.Text(), nullable=True),
        sa.Column("baseline_label", sa.Text(), nullable=True),
        sa.Column(
            "details",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_id"], ["document_run_evaluations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_run_evaluation_queries_evaluation_id", "document_run_evaluation_queries", ["evaluation_id"])
    op.create_index("ix_document_run_evaluation_queries_query_text", "document_run_evaluation_queries", ["query_text"])


def downgrade() -> None:
    op.drop_index("ix_document_run_evaluation_queries_query_text", table_name="document_run_evaluation_queries")
    op.drop_index("ix_document_run_evaluation_queries_evaluation_id", table_name="document_run_evaluation_queries")
    op.drop_table("document_run_evaluation_queries")
    op.drop_index("ix_document_run_evaluations_status", table_name="document_run_evaluations")
    op.drop_index("ix_document_run_evaluations_run_id", table_name="document_run_evaluations")
    op.drop_table("document_run_evaluations")
