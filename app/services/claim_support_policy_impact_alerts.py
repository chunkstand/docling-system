from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.audit_and_evidence import EvidenceManifest
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.semantic_memory import SemanticGovernanceEvent, SemanticGovernanceEventKind
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactAlertEventRef,
    ClaimSupportPolicyChangeImpactAlertItemResponse,
    ClaimSupportPolicyChangeImpactAlertResponse,
    ClaimSupportPolicyChangeImpactWorklistItemResponse,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_policy_impact_views import (
    REPLAY_OPEN_STATUSES,
    get_impact_row,
)
from app.services.claim_support_policy_impact_worklist import (
    claim_support_policy_change_impact_worklist,
)
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
