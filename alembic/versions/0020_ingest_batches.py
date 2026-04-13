"""add ingest batch tracking

Revision ID: 0020_ingest_batches
Revises: 0019_search_replay_source_type
Create Date: 2026-04-14 00:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020_ingest_batches"
down_revision: str | Sequence[str] | None = "0019_search_replay_source_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=True),
        sa.Column("recursive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("queued_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "recovery_queued_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_type IN ('local_directory', 'zip_upload')",
            name="ck_ingest_batches_source_type",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_errors', 'failed')",
            name="ck_ingest_batches_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingest_batches_created_at", "ingest_batches", ["created_at"])
    op.create_index(
        "ix_ingest_batches_status_created_at",
        "ingest_batches",
        ["status", "created_at"],
    )

    op.create_table(
        "ingest_batch_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("duplicate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("recovery_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'queued_recovery', 'duplicate', 'failed')",
            name="ck_ingest_batch_items_status",
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["ingest_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id",
            "relative_path",
            name="uq_ingest_batch_items_batch_relative_path",
        ),
    )
    op.create_index("ix_ingest_batch_items_batch_id", "ingest_batch_items", ["batch_id"])
    op.create_index("ix_ingest_batch_items_document_id", "ingest_batch_items", ["document_id"])
    op.create_index("ix_ingest_batch_items_run_id", "ingest_batch_items", ["run_id"])
    op.create_index("ix_ingest_batch_items_status", "ingest_batch_items", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingest_batch_items_status", table_name="ingest_batch_items")
    op.drop_index("ix_ingest_batch_items_run_id", table_name="ingest_batch_items")
    op.drop_index("ix_ingest_batch_items_document_id", table_name="ingest_batch_items")
    op.drop_index("ix_ingest_batch_items_batch_id", table_name="ingest_batch_items")
    op.drop_table("ingest_batch_items")
    op.drop_index("ix_ingest_batches_status_created_at", table_name="ingest_batches")
    op.drop_index("ix_ingest_batches_created_at", table_name="ingest_batches")
    op.drop_table("ingest_batches")
