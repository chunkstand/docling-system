"""add document tables and table segments

Revision ID: 0003_document_tables
Revises: 0002_document_run_cleanup_index
Create Date: 2026-04-09 13:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "0003_document_tables"
down_revision = "0002_document_run_cleanup_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_tables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("table_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("col_count", sa.Integer(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("preview_text", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column("json_path", sa.Text(), nullable=True),
        sa.Column("markdown_path", sa.Text(), nullable=True),
        sa.Column(
            "textsearch",
            sa.dialects.postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('english', coalesce(heading, '')), 'B') || "
                "to_tsvector('english', coalesce(search_text, ''))",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "table_index", name="uq_document_tables_run_table_index"),
    )
    op.create_index("ix_document_tables_document_id", "document_tables", ["document_id"])
    op.create_index("ix_document_tables_page_from", "document_tables", ["page_from"])
    op.create_index("ix_document_tables_page_to", "document_tables", ["page_to"])
    op.create_index(
        "ix_document_tables_textsearch",
        "document_tables",
        ["textsearch"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_document_tables_embedding_hnsw",
        "document_tables",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "document_table_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("source_table_ref", sa.Text(), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("segment_order", sa.Integer(), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["table_id"], ["document_tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_id", "segment_index", name="uq_document_table_segments_table_segment_index"),
    )
    op.create_index("ix_document_table_segments_run_id", "document_table_segments", ["run_id"])
    op.create_index("ix_document_table_segments_page_from", "document_table_segments", ["page_from"])
    op.create_index("ix_document_table_segments_page_to", "document_table_segments", ["page_to"])


def downgrade() -> None:
    op.drop_index("ix_document_table_segments_page_to", table_name="document_table_segments")
    op.drop_index("ix_document_table_segments_page_from", table_name="document_table_segments")
    op.drop_index("ix_document_table_segments_run_id", table_name="document_table_segments")
    op.drop_table("document_table_segments")

    op.drop_index("ix_document_tables_embedding_hnsw", table_name="document_tables")
    op.drop_index("ix_document_tables_textsearch", table_name="document_tables")
    op.drop_index("ix_document_tables_page_to", table_name="document_tables")
    op.drop_index("ix_document_tables_page_from", table_name="document_tables")
    op.drop_index("ix_document_tables_document_id", table_name="document_tables")
    op.drop_table("document_tables")
