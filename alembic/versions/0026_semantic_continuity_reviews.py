"""add semantic continuity summaries and review overlays

Revision ID: 0026_semantic_continuity_reviews
Revises: 0025_semantic_categories
Create Date: 2026-04-19 18:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0026_semantic_continuity_reviews"
down_revision: str | Sequence[str] | None = "0025_semantic_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_semantic_concept_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_status", sa.Text(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_document_semantic_concept_reviews_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["semantic_concepts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_semantic_concept_reviews_document_id",
        "document_semantic_concept_reviews",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_semantic_concept_reviews_concept_id",
        "document_semantic_concept_reviews",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_doc_sem_concept_reviews_doc_concept_created_at",
        "document_semantic_concept_reviews",
        ["document_id", "concept_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "document_semantic_category_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_status", sa.Text(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_document_semantic_category_reviews_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["semantic_concepts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["semantic_categories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_semantic_category_reviews_document_id",
        "document_semantic_category_reviews",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_semantic_category_reviews_concept_id",
        "document_semantic_category_reviews",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_semantic_category_reviews_category_id",
        "document_semantic_category_reviews",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        "ix_doc_sem_category_reviews_doc_binding_created_at",
        "document_semantic_category_reviews",
        ["document_id", "concept_id", "category_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "document_run_semantic_passes",
        sa.Column("baseline_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "document_run_semantic_passes",
        sa.Column("baseline_semantic_pass_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "document_run_semantic_passes",
        sa.Column(
            "continuity_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_foreign_key(
        "fk_document_run_semantic_passes_baseline_run_id",
        "document_run_semantic_passes",
        "document_runs",
        ["baseline_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_document_run_semantic_passes_baseline_semantic_pass_id",
        "document_run_semantic_passes",
        "document_run_semantic_passes",
        ["baseline_semantic_pass_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_document_run_semantic_passes_baseline_run_id",
        "document_run_semantic_passes",
        ["baseline_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_run_semantic_passes_baseline_run_id",
        table_name="document_run_semantic_passes",
    )
    op.drop_constraint(
        "fk_document_run_semantic_passes_baseline_semantic_pass_id",
        "document_run_semantic_passes",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_document_run_semantic_passes_baseline_run_id",
        "document_run_semantic_passes",
        type_="foreignkey",
    )
    op.drop_column("document_run_semantic_passes", "continuity_summary")
    op.drop_column("document_run_semantic_passes", "baseline_semantic_pass_id")
    op.drop_column("document_run_semantic_passes", "baseline_run_id")

    op.drop_index(
        "ix_doc_sem_category_reviews_doc_binding_created_at",
        table_name="document_semantic_category_reviews",
    )
    op.drop_index(
        "ix_document_semantic_category_reviews_category_id",
        table_name="document_semantic_category_reviews",
    )
    op.drop_index(
        "ix_document_semantic_category_reviews_concept_id",
        table_name="document_semantic_category_reviews",
    )
    op.drop_index(
        "ix_document_semantic_category_reviews_document_id",
        table_name="document_semantic_category_reviews",
    )
    op.drop_table("document_semantic_category_reviews")

    op.drop_index(
        "ix_doc_sem_concept_reviews_doc_concept_created_at",
        table_name="document_semantic_concept_reviews",
    )
    op.drop_index(
        "ix_document_semantic_concept_reviews_concept_id",
        table_name="document_semantic_concept_reviews",
    )
    op.drop_index(
        "ix_document_semantic_concept_reviews_document_id",
        table_name="document_semantic_concept_reviews",
    )
    op.drop_table("document_semantic_concept_reviews")
