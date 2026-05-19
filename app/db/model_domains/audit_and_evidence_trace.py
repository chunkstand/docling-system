from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class EvidenceTraceNode(Base):
    __tablename__ = "evidence_trace_nodes"
    __table_args__ = (
        CheckConstraint(
            "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
            "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
            name="ck_evidence_trace_nodes_single_owner",
        ),
        UniqueConstraint(
            "evidence_manifest_id",
            "node_key",
            name="uq_evidence_trace_nodes_manifest_node_key",
        ),
        UniqueConstraint(
            "evidence_package_export_id",
            "node_key",
            name="uq_evidence_trace_nodes_export_node_key",
        ),
        Index("ix_evidence_trace_nodes_manifest_id", "evidence_manifest_id"),
        Index("ix_evidence_trace_nodes_export_id", "evidence_package_export_id"),
        Index("ix_evidence_trace_nodes_node_kind", "node_kind"),
        Index("ix_evidence_trace_nodes_source", "source_table", "source_id"),
        Index("ix_evidence_trace_nodes_source_ref", "source_table", "source_ref"),
        Index("ix_evidence_trace_nodes_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="CASCADE"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
    )
    node_key: Mapped[str] = mapped_column(Text, nullable=False)
    node_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_ref: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceTraceEdge(Base):
    __tablename__ = "evidence_trace_edges"
    __table_args__ = (
        CheckConstraint(
            "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
            "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
            name="ck_evidence_trace_edges_single_owner",
        ),
        UniqueConstraint(
            "evidence_manifest_id",
            "edge_key",
            name="uq_evidence_trace_edges_manifest_edge_key",
        ),
        UniqueConstraint(
            "evidence_package_export_id",
            "edge_key",
            name="uq_evidence_trace_edges_export_edge_key",
        ),
        Index("ix_evidence_trace_edges_manifest_id", "evidence_manifest_id"),
        Index("ix_evidence_trace_edges_export_id", "evidence_package_export_id"),
        Index("ix_evidence_trace_edges_edge_kind", "edge_kind"),
        Index("ix_evidence_trace_edges_from_node_id", "from_node_id"),
        Index("ix_evidence_trace_edges_to_node_id", "to_node_id"),
        Index("ix_evidence_trace_edges_derivation_sha256", "derivation_sha256"),
        Index("ix_evidence_trace_edges_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="CASCADE"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
    )
    edge_key: Mapped[str] = mapped_column(Text, nullable=False)
    edge_kind: Mapped[str] = mapped_column(Text, nullable=False)
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_trace_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_trace_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_node_key: Mapped[str] = mapped_column(Text, nullable=False)
    to_node_key: Mapped[str] = mapped_column(Text, nullable=False)
    derivation_sha256: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimEvidenceDerivation(Base):
    __tablename__ = "claim_evidence_derivations"
    __table_args__ = (
        CheckConstraint(
            "support_verdict IS NULL OR support_verdict IN "
            "('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_evidence_derivations_support_verdict",
        ),
        Index("ix_claim_evidence_derivations_export_id", "evidence_package_export_id"),
        Index("ix_claim_evidence_derivations_agent_task_id", "agent_task_id"),
        Index("ix_claim_evidence_derivations_claim_id", "claim_id"),
        Index("ix_claim_evidence_derivations_derivation_sha256", "derivation_sha256"),
        Index("ix_claim_evidence_derivations_support_verdict", "support_verdict"),
        Index("ix_claim_evidence_derivations_support_judge_run_id", "support_judge_run_id"),
        Index(
            "ix_claim_evidence_derivations_provenance_lock_sha",
            "provenance_lock_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_package_export_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    claim_id: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str | None] = mapped_column(Text)
    derivation_rule: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_card_ids_json: Mapped[list] = mapped_column(
        "evidence_card_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    graph_edge_ids_json: Mapped[list] = mapped_column(
        "graph_edge_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    fact_ids_json: Mapped[list] = mapped_column(
        "fact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    assertion_ids_json: Mapped[list] = mapped_column(
        "assertion_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_document_ids_json: Mapped[list] = mapped_column(
        "source_document_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_snapshot_sha256s_json: Mapped[list] = mapped_column(
        "source_snapshot_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_search_request_ids_json: Mapped[list] = mapped_column(
        "source_search_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_search_request_result_ids_json: Mapped[list] = mapped_column(
        "source_search_request_result_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_package_export_ids_json: Mapped[list] = mapped_column(
        "source_evidence_package_export_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_package_sha256s_json: Mapped[list] = mapped_column(
        "source_evidence_package_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_trace_sha256s_json: Mapped[list] = mapped_column(
        "source_evidence_trace_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    semantic_ontology_snapshot_ids_json: Mapped[list] = mapped_column(
        "semantic_ontology_snapshot_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    semantic_graph_snapshot_ids_json: Mapped[list] = mapped_column(
        "semantic_graph_snapshot_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    retrieval_reranker_artifact_ids_json: Mapped[list] = mapped_column(
        "retrieval_reranker_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    search_harness_release_ids_json: Mapped[list] = mapped_column(
        "search_harness_release_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    release_audit_bundle_ids_json: Mapped[list] = mapped_column(
        "release_audit_bundle_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    release_validation_receipt_ids_json: Mapped[list] = mapped_column(
        "release_validation_receipt_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    provenance_lock_json: Mapped[dict] = mapped_column(
        "provenance_lock",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    provenance_lock_sha256: Mapped[str | None] = mapped_column(Text)
    support_verdict: Mapped[str | None] = mapped_column(Text)
    support_score: Mapped[float | None] = mapped_column(Float)
    support_judge_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="SET NULL"),
    )
    support_judgment_json: Mapped[dict] = mapped_column(
        "support_judgment",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    support_judgment_sha256: Mapped[str | None] = mapped_column(Text)
    evidence_package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    derivation_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
