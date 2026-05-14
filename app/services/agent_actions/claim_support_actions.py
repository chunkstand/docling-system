from __future__ import annotations

from app.db.models import AgentTaskSideEffectLevel
from app.schemas.agent_task_claim_support import (
    ApplyClaimSupportCalibrationPolicyTaskInput,
    ApplyClaimSupportCalibrationPolicyTaskOutput,
    DraftClaimSupportCalibrationPolicyTaskInput,
    DraftClaimSupportCalibrationPolicyTaskOutput,
    EvaluateClaimSupportJudgeTaskInput,
    EvaluateClaimSupportJudgeTaskOutput,
    QueueClaimSupportPolicyChangeImpactReplayTaskInput,
    QueueClaimSupportPolicyChangeImpactReplayTaskOutput,
    VerifyClaimSupportCalibrationPolicyTaskInput,
    VerifyClaimSupportCalibrationPolicyTaskOutput,
)
from app.services.agent_actions.claim_support_activation import (
    apply_claim_support_calibration_policy_executor,
)
from app.services.agent_actions.claim_support_drafting import (
    draft_claim_support_calibration_policy_executor,
)
from app.services.agent_actions.claim_support_evaluation import (
    evaluate_claim_support_judge_executor,
    queue_policy_change_impact_replay_executor,
)
from app.services.agent_actions.claim_support_verification import (
    verify_claim_support_calibration_policy_executor,
)
from app.services.agent_actions.types import AgentTaskActionDefinition


def build_claim_support_action_definitions() -> dict[str, AgentTaskActionDefinition]:
    return {
        "evaluate_claim_support_judge": AgentTaskActionDefinition(
            task_type="evaluate_claim_support_judge",
            capability="technical_reports",
            definition_kind="workflow",
            description=(
                "Replay and persist fixed hard-case evaluations for the technical report "
                "claim support judge."
            ),
            payload_model=EvaluateClaimSupportJudgeTaskInput,
            executor=evaluate_claim_support_judge_executor,
            output_model=EvaluateClaimSupportJudgeTaskOutput,
            output_schema_name="evaluate_claim_support_judge_output",
            output_schema_version="1.0",
            input_example={
                "evaluation_name": "claim_support_judge_calibration",
                "fixture_set_name": "default_claim_support_v1",
                "fixture_set_version": "v1",
                "policy_name": "claim_support_judge_calibration_policy",
                "min_support_score": 0.34,
                "min_overall_accuracy": 1.0,
                "min_verdict_precision": 1.0,
                "min_verdict_recall": 1.0,
            },
            context_builder_name="evaluate_claim_support_judge",
        ),
        "draft_claim_support_calibration_policy": AgentTaskActionDefinition(
            task_type="draft_claim_support_calibration_policy",
            capability="technical_reports",
            definition_kind="draft",
            description=(
                "Draft a claim-support calibration policy without changing the active policy."
            ),
            payload_model=DraftClaimSupportCalibrationPolicyTaskInput,
            executor=draft_claim_support_calibration_policy_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftClaimSupportCalibrationPolicyTaskOutput,
            output_schema_name="draft_claim_support_calibration_policy_output",
            output_schema_version="1.0",
            input_example={
                "policy_name": "claim_support_judge_calibration_policy",
                "policy_version": "v2",
                "rationale": "Tighten calibration coverage before report-generation promotion.",
                "min_hard_case_kind_count": 4,
                "required_hard_case_kinds": [
                    "exact_source_support",
                    "wrong_evidence",
                    "lexical_overlap_wrong_evidence",
                    "missing_traceable_evidence",
                ],
                "required_verdicts": ["supported", "unsupported", "insufficient_evidence"],
            },
            context_builder_name="generic",
        ),
        "verify_claim_support_calibration_policy": AgentTaskActionDefinition(
            task_type="verify_claim_support_calibration_policy",
            capability="technical_reports",
            definition_kind="verifier",
            description="Verify a draft claim-support calibration policy against replay fixtures.",
            payload_model=VerifyClaimSupportCalibrationPolicyTaskInput,
            executor=verify_claim_support_calibration_policy_executor,
            output_model=VerifyClaimSupportCalibrationPolicyTaskOutput,
            output_schema_name="verify_claim_support_calibration_policy_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "fixture_set_name": "default_claim_support_v1",
                "fixture_set_version": "v1",
                "include_replay_alert_fixtures": True,
                "require_replay_alert_fixture_coverage": True,
            },
            context_builder_name="generic",
        ),
        "apply_claim_support_calibration_policy": AgentTaskActionDefinition(
            task_type="apply_claim_support_calibration_policy",
            capability="technical_reports",
            definition_kind="promotion",
            description="Activate a verified claim-support calibration policy after approval.",
            payload_model=ApplyClaimSupportCalibrationPolicyTaskInput,
            executor=apply_claim_support_calibration_policy_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplyClaimSupportCalibrationPolicyTaskOutput,
            output_schema_name="apply_claim_support_calibration_policy_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified claim-support calibration policy.",
                "waiver_activation_approved_by": "reviewer@example.com",
                "waiver_activation_approval_note": (
                    "Reviewed active replay-alert fixture coverage waiver before activation."
                ),
            },
            context_builder_name="generic",
        ),
        "queue_claim_support_policy_change_impact_replay": AgentTaskActionDefinition(
            task_type="queue_claim_support_policy_change_impact_replay",
            capability="technical_reports",
            definition_kind="draft",
            description=(
                "Create managed replay tasks for stale technical-report artifacts identified "
                "by a claim-support policy change-impact row."
            ),
            payload_model=QueueClaimSupportPolicyChangeImpactReplayTaskInput,
            executor=queue_policy_change_impact_replay_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=QueueClaimSupportPolicyChangeImpactReplayTaskOutput,
            output_schema_name="queue_claim_support_policy_change_impact_replay_output",
            output_schema_version="1.0",
            input_example={
                "change_impact_id": "00000000-0000-0000-0000-000000000000",
                "requested_by": "docling-system",
            },
            context_builder_name="generic",
        ),
    }
