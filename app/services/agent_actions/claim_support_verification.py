from __future__ import annotations

from datetime import UTC, timedelta

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask
from app.db.public.claim_support import ClaimSupportCalibrationPolicy
from app.schemas.agent_task_claim_support import (
    DraftClaimSupportCalibrationPolicyTaskOutput,
    VerifyClaimSupportCalibrationPolicyTaskInput,
)
from app.services.agent_actions.claim_support_shared import (
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_EXPIRING_HOURS,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_FILENAME,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA_VERSION,
    replay_alert_fixture_coverage_waiver_sha256,
    require_policy_row_matches_draft_output,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
)
from app.services.claim_support_evaluations import (
    default_claim_support_evaluation_fixtures,
    ensure_claim_support_fixture_set,
    evaluate_claim_support_judge_fixture_set,
    mine_claim_support_failure_fixtures,
    persist_claim_support_judge_evaluation,
)
from app.services.claim_support_policy_impacts import (
    latest_claim_support_replay_alert_fixture_rows,
)
from app.services.claim_support_replay_alert_waivers import (
    record_replay_alert_fixture_coverage_waiver_ledger,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_operator_runs import record_knowledge_operator_run
from app.services.storage import StorageService


def verify_claim_support_calibration_policy_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyClaimSupportCalibrationPolicyTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_claim_support_calibration_policy",
        expected_schema_name="draft_claim_support_calibration_policy_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Claim-support policy verification must declare the requested policy draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target claim-support policy draft must be rerun after the context migration "
            "before verification."
        ),
    )
    draft_output = DraftClaimSupportCalibrationPolicyTaskOutput.model_validate(draft_context.output)
    policy_row = session.get(ClaimSupportCalibrationPolicy, draft_output.policy_id)
    if policy_row is None:
        raise ValueError(f"Claim support calibration policy not found: {draft_output.policy_id}")
    require_policy_row_matches_draft_output(policy_row, draft_output)
    if policy_row.status != "draft":
        raise ValueError("Only draft claim support calibration policies can be verified.")

    explicit_fixture_rows = [fixture.model_dump(mode="json") for fixture in payload.fixtures]
    default_fixture_rows = (
        [] if explicit_fixture_rows else default_claim_support_evaluation_fixtures()
    )
    base_fixture_rows = explicit_fixture_rows or default_fixture_rows
    base_case_ids = {
        str(fixture.get("case_id")) for fixture in base_fixture_rows if fixture.get("case_id")
    }
    replay_alert_fixture_rows, replay_alert_fixture_summary = (
        latest_claim_support_replay_alert_fixture_rows(
            session,
            include_promoted=payload.include_replay_alert_fixtures,
            limit=payload.replay_alert_fixture_limit,
            exclude_case_ids=base_case_ids,
        )
    )
    replay_case_ids = {
        str(fixture.get("case_id"))
        for fixture in replay_alert_fixture_rows
        if fixture.get("case_id")
    }
    mined_fixture_rows, mined_failure_manifest = mine_claim_support_failure_fixtures(
        session,
        limit=payload.mined_failure_limit if payload.include_mined_failures else 0,
        exclude_case_ids=base_case_ids | replay_case_ids,
    )
    fixture_rows = [*base_fixture_rows, *replay_alert_fixture_rows, *mined_fixture_rows]
    replay_alert_summary_basis = {
        **replay_alert_fixture_summary,
        "explicit_fixture_count": len(explicit_fixture_rows),
        "default_fixture_count": len(default_fixture_rows),
        "base_fixture_count": len(base_fixture_rows),
        "combined_pre_mined_fixture_count": len(base_fixture_rows) + len(replay_alert_fixture_rows),
    }
    replay_alert_fixture_summary = {
        **replay_alert_summary_basis,
        "verification_summary_sha256": str(payload_sha256(replay_alert_summary_basis)),
    }
    mined_failure_summary_basis = {
        **mined_failure_manifest,
        "enabled": payload.include_mined_failures,
        "explicit_fixture_count": len(explicit_fixture_rows),
        "default_fixture_count": len(default_fixture_rows),
        "replay_alert_fixture_count": len(replay_alert_fixture_rows),
        "combined_fixture_count": len(fixture_rows),
    }
    mined_failure_summary = {
        **mined_failure_summary_basis,
        "summary_sha256": str(payload_sha256(mined_failure_summary_basis)),
    }
    fixture_set_record = ensure_claim_support_fixture_set(
        session,
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows,
        metadata={
            "source": "verify_claim_support_calibration_policy",
            "mined_failure_summary": mined_failure_summary,
            "replay_alert_fixture_summary": replay_alert_fixture_summary,
        },
    )
    replay_alert_fixture_coverage_waiver: dict = {}
    if not payload.require_replay_alert_fixture_coverage:
        waived_at = utcnow()
        waiver_expires_at = payload.replay_alert_fixture_coverage_waiver_expires_at.astimezone(UTC)
        waiver_review_due_at = max(
            waived_at,
            waiver_expires_at
            - timedelta(hours=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_EXPIRING_HOURS),
        )
        waiver_basis = {
            "schema_name": "claim_support_replay_alert_fixture_coverage_waiver",
            "schema_version": CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA_VERSION,
            "verification_task_id": str(task.id),
            "target_task_id": str(payload.target_task_id),
            "policy_id": str(policy_row.id),
            "policy_sha256": policy_row.policy_sha256,
            "fixture_set_id": str(fixture_set_record.id),
            "fixture_set_sha256": fixture_set_record.fixture_set_sha256,
            "waived_by": payload.replay_alert_fixture_coverage_waived_by,
            "waiver_reason": payload.replay_alert_fixture_coverage_waiver_reason,
            "waiver_severity": (payload.replay_alert_fixture_coverage_waiver_severity),
            "waiver_expires_at": waiver_expires_at.isoformat(),
            "waiver_review_due_at": waiver_review_due_at.isoformat(),
            "waiver_remediation_owner": (
                payload.replay_alert_fixture_coverage_waiver_remediation_owner
            ),
            "waiver_status": "active",
            "waived_at": waived_at.isoformat(),
            "replay_alert_fixture_summary": replay_alert_fixture_summary,
            "replay_alert_fixture_summary_sha256": replay_alert_fixture_summary[
                "verification_summary_sha256"
            ],
            "stale_unconverted_escalation_event_count": (
                replay_alert_fixture_summary.get("stale_unconverted_escalation_event_count")
            ),
            "stale_unconverted_escalation_event_ids": (
                replay_alert_fixture_summary.get("stale_unconverted_escalation_event_ids") or []
            ),
            "stale_unconverted_escalation_set_sha256": (
                replay_alert_fixture_summary.get("stale_unconverted_escalation_set_sha256")
            ),
            "stale_unconverted_escalation_events": (
                replay_alert_fixture_summary.get("stale_unconverted_escalation_events") or []
            ),
        }
        waiver_payload = {
            **waiver_basis,
            "waiver_sha256": str(replay_alert_fixture_coverage_waiver_sha256(waiver_basis)),
        }
        waiver_artifact = create_agent_task_artifact(
            session,
            task_id=task.id,
            artifact_kind=(CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND),
            payload=waiver_payload,
            storage_service=StorageService(),
            filename=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_FILENAME,
        )
        waiver_ledger = record_replay_alert_fixture_coverage_waiver_ledger(
            session,
            waiver_artifact=waiver_artifact,
            waiver_payload=waiver_payload,
        )
        replay_alert_fixture_coverage_waiver = {
            **waiver_payload,
            "artifact_id": str(waiver_artifact.id),
            "artifact_kind": waiver_artifact.artifact_kind,
            "artifact_path": waiver_artifact.storage_path,
            "coverage_ledger_id": str(waiver_ledger.id),
            "coverage_status": waiver_ledger.coverage_status,
            "waived_escalation_event_count": (waiver_ledger.waived_escalation_event_count),
            "waived_escalation_set_sha256": (waiver_ledger.waived_escalation_set_sha256),
        }
    evaluation_payload = evaluate_claim_support_judge_fixture_set(
        evaluation_name="claim_support_calibration_policy_verification",
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows,
        calibration_policy=policy_row.policy_payload_json,
        fixture_set_id=fixture_set_record.id,
        policy_id=policy_row.id,
    )
    invalid_replay_alert_corpus_promotion_count = int(
        replay_alert_fixture_summary.get(
            "active_replay_alert_fixture_corpus_invalid_promotion_event_count"
        )
        or 0
    )
    active_replay_alert_corpus_governed = bool(
        replay_alert_fixture_summary.get("active_replay_alert_fixture_corpus_governed")
    )
    active_replay_alert_corpus_snapshot_id = replay_alert_fixture_summary.get(
        "active_replay_alert_fixture_corpus_snapshot_id"
    )
    replay_alert_coverage_passed = not payload.require_replay_alert_fixture_coverage or (
        int(replay_alert_fixture_summary.get("stale_unconverted_escalation_event_count") or 0) == 0
        and invalid_replay_alert_corpus_promotion_count == 0
        and (not active_replay_alert_corpus_snapshot_id or active_replay_alert_corpus_governed)
    )
    replay_alert_coverage_metric = {
        "metric_key": "claim_support_replay_alert_fixture_coverage",
        "stakeholder": "Omar Khattab / Luc Moreau / James Cheney",
        "passed": replay_alert_coverage_passed,
        "summary": (
            "Stale replay escalation receipts are represented in promoted "
            "claim-support fixture coverage."
        ),
        "details": {
            "required": payload.require_replay_alert_fixture_coverage,
            "enabled": replay_alert_fixture_summary.get("enabled"),
            "waiver": replay_alert_fixture_coverage_waiver,
            "included_replay_alert_fixture_count": replay_alert_fixture_summary.get(
                "included_replay_alert_fixture_count"
            ),
            "promoted_fixture_set_count": replay_alert_fixture_summary.get(
                "promoted_fixture_set_count"
            ),
            "promoted_escalation_event_count": replay_alert_fixture_summary.get(
                "promoted_escalation_event_count"
            ),
            "active_replay_alert_fixture_corpus_snapshot_id": (
                replay_alert_fixture_summary.get("active_replay_alert_fixture_corpus_snapshot_id")
            ),
            "active_replay_alert_fixture_corpus_sha256": (
                replay_alert_fixture_summary.get("active_replay_alert_fixture_corpus_sha256")
            ),
            "active_replay_alert_fixture_corpus_invalid_promotion_event_count": (
                invalid_replay_alert_corpus_promotion_count
            ),
            "active_replay_alert_fixture_corpus_governed": (active_replay_alert_corpus_governed),
            "active_replay_alert_fixture_corpus_governance_failures": (
                replay_alert_fixture_summary.get(
                    "active_replay_alert_fixture_corpus_governance_failures"
                )
                or []
            ),
            "active_replay_alert_fixture_corpus_governance_event_id": (
                replay_alert_fixture_summary.get(
                    "active_replay_alert_fixture_corpus_governance_event_id"
                )
            ),
            "active_replay_alert_fixture_corpus_governance_artifact_id": (
                replay_alert_fixture_summary.get(
                    "active_replay_alert_fixture_corpus_governance_artifact_id"
                )
            ),
            "active_replay_alert_fixture_corpus_governance_receipt_sha256": (
                replay_alert_fixture_summary.get(
                    "active_replay_alert_fixture_corpus_governance_receipt_sha256"
                )
            ),
            "unconverted_escalation_event_count": replay_alert_fixture_summary.get(
                "unconverted_escalation_event_count"
            ),
            "stale_unconverted_escalation_event_count": replay_alert_fixture_summary.get(
                "stale_unconverted_escalation_event_count"
            ),
            "replay_alert_fixture_summary_sha256": replay_alert_fixture_summary.get(
                "verification_summary_sha256"
            ),
        },
    }
    evaluation_payload["success_metrics"] = [
        *list(evaluation_payload.get("success_metrics") or []),
        replay_alert_coverage_metric,
    ]
    evaluation_payload["summary"] = {
        **dict(evaluation_payload.get("summary") or {}),
        "replay_alert_fixture_coverage_required": (payload.require_replay_alert_fixture_coverage),
        "replay_alert_fixture_coverage_passed": replay_alert_coverage_passed,
        "replay_alert_fixture_coverage_waiver_sha256": (
            replay_alert_fixture_coverage_waiver.get("waiver_sha256")
        ),
        "replay_alert_fixture_coverage_waiver_artifact_id": (
            replay_alert_fixture_coverage_waiver.get("artifact_id")
        ),
        "included_replay_alert_fixture_count": replay_alert_fixture_summary.get(
            "included_replay_alert_fixture_count"
        ),
        "stale_unconverted_escalation_event_count": replay_alert_fixture_summary.get(
            "stale_unconverted_escalation_event_count"
        ),
        "active_replay_alert_fixture_corpus_invalid_promotion_event_count": (
            invalid_replay_alert_corpus_promotion_count
        ),
        "active_replay_alert_fixture_corpus_governed": (active_replay_alert_corpus_governed),
        "active_replay_alert_fixture_corpus_governance_failures": (
            replay_alert_fixture_summary.get(
                "active_replay_alert_fixture_corpus_governance_failures"
            )
            or []
        ),
        "replay_alert_fixture_summary_sha256": replay_alert_fixture_summary.get(
            "verification_summary_sha256"
        ),
    }
    if not replay_alert_coverage_passed:
        coverage_reason = replay_alert_coverage_metric["summary"]
        existing_reasons = list(evaluation_payload.get("reasons") or [])
        if coverage_reason not in existing_reasons:
            existing_reasons.append(coverage_reason)
        evaluation_payload["reasons"] = existing_reasons
        evaluation_payload["summary"]["gate_outcome"] = "failed"
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="claim_support_calibration_policy_verification",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "policy_id": str(policy_row.id),
            "policy_sha256": policy_row.policy_sha256,
            "fixture_set_id": str(fixture_set_record.id),
            "fixture_set_sha256": fixture_set_record.fixture_set_sha256,
            "mined_failure_manifest_sha256": mined_failure_summary["manifest_sha256"],
            "mined_failure_summary_sha256": mined_failure_summary["summary_sha256"],
            "mined_failure_case_count": mined_failure_summary["mined_failure_case_count"],
            "replay_alert_fixture_count": replay_alert_fixture_summary[
                "included_replay_alert_fixture_count"
            ],
            "replay_alert_fixture_summary_sha256": replay_alert_fixture_summary[
                "verification_summary_sha256"
            ],
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "policy_payload": policy_row.policy_payload_json,
            "fixture_set_name": payload.fixture_set_name,
            "fixture_set_version": payload.fixture_set_version,
            "include_replay_alert_fixtures": payload.include_replay_alert_fixtures,
            "replay_alert_fixture_limit": payload.replay_alert_fixture_limit,
            "require_replay_alert_fixture_coverage": (
                payload.require_replay_alert_fixture_coverage
            ),
            "replay_alert_fixture_coverage_waiver": (replay_alert_fixture_coverage_waiver),
            "replay_alert_fixture_summary": replay_alert_fixture_summary,
            "include_mined_failures": payload.include_mined_failures,
            "mined_failure_limit": payload.mined_failure_limit,
            "mined_failure_summary": mined_failure_summary,
        },
        output_payload=evaluation_payload,
        metrics=evaluation_payload.get("summary") or {},
        metadata={"audit_role": "verifies a draft claim support calibration policy"},
        outputs=[
            {
                "output_kind": "claim_support_policy_verification",
                "target_table": "claim_support_calibration_policies",
                "target_id": str(policy_row.id),
                "payload": {
                    "gate_outcome": evaluation_payload["summary"]["gate_outcome"],
                    "policy_sha256": policy_row.policy_sha256,
                    "fixture_set_sha256": fixture_set_record.fixture_set_sha256,
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
    result_evaluation = {
        **evaluation_row.evaluation_payload_json,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    outcome = str(result_evaluation["summary"]["gate_outcome"])
    reasons = list(result_evaluation.get("reasons") or [])
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=task.id,
        verifier_type="claim_support_calibration_policy_gate",
        outcome=outcome,
        metrics=dict(result_evaluation.get("summary") or {}),
        reasons=reasons,
        details={
            "policy_id": str(policy_row.id),
            "policy_sha256": policy_row.policy_sha256,
            "fixture_set_id": str(fixture_set_record.id),
            "fixture_set_sha256": fixture_set_record.fixture_set_sha256,
            "evaluation_id": result_evaluation["evaluation_id"],
            "replay_alert_fixture_summary": replay_alert_fixture_summary,
            "replay_alert_fixture_coverage_waiver": (replay_alert_fixture_coverage_waiver),
            "mined_failure_summary": mined_failure_summary,
        },
    )
    result = {
        "draft_policy": policy_row.policy_payload_json,
        "evaluation": result_evaluation,
        "verification": record.model_dump(mode="json"),
        "replay_alert_fixture_summary": replay_alert_fixture_summary,
        "replay_alert_fixture_coverage_waiver": replay_alert_fixture_coverage_waiver,
        "mined_failure_summary": mined_failure_summary,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_calibration_policy_verification",
        payload=result,
        storage_service=StorageService(),
        filename="claim_support_calibration_policy_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
