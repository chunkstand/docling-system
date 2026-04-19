"""add document figures and figure count

Revision ID: 0007_document_figures
Revises: 0006_table_hardening_fields
Create Date: 2026-04-10 14:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007_document_figures"
down_revision = "0006_table_hardening_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_runs", sa.Column("figure_count", sa.Integer(), nullable=True))

    op.create_table(
        "document_figures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("figure_index", sa.Integer(), nullable=False),
        sa.Column("source_figure_ref", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="persisted"),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("json_path", sa.Text(), nullable=True),
        sa.Column("yaml_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "figure_index", name="uq_document_figures_run_figure_index"),
    )
    op.create_index("ix_document_figures_document_id", "document_figures", ["document_id"])
    op.create_index("ix_document_figures_run_id", "document_figures", ["run_id"])
    op.create_index("ix_document_figures_page_from", "document_figures", ["page_from"])
    op.create_index("ix_document_figures_page_to", "document_figures", ["page_to"])


def downgrade() -> None:
    op.drop_index("ix_document_figures_page_to", table_name="document_figures")
    op.drop_index("ix_document_figures_page_from", table_name="document_figures")
    op.drop_index("ix_document_figures_run_id", table_name="document_figures")
    op.drop_index("ix_document_figures_document_id", table_name="document_figures")
    op.drop_table("document_figures")
    op.drop_column("document_runs", "figure_count")
