from __future__ import annotations

from importlib import import_module
from uuid import UUID

from fastapi import status

from app.api.errors import api_error
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.db.models import ClaimSupportPolicyChangeImpact
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactReplayResponse,
    ClaimSupportPolicyChangeImpactReplayTaskResponse,
)
from app.services.claim_support_policy_impact_views import impact_response, uuid_list
from app.services.evidence import payload_sha256

CLAIM_SUPPORT_IMPACT_REPLAY_WORKFLOW_VERSION = "claim_support_policy_change_impact_replay_v1"
CLAIM_SUPPORT_IMPACT_REPLAY_PLAN_SCHEMA = "claim_support_policy_change_impact_replay_plan"
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_SCHEMA = "claim_support_policy_change_impact_replay_closure"
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_RECEIPT_SCHEMA = (
    "claim_support_policy_impact_replay_closure_receipt"
)
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_ARTIFACT_KIND = "claim_support_policy_impact_replay_closure"
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_FILENAME = "claim_support_policy_impact_replay_closure.json"
REPLAY_ACTIVE_STATUSES = {"processing", "retry_wait"}
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
    closure = dict(row.replay_closure_json or {})
    if row.replay_status not in {"closed", "no_action_required"}:
        return
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


replay_conflict = _replay_conflict
verify_replay_plan_integrity = _verify_replay_plan_integrity
verify_replay_closure_integrity = _verify_replay_closure_integrity
verify_terminal_replay_closure_integrity = _verify_terminal_replay_closure_integrity
replay_response = _replay_response


def queue_claim_support_policy_change_impact_replay_tasks(
    session,
    change_impact_id: UUID,
    *,
    requested_by: str,
    parent_task_id: UUID | None = None,
):
    return import_module(
        "app.services.claim_support_policy_impact_replay_queue"
    ).queue_claim_support_policy_change_impact_replay_tasks(
        session,
        change_impact_id,
        requested_by=requested_by,
        parent_task_id=parent_task_id,
    )


def refresh_claim_support_policy_change_impact_replay_status(
    session,
    change_impact_id: UUID,
    *,
    storage_service=None,
    commit: bool = True,
):
    return import_module(
        "app.services.claim_support_policy_impact_replay_closure"
    ).refresh_claim_support_policy_change_impact_replay_status(
        session,
        change_impact_id,
        storage_service=storage_service,
        commit=commit,
    )


def refresh_claim_support_policy_change_impacts_for_replay_task(
    session,
    task_id: UUID,
    *,
    storage_service=None,
    commit: bool = True,
):
    return import_module(
        "app.services.claim_support_policy_impact_replay_closure"
    ).refresh_claim_support_policy_change_impacts_for_replay_task(
        session,
        task_id,
        storage_service=storage_service,
        commit=commit,
    )
