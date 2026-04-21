"""add eval failure case control plane

Revision ID: 0031_eval_failure_cases
Revises: 0030_perf_indexes
Create Date: 2026-04-21 00:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0031_eval_failure_cases"
down_revision: str | Sequence[str] | None = "0030_perf_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eval_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("observation_key", sa.Text(), nullable=False),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("subject_kind", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("severity", sa.Text(), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("failure_classification", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("evaluation_id", sa.UUID(), nullable=True),
        sa.Column("evaluation_query_id", sa.UUID(), nullable=True),
        sa.Column("search_request_id", sa.UUID(), nullable=True),
        sa.Column("replay_run_id", sa.UUID(), nullable=True),
        sa.Column("harness_evaluation_id", sa.UUID(), nullable=True),
        sa.Column("agent_task_id", sa.UUID(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "surface IN ("
            "'document_evaluation', "
            "'search_request', "
            "'chat_answer', "
            "'search_replay', "
            "'harness_evaluation', "
            "'agent_task'"
            ")",
            name="ck_eval_observations_surface",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_eval_observations_severity",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'resolved', 'suppressed')",
            name="ck_eval_observations_status",
        ),
        sa.ForeignKeyConstraint(["agent_task_id"], ["agent_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["document_run_evaluations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_query_id"],
            ["document_run_evaluation_queries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["replay_run_id"], ["search_replay_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["search_request_id"], ["search_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("observation_key", name="uq_eval_observations_observation_key"),
    )
    op.create_index("ix_eval_observations_document_id", "eval_observations", ["document_id"])
    op.create_index("ix_eval_observations_evaluation_id", "eval_observations", ["evaluation_id"])
    op.create_index(
        "ix_eval_observations_search_request_id",
        "eval_observations",
        ["search_request_id"],
    )
    op.create_index(
        "ix_eval_observations_status_last_seen",
        "eval_observations",
        ["status", "last_seen_at"],
    )
    op.create_index(
        "ix_eval_observations_surface_last_seen",
        "eval_observations",
        ["surface", "last_seen_at"],
    )

    op.create_table(
        "eval_failure_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("severity", sa.Text(), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("failure_classification", sa.Text(), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("observed_behavior", sa.Text(), nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("source_observation_id", sa.UUID(), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("evaluation_id", sa.UUID(), nullable=True),
        sa.Column("evaluation_query_id", sa.UUID(), nullable=True),
        sa.Column("search_request_id", sa.UUID(), nullable=True),
        sa.Column("replay_run_id", sa.UUID(), nullable=True),
        sa.Column("harness_evaluation_id", sa.UUID(), nullable=True),
        sa.Column("agent_task_id", sa.UUID(), nullable=True),
        sa.Column(
            "recommended_next_actions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "allowed_repair_surfaces",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "blocked_repair_surfaces",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "verification_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "agent_task_payloads",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "surface IN ("
            "'document_evaluation', "
            "'search_request', "
            "'chat_answer', "
            "'search_replay', "
            "'harness_evaluation', "
            "'agent_task'"
            ")",
            name="ck_eval_failure_cases_surface",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_eval_failure_cases_severity",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'open', 'triaged', 'drafted', 'verified', 'awaiting_approval', "
            "'applied', 'rejected', 'resolved', 'suppressed'"
            ")",
            name="ck_eval_failure_cases_status",
        ),
        sa.ForeignKeyConstraint(["agent_task_id"], ["agent_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["document_run_evaluations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_query_id"],
            ["document_run_evaluation_queries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["replay_run_id"], ["search_replay_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["search_request_id"], ["search_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_observation_id"],
            ["eval_observations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_key", name="uq_eval_failure_cases_case_key"),
    )
    op.create_index("ix_eval_failure_cases_document_id", "eval_failure_cases", ["document_id"])
    op.create_index("ix_eval_failure_cases_evaluation_id", "eval_failure_cases", ["evaluation_id"])
    op.create_index(
        "ix_eval_failure_cases_search_request_id",
        "eval_failure_cases",
        ["search_request_id"],
    )
    op.create_index(
        "ix_eval_failure_cases_status_updated",
        "eval_failure_cases",
        ["status", "updated_at"],
    )
    op.create_index(
        "ix_eval_failure_cases_surface_status",
        "eval_failure_cases",
        ["surface", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_eval_failure_cases_surface_status", table_name="eval_failure_cases")
    op.drop_index("ix_eval_failure_cases_status_updated", table_name="eval_failure_cases")
    op.drop_index("ix_eval_failure_cases_search_request_id", table_name="eval_failure_cases")
    op.drop_index("ix_eval_failure_cases_evaluation_id", table_name="eval_failure_cases")
    op.drop_index("ix_eval_failure_cases_document_id", table_name="eval_failure_cases")
    op.drop_table("eval_failure_cases")
    op.drop_index("ix_eval_observations_surface_last_seen", table_name="eval_observations")
    op.drop_index("ix_eval_observations_status_last_seen", table_name="eval_observations")
    op.drop_index("ix_eval_observations_search_request_id", table_name="eval_observations")
    op.drop_index("ix_eval_observations_evaluation_id", table_name="eval_observations")
    op.drop_index("ix_eval_observations_document_id", table_name="eval_observations")
    op.drop_table("eval_observations")
