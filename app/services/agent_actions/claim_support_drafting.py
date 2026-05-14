from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
)
from app.schemas.agent_task_claim_support import DraftClaimSupportCalibrationPolicyTaskInput
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_evaluations import (
    draft_claim_support_calibration_policy,
    get_active_claim_support_calibration_policy,
)
from app.services.storage import StorageService


def _claim_support_thresholds_payload(payload) -> dict:
    return {
        "min_overall_accuracy": payload.min_overall_accuracy,
        "min_verdict_precision": payload.min_verdict_precision,
        "min_verdict_recall": payload.min_verdict_recall,
        "min_support_score": payload.min_support_score,
    }


def draft_claim_support_calibration_policy_executor(
    session: Session,
    task: AgentTask,
    payload: DraftClaimSupportCalibrationPolicyTaskInput,
) -> dict:
    active_policy = get_active_claim_support_calibration_policy(
        session,
        policy_name=payload.policy_name,
    )
    policy_row = draft_claim_support_calibration_policy(
        session,
        policy_name=payload.policy_name,
        policy_version=payload.policy_version,
        thresholds=_claim_support_thresholds_payload(payload),
        min_hard_case_kind_count=payload.min_hard_case_kind_count,
        required_hard_case_kinds=list(payload.required_hard_case_kinds),
        required_verdicts=list(payload.required_verdicts),
        owner=payload.owner,
        source=payload.source,
        rationale=payload.rationale,
    )
    draft_payload = {
        "policy_id": str(policy_row.id),
        "policy_name": policy_row.policy_name,
        "policy_version": policy_row.policy_version,
        "policy_sha256": policy_row.policy_sha256,
        "policy_payload": policy_row.policy_payload_json,
        "active_policy_id": str(active_policy.id) if active_policy is not None else None,
        "active_policy_sha256": active_policy.policy_sha256 if active_policy is not None else None,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_calibration_policy_draft",
        payload=draft_payload,
        storage_service=StorageService(),
        filename="claim_support_calibration_policy_draft.json",
    )
    return {
        **draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
