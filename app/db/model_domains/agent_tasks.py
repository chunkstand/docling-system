from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
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


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'blocked', 'awaiting_approval', 'rejected', 'queued', 'processing', "
            "'retry_wait', 'completed', 'failed'"
            ")",
            name="ck_agent_tasks_status",
        ),
        CheckConstraint(
            "side_effect_level IN ('read_only', 'draft_change', 'promotable')",
            name="ck_agent_tasks_side_effect_level",
        ),
        Index(
            "ix_agent_tasks_status_priority_next_attempt_at",
            "status",
            "priority",
            "next_attempt_at",
        ),
        Index("ix_agent_tasks_locked_at", "locked_at"),
        Index("ix_agent_tasks_parent_task_id", "parent_task_id"),
        Index("ix_agent_tasks_task_type_created_at", "task_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default=sql_text("100")
    )
    side_effect_level: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="read_only",
        server_default=sql_text("'read_only'"),
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    input_json: Mapped[dict] = mapped_column(
        "input",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    result_json: Mapped[dict] = mapped_column(
        "result",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    failure_artifact_path: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    workflow_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="v1", server_default=sql_text("'v1'")
    )
    tool_version: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    model_settings_json: Mapped[dict] = mapped_column(
        "model_settings",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(Text)
    approval_note: Mapped[str | None] = mapped_column(Text)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by: Mapped[str | None] = mapped_column(Text)
    rejection_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentTaskDependency(Base):
    __tablename__ = "agent_task_dependencies"
    __table_args__ = (
        CheckConstraint(
            "task_id <> depends_on_task_id",
            name="ck_agent_task_dependencies_not_self",
        ),
        CheckConstraint(
            "dependency_kind IN ("
            "'explicit', 'target_task', 'source_task', 'draft_task', 'verification_task'"
            ")",
            name="ck_agent_task_dependencies_dependency_kind",
        ),
        UniqueConstraint(
            "task_id",
            "depends_on_task_id",
            name="uq_agent_task_dependencies_task_depends_on",
        ),
        Index("ix_agent_task_dependencies_depends_on_task_id", "depends_on_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    dependency_kind: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="explicit",
        server_default=sql_text("'explicit'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskAttempt(Base):
    __tablename__ = "agent_task_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'abandoned')",
            name="ck_agent_task_attempts_status",
        ),
        UniqueConstraint("task_id", "attempt_number", name="uq_agent_task_attempts_task_attempt"),
        Index("ix_agent_task_attempts_task_id", "task_id"),
        Index("ix_agent_task_attempts_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(Text)
    input_json: Mapped[dict] = mapped_column(
        "input",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    result_json: Mapped[dict] = mapped_column(
        "result",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    cost_json: Mapped[dict] = mapped_column(
        "cost",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    performance_json: Mapped[dict] = mapped_column(
        "performance",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentTaskArtifact(Base):
    __tablename__ = "agent_task_artifacts"
    __table_args__ = (
        Index("ix_agent_task_artifacts_task_id", "task_id"),
        Index("ix_agent_task_artifacts_attempt_id", "attempt_id"),
        Index("ix_agent_task_artifacts_artifact_kind", "artifact_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_attempts.id", ondelete="SET NULL"),
    )
    artifact_kind: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskArtifactImmutabilityEvent(Base):
    __tablename__ = "agent_task_artifact_immutability_events"
    __table_args__ = (
        CheckConstraint(
            "event_kind IN ('mutation_blocked', 'supersession_attempt')",
            name="ck_agent_artifact_immut_events_event_kind",
        ),
        CheckConstraint(
            "mutation_operation IN ('UPDATE', 'DELETE', 'FREEZE_REUSE')",
            name="ck_agent_artifact_immut_events_mutation_op",
        ),
        Index(
            "ix_agent_artifact_immut_events_artifact_created",
            "artifact_id",
            "created_at",
        ),
        Index("ix_agent_artifact_immut_events_task_created", "task_id", "created_at"),
        Index("ix_agent_artifact_immut_events_kind", "event_kind"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_kind: Mapped[str] = mapped_column(Text, nullable=False)
    mutation_operation: Mapped[str] = mapped_column(Text, nullable=False)
    frozen_artifact_kind: Mapped[str | None] = mapped_column(Text)
    attempted_artifact_kind: Mapped[str | None] = mapped_column(Text)
    frozen_storage_path: Mapped[str | None] = mapped_column(Text)
    attempted_storage_path: Mapped[str | None] = mapped_column(Text)
    frozen_payload_sha256: Mapped[str | None] = mapped_column(Text)
    attempted_payload_sha256: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskOutcome(Base):
    __tablename__ = "agent_task_outcomes"
    __table_args__ = (
        CheckConstraint(
            "outcome_label IN ('useful', 'not_useful', 'correct', 'incorrect')",
            name="ck_agent_task_outcomes_outcome_label",
        ),
        UniqueConstraint(
            "task_id",
            "outcome_label",
            "created_by",
            name="uq_agent_task_outcomes_task_label_actor",
        ),
        Index("ix_agent_task_outcomes_task_id", "task_id"),
        Index("ix_agent_task_outcomes_outcome_label", "outcome_label"),
        Index("ix_agent_task_outcomes_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    outcome_label: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskVerification(Base):
    __tablename__ = "agent_task_verifications"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('passed', 'failed', 'error')",
            name="ck_agent_task_verifications_outcome",
        ),
        Index("ix_agent_task_verifications_target_task_id", "target_task_id"),
        Index("ix_agent_task_verifications_verification_task_id", "verification_task_id"),
        Index("ix_agent_task_verifications_verifier_type", "verifier_type"),
        Index("ix_agent_task_verifications_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    verification_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    verifier_type: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
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
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeOperatorRun(Base):
    __tablename__ = "knowledge_operator_runs"
    __table_args__ = (
        CheckConstraint(
            "operator_kind IN ("
            "'parse', 'embed', 'retrieve', 'rerank', 'judge', "
            "'generate', 'verify', 'export', 'orchestrate'"
            ")",
            name="ck_knowledge_operator_runs_operator_kind",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed', 'skipped')",
            name="ck_knowledge_operator_runs_status",
        ),
        Index("ix_knowledge_operator_runs_created_at", "created_at"),
        Index("ix_knowledge_operator_runs_search_request_id", "search_request_id"),
        Index("ix_knowledge_operator_runs_agent_task_id", "agent_task_id"),
        Index("ix_knowledge_operator_runs_parent_id", "parent_operator_run_id"),
        Index("ix_knowledge_operator_runs_kind_created_at", "operator_kind", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_operator_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="SET NULL"),
    )
    operator_kind: Mapped[str] = mapped_column(Text, nullable=False)
    operator_name: Mapped[str] = mapped_column(Text, nullable=False)
    operator_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="SET NULL"),
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    agent_task_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_attempts.id", ondelete="SET NULL"),
    )
    model_name: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(Text)
    prompt_sha256: Mapped[str | None] = mapped_column(Text)
    config_sha256: Mapped[str | None] = mapped_column(Text)
    input_sha256: Mapped[str | None] = mapped_column(Text)
    output_sha256: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeOperatorInput(Base):
    __tablename__ = "knowledge_operator_inputs"
    __table_args__ = (
        Index("ix_knowledge_operator_inputs_operator_run_id", "operator_run_id"),
        Index("ix_knowledge_operator_inputs_source", "source_table", "source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    input_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    artifact_path: Mapped[str | None] = mapped_column(Text)
    artifact_sha256: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeOperatorOutput(Base):
    __tablename__ = "knowledge_operator_outputs"
    __table_args__ = (
        Index("ix_knowledge_operator_outputs_operator_run_id", "operator_run_id"),
        Index("ix_knowledge_operator_outputs_target", "target_table", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    output_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    output_kind: Mapped[str] = mapped_column(Text, nullable=False)
    target_table: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    artifact_path: Mapped[str | None] = mapped_column(Text)
    artifact_sha256: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
