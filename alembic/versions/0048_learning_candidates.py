"""add retrieval learning candidate evaluations

Revision ID: 0048_learning_candidates
Revises: 0047_retrieval_learning_trace
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0048_learning_candidates"
down_revision: str | Sequence[str] | None = "0047_retrieval_learning_trace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'technical_report_prov_export_frozen', "
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated'"
    ")"
)

LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'technical_report_prov_export_frozen', "
    "'retrieval_training_run_materialized'"
    ")"
)


def _replace_semantic_governance_event_kind_constraint(sql_text: str) -> None:
    op.drop_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        sql_text,
    )


def upgrade() -> None:
    _replace_semantic_governance_event_kind_constraint(
        SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
    op.create_table(
        "retrieval_learning_candidate_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retrieval_training_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgment_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_harness_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_harness_release_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("semantic_governance_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("training_dataset_sha256", sa.Text(), nullable=False),
        sa.Column(
            "training_example_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("positive_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("negative_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("missing_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("hard_negative_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("baseline_harness_name", sa.Text(), nullable=False),
        sa.Column("candidate_harness_name", sa.Text(), nullable=False),
        sa.Column(
            "source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("gate_outcome", sa.Text(), nullable=True),
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
            "evaluation_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "release_snapshot",
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
        sa.Column("learning_package_sha256", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_retrieval_learning_candidate_evaluations_status",
        ),
        sa.CheckConstraint(
            "gate_outcome IS NULL OR gate_outcome IN ('passed', 'failed', 'error')",
            name="ck_retrieval_learning_candidate_evaluations_gate_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_training_run_id"],
            ["retrieval_training_runs.id"],
            name="fk_retrieval_learning_candidate_training_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["judgment_set_id"],
            ["retrieval_judgment_sets.id"],
            name="fk_retrieval_learning_candidate_judgment_set",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            name="fk_retrieval_learning_candidate_evaluation",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_release_id"],
            ["search_harness_releases.id"],
            name="fk_retrieval_learning_candidate_release",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_governance_event_id"],
            ["semantic_governance_events.id"],
            name="fk_retrieval_learning_candidate_governance",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "retrieval_training_run_id",
            "search_harness_evaluation_id",
            name="uq_retrieval_learning_candidate_training_eval",
        ),
    )
    op.create_index(
        "ix_retrieval_learning_candidate_training",
        "retrieval_learning_candidate_evaluations",
        ["retrieval_training_run_id", "created_at"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_judgment_set",
        "retrieval_learning_candidate_evaluations",
        ["judgment_set_id", "created_at"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_evaluation",
        "retrieval_learning_candidate_evaluations",
        ["search_harness_evaluation_id"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_release",
        "retrieval_learning_candidate_evaluations",
        ["search_harness_release_id"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_governance",
        "retrieval_learning_candidate_evaluations",
        ["semantic_governance_event_id"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_dataset_sha",
        "retrieval_learning_candidate_evaluations",
        ["training_dataset_sha256"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_harness_created",
        "retrieval_learning_candidate_evaluations",
        ["candidate_harness_name", "created_at"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_outcome_created",
        "retrieval_learning_candidate_evaluations",
        ["gate_outcome", "created_at"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_package_sha",
        "retrieval_learning_candidate_evaluations",
        ["learning_package_sha256"],
    )
    op.create_index(
        "ix_retrieval_learning_candidate_created_at",
        "retrieval_learning_candidate_evaluations",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_learning_candidate_created_at",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_package_sha",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_outcome_created",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_harness_created",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_dataset_sha",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_governance",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_release",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_evaluation",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_training",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_index(
        "ix_retrieval_learning_candidate_judgment_set",
        table_name="retrieval_learning_candidate_evaluations",
    )
    op.drop_table("retrieval_learning_candidate_evaluations")
    _replace_semantic_governance_event_kind_constraint(
        LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
