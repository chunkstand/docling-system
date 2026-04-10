"""rename markdown artifact columns to yaml

Revision ID: 0004_yaml_artifacts
Revises: 0003_document_tables
Create Date: 2026-04-09 15:35:00.000000
"""
from __future__ import annotations

from alembic import op


revision = "0004_yaml_artifacts"
down_revision = "0003_document_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("document_runs", "markdown_path", new_column_name="yaml_path")
    op.alter_column("document_tables", "markdown_path", new_column_name="yaml_path")


def downgrade() -> None:
    op.alter_column("document_tables", "yaml_path", new_column_name="markdown_path")
    op.alter_column("document_runs", "yaml_path", new_column_name="markdown_path")
