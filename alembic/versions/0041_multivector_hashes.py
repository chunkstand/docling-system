"""add multivector embedding hashes

Revision ID: 0041_multivector_hashes
Revises: 0040_span_multivectors
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0041_multivector_hashes"
down_revision: str | Sequence[str] | None = "0040_span_multivectors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "retrieval_evidence_span_multivectors",
        sa.Column("embedding_sha256", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_retrieval_span_multivectors_embedding_sha256",
        "retrieval_evidence_span_multivectors",
        ["embedding_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_span_multivectors_embedding_sha256",
        table_name="retrieval_evidence_span_multivectors",
    )
    op.drop_column("retrieval_evidence_span_multivectors", "embedding_sha256")
