"""make audit bundle exports append-only

Revision ID: 0039_audit_bundle_immutability
Revises: 0038_audit_bundle_exports
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0039_audit_bundle_immutability"
down_revision: str | Sequence[str] | None = "0038_audit_bundle_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PREVENT_MUTATION_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_audit_bundle_export_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_bundle_exports rows are immutable'
        USING ERRCODE = 'integrity_constraint_violation';
    RETURN OLD;
END;
$$;
"""

PREVENT_MUTATION_TRIGGER_SQL = """
CREATE TRIGGER trg_audit_bundle_exports_prevent_update_delete
BEFORE UPDATE OR DELETE ON audit_bundle_exports
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_bundle_export_mutation();
"""


def upgrade() -> None:
    op.execute(PREVENT_MUTATION_FUNCTION_SQL)
    op.execute(PREVENT_MUTATION_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_audit_bundle_exports_prevent_update_delete
        ON audit_bundle_exports;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_bundle_export_mutation();")
