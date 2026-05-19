from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SemanticGovernanceEvent(Base):
    __tablename__ = "semantic_governance_events"
    __table_args__ = (
        CheckConstraint(
            "event_kind IN ("
            "'ontology_snapshot_recorded', "
            "'ontology_snapshot_activated', "
            "'semantic_graph_snapshot_recorded', "
            "'semantic_graph_snapshot_activated', "
            "'search_harness_release_recorded', "
            "'search_harness_release_readiness_assessed', "
            "'technical_report_prov_export_frozen', "
            "'technical_report_readiness_db_gate_recorded', "
            "'technical_report_claim_retrieval_feedback_recorded', "
            "'retrieval_training_run_materialized', "
            "'retrieval_learning_candidate_evaluated', "
            "'retrieval_reranker_artifact_materialized', "
            "'claim_support_policy_activated', "
            "'claim_support_policy_impact_replay_closed', "
            "'claim_support_policy_impact_replay_escalated', "
            "'claim_support_policy_impact_fixture_promoted', "
            "'claim_support_replay_alert_fixture_coverage_waiver_closed', "
            "'claim_support_replay_alert_fixture_corpus_snapshot_activated'"
            ")",
            name="ck_semantic_governance_events_event_kind",
        ),
        UniqueConstraint(
            "deduplication_key",
            name="uq_semantic_governance_events_dedup_key",
        ),
        UniqueConstraint(
            "event_sequence",
            name="uq_semantic_governance_events_sequence",
        ),
        Index(
            "ix_semantic_governance_events_scope_created",
            "governance_scope",
            "created_at",
        ),
        Index("ix_semantic_governance_events_kind_created", "event_kind", "created_at"),
        Index(
            "ix_semantic_governance_events_subject",
            "subject_table",
            "subject_id",
        ),
        Index("ix_semantic_governance_events_task_created", "task_id", "created_at"),
        Index(
            "ix_semantic_governance_events_ontology",
            "ontology_snapshot_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_graph",
            "semantic_graph_snapshot_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_release",
            "search_harness_release_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_manifest",
            "evidence_manifest_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_artifact",
            "agent_task_artifact_id",
            "created_at",
        ),
        Index("ix_semantic_governance_events_receipt_sha", "receipt_sha256"),
        Index("ix_semantic_governance_events_payload_sha", "payload_sha256"),
        Index("ix_semantic_governance_events_event_hash", "event_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_sequence: Mapped[int] = mapped_column(Integer, Identity(), nullable=False)
    event_kind: Mapped[str] = mapped_column(Text, nullable=False)
    governance_scope: Mapped[str] = mapped_column(Text, nullable=False)
    subject_table: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    semantic_graph_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_graph_snapshots.id", ondelete="SET NULL"),
    )
    search_harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="SET NULL"),
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="SET NULL"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="SET NULL"),
    )
    agent_task_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    previous_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="RESTRICT"),
    )
    previous_event_hash: Mapped[str | None] = mapped_column(Text)
    receipt_sha256: Mapped[str | None] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    event_hash: Mapped[str] = mapped_column(Text, nullable=False)
    deduplication_key: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(
        "event_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
