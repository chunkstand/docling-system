"""Add claim support judgments.

Revision ID: 0055_claim_support_judgments
Revises: 0054_claim_provenance_locks
Create Date: 2026-04-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0055_claim_support_judgments"
down_revision: str | Sequence[str] | None = "0054_claim_provenance_locks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "claim_evidence_derivations",
        sa.Column("support_verdict", sa.Text(), nullable=True),
    )
    op.add_column(
        "claim_evidence_derivations",
        sa.Column("support_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "claim_evidence_derivations",
        sa.Column("support_judge_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "claim_evidence_derivations",
        sa.Column(
            "support_judgment",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "claim_evidence_derivations",
        sa.Column("support_judgment_sha256", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_claim_evidence_derivations_support_verdict",
        "claim_evidence_derivations",
        "support_verdict IS NULL OR support_verdict IN "
        "('supported', 'unsupported', 'insufficient_evidence')",
    )
    op.create_foreign_key(
        "fk_claim_evidence_derivations_support_judge_run_id",
        "claim_evidence_derivations",
        "knowledge_operator_runs",
        ["support_judge_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_claim_evidence_derivations_support_verdict",
        "claim_evidence_derivations",
        ["support_verdict"],
    )
    op.create_index(
        "ix_claim_evidence_derivations_support_judge_run_id",
        "claim_evidence_derivations",
        ["support_judge_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_evidence_derivations_support_judge_run_id",
        table_name="claim_evidence_derivations",
    )
    op.drop_index(
        "ix_claim_evidence_derivations_support_verdict",
        table_name="claim_evidence_derivations",
    )
    op.drop_constraint(
        "fk_claim_evidence_derivations_support_judge_run_id",
        "claim_evidence_derivations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_claim_evidence_derivations_support_verdict",
        "claim_evidence_derivations",
        type_="check",
    )
    op.drop_column("claim_evidence_derivations", "support_judgment_sha256")
    op.drop_column("claim_evidence_derivations", "support_judgment")
    op.drop_column("claim_evidence_derivations", "support_judge_run_id")
    op.drop_column("claim_evidence_derivations", "support_score")
    op.drop_column("claim_evidence_derivations", "support_verdict")
