"""add immutable audit bundle exports

Revision ID: 0038_audit_bundle_exports
Revises: 0037_search_harness_releases
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0038_audit_bundle_exports"
down_revision: str | Sequence[str] | None = "0037_search_harness_releases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_bundle_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_kind", sa.Text(), nullable=False),
        sa.Column("source_table", sa.Text(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_harness_release_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.Text(), nullable=False),
        sa.Column("bundle_sha256", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("signature_algorithm", sa.Text(), nullable=False),
        sa.Column("signing_key_id", sa.Text(), nullable=False),
        sa.Column(
            "bundle_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "integrity",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column(
            "export_status",
            sa.Text(),
            server_default=sa.text("'completed'"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "bundle_kind IN ('search_harness_release_provenance')",
            name="ck_audit_bundle_exports_bundle_kind",
        ),
        sa.CheckConstraint(
            "source_table IN ('search_harness_releases')",
            name="ck_audit_bundle_exports_source_table",
        ),
        sa.CheckConstraint(
            "export_status IN ('completed', 'failed')",
            name="ck_audit_bundle_exports_status",
        ),
        sa.ForeignKeyConstraint(
            ["search_harness_release_id"],
            ["search_harness_releases.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_bundle_exports_bundle_kind_created_at",
        "audit_bundle_exports",
        ["bundle_kind", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_exports_bundle_sha256",
        "audit_bundle_exports",
        ["bundle_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_exports_payload_sha256",
        "audit_bundle_exports",
        ["payload_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_exports_release_created_at",
        "audit_bundle_exports",
        ["search_harness_release_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_bundle_exports_source",
        "audit_bundle_exports",
        ["source_table", "source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_bundle_exports_source", table_name="audit_bundle_exports")
    op.drop_index(
        "ix_audit_bundle_exports_release_created_at",
        table_name="audit_bundle_exports",
    )
    op.drop_index("ix_audit_bundle_exports_payload_sha256", table_name="audit_bundle_exports")
    op.drop_index("ix_audit_bundle_exports_bundle_sha256", table_name="audit_bundle_exports")
    op.drop_index(
        "ix_audit_bundle_exports_bundle_kind_created_at",
        table_name="audit_bundle_exports",
    )
    op.drop_table("audit_bundle_exports")
