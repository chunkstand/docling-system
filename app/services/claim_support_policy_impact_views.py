from __future__ import annotations

from datetime import timedelta
from importlib import import_module
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.coercion import compact_strings as _string_list
from app.core.time import utcnow
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactResponse,
    ClaimSupportPolicyChangeImpactSummaryResponse,
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


def get_claim_support_policy_change_impact(
    session: Session,
    change_impact_id: UUID,
) -> ClaimSupportPolicyChangeImpactResponse:
    return impact_response(get_impact_row(session, change_impact_id))


def claim_support_policy_change_impact_worklist(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    include_closed: bool = False,
    change_impact_ids: list[UUID] | None = None,
):
    return import_module(
        "app.services.claim_support_policy_impact_worklist"
    ).claim_support_policy_change_impact_worklist(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_closed=include_closed,
        change_impact_ids=change_impact_ids,
    )


def claim_support_policy_change_impact_alerts(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
):
    return import_module(
        "app.services.claim_support_policy_impact_alerts"
    ).claim_support_policy_change_impact_alerts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
    )


def record_claim_support_policy_change_impact_alert_escalations(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    requested_by: str = "docling-system",
    storage_service=None,
    commit: bool = True,
):
    return import_module(
        "app.services.claim_support_policy_impact_alerts"
    ).record_claim_support_policy_change_impact_alert_escalations(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        requested_by=requested_by,
        storage_service=storage_service,
        commit=commit,
    )
