"""add table hardening fields

Revision ID: 0006_table_hardening_fields
Revises: 0005_validation_gate_fields
Create Date: 2026-04-09 23:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_table_hardening_fields"
down_revision = "0005_validation_gate_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_tables", sa.Column("logical_table_key", sa.Text(), nullable=True))
    op.add_column("document_tables", sa.Column("table_version", sa.Integer(), nullable=True))
    op.add_column("document_tables", sa.Column("supersedes_table_id", sa.Uuid(), nullable=True))
    op.add_column("document_tables", sa.Column("lineage_group", sa.Text(), nullable=True))
    op.add_column(
        "document_tables",
        sa.Column("status", sa.Text(), nullable=False, server_default="persisted"),
    )


def downgrade() -> None:
    op.drop_column("document_tables", "status")
    op.drop_column("document_tables", "lineage_group")
    op.drop_column("document_tables", "supersedes_table_id")
    op.drop_column("document_tables", "table_version")
    op.drop_column("document_tables", "logical_table_key")
