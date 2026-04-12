"""add search harness config and chat answer feedback

Revision ID: 0012_harness_chat_feedback
Revises: 0011_search_feedback_replays
Create Date: 2026-04-12 21:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012_harness_chat_feedback"
down_revision = "0011_search_feedback_replays"
branch_labels = None
depends_on = None


def _jsonb_type() -> sa.JSON:
    return sa.JSON().with_variant(
        sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
        "postgresql",
    )


def upgrade() -> None:
    op.add_column(
        "search_requests",
        sa.Column(
            "harness_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'default_v1'"),
        ),
    )
    op.add_column(
        "search_requests",
        sa.Column(
            "reranker_version",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
    )
    op.add_column(
        "search_requests",
        sa.Column(
            "retrieval_profile_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'default_v1'"),
        ),
    )
    op.add_column(
        "search_requests",
        sa.Column(
            "harness_config",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column(
        "search_replay_runs",
        sa.Column(
            "harness_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'default_v1'"),
        ),
    )
    op.add_column(
        "search_replay_runs",
        sa.Column(
            "reranker_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'linear_feature_reranker'"),
        ),
    )
    op.add_column(
        "search_replay_runs",
        sa.Column(
            "reranker_version",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
    )
    op.add_column(
        "search_replay_runs",
        sa.Column(
            "retrieval_profile_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'default_v1'"),
        ),
    )
    op.add_column(
        "search_replay_runs",
        sa.Column(
            "harness_config",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_table(
        "chat_answer_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("search_request_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column(
            "used_fallback",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("warning", sa.Text(), nullable=True),
        sa.Column(
            "citations",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "harness_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'default_v1'"),
        ),
        sa.Column("reranker_name", sa.Text(), nullable=False),
        sa.Column(
            "reranker_version",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
        sa.Column(
            "retrieval_profile_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'default_v1'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode IN ('keyword', 'semantic', 'hybrid')",
            name="ck_chat_answer_records_mode",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_answer_records_search_request_id",
        "chat_answer_records",
        ["search_request_id"],
    )
    op.create_index(
        "ix_chat_answer_records_created_at",
        "chat_answer_records",
        ["created_at"],
    )

    op.create_table(
        "chat_answer_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chat_answer_id", sa.Uuid(), nullable=False),
        sa.Column("feedback_type", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "feedback_type IN ('helpful', 'unhelpful', 'unsupported', 'incomplete')",
            name="ck_chat_answer_feedback_type",
        ),
        sa.ForeignKeyConstraint(
            ["chat_answer_id"],
            ["chat_answer_records.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_answer_feedback_answer_id",
        "chat_answer_feedback",
        ["chat_answer_id"],
    )
    op.create_index(
        "ix_chat_answer_feedback_feedback_type",
        "chat_answer_feedback",
        ["feedback_type"],
    )
    op.create_index(
        "ix_chat_answer_feedback_created_at",
        "chat_answer_feedback",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_answer_feedback_created_at", table_name="chat_answer_feedback")
    op.drop_index("ix_chat_answer_feedback_feedback_type", table_name="chat_answer_feedback")
    op.drop_index("ix_chat_answer_feedback_answer_id", table_name="chat_answer_feedback")
    op.drop_table("chat_answer_feedback")

    op.drop_index("ix_chat_answer_records_created_at", table_name="chat_answer_records")
    op.drop_index("ix_chat_answer_records_search_request_id", table_name="chat_answer_records")
    op.drop_table("chat_answer_records")

    op.drop_column("search_replay_runs", "harness_config")
    op.drop_column("search_replay_runs", "retrieval_profile_name")
    op.drop_column("search_replay_runs", "reranker_version")
    op.drop_column("search_replay_runs", "reranker_name")
    op.drop_column("search_replay_runs", "harness_name")

    op.drop_column("search_requests", "harness_config")
    op.drop_column("search_requests", "retrieval_profile_name")
    op.drop_column("search_requests", "reranker_version")
    op.drop_column("search_requests", "harness_name")
