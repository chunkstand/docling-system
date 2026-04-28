"""Constrain active claim support calibration policies.

Revision ID: 0058_claim_policy_activation
Revises: 0057_claim_support_policy
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0058_claim_policy_activation"
down_revision: str | Sequence[str] | None = "0057_claim_support_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked_active AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY policy_name
                    ORDER BY created_at DESC, id DESC
                ) AS active_rank
            FROM claim_support_calibration_policies
            WHERE status = 'active'
        )
        UPDATE claim_support_calibration_policies AS policies
        SET status = 'retired'
        FROM ranked_active
        WHERE policies.id = ranked_active.id
          AND ranked_active.active_rank > 1
        """
    )
    op.create_index(
        "uq_claim_support_calibration_policies_active_name",
        "claim_support_calibration_policies",
        ["policy_name"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_claim_support_calibration_policies_active_name",
        table_name="claim_support_calibration_policies",
    )
