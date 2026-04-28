"""Add claim support replay fixture corpus snapshots.

Revision ID: 0067_claim_replay_fixture_corpus
Revises: 0066_claim_waiver_ledger
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0067_claim_replay_fixture_corpus"
down_revision: str | Sequence[str] | None = "0066_claim_waiver_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_support_replay_alert_fixture_corpus_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_name", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("snapshot_sha256", sa.Text(), nullable=False),
        sa.Column("fixture_count", sa.Integer(), nullable=False),
        sa.Column("promotion_event_count", sa.Integer(), nullable=False),
        sa.Column("promotion_fixture_set_count", sa.Integer(), nullable=False),
        sa.Column(
            "invalid_promotion_event_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "source_promotion_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_promotion_artifact_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_promotion_receipt_sha256s",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_fixture_set_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_fixture_set_sha256s",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_escalation_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "invalid_promotion_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'superseded')",
            name="ck_cs_replay_fixture_corpus_snapshots_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_sha256",
            name="uq_cs_replay_fixture_corpus_snapshots_sha",
        ),
    )
    op.create_index(
        "ix_cs_replay_fixture_corpus_snapshots_status_created",
        "claim_support_replay_alert_fixture_corpus_snapshots",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_cs_replay_fixture_corpus_snapshots_sha",
        "claim_support_replay_alert_fixture_corpus_snapshots",
        ["snapshot_sha256"],
    )

    op.create_table(
        "claim_support_replay_alert_fixture_corpus_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("case_identity_sha256", sa.Text(), nullable=False),
        sa.Column("fixture_sha256", sa.Text(), nullable=False),
        sa.Column(
            "fixture",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("fixture_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("promotion_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("promotion_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("promotion_receipt_sha256", sa.Text(), nullable=True),
        sa.Column(
            "source_change_impact_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_escalation_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "replay_alert_source",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["fixture_set_id"],
            ["claim_support_fixture_sets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["promotion_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["promotion_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["claim_support_replay_alert_fixture_corpus_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "case_identity_sha256",
            name="uq_cs_replay_fixture_corpus_rows_snapshot_identity",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "row_index",
            name="uq_cs_replay_fixture_corpus_rows_snapshot_index",
        ),
    )
    op.create_index(
        "ix_cs_replay_fixture_corpus_rows_snapshot",
        "claim_support_replay_alert_fixture_corpus_rows",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_cs_replay_fixture_corpus_rows_case",
        "claim_support_replay_alert_fixture_corpus_rows",
        ["case_id"],
    )
    op.create_index(
        "ix_cs_replay_fixture_corpus_rows_fixture_sha",
        "claim_support_replay_alert_fixture_corpus_rows",
        ["fixture_sha256"],
    )
    op.create_index(
        "ix_cs_replay_fixture_corpus_rows_promotion",
        "claim_support_replay_alert_fixture_corpus_rows",
        ["promotion_event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_replay_fixture_corpus_rows_promotion",
        table_name="claim_support_replay_alert_fixture_corpus_rows",
    )
    op.drop_index(
        "ix_cs_replay_fixture_corpus_rows_fixture_sha",
        table_name="claim_support_replay_alert_fixture_corpus_rows",
    )
    op.drop_index(
        "ix_cs_replay_fixture_corpus_rows_case",
        table_name="claim_support_replay_alert_fixture_corpus_rows",
    )
    op.drop_index(
        "ix_cs_replay_fixture_corpus_rows_snapshot",
        table_name="claim_support_replay_alert_fixture_corpus_rows",
    )
    op.drop_table("claim_support_replay_alert_fixture_corpus_rows")

    op.drop_index(
        "ix_cs_replay_fixture_corpus_snapshots_sha",
        table_name="claim_support_replay_alert_fixture_corpus_snapshots",
    )
    op.drop_index(
        "ix_cs_replay_fixture_corpus_snapshots_status_created",
        table_name="claim_support_replay_alert_fixture_corpus_snapshots",
    )
    op.drop_table("claim_support_replay_alert_fixture_corpus_snapshots")
