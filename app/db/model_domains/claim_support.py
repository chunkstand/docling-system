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


class ClaimSupportReplayAlertFixtureCoverageWaiverLedger(Base):
    __tablename__ = "claim_support_replay_alert_fixture_coverage_waiver_ledgers"
    __table_args__ = (
        CheckConstraint(
            "coverage_status IN ('open', 'partially_covered', 'closed', 'no_action_required')",
            name="ck_cs_waiver_ledgers_status",
        ),
        UniqueConstraint(
            "waiver_artifact_id",
            "waiver_sha256",
            name="uq_cs_waiver_ledgers_artifact_sha",
        ),
        Index("ix_cs_waiver_ledgers_artifact", "waiver_artifact_id"),
        Index("ix_cs_waiver_ledgers_task", "verification_task_id"),
        Index("ix_cs_waiver_ledgers_status", "coverage_status", "created_at"),
        Index("ix_cs_waiver_ledgers_closure", "closure_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waiver_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    target_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    fixture_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claim_support_fixture_sets.id", ondelete="SET NULL")
    )
    waiver_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    waiver_severity: Mapped[str | None] = mapped_column(Text)
    waived_by: Mapped[str | None] = mapped_column(Text)
    waiver_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waiver_review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waiver_remediation_owner: Mapped[str | None] = mapped_column(Text)
    waived_escalation_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    covered_escalation_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    coverage_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    coverage_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="open",
        server_default=sql_text("'open'"),
    )
    waived_escalation_set_sha256: Mapped[str | None] = mapped_column(Text)
    covered_escalation_set_sha256: Mapped[str | None] = mapped_column(Text)
    source_change_impact_ids_json: Mapped[list] = mapped_column(
        "source_change_impact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_verification_task_ids_json: Mapped[list] = mapped_column(
        "source_verification_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    closure_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    closure_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    closure_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    promotion_event_ids_json: Mapped[list] = mapped_column(
        "promotion_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    promotion_artifact_ids_json: Mapped[list] = mapped_column(
        "promotion_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    promotion_receipt_sha256s_json: Mapped[list] = mapped_column(
        "promotion_receipt_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    ledger_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportReplayAlertFixtureCoverageWaiverEscalation(Base):
    __tablename__ = "claim_support_replay_alert_fixture_coverage_waiver_escalations"
    __table_args__ = (
        UniqueConstraint(
            "ledger_id",
            "escalation_event_id",
            name="uq_cs_waiver_escalations_ledger_event",
        ),
        Index("ix_cs_waiver_escalations_ledger", "ledger_id"),
        Index("ix_cs_waiver_escalations_event", "escalation_event_id"),
        Index("ix_cs_waiver_escalations_covered", "ledger_id", "covered"),
        Index("ix_cs_waiver_escalations_impact", "change_impact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claim_support_replay_alert_fixture_coverage_waiver_ledgers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    waiver_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    escalation_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    change_impact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_policy_change_impacts.id", ondelete="SET NULL"),
    )
    escalation_event_hash: Mapped[str | None] = mapped_column(Text)
    escalation_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    alert_kind: Mapped[str | None] = mapped_column(Text)
    replay_status: Mapped[str | None] = mapped_column(Text)
    covered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    covered_by_promotion_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    covered_by_promotion_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    covered_by_promotion_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    covered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportFixtureSet(Base):
    __tablename__ = "claim_support_fixture_sets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'retired')",
            name="ck_claim_support_fixture_sets_status",
        ),
        UniqueConstraint(
            "fixture_set_name",
            "fixture_set_version",
            "fixture_set_sha256",
            name="uq_claim_support_fixture_sets_identity",
        ),
        Index(
            "ix_claim_support_fixture_sets_name_version",
            "fixture_set_name",
            "fixture_set_version",
        ),
        Index("ix_claim_support_fixture_sets_status", "status"),
        Index("ix_claim_support_fixture_sets_sha", "fixture_set_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fixture_set_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hard_case_kinds_json: Mapped[list] = mapped_column(
        "hard_case_kinds",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    verdicts_json: Mapped[list] = mapped_column(
        "verdicts",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    fixtures_json: Mapped[list] = mapped_column(
        "fixtures",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimSupportReplayAlertFixtureCorpusSnapshot(Base):
    __tablename__ = "claim_support_replay_alert_fixture_corpus_snapshots"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'superseded')",
            name="ck_cs_replay_fixture_corpus_snapshots_status",
        ),
        UniqueConstraint(
            "snapshot_sha256",
            name="uq_cs_replay_fixture_corpus_snapshots_sha",
        ),
        Index(
            "ix_cs_replay_fixture_corpus_snapshots_status_created",
            "status",
            "created_at",
        ),
        Index("ix_cs_replay_fixture_corpus_snapshots_sha", "snapshot_sha256"),
        Index(
            "ix_cs_replay_fixture_corpus_snapshots_governance_event",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_cs_replay_fixture_corpus_snapshots_governance_artifact",
            "governance_artifact_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="active",
        server_default=sql_text("'active'"),
    )
    snapshot_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_count: Mapped[int] = mapped_column(Integer, nullable=False)
    promotion_event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    promotion_fixture_set_count: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_promotion_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    source_promotion_event_ids_json: Mapped[list] = mapped_column(
        "source_promotion_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_promotion_artifact_ids_json: Mapped[list] = mapped_column(
        "source_promotion_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_promotion_receipt_sha256s_json: Mapped[list] = mapped_column(
        "source_promotion_receipt_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_fixture_set_ids_json: Mapped[list] = mapped_column(
        "source_fixture_set_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_fixture_set_sha256s_json: Mapped[list] = mapped_column(
        "source_fixture_set_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_escalation_event_ids_json: Mapped[list] = mapped_column(
        "source_escalation_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    invalid_promotion_event_ids_json: Mapped[list] = mapped_column(
        "invalid_promotion_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    snapshot_payload_json: Mapped[dict] = mapped_column(
        "snapshot_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    governance_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    governance_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportReplayAlertFixtureCorpusRow(Base):
    __tablename__ = "claim_support_replay_alert_fixture_corpus_rows"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "case_identity_sha256",
            name="uq_cs_replay_fixture_corpus_rows_snapshot_identity",
        ),
        UniqueConstraint(
            "snapshot_id",
            "row_index",
            name="uq_cs_replay_fixture_corpus_rows_snapshot_index",
        ),
        Index("ix_cs_replay_fixture_corpus_rows_snapshot", "snapshot_id"),
        Index("ix_cs_replay_fixture_corpus_rows_case", "case_id"),
        Index("ix_cs_replay_fixture_corpus_rows_fixture_sha", "fixture_sha256"),
        Index("ix_cs_replay_fixture_corpus_rows_promotion", "promotion_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_replay_alert_fixture_corpus_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    case_identity_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_json: Mapped[dict] = mapped_column(
        "fixture",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    fixture_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claim_support_fixture_sets.id", ondelete="SET NULL")
    )
    promotion_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    promotion_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    promotion_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    source_change_impact_ids_json: Mapped[list] = mapped_column(
        "source_change_impact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_escalation_event_ids_json: Mapped[list] = mapped_column(
        "source_escalation_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    replay_alert_source_json: Mapped[dict] = mapped_column(
        "replay_alert_source",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class ClaimSupportPolicyChangeImpact(Base):
    __tablename__ = "claim_support_policy_change_impacts"
    __table_args__ = (
        CheckConstraint(
            "affected_support_judgment_count >= 0",
            name="ck_claim_support_policy_change_impacts_support_count",
        ),
        CheckConstraint(
            "affected_generated_document_count >= 0",
            name="ck_claim_support_policy_change_impacts_document_count",
        ),
        CheckConstraint(
            "affected_verification_count >= 0",
            name="ck_claim_support_policy_change_impacts_verification_count",
        ),
        CheckConstraint(
            "replay_recommended_count >= 0",
            name="ck_claim_support_policy_change_impacts_replay_count",
        ),
        CheckConstraint(
            "replay_status IN "
            "('no_action_required', 'pending', 'queued', 'in_progress', 'blocked', 'closed')",
            name="ck_claim_support_policy_change_impacts_replay_status",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_activation_task",
            "activation_task_id",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_policy",
            "activated_policy_id",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_governance_event",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_governance_artifact",
            "governance_artifact_id",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_scope_created",
            "impact_scope",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_payload_sha",
            "impact_payload_sha256",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_replay_status",
            "replay_status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activation_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    activated_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    previous_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    governance_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    impact_scope: Mapped[str] = mapped_column(Text, nullable=False)
    policy_name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    activated_policy_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    previous_policy_sha256: Mapped[str | None] = mapped_column(Text)
    affected_support_judgment_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    affected_generated_document_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    affected_verification_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    replay_recommended_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    replay_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=sql_text("'pending'"),
    )
    impacted_claim_derivation_ids_json: Mapped[list] = mapped_column(
        "impacted_claim_derivation_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impacted_task_ids_json: Mapped[list] = mapped_column(
        "impacted_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impacted_verification_task_ids_json: Mapped[list] = mapped_column(
        "impacted_verification_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impact_payload_json: Mapped[dict] = mapped_column(
        "impact_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    impact_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    replay_task_ids_json: Mapped[list] = mapped_column(
        "replay_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    replay_task_plan_json: Mapped[dict] = mapped_column(
        "replay_task_plan",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    replay_closure_json: Mapped[dict] = mapped_column(
        "replay_closure",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    replay_closure_sha256: Mapped[str | None] = mapped_column(Text)
    replay_status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replay_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
