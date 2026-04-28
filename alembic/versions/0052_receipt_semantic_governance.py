"""add semantic governance receipt check

Revision ID: 0052_receipt_sem_gov
Revises: 0051_audit_bundle_receipts
Create Date: 2026-04-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0052_receipt_sem_gov"
down_revision: str | Sequence[str] | None = "0051_audit_bundle_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "audit_bundle_validation_receipts",
        sa.Column(
            "semantic_governance_valid",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.alter_column(
        "audit_bundle_validation_receipts",
        "semantic_governance_valid",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("audit_bundle_validation_receipts", "semantic_governance_valid")
