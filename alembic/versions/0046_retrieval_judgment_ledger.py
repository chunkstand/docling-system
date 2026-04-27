"""add retrieval judgment learning ledger

Revision ID: 0046_retrieval_judgment_ledger
Revises: 0045_semantic_governance
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0046_retrieval_judgment_ledger"
down_revision: str | Sequence[str] | None = "0045_semantic_governance"
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
    "'retrieval_training_run_materialized'"
    ")"
)

LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'technical_report_prov_export_frozen'"
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
        "retrieval_judgment_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("set_name", sa.Text(), nullable=False),
        sa.Column("set_kind", sa.Text(), server_default=sa.text("'mixed'"), nullable=False),
        sa.Column(
            "source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("source_limit", sa.Integer(), nullable=False),
        sa.Column(
            "criteria",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("judgment_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("positive_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("negative_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("missing_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "hard_negative_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("payload_sha256", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "set_kind IN ('feedback', 'replay', 'mixed', 'training')",
            name="ck_retrieval_judgment_sets_set_kind",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("set_name", name="uq_retrieval_judgment_sets_set_name"),
    )
    op.create_index(
        "ix_retrieval_judgment_sets_created_at",
        "retrieval_judgment_sets",
        ["created_at"],
    )
    op.create_index(
        "ix_retrieval_judgment_sets_payload_sha",
        "retrieval_judgment_sets",
        ["payload_sha256"],
    )
    op.create_index(
        "ix_retrieval_judgment_sets_set_kind_created",
        "retrieval_judgment_sets",
        ["set_kind", "created_at"],
    )

    op.create_table(
        "retrieval_judgments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgment_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgment_kind", sa.Text(), nullable=False),
        sa.Column("judgment_label", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_feedback_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_replay_query_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_replay_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evaluation_query_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_search_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_request_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result_rank", sa.Integer(), nullable=True),
        sa.Column("result_type", sa.Text(), nullable=True),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("expected_result_type", sa.Text(), nullable=True),
        sa.Column("expected_top_n", sa.Integer(), nullable=True),
        sa.Column("harness_name", sa.Text(), nullable=True),
        sa.Column("reranker_name", sa.Text(), nullable=True),
        sa.Column("reranker_version", sa.Text(), nullable=True),
        sa.Column("retrieval_profile_name", sa.Text(), nullable=True),
        sa.Column(
            "rerank_features",
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
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("deduplication_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "judgment_kind IN ('positive', 'negative', 'missing')",
            name="ck_retrieval_judgments_kind",
        ),
        sa.CheckConstraint(
            "source_type IN ('feedback', 'replay')",
            name="ck_retrieval_judgments_source_type",
        ),
        sa.CheckConstraint(
            "result_type IS NULL OR result_type IN ('chunk', 'table')",
            name="ck_retrieval_judgments_result_type",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_query_id"],
            ["document_run_evaluation_queries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["judgment_set_id"],
            ["retrieval_judgment_sets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["search_feedback_id"],
            ["search_feedback.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_replay_query_id"],
            ["search_replay_queries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_replay_run_id"],
            ["search_replay_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_result_id"],
            ["search_request_results.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_key", name="uq_retrieval_judgments_dedup_key"),
    )
    op.create_index(
        "ix_retrieval_judgments_created_at",
        "retrieval_judgments",
        ["created_at"],
    )
    op.create_index(
        "ix_retrieval_judgments_feedback",
        "retrieval_judgments",
        ["search_feedback_id"],
    )
    op.create_index(
        "ix_retrieval_judgments_replay_query",
        "retrieval_judgments",
        ["search_replay_query_id"],
    )
    op.create_index(
        "ix_retrieval_judgments_result",
        "retrieval_judgments",
        ["result_type", "result_id"],
    )
    op.create_index(
        "ix_retrieval_judgments_search_request",
        "retrieval_judgments",
        ["search_request_id"],
    )
    op.create_index(
        "ix_retrieval_judgments_search_result",
        "retrieval_judgments",
        ["search_request_result_id"],
    )
    op.create_index(
        "ix_retrieval_judgments_set_kind",
        "retrieval_judgments",
        ["judgment_set_id", "judgment_kind"],
    )
    op.create_index(
        "ix_retrieval_judgments_source",
        "retrieval_judgments",
        ["source_type", "source_ref_id"],
    )
    op.create_index(
        "ix_retrieval_judgments_source_request",
        "retrieval_judgments",
        ["source_search_request_id"],
    )

    op.create_table(
        "retrieval_hard_negatives",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgment_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("positive_judgment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hard_negative_kind", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_feedback_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_replay_query_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_request_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result_rank", sa.Integer(), nullable=True),
        sa.Column("result_type", sa.Text(), nullable=True),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "rerank_features",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("deduplication_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "hard_negative_kind IN ("
            "'explicit_irrelevant', "
            "'missing_expected', "
            "'failed_replay_top_result', "
            "'wrong_result_type', "
            "'no_answer_returned'"
            ")",
            name="ck_retrieval_hard_negatives_kind",
        ),
        sa.CheckConstraint(
            "source_type IN ('feedback', 'replay')",
            name="ck_retrieval_hard_negatives_source_type",
        ),
        sa.CheckConstraint(
            "result_type IS NULL OR result_type IN ('chunk', 'table')",
            name="ck_retrieval_hard_negatives_result_type",
        ),
        sa.ForeignKeyConstraint(
            ["judgment_id"],
            ["retrieval_judgments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["judgment_set_id"],
            ["retrieval_judgment_sets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["positive_judgment_id"],
            ["retrieval_judgments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_feedback_id"],
            ["search_feedback.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_replay_query_id"],
            ["search_replay_queries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_result_id"],
            ["search_request_results.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deduplication_key",
            name="uq_retrieval_hard_negatives_dedup_key",
        ),
    )
    op.create_index(
        "ix_retrieval_hard_negatives_created_at",
        "retrieval_hard_negatives",
        ["created_at"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_feedback",
        "retrieval_hard_negatives",
        ["search_feedback_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_judgment",
        "retrieval_hard_negatives",
        ["judgment_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_positive_judgment",
        "retrieval_hard_negatives",
        ["positive_judgment_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_replay_query",
        "retrieval_hard_negatives",
        ["search_replay_query_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_request",
        "retrieval_hard_negatives",
        ["search_request_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_result",
        "retrieval_hard_negatives",
        ["result_type", "result_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_search_result",
        "retrieval_hard_negatives",
        ["search_request_result_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_set_kind",
        "retrieval_hard_negatives",
        ["judgment_set_id", "hard_negative_kind"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_source",
        "retrieval_hard_negatives",
        ["source_type", "source_ref_id"],
    )

    op.create_table(
        "retrieval_training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgment_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "run_kind",
            sa.Text(),
            server_default=sa.text("'materialized_training_dataset'"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), server_default=sa.text("'completed'"), nullable=False),
        sa.Column("search_harness_evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_harness_release_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("semantic_governance_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("training_dataset_sha256", sa.Text(), nullable=False),
        sa.Column(
            "training_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("example_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("positive_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("negative_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("missing_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "hard_negative_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "run_kind IN ('materialized_training_dataset')",
            name="ck_retrieval_training_runs_run_kind",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_retrieval_training_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["judgment_set_id"],
            ["retrieval_judgment_sets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_evaluation_id"],
            ["search_harness_evaluations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_release_id"],
            ["search_harness_releases.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_governance_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_retrieval_training_runs_created_at",
        "retrieval_training_runs",
        ["created_at"],
    )
    op.create_index(
        "ix_retrieval_training_runs_dataset_sha",
        "retrieval_training_runs",
        ["training_dataset_sha256"],
    )
    op.create_index(
        "ix_retrieval_training_runs_governance",
        "retrieval_training_runs",
        ["semantic_governance_event_id"],
    )
    op.create_index(
        "ix_retrieval_training_runs_judgment_set",
        "retrieval_training_runs",
        ["judgment_set_id"],
    )
    op.create_index(
        "ix_retrieval_training_runs_release",
        "retrieval_training_runs",
        ["search_harness_release_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_retrieval_training_runs_release", table_name="retrieval_training_runs")
    op.drop_index(
        "ix_retrieval_training_runs_judgment_set",
        table_name="retrieval_training_runs",
    )
    op.drop_index("ix_retrieval_training_runs_governance", table_name="retrieval_training_runs")
    op.drop_index(
        "ix_retrieval_training_runs_dataset_sha",
        table_name="retrieval_training_runs",
    )
    op.drop_index("ix_retrieval_training_runs_created_at", table_name="retrieval_training_runs")
    op.drop_table("retrieval_training_runs")

    op.drop_index("ix_retrieval_hard_negatives_source", table_name="retrieval_hard_negatives")
    op.drop_index("ix_retrieval_hard_negatives_set_kind", table_name="retrieval_hard_negatives")
    op.drop_index(
        "ix_retrieval_hard_negatives_search_result",
        table_name="retrieval_hard_negatives",
    )
    op.drop_index("ix_retrieval_hard_negatives_result", table_name="retrieval_hard_negatives")
    op.drop_index("ix_retrieval_hard_negatives_request", table_name="retrieval_hard_negatives")
    op.drop_index(
        "ix_retrieval_hard_negatives_replay_query",
        table_name="retrieval_hard_negatives",
    )
    op.drop_index(
        "ix_retrieval_hard_negatives_positive_judgment",
        table_name="retrieval_hard_negatives",
    )
    op.drop_index("ix_retrieval_hard_negatives_judgment", table_name="retrieval_hard_negatives")
    op.drop_index("ix_retrieval_hard_negatives_feedback", table_name="retrieval_hard_negatives")
    op.drop_index("ix_retrieval_hard_negatives_created_at", table_name="retrieval_hard_negatives")
    op.drop_table("retrieval_hard_negatives")

    op.drop_index("ix_retrieval_judgments_source_request", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_source", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_set_kind", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_search_result", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_search_request", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_result", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_replay_query", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_feedback", table_name="retrieval_judgments")
    op.drop_index("ix_retrieval_judgments_created_at", table_name="retrieval_judgments")
    op.drop_table("retrieval_judgments")

    op.drop_index(
        "ix_retrieval_judgment_sets_set_kind_created",
        table_name="retrieval_judgment_sets",
    )
    op.drop_index(
        "ix_retrieval_judgment_sets_payload_sha",
        table_name="retrieval_judgment_sets",
    )
    op.drop_index(
        "ix_retrieval_judgment_sets_created_at",
        table_name="retrieval_judgment_sets",
    )
    op.drop_table("retrieval_judgment_sets")
    _replace_semantic_governance_event_kind_constraint(
        LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
