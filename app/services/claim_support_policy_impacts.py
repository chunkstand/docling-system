from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskStatus,
    AgentTaskVerification,
    ClaimSupportPolicyChangeImpact,
)
from app.schemas.agent_tasks import (
    AgentTaskCreateRequest,
    ClaimSupportPolicyChangeImpactReplayResponse,
    ClaimSupportPolicyChangeImpactReplayTaskResponse,
    ClaimSupportPolicyChangeImpactResponse,
)
from app.services.evidence import payload_sha256

CLAIM_SUPPORT_IMPACT_REPLAY_WORKFLOW_VERSION = "claim_support_policy_change_impact_replay_v1"
CLAIM_SUPPORT_IMPACT_REPLAY_PLAN_SCHEMA = "claim_support_policy_change_impact_replay_plan"
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_SCHEMA = "claim_support_policy_change_impact_replay_closure"
REPLAY_TERMINAL_FAILURE_STATUSES = {
    AgentTaskStatus.FAILED.value,
    AgentTaskStatus.REJECTED.value,
}
REPLAY_ACTIVE_STATUSES = {
    AgentTaskStatus.PROCESSING.value,
    AgentTaskStatus.RETRY_WAIT.value,
}


def _uuid_or_none(value) -> UUID | None:
    if value in {None, ""}:
        return None
    return UUID(str(value))


def _uuid_list(values) -> list[UUID]:
    rows: list[UUID] = []
    for value in values or []:
        if value in {None, ""}:
            continue
        rows.append(UUID(str(value)))
    return rows


def _string_list(values) -> list[str]:
    return [str(value) for value in values or [] if value not in {None, ""}]


def _impact_not_found(change_impact_id: UUID):
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "claim_support_policy_change_impact_not_found",
        "Claim support policy change impact row was not found.",
        change_impact_id=str(change_impact_id),
    )


def _get_impact_row(
    session: Session,
    change_impact_id: UUID,
) -> ClaimSupportPolicyChangeImpact:
    row = session.get(ClaimSupportPolicyChangeImpact, change_impact_id)
    if row is None:
        raise _impact_not_found(change_impact_id)
    return row


def _latest_verification_by_task(
    session: Session,
    verification_task_ids: list[UUID],
) -> dict[UUID, AgentTaskVerification]:
    if not verification_task_ids:
        return {}
    rows = (
        session.execute(
            select(AgentTaskVerification)
            .where(
                AgentTaskVerification.verification_task_id.in_(verification_task_ids),
                AgentTaskVerification.verifier_type == "technical_report_gate",
            )
            .order_by(
                AgentTaskVerification.verification_task_id,
                AgentTaskVerification.created_at.desc(),
                AgentTaskVerification.id.desc(),
            )
        )
        .scalars()
        .all()
    )
    latest: dict[UUID, AgentTaskVerification] = {}
    for row in rows:
        if row.verification_task_id is not None and row.verification_task_id not in latest:
            latest[row.verification_task_id] = row
    return latest


def _impact_response(
    row: ClaimSupportPolicyChangeImpact,
) -> ClaimSupportPolicyChangeImpactResponse:
    return ClaimSupportPolicyChangeImpactResponse(
        change_impact_id=row.id,
        activation_task_id=row.activation_task_id,
        activated_policy_id=row.activated_policy_id,
        previous_policy_id=row.previous_policy_id,
        semantic_governance_event_id=row.semantic_governance_event_id,
        governance_artifact_id=row.governance_artifact_id,
        impact_scope=row.impact_scope,
        policy_name=row.policy_name,
        policy_version=row.policy_version,
        activated_policy_sha256=row.activated_policy_sha256,
        previous_policy_sha256=row.previous_policy_sha256,
        affected_support_judgment_count=row.affected_support_judgment_count,
        affected_generated_document_count=row.affected_generated_document_count,
        affected_verification_count=row.affected_verification_count,
        replay_recommended_count=row.replay_recommended_count,
        replay_status=row.replay_status,
        impacted_claim_derivation_ids=_string_list(row.impacted_claim_derivation_ids_json),
        impacted_task_ids=_string_list(row.impacted_task_ids_json),
        impacted_verification_task_ids=_string_list(row.impacted_verification_task_ids_json),
        impact_payload_sha256=row.impact_payload_sha256,
        impact_payload=dict(row.impact_payload_json or {}),
        replay_task_ids=_uuid_list(row.replay_task_ids_json),
        replay_task_plan=dict(row.replay_task_plan_json or {}),
        replay_closure=dict(row.replay_closure_json or {}),
        replay_closure_sha256=row.replay_closure_sha256,
        replay_status_updated_at=row.replay_status_updated_at,
        replay_closed_at=row.replay_closed_at,
        created_at=row.created_at,
    )


def _replay_task_response(task_spec: dict) -> ClaimSupportPolicyChangeImpactReplayTaskResponse:
    return ClaimSupportPolicyChangeImpactReplayTaskResponse(
        action=str(task_spec.get("action") or ""),
        source_task_id=_uuid_or_none(task_spec.get("source_task_id")),
        prior_verification_task_id=_uuid_or_none(task_spec.get("prior_verification_task_id")),
        replay_task_id=UUID(str(task_spec["replay_task_id"])),
        task_type=str(task_spec.get("task_type") or ""),
        status=str(task_spec.get("status") or ""),
        dependency_task_ids=_uuid_list(task_spec.get("dependency_task_ids") or []),
        reason=task_spec.get("reason"),
    )


def _replay_response(
    row: ClaimSupportPolicyChangeImpact,
    *,
    created_tasks: list[dict] | None = None,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    plan = dict(row.replay_task_plan_json or {})
    task_specs = created_tasks if created_tasks is not None else list(plan.get("tasks") or [])
    return ClaimSupportPolicyChangeImpactReplayResponse(
        change_impact=_impact_response(row),
        replay_status=row.replay_status,
        replay_task_ids=_uuid_list(row.replay_task_ids_json),
        created_tasks=[_replay_task_response(task_spec) for task_spec in task_specs],
        replay_task_plan=plan,
        replay_closure=dict(row.replay_closure_json or {}),
        replay_closure_sha256=row.replay_closure_sha256,
    )


def list_claim_support_policy_change_impacts(
    session: Session,
    *,
    policy_name: str | None = None,
    replay_status: str | None = None,
    limit: int = 50,
) -> list[ClaimSupportPolicyChangeImpactResponse]:
    statement = (
        select(ClaimSupportPolicyChangeImpact)
        .order_by(
            ClaimSupportPolicyChangeImpact.created_at.desc(),
            ClaimSupportPolicyChangeImpact.id.desc(),
        )
        .limit(limit)
    )
    if policy_name is not None:
        statement = statement.where(ClaimSupportPolicyChangeImpact.policy_name == policy_name)
    if replay_status is not None:
        statement = statement.where(ClaimSupportPolicyChangeImpact.replay_status == replay_status)
    return [_impact_response(row) for row in session.execute(statement).scalars().all()]


def get_claim_support_policy_change_impact(
    session: Session,
    change_impact_id: UUID,
) -> ClaimSupportPolicyChangeImpactResponse:
    return _impact_response(_get_impact_row(session, change_impact_id))


def _require_source_task(
    session: Session,
    *,
    task_id: UUID,
    expected_task_type: str,
    change_impact_id: UUID,
) -> AgentTask:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_source_task_not_found",
            "A replay recommendation points at a task that no longer exists.",
            change_impact_id=str(change_impact_id),
            source_task_id=str(task_id),
            expected_task_type=expected_task_type,
        )
    if task.task_type != expected_task_type:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_source_task_type_mismatch",
            "A replay recommendation points at an unexpected task type.",
            change_impact_id=str(change_impact_id),
            source_task_id=str(task_id),
            expected_task_type=expected_task_type,
            actual_task_type=task.task_type,
        )
    return task


def _queue_agent_task(
    session: Session,
    *,
    source_task: AgentTask,
    task_type: str,
    task_input: dict,
    parent_task_id: UUID | None,
    dependency_task_ids: list[UUID] | None = None,
):
    from app.services.agent_tasks import create_agent_task

    return create_agent_task(
        session,
        AgentTaskCreateRequest(
            task_type=task_type,
            priority=source_task.priority,
            parent_task_id=parent_task_id,
            dependency_task_ids=dependency_task_ids or [],
            input=task_input,
            workflow_version=CLAIM_SUPPORT_IMPACT_REPLAY_WORKFLOW_VERSION,
            tool_version=source_task.tool_version,
            prompt_version=source_task.prompt_version,
            model=source_task.model,
            model_settings=dict(source_task.model_settings_json or {}),
        ),
    )


def queue_claim_support_policy_change_impact_replay_tasks(
    session: Session,
    change_impact_id: UUID,
    *,
    requested_by: str,
    parent_task_id: UUID | None = None,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    row = _get_impact_row(session, change_impact_id)
    if row.replay_recommended_count <= 0:
        return refresh_claim_support_policy_change_impact_replay_status(
            session,
            change_impact_id,
        )
    if row.replay_task_ids_json:
        return refresh_claim_support_policy_change_impact_replay_status(
            session,
            change_impact_id,
        )

    recommendations = list((row.impact_payload_json or {}).get("replay_recommendations") or [])
    if not recommendations:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_recommendations_missing",
            "The impact row requires replay but does not contain replay recommendations.",
            change_impact_id=str(change_impact_id),
        )

    parent_task_id = parent_task_id or row.activation_task_id
    draft_replay_task_ids: dict[str, UUID] = {}
    created_task_specs: list[dict] = []

    for recommendation in recommendations:
        action = str(recommendation.get("action") or "")
        if action == "rerun_draft_technical_report":
            source_task_id = UUID(str(recommendation["target_task_id"]))
            source_task = _require_source_task(
                session,
                task_id=source_task_id,
                expected_task_type="draft_technical_report",
                change_impact_id=change_impact_id,
            )
            if str(source_task_id) in draft_replay_task_ids:
                continue
            task_detail = _queue_agent_task(
                session,
                source_task=source_task,
                task_type="draft_technical_report",
                task_input=dict(source_task.input_json or {}),
                parent_task_id=parent_task_id,
            )
            draft_replay_task_ids[str(source_task_id)] = task_detail.task_id
            created_task_specs.append(
                {
                    "action": action,
                    "source_task_id": str(source_task_id),
                    "replay_task_id": str(task_detail.task_id),
                    "task_type": "draft_technical_report",
                    "status": task_detail.status,
                    "dependency_task_ids": [
                        str(value) for value in task_detail.dependency_task_ids
                    ],
                    "reason": recommendation.get("reason"),
                    "priority": recommendation.get("priority"),
                }
            )
        elif action == "rerun_verify_technical_report":
            source_draft_task_id = UUID(str(recommendation["target_task_id"]))
            replay_draft_task_id = draft_replay_task_ids.get(str(source_draft_task_id))
            if replay_draft_task_id is None:
                source_draft_task = _require_source_task(
                    session,
                    task_id=source_draft_task_id,
                    expected_task_type="draft_technical_report",
                    change_impact_id=change_impact_id,
                )
                task_detail = _queue_agent_task(
                    session,
                    source_task=source_draft_task,
                    task_type="draft_technical_report",
                    task_input=dict(source_draft_task.input_json or {}),
                    parent_task_id=parent_task_id,
                )
                replay_draft_task_id = task_detail.task_id
                draft_replay_task_ids[str(source_draft_task_id)] = replay_draft_task_id
                created_task_specs.append(
                    {
                        "action": "rerun_draft_technical_report",
                        "source_task_id": str(source_draft_task_id),
                        "replay_task_id": str(task_detail.task_id),
                        "task_type": "draft_technical_report",
                        "status": task_detail.status,
                        "dependency_task_ids": [
                            str(value) for value in task_detail.dependency_task_ids
                        ],
                        "reason": "Required before replaying technical-report verification.",
                        "priority": "high",
                    }
                )
            prior_verification_task_id = UUID(str(recommendation["prior_verification_task_id"]))
            source_task = _require_source_task(
                session,
                task_id=prior_verification_task_id,
                expected_task_type="verify_technical_report",
                change_impact_id=change_impact_id,
            )
            verify_input = dict(source_task.input_json or {})
            verify_input["target_task_id"] = str(replay_draft_task_id)
            task_detail = _queue_agent_task(
                session,
                source_task=source_task,
                task_type="verify_technical_report",
                task_input=verify_input,
                parent_task_id=parent_task_id,
                dependency_task_ids=[replay_draft_task_id],
            )
            created_task_specs.append(
                {
                    "action": action,
                    "source_task_id": str(source_draft_task_id),
                    "prior_verification_task_id": str(prior_verification_task_id),
                    "replay_task_id": str(task_detail.task_id),
                    "task_type": "verify_technical_report",
                    "status": task_detail.status,
                    "dependency_task_ids": [
                        str(value) for value in task_detail.dependency_task_ids
                    ],
                    "reason": recommendation.get("reason"),
                    "priority": recommendation.get("priority"),
                }
            )
        else:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "claim_support_impact_replay_action_unknown",
                "The impact row contains an unsupported replay recommendation action.",
                change_impact_id=str(change_impact_id),
                action=action,
            )

    row = _get_impact_row(session, change_impact_id)
    task_ids = [spec["replay_task_id"] for spec in created_task_specs]
    plan_basis = {
        "schema_name": CLAIM_SUPPORT_IMPACT_REPLAY_PLAN_SCHEMA,
        "schema_version": "1.0",
        "change_impact_id": str(row.id),
        "impact_payload_sha256": row.impact_payload_sha256,
        "created_at": utcnow().isoformat(),
        "created_by": requested_by,
        "replay_recommended_count": row.replay_recommended_count,
        "created_task_count": len(created_task_specs),
        "tasks": created_task_specs,
    }
    replay_plan = {
        **plan_basis,
        "replay_task_plan_sha256": payload_sha256(plan_basis),
    }
    row.replay_task_ids_json = task_ids
    row.replay_task_plan_json = replay_plan
    row.replay_status = "queued"
    row.replay_status_updated_at = utcnow()
    row.replay_closed_at = None
    row.replay_closure_json = {}
    row.replay_closure_sha256 = None
    session.add(row)
    session.commit()
    return _replay_response(row, created_tasks=created_task_specs)


def refresh_claim_support_policy_change_impact_replay_status(
    session: Session,
    change_impact_id: UUID,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    row = _get_impact_row(session, change_impact_id)
    now = utcnow()
    if row.replay_recommended_count <= 0:
        closure_basis = {
            "schema_name": CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_SCHEMA,
            "schema_version": "1.0",
            "change_impact_id": str(row.id),
            "impact_payload_sha256": row.impact_payload_sha256,
            "status": "no_action_required",
            "closed": True,
            "evaluated_at": now.isoformat(),
            "reasons": ["No replay was recommended for this policy change impact."],
            "tasks": [],
        }
        row.replay_status = "no_action_required"
        row.replay_status_updated_at = now
        row.replay_closed_at = row.replay_closed_at or now
        row.replay_closure_json = {
            **closure_basis,
            "replay_closure_sha256": payload_sha256(closure_basis),
        }
        row.replay_closure_sha256 = row.replay_closure_json["replay_closure_sha256"]
        session.add(row)
        session.commit()
        return _replay_response(row)

    replay_task_ids = _uuid_list(row.replay_task_ids_json)
    if not replay_task_ids:
        row.replay_status = "pending"
        row.replay_status_updated_at = now
        row.replay_closed_at = None
        row.replay_closure_json = {}
        row.replay_closure_sha256 = None
        session.add(row)
        session.commit()
        return _replay_response(row)

    task_rows = (
        session.execute(select(AgentTask).where(AgentTask.id.in_(replay_task_ids)))
        .scalars()
        .all()
    )
    tasks_by_id = {task.id: task for task in task_rows}
    plan_tasks = list((row.replay_task_plan_json or {}).get("tasks") or [])
    verification_task_ids = [
        UUID(str(task_spec["replay_task_id"]))
        for task_spec in plan_tasks
        if task_spec.get("task_type") == "verify_technical_report"
        and task_spec.get("replay_task_id")
    ]
    latest_verifications = _latest_verification_by_task(session, verification_task_ids)
    task_statuses: list[dict] = []
    reasons: list[str] = []
    all_closed = True
    blocked = False
    in_progress = False

    for task_spec in plan_tasks:
        replay_task_id = UUID(str(task_spec["replay_task_id"]))
        task = tasks_by_id.get(replay_task_id)
        verification = latest_verifications.get(replay_task_id)
        task_status = task.status if task is not None else "missing"
        verification_outcome = verification.outcome if verification is not None else None
        task_closed = task_status == AgentTaskStatus.COMPLETED.value
        if task_spec.get("task_type") == "verify_technical_report":
            task_closed = task_closed and verification_outcome == "passed"
        if task_status in REPLAY_TERMINAL_FAILURE_STATUSES or task_status == "missing":
            blocked = True
        if task_status in REPLAY_ACTIVE_STATUSES:
            in_progress = True
        if task_status == AgentTaskStatus.COMPLETED.value and (
            task_spec.get("task_type") == "verify_technical_report"
            and verification_outcome != "passed"
        ):
            blocked = True
        if not task_closed:
            all_closed = False
        task_statuses.append(
            {
                **task_spec,
                "status": task_status,
                "completed_at": task.completed_at.isoformat()
                if task is not None and task.completed_at
                else None,
                "verification_id": str(verification.id) if verification is not None else None,
                "verification_outcome": verification_outcome,
            }
        )

    if blocked:
        replay_status = "blocked"
        reasons.append(
            "At least one replay task failed, is missing, or completed without a passed "
            "technical-report gate."
        )
    elif all_closed:
        replay_status = "closed"
        reasons.append("All replay tasks completed with required verification evidence.")
    elif in_progress:
        replay_status = "in_progress"
        reasons.append("At least one replay task is actively processing or waiting to retry.")
    else:
        replay_status = "queued"
        reasons.append("Replay tasks have been created but have not all completed.")

    closure_basis = {
        "schema_name": CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_SCHEMA,
        "schema_version": "1.0",
        "change_impact_id": str(row.id),
        "impact_payload_sha256": row.impact_payload_sha256,
        "status": replay_status,
        "closed": replay_status == "closed",
        "evaluated_at": now.isoformat(),
        "replay_task_count": len(replay_task_ids),
        "completed_task_count": sum(
            1
            for task_id in replay_task_ids
            if tasks_by_id.get(task_id) is not None
            and tasks_by_id[task_id].status == AgentTaskStatus.COMPLETED.value
        ),
        "passed_verification_task_count": sum(
            1
            for task_id, verification in latest_verifications.items()
            if task_id in replay_task_ids and verification.outcome == "passed"
        ),
        "reasons": reasons,
        "tasks": task_statuses,
    }
    row.replay_status = replay_status
    row.replay_status_updated_at = now
    row.replay_closed_at = now if replay_status == "closed" else None
    if replay_status == "closed":
        row.replay_closure_json = {
            **closure_basis,
            "replay_closure_sha256": payload_sha256(closure_basis),
        }
        row.replay_closure_sha256 = row.replay_closure_json["replay_closure_sha256"]
    else:
        row.replay_closure_json = closure_basis
        row.replay_closure_sha256 = None
    session.add(row)
    session.commit()
    return _replay_response(row)
