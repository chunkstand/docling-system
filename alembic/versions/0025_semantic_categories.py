"""add semantic categories and binding governance

Revision ID: 0025_semantic_categories
Revises: 0024_semantic_pass_foundation
Create Date: 2026-04-19 15:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0025_semantic_categories"
down_revision: str | Sequence[str] | None = "0024_semantic_pass_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_key", sa.Text(), nullable=False),
        sa.Column("preferred_label", sa.Text(), nullable=False),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column("registry_version", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category_key",
            "registry_version",
            name="uq_semantic_categories_key_registry_version",
        ),
    )
    op.create_index(
        "ix_semantic_categories_category_key",
        "semantic_categories",
        ["category_key"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_categories_registry_version",
        "semantic_categories",
        ["registry_version"],
        unique=False,
    )

    op.add_column(
        "semantic_concept_terms",
        sa.Column(
            "created_from",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'registry'"),
        ),
    )
    op.add_column(
        "semantic_concept_terms",
        sa.Column(
            "review_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'approved'"),
        ),
    )
    op.add_column(
        "semantic_concept_terms",
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_check_constraint(
        "ck_semantic_concept_terms_created_from",
        "semantic_concept_terms",
        "created_from IN ('registry', 'derived')",
    )
    op.create_check_constraint(
        "ck_semantic_concept_terms_review_status",
        "semantic_concept_terms",
        "review_status IN ('candidate', 'approved', 'rejected')",
    )

    op.create_table(
        "semantic_concept_category_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("binding_type", sa.Text(), nullable=False),
        sa.Column(
            "created_from",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'registry'"),
        ),
        sa.Column(
            "review_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'approved'"),
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "binding_type IN ('concept_category')",
            name="ck_semantic_concept_category_bindings_binding_type",
        ),
        sa.CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_concept_category_bindings_created_from",
        ),
        sa.CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_concept_category_bindings_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["semantic_categories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["semantic_concepts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "concept_id",
            "category_id",
            name="uq_semantic_concept_category_bindings_concept_category",
        ),
    )
    op.create_index(
        "ix_semantic_concept_category_bindings_concept_id",
        "semantic_concept_category_bindings",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_concept_category_bindings_category_id",
        "semantic_concept_category_bindings",
        ["category_id"],
        unique=False,
    )

    op.add_column(
        "semantic_assertions",
        sa.Column(
            "epistemic_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'observed'"),
        ),
    )
    op.add_column(
        "semantic_assertions",
        sa.Column(
            "context_scope",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'document_run'"),
        ),
    )
    op.add_column(
        "semantic_assertions",
        sa.Column(
            "review_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'candidate'"),
        ),
    )
    op.create_check_constraint(
        "ck_semantic_assertions_epistemic_status",
        "semantic_assertions",
        "epistemic_status IN ('observed', 'inferred', 'curated')",
    )
    op.create_check_constraint(
        "ck_semantic_assertions_context_scope",
        "semantic_assertions",
        "context_scope IN ('document_run', 'document', 'registry')",
    )
    op.create_check_constraint(
        "ck_semantic_assertions_review_status",
        "semantic_assertions",
        "review_status IN ('candidate', 'approved', 'rejected')",
    )

    op.create_table(
        "semantic_assertion_category_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assertion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_category_binding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("binding_type", sa.Text(), nullable=False),
        sa.Column(
            "created_from",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'derived'"),
        ),
        sa.Column(
            "review_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'candidate'"),
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "binding_type IN ('assertion_category')",
            name="ck_semantic_assertion_category_bindings_binding_type",
        ),
        sa.CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_assertion_category_bindings_created_from",
        ),
        sa.CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_assertion_category_bindings_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["assertion_id"],
            ["semantic_assertions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["semantic_categories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["concept_category_binding_id"],
            ["semantic_concept_category_bindings.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assertion_id",
            "category_id",
            name="uq_semantic_assertion_category_bindings_assertion_category",
        ),
    )
    op.create_index(
        "ix_semantic_assertion_category_bindings_assertion_id",
        "semantic_assertion_category_bindings",
        ["assertion_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_assertion_category_bindings_category_id",
        "semantic_assertion_category_bindings",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_semantic_assertion_category_bindings_category_id",
        table_name="semantic_assertion_category_bindings",
    )
    op.drop_index(
        "ix_semantic_assertion_category_bindings_assertion_id",
        table_name="semantic_assertion_category_bindings",
    )
    op.drop_table("semantic_assertion_category_bindings")

    op.drop_constraint("ck_semantic_assertions_review_status", "semantic_assertions", type_="check")
    op.drop_constraint(
        "ck_semantic_assertions_context_scope", "semantic_assertions", type_="check"
    )
    op.drop_constraint(
        "ck_semantic_assertions_epistemic_status", "semantic_assertions", type_="check"
    )
    op.drop_column("semantic_assertions", "review_status")
    op.drop_column("semantic_assertions", "context_scope")
    op.drop_column("semantic_assertions", "epistemic_status")

    op.drop_index(
        "ix_semantic_concept_category_bindings_category_id",
        table_name="semantic_concept_category_bindings",
    )
    op.drop_index(
        "ix_semantic_concept_category_bindings_concept_id",
        table_name="semantic_concept_category_bindings",
    )
    op.drop_table("semantic_concept_category_bindings")

    op.drop_constraint(
        "ck_semantic_concept_terms_review_status",
        "semantic_concept_terms",
        type_="check",
    )
    op.drop_constraint(
        "ck_semantic_concept_terms_created_from",
        "semantic_concept_terms",
        type_="check",
    )
    op.drop_column("semantic_concept_terms", "details")
    op.drop_column("semantic_concept_terms", "review_status")
    op.drop_column("semantic_concept_terms", "created_from")

    op.drop_index("ix_semantic_categories_registry_version", table_name="semantic_categories")
    op.drop_index("ix_semantic_categories_category_key", table_name="semantic_categories")
    op.drop_table("semantic_categories")
