from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class EvalObservation(Base):
    __tablename__ = "eval_observations"
    __table_args__ = (
        CheckConstraint(
            "surface IN ("
            "'document_evaluation', "
            "'search_request', "
            "'chat_answer', "
            "'search_replay', "
            "'harness_evaluation', "
            "'agent_task'"
            ")",
            name="ck_eval_observations_surface",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_eval_observations_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'resolved', 'suppressed')",
            name="ck_eval_observations_status",
        ),
        UniqueConstraint("observation_key", name="uq_eval_observations_observation_key"),
        Index("ix_eval_observations_surface_last_seen", "surface", "last_seen_at"),
        Index("ix_eval_observations_status_last_seen", "status", "last_seen_at"),
        Index("ix_eval_observations_document_id", "document_id"),
        Index("ix_eval_observations_search_request_id", "search_request_id"),
        Index("ix_eval_observations_evaluation_id", "evaluation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_key: Mapped[str] = mapped_column(Text, nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    subject_kind: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default=sql_text("'active'")
    )
    severity: Mapped[str] = mapped_column(
        Text, nullable=False, default="medium", server_default=sql_text("'medium'")
    )
    failure_classification: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="SET NULL")
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluations.id", ondelete="SET NULL")
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL")
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_requests.id", ondelete="SET NULL")
    )
    replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_replay_runs.id", ondelete="SET NULL")
    )
    harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_harness_evaluations.id", ondelete="SET NULL")
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvalFailureCase(Base):
    __tablename__ = "eval_failure_cases"
    __table_args__ = (
        CheckConstraint(
            "surface IN ("
            "'document_evaluation', "
            "'search_request', "
            "'chat_answer', "
            "'search_replay', "
            "'harness_evaluation', "
            "'agent_task'"
            ")",
            name="ck_eval_failure_cases_surface",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_eval_failure_cases_severity",
        ),
        CheckConstraint(
            "status IN ("
            "'open', 'triaged', 'drafted', 'verified', 'awaiting_approval', "
            "'applied', 'rejected', 'resolved', 'suppressed'"
            ")",
            name="ck_eval_failure_cases_status",
        ),
        UniqueConstraint("case_key", name="uq_eval_failure_cases_case_key"),
        Index("ix_eval_failure_cases_status_updated", "status", "updated_at"),
        Index("ix_eval_failure_cases_surface_status", "surface", "status"),
        Index("ix_eval_failure_cases_document_id", "document_id"),
        Index("ix_eval_failure_cases_search_request_id", "search_request_id"),
        Index("ix_eval_failure_cases_evaluation_id", "evaluation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="open", server_default=sql_text("'open'")
    )
    severity: Mapped[str] = mapped_column(
        Text, nullable=False, default="medium", server_default=sql_text("'medium'")
    )
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    failure_classification: Mapped[str] = mapped_column(Text, nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    observed_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    source_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_observations.id", ondelete="SET NULL")
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="SET NULL")
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluations.id", ondelete="SET NULL")
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL")
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_requests.id", ondelete="SET NULL")
    )
    replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_replay_runs.id", ondelete="SET NULL")
    )
    harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_harness_evaluations.id", ondelete="SET NULL")
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    recommended_next_actions_json: Mapped[list] = mapped_column(
        "recommended_next_actions",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    allowed_repair_surfaces_json: Mapped[list] = mapped_column(
        "allowed_repair_surfaces",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    blocked_repair_surfaces_json: Mapped[list] = mapped_column(
        "blocked_repair_surfaces",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    verification_requirements_json: Mapped[dict] = mapped_column(
        "verification_requirements",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    agent_task_payloads_json: Mapped[dict] = mapped_column(
        "agent_task_payloads",
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
