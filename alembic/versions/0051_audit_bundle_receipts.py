"""add audit bundle validation receipts

Revision ID: 0051_audit_bundle_receipts
Revises: 0050_audit_bundle_source
Create Date: 2026-04-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0051_audit_bundle_receipts"
down_revision: str | Sequence[str] | None = "0050_audit_bundle_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CREATE_IMMUTABILITY_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_audit_bundle_validation_receipt_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_bundle_validation_receipts rows are immutable';
END;
$$ LANGUAGE plpgsql;
"""

CREATE_IMMUTABILITY_TRIGGER_SQL = """
CREATE TRIGGER trg_audit_bundle_validation_receipts_prevent_update_delete
BEFORE UPDATE OR DELETE ON audit_bundle_validation_receipts
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_bundle_validation_receipt_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "audit_bundle_validation_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audit_bundle_export_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_kind", sa.Text(), nullable=False),
        sa.Column("source_table", sa.Text(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_profile", sa.Text(), nullable=False),
        sa.Column("validation_status", sa.Text(), nullable=False),
        sa.Column("payload_schema_valid", sa.Boolean(), nullable=False),
        sa.Column("prov_graph_valid", sa.Boolean(), nullable=False),
        sa.Column("bundle_integrity_valid", sa.Boolean(), nullable=False),
        sa.Column("source_integrity_valid", sa.Boolean(), nullable=False),
        sa.Column("receipt_storage_path", sa.Text(), nullable=False),
        sa.Column("prov_jsonld_storage_path", sa.Text(), nullable=False),
        sa.Column("receipt_sha256", sa.Text(), nullable=False),
        sa.Column("prov_jsonld_sha256", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("signature_algorithm", sa.Text(), nullable=False),
        sa.Column("signing_key_id", sa.Text(), nullable=False),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "receipt_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "prov_jsonld",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "bundle_kind IN ("
            "'search_harness_release_provenance', "
            "'retrieval_training_run_provenance'"
            ")",
            name="ck_audit_bundle_validation_receipts_bundle_kind",
        ),
        sa.CheckConstraint(
            "source_table IN ('search_harness_releases', 'retrieval_training_runs')",
            name="ck_audit_bundle_validation_receipts_source_table",
        ),
        sa.CheckConstraint(
            "validation_status IN ('passed', 'failed')",
            name="ck_audit_bundle_validation_receipts_status",
        ),
        sa.ForeignKeyConstraint(
            ["audit_bundle_export_id"],
            ["audit_bundle_exports.id"],
            name="fk_audit_bundle_validation_receipts_export",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_bundle_validation_receipts_bundle_created",
        "audit_bundle_validation_receipts",
        ["audit_bundle_export_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_validation_receipts_prov_jsonld_sha",
        "audit_bundle_validation_receipts",
        ["prov_jsonld_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_validation_receipts_receipt_sha",
        "audit_bundle_validation_receipts",
        ["receipt_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_validation_receipts_source",
        "audit_bundle_validation_receipts",
        ["source_table", "source_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_validation_receipts_status_created",
        "audit_bundle_validation_receipts",
        ["validation_status", "created_at"],
        unique=False,
    )
    op.execute(CREATE_IMMUTABILITY_FUNCTION_SQL)
    op.execute(CREATE_IMMUTABILITY_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS
        trg_audit_bundle_validation_receipts_prevent_update_delete
        ON audit_bundle_validation_receipts;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_bundle_validation_receipt_mutation();")
    op.drop_index(
        "ix_audit_bundle_validation_receipts_status_created",
        table_name="audit_bundle_validation_receipts",
    )
    op.drop_index(
        "ix_audit_bundle_validation_receipts_source",
        table_name="audit_bundle_validation_receipts",
    )
    op.drop_index(
        "ix_audit_bundle_validation_receipts_receipt_sha",
        table_name="audit_bundle_validation_receipts",
    )
    op.drop_index(
        "ix_audit_bundle_validation_receipts_prov_jsonld_sha",
        table_name="audit_bundle_validation_receipts",
    )
    op.drop_index(
        "ix_audit_bundle_validation_receipts_bundle_created",
        table_name="audit_bundle_validation_receipts",
    )
    op.drop_table("audit_bundle_validation_receipts")
