"""Add claim support judge evaluations.

Revision ID: 0056_claim_support_evaluations
Revises: 0055_claim_support_judgments
Create Date: 2026-04-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0056_claim_support_evaluations"
down_revision: str | Sequence[str] | None = "0055_claim_support_judgments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_support_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operator_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evaluation_name", sa.Text(), nullable=False),
        sa.Column("fixture_set_name", sa.Text(), nullable=False),
        sa.Column("fixture_set_sha256", sa.Text(), nullable=False),
        sa.Column("judge_name", sa.Text(), nullable=False),
        sa.Column("judge_version", sa.Text(), nullable=False),
        sa.Column("min_support_score", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("gate_outcome", sa.Text(), nullable=False),
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
            "evaluation_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("evaluation_payload_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_claim_support_evaluations_status",
        ),
        sa.CheckConstraint(
            "gate_outcome IN ('passed', 'failed')",
            name="ck_claim_support_evaluations_gate_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["operator_run_id"],
            ["knowledge_operator_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claim_support_evaluations_agent_task_id",
        "claim_support_evaluations",
        ["agent_task_id"],
    )
    op.create_index(
        "ix_claim_support_evaluations_operator_run_id",
        "claim_support_evaluations",
        ["operator_run_id"],
    )
    op.create_index(
        "ix_claim_support_evaluations_created_at",
        "claim_support_evaluations",
        ["created_at"],
    )
    op.create_index(
        "ix_claim_support_evaluations_gate_created",
        "claim_support_evaluations",
        ["gate_outcome", "created_at"],
    )
    op.create_index(
        "ix_claim_support_evaluations_fixture_sha",
        "claim_support_evaluations",
        ["fixture_set_sha256"],
    )

    op.create_table(
        "claim_support_evaluation_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_index", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("hard_case_kind", sa.Text(), nullable=True),
        sa.Column("expected_verdict", sa.Text(), nullable=False),
        sa.Column("predicted_verdict", sa.Text(), nullable=False),
        sa.Column("support_score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column(
            "claim_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "support_judgment",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "failure_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "expected_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_support_evaluation_cases_expected_verdict",
        ),
        sa.CheckConstraint(
            "predicted_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_support_evaluation_cases_predicted_verdict",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["claim_support_evaluations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_id",
            "case_id",
            name="uq_claim_support_evaluation_cases_eval_case",
        ),
    )
    op.create_index(
        "ix_claim_support_evaluation_cases_eval_id",
        "claim_support_evaluation_cases",
        ["evaluation_id"],
    )
    op.create_index(
        "ix_claim_support_evaluation_cases_case_id",
        "claim_support_evaluation_cases",
        ["case_id"],
    )
    op.create_index(
        "ix_claim_support_evaluation_cases_expected",
        "claim_support_evaluation_cases",
        ["expected_verdict"],
    )
    op.create_index(
        "ix_claim_support_evaluation_cases_predicted",
        "claim_support_evaluation_cases",
        ["predicted_verdict"],
    )
    op.create_index(
        "ix_claim_support_evaluation_cases_passed",
        "claim_support_evaluation_cases",
        ["passed"],
    )
    op.create_index(
        "ix_claim_support_evaluation_cases_hard_kind",
        "claim_support_evaluation_cases",
        ["hard_case_kind"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_support_evaluation_cases_hard_kind",
        table_name="claim_support_evaluation_cases",
    )
    op.drop_index(
        "ix_claim_support_evaluation_cases_passed",
        table_name="claim_support_evaluation_cases",
    )
    op.drop_index(
        "ix_claim_support_evaluation_cases_predicted",
        table_name="claim_support_evaluation_cases",
    )
    op.drop_index(
        "ix_claim_support_evaluation_cases_expected",
        table_name="claim_support_evaluation_cases",
    )
    op.drop_index(
        "ix_claim_support_evaluation_cases_case_id",
        table_name="claim_support_evaluation_cases",
    )
    op.drop_index(
        "ix_claim_support_evaluation_cases_eval_id",
        table_name="claim_support_evaluation_cases",
    )
    op.drop_table("claim_support_evaluation_cases")

    op.drop_index(
        "ix_claim_support_evaluations_fixture_sha",
        table_name="claim_support_evaluations",
    )
    op.drop_index(
        "ix_claim_support_evaluations_gate_created",
        table_name="claim_support_evaluations",
    )
    op.drop_index(
        "ix_claim_support_evaluations_created_at",
        table_name="claim_support_evaluations",
    )
    op.drop_index(
        "ix_claim_support_evaluations_operator_run_id",
        table_name="claim_support_evaluations",
    )
    op.drop_index(
        "ix_claim_support_evaluations_agent_task_id",
        table_name="claim_support_evaluations",
    )
    op.drop_table("claim_support_evaluations")
