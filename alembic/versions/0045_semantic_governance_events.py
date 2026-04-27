"""add semantic governance ledger events

Revision ID: 0045_semantic_governance
Revises: 0044_prov_artifact_immutability
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0045_semantic_governance"
down_revision: str | Sequence[str] | None = "0044_prov_artifact_immutability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PREVENT_SEMANTIC_GOVERNANCE_EVENT_MUTATION_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_semantic_governance_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'semantic_governance_events rows are immutable'
        USING ERRCODE = 'integrity_constraint_violation';
    RETURN OLD;
END;
$$;
"""

PREVENT_SEMANTIC_GOVERNANCE_EVENT_MUTATION_TRIGGER_SQL = """
CREATE TRIGGER trg_semantic_governance_events_prevent_update_delete
BEFORE UPDATE OR DELETE ON semantic_governance_events
FOR EACH ROW
EXECUTE FUNCTION prevent_semantic_governance_event_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "semantic_governance_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_sequence", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("event_kind", sa.Text(), nullable=False),
        sa.Column("governance_scope", sa.Text(), nullable=False),
        sa.Column("subject_table", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("ontology_snapshot_id", sa.UUID(), nullable=True),
        sa.Column("semantic_graph_snapshot_id", sa.UUID(), nullable=True),
        sa.Column("search_harness_evaluation_id", sa.UUID(), nullable=True),
        sa.Column("search_harness_release_id", sa.UUID(), nullable=True),
        sa.Column("evidence_manifest_id", sa.UUID(), nullable=True),
        sa.Column("evidence_package_export_id", sa.UUID(), nullable=True),
        sa.Column("agent_task_artifact_id", sa.UUID(), nullable=True),
        sa.Column("previous_event_id", sa.UUID(), nullable=True),
        sa.Column("previous_event_hash", sa.Text(), nullable=True),
        sa.Column("receipt_sha256", sa.Text(), nullable=True),
        sa.Column("payload_sha256", sa.Text(), nullable=False),
        sa.Column("event_hash", sa.Text(), nullable=False),
        sa.Column("deduplication_key", sa.Text(), nullable=False),
        sa.Column(
            "event_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_kind IN ("
            "'ontology_snapshot_recorded', "
            "'ontology_snapshot_activated', "
            "'semantic_graph_snapshot_recorded', "
            "'semantic_graph_snapshot_activated', "
            "'search_harness_release_recorded', "
            "'technical_report_prov_export_frozen'"
            ")",
            name="ck_semantic_governance_events_event_kind",
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_manifest_id"],
            ["evidence_manifests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_package_export_id"],
            ["evidence_package_exports.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ontology_snapshot_id"],
            ["semantic_ontology_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["previous_event_id"],
            ["semantic_governance_events.id"],
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
            ["semantic_graph_snapshot_id"],
            ["semantic_graph_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deduplication_key",
            name="uq_semantic_governance_events_dedup_key",
        ),
        sa.UniqueConstraint(
            "event_sequence",
            name="uq_semantic_governance_events_sequence",
        ),
    )
    op.create_index(
        "ix_semantic_governance_events_scope_created",
        "semantic_governance_events",
        ["governance_scope", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_kind_created",
        "semantic_governance_events",
        ["event_kind", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_subject",
        "semantic_governance_events",
        ["subject_table", "subject_id"],
    )
    op.create_index(
        "ix_semantic_governance_events_task_created",
        "semantic_governance_events",
        ["task_id", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_ontology",
        "semantic_governance_events",
        ["ontology_snapshot_id", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_graph",
        "semantic_governance_events",
        ["semantic_graph_snapshot_id", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_release",
        "semantic_governance_events",
        ["search_harness_release_id", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_manifest",
        "semantic_governance_events",
        ["evidence_manifest_id", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_artifact",
        "semantic_governance_events",
        ["agent_task_artifact_id", "created_at"],
    )
    op.create_index(
        "ix_semantic_governance_events_receipt_sha",
        "semantic_governance_events",
        ["receipt_sha256"],
    )
    op.create_index(
        "ix_semantic_governance_events_payload_sha",
        "semantic_governance_events",
        ["payload_sha256"],
    )
    op.create_index(
        "ix_semantic_governance_events_event_hash",
        "semantic_governance_events",
        ["event_hash"],
    )
    op.execute(PREVENT_SEMANTIC_GOVERNANCE_EVENT_MUTATION_FUNCTION_SQL)
    op.execute(PREVENT_SEMANTIC_GOVERNANCE_EVENT_MUTATION_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_semantic_governance_events_prevent_update_delete
        ON semantic_governance_events;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_semantic_governance_event_mutation();")
    op.drop_index(
        "ix_semantic_governance_events_event_hash",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_payload_sha",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_receipt_sha",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_artifact",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_manifest",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_release",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_graph",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_ontology",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_task_created",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_subject",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_kind_created",
        table_name="semantic_governance_events",
    )
    op.drop_index(
        "ix_semantic_governance_events_scope_created",
        table_name="semantic_governance_events",
    )
    op.drop_table("semantic_governance_events")
