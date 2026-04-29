"""add technical report release readiness DB gates

Revision ID: 0071_tr_readiness_gate
Revises: 0070_release_readiness
Create Date: 2026-04-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0071_tr_readiness_gate"
down_revision: str | Sequence[str] | None = "0070_release_readiness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'search_harness_release_readiness_assessed', "
    "'technical_report_prov_export_frozen', "
    "'technical_report_readiness_db_gate_recorded', "
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated', "
    "'retrieval_reranker_artifact_materialized', "
    "'claim_support_policy_activated', "
    "'claim_support_policy_impact_replay_closed', "
    "'claim_support_policy_impact_replay_escalated', "
    "'claim_support_policy_impact_fixture_promoted', "
    "'claim_support_replay_alert_fixture_coverage_waiver_closed', "
    "'claim_support_replay_alert_fixture_corpus_snapshot_activated'"
    ")"
)

LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'search_harness_release_readiness_assessed', "
    "'technical_report_prov_export_frozen', "
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated', "
    "'retrieval_reranker_artifact_materialized', "
    "'claim_support_policy_activated', "
    "'claim_support_policy_impact_replay_closed', "
    "'claim_support_policy_impact_replay_escalated', "
    "'claim_support_policy_impact_fixture_promoted', "
    "'claim_support_replay_alert_fixture_coverage_waiver_closed', "
    "'claim_support_replay_alert_fixture_corpus_snapshot_activated'"
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
        "technical_report_release_readiness_db_gates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "technical_report_verification_task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_verification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_verification_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("harness_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_manifest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prov_export_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("semantic_governance_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("check_key", sa.Text(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=True),
        sa.Column("coverage_complete", sa.Boolean(), nullable=False),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("source_search_request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("verified_request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "source_search_request_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "verified_request_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "missing_expected_request_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "unexpected_verified_request_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "gate_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("gate_payload_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "check_key = 'release_readiness_assessment_db_integrity'",
            name="ck_tr_readiness_db_gates_check_key",
        ),
        sa.CheckConstraint(
            "source_search_request_count >= 0 "
            "AND verified_request_count >= 0 "
            "AND failure_count >= 0",
            name="ck_tr_readiness_db_gates_nonnegative_counts",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_manifest_id"],
            ["evidence_manifests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["harness_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["prov_export_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_governance_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_verification_id"],
            ["agent_task_verifications.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_verification_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["technical_report_verification_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "technical_report_verification_task_id",
            name="uq_tr_readiness_db_gates_verification_task",
        ),
    )
    op.create_index(
        "ix_tr_readiness_db_gates_verification_task",
        "technical_report_release_readiness_db_gates",
        ["technical_report_verification_task_id"],
    )
    op.create_index(
        "ix_tr_readiness_db_gates_source_verification",
        "technical_report_release_readiness_db_gates",
        ["source_verification_id"],
    )
    op.create_index(
        "ix_tr_readiness_db_gates_harness_task",
        "technical_report_release_readiness_db_gates",
        ["harness_task_id"],
    )
    op.create_index(
        "ix_tr_readiness_db_gates_manifest",
        "technical_report_release_readiness_db_gates",
        ["evidence_manifest_id"],
    )
    op.create_index(
        "ix_tr_readiness_db_gates_prov_artifact",
        "technical_report_release_readiness_db_gates",
        ["prov_export_artifact_id"],
    )
    op.create_index(
        "ix_tr_readiness_db_gates_governance",
        "technical_report_release_readiness_db_gates",
        ["semantic_governance_event_id"],
    )
    op.create_index(
        "ix_tr_readiness_db_gates_payload_sha",
        "technical_report_release_readiness_db_gates",
        ["gate_payload_sha256"],
    )
    op.create_index(
        "ix_tr_readiness_db_gates_created",
        "technical_report_release_readiness_db_gates",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tr_readiness_db_gates_created",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_index(
        "ix_tr_readiness_db_gates_payload_sha",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_index(
        "ix_tr_readiness_db_gates_governance",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_index(
        "ix_tr_readiness_db_gates_prov_artifact",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_index(
        "ix_tr_readiness_db_gates_manifest",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_index(
        "ix_tr_readiness_db_gates_harness_task",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_index(
        "ix_tr_readiness_db_gates_source_verification",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_index(
        "ix_tr_readiness_db_gates_verification_task",
        table_name="technical_report_release_readiness_db_gates",
    )
    op.drop_table("technical_report_release_readiness_db_gates")
    op.execute(
        """
        UPDATE semantic_governance_events
        SET previous_event_id = NULL, previous_event_hash = NULL
        WHERE previous_event_id IN (
            SELECT id
            FROM semantic_governance_events
            WHERE event_kind = 'technical_report_readiness_db_gate_recorded'
        );
        """
    )
    op.execute(
        """
        DELETE FROM semantic_governance_events
        WHERE event_kind = 'technical_report_readiness_db_gate_recorded';
        """
    )
    _replace_semantic_governance_event_kind_constraint(
        LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
