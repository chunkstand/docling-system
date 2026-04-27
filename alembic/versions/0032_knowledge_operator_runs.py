"""add knowledge operator run evidence ledger

Revision ID: 0032_knowledge_operator_runs
Revises: 0031_eval_failure_cases
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0032_knowledge_operator_runs"
down_revision: str | Sequence[str] | None = "0031_eval_failure_cases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_operator_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_operator_run_id", sa.UUID(), nullable=True),
        sa.Column("operator_kind", sa.Text(), nullable=False),
        sa.Column("operator_name", sa.Text(), nullable=False),
        sa.Column("operator_version", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'completed'"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("search_request_id", sa.UUID(), nullable=True),
        sa.Column("search_harness_evaluation_id", sa.UUID(), nullable=True),
        sa.Column("agent_task_id", sa.UUID(), nullable=True),
        sa.Column("agent_task_attempt_id", sa.UUID(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("prompt_sha256", sa.Text(), nullable=True),
        sa.Column("config_sha256", sa.Text(), nullable=True),
        sa.Column("input_sha256", sa.Text(), nullable=True),
        sa.Column("output_sha256", sa.Text(), nullable=True),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "operator_kind IN ("
            "'parse', 'embed', 'retrieve', 'rerank', 'judge', "
            "'generate', 'verify', 'export', 'orchestrate'"
            ")",
            name="ck_knowledge_operator_runs_operator_kind",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed', 'skipped')",
            name="ck_knowledge_operator_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_attempt_id"],
            ["agent_task_attempts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["agent_task_id"], ["agent_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["parent_operator_run_id"],
            ["knowledge_operator_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["search_harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["search_request_id"], ["search_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_operator_runs_agent_task_id",
        "knowledge_operator_runs",
        ["agent_task_id"],
    )
    op.create_index(
        "ix_knowledge_operator_runs_created_at",
        "knowledge_operator_runs",
        ["created_at"],
    )
    op.create_index(
        "ix_knowledge_operator_runs_kind_created_at",
        "knowledge_operator_runs",
        ["operator_kind", "created_at"],
    )
    op.create_index(
        "ix_knowledge_operator_runs_parent_id",
        "knowledge_operator_runs",
        ["parent_operator_run_id"],
    )
    op.create_index(
        "ix_knowledge_operator_runs_search_request_id",
        "knowledge_operator_runs",
        ["search_request_id"],
    )

    op.create_table(
        "knowledge_operator_inputs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("operator_run_id", sa.UUID(), nullable=False),
        sa.Column("input_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("input_kind", sa.Text(), nullable=False),
        sa.Column("source_table", sa.Text(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("artifact_sha256", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["operator_run_id"],
            ["knowledge_operator_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_operator_inputs_operator_run_id",
        "knowledge_operator_inputs",
        ["operator_run_id"],
    )
    op.create_index(
        "ix_knowledge_operator_inputs_source",
        "knowledge_operator_inputs",
        ["source_table", "source_id"],
    )

    op.create_table(
        "knowledge_operator_outputs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("operator_run_id", sa.UUID(), nullable=False),
        sa.Column("output_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("output_kind", sa.Text(), nullable=False),
        sa.Column("target_table", sa.Text(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("artifact_sha256", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["operator_run_id"],
            ["knowledge_operator_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_operator_outputs_operator_run_id",
        "knowledge_operator_outputs",
        ["operator_run_id"],
    )
    op.create_index(
        "ix_knowledge_operator_outputs_target",
        "knowledge_operator_outputs",
        ["target_table", "target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_operator_outputs_target", table_name="knowledge_operator_outputs")
    op.drop_index(
        "ix_knowledge_operator_outputs_operator_run_id",
        table_name="knowledge_operator_outputs",
    )
    op.drop_table("knowledge_operator_outputs")
    op.drop_index("ix_knowledge_operator_inputs_source", table_name="knowledge_operator_inputs")
    op.drop_index(
        "ix_knowledge_operator_inputs_operator_run_id",
        table_name="knowledge_operator_inputs",
    )
    op.drop_table("knowledge_operator_inputs")
    op.drop_index(
        "ix_knowledge_operator_runs_search_request_id",
        table_name="knowledge_operator_runs",
    )
    op.drop_index("ix_knowledge_operator_runs_parent_id", table_name="knowledge_operator_runs")
    op.drop_index(
        "ix_knowledge_operator_runs_kind_created_at",
        table_name="knowledge_operator_runs",
    )
    op.drop_index("ix_knowledge_operator_runs_created_at", table_name="knowledge_operator_runs")
    op.drop_index(
        "ix_knowledge_operator_runs_agent_task_id",
        table_name="knowledge_operator_runs",
    )
    op.drop_table("knowledge_operator_runs")
