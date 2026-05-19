from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClaimSupportCalibrationPolicy(Base):
    __tablename__ = "claim_support_calibration_policies"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'retired')",
            name="ck_claim_support_calibration_policies_status",
        ),
        UniqueConstraint(
            "policy_name",
            "policy_version",
            "policy_sha256",
            name="uq_claim_support_calibration_policies_identity",
        ),
        Index(
            "ix_claim_support_calibration_policies_name_version",
            "policy_name",
            "policy_version",
        ),
        Index(
            "uq_claim_support_calibration_policies_active_name",
            "policy_name",
            unique=True,
            postgresql_where=sql_text("status = 'active'"),
        ),
        Index("ix_claim_support_calibration_policies_status", "status"),
        Index("ix_claim_support_calibration_policies_sha", "policy_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    policy_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    min_hard_case_kind_count: Mapped[int] = mapped_column(Integer, nullable=False)
    required_hard_case_kinds_json: Mapped[list] = mapped_column(
        "required_hard_case_kinds",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    required_verdicts_json: Mapped[list] = mapped_column(
        "required_verdicts",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    policy_payload_json: Mapped[dict] = mapped_column(
        "policy_payload",
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimSupportEvaluation(Base):
    __tablename__ = "claim_support_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_claim_support_evaluations_status",
        ),
        CheckConstraint(
            "gate_outcome IN ('passed', 'failed')",
            name="ck_claim_support_evaluations_gate_outcome",
        ),
        Index("ix_claim_support_evaluations_agent_task_id", "agent_task_id"),
        Index("ix_claim_support_evaluations_operator_run_id", "operator_run_id"),
        Index("ix_claim_support_evaluations_created_at", "created_at"),
        Index("ix_claim_support_evaluations_gate_created", "gate_outcome", "created_at"),
        Index("ix_claim_support_evaluations_fixture_sha", "fixture_set_sha256"),
        Index("ix_claim_support_evaluations_fixture_set_id", "fixture_set_id"),
        Index("ix_claim_support_evaluations_policy_id", "policy_id"),
        Index("ix_claim_support_evaluations_policy_sha", "policy_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    operator_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="SET NULL"),
    )
    fixture_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_fixture_sets.id", ondelete="SET NULL"),
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    evaluation_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_version: Mapped[str | None] = mapped_column(Text)
    fixture_set_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    policy_name: Mapped[str | None] = mapped_column(Text)
    policy_version: Mapped[str | None] = mapped_column(Text)
    policy_sha256: Mapped[str | None] = mapped_column(Text)
    judge_name: Mapped[str] = mapped_column(Text, nullable=False)
    judge_version: Mapped[str] = mapped_column(Text, nullable=False)
    min_support_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    gate_outcome: Mapped[str] = mapped_column(Text, nullable=False)
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
    evaluation_payload_json: Mapped[dict] = mapped_column(
        "evaluation_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportEvaluationCase(Base):
    __tablename__ = "claim_support_evaluation_cases"
    __table_args__ = (
        CheckConstraint(
            "expected_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_support_evaluation_cases_expected_verdict",
        ),
        CheckConstraint(
            "predicted_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_support_evaluation_cases_predicted_verdict",
        ),
        UniqueConstraint(
            "evaluation_id",
            "case_id",
            name="uq_claim_support_evaluation_cases_eval_case",
        ),
        Index("ix_claim_support_evaluation_cases_eval_id", "evaluation_id"),
        Index("ix_claim_support_evaluation_cases_case_id", "case_id"),
        Index("ix_claim_support_evaluation_cases_expected", "expected_verdict"),
        Index("ix_claim_support_evaluation_cases_predicted", "predicted_verdict"),
        Index("ix_claim_support_evaluation_cases_passed", "passed"),
        Index("ix_claim_support_evaluation_cases_hard_kind", "hard_case_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_index: Mapped[int] = mapped_column(Integer, nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    hard_case_kind: Mapped[str | None] = mapped_column(Text)
    expected_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    support_score: Mapped[float | None] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    claim_payload_json: Mapped[dict] = mapped_column(
        "claim_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    support_judgment_json: Mapped[dict] = mapped_column(
        "support_judgment",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    failure_reasons_json: Mapped[list] = mapped_column(
        "failure_reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
