"""add evidence package exports and claim derivations

Revision ID: 0033_evidence_package_exports
Revises: 0032_knowledge_operator_runs
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0033_evidence_package_exports"
down_revision: str | Sequence[str] | None = "0032_knowledge_operator_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_package_exports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("package_kind", sa.Text(), nullable=False),
        sa.Column("search_request_id", sa.UUID(), nullable=True),
        sa.Column("agent_task_id", sa.UUID(), nullable=True),
        sa.Column("agent_task_artifact_id", sa.UUID(), nullable=True),
        sa.Column("package_sha256", sa.Text(), nullable=False),
        sa.Column(
            "package_payload",
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
            "operator_run_ids",
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
            "export_status",
            sa.Text(),
            server_default=sa.text("'completed'"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "package_kind IN ('search_request', 'technical_report_claims')",
            name="ck_evidence_package_exports_package_kind",
        ),
        sa.CheckConstraint(
            "export_status IN ('completed', 'failed')",
            name="ck_evidence_package_exports_export_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["agent_task_id"], ["agent_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_package_exports_agent_task_id",
        "evidence_package_exports",
        ["agent_task_id"],
    )
    op.create_index(
        "ix_evidence_package_exports_created_at",
        "evidence_package_exports",
        ["created_at"],
    )
    op.create_index(
        "ix_evidence_package_exports_package_sha256",
        "evidence_package_exports",
        ["package_sha256"],
    )
    op.create_index(
        "ix_evidence_package_exports_search_request_id",
        "evidence_package_exports",
        ["search_request_id"],
    )

    op.create_table(
        "claim_evidence_derivations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("evidence_package_export_id", sa.UUID(), nullable=False),
        sa.Column("agent_task_id", sa.UUID(), nullable=True),
        sa.Column("claim_id", sa.Text(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=True),
        sa.Column("derivation_rule", sa.Text(), nullable=False),
        sa.Column(
            "evidence_card_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "graph_edge_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "fact_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "assertion_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_document_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_snapshot_sha256s",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("evidence_package_sha256", sa.Text(), nullable=False),
        sa.Column("derivation_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_package_export_id"],
            ["evidence_package_exports.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claim_evidence_derivations_agent_task_id",
        "claim_evidence_derivations",
        ["agent_task_id"],
    )
    op.create_index(
        "ix_claim_evidence_derivations_claim_id",
        "claim_evidence_derivations",
        ["claim_id"],
    )
    op.create_index(
        "ix_claim_evidence_derivations_derivation_sha256",
        "claim_evidence_derivations",
        ["derivation_sha256"],
    )
    op.create_index(
        "ix_claim_evidence_derivations_export_id",
        "claim_evidence_derivations",
        ["evidence_package_export_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_evidence_derivations_export_id",
        table_name="claim_evidence_derivations",
    )
    op.drop_index(
        "ix_claim_evidence_derivations_derivation_sha256",
        table_name="claim_evidence_derivations",
    )
    op.drop_index(
        "ix_claim_evidence_derivations_claim_id",
        table_name="claim_evidence_derivations",
    )
    op.drop_index(
        "ix_claim_evidence_derivations_agent_task_id",
        table_name="claim_evidence_derivations",
    )
    op.drop_table("claim_evidence_derivations")
    op.drop_index(
        "ix_evidence_package_exports_search_request_id",
        table_name="evidence_package_exports",
    )
    op.drop_index(
        "ix_evidence_package_exports_package_sha256",
        table_name="evidence_package_exports",
    )
    op.drop_index(
        "ix_evidence_package_exports_created_at",
        table_name="evidence_package_exports",
    )
    op.drop_index(
        "ix_evidence_package_exports_agent_task_id",
        table_name="evidence_package_exports",
    )
    op.drop_table("evidence_package_exports")
