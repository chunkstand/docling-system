"""persist search evidence package trace graphs

Revision ID: 0043_search_trace_exports
Revises: 0042_multivector_hash_required
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0043_search_trace_exports"
down_revision: str | Sequence[str] | None = "0042_multivector_hash_required"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_package_exports",
        sa.Column("trace_sha256", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_evidence_package_exports_trace_sha256",
        "evidence_package_exports",
        ["trace_sha256"],
    )

    op.add_column(
        "evidence_trace_nodes",
        sa.Column("evidence_package_export_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "evidence_trace_edges",
        sa.Column("evidence_package_export_id", sa.UUID(), nullable=True),
    )

    op.alter_column("evidence_trace_nodes", "evidence_manifest_id", nullable=True)
    op.alter_column("evidence_trace_edges", "evidence_manifest_id", nullable=True)

    op.create_foreign_key(
        "fk_evidence_trace_nodes_export_id",
        "evidence_trace_nodes",
        "evidence_package_exports",
        ["evidence_package_export_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_evidence_trace_edges_export_id",
        "evidence_trace_edges",
        "evidence_package_exports",
        ["evidence_package_export_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_evidence_trace_nodes_export_id",
        "evidence_trace_nodes",
        ["evidence_package_export_id"],
    )
    op.create_index(
        "ix_evidence_trace_edges_export_id",
        "evidence_trace_edges",
        ["evidence_package_export_id"],
    )
    op.create_unique_constraint(
        "uq_evidence_trace_nodes_export_node_key",
        "evidence_trace_nodes",
        ["evidence_package_export_id", "node_key"],
    )
    op.create_unique_constraint(
        "uq_evidence_trace_edges_export_edge_key",
        "evidence_trace_edges",
        ["evidence_package_export_id", "edge_key"],
    )
    op.create_check_constraint(
        "ck_evidence_trace_nodes_single_owner",
        "evidence_trace_nodes",
        "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
        "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_evidence_trace_edges_single_owner",
        "evidence_trace_edges",
        "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
        "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_evidence_trace_edges_single_owner",
        "evidence_trace_edges",
        type_="check",
    )
    op.drop_constraint(
        "ck_evidence_trace_nodes_single_owner",
        "evidence_trace_nodes",
        type_="check",
    )
    op.drop_constraint(
        "uq_evidence_trace_edges_export_edge_key",
        "evidence_trace_edges",
        type_="unique",
    )
    op.drop_constraint(
        "uq_evidence_trace_nodes_export_node_key",
        "evidence_trace_nodes",
        type_="unique",
    )
    op.drop_index("ix_evidence_trace_edges_export_id", table_name="evidence_trace_edges")
    op.drop_index("ix_evidence_trace_nodes_export_id", table_name="evidence_trace_nodes")
    op.drop_constraint(
        "fk_evidence_trace_edges_export_id",
        "evidence_trace_edges",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_evidence_trace_nodes_export_id",
        "evidence_trace_nodes",
        type_="foreignkey",
    )
    op.execute("DELETE FROM evidence_trace_edges WHERE evidence_manifest_id IS NULL")
    op.execute("DELETE FROM evidence_trace_nodes WHERE evidence_manifest_id IS NULL")
    op.alter_column("evidence_trace_edges", "evidence_manifest_id", nullable=False)
    op.alter_column("evidence_trace_nodes", "evidence_manifest_id", nullable=False)
    op.drop_column("evidence_trace_edges", "evidence_package_export_id")
    op.drop_column("evidence_trace_nodes", "evidence_package_export_id")

    op.drop_index(
        "ix_evidence_package_exports_trace_sha256",
        table_name="evidence_package_exports",
    )
    op.drop_column("evidence_package_exports", "trace_sha256")
