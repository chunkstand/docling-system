"""add durable release readiness assessments

Revision ID: 0070_release_readiness
Revises: 0069_replay_alert_learning
Create Date: 2026-04-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0070_release_readiness"
down_revision: str | Sequence[str] | None = "0069_replay_alert_learning"
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

CREATE_IMMUTABILITY_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_search_harness_release_readiness_assessment_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'search_harness_release_readiness_assessments rows are immutable'
        USING ERRCODE = 'integrity_constraint_violation';
    RETURN OLD;
END;
$$;
"""

CREATE_IMMUTABILITY_TRIGGER_SQL = """
CREATE TRIGGER trg_shr_readiness_assessments_prevent_update_delete
BEFORE UPDATE OR DELETE ON search_harness_release_readiness_assessments
FOR EACH ROW
EXECUTE FUNCTION prevent_search_harness_release_readiness_assessment_mutation();
"""


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
        "search_harness_release_readiness_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_harness_release_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("release_audit_bundle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("release_validation_receipt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("semantic_governance_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("readiness_profile", sa.Text(), nullable=False),
        sa.Column("readiness_status", sa.Text(), nullable=False),
        sa.Column("ready", sa.Boolean(), nullable=False),
        sa.Column(
            "blockers",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "blocker_details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "checks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "diagnostics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "lineage_remediation",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "readiness_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "assessment_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("readiness_payload_sha256", sa.Text(), nullable=False),
        sa.Column("assessment_payload_sha256", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "readiness_status IN ('ready', 'blocked')",
            name="ck_search_harness_release_readiness_assessments_status",
        ),
        sa.ForeignKeyConstraint(
            ["release_audit_bundle_id"],
            ["audit_bundle_exports.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["release_validation_receipt_id"],
            ["audit_bundle_validation_receipts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_release_id"],
            ["search_harness_releases.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_governance_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shr_readiness_assessments_release_created",
        "search_harness_release_readiness_assessments",
        ["search_harness_release_id", "created_at"],
    )
    op.create_index(
        "ix_shr_readiness_assessments_status_created",
        "search_harness_release_readiness_assessments",
        ["readiness_status", "created_at"],
    )
    op.create_index(
        "ix_shr_readiness_assessments_bundle_created",
        "search_harness_release_readiness_assessments",
        ["release_audit_bundle_id", "created_at"],
    )
    op.create_index(
        "ix_shr_readiness_assessments_receipt_created",
        "search_harness_release_readiness_assessments",
        ["release_validation_receipt_id", "created_at"],
    )
    op.create_index(
        "ix_shr_readiness_assessments_governance",
        "search_harness_release_readiness_assessments",
        ["semantic_governance_event_id"],
    )
    op.create_index(
        "ix_shr_readiness_assessments_payload_sha",
        "search_harness_release_readiness_assessments",
        ["assessment_payload_sha256"],
    )
    op.create_index(
        "ix_shr_readiness_assessments_readiness_sha",
        "search_harness_release_readiness_assessments",
        ["readiness_payload_sha256"],
    )
    op.execute(CREATE_IMMUTABILITY_FUNCTION_SQL)
    op.execute(CREATE_IMMUTABILITY_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_shr_readiness_assessments_prevent_update_delete
        ON search_harness_release_readiness_assessments;
        """
    )
    op.execute(
        "DROP FUNCTION IF EXISTS "
        "prevent_search_harness_release_readiness_assessment_mutation();"
    )
    op.drop_index(
        "ix_shr_readiness_assessments_readiness_sha",
        table_name="search_harness_release_readiness_assessments",
    )
    op.drop_index(
        "ix_shr_readiness_assessments_payload_sha",
        table_name="search_harness_release_readiness_assessments",
    )
    op.drop_index(
        "ix_shr_readiness_assessments_governance",
        table_name="search_harness_release_readiness_assessments",
    )
    op.drop_index(
        "ix_shr_readiness_assessments_receipt_created",
        table_name="search_harness_release_readiness_assessments",
    )
    op.drop_index(
        "ix_shr_readiness_assessments_bundle_created",
        table_name="search_harness_release_readiness_assessments",
    )
    op.drop_index(
        "ix_shr_readiness_assessments_status_created",
        table_name="search_harness_release_readiness_assessments",
    )
    op.drop_index(
        "ix_shr_readiness_assessments_release_created",
        table_name="search_harness_release_readiness_assessments",
    )
    op.drop_table("search_harness_release_readiness_assessments")
    _replace_semantic_governance_event_kind_constraint(
        LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
