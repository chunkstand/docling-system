from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.coercion import compact_strings as _string_list
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskStatus,
    AgentTaskVerification,
    ClaimSupportPolicyChangeImpact,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
)
from app.schemas.agent_tasks import (
    AgentTaskCreateRequest,
    ClaimSupportPolicyChangeImpactReplayResponse,
    ClaimSupportPolicyChangeImpactReplayTaskResponse,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_policy_impact_views import (
    REPLAY_OPEN_STATUSES,
    REPLAY_TERMINAL_FAILURE_STATUSES,
    REPLAY_TERMINAL_STATUSES,
    get_impact_row,
    impact_response,
    uuid_list,
)
from app.services.evidence import payload_sha256
from app.services.semantic_governance import (
    active_semantic_basis,
    record_semantic_governance_event,
)
from app.services.storage import StorageService

CLAIM_SUPPORT_IMPACT_REPLAY_WORKFLOW_VERSION = "claim_support_policy_change_impact_replay_v1"
CLAIM_SUPPORT_IMPACT_REPLAY_PLAN_SCHEMA = "claim_support_policy_change_impact_replay_plan"
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_SCHEMA = "claim_support_policy_change_impact_replay_closure"
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_RECEIPT_SCHEMA = (
    "claim_support_policy_impact_replay_closure_receipt"
)
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_ARTIFACT_KIND = "claim_support_policy_impact_replay_closure"
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_FILENAME = "claim_support_policy_impact_replay_closure.json"
REPLAY_ACTIVE_STATUSES = {
    AgentTaskStatus.PROCESSING.value,
    AgentTaskStatus.RETRY_WAIT.value,
}
REPLAY_PLAN_HASH_FIELD = "replay_task_plan_sha256"
REPLAY_CLOSURE_HASH_FIELD = "replay_closure_sha256"

def _replay_conflict(
    change_impact_id: UUID,
    error_code: str,
    error_message: str,
    **details,
):
    return api_error(
        status.HTTP_409_CONFLICT,
        error_code,
        error_message,
        change_impact_id=str(change_impact_id),
        **details,
    )

def _verify_hash_field(
    *,
    payload: dict,
    hash_field: str,
    error_code: str,
    error_message: str,
    change_impact_id: UUID,
) -> None:
    recorded_sha = str((payload or {}).get(hash_field) or "")
    if not recorded_sha:
        return
    basis = dict(payload or {})
    basis.pop(hash_field, None)
    expected_sha = payload_sha256(basis)
    if recorded_sha != expected_sha:
        raise _replay_conflict(
            change_impact_id,
            error_code,
            error_message,
            recorded_sha256=recorded_sha,
            expected_sha256=expected_sha,
        )

def _verify_replay_plan_integrity(row: ClaimSupportPolicyChangeImpact) -> None:
    plan = dict(row.replay_task_plan_json or {})
    if not plan:
        return
    _verify_hash_field(
        payload=plan,
        hash_field=REPLAY_PLAN_HASH_FIELD,
        error_code="claim_support_impact_replay_plan_hash_mismatch",
        error_message="Claim support impact replay task plan hash does not match payload.",
        change_impact_id=row.id,
    )

def _verify_replay_closure_integrity(row: ClaimSupportPolicyChangeImpact) -> None:
    closure = dict(row.replay_closure_json or {})
    if not closure:
        return
    _verify_hash_field(
        payload=closure,
        hash_field=REPLAY_CLOSURE_HASH_FIELD,
        error_code="claim_support_impact_replay_closure_hash_mismatch",
        error_message="Claim support impact replay closure hash does not match payload.",
        change_impact_id=row.id,
    )
    recorded_row_sha = row.replay_closure_sha256
    recorded_payload_sha = closure.get(REPLAY_CLOSURE_HASH_FIELD)
    if recorded_row_sha and recorded_payload_sha and recorded_row_sha != recorded_payload_sha:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_closure_row_hash_mismatch",
            "Claim support impact replay closure row hash does not match payload.",
            row_sha256=recorded_row_sha,
            payload_sha256=recorded_payload_sha,
        )

def _verify_terminal_replay_closure_integrity(
    row: ClaimSupportPolicyChangeImpact,
) -> None:
    if row.replay_status not in REPLAY_TERMINAL_STATUSES:
        return
    closure = dict(row.replay_closure_json or {})
    if not closure:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_closure_missing",
            "Terminal claim support impact replay rows must include a closure receipt.",
            replay_status=row.replay_status,
        )
    _verify_replay_closure_integrity(row)
    recorded_payload_sha = closure.get(REPLAY_CLOSURE_HASH_FIELD)
    if not recorded_payload_sha:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_closure_hash_missing",
            "Terminal claim support impact replay closures must include a payload hash.",
            replay_status=row.replay_status,
        )
    if not row.replay_closure_sha256:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_row_hash_missing",
            "Terminal claim support impact replay rows must record the closure hash.",
            replay_status=row.replay_status,
            replay_closure_sha256=recorded_payload_sha,
        )
    if closure.get("status") != row.replay_status:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_status_mismatch",
            "Terminal claim support impact replay closure status does not match the row.",
            row_replay_status=row.replay_status,
            closure_status=closure.get("status"),
        )
    if closure.get("closed") is not True:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_not_closed",
            "Terminal claim support impact replay closures must be marked closed.",
            replay_status=row.replay_status,
        )
    if row.replay_closed_at is None:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_closed_at_missing",
            "Terminal claim support impact replay rows must record replay_closed_at.",
            replay_status=row.replay_status,
        )

def _replay_response(
    row: ClaimSupportPolicyChangeImpact,
    *,
    created_tasks: list[dict] | None = None,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    plan = dict(row.replay_task_plan_json or {})
    task_specs = created_tasks if created_tasks is not None else list(plan.get("tasks") or [])
    return ClaimSupportPolicyChangeImpactReplayResponse(
        change_impact=impact_response(row),
        replay_status=row.replay_status,
        replay_task_ids=uuid_list(row.replay_task_ids_json),
        created_tasks=[
            ClaimSupportPolicyChangeImpactReplayTaskResponse(
                action=str(task_spec.get("action") or ""),
                source_task_id=_uuid_or_none(task_spec.get("source_task_id")),
                prior_verification_task_id=_uuid_or_none(
                    task_spec.get("prior_verification_task_id")
                ),
                replay_task_id=UUID(str(task_spec["replay_task_id"])),
                task_type=str(task_spec.get("task_type") or ""),
                status=str(task_spec.get("status") or ""),
                dependency_task_ids=uuid_list(task_spec.get("dependency_task_ids") or []),
                reason=task_spec.get("reason"),
            )
            for task_spec in task_specs
        ],
        replay_task_plan=plan,
        replay_closure=dict(row.replay_closure_json or {}),
        replay_closure_sha256=row.replay_closure_sha256,
    )

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
        raise _replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_recommendation_invalid",
            "A replay recommendation is missing a required task identifier.",
            recommendation_index=recommendation_index,
            field_name=field_name,
        )
    try:
        task_id = UUID(str(raw_value))
    except ValueError as exc:
        raise _replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_recommendation_invalid",
            "A replay recommendation contains an invalid task identifier.",
            recommendation_index=recommendation_index,
            field_name=field_name,
            field_value=str(raw_value),
        ) from exc
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_source_task_not_found",
            "A replay recommendation points at a task that no longer exists.",
            source_task_id=str(task_id),
            expected_task_type=expected_task_type,
        )
    if task.task_type != expected_task_type:
        raise _replay_conflict(
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
    row: ClaimSupportPolicyChangeImpact,
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
                raise _replay_conflict(
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
            raise _replay_conflict(
                row.id,
                "claim_support_impact_replay_action_unknown",
                "The impact row contains an unsupported replay recommendation action.",
                recommendation_index=index,
                action=action,
            )
    return ordered_items

def _record_replay_closure_governance_event(
    session: Session,
    row: ClaimSupportPolicyChangeImpact,
    *,
    storage_service: StorageService | None = None,
    created_by: str = "docling-system",
) -> SemanticGovernanceEvent | None:
    if row.replay_status not in {"closed", "no_action_required"}:
        return None
    if not row.replay_closure_json:
        return None
    _verify_terminal_replay_closure_integrity(row)
    closure = dict(row.replay_closure_json or {})
    closure_sha256 = (
        row.replay_closure_sha256
        or closure.get(REPLAY_CLOSURE_HASH_FIELD)
        or payload_sha256(closure)
    )
    if not closure_sha256:
        return None
    deduplication_key = f"claim_support_policy_impact_replay_closed:{row.id}:{closure_sha256}"
    existing = session.scalar(
        select(SemanticGovernanceEvent)
        .where(
            SemanticGovernanceEvent.deduplication_key
            == deduplication_key
        )
        .limit(1)
    )
    if existing is not None:
        return existing
    semantic_basis = active_semantic_basis(session)
    tasks = list(closure.get("tasks") or [])
    anchor_task_id = next(
        (
            UUID(str(task_spec["replay_task_id"]))
            for task_spec in tasks
            if task_spec.get("task_type") == "verify_technical_report"
            and task_spec.get("verification_outcome") == "passed"
            and task_spec.get("replay_task_id")
        ),
        None,
    )
    if anchor_task_id is None:
        anchor_task_id = next(
            (
                UUID(str(task_spec["replay_task_id"]))
                for task_spec in tasks
                if task_spec.get("replay_task_id")
            ),
            None,
        )
    if anchor_task_id is None:
        replay_task_ids = uuid_list(row.replay_task_ids_json)
        anchor_task_id = replay_task_ids[-1] if replay_task_ids else row.activation_task_id
    plan = dict(row.replay_task_plan_json or {})
    plan_sha256 = plan.get(REPLAY_PLAN_HASH_FIELD) or payload_sha256(plan)
    closed_at = row.replay_closed_at.isoformat() if row.replay_closed_at else None
    replay_task_ids = _string_list(row.replay_task_ids_json)
    basis = {
        "schema_name": CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "change_impact_id": str(row.id),
        "source": {"source_table": "claim_support_policy_change_impacts", "source_id": str(row.id)},
        "policy_name": row.policy_name,
        "policy_version": row.policy_version,
        "impact_scope": row.impact_scope,
        "impact_payload_sha256": row.impact_payload_sha256,
        "replay_status": row.replay_status,
        "replay_closed_at": closed_at,
        "anchor_task_id": str(anchor_task_id) if anchor_task_id is not None else None,
        "activation_task_id": str(row.activation_task_id) if row.activation_task_id else None,
        "activated_policy_id": str(row.activated_policy_id) if row.activated_policy_id else None,
        "previous_policy_id": str(row.previous_policy_id) if row.previous_policy_id else None,
        "replay_task_ids": replay_task_ids,
        "replay_task_plan_sha256": plan_sha256,
        "replay_closure_sha256": closure_sha256,
        "replay_closure": closure,
    }
    receipt_payload = {**basis, "receipt_sha256": payload_sha256(basis)}
    artifact = (
        create_agent_task_artifact(
            session,
            task_id=anchor_task_id,
            artifact_kind=CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_ARTIFACT_KIND,
            payload=receipt_payload,
            storage_service=storage_service,
            filename=f"{receipt_payload['change_impact_id']}_{CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_FILENAME}",
        )
        if anchor_task_id is not None
        else None
    )
    receipt_sha256 = receipt_payload["receipt_sha256"]
    artifact_id = artifact.id if artifact is not None else None
    artifact_kind = artifact.artifact_kind if artifact is not None else None
    artifact_path = artifact.storage_path if artifact is not None else None
    return record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED.value,
        governance_scope=row.impact_scope,
        subject_table="claim_support_policy_change_impacts",
        subject_id=row.id,
        task_id=anchor_task_id,
        ontology_snapshot_id=_uuid_or_none(semantic_basis.get("active_ontology_snapshot_id")),
        semantic_graph_snapshot_id=_uuid_or_none(
            semantic_basis.get("active_semantic_graph_snapshot_id")
        ),
        agent_task_artifact_id=artifact_id,
        receipt_sha256=receipt_sha256,
        event_payload={
            "claim_support_policy_impact_replay_closure": {
                "change_impact_id": str(row.id),
                "policy_name": row.policy_name,
                "policy_version": row.policy_version,
                "impact_payload_sha256": row.impact_payload_sha256,
                "replay_status": row.replay_status,
                "replay_task_ids": replay_task_ids,
                "replay_task_plan_sha256": plan_sha256,
                "replay_closure_sha256": closure_sha256,
                "closure_artifact_id": str(artifact_id) if artifact_id is not None else None,
                "closure_artifact_kind": artifact_kind,
                "closure_artifact_path": artifact_path,
                "receipt_sha256": receipt_sha256,
                "closed_at": closed_at,
            },
            "semantic_basis": semantic_basis,
        },
        deduplication_key=deduplication_key,
        created_by=created_by,
    )

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
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    row = get_impact_row(session, change_impact_id, for_update=True)
    _verify_replay_plan_integrity(row)
    _verify_replay_closure_integrity(row)
    if row.replay_recommended_count <= 0:
        return refresh_claim_support_policy_change_impact_replay_status(session, change_impact_id)
    if row.replay_task_ids_json:
        return refresh_claim_support_policy_change_impact_replay_status(session, change_impact_id)
    recommendations = list((row.impact_payload_json or {}).get("replay_recommendations") or [])
    if not recommendations:
        raise _replay_conflict(
            change_impact_id,
            "claim_support_impact_replay_recommendations_missing",
            "The impact row requires replay but does not contain replay recommendations.",
        )

    parent_task_id = parent_task_id or row.activation_task_id
    created_task_specs: list[dict] = []
    work_items = _validated_replay_work_items(session, row=row, recommendations=recommendations)
    if not work_items:
        raise _replay_conflict(
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
                raise _replay_conflict(
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
    return _replay_response(row, created_tasks=created_task_specs)

def refresh_claim_support_policy_change_impact_replay_status(
    session: Session,
    change_impact_id: UUID,
    *,
    storage_service: StorageService | None = None,
    commit: bool = True,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    row = get_impact_row(session, change_impact_id, for_update=True)
    _verify_replay_plan_integrity(row)
    _verify_replay_closure_integrity(row)
    now = utcnow()
    if row.replay_status in {"closed", "no_action_required"} and row.replay_closure_json:
        _verify_terminal_replay_closure_integrity(row)
        _record_replay_closure_governance_event(session, row, storage_service=storage_service)
        session.commit() if commit else session.flush()
        return _replay_response(row)
    if row.replay_status == "closed":
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_closure_missing",
            "Closed claim support impact replay rows must include a closure receipt.",
            replay_status=row.replay_status,
        )
    if row.replay_status == "no_action_required" and row.replay_recommended_count > 0:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_no_action_inconsistent",
            "No-action claim support impact replay rows cannot require replay tasks.",
            replay_recommended_count=row.replay_recommended_count,
        )

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
            REPLAY_CLOSURE_HASH_FIELD: payload_sha256(closure_basis),
        }
        row.replay_closure_sha256 = row.replay_closure_json[REPLAY_CLOSURE_HASH_FIELD]
        _record_replay_closure_governance_event(session, row, storage_service=storage_service)
        session.add(row)
        session.commit() if commit else session.flush()
        return _replay_response(row)

    replay_task_ids = uuid_list(row.replay_task_ids_json)
    if not replay_task_ids:
        row.replay_status = "pending"
        row.replay_status_updated_at = now
        row.replay_closed_at = None
        row.replay_closure_json = {}
        row.replay_closure_sha256 = None
        session.add(row)
        session.commit() if commit else session.flush()
        return _replay_response(row)

    task_rows = (
        session.execute(select(AgentTask).where(AgentTask.id.in_(replay_task_ids)))
        .scalars()
        .all()
    )
    tasks_by_id = {task.id: task for task in task_rows}
    plan_tasks = list((row.replay_task_plan_json or {}).get("tasks") or [])
    if not plan_tasks:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_plan_missing",
            "Replay task IDs exist but the replay task plan is missing.",
            replay_task_ids=[str(task_id) for task_id in replay_task_ids],
        )
    plan_task_ids = {
        str(task_spec.get("replay_task_id"))
        for task_spec in plan_tasks
        if task_spec.get("replay_task_id")
    }
    replay_task_id_text = {str(task_id) for task_id in replay_task_ids}
    if plan_task_ids != replay_task_id_text:
        raise _replay_conflict(
            row.id,
            "claim_support_impact_replay_plan_task_mismatch",
            "Replay task IDs do not match the replay task plan.",
            replay_task_ids=sorted(replay_task_id_text),
            plan_task_ids=sorted(plan_task_ids),
        )
    verification_task_ids = [
        UUID(str(task_spec["replay_task_id"]))
        for task_spec in plan_tasks
        if task_spec.get("task_type") == "verify_technical_report"
        and task_spec.get("replay_task_id")
    ]
    verification_rows = (
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
        if verification_task_ids
        else []
    )
    latest_verifications: dict[UUID, AgentTaskVerification] = {}
    for verification in verification_rows:
        if verification.verification_task_id is not None:
            latest_verifications.setdefault(verification.verification_task_id, verification)
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
            REPLAY_CLOSURE_HASH_FIELD: payload_sha256(closure_basis),
        }
        row.replay_closure_sha256 = row.replay_closure_json[REPLAY_CLOSURE_HASH_FIELD]
        _record_replay_closure_governance_event(session, row, storage_service=storage_service)
    else:
        row.replay_closure_json = closure_basis
        row.replay_closure_sha256 = None
    session.add(row)
    session.commit() if commit else session.flush()
    return _replay_response(row)

def refresh_claim_support_policy_change_impacts_for_replay_task(
    session: Session,
    task_id: UUID,
    *,
    storage_service: StorageService | None = None,
    commit: bool = True,
) -> list[ClaimSupportPolicyChangeImpactReplayResponse]:
    candidate_rows = session.execute(
        select(ClaimSupportPolicyChangeImpact)
        .where(ClaimSupportPolicyChangeImpact.replay_status.in_(REPLAY_OPEN_STATUSES))
        .order_by(ClaimSupportPolicyChangeImpact.created_at.asc())
    ).scalars().all()
    rows = [
        row
        for row in candidate_rows
        if str(task_id) in _string_list(row.replay_task_ids_json)
    ]
    responses = [
        refresh_claim_support_policy_change_impact_replay_status(
            session,
            row.id,
            storage_service=storage_service,
            commit=False,
        )
        for row in rows
    ]
    session.commit() if commit else session.flush()
    return responses
