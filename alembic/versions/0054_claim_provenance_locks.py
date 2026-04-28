"""add technical report claim provenance locks

Revision ID: 0054_claim_provenance_locks
Revises: 0053_reranker_artifacts
Create Date: 2026-04-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0054_claim_provenance_locks"
down_revision: str | Sequence[str] | None = "0053_reranker_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb_column(name: str, default_sql: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text(default_sql),
        nullable=False,
    )


def upgrade() -> None:
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("source_search_request_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("source_search_request_result_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("source_evidence_package_export_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("source_evidence_package_sha256s", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("source_evidence_trace_sha256s", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("semantic_ontology_snapshot_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("semantic_graph_snapshot_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("retrieval_reranker_artifact_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("search_harness_release_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("release_audit_bundle_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("release_validation_receipt_ids", "'[]'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        _jsonb_column("provenance_lock", "'{}'::jsonb"),
    )
    op.add_column(
        "claim_evidence_derivations",
        sa.Column("provenance_lock_sha256", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_claim_evidence_derivations_provenance_lock_sha",
        "claim_evidence_derivations",
        ["provenance_lock_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_evidence_derivations_provenance_lock_sha",
        table_name="claim_evidence_derivations",
    )
    op.drop_column("claim_evidence_derivations", "provenance_lock_sha256")
    op.drop_column("claim_evidence_derivations", "provenance_lock")
    op.drop_column("claim_evidence_derivations", "release_validation_receipt_ids")
    op.drop_column("claim_evidence_derivations", "release_audit_bundle_ids")
    op.drop_column("claim_evidence_derivations", "search_harness_release_ids")
    op.drop_column("claim_evidence_derivations", "retrieval_reranker_artifact_ids")
    op.drop_column("claim_evidence_derivations", "semantic_graph_snapshot_ids")
    op.drop_column("claim_evidence_derivations", "semantic_ontology_snapshot_ids")
    op.drop_column("claim_evidence_derivations", "source_evidence_trace_sha256s")
    op.drop_column("claim_evidence_derivations", "source_evidence_package_sha256s")
    op.drop_column("claim_evidence_derivations", "source_evidence_package_export_ids")
    op.drop_column("claim_evidence_derivations", "source_search_request_result_ids")
    op.drop_column("claim_evidence_derivations", "source_search_request_ids")
