"""add api idempotency key storage

Revision ID: 0022_api_idempotency_keys
Revises: 0021_agent_task_dependency_kind
Create Date: 2026-04-18 15:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022_api_idempotency_keys"
down_revision: str | Sequence[str] | None = "0021_agent_task_dependency_kind"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_fingerprint", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column(
            "response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "idempotency_key", name="uq_api_idempotency_keys_scope_key"),
    )
    op.create_index(
        "ix_api_idempotency_keys_created_at",
        "api_idempotency_keys",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_api_idempotency_keys_created_at", table_name="api_idempotency_keys")
    op.drop_table("api_idempotency_keys")
