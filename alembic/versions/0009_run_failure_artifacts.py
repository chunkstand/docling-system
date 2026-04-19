"""add run failure artifact fields

Revision ID: 0009_run_failure_artifacts
Revises: 0008_run_evaluations
Create Date: 2026-04-12 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009_run_failure_artifacts"
down_revision = "0008_run_evaluations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_runs", sa.Column("failure_stage", sa.Text(), nullable=True))
    op.add_column("document_runs", sa.Column("failure_artifact_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_runs", "failure_artifact_path")
    op.drop_column("document_runs", "failure_stage")
