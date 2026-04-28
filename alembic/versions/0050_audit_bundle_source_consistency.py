"""enforce audit bundle source consistency

Revision ID: 0050_audit_bundle_source
Revises: 0049_training_audit_bundles
Create Date: 2026-04-28 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0050_audit_bundle_source"
down_revision: str | Sequence[str] | None = "0049_training_audit_bundles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


AUDIT_BUNDLE_SOURCE_CONSISTENCY_CHECK_SQL = (
    "("
    "bundle_kind = 'search_harness_release_provenance' "
    "AND source_table = 'search_harness_releases' "
    "AND search_harness_release_id IS NOT NULL "
    "AND search_harness_release_id = source_id "
    "AND retrieval_training_run_id IS NULL"
    ") OR ("
    "bundle_kind = 'retrieval_training_run_provenance' "
    "AND source_table = 'retrieval_training_runs' "
    "AND retrieval_training_run_id IS NOT NULL "
    "AND retrieval_training_run_id = source_id"
    ")"
)


def upgrade() -> None:
    op.create_check_constraint(
        "ck_audit_bundle_exports_source_consistency",
        "audit_bundle_exports",
        AUDIT_BUNDLE_SOURCE_CONSISTENCY_CHECK_SQL,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_audit_bundle_exports_source_consistency",
        "audit_bundle_exports",
        type_="check",
    )
