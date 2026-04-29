from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    ClaimSupportCalibrationPolicy,
    KnowledgeOperatorOutput,
)
from app.schemas.agent_tasks import (
    REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_MAX_HOURS,
    ApplyClaimSupportCalibrationPolicyTaskInput,
    ApplyClaimSupportCalibrationPolicyTaskOutput,
    DraftClaimSupportCalibrationPolicyTaskOutput,
    VerifyClaimSupportCalibrationPolicyTaskOutput,
)
from app.services.agent_actions.claim_support_shared import (
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA_VERSION,
    replay_alert_fixture_coverage_waiver_sha256,
    require_policy_row_matches_draft_output,
    require_utc_datetime,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
)
from app.services.claim_support_evaluations import (
    activate_claim_support_calibration_policy,
    get_active_claim_support_calibration_policy,
)
from app.services.claim_support_policy_governance import (
    CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
    CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_FILENAME,
    build_claim_support_policy_activation_governance_payload,
    build_claim_support_policy_change_impact_payload,
    persist_claim_support_policy_change_impact,
    record_claim_support_policy_activation_governance_event,
)
from app.services.evidence import (
    payload_sha256,
    record_knowledge_operator_run,
)
from app.services.storage import StorageService


def require_active_replay_alert_fixture_coverage_waiver(
    *,
    waiver: dict,
    payload: ApplyClaimSupportCalibrationPolicyTaskInput,
    task: AgentTask,
) -> dict:
    if waiver.get("schema_name") != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA:
        raise ValueError("Replay-alert fixture coverage waiver has an unexpected schema name.")
    if (
        waiver.get("schema_version")
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA_VERSION
    ):
        raise ValueError(
            "Replay-alert fixture coverage waiver must use lifecycle schema version "
            f"{CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA_VERSION}."
        )
    expected_waiver_sha = waiver.get("waiver_sha256")
    actual_waiver_sha = replay_alert_fixture_coverage_waiver_sha256(waiver)
    if not expected_waiver_sha or actual_waiver_sha != expected_waiver_sha:
        raise ValueError("Replay-alert fixture coverage waiver hash does not match its payload.")
    expires_at = require_utc_datetime(
        waiver.get("waiver_expires_at"),
        field_name="replay_alert_fixture_coverage_waiver.waiver_expires_at",
    )
    now = utcnow()
    if expires_at <= now:
        raise ValueError("Replay-alert fixture coverage waiver expired before policy activation.")
    if expires_at > now + timedelta(hours=REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_MAX_HOURS):
        raise ValueError(
            "Replay-alert fixture coverage waiver expiry exceeds the maximum "
            f"{REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_MAX_HOURS}-hour lifecycle window."
        )
    severity = str(waiver.get("waiver_severity") or "").strip().lower()
    if severity not in {"low", "medium", "high", "critical"}:
        raise ValueError("Replay-alert fixture coverage waiver is missing a valid severity.")
    if not task.approved_by or not task.approved_at:
        raise ValueError(
            "Activating a policy verified under a replay-alert fixture coverage "
            "waiver requires the activation task to be approved first."
        )
    if not payload.waiver_activation_approved_by:
        raise ValueError(
            "Activating a policy verified under a replay-alert fixture coverage "
            "waiver requires waiver_activation_approved_by."
        )
    if not payload.waiver_activation_approval_note:
        raise ValueError(
            "Activating a policy verified under a replay-alert fixture coverage "
            "waiver requires waiver_activation_approval_note."
        )
    if (
        task.approved_by
        and payload.waiver_activation_approved_by.strip().casefold()
        == task.approved_by.strip().casefold()
    ):
        raise ValueError(
            "Replay-alert fixture coverage waiver activation approval must come "
            "from a different operator than the task approval."
        )
    waived_by = str(waiver.get("waived_by") or "").strip()
    if (
        waived_by
        and payload.waiver_activation_approved_by.strip().casefold() == waived_by.casefold()
    ):
        raise ValueError(
            "Replay-alert fixture coverage waiver activation approval must come "
            "from a different operator than the waiver creator."
        )
    return {
        "required": True,
        "approved_by": payload.waiver_activation_approved_by,
        "approval_note": payload.waiver_activation_approval_note,
        "approved_at": now.isoformat(),
        "task_approved_by": task.approved_by,
        "task_approved_at": task.approved_at.isoformat() if task.approved_at else None,
        "waiver_sha256": waiver.get("waiver_sha256"),
        "waiver_artifact_id": waiver.get("artifact_id"),
        "waiver_severity": severity,
        "waiver_expires_at": expires_at.isoformat(),
        "waiver_status": "active",
    }


def apply_claim_support_calibration_policy_executor(
    session: Session,
    task: AgentTask,
    payload: ApplyClaimSupportCalibrationPolicyTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_claim_support_calibration_policy",
        expected_schema_name="draft_claim_support_calibration_policy_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Policy apply task must declare the requested claim-support policy draft "
            "as a draft_task dependency."
        ),
        rerun_message=(
            "Claim-support policy draft must be rerun after the context migration "
            "before it can be applied."
        ),
    )
    verification_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_claim_support_calibration_policy",
        expected_schema_name="verify_claim_support_calibration_policy_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Policy apply task must declare the requested claim-support policy verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Claim-support policy verification must be rerun after the context migration "
            "before it can be applied."
        ),
    )
    draft_output = DraftClaimSupportCalibrationPolicyTaskOutput.model_validate(draft_context.output)
    verification_output = VerifyClaimSupportCalibrationPolicyTaskOutput.model_validate(
        verification_context.output
    )
    verification = verification_output.verification
    if verification.outcome != "passed":
        raise ValueError(
            "Only passed claim-support calibration policy verifications can be applied."
        )
    if verification.target_task_id != payload.draft_task_id:
        raise ValueError(
            "Verification task does not target the requested claim-support policy draft."
        )
    if str(draft_output.policy_id) != str(verification_output.evaluation.get("policy_id")):
        raise ValueError("Verification did not evaluate the requested claim-support policy draft.")
    draft_policy = session.get(ClaimSupportCalibrationPolicy, draft_output.policy_id)
    if draft_policy is None:
        raise ValueError(f"Claim support calibration policy not found: {draft_output.policy_id}")
    require_policy_row_matches_draft_output(draft_policy, draft_output)
    if draft_policy.status != "draft":
        raise ValueError("Only draft claim support calibration policies can be applied.")

    verification_details = dict(verification.details or {})
    verification_policy_sha256 = str(verification_details.get("policy_sha256") or "")
    evaluation_policy_sha256 = str(verification_output.evaluation.get("policy_sha256") or "")
    if verification_policy_sha256 != draft_output.policy_sha256:
        raise ValueError("Verification policy hash does not match the requested draft policy.")
    if evaluation_policy_sha256 != draft_output.policy_sha256:
        raise ValueError("Verification evaluation hash does not match the requested draft policy.")
    if dict(verification_output.draft_policy or {}) != dict(draft_output.policy_payload or {}):
        raise ValueError("Verification draft policy payload does not match the draft task output.")

    verification_evaluation_id = verification_details.get(
        "evaluation_id"
    ) or verification_output.evaluation.get("evaluation_id")
    verification_fixture_set_id = verification_details.get("fixture_set_id")
    verification_fixture_set_sha256 = verification_details.get("fixture_set_sha256")
    verification_mined_failure_summary = dict(
        verification_output.mined_failure_summary
        or verification_details.get("mined_failure_summary")
        or {}
    )
    verification_replay_alert_fixture_summary = dict(
        verification_output.replay_alert_fixture_summary
        or verification_details.get("replay_alert_fixture_summary")
        or {}
    )
    verification_replay_alert_fixture_coverage_waiver = dict(
        verification_output.replay_alert_fixture_coverage_waiver
        or verification_details.get("replay_alert_fixture_coverage_waiver")
        or {}
    )
    waiver_activation_approval: dict = {}
    if verification_replay_alert_fixture_coverage_waiver:
        waiver_activation_approval = require_active_replay_alert_fixture_coverage_waiver(
            waiver=verification_replay_alert_fixture_coverage_waiver,
            payload=payload,
            task=task,
        )

    previous_active = get_active_claim_support_calibration_policy(
        session,
        policy_name=draft_output.policy_name,
    )
    activated_policy, retired_policies = activate_claim_support_calibration_policy(
        session,
        policy_id=draft_output.policy_id,
        activation_metadata={
            "activated_by_task_id": str(task.id),
            "verification_task_id": str(payload.verification_task_id),
            "reason": payload.reason,
            "waiver_activation_approval": waiver_activation_approval,
        },
    )
    apply_payload = {
        "draft_task_id": str(payload.draft_task_id),
        "verification_task_id": str(payload.verification_task_id),
        "reason": payload.reason,
        "approved_by": task.approved_by,
        "approved_at": task.approved_at.isoformat() if task.approved_at else None,
        "approval_note": task.approval_note,
        "previous_active_policy_id": (
            str(previous_active.id) if previous_active is not None else None
        ),
        "previous_active_policy_sha256": (
            previous_active.policy_sha256 if previous_active is not None else None
        ),
        "activated_policy_id": str(activated_policy.id),
        "activated_policy_sha256": activated_policy.policy_sha256,
        "policy_name": activated_policy.policy_name,
        "policy_version": activated_policy.policy_version,
        "draft_policy_sha256": draft_output.policy_sha256,
        "verification_id": str(verification.verification_id),
        "verification_outcome": verification.outcome,
        "verification_reasons": list(verification.reasons),
        "verification_evaluation_id": (
            str(verification_evaluation_id) if verification_evaluation_id else None
        ),
        "verification_fixture_set_id": (
            str(verification_fixture_set_id) if verification_fixture_set_id else None
        ),
        "verification_fixture_set_sha256": (
            str(verification_fixture_set_sha256) if verification_fixture_set_sha256 else None
        ),
        "verification_policy_sha256": verification_policy_sha256,
        "verification_replay_alert_fixture_summary": (verification_replay_alert_fixture_summary),
        "verification_replay_alert_fixture_coverage_waiver": (
            verification_replay_alert_fixture_coverage_waiver
        ),
        "verification_mined_failure_summary": verification_mined_failure_summary,
        "waiver_activation_approval": waiver_activation_approval,
        "success_metrics": [
            {
                "metric_key": "claim_support_policy_verification_passed",
                "stakeholder": "Luc Moreau / James Cheney",
                "passed": True,
                "summary": "Only a passed verifier record can activate the calibration policy.",
                "details": {
                    "verification_task_id": str(payload.verification_task_id),
                    "verification_id": str(verification.verification_id),
                    "verification_outcome": verification.outcome,
                    "verification_policy_sha256": verification_policy_sha256,
                    "verification_fixture_set_sha256": verification_fixture_set_sha256,
                    "replay_alert_fixture_summary_sha256": (
                        verification_replay_alert_fixture_summary.get("verification_summary_sha256")
                    ),
                    "replay_alert_fixture_count": (
                        verification_replay_alert_fixture_summary.get(
                            "included_replay_alert_fixture_count"
                        )
                    ),
                    "replay_alert_fixture_coverage_waiver_sha256": (
                        verification_replay_alert_fixture_coverage_waiver.get("waiver_sha256")
                    ),
                    "replay_alert_fixture_coverage_waiver_artifact_id": (
                        verification_replay_alert_fixture_coverage_waiver.get("artifact_id")
                    ),
                    "waiver_activation_approval": waiver_activation_approval,
                    "mined_failure_manifest_sha256": (
                        verification_mined_failure_summary.get("manifest_sha256")
                    ),
                    "mined_failure_summary_sha256": (
                        verification_mined_failure_summary.get("summary_sha256")
                    ),
                    "mined_failure_case_count": (
                        verification_mined_failure_summary.get("mined_failure_case_count")
                    ),
                },
            },
            {
                "metric_key": "claim_support_policy_single_active",
                "stakeholder": "Juan Sequeda",
                "passed": True,
                "summary": "Prior active policies for this policy name were retired.",
                "details": {
                    "policy_name": activated_policy.policy_name,
                    "retired_policy_ids": [str(row.id) for row in retired_policies],
                },
            },
        ],
    }
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="orchestrate",
        operator_name="claim_support_calibration_policy_activation",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "draft_task_id": str(payload.draft_task_id),
            "verification_task_id": str(payload.verification_task_id),
        },
        input_payload={
            "draft_policy": draft_output.policy_payload,
            "verification": verification.model_dump(mode="json"),
            "verification_replay_alert_fixture_summary": (
                verification_replay_alert_fixture_summary
            ),
            "verification_replay_alert_fixture_coverage_waiver": (
                verification_replay_alert_fixture_coverage_waiver
            ),
            "verification_mined_failure_summary": verification_mined_failure_summary,
            "waiver_activation_approval": waiver_activation_approval,
            "reason": payload.reason,
        },
        output_payload=apply_payload,
        metrics={
            "activated_policy_id": str(activated_policy.id),
            "retired_policy_count": len(retired_policies),
        },
        metadata={"audit_role": "activates a verified claim support calibration policy"},
        outputs=[
            {
                "output_kind": "claim_support_calibration_policy_activation",
                "target_table": "claim_support_calibration_policies",
                "target_id": str(activated_policy.id),
                "payload": {
                    "policy_sha256": activated_policy.policy_sha256,
                    "previous_active_policy_id": (
                        str(previous_active.id) if previous_active is not None else None
                    ),
                },
            }
        ],
    )
    result = {
        **apply_payload,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    storage_service = StorageService()
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_calibration_policy_activation",
        payload=result,
        storage_service=storage_service,
        filename="claim_support_calibration_policy_activation.json",
    )
    governance_artifact_id = uuid4()
    governance_artifact_path = (
        storage_service.get_agent_task_dir(task.id)
        / CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_FILENAME
    )
    change_impact_id = uuid4()
    change_impact_payload = build_claim_support_policy_change_impact_payload(
        session,
        task=task,
        activated_policy=activated_policy,
        previous_active_policy=previous_active,
        activation_artifact=artifact,
        governance_artifact_id=governance_artifact_id,
        governance_artifact_path=str(governance_artifact_path),
        apply_payload=result,
        change_impact_id=change_impact_id,
    )
    governance_payload = build_claim_support_policy_activation_governance_payload(
        session,
        task=task,
        activated_policy=activated_policy,
        previous_active_policy=previous_active,
        retired_policies=retired_policies,
        verification=verification.model_dump(mode="json"),
        verification_output=verification_output.model_dump(mode="json"),
        apply_payload=result,
        activation_artifact=artifact,
        governance_artifact_id=governance_artifact_id,
        governance_artifact_path=str(governance_artifact_path),
        operator_run=operator_run,
        change_impact_payload=change_impact_payload,
    )
    governance_artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind=CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
        payload=governance_payload,
        storage_service=storage_service,
        filename=CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_FILENAME,
        artifact_id=governance_artifact_id,
    )
    governance_event = record_claim_support_policy_activation_governance_event(
        session,
        task=task,
        activated_policy=activated_policy,
        governance_artifact=governance_artifact,
        governance_payload=governance_payload,
    )
    change_impact_row = persist_claim_support_policy_change_impact(
        session,
        impact_payload=change_impact_payload,
        task=task,
        activated_policy=activated_policy,
        previous_active_policy=previous_active,
        governance_event=governance_event,
        governance_artifact=governance_artifact,
        change_impact_id=change_impact_id,
        storage_service=storage_service,
    )
    governance_receipt = governance_payload.get("activation_governance_receipt") or {}
    governance_integrity = governance_payload.get("integrity") or {}
    change_impact_summary = change_impact_payload.get("impact_summary") or {}
    change_impact_result = {
        "activation_change_impact_id": str(change_impact_row.id),
        "activation_change_impact_payload_sha256": (
            change_impact_payload.get("activation_change_impact_payload_sha256")
        ),
        "activation_change_impact_summary": change_impact_summary,
        "activation_change_impact_replay_recommended_count": (
            change_impact_summary.get("replay_recommended_count")
        ),
    }
    governance_result = {
        "activation_governance_artifact_id": str(governance_artifact.id),
        "activation_governance_artifact_kind": governance_artifact.artifact_kind,
        "activation_governance_artifact_path": governance_artifact.storage_path,
        "activation_governance_payload_sha256": governance_payload.get(
            "activation_governance_payload_sha256"
        ),
        "activation_governance_receipt_sha256": governance_receipt.get("receipt_sha256"),
        "activation_governance_signature_status": governance_receipt.get("signature_status"),
        "activation_governance_prov_jsonld_sha256": governance_integrity.get("prov_jsonld_sha256"),
        "activation_governance_event_id": str(governance_event.id),
        "activation_governance_event_hash": governance_event.event_hash,
        **change_impact_result,
    }
    final_result = {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        **governance_result,
    }
    if operator_run is not None:
        operator_output_payload = ApplyClaimSupportCalibrationPolicyTaskOutput.model_validate(
            final_result
        ).model_dump(mode="json", exclude_none=True)
        operator_run.output_sha256 = payload_sha256(operator_output_payload)
        operator_run.metrics_json = {
            **dict(operator_run.metrics_json or {}),
            "activation_artifact_id": str(artifact.id),
            "activation_governance_artifact_id": str(governance_artifact.id),
            "activation_governance_receipt_sha256": governance_receipt.get("receipt_sha256"),
            "activation_governance_event_id": str(governance_event.id),
            "activation_change_impact_id": str(change_impact_row.id),
            "activation_change_impact_payload_sha256": (
                change_impact_payload.get("activation_change_impact_payload_sha256")
            ),
            "activation_change_impact_replay_recommended_count": (
                change_impact_summary.get("replay_recommended_count")
            ),
        }
        operator_output = session.scalar(
            select(KnowledgeOperatorOutput)
            .where(
                KnowledgeOperatorOutput.operator_run_id == operator_run.id,
                KnowledgeOperatorOutput.output_kind
                == "claim_support_calibration_policy_activation",
            )
            .order_by(KnowledgeOperatorOutput.output_index.asc())
            .limit(1)
        )
        if operator_output is not None:
            operator_output.payload_json = {
                **dict(operator_output.payload_json or {}),
                **governance_result,
            }
            operator_output.artifact_path = governance_artifact.storage_path
            operator_output.artifact_sha256 = governance_result[
                "activation_governance_payload_sha256"
            ]
    return final_result
