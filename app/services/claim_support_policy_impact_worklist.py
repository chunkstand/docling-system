from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.semantic_memory import SemanticGovernanceEvent, SemanticGovernanceEventKind
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactClosureEventRef,
    ClaimSupportPolicyChangeImpactWorklistItemResponse,
    ClaimSupportPolicyChangeImpactWorklistResponse,
    ClaimSupportPolicyChangeImpactWorklistTaskRef,
)
from app.services.claim_support_policy_impact_views import (
    REPLAY_OPEN_STATUSES,
    REPLAY_TERMINAL_FAILURE_STATUSES,
    REPLAY_TERMINAL_STATUSES,
    impact_response,
    summarize_claim_support_policy_change_impacts,
    uuid_list,
)


def _hours_since(now, value) -> float:
    return 0.0 if value is None else round(
        max(0.0, (now - value).total_seconds() / 3600.0),
        2,
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


def _worklist_next_action(
    row: ClaimSupportPolicyChangeImpact,
    *,
    is_stale: bool,
) -> str:
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
