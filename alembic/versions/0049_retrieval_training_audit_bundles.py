"""allow retrieval training audit bundle exports

Revision ID: 0049_training_audit_bundles
Revises: 0048_learning_candidates
Create Date: 2026-04-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0049_training_audit_bundles"
down_revision: str | Sequence[str] | None = "0048_learning_candidates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


AUDIT_BUNDLE_KIND_CHECK_SQL = (
    "bundle_kind IN ("
    "'search_harness_release_provenance', "
    "'retrieval_training_run_provenance'"
    ")"
)

LEGACY_AUDIT_BUNDLE_KIND_CHECK_SQL = (
    "bundle_kind IN ('search_harness_release_provenance')"
)

AUDIT_BUNDLE_SOURCE_TABLE_CHECK_SQL = (
    "source_table IN ('search_harness_releases', 'retrieval_training_runs')"
)

LEGACY_AUDIT_BUNDLE_SOURCE_TABLE_CHECK_SQL = (
    "source_table IN ('search_harness_releases')"
)


def _replace_audit_bundle_constraints(
    *,
    bundle_kind_sql: str,
    source_table_sql: str,
) -> None:
    op.drop_constraint(
        "ck_audit_bundle_exports_bundle_kind",
        "audit_bundle_exports",
        type_="check",
    )
    op.create_check_constraint(
        "ck_audit_bundle_exports_bundle_kind",
        "audit_bundle_exports",
        bundle_kind_sql,
    )
    op.drop_constraint(
        "ck_audit_bundle_exports_source_table",
        "audit_bundle_exports",
        type_="check",
    )
    op.create_check_constraint(
        "ck_audit_bundle_exports_source_table",
        "audit_bundle_exports",
        source_table_sql,
    )


def upgrade() -> None:
    _replace_audit_bundle_constraints(
        bundle_kind_sql=AUDIT_BUNDLE_KIND_CHECK_SQL,
        source_table_sql=AUDIT_BUNDLE_SOURCE_TABLE_CHECK_SQL,
    )
    op.add_column(
        "audit_bundle_exports",
        sa.Column("retrieval_training_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_audit_bundle_exports_retrieval_training_run",
        "audit_bundle_exports",
        "retrieval_training_runs",
        ["retrieval_training_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_audit_bundle_exports_training_run_created_at",
        "audit_bundle_exports",
        ["retrieval_training_run_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audit_bundle_exports_training_run_created_at",
        table_name="audit_bundle_exports",
    )
    op.drop_constraint(
        "fk_audit_bundle_exports_retrieval_training_run",
        "audit_bundle_exports",
        type_="foreignkey",
    )
    op.drop_column("audit_bundle_exports", "retrieval_training_run_id")
    _replace_audit_bundle_constraints(
        bundle_kind_sql=LEGACY_AUDIT_BUNDLE_KIND_CHECK_SQL,
        source_table_sql=LEGACY_AUDIT_BUNDLE_SOURCE_TABLE_CHECK_SQL,
    )
