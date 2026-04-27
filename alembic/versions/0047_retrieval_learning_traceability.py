"""add retrieval learning traceability columns

Revision ID: 0047_retrieval_learning_trace
Revises: 0046_retrieval_judgment_ledger
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0047_retrieval_learning_trace"
down_revision: str | Sequence[str] | None = "0046_retrieval_judgment_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "retrieval_judgments",
        sa.Column("source_payload_sha256", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_retrieval_judgments_source_payload_sha",
        "retrieval_judgments",
        ["source_payload_sha256"],
    )

    op.add_column(
        "retrieval_hard_negatives",
        sa.Column("search_replay_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "retrieval_hard_negatives",
        sa.Column("evaluation_query_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "retrieval_hard_negatives",
        sa.Column("source_search_request_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "retrieval_hard_negatives",
        sa.Column("expected_result_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "retrieval_hard_negatives",
        sa.Column("expected_top_n", sa.Integer(), nullable=True),
    )
    op.add_column(
        "retrieval_hard_negatives",
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_hard_negatives",
        sa.Column("source_payload_sha256", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_retrieval_hard_negatives_replay_run",
        "retrieval_hard_negatives",
        "search_replay_runs",
        ["search_replay_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_retrieval_hard_negatives_evaluation_query",
        "retrieval_hard_negatives",
        "document_run_evaluation_queries",
        ["evaluation_query_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_retrieval_hard_negatives_source_search_request",
        "retrieval_hard_negatives",
        "search_requests",
        ["source_search_request_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_retrieval_hard_negatives_source_request",
        "retrieval_hard_negatives",
        ["source_search_request_id"],
    )
    op.create_index(
        "ix_retrieval_hard_negatives_source_payload_sha",
        "retrieval_hard_negatives",
        ["source_payload_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_hard_negatives_source_payload_sha",
        table_name="retrieval_hard_negatives",
    )
    op.drop_index(
        "ix_retrieval_hard_negatives_source_request",
        table_name="retrieval_hard_negatives",
    )
    op.drop_constraint(
        "fk_retrieval_hard_negatives_source_search_request",
        "retrieval_hard_negatives",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_retrieval_hard_negatives_evaluation_query",
        "retrieval_hard_negatives",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_retrieval_hard_negatives_replay_run",
        "retrieval_hard_negatives",
        type_="foreignkey",
    )
    op.drop_column("retrieval_hard_negatives", "source_payload_sha256")
    op.drop_column("retrieval_hard_negatives", "evidence_refs")
    op.drop_column("retrieval_hard_negatives", "expected_top_n")
    op.drop_column("retrieval_hard_negatives", "expected_result_type")
    op.drop_column("retrieval_hard_negatives", "source_search_request_id")
    op.drop_column("retrieval_hard_negatives", "evaluation_query_id")
    op.drop_column("retrieval_hard_negatives", "search_replay_run_id")

    op.drop_index(
        "ix_retrieval_judgments_source_payload_sha",
        table_name="retrieval_judgments",
    )
    op.drop_column("retrieval_judgments", "source_payload_sha256")
