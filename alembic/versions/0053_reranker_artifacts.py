"""add retrieval reranker artifacts

Revision ID: 0053_reranker_artifacts
Revises: 0052_receipt_sem_gov
Create Date: 2026-04-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0053_reranker_artifacts"
down_revision: str | Sequence[str] | None = "0052_receipt_sem_gov"
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
    "'retrieval_learning_candidate_evaluated', "
    "'retrieval_reranker_artifact_materialized'"
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
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated'"
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
        "retrieval_reranker_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retrieval_training_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgment_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "retrieval_learning_candidate_evaluation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("search_harness_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_harness_release_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("semantic_governance_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_kind", sa.Text(), nullable=False),
        sa.Column("artifact_name", sa.Text(), nullable=False),
        sa.Column("artifact_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("gate_outcome", sa.Text(), nullable=True),
        sa.Column("baseline_harness_name", sa.Text(), nullable=False),
        sa.Column("candidate_harness_name", sa.Text(), nullable=False),
        sa.Column(
            "source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("limit", sa.Integer(), nullable=False),
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
            "feature_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "harness_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "artifact_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
            "change_impact_report",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("artifact_sha256", sa.Text(), nullable=False),
        sa.Column("change_impact_sha256", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "artifact_kind IN ('linear_feature_weight_candidate')",
            name="ck_retrieval_reranker_artifacts_kind",
        ),
        sa.CheckConstraint(
            "status IN ('evaluated', 'failed')",
            name="ck_retrieval_reranker_artifacts_status",
        ),
        sa.CheckConstraint(
            "gate_outcome IS NULL OR gate_outcome IN ('passed', 'failed', 'error')",
            name="ck_retrieval_reranker_artifacts_gate_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_training_run_id"],
            ["retrieval_training_runs.id"],
            name="fk_retrieval_reranker_artifacts_training_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["judgment_set_id"],
            ["retrieval_judgment_sets.id"],
            name="fk_retrieval_reranker_artifacts_judgment_set",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_learning_candidate_evaluation_id"],
            ["retrieval_learning_candidate_evaluations.id"],
            name="fk_retrieval_reranker_artifacts_candidate_eval",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            name="fk_retrieval_reranker_artifacts_evaluation",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_release_id"],
            ["search_harness_releases.id"],
            name="fk_retrieval_reranker_artifacts_release",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_governance_event_id"],
            ["semantic_governance_events.id"],
            name="fk_retrieval_reranker_artifacts_governance",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "retrieval_learning_candidate_evaluation_id",
            name="uq_retrieval_reranker_artifacts_candidate_eval",
        ),
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_training_created",
        "retrieval_reranker_artifacts",
        ["retrieval_training_run_id", "created_at"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_candidate_eval",
        "retrieval_reranker_artifacts",
        ["retrieval_learning_candidate_evaluation_id"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_evaluation",
        "retrieval_reranker_artifacts",
        ["search_harness_evaluation_id"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_release",
        "retrieval_reranker_artifacts",
        ["search_harness_release_id"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_governance",
        "retrieval_reranker_artifacts",
        ["semantic_governance_event_id"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_candidate_created",
        "retrieval_reranker_artifacts",
        ["candidate_harness_name", "created_at"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_gate_created",
        "retrieval_reranker_artifacts",
        ["gate_outcome", "created_at"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_artifact_sha",
        "retrieval_reranker_artifacts",
        ["artifact_sha256"],
    )
    op.create_index(
        "ix_retrieval_reranker_artifacts_impact_sha",
        "retrieval_reranker_artifacts",
        ["change_impact_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_reranker_artifacts_impact_sha",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_artifact_sha",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_gate_created",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_candidate_created",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_governance",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_release",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_evaluation",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_candidate_eval",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_index(
        "ix_retrieval_reranker_artifacts_training_created",
        table_name="retrieval_reranker_artifacts",
    )
    op.drop_table("retrieval_reranker_artifacts")
    _replace_semantic_governance_event_kind_constraint(
        LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
