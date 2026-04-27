"""add retrieval evidence spans

Revision ID: 0036_retrieval_evidence_spans
Revises: 0035_evidence_trace_graph
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0036_retrieval_evidence_spans"
down_revision: str | Sequence[str] | None = "0035_evidence_trace_graph"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RETRIEVAL_SPAN_TEXTSEARCH_SQL = (
    "setweight(to_tsvector('english', coalesce(heading, '')), 'A') || "
    "to_tsvector('english', coalesce(span_text, ''))"
)


def upgrade() -> None:
    op.create_table(
        "retrieval_evidence_spans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=True),
        sa.Column("table_id", sa.UUID(), nullable=True),
        sa.Column("span_index", sa.Integer(), nullable=False),
        sa.Column("span_text", sa.Text(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column("source_snapshot_sha256", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column(
            "textsearch",
            postgresql.TSVECTOR(),
            sa.Computed(RETRIEVAL_SPAN_TEXTSEARCH_SQL, persisted=True),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_retrieval_evidence_spans_source_type",
        ),
        sa.CheckConstraint(
            "("
            "source_type = 'chunk' AND chunk_id IS NOT NULL AND table_id IS NULL"
            ") OR ("
            "source_type = 'table' AND table_id IS NOT NULL AND chunk_id IS NULL"
            ")",
            name="ck_retrieval_evidence_spans_source_ref",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["document_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "source_type",
            "source_id",
            "span_index",
            name="uq_retrieval_evidence_spans_run_source_span",
        ),
    )
    op.create_index(
        "ix_retrieval_evidence_spans_chunk_id",
        "retrieval_evidence_spans",
        ["chunk_id"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_content_sha256",
        "retrieval_evidence_spans",
        ["content_sha256"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_document_id",
        "retrieval_evidence_spans",
        ["document_id"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_embedding_hnsw",
        "retrieval_evidence_spans",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_retrieval_evidence_spans_page_from",
        "retrieval_evidence_spans",
        ["page_from"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_page_to",
        "retrieval_evidence_spans",
        ["page_to"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_run_id",
        "retrieval_evidence_spans",
        ["run_id"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_source",
        "retrieval_evidence_spans",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_table_id",
        "retrieval_evidence_spans",
        ["table_id"],
    )
    op.create_index(
        "ix_retrieval_evidence_spans_textsearch",
        "retrieval_evidence_spans",
        ["textsearch"],
        postgresql_using="gin",
    )

    op.create_table(
        "search_request_result_spans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("search_request_id", sa.UUID(), nullable=False),
        sa.Column("search_request_result_id", sa.UUID(), nullable=False),
        sa.Column("retrieval_evidence_span_id", sa.UUID(), nullable=True),
        sa.Column("span_rank", sa.Integer(), nullable=False),
        sa.Column("score_kind", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("span_index", sa.Integer(), nullable=False),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("text_excerpt", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column("source_snapshot_sha256", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_search_request_result_spans_source_type",
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_evidence_span_id"],
            ["retrieval_evidence_spans.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            ["search_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_result_id"],
            ["search_request_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "search_request_result_id",
            "span_rank",
            name="uq_search_request_result_spans_result_rank",
        ),
    )
    op.create_index(
        "ix_search_request_result_spans_content_sha256",
        "search_request_result_spans",
        ["content_sha256"],
    )
    op.create_index(
        "ix_search_request_result_spans_request_id",
        "search_request_result_spans",
        ["search_request_id"],
    )
    op.create_index(
        "ix_search_request_result_spans_result_id",
        "search_request_result_spans",
        ["search_request_result_id"],
    )
    op.create_index(
        "ix_search_request_result_spans_source",
        "search_request_result_spans",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_search_request_result_spans_span_id",
        "search_request_result_spans",
        ["retrieval_evidence_span_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_request_result_spans_span_id",
        table_name="search_request_result_spans",
    )
    op.drop_index(
        "ix_search_request_result_spans_source",
        table_name="search_request_result_spans",
    )
    op.drop_index(
        "ix_search_request_result_spans_result_id",
        table_name="search_request_result_spans",
    )
    op.drop_index(
        "ix_search_request_result_spans_request_id",
        table_name="search_request_result_spans",
    )
    op.drop_index(
        "ix_search_request_result_spans_content_sha256",
        table_name="search_request_result_spans",
    )
    op.drop_table("search_request_result_spans")

    op.drop_index(
        "ix_retrieval_evidence_spans_textsearch",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_table_id",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_source",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_run_id",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_page_to",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_page_from",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_embedding_hnsw",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_document_id",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_content_sha256",
        table_name="retrieval_evidence_spans",
    )
    op.drop_index(
        "ix_retrieval_evidence_spans_chunk_id",
        table_name="retrieval_evidence_spans",
    )
    op.drop_table("retrieval_evidence_spans")
