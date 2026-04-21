"""add semantic graph snapshot memory

Revision ID: 0028_semantic_graph_memory
Revises: 0027_portable_ontology_snapshots
Create Date: 2026-04-20 13:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0028_semantic_graph_memory"
down_revision: str | Sequence[str] | None = "0027_portable_ontology_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_graph_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("graph_name", sa.Text(), nullable=False),
        sa.Column("graph_version", sa.Text(), nullable=False),
        sa.Column("ontology_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_task_type", sa.Text(), nullable=True),
        sa.Column("parent_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_kind IN ('graph_promotion_apply')",
            name="ck_semantic_graph_snapshots_source_kind",
        ),
        sa.ForeignKeyConstraint(
            ["ontology_snapshot_id"],
            ["semantic_ontology_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_snapshot_id"],
            ["semantic_graph_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "graph_version",
            name="uq_semantic_graph_snapshots_graph_version",
        ),
    )
    op.create_index(
        "ix_semantic_graph_snapshots_created_at",
        "semantic_graph_snapshots",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_graph_snapshots_ontology_snapshot_id",
        "semantic_graph_snapshots",
        ["ontology_snapshot_id"],
        unique=False,
    )

    op.create_table(
        "workspace_semantic_graph_state",
        sa.Column("workspace_key", sa.Text(), nullable=False),
        sa.Column("active_graph_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["active_graph_snapshot_id"],
            ["semantic_graph_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("workspace_key"),
    )


def downgrade() -> None:
    op.drop_table("workspace_semantic_graph_state")
    op.drop_index(
        "ix_semantic_graph_snapshots_ontology_snapshot_id",
        table_name="semantic_graph_snapshots",
    )
    op.drop_index(
        "ix_semantic_graph_snapshots_created_at",
        table_name="semantic_graph_snapshots",
    )
    op.drop_table("semantic_graph_snapshots")
