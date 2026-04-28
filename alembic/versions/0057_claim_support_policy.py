"""Add claim support fixture and calibration policy governance.

Revision ID: 0057_claim_support_policy
Revises: 0056_claim_support_evaluations
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0057_claim_support_policy"
down_revision: str | Sequence[str] | None = "0056_claim_support_evaluations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_support_fixture_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fixture_set_name", sa.Text(), nullable=False),
        sa.Column("fixture_set_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("fixture_set_sha256", sa.Text(), nullable=False),
        sa.Column("fixture_count", sa.Integer(), nullable=False),
        sa.Column(
            "hard_case_kinds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "verdicts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "fixtures",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'retired')",
            name="ck_claim_support_fixture_sets_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fixture_set_name",
            "fixture_set_version",
            "fixture_set_sha256",
            name="uq_claim_support_fixture_sets_identity",
        ),
    )
    op.create_index(
        "ix_claim_support_fixture_sets_name_version",
        "claim_support_fixture_sets",
        ["fixture_set_name", "fixture_set_version"],
    )
    op.create_index(
        "ix_claim_support_fixture_sets_status",
        "claim_support_fixture_sets",
        ["status"],
    )
    op.create_index(
        "ix_claim_support_fixture_sets_sha",
        "claim_support_fixture_sets",
        ["fixture_set_sha256"],
    )

    op.create_table(
        "claim_support_calibration_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_name", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("policy_sha256", sa.Text(), nullable=False),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("min_hard_case_kind_count", sa.Integer(), nullable=False),
        sa.Column(
            "required_hard_case_kinds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "required_verdicts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "thresholds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "policy_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'retired')",
            name="ck_claim_support_calibration_policies_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_name",
            "policy_version",
            "policy_sha256",
            name="uq_claim_support_calibration_policies_identity",
        ),
    )
    op.create_index(
        "ix_claim_support_calibration_policies_name_version",
        "claim_support_calibration_policies",
        ["policy_name", "policy_version"],
    )
    op.create_index(
        "ix_claim_support_calibration_policies_status",
        "claim_support_calibration_policies",
        ["status"],
    )
    op.create_index(
        "ix_claim_support_calibration_policies_sha",
        "claim_support_calibration_policies",
        ["policy_sha256"],
    )

    op.add_column(
        "claim_support_evaluations",
        sa.Column("fixture_set_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "claim_support_evaluations",
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "claim_support_evaluations",
        sa.Column("fixture_set_version", sa.Text(), nullable=True),
    )
    op.add_column(
        "claim_support_evaluations",
        sa.Column("policy_name", sa.Text(), nullable=True),
    )
    op.add_column(
        "claim_support_evaluations",
        sa.Column("policy_version", sa.Text(), nullable=True),
    )
    op.add_column(
        "claim_support_evaluations",
        sa.Column("policy_sha256", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_claim_support_evaluations_fixture_set",
        "claim_support_evaluations",
        "claim_support_fixture_sets",
        ["fixture_set_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_claim_support_evaluations_policy",
        "claim_support_evaluations",
        "claim_support_calibration_policies",
        ["policy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_claim_support_evaluations_fixture_set_id",
        "claim_support_evaluations",
        ["fixture_set_id"],
    )
    op.create_index(
        "ix_claim_support_evaluations_policy_id",
        "claim_support_evaluations",
        ["policy_id"],
    )
    op.create_index(
        "ix_claim_support_evaluations_policy_sha",
        "claim_support_evaluations",
        ["policy_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_support_evaluations_policy_sha",
        table_name="claim_support_evaluations",
    )
    op.drop_index(
        "ix_claim_support_evaluations_policy_id",
        table_name="claim_support_evaluations",
    )
    op.drop_index(
        "ix_claim_support_evaluations_fixture_set_id",
        table_name="claim_support_evaluations",
    )
    op.drop_constraint(
        "fk_claim_support_evaluations_policy",
        "claim_support_evaluations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_claim_support_evaluations_fixture_set",
        "claim_support_evaluations",
        type_="foreignkey",
    )
    op.drop_column("claim_support_evaluations", "policy_sha256")
    op.drop_column("claim_support_evaluations", "policy_version")
    op.drop_column("claim_support_evaluations", "policy_name")
    op.drop_column("claim_support_evaluations", "fixture_set_version")
    op.drop_column("claim_support_evaluations", "policy_id")
    op.drop_column("claim_support_evaluations", "fixture_set_id")

    op.drop_index(
        "ix_claim_support_calibration_policies_sha",
        table_name="claim_support_calibration_policies",
    )
    op.drop_index(
        "ix_claim_support_calibration_policies_status",
        table_name="claim_support_calibration_policies",
    )
    op.drop_index(
        "ix_claim_support_calibration_policies_name_version",
        table_name="claim_support_calibration_policies",
    )
    op.drop_table("claim_support_calibration_policies")

    op.drop_index(
        "ix_claim_support_fixture_sets_sha",
        table_name="claim_support_fixture_sets",
    )
    op.drop_index(
        "ix_claim_support_fixture_sets_status",
        table_name="claim_support_fixture_sets",
    )
    op.drop_index(
        "ix_claim_support_fixture_sets_name_version",
        table_name="claim_support_fixture_sets",
    )
    op.drop_table("claim_support_fixture_sets")
