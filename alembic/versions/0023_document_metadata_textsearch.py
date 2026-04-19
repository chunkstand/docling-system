"""add document metadata textsearch

Revision ID: 0023_doc_metadata_textsearch
Revises: 0022_api_idempotency_keys
Create Date: 2026-04-18 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Keep revision ids within Alembic's default alembic_version.version_num VARCHAR(32) contract.
revision: str = "0023_doc_metadata_textsearch"
down_revision: str | Sequence[str] | None = "0022_api_idempotency_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DOCUMENT_METADATA_NORMALIZE_SQL = """
trim(
    regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        coalesce(title, '') || ' ' ||
                        regexp_replace(coalesce(source_filename, ''), '\\.[^.]+$', '', 'g'),
                        '([A-Z]+)([A-Z][a-z])', '\\1 \\2', 'g'
                    ),
                    '([a-z0-9])([A-Z])', '\\1 \\2', 'g'
                ),
                '([A-Za-z])([0-9])', '\\1 \\2', 'g'
            ),
            '([0-9])([A-Za-z])', '\\1 \\2', 'g'
        ),
        '[^A-Za-z0-9]+', ' ', 'g'
    )
)
""".strip()
DOCUMENT_METADATA_TEXTSEARCH_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    f"setweight(to_tsvector('simple', {DOCUMENT_METADATA_NORMALIZE_SQL}), 'A')"
)


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "metadata_textsearch",
            postgresql.TSVECTOR(),
            sa.Computed(DOCUMENT_METADATA_TEXTSEARCH_SQL, persisted=True),
        ),
    )
    op.create_index(
        "ix_documents_metadata_textsearch",
        "documents",
        ["metadata_textsearch"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_documents_metadata_textsearch", table_name="documents")
    op.drop_column("documents", "metadata_textsearch")
