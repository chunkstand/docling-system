"""add evidence trace graph

Revision ID: 0035_evidence_trace_graph
Revises: 0034_evidence_manifests
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0035_evidence_trace_graph"
down_revision: str | Sequence[str] | None = "0034_evidence_manifests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_manifests",
        sa.Column("trace_sha256", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_evidence_manifests_trace_sha256",
        "evidence_manifests",
        ["trace_sha256"],
    )

    op.create_table(
        "evidence_trace_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("evidence_manifest_id", sa.UUID(), nullable=False),
        sa.Column("node_key", sa.Text(), nullable=False),
        sa.Column("node_kind", sa.Text(), nullable=False),
        sa.Column("source_table", sa.Text(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_manifest_id"],
            ["evidence_manifests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evidence_manifest_id",
            "node_key",
            name="uq_evidence_trace_nodes_manifest_node_key",
        ),
    )
    op.create_index(
        "ix_evidence_trace_nodes_content_sha256",
        "evidence_trace_nodes",
        ["content_sha256"],
    )
    op.create_index(
        "ix_evidence_trace_nodes_manifest_id",
        "evidence_trace_nodes",
        ["evidence_manifest_id"],
    )
    op.create_index(
        "ix_evidence_trace_nodes_node_kind",
        "evidence_trace_nodes",
        ["node_kind"],
    )
    op.create_index(
        "ix_evidence_trace_nodes_source",
        "evidence_trace_nodes",
        ["source_table", "source_id"],
    )
    op.create_index(
        "ix_evidence_trace_nodes_source_ref",
        "evidence_trace_nodes",
        ["source_table", "source_ref"],
    )

    op.create_table(
        "evidence_trace_edges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("evidence_manifest_id", sa.UUID(), nullable=False),
        sa.Column("edge_key", sa.Text(), nullable=False),
        sa.Column("edge_kind", sa.Text(), nullable=False),
        sa.Column("from_node_id", sa.UUID(), nullable=False),
        sa.Column("to_node_id", sa.UUID(), nullable=False),
        sa.Column("from_node_key", sa.Text(), nullable=False),
        sa.Column("to_node_key", sa.Text(), nullable=False),
        sa.Column("derivation_sha256", sa.Text(), nullable=True),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_manifest_id"],
            ["evidence_manifests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_node_id"],
            ["evidence_trace_nodes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_node_id"],
            ["evidence_trace_nodes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evidence_manifest_id",
            "edge_key",
            name="uq_evidence_trace_edges_manifest_edge_key",
        ),
    )
    op.create_index(
        "ix_evidence_trace_edges_content_sha256",
        "evidence_trace_edges",
        ["content_sha256"],
    )
    op.create_index(
        "ix_evidence_trace_edges_derivation_sha256",
        "evidence_trace_edges",
        ["derivation_sha256"],
    )
    op.create_index(
        "ix_evidence_trace_edges_edge_kind",
        "evidence_trace_edges",
        ["edge_kind"],
    )
    op.create_index(
        "ix_evidence_trace_edges_from_node_id",
        "evidence_trace_edges",
        ["from_node_id"],
    )
    op.create_index(
        "ix_evidence_trace_edges_manifest_id",
        "evidence_trace_edges",
        ["evidence_manifest_id"],
    )
    op.create_index(
        "ix_evidence_trace_edges_to_node_id",
        "evidence_trace_edges",
        ["to_node_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_trace_edges_to_node_id", table_name="evidence_trace_edges")
    op.drop_index("ix_evidence_trace_edges_manifest_id", table_name="evidence_trace_edges")
    op.drop_index("ix_evidence_trace_edges_from_node_id", table_name="evidence_trace_edges")
    op.drop_index("ix_evidence_trace_edges_edge_kind", table_name="evidence_trace_edges")
    op.drop_index("ix_evidence_trace_edges_derivation_sha256", table_name="evidence_trace_edges")
    op.drop_index("ix_evidence_trace_edges_content_sha256", table_name="evidence_trace_edges")
    op.drop_table("evidence_trace_edges")

    op.drop_index("ix_evidence_trace_nodes_source_ref", table_name="evidence_trace_nodes")
    op.drop_index("ix_evidence_trace_nodes_source", table_name="evidence_trace_nodes")
    op.drop_index("ix_evidence_trace_nodes_node_kind", table_name="evidence_trace_nodes")
    op.drop_index("ix_evidence_trace_nodes_manifest_id", table_name="evidence_trace_nodes")
    op.drop_index("ix_evidence_trace_nodes_content_sha256", table_name="evidence_trace_nodes")
    op.drop_table("evidence_trace_nodes")

    op.drop_index("ix_evidence_manifests_trace_sha256", table_name="evidence_manifests")
    op.drop_column("evidence_manifests", "trace_sha256")
