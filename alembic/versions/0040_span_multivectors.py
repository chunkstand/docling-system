"""add retrieval evidence span multivectors

Revision ID: 0040_span_multivectors
Revises: 0039_audit_bundle_immutability
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0040_span_multivectors"
down_revision: str | Sequence[str] | None = "0039_audit_bundle_immutability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retrieval_evidence_span_multivectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retrieval_evidence_span_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vector_index", sa.Integer(), nullable=False),
        sa.Column("token_start", sa.Integer(), nullable=False),
        sa.Column("token_end", sa.Integer(), nullable=False),
        sa.Column("vector_text", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_retrieval_span_multivectors_source_type",
        ),
        sa.CheckConstraint(
            "token_start >= 0 AND token_end > token_start",
            name="ck_retrieval_span_multivectors_token_range",
        ),
        sa.CheckConstraint(
            "embedding_dim = 1536",
            name="ck_retrieval_span_multivectors_embedding_dim",
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_evidence_span_id"],
            ["retrieval_evidence_spans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "retrieval_evidence_span_id",
            "vector_index",
            name="uq_retrieval_span_multivectors_span_vector",
        ),
    )
    op.create_index(
        "ix_retrieval_span_multivectors_content_sha256",
        "retrieval_evidence_span_multivectors",
        ["content_sha256"],
    )
    op.create_index(
        "ix_retrieval_span_multivectors_document_id",
        "retrieval_evidence_span_multivectors",
        ["document_id"],
    )
    op.create_index(
        "ix_retrieval_span_multivectors_embedding_hnsw",
        "retrieval_evidence_span_multivectors",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_retrieval_span_multivectors_model",
        "retrieval_evidence_span_multivectors",
        ["embedding_model"],
    )
    op.create_index(
        "ix_retrieval_span_multivectors_run_id",
        "retrieval_evidence_span_multivectors",
        ["run_id"],
    )
    op.create_index(
        "ix_retrieval_span_multivectors_source",
        "retrieval_evidence_span_multivectors",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_retrieval_span_multivectors_span_id",
        "retrieval_evidence_span_multivectors",
        ["retrieval_evidence_span_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_span_multivectors_span_id",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_index(
        "ix_retrieval_span_multivectors_source",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_index(
        "ix_retrieval_span_multivectors_run_id",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_index(
        "ix_retrieval_span_multivectors_model",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_index(
        "ix_retrieval_span_multivectors_embedding_hnsw",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_index(
        "ix_retrieval_span_multivectors_document_id",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_index(
        "ix_retrieval_span_multivectors_content_sha256",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_table("retrieval_evidence_span_multivectors")
