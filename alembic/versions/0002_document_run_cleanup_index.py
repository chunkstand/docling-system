"""add cleanup index for document runs

Revision ID: 0002_document_run_cleanup_index
Revises: 0001_initial
Create Date: 2026-04-09 00:30:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0002_document_run_cleanup_index"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_document_runs_status_completed_at",
        "document_runs",
        ["status", "completed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_runs_status_completed_at", table_name="document_runs")
