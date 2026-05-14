from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.coercion import compact_strings as _string_list
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    ClaimSupportPolicyChangeImpact,
    EvidenceManifest,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
)
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactAlertEventRef,
    ClaimSupportPolicyChangeImpactAlertItemResponse,
    ClaimSupportPolicyChangeImpactAlertResponse,
    ClaimSupportPolicyChangeImpactClosureEventRef,
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

CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_RECEIPT_SCHEMA = (
    "claim_support_policy_impact_replay_escalation_receipt"
)
CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_ARTIFACT_KIND = (
    "claim_support_policy_impact_replay_escalation"
)
CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED.value
)
REPLAY_TERMINAL_FAILURE_STATUSES = {"failed", "rejected"}
REPLAY_OPEN_STATUSES = {"pending", "queued", "in_progress", "blocked"}
REPLAY_TERMINAL_STATUSES = {"closed", "no_action_required"}

def uuid_list(values) -> list[UUID]:
    return [UUID(str(value)) for value in values or [] if value not in {None, ""}]

def get_impact_row(
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
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "claim_support_policy_change_impact_not_found",
            "Claim support policy change impact row was not found.",
            change_impact_id=str(change_impact_id),
        )
    return row

def impact_response(
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
        replay_task_ids=uuid_list(row.replay_task_ids_json),
        replay_task_plan=dict(row.replay_task_plan_json or {}),
        replay_closure=dict(row.replay_closure_json or {}),
        replay_closure_sha256=row.replay_closure_sha256,
        replay_status_updated_at=row.replay_status_updated_at,
        replay_closed_at=row.replay_closed_at,
        created_at=row.created_at,
    )

def _hours_since(now, value) -> float:
    return 0.0 if value is None else round(
        max(0.0, (now - value).total_seconds() / 3600.0), 2
    )

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
    actions = {
        "pending": "Queue managed replay tasks.",
        "queued": "Run or monitor queued replay tasks; refresh status after task completion.",
        "in_progress": "Monitor replay tasks and refresh status after completion.",
        "blocked": "Inspect failed, rejected, missing, or unverified replay tasks before closure.",
        "closed": "Review the closure receipt and related governance event.",
        "no_action_required": "Review the no-action closure receipt.",
    }
    if row.replay_status in actions:
        return actions[row.replay_status]
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
    return [impact_response(row) for row in session.execute(statement).scalars().all()]

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
    change_impact_ids: list[UUID] | None = None,
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
    if change_impact_ids is not None:
        if not change_impact_ids:
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
        statement = statement.where(ClaimSupportPolicyChangeImpact.id.in_(change_impact_ids))
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

    replay_task_ids = {task_id for row in rows for task_id in uuid_list(row.replay_task_ids_json)}
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
        row_replay_task_ids = uuid_list(row.replay_task_ids_json)
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
        audit_bundle_task_ids = uuid_list(row.impacted_verification_task_ids_json)
        items.append(
            ClaimSupportPolicyChangeImpactWorklistItemResponse(
                change_impact=impact_response(row),
                severity=_worklist_severity(row, is_stale=is_stale),
                status_label=str(row.replay_status).replace("_", " "),
                is_open=is_open,
                is_stale=is_stale,
                age_hours=_hours_since(generated_at, row.created_at),
                status_age_hours=_hours_since(generated_at, status_updated_at),
                next_action=_worklist_next_action(row, is_stale=is_stale),
                recommended_action=_worklist_recommended_action(row, is_stale=is_stale),
                reasons=_worklist_reasons(row, is_stale=is_stale),
                affected_draft_task_ids=uuid_list(row.impacted_task_ids_json),
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

def _alert_row_ids(
    session: Session,
    *,
    policy_name: str | None,
    stale_after_hours: int,
) -> list[UUID]:
    stale_after_hours = max(1, stale_after_hours)
    stale_cutoff = utcnow() - timedelta(hours=stale_after_hours)
    status_updated_at = func.coalesce(
        ClaimSupportPolicyChangeImpact.replay_status_updated_at,
        ClaimSupportPolicyChangeImpact.created_at,
    )
    statement = (
        select(ClaimSupportPolicyChangeImpact.id)
        .where(
            or_(
                ClaimSupportPolicyChangeImpact.replay_status == "blocked",
                (
                    ClaimSupportPolicyChangeImpact.replay_status.in_(
                        REPLAY_OPEN_STATUSES - {"blocked"}
                    )
                    & (status_updated_at <= stale_cutoff)
                ),
            )
        )
        .order_by(
            ClaimSupportPolicyChangeImpact.created_at.desc(),
            ClaimSupportPolicyChangeImpact.id.desc(),
        )
    )
    if policy_name is not None:
        statement = statement.where(ClaimSupportPolicyChangeImpact.policy_name == policy_name)
    return list(session.scalars(statement))

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
    alert_row_ids = _alert_row_ids(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
    )
    worklist = claim_support_policy_change_impact_worklist(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=max(1, len(alert_row_ids)),
        include_closed=False,
        change_impact_ids=alert_row_ids,
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

def _record_alert_escalation_event(
    session: Session,
    row: ClaimSupportPolicyChangeImpact,
    *,
    item: ClaimSupportPolicyChangeImpactWorklistItemResponse,
    alert_kind: str,
    requested_by: str,
    stale_after_hours: int,
    generated_at,
    storage_service: StorageService | None,
) -> tuple[SemanticGovernanceEvent, bool]:
    status_updated_at = row.replay_status_updated_at or row.created_at
    status_updated_at_text = status_updated_at.isoformat() if status_updated_at else "missing"
    deduplication_key = (
        "claim_support_policy_impact_replay_escalated:"
        f"{row.id}:{alert_kind}:{row.replay_status}:"
        f"{status_updated_at_text}:stale_after_hours={stale_after_hours}"
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
        "alert_kind": alert_kind,
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
                f"{row.id}_{alert_kind}_{receipt_sha256[:12]}.json"
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

def _fresh_alert_worklist_item(
    session: Session,
    *,
    change_impact_id: UUID,
    stale_after_hours: int,
) -> tuple[ClaimSupportPolicyChangeImpactWorklistItemResponse, str] | None:
    worklist = claim_support_policy_change_impact_worklist(
        session,
        stale_after_hours=stale_after_hours,
        limit=1,
        include_closed=False,
        change_impact_ids=[change_impact_id],
    )
    if not worklist.items:
        return None
    item = worklist.items[0]
    alert_kind = _alert_kind_for_worklist_item(item)
    if alert_kind is None:
        return None
    return item, alert_kind

def _refresh_existing_evidence_manifests_for_alert_item(
    session: Session,
    item: ClaimSupportPolicyChangeImpactWorklistItemResponse,
) -> None:
    verification_task_ids = list(item.audit_bundle_task_ids)
    if not verification_task_ids:
        return
    existing_manifest_task_ids = list(
        session.scalars(
            select(EvidenceManifest.verification_task_id)
            .where(EvidenceManifest.verification_task_id.in_(verification_task_ids))
            .order_by(EvidenceManifest.created_at.asc())
        )
    )
    if not existing_manifest_task_ids:
        return
    from app.services.evidence import refresh_technical_report_evidence_manifest

    for task_id in dict.fromkeys(existing_manifest_task_ids):
        refresh_technical_report_evidence_manifest(session, task_id=task_id)

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
        row = get_impact_row(session, item.change_impact.change_impact_id, for_update=True)
        fresh_item = _fresh_alert_worklist_item(
            session,
            change_impact_id=row.id,
            stale_after_hours=stale_after_hours,
        )
        if fresh_item is None:
            continue
        current_item, alert_kind = fresh_item
        _, created = _record_alert_escalation_event(
            session,
            row,
            item=current_item,
            alert_kind=alert_kind,
            requested_by=requested_by,
            stale_after_hours=stale_after_hours,
            generated_at=feed.generated_at,
            storage_service=storage_service,
        )
        if created:
            created_count += 1
        _refresh_existing_evidence_manifests_for_alert_item(session, current_item)
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
    return impact_response(get_impact_row(session, change_impact_id))
