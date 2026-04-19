"""add semantic pass foundation

Revision ID: 0024_semantic_pass_foundation
Revises: 0023_doc_metadata_textsearch
Create Date: 2026-04-19 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0024_semantic_pass_foundation"
down_revision: str | Sequence[str] | None = "0023_doc_metadata_textsearch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_concepts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_key", sa.Text(), nullable=False),
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
            "concept_key",
            "registry_version",
            name="uq_semantic_concepts_key_registry_version",
        ),
    )
    op.create_index(
        "ix_semantic_concepts_concept_key",
        "semantic_concepts",
        ["concept_key"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_concepts_registry_version",
        "semantic_concepts",
        ["registry_version"],
        unique=False,
    )

    op.create_table(
        "semantic_terms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registry_version", sa.Text(), nullable=False),
        sa.Column("term_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("term_kind", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "term_kind IN ('preferred_label', 'alias')",
            name="ck_semantic_terms_term_kind",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "registry_version",
            "normalized_text",
            name="uq_semantic_terms_registry_version_normalized_text",
        ),
    )
    op.create_index(
        "ix_semantic_terms_registry_version",
        "semantic_terms",
        ["registry_version"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_terms_normalized_text",
        "semantic_terms",
        ["normalized_text"],
        unique=False,
    )

    op.create_table(
        "semantic_concept_terms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("term_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mapping_kind", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mapping_kind IN ('preferred_label', 'alias')",
            name="ck_semantic_concept_terms_mapping_kind",
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["semantic_concepts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["semantic_terms.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "concept_id",
            "term_id",
            name="uq_semantic_concept_terms_concept_term",
        ),
    )
    op.create_index(
        "ix_semantic_concept_terms_concept_id",
        "semantic_concept_terms",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_concept_terms_term_id",
        "semantic_concept_terms",
        ["term_id"],
        unique=False,
    )

    op.create_table(
        "document_run_semantic_passes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("registry_version", sa.Text(), nullable=False),
        sa.Column("registry_sha256", sa.Text(), nullable=False),
        sa.Column("extractor_version", sa.Text(), nullable=False),
        sa.Column("artifact_schema_version", sa.Text(), nullable=False),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evaluation_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("evaluation_fixture_name", sa.Text(), nullable=True),
        sa.Column(
            "evaluation_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "evaluation_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("artifact_json_path", sa.Text(), nullable=True),
        sa.Column("artifact_yaml_path", sa.Text(), nullable=True),
        sa.Column("artifact_json_sha256", sa.Text(), nullable=True),
        sa.Column("artifact_yaml_sha256", sa.Text(), nullable=True),
        sa.Column(
            "assertion_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "evidence_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_document_run_semantic_passes_status",
        ),
        sa.CheckConstraint(
            "evaluation_status IN ('pending', 'completed', 'failed', 'skipped')",
            name="ck_document_run_semantic_passes_evaluation_status",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "registry_version",
            "extractor_version",
            "artifact_schema_version",
            name="uq_document_run_semantic_passes_run_version_tuple",
        ),
    )
    op.create_index(
        "ix_document_run_semantic_passes_document_id",
        "document_run_semantic_passes",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_run_semantic_passes_run_id",
        "document_run_semantic_passes",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_run_semantic_passes_status",
        "document_run_semantic_passes",
        ["status"],
        unique=False,
    )

    op.create_table(
        "semantic_assertions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_pass_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assertion_kind", sa.Text(), nullable=False),
        sa.Column(
            "matched_terms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "evidence_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "assertion_kind IN ('concept_mention')",
            name="ck_semantic_assertions_assertion_kind",
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["semantic_concepts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_pass_id"],
            ["document_run_semantic_passes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "semantic_pass_id",
            "concept_id",
            "assertion_kind",
            name="uq_semantic_assertions_pass_concept_kind",
        ),
    )
    op.create_index(
        "ix_semantic_assertions_semantic_pass_id",
        "semantic_assertions",
        ["semantic_pass_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_assertions_concept_id",
        "semantic_assertions",
        ["concept_id"],
        unique=False,
    )

    op.create_table(
        "semantic_assertion_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assertion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("figure_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column(
            "matched_terms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("source_label", sa.Text(), nullable=True),
        sa.Column("source_artifact_path", sa.Text(), nullable=True),
        sa.Column("source_artifact_sha256", sa.Text(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('chunk', 'table', 'figure')",
            name="ck_semantic_assertion_evidence_source_type",
        ),
        sa.ForeignKeyConstraint(
            ["assertion_id"],
            ["semantic_assertions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["figure_id"], ["document_figures.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["document_tables.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assertion_id",
            "source_type",
            "source_locator",
            name="uq_semantic_assertion_evidence_assertion_source",
        ),
    )
    op.create_index(
        "ix_semantic_assertion_evidence_assertion_id",
        "semantic_assertion_evidence",
        ["assertion_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_assertion_evidence_run_id",
        "semantic_assertion_evidence",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_assertion_evidence_source_type",
        "semantic_assertion_evidence",
        ["source_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_semantic_assertion_evidence_source_type",
        table_name="semantic_assertion_evidence",
    )
    op.drop_index("ix_semantic_assertion_evidence_run_id", table_name="semantic_assertion_evidence")
    op.drop_index(
        "ix_semantic_assertion_evidence_assertion_id",
        table_name="semantic_assertion_evidence",
    )
    op.drop_table("semantic_assertion_evidence")

    op.drop_index("ix_semantic_assertions_concept_id", table_name="semantic_assertions")
    op.drop_index("ix_semantic_assertions_semantic_pass_id", table_name="semantic_assertions")
    op.drop_table("semantic_assertions")

    op.drop_index(
        "ix_document_run_semantic_passes_status",
        table_name="document_run_semantic_passes",
    )
    op.drop_index(
        "ix_document_run_semantic_passes_run_id",
        table_name="document_run_semantic_passes",
    )
    op.drop_index(
        "ix_document_run_semantic_passes_document_id",
        table_name="document_run_semantic_passes",
    )
    op.drop_table("document_run_semantic_passes")

    op.drop_index("ix_semantic_concept_terms_term_id", table_name="semantic_concept_terms")
    op.drop_index("ix_semantic_concept_terms_concept_id", table_name="semantic_concept_terms")
    op.drop_table("semantic_concept_terms")

    op.drop_index("ix_semantic_terms_normalized_text", table_name="semantic_terms")
    op.drop_index("ix_semantic_terms_registry_version", table_name="semantic_terms")
    op.drop_table("semantic_terms")

    op.drop_index("ix_semantic_concepts_registry_version", table_name="semantic_concepts")
    op.drop_index("ix_semantic_concepts_concept_key", table_name="semantic_concepts")
    op.drop_table("semantic_concepts")
