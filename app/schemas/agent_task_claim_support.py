from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.agent_task_core import AgentTaskVerificationResponse
from app.schemas.agent_task_semantics import SemanticSuccessMetricCheck

REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_MAX_HOURS = 72


class ClaimSupportEvaluationFixture(BaseModel):
    case_id: str = Field(min_length=1)
    expected_verdict: str = Field(pattern="^(supported|unsupported|insufficient_evidence)$")
    draft_payload: dict
    claim_id: str | None = None
    description: str | None = None
    hard_case_kind: str | None = None


class ClaimSupportEvaluationCaseResult(BaseModel):
    case_index: int
    case_id: str
    description: str | None = None
    hard_case_kind: str | None = None
    expected_verdict: str
    predicted_verdict: str
    support_score: float | None = None
    passed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    claim_payload: dict = Field(default_factory=dict)
    support_judgment: dict = Field(default_factory=dict)


class EvaluateClaimSupportJudgeTaskInput(BaseModel):
    evaluation_name: str = Field(default="claim_support_judge_calibration", min_length=1)
    fixture_set_name: str = Field(default="default_claim_support_v1", min_length=1)
    fixture_set_version: str = Field(default="v1", min_length=1)
    policy_name: str = Field(default="claim_support_judge_calibration_policy", min_length=1)
    policy_version: str | None = Field(default=None, min_length=1)
    fixtures: list[ClaimSupportEvaluationFixture] = Field(default_factory=list, max_length=100)
    min_support_score: float = Field(default=0.34, ge=0.0, le=1.0)
    min_overall_accuracy: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_precision: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_recall: float = Field(default=1.0, ge=0.0, le=1.0)


class DraftClaimSupportCalibrationPolicyTaskInput(BaseModel):
    policy_name: str = Field(default="claim_support_judge_calibration_policy", min_length=1)
    policy_version: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    owner: str = Field(default="docling-system", min_length=1)
    source: str = Field(default="operator_draft", min_length=1)
    min_support_score: float = Field(default=0.34, ge=0.0, le=1.0)
    min_overall_accuracy: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_precision: float = Field(default=1.0, ge=0.0, le=1.0)
    min_verdict_recall: float = Field(default=1.0, ge=0.0, le=1.0)
    min_hard_case_kind_count: int = Field(default=4, ge=0, le=100)
    required_hard_case_kinds: list[str] = Field(default_factory=list, max_length=100)
    required_verdicts: list[str] = Field(
        default_factory=lambda: ["supported", "unsupported", "insufficient_evidence"],
        max_length=3,
    )


class DraftClaimSupportCalibrationPolicyTaskOutput(BaseModel):
    policy_id: UUID
    policy_name: str
    policy_version: str
    policy_sha256: str
    policy_payload: dict = Field(default_factory=dict)
    active_policy_id: UUID | None = None
    active_policy_sha256: str | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class VerifyClaimSupportCalibrationPolicyTaskInput(BaseModel):
    target_task_id: UUID
    fixture_set_name: str = Field(default="default_claim_support_v1", min_length=1)
    fixture_set_version: str = Field(default="v1", min_length=1)
    fixtures: list[ClaimSupportEvaluationFixture] = Field(default_factory=list, max_length=100)
    include_replay_alert_fixtures: bool = True
    replay_alert_fixture_limit: int = Field(default=100, ge=0, le=100)
    require_replay_alert_fixture_coverage: bool = True
    replay_alert_fixture_coverage_waived_by: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    replay_alert_fixture_coverage_waiver_reason: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )
    replay_alert_fixture_coverage_waiver_severity: str | None = Field(
        default=None,
        pattern="^(low|medium|high|critical)$",
    )
    replay_alert_fixture_coverage_waiver_expires_at: datetime | None = None
    replay_alert_fixture_coverage_waiver_remediation_owner: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    include_mined_failures: bool = True
    mined_failure_limit: int = Field(default=20, ge=0, le=100)

    @model_validator(mode="after")
    def require_replay_alert_coverage_waiver_details(self):
        if self.require_replay_alert_fixture_coverage:
            return self
        if not self.replay_alert_fixture_coverage_waived_by:
            raise ValueError(
                "replay_alert_fixture_coverage_waived_by is required when "
                "require_replay_alert_fixture_coverage is false."
            )
        if not self.replay_alert_fixture_coverage_waiver_reason:
            raise ValueError(
                "replay_alert_fixture_coverage_waiver_reason is required when "
                "require_replay_alert_fixture_coverage is false."
            )
        if not self.replay_alert_fixture_coverage_waiver_severity:
            raise ValueError(
                "replay_alert_fixture_coverage_waiver_severity is required when "
                "require_replay_alert_fixture_coverage is false."
            )
        if self.replay_alert_fixture_coverage_waiver_expires_at is None:
            raise ValueError(
                "replay_alert_fixture_coverage_waiver_expires_at is required when "
                "require_replay_alert_fixture_coverage is false."
            )
        if (
            self.replay_alert_fixture_coverage_waiver_expires_at.tzinfo is None
            or self.replay_alert_fixture_coverage_waiver_expires_at.utcoffset() is None
        ):
            raise ValueError(
                "replay_alert_fixture_coverage_waiver_expires_at must include a timezone."
            )
        now = datetime.now(UTC)
        expires_at = self.replay_alert_fixture_coverage_waiver_expires_at.astimezone(UTC)
        if expires_at <= now:
            raise ValueError(
                "replay_alert_fixture_coverage_waiver_expires_at must be in the future."
            )
        if expires_at > now + timedelta(hours=REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_MAX_HOURS):
            raise ValueError(
                "replay_alert_fixture_coverage_waiver_expires_at must be within "
                f"{REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_MAX_HOURS} hours."
            )
        return self


class VerifyClaimSupportCalibrationPolicyTaskOutput(BaseModel):
    draft_policy: dict = Field(default_factory=dict)
    evaluation: dict = Field(default_factory=dict)
    verification: AgentTaskVerificationResponse
    replay_alert_fixture_summary: dict = Field(default_factory=dict)
    replay_alert_fixture_coverage_waiver: dict = Field(default_factory=dict)
    mined_failure_summary: dict = Field(default_factory=dict)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


class ApplyClaimSupportCalibrationPolicyTaskInput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str = Field(min_length=1)
    waiver_activation_approved_by: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    waiver_activation_approval_note: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )


class ApplyClaimSupportCalibrationPolicyTaskOutput(BaseModel):
    draft_task_id: UUID
    verification_task_id: UUID
    reason: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_note: str | None = None
    previous_active_policy_id: UUID | None = None
    previous_active_policy_sha256: str | None = None
    activated_policy_id: UUID
    activated_policy_sha256: str
    policy_name: str
    policy_version: str
    draft_policy_sha256: str
    verification_id: UUID
    verification_outcome: str
    verification_reasons: list[str] = Field(default_factory=list)
    verification_evaluation_id: UUID | None = None
    verification_fixture_set_id: UUID | None = None
    verification_fixture_set_sha256: str | None = None
    verification_policy_sha256: str
    verification_replay_alert_fixture_summary: dict = Field(default_factory=dict)
    verification_replay_alert_fixture_coverage_waiver: dict = Field(default_factory=dict)
    verification_mined_failure_summary: dict = Field(default_factory=dict)
    waiver_activation_approval: dict = Field(default_factory=dict)
    operator_run_id: UUID | None = None
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None
    activation_governance_artifact_id: UUID | None = None
    activation_governance_artifact_kind: str | None = None
    activation_governance_artifact_path: str | None = None
    activation_governance_payload_sha256: str | None = None
    activation_governance_receipt_sha256: str | None = None
    activation_governance_signature_status: str | None = None
    activation_governance_prov_jsonld_sha256: str | None = None
    activation_governance_event_id: UUID | None = None
    activation_governance_event_hash: str | None = None
    activation_change_impact_id: UUID | None = None
    activation_change_impact_payload_sha256: str | None = None
    activation_change_impact_summary: dict = Field(default_factory=dict)
    activation_change_impact_replay_recommended_count: int | None = None


class ClaimSupportPolicyChangeImpactReplayTaskResponse(BaseModel):
    action: str
    source_task_id: UUID | None = None
    prior_verification_task_id: UUID | None = None
    replay_task_id: UUID
    task_type: str
    status: str
    dependency_task_ids: list[UUID] = Field(default_factory=list)
    reason: str | None = None


class ClaimSupportPolicyChangeImpactResponse(BaseModel):
    change_impact_id: UUID
    activation_task_id: UUID | None = None
    activated_policy_id: UUID | None = None
    previous_policy_id: UUID | None = None
    semantic_governance_event_id: UUID | None = None
    governance_artifact_id: UUID | None = None
    impact_scope: str
    policy_name: str
    policy_version: str
    activated_policy_sha256: str
    previous_policy_sha256: str | None = None
    affected_support_judgment_count: int
    affected_generated_document_count: int
    affected_verification_count: int
    replay_recommended_count: int
    replay_status: str
    impacted_claim_derivation_ids: list[str] = Field(default_factory=list)
    impacted_task_ids: list[str] = Field(default_factory=list)
    impacted_verification_task_ids: list[str] = Field(default_factory=list)
    impact_payload_sha256: str
    impact_payload: dict = Field(default_factory=dict)
    replay_task_ids: list[UUID] = Field(default_factory=list)
    replay_task_plan: dict = Field(default_factory=dict)
    replay_closure: dict = Field(default_factory=dict)
    replay_closure_sha256: str | None = None
    replay_status_updated_at: datetime | None = None
    replay_closed_at: datetime | None = None
    created_at: datetime


class ClaimSupportPolicyChangeImpactSummaryResponse(BaseModel):
    total_count: int
    replay_status_counts: dict[str, int] = Field(default_factory=dict)
    open_count: int
    stale_open_count: int
    stale_after_hours: int
    stale_cutoff: datetime


class ClaimSupportPolicyChangeImpactWorklistTaskRef(BaseModel):
    task_id: UUID
    task_type: str
    status: str
    completed_at: datetime | None = None
    is_terminal_failure: bool = False
    is_required_for_closure: bool = False


class ClaimSupportPolicyChangeImpactClosureEventRef(BaseModel):
    event_id: UUID
    event_hash: str
    receipt_sha256: str | None = None
    artifact_id: UUID | None = None
    artifact_kind: str | None = None
    artifact_path: str | None = None
    created_at: datetime


class ClaimSupportPolicyChangeImpactAlertEventRef(BaseModel):
    event_id: UUID
    event_hash: str
    receipt_sha256: str | None = None
    artifact_id: UUID | None = None
    artifact_kind: str | None = None
    artifact_path: str | None = None
    alert_kind: str | None = None
    created_at: datetime


class ClaimSupportPolicyChangeImpactWorklistItemResponse(BaseModel):
    change_impact: ClaimSupportPolicyChangeImpactResponse
    severity: str
    status_label: str
    is_open: bool
    is_stale: bool
    age_hours: float
    status_age_hours: float
    next_action: str
    recommended_action: str
    reasons: list[str] = Field(default_factory=list)
    affected_draft_task_ids: list[UUID] = Field(default_factory=list)
    affected_verification_task_ids: list[UUID] = Field(default_factory=list)
    audit_bundle_task_ids: list[UUID] = Field(default_factory=list)
    replay_tasks: list[ClaimSupportPolicyChangeImpactWorklistTaskRef] = Field(default_factory=list)
    closure_events: list[ClaimSupportPolicyChangeImpactClosureEventRef] = Field(
        default_factory=list
    )
    closure_receipt_artifact_id: UUID | None = None
    closure_receipt_sha256: str | None = None
    operator_links: dict = Field(default_factory=dict)


class ClaimSupportPolicyChangeImpactWorklistResponse(BaseModel):
    summary: ClaimSupportPolicyChangeImpactSummaryResponse
    generated_at: datetime
    stale_after_hours: int
    limit: int = 50
    matching_count: int = 0
    item_count: int
    has_more: bool = False
    items: list[ClaimSupportPolicyChangeImpactWorklistItemResponse] = Field(default_factory=list)


class ClaimSupportPolicyChangeImpactAlertItemResponse(BaseModel):
    change_impact: ClaimSupportPolicyChangeImpactResponse
    alert_kind: str
    severity: str
    replay_status: str
    is_stale: bool
    age_hours: float
    status_age_hours: float
    next_action: str
    recommended_action: str
    reasons: list[str] = Field(default_factory=list)
    affected_draft_task_ids: list[UUID] = Field(default_factory=list)
    affected_verification_task_ids: list[UUID] = Field(default_factory=list)
    audit_bundle_task_ids: list[UUID] = Field(default_factory=list)
    replay_tasks: list[ClaimSupportPolicyChangeImpactWorklistTaskRef] = Field(default_factory=list)
    escalation_events: list[ClaimSupportPolicyChangeImpactAlertEventRef] = Field(
        default_factory=list
    )
    latest_escalation_event_id: UUID | None = None
    latest_escalation_receipt_sha256: str | None = None
    operator_links: dict = Field(default_factory=dict)


class ClaimSupportPolicyChangeImpactAlertResponse(BaseModel):
    summary: ClaimSupportPolicyChangeImpactSummaryResponse
    generated_at: datetime
    stale_after_hours: int
    limit: int = 50
    matching_count: int = 0
    item_count: int
    has_more: bool = False
    recorded_escalation_count: int = 0
    items: list[ClaimSupportPolicyChangeImpactAlertItemResponse] = Field(default_factory=list)


class ClaimSupportPolicyChangeImpactAlertEscalationRequest(BaseModel):
    requested_by: str = Field(default="docling-system", min_length=1)


class ClaimSupportPolicyChangeImpactFixturePromotionEventRef(BaseModel):
    event_id: UUID
    event_hash: str
    receipt_sha256: str | None = None
    fixture_set_id: UUID | None = None
    fixture_set_sha256: str | None = None
    artifact_id: UUID | None = None
    artifact_kind: str | None = None
    artifact_path: str | None = None
    created_at: datetime


class ClaimSupportPolicyChangeImpactFixtureCandidateResponse(BaseModel):
    candidate_id: str
    change_impact_id: UUID
    alert_kind: str
    severity: str
    replay_status: str
    is_stale: bool
    source_claim_derivation_id: UUID | None = None
    source_draft_task_id: UUID | None = None
    affected_verification_task_ids: list[UUID] = Field(default_factory=list)
    escalation_event_ids: list[UUID] = Field(default_factory=list)
    latest_escalation_event_id: UUID | None = None
    case_id: str
    hard_case_kind: str
    expected_verdict: str
    fixture_sha256: str
    fixture: dict = Field(default_factory=dict)
    source_payload_sha256: str
    already_promoted: bool = False
    promotion_events: list[ClaimSupportPolicyChangeImpactFixturePromotionEventRef] = Field(
        default_factory=list
    )
    operator_links: dict = Field(default_factory=dict)


class ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse(BaseModel):
    alert_matching_count: int
    candidate_count: int
    promoted_candidate_count: int = 0
    unpromoted_candidate_count: int = 0
    source_escalation_event_count: int = 0
    stale_after_hours: int


class ClaimSupportPolicyChangeImpactFixtureCandidateListResponse(BaseModel):
    summary: ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse
    generated_at: datetime
    stale_after_hours: int
    limit: int = 50
    matching_count: int = 0
    item_count: int
    has_more: bool = False
    items: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse] = Field(
        default_factory=list
    )


class ClaimSupportPolicyChangeImpactFixturePromotionRequest(BaseModel):
    fixture_set_name: str = Field(
        default="claim_support_replay_alert_promotions",
        min_length=1,
    )
    fixture_set_version: str = Field(default="v1", min_length=1)
    requested_by: str = Field(default="docling-system", min_length=1)
    include_unescalated: bool = False


class ClaimSupportPolicyChangeImpactFixturePromotionResponse(BaseModel):
    fixture_set_id: UUID | None = None
    fixture_set_name: str
    fixture_set_version: str
    fixture_set_sha256: str | None = None
    fixture_count: int = 0
    promoted_candidate_count: int = 0
    skipped_candidate_count: int = 0
    candidate_matching_count: int = 0
    candidate_item_count: int = 0
    has_more_candidates: bool = False
    candidate_summary: ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse | None = None
    source_change_impact_ids: list[UUID] = Field(default_factory=list)
    source_escalation_event_ids: list[UUID] = Field(default_factory=list)
    promotion_event_id: UUID | None = None
    promotion_receipt_sha256: str | None = None
    artifact_id: UUID | None = None
    artifact_kind: str | None = None
    artifact_path: str | None = None
    created: bool = False
    active_replay_fixture_corpus_snapshot_id: UUID | None = None
    active_replay_fixture_corpus_sha256: str | None = None
    active_replay_fixture_corpus_fixture_count: int = 0
    active_replay_fixture_corpus_governance_event_id: UUID | None = None
    active_replay_fixture_corpus_governance_artifact_id: UUID | None = None
    active_replay_fixture_corpus_governance_receipt_sha256: str | None = None
    active_replay_fixture_corpus_governed: bool = False
    waiver_closure_count: int = 0
    waiver_closure_event_ids: list[UUID] = Field(default_factory=list)
    waiver_closure_artifact_ids: list[UUID] = Field(default_factory=list)
    waiver_closure_receipt_sha256s: list[str] = Field(default_factory=list)
    closed_waiver_artifact_ids: list[UUID] = Field(default_factory=list)
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse] = Field(
        default_factory=list
    )


class ClaimSupportPolicyChangeImpactReplayRequest(BaseModel):
    requested_by: str = Field(default="docling-system", min_length=1)


class ClaimSupportPolicyChangeImpactReplayResponse(BaseModel):
    change_impact: ClaimSupportPolicyChangeImpactResponse
    replay_status: str
    replay_task_ids: list[UUID] = Field(default_factory=list)
    created_tasks: list[ClaimSupportPolicyChangeImpactReplayTaskResponse] = Field(
        default_factory=list
    )
    replay_task_plan: dict = Field(default_factory=dict)
    replay_closure: dict = Field(default_factory=dict)
    replay_closure_sha256: str | None = None


class QueueClaimSupportPolicyChangeImpactReplayTaskInput(BaseModel):
    change_impact_id: UUID
    requested_by: str = Field(default="docling-system", min_length=1)


class QueueClaimSupportPolicyChangeImpactReplayTaskOutput(
    ClaimSupportPolicyChangeImpactReplayResponse
):
    artifact_id: UUID | None = None
    artifact_kind: str | None = None
    artifact_path: str | None = None


class EvaluateClaimSupportJudgeTaskOutput(BaseModel):
    evaluation_id: UUID
    evaluation_name: str
    fixture_set_id: UUID | None = None
    fixture_set_name: str
    fixture_set_version: str = "v1"
    fixture_set_sha256: str
    policy_id: UUID | None = None
    policy_name: str | None = None
    policy_version: str | None = None
    policy_sha256: str | None = None
    calibration_policy: dict = Field(default_factory=dict)
    judge_name: str
    judge_version: str
    thresholds: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)
    verdict_metrics: dict = Field(default_factory=dict)
    case_results: list[ClaimSupportEvaluationCaseResult] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    success_metrics: list[SemanticSuccessMetricCheck] = Field(default_factory=list)
    operator_run_id: UUID | None = None
    artifact_id: UUID
    artifact_kind: str
    artifact_path: str | None = None


__all__ = [
    "ClaimSupportEvaluationFixture",
    "ClaimSupportEvaluationCaseResult",
    "EvaluateClaimSupportJudgeTaskInput",
    "DraftClaimSupportCalibrationPolicyTaskInput",
    "DraftClaimSupportCalibrationPolicyTaskOutput",
    "VerifyClaimSupportCalibrationPolicyTaskInput",
    "VerifyClaimSupportCalibrationPolicyTaskOutput",
    "ApplyClaimSupportCalibrationPolicyTaskInput",
    "ApplyClaimSupportCalibrationPolicyTaskOutput",
    "ClaimSupportPolicyChangeImpactReplayTaskResponse",
    "ClaimSupportPolicyChangeImpactResponse",
    "ClaimSupportPolicyChangeImpactSummaryResponse",
    "ClaimSupportPolicyChangeImpactWorklistTaskRef",
    "ClaimSupportPolicyChangeImpactClosureEventRef",
    "ClaimSupportPolicyChangeImpactAlertEventRef",
    "ClaimSupportPolicyChangeImpactWorklistItemResponse",
    "ClaimSupportPolicyChangeImpactWorklistResponse",
    "ClaimSupportPolicyChangeImpactAlertItemResponse",
    "ClaimSupportPolicyChangeImpactAlertResponse",
    "ClaimSupportPolicyChangeImpactAlertEscalationRequest",
    "ClaimSupportPolicyChangeImpactFixturePromotionEventRef",
    "ClaimSupportPolicyChangeImpactFixtureCandidateResponse",
    "ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse",
    "ClaimSupportPolicyChangeImpactFixtureCandidateListResponse",
    "ClaimSupportPolicyChangeImpactFixturePromotionRequest",
    "ClaimSupportPolicyChangeImpactFixturePromotionResponse",
    "ClaimSupportPolicyChangeImpactReplayRequest",
    "ClaimSupportPolicyChangeImpactReplayResponse",
    "QueueClaimSupportPolicyChangeImpactReplayTaskInput",
    "QueueClaimSupportPolicyChangeImpactReplayTaskOutput",
    "EvaluateClaimSupportJudgeTaskOutput",
]
