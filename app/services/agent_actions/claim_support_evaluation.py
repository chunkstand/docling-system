from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
)
from app.schemas.agent_task_claim_support import (
    EvaluateClaimSupportJudgeTaskInput,
    QueueClaimSupportPolicyChangeImpactReplayTaskInput,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_evaluations import (
    ensure_claim_support_fixture_set,
    evaluate_claim_support_judge_fixture_set,
    persist_claim_support_judge_evaluation,
    resolve_claim_support_calibration_policy,
)
from app.services.claim_support_policy_impacts import (
    queue_claim_support_policy_change_impact_replay_tasks,
)
from app.services.evidence_operator_runs import record_knowledge_operator_run
from app.services.storage import StorageService


def queue_policy_change_impact_replay_executor(
    session: Session,
    task: AgentTask,
    payload: QueueClaimSupportPolicyChangeImpactReplayTaskInput,
) -> dict:
    replay = queue_claim_support_policy_change_impact_replay_tasks(
        session,
        payload.change_impact_id,
        requested_by=payload.requested_by,
        parent_task_id=task.id,
    )
    replay_payload = replay.model_dump(mode="json")
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_policy_change_impact_replay_plan",
        payload=replay_payload,
        storage_service=StorageService(),
        filename="claim_support_policy_change_impact_replay_plan.json",
    )
    return {
        **replay_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def evaluate_claim_support_judge_executor(
    session: Session,
    task: AgentTask,
    payload: EvaluateClaimSupportJudgeTaskInput,
) -> dict:
    fixture_rows = [fixture.model_dump(mode="json") for fixture in payload.fixtures]
    fixture_set_record = ensure_claim_support_fixture_set(
        session,
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows or None,
        metadata={"source": "evaluate_claim_support_judge"},
    )
    requested_thresholds = {
        "min_overall_accuracy": payload.min_overall_accuracy,
        "min_verdict_precision": payload.min_verdict_precision,
        "min_verdict_recall": payload.min_verdict_recall,
        "min_support_score": payload.min_support_score,
    }
    policy_record = resolve_claim_support_calibration_policy(
        session,
        policy_name=payload.policy_name,
        policy_version=payload.policy_version,
        thresholds=requested_thresholds,
    )
    evaluation_payload = evaluate_claim_support_judge_fixture_set(
        evaluation_name=payload.evaluation_name,
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows or None,
        calibration_policy=policy_record.policy_payload_json,
        fixture_set_id=fixture_set_record.id,
        policy_id=policy_record.id,
        min_support_score=payload.min_support_score,
        min_overall_accuracy=payload.min_overall_accuracy,
        min_verdict_precision=payload.min_verdict_precision,
        min_verdict_recall=payload.min_verdict_recall,
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="technical_report_claim_support_judge_evaluation",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "evaluation_name": payload.evaluation_name,
            "fixture_set_name": payload.fixture_set_name,
            "fixture_set_version": payload.fixture_set_version,
            "fixture_set_id": str(fixture_set_record.id),
            "policy_id": str(policy_record.id),
            "policy_name": policy_record.policy_name,
            "policy_version": policy_record.policy_version,
            "policy_sha256": policy_record.policy_sha256,
            "thresholds": evaluation_payload.get("thresholds") or {},
        },
        input_payload={
            "fixture_set_name": payload.fixture_set_name,
            "fixture_set_version": payload.fixture_set_version,
            "policy_name": payload.policy_name,
            "policy_version": payload.policy_version or "active",
            "custom_fixture_count": len(payload.fixtures),
            "min_support_score": payload.min_support_score,
        },
        output_payload=evaluation_payload,
        metrics=evaluation_payload.get("summary") or {},
        metadata={
            "audit_role": ("records replay evaluation of the technical report claim support judge"),
        },
        outputs=[
            {
                "output_kind": "claim_support_judge_evaluation",
                "target_table": "claim_support_evaluations",
                "target_id": evaluation_payload["evaluation_id"],
                "payload": {
                    "gate_outcome": evaluation_payload["summary"]["gate_outcome"],
                    "case_count": evaluation_payload["summary"]["case_count"],
                    "overall_accuracy": evaluation_payload["summary"]["overall_accuracy"],
                    "fixture_set_sha256": evaluation_payload["fixture_set_sha256"],
                    "policy_sha256": evaluation_payload["policy_sha256"],
                },
            }
        ],
    )
    evaluation_row = persist_claim_support_judge_evaluation(
        session,
        evaluation_payload,
        agent_task_id=task.id,
        operator_run_id=operator_run.id if operator_run is not None else None,
    )
    result_payload = {
        **evaluation_row.evaluation_payload_json,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_judge_evaluation",
        payload=result_payload,
        storage_service=StorageService(),
        filename="claim_support_judge_evaluation.json",
    )
    return {
        **result_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
