"""make frozen technical report prov artifacts append-only

Revision ID: 0044_prov_artifact_immutability
Revises: 0043_search_trace_exports
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0044_prov_artifact_immutability"
down_revision: str | Sequence[str] | None = "0043_search_trace_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_frozen_agent_task_artifact_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND (
           OLD.artifact_kind = 'technical_report_prov_export'
           OR NEW.artifact_kind = 'technical_report_prov_export'
       )
    THEN
        INSERT INTO agent_task_artifact_immutability_events (
            artifact_id,
            task_id,
            event_kind,
            mutation_operation,
            frozen_artifact_kind,
            attempted_artifact_kind,
            frozen_storage_path,
            attempted_storage_path,
            frozen_payload_sha256,
            attempted_payload_sha256,
            details,
            created_at
        )
        VALUES (
            OLD.id,
            OLD.task_id,
            'mutation_blocked',
            TG_OP,
            OLD.artifact_kind,
            NEW.artifact_kind,
            OLD.storage_path,
            NEW.storage_path,
            OLD.payload #>> '{frozen_export,export_payload_sha256}',
            NEW.payload #>> '{frozen_export,export_payload_sha256}',
            jsonb_build_object(
                'reason', 'technical_report_prov_export artifacts are immutable',
                'protected_artifact_kind', 'technical_report_prov_export'
            ),
            now()
        );
        RETURN OLD;
    END IF;

    IF TG_OP = 'DELETE'
       AND OLD.artifact_kind = 'technical_report_prov_export'
    THEN
        INSERT INTO agent_task_artifact_immutability_events (
            artifact_id,
            task_id,
            event_kind,
            mutation_operation,
            frozen_artifact_kind,
            attempted_artifact_kind,
            frozen_storage_path,
            attempted_storage_path,
            frozen_payload_sha256,
            attempted_payload_sha256,
            details,
            created_at
        )
        VALUES (
            OLD.id,
            OLD.task_id,
            'mutation_blocked',
            TG_OP,
            OLD.artifact_kind,
            NULL,
            OLD.storage_path,
            NULL,
            OLD.payload #>> '{frozen_export,export_payload_sha256}',
            NULL,
            jsonb_build_object(
                'reason', 'technical_report_prov_export artifacts are immutable',
                'protected_artifact_kind', 'technical_report_prov_export'
            ),
            now()
        );
        RETURN NULL;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
"""

PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_TRIGGER_SQL = """
CREATE TRIGGER trg_agent_task_artifacts_prevent_frozen_prov_mutation
BEFORE UPDATE OR DELETE ON agent_task_artifacts
FOR EACH ROW
EXECUTE FUNCTION prevent_frozen_agent_task_artifact_mutation();
"""

PREVENT_IMMUTABILITY_EVENT_MUTATION_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_agent_task_artifact_immutability_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'agent_task_artifact_immutability_events rows are immutable'
        USING ERRCODE = 'integrity_constraint_violation';
    RETURN OLD;
END;
$$;
"""

PREVENT_IMMUTABILITY_EVENT_MUTATION_TRIGGER_SQL = """
CREATE TRIGGER trg_agent_task_artifact_immutability_events_prevent_update_delete
BEFORE UPDATE OR DELETE ON agent_task_artifact_immutability_events
FOR EACH ROW
EXECUTE FUNCTION prevent_agent_task_artifact_immutability_event_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "agent_task_artifact_immutability_events",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("event_kind", sa.Text(), nullable=False),
        sa.Column("mutation_operation", sa.Text(), nullable=False),
        sa.Column("frozen_artifact_kind", sa.Text(), nullable=True),
        sa.Column("attempted_artifact_kind", sa.Text(), nullable=True),
        sa.Column("frozen_storage_path", sa.Text(), nullable=True),
        sa.Column("attempted_storage_path", sa.Text(), nullable=True),
        sa.Column("frozen_payload_sha256", sa.Text(), nullable=True),
        sa.Column("attempted_payload_sha256", sa.Text(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_kind IN ('mutation_blocked', 'supersession_attempt')",
            name="ck_agent_artifact_immut_events_event_kind",
        ),
        sa.CheckConstraint(
            "mutation_operation IN ('UPDATE', 'DELETE', 'FREEZE_REUSE')",
            name="ck_agent_artifact_immut_events_mutation_op",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_artifact_immut_events_artifact_created",
        "agent_task_artifact_immutability_events",
        ["artifact_id", "created_at"],
    )
    op.create_index(
        "ix_agent_artifact_immut_events_task_created",
        "agent_task_artifact_immutability_events",
        ["task_id", "created_at"],
    )
    op.create_index(
        "ix_agent_artifact_immut_events_kind",
        "agent_task_artifact_immutability_events",
        ["event_kind"],
    )
    op.execute(PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_FUNCTION_SQL)
    op.execute(PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_TRIGGER_SQL)
    op.execute(PREVENT_IMMUTABILITY_EVENT_MUTATION_FUNCTION_SQL)
    op.execute(PREVENT_IMMUTABILITY_EVENT_MUTATION_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_agent_task_artifact_immutability_events_prevent_update_delete
        ON agent_task_artifact_immutability_events;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_agent_task_artifacts_prevent_frozen_prov_mutation
        ON agent_task_artifacts;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_agent_task_artifact_immutability_event_mutation();")
    op.execute("DROP FUNCTION IF EXISTS prevent_frozen_agent_task_artifact_mutation();")
    op.drop_index(
        "ix_agent_artifact_immut_events_kind",
        table_name="agent_task_artifact_immutability_events",
    )
    op.drop_index(
        "ix_agent_artifact_immut_events_task_created",
        table_name="agent_task_artifact_immutability_events",
    )
    op.drop_index(
        "ix_agent_artifact_immut_events_artifact_created",
        table_name="agent_task_artifact_immutability_events",
    )
    op.drop_table("agent_task_artifact_immutability_events")
