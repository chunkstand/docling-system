from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskStatus,
    AgentTaskVerification,
    ClaimSupportPolicyChangeImpact,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
)
from app.schemas.agent_tasks import (
    AgentTaskCreateRequest,
    ClaimSupportPolicyChangeImpactAlertEventRef,
    ClaimSupportPolicyChangeImpactAlertItemResponse,
    ClaimSupportPolicyChangeImpactAlertResponse,
    ClaimSupportPolicyChangeImpactClosureEventRef,
    ClaimSupportPolicyChangeImpactReplayResponse,
    ClaimSupportPolicyChangeImpactReplayTaskResponse,
    ClaimSupportPolicyChangeImpactResponse,
    ClaimSupportPolicyChangeImpactSummaryResponse,
    ClaimSupportPolicyChangeImpactWorklistItemResponse,
    ClaimSupportPolicyChangeImpactWorklistResponse,
    ClaimSupportPolicyChangeImpactWorklistTaskRef,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
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
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_ARTIFACT_KIND = (
    "claim_support_policy_impact_replay_closure"
)
CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_FILENAME = (
    "claim_support_policy_impact_replay_closure.json"
)
CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_RECEIPT_SCHEMA = (
    "claim_support_policy_impact_replay_escalation_receipt"
)
CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_ARTIFACT_KIND = (
    "claim_support_policy_impact_replay_escalation"
)
CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED.value
)
REPLAY_TERMINAL_FAILURE_STATUSES = {
    AgentTaskStatus.FAILED.value,
    AgentTaskStatus.REJECTED.value,
}
REPLAY_ACTIVE_STATUSES = {
    AgentTaskStatus.PROCESSING.value,
    AgentTaskStatus.RETRY_WAIT.value,
}
REPLAY_OPEN_STATUSES = {
    "pending",
    "queued",
    "in_progress",
    "blocked",
}
REPLAY_TERMINAL_STATUSES = {
    "closed",
    "no_action_required",
}
ALERT_INTERNAL_LIMIT = 1_000_000
REPLAY_PLAN_HASH_FIELD = "replay_task_plan_sha256"
REPLAY_CLOSURE_HASH_FIELD = "replay_closure_sha256"


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
    *,
    for_update: bool = False,
) -> ClaimSupportPolicyChangeImpact:
    statement = select(ClaimSupportPolicyChangeImpact).where(
        ClaimSupportPolicyChangeImpact.id == change_impact_id
    )
    if for_update:
        statement = statement.with_for_update()
    row = session.execute(statement).scalar_one_or_none()
    if row is None:
        raise _impact_not_found(change_impact_id)
    return row


def _hash_payload_excluding(payload: dict, hash_field: str) -> str:
    basis = dict(payload or {})
    basis.pop(hash_field, None)
    return payload_sha256(basis)


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
    expected_sha = _hash_payload_excluding(payload, hash_field)
    if recorded_sha != expected_sha:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code,
            error_message,
            change_impact_id=str(change_impact_id),
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
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_closure_row_hash_mismatch",
            "Claim support impact replay closure row hash does not match payload.",
            change_impact_id=str(row.id),
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
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_terminal_closure_missing",
            "Terminal claim support impact replay rows must include a closure receipt.",
            change_impact_id=str(row.id),
            replay_status=row.replay_status,
        )
    _verify_replay_closure_integrity(row)
    recorded_payload_sha = closure.get(REPLAY_CLOSURE_HASH_FIELD)
    if not recorded_payload_sha:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_terminal_closure_hash_missing",
            "Terminal claim support impact replay closures must include a payload hash.",
            change_impact_id=str(row.id),
            replay_status=row.replay_status,
        )
    if not row.replay_closure_sha256:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_terminal_row_hash_missing",
            "Terminal claim support impact replay rows must record the closure hash.",
            change_impact_id=str(row.id),
            replay_status=row.replay_status,
            replay_closure_sha256=recorded_payload_sha,
        )
    if closure.get("status") != row.replay_status:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_terminal_status_mismatch",
            "Terminal claim support impact replay closure status does not match the row.",
            change_impact_id=str(row.id),
            row_replay_status=row.replay_status,
            closure_status=closure.get("status"),
        )
    if closure.get("closed") is not True:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_terminal_not_closed",
            "Terminal claim support impact replay closures must be marked closed.",
            change_impact_id=str(row.id),
            replay_status=row.replay_status,
        )
    if row.replay_closed_at is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_terminal_closed_at_missing",
            "Terminal claim support impact replay rows must record replay_closed_at.",
            change_impact_id=str(row.id),
            replay_status=row.replay_status,
        )


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


def _hours_since(now, value) -> float:
    if value is None:
        return 0.0
    return round(max(0.0, (now - value).total_seconds() / 3600.0), 2)


def _worklist_severity(
    row: ClaimSupportPolicyChangeImpact,
    *,
    is_stale: bool,
) -> str:
    if row.replay_status == "blocked":
        return "critical"
    if is_stale:
        return "warning"
    if row.replay_status == "in_progress":
        return "active"
    if row.replay_status in {"closed", "no_action_required"}:
        return "cleared"
    return "attention"


def _worklist_next_action(row: ClaimSupportPolicyChangeImpact, *, is_stale: bool) -> str:
    if row.replay_status == "pending":
        return "Queue managed replay tasks."
    if row.replay_status == "queued":
        return (
            "Run or monitor queued replay tasks; refresh status after task completion."
        )
    if row.replay_status == "in_progress":
        return "Monitor replay tasks and refresh status after completion."
    if row.replay_status == "blocked":
        return "Inspect failed, rejected, missing, or unverified replay tasks before closure."
    if row.replay_status == "closed":
        return "Review the closure receipt and related governance event."
    if row.replay_status == "no_action_required":
        return "Review the no-action closure receipt."
    if is_stale:
        return "Refresh replay status or inspect the replay task queue."
    return "Inspect the replay impact row."


def _worklist_recommended_action(
    row: ClaimSupportPolicyChangeImpact,
    *,
    is_stale: bool,
) -> str:
    if row.replay_status == "pending":
        return "queue_replay"
    if row.replay_status in {"queued", "in_progress"}:
        return "refresh_status" if is_stale else "monitor_replay"
    if row.replay_status == "blocked":
        return "inspect_blockers"
    if row.replay_status in {"closed", "no_action_required"}:
        return "review_closure_receipt"
    return "inspect"


def _worklist_reasons(
    row: ClaimSupportPolicyChangeImpact,
    *,
    is_stale: bool,
) -> list[str]:
    reasons: list[str] = []
    if row.replay_status in REPLAY_OPEN_STATUSES:
        reasons.append("Replay impact is still open.")
    if row.replay_status == "blocked":
        reasons.append("Replay closure is blocked by failed, missing, or unverified tasks.")
    if is_stale:
        reasons.append("Replay status has not changed within the stale threshold.")
    if row.replay_status in REPLAY_TERMINAL_STATUSES:
        reasons.append("Replay impact has a terminal closure receipt.")
    if row.replay_status == "pending":
        reasons.append("Managed replay tasks have not been queued yet.")
    return reasons


def _worklist_task_ref(
    task_id: UUID,
    *,
    task: AgentTask | None,
    required_task_ids: set[str],
) -> ClaimSupportPolicyChangeImpactWorklistTaskRef:
    task_type = task.task_type if task is not None else "missing"
    status_value = task.status if task is not None else "missing"
    return ClaimSupportPolicyChangeImpactWorklistTaskRef(
        task_id=task_id,
        task_type=task_type,
        status=status_value,
        completed_at=task.completed_at if task is not None else None,
        is_terminal_failure=status_value in REPLAY_TERMINAL_FAILURE_STATUSES
        or status_value == "missing",
        is_required_for_closure=str(task_id) in required_task_ids,
    )


def _worklist_closure_event_ref(
    event: SemanticGovernanceEvent,
    *,
    artifact: AgentTaskArtifact | None,
) -> ClaimSupportPolicyChangeImpactClosureEventRef:
    return ClaimSupportPolicyChangeImpactClosureEventRef(
        event_id=event.id,
        event_hash=event.event_hash,
        receipt_sha256=event.receipt_sha256,
        artifact_id=event.agent_task_artifact_id,
        artifact_kind=artifact.artifact_kind if artifact is not None else None,
        artifact_path=artifact.storage_path if artifact is not None else None,
        created_at=event.created_at,
    )


def _alert_event_ref(
    event: SemanticGovernanceEvent,
    *,
    artifact: AgentTaskArtifact | None,
) -> ClaimSupportPolicyChangeImpactAlertEventRef:
    event_payload = dict(event.event_payload_json or {})
    escalation_payload = dict(
        event_payload.get("claim_support_policy_impact_replay_escalation") or {}
    )
    return ClaimSupportPolicyChangeImpactAlertEventRef(
        event_id=event.id,
        event_hash=event.event_hash,
        receipt_sha256=event.receipt_sha256,
        artifact_id=event.agent_task_artifact_id,
        artifact_kind=artifact.artifact_kind if artifact is not None else None,
        artifact_path=artifact.storage_path if artifact is not None else None,
        alert_kind=escalation_payload.get("alert_kind"),
        created_at=event.created_at,
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


def summarize_claim_support_policy_change_impacts(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
) -> ClaimSupportPolicyChangeImpactSummaryResponse:
    stale_after_hours = max(1, stale_after_hours)
    stale_cutoff = utcnow() - timedelta(hours=stale_after_hours)
    statement = select(ClaimSupportPolicyChangeImpact)
    if policy_name is not None:
        statement = statement.where(ClaimSupportPolicyChangeImpact.policy_name == policy_name)
    rows = session.execute(statement).scalars().all()
    status_counts: dict[str, int] = {}
    open_count = 0
    stale_open_count = 0
    for row in rows:
        status_value = str(row.replay_status)
        status_counts[status_value] = status_counts.get(status_value, 0) + 1
        if status_value not in REPLAY_OPEN_STATUSES:
            continue
        open_count += 1
        status_updated_at = row.replay_status_updated_at or row.created_at
        if status_updated_at <= stale_cutoff:
            stale_open_count += 1
    return ClaimSupportPolicyChangeImpactSummaryResponse(
        total_count=len(rows),
        replay_status_counts=status_counts,
        open_count=open_count,
        stale_open_count=stale_open_count,
        stale_after_hours=stale_after_hours,
        stale_cutoff=stale_cutoff,
    )


def claim_support_policy_change_impact_worklist(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    include_closed: bool = False,
) -> ClaimSupportPolicyChangeImpactWorklistResponse:
    stale_after_hours = max(1, stale_after_hours)
    limit = max(1, limit)
    generated_at = utcnow()
    stale_cutoff = generated_at - timedelta(hours=stale_after_hours)
    summary = summarize_claim_support_policy_change_impacts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
    )
    statement = select(ClaimSupportPolicyChangeImpact).order_by(
        ClaimSupportPolicyChangeImpact.created_at.desc(),
        ClaimSupportPolicyChangeImpact.id.desc(),
    )
    if policy_name is not None:
        statement = statement.where(ClaimSupportPolicyChangeImpact.policy_name == policy_name)
    if not include_closed:
        statement = statement.where(
            ClaimSupportPolicyChangeImpact.replay_status.in_(REPLAY_OPEN_STATUSES)
        )
    rows = list(session.execute(statement).scalars().all())
    if not rows:
        return ClaimSupportPolicyChangeImpactWorklistResponse(
            summary=summary,
            generated_at=generated_at,
            stale_after_hours=stale_after_hours,
            limit=limit,
            matching_count=0,
            item_count=0,
            has_more=False,
            items=[],
        )

    replay_task_ids = {
        task_id
        for row in rows
        for task_id in _uuid_list(row.replay_task_ids_json)
    }
    task_rows = (
        list(
            session.execute(select(AgentTask).where(AgentTask.id.in_(list(replay_task_ids))))
            .scalars()
            .all()
        )
        if replay_task_ids
        else []
    )
    tasks_by_id = {row.id: row for row in task_rows}
    row_ids = [row.id for row in rows]
    closure_events = list(
        session.execute(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.subject_table == "claim_support_policy_change_impacts",
                SemanticGovernanceEvent.subject_id.in_(row_ids),
                SemanticGovernanceEvent.event_kind
                == SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED.value,
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
        .scalars()
        .all()
    )
    artifact_ids = {
        event.agent_task_artifact_id
        for event in closure_events
        if event.agent_task_artifact_id is not None
    }
    artifact_rows = (
        list(
            session.execute(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.id.in_(list(artifact_ids))
                )
            )
            .scalars()
            .all()
        )
        if artifact_ids
        else []
    )
    artifacts_by_id = {row.id: row for row in artifact_rows}
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    for event in closure_events:
        if event.subject_id is not None:
            events_by_row.setdefault(event.subject_id, []).append(event)

    items: list[ClaimSupportPolicyChangeImpactWorklistItemResponse] = []
    for row in rows:
        status_updated_at = row.replay_status_updated_at or row.created_at
        is_open = row.replay_status in REPLAY_OPEN_STATUSES
        is_stale = is_open and status_updated_at <= stale_cutoff
        replay_plan_tasks = list((row.replay_task_plan_json or {}).get("tasks") or [])
        required_task_ids = {
            str(task_spec["replay_task_id"])
            for task_spec in replay_plan_tasks
            if task_spec.get("task_type") == "verify_technical_report"
            and task_spec.get("replay_task_id")
        }
        row_replay_task_ids = _uuid_list(row.replay_task_ids_json)
        row_events = events_by_row.get(row.id, [])
        closure_event_refs = [
            _worklist_closure_event_ref(
                event,
                artifact=artifacts_by_id.get(event.agent_task_artifact_id),
            )
            for event in row_events
        ]
        latest_closure_event = row_events[-1] if row_events else None
        closure_artifact_id = (
            latest_closure_event.agent_task_artifact_id if latest_closure_event else None
        )
        audit_bundle_task_ids = _uuid_list(row.impacted_verification_task_ids_json)
        items.append(
            ClaimSupportPolicyChangeImpactWorklistItemResponse(
                change_impact=_impact_response(row),
                severity=_worklist_severity(row, is_stale=is_stale),
                status_label=str(row.replay_status).replace("_", " "),
                is_open=is_open,
                is_stale=is_stale,
                age_hours=_hours_since(generated_at, row.created_at),
                status_age_hours=_hours_since(generated_at, status_updated_at),
                next_action=_worklist_next_action(row, is_stale=is_stale),
                recommended_action=_worklist_recommended_action(row, is_stale=is_stale),
                reasons=_worklist_reasons(row, is_stale=is_stale),
                affected_draft_task_ids=_uuid_list(row.impacted_task_ids_json),
                affected_verification_task_ids=audit_bundle_task_ids,
                audit_bundle_task_ids=audit_bundle_task_ids,
                replay_tasks=[
                    _worklist_task_ref(
                        task_id,
                        task=tasks_by_id.get(task_id),
                        required_task_ids=required_task_ids,
                    )
                    for task_id in row_replay_task_ids
                ],
                closure_events=closure_event_refs,
                closure_receipt_artifact_id=closure_artifact_id,
                closure_receipt_sha256=(
                    latest_closure_event.receipt_sha256 if latest_closure_event else None
                ),
                operator_links={
                    "detail": (
                        "/agent-tasks/claim-support-policy-change-impacts/"
                        f"{row.id}"
                    ),
                    "queue_replay": (
                        "/agent-tasks/claim-support-policy-change-impacts/"
                        f"{row.id}/replay-tasks"
                    ),
                    "refresh_status": (
                        "/agent-tasks/claim-support-policy-change-impacts/"
                        f"{row.id}/replay-status"
                    ),
                    "affected_audit_bundles": [
                        f"/agent-tasks/{task_id}/audit-bundle"
                        for task_id in audit_bundle_task_ids
                    ],
                    "closure_artifact": (
                        f"/agent-tasks/{latest_closure_event.task_id}/artifacts/"
                        f"{latest_closure_event.agent_task_artifact_id}"
                    )
                    if latest_closure_event is not None
                    and latest_closure_event.task_id is not None
                    and latest_closure_event.agent_task_artifact_id is not None
                    else None,
                },
            )
        )

    severity_order = {
        "critical": 0,
        "warning": 1,
        "active": 2,
        "attention": 3,
        "cleared": 4,
    }
    items.sort(
        key=lambda item: (
            severity_order.get(item.severity, 99),
            -item.status_age_hours,
            str(item.change_impact.change_impact_id),
        )
    )
    matching_count = len(items)
    limited_items = items[:limit]
    return ClaimSupportPolicyChangeImpactWorklistResponse(
        summary=summary,
        generated_at=generated_at,
        stale_after_hours=stale_after_hours,
        limit=limit,
        matching_count=matching_count,
        item_count=len(limited_items),
        has_more=matching_count > len(limited_items),
        items=limited_items,
    )


def _alert_kind_for_worklist_item(
    item: ClaimSupportPolicyChangeImpactWorklistItemResponse,
) -> str | None:
    if item.change_impact.replay_status == "blocked":
        return "blocked"
    if item.is_stale:
        return "stale"
    return None


def _alert_events_by_row(
    session: Session,
    row_ids: list[UUID],
) -> dict[UUID, list[SemanticGovernanceEvent]]:
    if not row_ids:
        return {}
    events = list(
        session.execute(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.subject_table
                == "claim_support_policy_change_impacts",
                SemanticGovernanceEvent.subject_id.in_(row_ids),
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND,
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
        .scalars()
        .all()
    )
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    for event in events:
        if event.subject_id is not None:
            events_by_row.setdefault(event.subject_id, []).append(event)
    return events_by_row


def _artifact_rows_by_id(
    session: Session,
    events: list[SemanticGovernanceEvent],
) -> dict[UUID, AgentTaskArtifact]:
    artifact_ids = {
        event.agent_task_artifact_id
        for event in events
        if event.agent_task_artifact_id is not None
    }
    if not artifact_ids:
        return {}
    artifact_rows = list(
        session.execute(
            select(AgentTaskArtifact).where(AgentTaskArtifact.id.in_(artifact_ids))
        )
        .scalars()
        .all()
    )
    return {row.id: row for row in artifact_rows}


def _alert_item_response(
    item: ClaimSupportPolicyChangeImpactWorklistItemResponse,
    *,
    alert_kind: str,
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]],
    artifacts_by_id: dict[UUID, AgentTaskArtifact],
) -> ClaimSupportPolicyChangeImpactAlertItemResponse:
    row_events = events_by_row.get(item.change_impact.change_impact_id, [])
    escalation_events = [
        _alert_event_ref(
            event,
            artifact=artifacts_by_id.get(event.agent_task_artifact_id),
        )
        for event in row_events
    ]
    latest_event = escalation_events[-1] if escalation_events else None
    operator_links = {
        **dict(item.operator_links or {}),
        "alerts": "/agent-tasks/claim-support-policy-change-impacts/alerts",
        "record_escalations": (
            "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations"
        ),
    }
    return ClaimSupportPolicyChangeImpactAlertItemResponse(
        change_impact=item.change_impact,
        alert_kind=alert_kind,
        severity=item.severity,
        replay_status=item.change_impact.replay_status,
        is_stale=item.is_stale,
        age_hours=item.age_hours,
        status_age_hours=item.status_age_hours,
        next_action=item.next_action,
        recommended_action=item.recommended_action,
        reasons=list(item.reasons),
        affected_draft_task_ids=list(item.affected_draft_task_ids),
        affected_verification_task_ids=list(item.affected_verification_task_ids),
        audit_bundle_task_ids=list(item.audit_bundle_task_ids),
        replay_tasks=list(item.replay_tasks),
        escalation_events=escalation_events,
        latest_escalation_event_id=latest_event.event_id if latest_event else None,
        latest_escalation_receipt_sha256=(
            latest_event.receipt_sha256 if latest_event else None
        ),
        operator_links=operator_links,
    )


def claim_support_policy_change_impact_alerts(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
) -> ClaimSupportPolicyChangeImpactAlertResponse:
    limit = max(1, limit)
    worklist = claim_support_policy_change_impact_worklist(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=ALERT_INTERNAL_LIMIT,
        include_closed=False,
    )
    alert_pairs = [
        (item, alert_kind)
        for item in worklist.items
        if (alert_kind := _alert_kind_for_worklist_item(item)) is not None
    ]
    matching_count = len(alert_pairs)
    limited_pairs = alert_pairs[:limit]
    row_ids = [item.change_impact.change_impact_id for item, _ in limited_pairs]
    events_by_row = _alert_events_by_row(session, row_ids)
    artifacts_by_id = _artifact_rows_by_id(
        session,
        [event for events in events_by_row.values() for event in events],
    )
    return ClaimSupportPolicyChangeImpactAlertResponse(
        summary=worklist.summary,
        generated_at=worklist.generated_at,
        stale_after_hours=worklist.stale_after_hours,
        limit=limit,
        matching_count=matching_count,
        item_count=len(limited_pairs),
        has_more=matching_count > len(limited_pairs),
        recorded_escalation_count=0,
        items=[
            _alert_item_response(
                item,
                alert_kind=alert_kind,
                events_by_row=events_by_row,
                artifacts_by_id=artifacts_by_id,
            )
            for item, alert_kind in limited_pairs
        ],
    )


def _alert_escalation_deduplication_key(
    row: ClaimSupportPolicyChangeImpact,
    *,
    alert_kind: str,
    stale_after_hours: int,
) -> str:
    status_updated_at = row.replay_status_updated_at or row.created_at
    status_updated_at_text = status_updated_at.isoformat() if status_updated_at else "missing"
    return (
        "claim_support_policy_impact_replay_escalated:"
        f"{row.id}:{alert_kind}:{row.replay_status}:"
        f"{status_updated_at_text}:stale_after_hours={stale_after_hours}"
    )


def _record_alert_escalation_event(
    session: Session,
    row: ClaimSupportPolicyChangeImpact,
    *,
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
    requested_by: str,
    stale_after_hours: int,
    generated_at,
    storage_service: StorageService | None,
) -> tuple[SemanticGovernanceEvent, bool]:
    deduplication_key = _alert_escalation_deduplication_key(
        row,
        alert_kind=item.alert_kind,
        stale_after_hours=stale_after_hours,
    )
    existing = session.scalar(
        select(SemanticGovernanceEvent)
        .where(SemanticGovernanceEvent.deduplication_key == deduplication_key)
        .limit(1)
    )
    if existing is not None:
        return existing, False

    semantic_basis = active_semantic_basis(session)
    receipt_basis: dict[str, Any] = {
        "schema_name": CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "change_impact_id": str(row.id),
        "alert_kind": item.alert_kind,
        "severity": item.severity,
        "policy_name": row.policy_name,
        "policy_version": row.policy_version,
        "impact_scope": row.impact_scope,
        "impact_payload_sha256": row.impact_payload_sha256,
        "replay_status": row.replay_status,
        "replay_recommended_count": row.replay_recommended_count,
        "replay_task_ids": [str(task_id) for task_id in item.change_impact.replay_task_ids],
        "affected_draft_task_ids": [
            str(task_id) for task_id in item.affected_draft_task_ids
        ],
        "affected_verification_task_ids": [
            str(task_id) for task_id in item.affected_verification_task_ids
        ],
        "audit_bundle_task_ids": [str(task_id) for task_id in item.audit_bundle_task_ids],
        "replay_tasks": [task.model_dump(mode="json") for task in item.replay_tasks],
        "is_stale": item.is_stale,
        "stale_after_hours": stale_after_hours,
        "age_hours": item.age_hours,
        "status_age_hours": item.status_age_hours,
        "reasons": list(item.reasons),
        "recommended_action": item.recommended_action,
        "next_action": item.next_action,
        "operator_links": dict(item.operator_links),
        "semantic_basis": semantic_basis,
        "generated_at": generated_at.isoformat(),
        "recorded_at": utcnow().isoformat(),
        "recorded_by": requested_by,
        "deduplication_key": deduplication_key,
    }
    receipt_sha256 = str(payload_sha256(receipt_basis))
    receipt_payload = {
        **receipt_basis,
        "receipt_sha256": receipt_sha256,
    }
    artifact: AgentTaskArtifact | None = None
    if row.activation_task_id is not None:
        artifact = create_agent_task_artifact(
            session,
            task_id=row.activation_task_id,
            artifact_kind=CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_ARTIFACT_KIND,
            payload=receipt_payload,
            storage_service=storage_service,
            filename=(
                "claim_support_policy_impact_replay_escalation_"
                f"{row.id}_{item.alert_kind}_{receipt_sha256[:12]}.json"
            ),
        )

    event = record_semantic_governance_event(
        session,
        event_kind=CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND,
        governance_scope=row.impact_scope,
        subject_table="claim_support_policy_change_impacts",
        subject_id=row.id,
        task_id=row.activation_task_id,
        ontology_snapshot_id=_uuid_or_none(semantic_basis.get("active_ontology_snapshot_id")),
        semantic_graph_snapshot_id=_uuid_or_none(
            semantic_basis.get("active_semantic_graph_snapshot_id")
        ),
        agent_task_artifact_id=artifact.id if artifact is not None else None,
        receipt_sha256=receipt_sha256,
        event_payload={
            "claim_support_policy_impact_replay_escalation": receipt_payload,
            "semantic_basis": semantic_basis,
        },
        deduplication_key=deduplication_key,
        created_by=requested_by,
    )
    return event, True


def record_claim_support_policy_change_impact_alert_escalations(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    requested_by: str = "docling-system",
    storage_service: StorageService | None = None,
    commit: bool = True,
) -> ClaimSupportPolicyChangeImpactAlertResponse:
    feed = claim_support_policy_change_impact_alerts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
    )
    created_count = 0
    for item in feed.items:
        row = _get_impact_row(session, item.change_impact.change_impact_id, for_update=True)
        _, created = _record_alert_escalation_event(
            session,
            row,
            item=item,
            requested_by=requested_by,
            stale_after_hours=stale_after_hours,
            generated_at=feed.generated_at,
            storage_service=storage_service,
        )
        if created:
            created_count += 1
    if commit:
        session.commit()
    else:
        session.flush()
    recorded_feed = claim_support_policy_change_impact_alerts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
    )
    return recorded_feed.model_copy(update={"recorded_escalation_count": created_count})


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


def _recommendation_uuid(
    recommendation: dict,
    field_name: str,
    *,
    change_impact_id: UUID,
    recommendation_index: int,
) -> UUID:
    raw_value = recommendation.get(field_name)
    if raw_value in {None, ""}:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_recommendation_invalid",
            "A replay recommendation is missing a required task identifier.",
            change_impact_id=str(change_impact_id),
            recommendation_index=recommendation_index,
            field_name=field_name,
        )
    try:
        return UUID(str(raw_value))
    except ValueError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_recommendation_invalid",
            "A replay recommendation contains an invalid task identifier.",
            change_impact_id=str(change_impact_id),
            recommendation_index=recommendation_index,
            field_name=field_name,
            field_value=str(raw_value),
        ) from exc


def _source_task_sha256(task: AgentTask, field_name: str) -> str:
    return payload_sha256(getattr(task, field_name) or {})


def _validate_verify_recommendation_source(
    source_verify_task: AgentTask,
    *,
    source_draft_task_id: UUID,
    change_impact_id: UUID,
) -> None:
    source_target_task_id = (source_verify_task.input_json or {}).get("target_task_id")
    if str(source_target_task_id) != str(source_draft_task_id):
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_source_verification_mismatch",
            "A replay verification recommendation does not target its source draft task.",
            change_impact_id=str(change_impact_id),
            source_draft_task_id=str(source_draft_task_id),
            prior_verification_task_id=str(source_verify_task.id),
            verification_target_task_id=str(source_target_task_id),
        )


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
            source_task_id = _recommendation_uuid(
                recommendation,
                "target_task_id",
                change_impact_id=row.id,
                recommendation_index=index,
            )
            source_task = _require_source_task(
                session,
                task_id=source_task_id,
                expected_task_type="draft_technical_report",
                change_impact_id=row.id,
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
            source_draft_task_id = _recommendation_uuid(
                recommendation,
                "target_task_id",
                change_impact_id=row.id,
                recommendation_index=index,
            )
            prior_verification_task_id = _recommendation_uuid(
                recommendation,
                "prior_verification_task_id",
                change_impact_id=row.id,
                recommendation_index=index,
            )
            source_draft_task = _require_source_task(
                session,
                task_id=source_draft_task_id,
                expected_task_type="draft_technical_report",
                change_impact_id=row.id,
            )
            source_verify_task = _require_source_task(
                session,
                task_id=prior_verification_task_id,
                expected_task_type="verify_technical_report",
                change_impact_id=row.id,
            )
            _validate_verify_recommendation_source(
                source_verify_task,
                source_draft_task_id=source_draft_task_id,
                change_impact_id=row.id,
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
            raise api_error(
                status.HTTP_409_CONFLICT,
                "claim_support_impact_replay_action_unknown",
                "The impact row contains an unsupported replay recommendation action.",
                change_impact_id=str(row.id),
                recommendation_index=index,
                action=action,
            )
    return ordered_items


def _replay_closure_hash(row: ClaimSupportPolicyChangeImpact) -> str | None:
    closure = dict(row.replay_closure_json or {})
    return (
        row.replay_closure_sha256
        or closure.get(REPLAY_CLOSURE_HASH_FIELD)
        or payload_sha256(closure)
    )


def _replay_closure_event_deduplication_key(
    row: ClaimSupportPolicyChangeImpact,
    closure_sha256: str,
) -> str:
    return f"claim_support_policy_impact_replay_closed:{row.id}:{closure_sha256}"


def _existing_replay_closure_event(
    session: Session,
    *,
    row: ClaimSupportPolicyChangeImpact,
    closure_sha256: str,
) -> SemanticGovernanceEvent | None:
    return session.scalar(
        select(SemanticGovernanceEvent)
        .where(
            SemanticGovernanceEvent.deduplication_key
            == _replay_closure_event_deduplication_key(row, closure_sha256)
        )
        .limit(1)
    )


def _replay_closure_anchor_task_id(
    row: ClaimSupportPolicyChangeImpact,
) -> UUID | None:
    closure = dict(row.replay_closure_json or {})
    tasks = list(closure.get("tasks") or [])
    for task_spec in tasks:
        if (
            task_spec.get("task_type") == "verify_technical_report"
            and task_spec.get("verification_outcome") == "passed"
            and task_spec.get("replay_task_id")
        ):
            return UUID(str(task_spec["replay_task_id"]))
    for task_spec in tasks:
        if task_spec.get("replay_task_id"):
            return UUID(str(task_spec["replay_task_id"]))
    replay_task_ids = _uuid_list(row.replay_task_ids_json)
    if replay_task_ids:
        return replay_task_ids[-1]
    return row.activation_task_id


def _replay_closure_receipt_payload(
    row: ClaimSupportPolicyChangeImpact,
    *,
    anchor_task_id: UUID | None,
    closure_sha256: str,
) -> dict:
    closure = dict(row.replay_closure_json or {})
    plan = dict(row.replay_task_plan_json or {})
    plan_sha256 = plan.get(REPLAY_PLAN_HASH_FIELD) or payload_sha256(plan)
    basis = {
        "schema_name": CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "change_impact_id": str(row.id),
        "source": {
            "source_table": "claim_support_policy_change_impacts",
            "source_id": str(row.id),
        },
        "policy_name": row.policy_name,
        "policy_version": row.policy_version,
        "impact_scope": row.impact_scope,
        "impact_payload_sha256": row.impact_payload_sha256,
        "replay_status": row.replay_status,
        "replay_closed_at": row.replay_closed_at.isoformat()
        if row.replay_closed_at
        else None,
        "anchor_task_id": str(anchor_task_id) if anchor_task_id is not None else None,
        "activation_task_id": str(row.activation_task_id) if row.activation_task_id else None,
        "activated_policy_id": str(row.activated_policy_id) if row.activated_policy_id else None,
        "previous_policy_id": str(row.previous_policy_id) if row.previous_policy_id else None,
        "replay_task_ids": _string_list(row.replay_task_ids_json),
        "replay_task_plan_sha256": plan_sha256,
        "replay_closure_sha256": closure_sha256,
        "replay_closure": closure,
    }
    return {
        **basis,
        "receipt_sha256": payload_sha256(basis),
    }


def _create_replay_closure_artifact(
    session: Session,
    *,
    anchor_task_id: UUID | None,
    receipt_payload: dict,
    storage_service: StorageService | None,
) -> AgentTaskArtifact | None:
    if anchor_task_id is None:
        return None
    return create_agent_task_artifact(
        session,
        task_id=anchor_task_id,
        artifact_kind=CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_ARTIFACT_KIND,
        payload=receipt_payload,
        storage_service=storage_service,
        filename=(
            f"{receipt_payload['change_impact_id']}_"
            f"{CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_FILENAME}"
        ),
    )


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
    closure_sha256 = _replay_closure_hash(row)
    if not closure_sha256:
        return None
    existing = _existing_replay_closure_event(
        session,
        row=row,
        closure_sha256=closure_sha256,
    )
    if existing is not None:
        return existing

    semantic_basis = active_semantic_basis(session)
    anchor_task_id = _replay_closure_anchor_task_id(row)
    receipt_payload = _replay_closure_receipt_payload(
        row,
        anchor_task_id=anchor_task_id,
        closure_sha256=closure_sha256,
    )
    artifact = _create_replay_closure_artifact(
        session,
        anchor_task_id=anchor_task_id,
        receipt_payload=receipt_payload,
        storage_service=storage_service,
    )
    ontology_snapshot_id = _uuid_or_none(semantic_basis.get("active_ontology_snapshot_id"))
    semantic_graph_snapshot_id = _uuid_or_none(
        semantic_basis.get("active_semantic_graph_snapshot_id")
    )
    receipt_sha256 = receipt_payload["receipt_sha256"]
    return record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED.value,
        governance_scope=row.impact_scope,
        subject_table="claim_support_policy_change_impacts",
        subject_id=row.id,
        task_id=anchor_task_id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=semantic_graph_snapshot_id,
        agent_task_artifact_id=artifact.id if artifact is not None else None,
        receipt_sha256=receipt_sha256,
        event_payload={
            "claim_support_policy_impact_replay_closure": {
                "change_impact_id": str(row.id),
                "policy_name": row.policy_name,
                "policy_version": row.policy_version,
                "impact_payload_sha256": row.impact_payload_sha256,
                "replay_status": row.replay_status,
                "replay_task_ids": _string_list(row.replay_task_ids_json),
                "replay_task_plan_sha256": (
                    (row.replay_task_plan_json or {}).get(REPLAY_PLAN_HASH_FIELD)
                    or payload_sha256(row.replay_task_plan_json or {})
                ),
                "replay_closure_sha256": closure_sha256,
                "closure_artifact_id": str(artifact.id) if artifact is not None else None,
                "closure_artifact_kind": (
                    artifact.artifact_kind if artifact is not None else None
                ),
                "closure_artifact_path": artifact.storage_path
                if artifact is not None
                else None,
                "receipt_sha256": receipt_sha256,
                "closed_at": row.replay_closed_at.isoformat()
                if row.replay_closed_at
                else None,
            },
            "semantic_basis": semantic_basis,
        },
        deduplication_key=_replay_closure_event_deduplication_key(row, closure_sha256),
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


def queue_claim_support_policy_change_impact_replay_tasks(
    session: Session,
    change_impact_id: UUID,
    *,
    requested_by: str,
    parent_task_id: UUID | None = None,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    row = _get_impact_row(session, change_impact_id, for_update=True)
    _verify_replay_plan_integrity(row)
    _verify_replay_closure_integrity(row)
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
    created_task_specs: list[dict] = []
    work_items = _validated_replay_work_items(
        session,
        row=row,
        recommendations=recommendations,
    )
    if not work_items:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_no_valid_work",
            "The impact row did not contain any valid replay work after de-duplication.",
            change_impact_id=str(change_impact_id),
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
                    "source_task_input_sha256": _source_task_sha256(source_task, "input_json"),
                    "source_task_result_sha256": _source_task_sha256(source_task, "result_json"),
                    "replay_task_input_sha256": payload_sha256(task_detail.input),
                }
            )
        elif action == "rerun_verify_technical_report":
            source_draft_task_id = item["source_draft_task_id"]
            replay_draft_task_id = draft_replay_task_ids.get(str(source_draft_task_id))
            if replay_draft_task_id is None:
                raise api_error(
                    status.HTTP_409_CONFLICT,
                    "claim_support_impact_replay_plan_invalid",
                    "Replay verification work was planned before its draft replay task.",
                    change_impact_id=str(change_impact_id),
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
                    "source_task_input_sha256": _source_task_sha256(source_task, "input_json"),
                    "source_task_result_sha256": _source_task_sha256(source_task, "result_json"),
                    "replay_task_input_sha256": payload_sha256(task_detail.input),
                }
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
    row = _get_impact_row(session, change_impact_id, for_update=True)
    _verify_replay_plan_integrity(row)
    _verify_replay_closure_integrity(row)
    now = utcnow()
    if row.replay_status in {"closed", "no_action_required"} and row.replay_closure_json:
        _verify_terminal_replay_closure_integrity(row)
        _record_replay_closure_governance_event(
            session,
            row,
            storage_service=storage_service,
        )
        if commit:
            session.commit()
        else:
            session.flush()
        return _replay_response(row)
    if row.replay_status == "closed":
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_terminal_closure_missing",
            "Closed claim support impact replay rows must include a closure receipt.",
            change_impact_id=str(row.id),
            replay_status=row.replay_status,
        )
    if row.replay_status == "no_action_required" and row.replay_recommended_count > 0:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_no_action_inconsistent",
            "No-action claim support impact replay rows cannot require replay tasks.",
            change_impact_id=str(row.id),
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
        _record_replay_closure_governance_event(
            session,
            row,
            storage_service=storage_service,
        )
        session.add(row)
        if commit:
            session.commit()
        else:
            session.flush()
        return _replay_response(row)

    replay_task_ids = _uuid_list(row.replay_task_ids_json)
    if not replay_task_ids:
        row.replay_status = "pending"
        row.replay_status_updated_at = now
        row.replay_closed_at = None
        row.replay_closure_json = {}
        row.replay_closure_sha256 = None
        session.add(row)
        if commit:
            session.commit()
        else:
            session.flush()
        return _replay_response(row)

    task_rows = (
        session.execute(select(AgentTask).where(AgentTask.id.in_(replay_task_ids)))
        .scalars()
        .all()
    )
    tasks_by_id = {task.id: task for task in task_rows}
    plan_tasks = list((row.replay_task_plan_json or {}).get("tasks") or [])
    if not plan_tasks:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_plan_missing",
            "Replay task IDs exist but the replay task plan is missing.",
            change_impact_id=str(row.id),
            replay_task_ids=[str(task_id) for task_id in replay_task_ids],
        )
    plan_task_ids = {
        str(task_spec.get("replay_task_id"))
        for task_spec in plan_tasks
        if task_spec.get("replay_task_id")
    }
    replay_task_id_text = {str(task_id) for task_id in replay_task_ids}
    if plan_task_ids != replay_task_id_text:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "claim_support_impact_replay_plan_task_mismatch",
            "Replay task IDs do not match the replay task plan.",
            change_impact_id=str(row.id),
            replay_task_ids=sorted(replay_task_id_text),
            plan_task_ids=sorted(plan_task_ids),
        )
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
            REPLAY_CLOSURE_HASH_FIELD: payload_sha256(closure_basis),
        }
        row.replay_closure_sha256 = row.replay_closure_json[REPLAY_CLOSURE_HASH_FIELD]
        _record_replay_closure_governance_event(
            session,
            row,
            storage_service=storage_service,
        )
    else:
        row.replay_closure_json = closure_basis
        row.replay_closure_sha256 = None
    session.add(row)
    if commit:
        session.commit()
    else:
        session.flush()
    return _replay_response(row)


def refresh_claim_support_policy_change_impacts_for_replay_task(
    session: Session,
    task_id: UUID,
    *,
    storage_service: StorageService | None = None,
    commit: bool = True,
) -> list[ClaimSupportPolicyChangeImpactReplayResponse]:
    candidate_rows = (
        session.execute(
            select(ClaimSupportPolicyChangeImpact)
            .where(
                ClaimSupportPolicyChangeImpact.replay_status.in_(REPLAY_OPEN_STATUSES),
            )
            .order_by(ClaimSupportPolicyChangeImpact.created_at.asc())
        )
        .scalars()
        .all()
    )
    rows = [
        row
        for row in candidate_rows
        if str(task_id) in set(_string_list(row.replay_task_ids_json))
    ]
    responses: list[ClaimSupportPolicyChangeImpactReplayResponse] = []
    for row in rows:
        responses.append(
            refresh_claim_support_policy_change_impact_replay_status(
                session,
                row.id,
                storage_service=storage_service,
                commit=False,
            )
        )
    if commit:
        session.commit()
    else:
        session.flush()
    return responses
