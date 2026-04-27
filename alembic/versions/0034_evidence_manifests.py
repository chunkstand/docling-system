"""add evidence manifests

Revision ID: 0034_evidence_manifests
Revises: 0033_evidence_package_exports
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0034_evidence_manifests"
down_revision: str | Sequence[str] | None = "0033_evidence_package_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_manifests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("manifest_kind", sa.Text(), nullable=False),
        sa.Column("agent_task_id", sa.UUID(), nullable=False),
        sa.Column("draft_task_id", sa.UUID(), nullable=True),
        sa.Column("verification_task_id", sa.UUID(), nullable=False),
        sa.Column("evidence_package_export_id", sa.UUID(), nullable=True),
        sa.Column("manifest_sha256", sa.Text(), nullable=False),
        sa.Column(
            "manifest_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_snapshot_sha256s",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "document_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "run_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "claim_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "search_request_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "operator_run_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "manifest_status",
            sa.Text(),
            server_default=sa.text("'completed'"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "manifest_kind IN ('technical_report_court_evidence')",
            name="ck_evidence_manifests_manifest_kind",
        ),
        sa.CheckConstraint(
            "manifest_status IN ('completed', 'failed')",
            name="ck_evidence_manifests_manifest_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["draft_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_package_export_id"],
            ["evidence_package_exports.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["verification_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "verification_task_id",
            "manifest_kind",
            name="uq_evidence_manifests_verification_task_kind",
        ),
    )
    op.create_index(
        "ix_evidence_manifests_agent_task_id",
        "evidence_manifests",
        ["agent_task_id"],
    )
    op.create_index(
        "ix_evidence_manifests_created_at",
        "evidence_manifests",
        ["created_at"],
    )
    op.create_index(
        "ix_evidence_manifests_draft_task_id",
        "evidence_manifests",
        ["draft_task_id"],
    )
    op.create_index(
        "ix_evidence_manifests_export_id",
        "evidence_manifests",
        ["evidence_package_export_id"],
    )
    op.create_index(
        "ix_evidence_manifests_manifest_sha256",
        "evidence_manifests",
        ["manifest_sha256"],
    )
    op.create_index(
        "ix_evidence_manifests_verification_task_id",
        "evidence_manifests",
        ["verification_task_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_manifests_verification_task_id",
        table_name="evidence_manifests",
    )
    op.drop_index(
        "ix_evidence_manifests_manifest_sha256",
        table_name="evidence_manifests",
    )
    op.drop_index(
        "ix_evidence_manifests_export_id",
        table_name="evidence_manifests",
    )
    op.drop_index(
        "ix_evidence_manifests_draft_task_id",
        table_name="evidence_manifests",
    )
    op.drop_index(
        "ix_evidence_manifests_created_at",
        table_name="evidence_manifests",
    )
    op.drop_index(
        "ix_evidence_manifests_agent_task_id",
        table_name="evidence_manifests",
    )
    op.drop_table("evidence_manifests")
