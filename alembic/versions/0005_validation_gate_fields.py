"""add validation gate fields and validating status

Revision ID: 0005_validation_gate_fields
Revises: 0004_yaml_artifacts
Create Date: 2026-04-09 22:40:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_validation_gate_fields"
down_revision = "0004_yaml_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_runs", sa.Column("table_count", sa.Integer(), nullable=True))
    op.add_column("document_runs", sa.Column("validation_status", sa.Text(), nullable=True))
    op.add_column(
        "document_runs",
        sa.Column(
            "validation_results",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.drop_constraint("ck_document_runs_status", "document_runs", type_="check")
    op.create_check_constraint(
        "ck_document_runs_status",
        "document_runs",
        "status IN ('queued', 'processing', 'validating', 'retry_wait', 'completed', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_document_runs_status", "document_runs", type_="check")
    op.create_check_constraint(
        "ck_document_runs_status",
        "document_runs",
        "status IN ('queued', 'processing', 'retry_wait', 'completed', 'failed')",
    )

    op.drop_column("document_runs", "validation_results")
    op.drop_column("document_runs", "validation_status")
    op.drop_column("document_runs", "table_count")
