from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.model_domains.retrieval_learning_examples import RetrievalJudgmentSet


class RetrievalTrainingRun(Base):
    __tablename__ = "retrieval_training_runs"
    __table_args__ = (
        CheckConstraint(
            "run_kind IN ('materialized_training_dataset')",
            name="ck_retrieval_training_runs_run_kind",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_retrieval_training_runs_status",
        ),
        Index("ix_retrieval_training_runs_judgment_set", "judgment_set_id"),
        Index("ix_retrieval_training_runs_release", "search_harness_release_id"),
        Index("ix_retrieval_training_runs_governance", "semantic_governance_event_id"),
        Index("ix_retrieval_training_runs_dataset_sha", "training_dataset_sha256"),
        Index("ix_retrieval_training_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    judgment_set: Mapped[RetrievalJudgmentSet] = relationship(
        "RetrievalJudgmentSet",
        foreign_keys=[judgment_set_id],
    )
    run_kind: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="materialized_training_dataset",
        server_default=sql_text("'materialized_training_dataset'"),
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    search_harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="SET NULL"),
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    training_dataset_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    training_payload_json: Mapped[dict] = mapped_column(
        "training_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    example_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalLearningCandidateEvaluation(Base):
    __tablename__ = "retrieval_learning_candidate_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_retrieval_learning_candidate_evaluations_status",
        ),
        CheckConstraint(
            "gate_outcome IS NULL OR gate_outcome IN ('passed', 'failed', 'error')",
            name="ck_retrieval_learning_candidate_evaluations_gate_outcome",
        ),
        UniqueConstraint(
            "retrieval_training_run_id",
            "search_harness_evaluation_id",
            name="uq_retrieval_learning_candidate_training_eval",
        ),
        Index(
            "ix_retrieval_learning_candidate_training",
            "retrieval_training_run_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_judgment_set",
            "judgment_set_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_evaluation",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_retrieval_learning_candidate_release",
            "search_harness_release_id",
        ),
        Index(
            "ix_retrieval_learning_candidate_governance",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_retrieval_learning_candidate_dataset_sha",
            "training_dataset_sha256",
        ),
        Index(
            "ix_retrieval_learning_candidate_harness_created",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_outcome_created",
            "gate_outcome",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_package_sha",
            "learning_package_sha256",
        ),
        Index("ix_retrieval_learning_candidate_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_training_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retrieval_training_run: Mapped[RetrievalTrainingRun] = relationship(
        "RetrievalTrainingRun",
        foreign_keys=[retrieval_training_run_id],
    )
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    judgment_set: Mapped[RetrievalJudgmentSet] = relationship(
        "RetrievalJudgmentSet",
        foreign_keys=[judgment_set_id],
    )
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    training_dataset_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    training_example_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    gate_outcome: Mapped[str | None] = mapped_column(Text)
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evaluation_snapshot_json: Mapped[dict] = mapped_column(
        "evaluation_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    release_snapshot_json: Mapped[dict] = mapped_column(
        "release_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    learning_package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalRerankerArtifact(Base):
    __tablename__ = "retrieval_reranker_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_kind IN ('linear_feature_weight_candidate')",
            name="ck_retrieval_reranker_artifacts_kind",
        ),
        CheckConstraint(
            "status IN ('evaluated', 'failed')",
            name="ck_retrieval_reranker_artifacts_status",
        ),
        CheckConstraint(
            "gate_outcome IS NULL OR gate_outcome IN ('passed', 'failed', 'error')",
            name="ck_retrieval_reranker_artifacts_gate_outcome",
        ),
        UniqueConstraint(
            "retrieval_learning_candidate_evaluation_id",
            name="uq_retrieval_reranker_artifacts_candidate_eval",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_training_created",
            "retrieval_training_run_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_candidate_eval",
            "retrieval_learning_candidate_evaluation_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_evaluation",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_release",
            "search_harness_release_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_governance",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_candidate_created",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_gate_created",
            "gate_outcome",
            "created_at",
        ),
        Index("ix_retrieval_reranker_artifacts_artifact_sha", "artifact_sha256"),
        Index(
            "ix_retrieval_reranker_artifacts_impact_sha",
            "change_impact_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_training_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retrieval_training_run: Mapped[RetrievalTrainingRun] = relationship(
        "RetrievalTrainingRun",
        foreign_keys=[retrieval_training_run_id],
    )
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    judgment_set: Mapped[RetrievalJudgmentSet] = relationship(
        "RetrievalJudgmentSet",
        foreign_keys=[judgment_set_id],
    )
    retrieval_learning_candidate_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_learning_candidate_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retrieval_learning_candidate_evaluation: Mapped[RetrievalLearningCandidateEvaluation] = (
        relationship(
            "RetrievalLearningCandidateEvaluation",
            foreign_keys=[retrieval_learning_candidate_evaluation_id],
        )
    )
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    artifact_kind: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_name: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    gate_outcome: Mapped[str | None] = mapped_column(Text)
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    training_dataset_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    training_example_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    feature_weights_json: Mapped[dict] = mapped_column(
        "feature_weights",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    harness_overrides_json: Mapped[dict] = mapped_column(
        "harness_overrides",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    artifact_payload_json: Mapped[dict] = mapped_column(
        "artifact_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_snapshot_json: Mapped[dict] = mapped_column(
        "evaluation_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    release_snapshot_json: Mapped[dict] = mapped_column(
        "release_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    change_impact_report_json: Mapped[dict] = mapped_column(
        "change_impact_report",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    artifact_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    change_impact_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
