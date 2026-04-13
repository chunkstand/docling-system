"""add agent task substrate tables

Revision ID: 0013_agent_task_substrate
Revises: 0012_harness_chat_feedback
Create Date: 2026-04-12 23:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0013_agent_task_substrate"
down_revision = "0012_harness_chat_feedback"
branch_labels = None
depends_on = None


def _jsonb_type() -> sa.JSON:
    return sa.JSON().with_variant(
        sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
        "postgresql",
    )


def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "side_effect_level",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'read_only'"),
        ),
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("parent_task_id", sa.Uuid(), nullable=True),
        sa.Column(
            "input",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("failure_artifact_path", sa.Text(), nullable=True),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "workflow_version",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
        sa.Column("tool_version", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column(
            "model_settings",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ("
            "'blocked', 'awaiting_approval', 'queued', "
            "'processing', 'retry_wait', 'completed', 'failed'"
            ")",
            name="ck_agent_tasks_status",
        ),
        sa.CheckConstraint(
            "side_effect_level IN ('read_only', 'draft_change', 'promotable')",
            name="ck_agent_tasks_side_effect_level",
        ),
        sa.ForeignKeyConstraint(
            ["parent_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_tasks_status_priority_next_attempt_at",
        "agent_tasks",
        ["status", "priority", "next_attempt_at"],
    )
    op.create_index("ix_agent_tasks_locked_at", "agent_tasks", ["locked_at"])
    op.create_index("ix_agent_tasks_parent_task_id", "agent_tasks", ["parent_task_id"])
    op.create_index(
        "ix_agent_tasks_task_type_created_at",
        "agent_tasks",
        ["task_type", "created_at"],
    )

    op.create_table(
        "agent_task_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("depends_on_task_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "task_id <> depends_on_task_id",
            name="ck_agent_task_dependencies_not_self",
        ),
        sa.ForeignKeyConstraint(
            ["depends_on_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "depends_on_task_id",
            name="uq_agent_task_dependencies_task_depends_on",
        ),
    )
    op.create_index(
        "ix_agent_task_dependencies_depends_on_task_id",
        "agent_task_dependencies",
        ["depends_on_task_id"],
    )

    op.create_table(
        "agent_task_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=True),
        sa.Column(
            "input",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'abandoned')",
            name="ck_agent_task_attempts_status",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "attempt_number",
            name="uq_agent_task_attempts_task_attempt",
        ),
    )
    op.create_index("ix_agent_task_attempts_task_id", "agent_task_attempts", ["task_id"])
    op.create_index(
        "ix_agent_task_attempts_created_at",
        "agent_task_attempts",
        ["created_at"],
    )

    op.create_table(
        "agent_task_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=True),
        sa.Column("artifact_kind", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            _jsonb_type(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["agent_task_attempts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_task_artifacts_task_id", "agent_task_artifacts", ["task_id"])
    op.create_index(
        "ix_agent_task_artifacts_attempt_id",
        "agent_task_artifacts",
        ["attempt_id"],
    )
    op.create_index(
        "ix_agent_task_artifacts_artifact_kind",
        "agent_task_artifacts",
        ["artifact_kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_task_artifacts_artifact_kind", table_name="agent_task_artifacts")
    op.drop_index("ix_agent_task_artifacts_attempt_id", table_name="agent_task_artifacts")
    op.drop_index("ix_agent_task_artifacts_task_id", table_name="agent_task_artifacts")
    op.drop_table("agent_task_artifacts")

    op.drop_index("ix_agent_task_attempts_created_at", table_name="agent_task_attempts")
    op.drop_index("ix_agent_task_attempts_task_id", table_name="agent_task_attempts")
    op.drop_table("agent_task_attempts")

    op.drop_index(
        "ix_agent_task_dependencies_depends_on_task_id",
        table_name="agent_task_dependencies",
    )
    op.drop_table("agent_task_dependencies")

    op.drop_index("ix_agent_tasks_task_type_created_at", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_parent_task_id", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_locked_at", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_status_priority_next_attempt_at", table_name="agent_tasks")
    op.drop_table("agent_tasks")
