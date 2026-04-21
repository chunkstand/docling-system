"""add portable ontology snapshots and semantic fact graph

Revision ID: 0027_portable_ontology_snapshots
Revises: 0026_semantic_continuity_reviews
Create Date: 2026-04-20 11:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027_portable_ontology_snapshots"
down_revision: str | Sequence[str] | None = "0026_semantic_continuity_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_ontology_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ontology_name", sa.Text(), nullable=False),
        sa.Column("ontology_version", sa.Text(), nullable=False),
        sa.Column("upper_ontology_version", sa.Text(), nullable=False),
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
            "source_kind IN ('upper_seed', 'ontology_extension_apply')",
            name="ck_semantic_ontology_snapshots_source_kind",
        ),
        sa.ForeignKeyConstraint(
            ["parent_snapshot_id"],
            ["semantic_ontology_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_task_id"],
            ["agent_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ontology_version",
            name="uq_semantic_ontology_snapshots_ontology_version",
        ),
    )
    op.create_index(
        "ix_semantic_ontology_snapshots_created_at",
        "semantic_ontology_snapshots",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_ontology_snapshots_upper_ontology_version",
        "semantic_ontology_snapshots",
        ["upper_ontology_version"],
        unique=False,
    )

    op.create_table(
        "workspace_semantic_state",
        sa.Column("workspace_key", sa.Text(), nullable=False),
        sa.Column("active_ontology_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["active_ontology_snapshot_id"],
            ["semantic_ontology_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("workspace_key"),
    )

    op.add_column(
        "document_run_semantic_passes",
        sa.Column("ontology_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "document_run_semantic_passes",
        sa.Column("upper_ontology_version", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_run_semantic_passes_ontology_snapshot_id",
        "document_run_semantic_passes",
        "semantic_ontology_snapshots",
        ["ontology_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_document_run_semantic_passes_ontology_snapshot_id",
        "document_run_semantic_passes",
        ["ontology_snapshot_id"],
        unique=False,
    )

    op.create_table(
        "semantic_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_key", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("preferred_label", sa.Text(), nullable=False),
        sa.Column("ontology_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "entity_type IN ('document', 'concept', 'literal')",
            name="ck_semantic_entities_entity_type",
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["semantic_concepts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ontology_snapshot_id"],
            ["semantic_ontology_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_key", name="uq_semantic_entities_entity_key"),
    )
    op.create_index(
        "ix_semantic_entities_document_id",
        "semantic_entities",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_entities_concept_id",
        "semantic_entities",
        ["concept_id"],
        unique=False,
    )

    op.create_table(
        "semantic_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_pass_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ontology_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_key", sa.Text(), nullable=False),
        sa.Column("relation_label", sa.Text(), nullable=False),
        sa.Column("object_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_value_text", sa.Text(), nullable=True),
        sa.Column("source_assertion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_status", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_facts_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["object_entity_id"],
            ["semantic_entities.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ontology_snapshot_id"],
            ["semantic_ontology_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["document_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_pass_id"],
            ["document_run_semantic_passes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_assertion_id"],
            ["semantic_assertions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["subject_entity_id"],
            ["semantic_entities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_semantic_facts_document_id", "semantic_facts", ["document_id"], unique=False
    )
    op.create_index("ix_semantic_facts_run_id", "semantic_facts", ["run_id"], unique=False)
    op.create_index(
        "ix_semantic_facts_semantic_pass_id",
        "semantic_facts",
        ["semantic_pass_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_facts_relation_key",
        "semantic_facts",
        ["relation_key"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_facts_subject_entity_id",
        "semantic_facts",
        ["subject_entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_facts_object_entity_id",
        "semantic_facts",
        ["object_entity_id"],
        unique=False,
    )

    op.create_table(
        "semantic_fact_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assertion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assertion_evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assertion_evidence_id"],
            ["semantic_assertion_evidence.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assertion_id"],
            ["semantic_assertions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["semantic_facts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_semantic_fact_evidence_fact_id",
        "semantic_fact_evidence",
        ["fact_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_fact_evidence_assertion_id",
        "semantic_fact_evidence",
        ["assertion_id"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_fact_evidence_evidence_id",
        "semantic_fact_evidence",
        ["assertion_evidence_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_semantic_fact_evidence_evidence_id", table_name="semantic_fact_evidence")
    op.drop_index("ix_semantic_fact_evidence_assertion_id", table_name="semantic_fact_evidence")
    op.drop_index("ix_semantic_fact_evidence_fact_id", table_name="semantic_fact_evidence")
    op.drop_table("semantic_fact_evidence")

    op.drop_index("ix_semantic_facts_object_entity_id", table_name="semantic_facts")
    op.drop_index("ix_semantic_facts_subject_entity_id", table_name="semantic_facts")
    op.drop_index("ix_semantic_facts_relation_key", table_name="semantic_facts")
    op.drop_index("ix_semantic_facts_semantic_pass_id", table_name="semantic_facts")
    op.drop_index("ix_semantic_facts_run_id", table_name="semantic_facts")
    op.drop_index("ix_semantic_facts_document_id", table_name="semantic_facts")
    op.drop_table("semantic_facts")

    op.drop_index("ix_semantic_entities_concept_id", table_name="semantic_entities")
    op.drop_index("ix_semantic_entities_document_id", table_name="semantic_entities")
    op.drop_table("semantic_entities")

    op.drop_index(
        "ix_document_run_semantic_passes_ontology_snapshot_id",
        table_name="document_run_semantic_passes",
    )
    op.drop_constraint(
        "fk_document_run_semantic_passes_ontology_snapshot_id",
        "document_run_semantic_passes",
        type_="foreignkey",
    )
    op.drop_column("document_run_semantic_passes", "upper_ontology_version")
    op.drop_column("document_run_semantic_passes", "ontology_snapshot_id")

    op.drop_table("workspace_semantic_state")

    op.drop_index(
        "ix_semantic_ontology_snapshots_upper_ontology_version",
        table_name="semantic_ontology_snapshots",
    )
    op.drop_index(
        "ix_semantic_ontology_snapshots_created_at",
        table_name="semantic_ontology_snapshots",
    )
    op.drop_table("semantic_ontology_snapshots")
