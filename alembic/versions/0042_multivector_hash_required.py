"""require multivector embedding hashes

Revision ID: 0042_multivector_hash_required
Revises: 0041_multivector_hashes
Create Date: 2026-04-27 00:00:00.000000
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0042_multivector_hash_required"
down_revision: str | Sequence[str] | None = "0041_multivector_hashes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _embedding_sha256_from_text(embedding_text: str) -> str:
    stripped = embedding_text.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]
    embedding = [float(value) for value in stripped.split(",") if value]
    payload = {
        "schema_name": "retrieval_evidence_span_multivector_embedding",
        "schema_version": "1.0",
        "embedding": embedding,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, embedding::text AS embedding_text
            FROM retrieval_evidence_span_multivectors
            WHERE embedding_sha256 IS NULL
            """
        )
    )
    for row in rows:
        bind.execute(
            sa.text(
                """
                UPDATE retrieval_evidence_span_multivectors
                SET embedding_sha256 = :embedding_sha256
                WHERE id = :id
                """
            ),
            {
                "id": row.id,
                "embedding_sha256": _embedding_sha256_from_text(row.embedding_text),
            },
        )
    op.alter_column(
        "retrieval_evidence_span_multivectors",
        "embedding_sha256",
        existing_type=sa.Text(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "retrieval_evidence_span_multivectors",
        "embedding_sha256",
        existing_type=sa.Text(),
        nullable=True,
    )
