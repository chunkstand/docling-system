from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_core import AgentTaskCreateRequest
from app.services.claim_support_policy_impact_replay import (
    CLAIM_SUPPORT_IMPACT_REPLAY_PLAN_SCHEMA,
    CLAIM_SUPPORT_IMPACT_REPLAY_WORKFLOW_VERSION,
    REPLAY_PLAN_HASH_FIELD,
    replay_conflict,
    replay_response,
    verify_replay_closure_integrity,
    verify_replay_plan_integrity,
)
from app.services.claim_support_policy_impact_views import get_impact_row
from app.services.evidence import payload_sha256


def _recommended_source_task(
    session: Session,
    *,
    recommendation: dict,
    field_name: str,
    expected_task_type: str,
    change_impact_id: UUID,
    recommendation_index: int,
) -> tuple[UUID, AgentTask]:
    raw_value = recommendation.get(field_name)
    if raw_value in {None, ""}:
        raise replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_recommendation_invalid",
            "A replay recommendation is missing a required task identifier.",
            recommendation_index=recommendation_index,
            field_name=field_name,
        )
    try:
        task_id = UUID(str(raw_value))
    except ValueError as exc:
        raise replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_recommendation_invalid",
            "A replay recommendation contains an invalid task identifier.",
            recommendation_index=recommendation_index,
            field_name=field_name,
            field_value=str(raw_value),
        ) from exc
    task = session.get(AgentTask, task_id)
    if task is None:
        raise replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_source_task_not_found",
            "A replay recommendation points at a task that no longer exists.",
            source_task_id=str(task_id),
            expected_task_type=expected_task_type,
        )
    if task.task_type != expected_task_type:
        raise replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_source_task_type_mismatch",
            "A replay recommendation points at an unexpected task type.",
            source_task_id=str(task_id),
            expected_task_type=expected_task_type,
            actual_task_type=task.task_type,
        )
    return task_id, task


def _validated_replay_work_items(
    session: Session,
    *,
    row,
    recommendations: list[dict],
) -> list[dict]:
    draft_items: dict[str, dict] = {}
    verify_items: dict[tuple[str, str], dict] = {}
    ordered_items: list[dict] = []
    for index, recommendation in enumerate(recommendations):
        action = str(recommendation.get("action") or "")
        if action == "rerun_draft_technical_report":
            source_task_id, source_task = _recommended_source_task(
                session,
                recommendation=recommendation,
                field_name="target_task_id",
                expected_task_type="draft_technical_report",
                change_impact_id=row.id,
                recommendation_index=index,
            )
            if str(source_task_id) not in draft_items:
                item = {
                    "action": action,
                    "source_draft_task_id": source_task_id,
                    "source_draft_task": source_task,
                    "recommendation": recommendation,
                }
                draft_items[str(source_task_id)] = item
                ordered_items.append(item)
        elif action == "rerun_verify_technical_report":
            source_draft_task_id, source_draft_task = _recommended_source_task(
                session,
                recommendation=recommendation,
                field_name="target_task_id",
                expected_task_type="draft_technical_report",
                change_impact_id=row.id,
                recommendation_index=index,
            )
            prior_verification_task_id, source_verify_task = _recommended_source_task(
                session,
                recommendation=recommendation,
                field_name="prior_verification_task_id",
                expected_task_type="verify_technical_report",
                change_impact_id=row.id,
                recommendation_index=index,
            )
            source_target_task_id = (source_verify_task.input_json or {}).get("target_task_id")
            if str(source_target_task_id) != str(source_draft_task_id):
                raise replay_conflict(
                    row.id,
                    "claim_support_impact_replay_source_verification_mismatch",
                    "A replay verification recommendation does not target its source draft task.",
                    source_draft_task_id=str(source_draft_task_id),
                    prior_verification_task_id=str(source_verify_task.id),
                    verification_target_task_id=str(source_target_task_id),
                )
            if str(source_draft_task_id) not in draft_items:
                draft_item = {
                    "action": "rerun_draft_technical_report",
                    "source_draft_task_id": source_draft_task_id,
                    "source_draft_task": source_draft_task,
                    "recommendation": {
                        "reason": "Required before replaying technical-report verification.",
                        "priority": "high",
                    },
                }
                draft_items[str(source_draft_task_id)] = draft_item
                ordered_items.append(draft_item)
            verify_key = (str(source_draft_task_id), str(prior_verification_task_id))
            if verify_key not in verify_items:
                item = {
                    "action": action,
                    "source_draft_task_id": source_draft_task_id,
                    "prior_verification_task_id": prior_verification_task_id,
                    "source_verify_task": source_verify_task,
                    "recommendation": recommendation,
                }
                verify_items[verify_key] = item
                ordered_items.append(item)
        else:
            raise replay_conflict(
                row.id,
                "claim_support_impact_replay_action_unknown",
                "The impact row contains an unsupported replay recommendation action.",
                recommendation_index=index,
                action=action,
            )
    return ordered_items


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
        commit=False,
    )


def _created_task_spec(
    *,
    action: str,
    task_type: str,
    task_detail,
    source_task: AgentTask,
    source_task_id: UUID,
    recommendation: dict,
    prior_verification_task_id: UUID | None = None,
) -> dict:
    spec = {
        "action": action,
        "source_task_id": str(source_task_id),
        "replay_task_id": str(task_detail.task_id),
        "task_type": task_type,
        "status": task_detail.status,
        "dependency_task_ids": [str(value) for value in task_detail.dependency_task_ids],
        "reason": recommendation.get("reason"),
        "priority": recommendation.get("priority"),
        "source_task_input_sha256": payload_sha256(source_task.input_json or {}),
        "source_task_result_sha256": payload_sha256(source_task.result_json or {}),
        "replay_task_input_sha256": payload_sha256(task_detail.input),
    }
    if prior_verification_task_id is not None:
        spec["prior_verification_task_id"] = str(prior_verification_task_id)
    return spec


def queue_claim_support_policy_change_impact_replay_tasks(
    session: Session,
    change_impact_id: UUID,
    *,
    requested_by: str,
    parent_task_id: UUID | None = None,
):
    row = get_impact_row(session, change_impact_id, for_update=True)
    verify_replay_plan_integrity(row)
    verify_replay_closure_integrity(row)
    if row.replay_recommended_count <= 0:
        from app.services.claim_support_policy_impact_replay_closure import (
            refresh_claim_support_policy_change_impact_replay_status,
        )

        return refresh_claim_support_policy_change_impact_replay_status(session, change_impact_id)
    if row.replay_task_ids_json:
        from app.services.claim_support_policy_impact_replay_closure import (
            refresh_claim_support_policy_change_impact_replay_status,
        )

        return refresh_claim_support_policy_change_impact_replay_status(session, change_impact_id)
    recommendations = list((row.impact_payload_json or {}).get("replay_recommendations") or [])
    if not recommendations:
        raise replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_recommendations_missing",
            "The impact row requires replay but does not contain replay recommendations.",
        )

    parent_task_id = parent_task_id or row.activation_task_id
    created_task_specs: list[dict] = []
    work_items = _validated_replay_work_items(session, row=row, recommendations=recommendations)
    if not work_items:
        raise replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_no_valid_work",
            "The impact row did not contain any valid replay work after de-duplication.",
        )

    draft_replay_task_ids: dict[str, UUID] = {}
    for item in work_items:
        action = str(item["action"])
        recommendation = dict(item.get("recommendation") or {})
        if action == "rerun_draft_technical_report":
            source_task_id = item["source_draft_task_id"]
            source_task = item["source_draft_task"]
            task_detail = _queue_agent_task(
                session,
                source_task=source_task,
                task_type="draft_technical_report",
                task_input=dict(source_task.input_json or {}),
                parent_task_id=parent_task_id,
            )
            draft_replay_task_ids[str(source_task_id)] = task_detail.task_id
            created_task_specs.append(
                _created_task_spec(
                    action=action,
                    task_type="draft_technical_report",
                    task_detail=task_detail,
                    source_task=source_task,
                    source_task_id=source_task_id,
                    recommendation=recommendation,
                )
            )
        elif action == "rerun_verify_technical_report":
            source_draft_task_id = item["source_draft_task_id"]
            replay_draft_task_id = draft_replay_task_ids.get(str(source_draft_task_id))
            if replay_draft_task_id is None:
                raise replay_conflict(
                    change_impact_id,
                    "claim_support_impact_replay_plan_invalid",
                    "Replay verification work was planned before its draft replay task.",
                    source_draft_task_id=str(source_draft_task_id),
                )
            prior_verification_task_id = item["prior_verification_task_id"]
            source_task = item["source_verify_task"]
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
                _created_task_spec(
                    action=action,
                    task_type="verify_technical_report",
                    task_detail=task_detail,
                    source_task=source_task,
                    source_task_id=source_draft_task_id,
                    recommendation=recommendation,
                    prior_verification_task_id=prior_verification_task_id,
                )
            )

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
        REPLAY_PLAN_HASH_FIELD: payload_sha256(plan_basis),
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
    return replay_response(row, created_tasks=created_task_specs)
