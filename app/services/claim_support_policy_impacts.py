from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskStatus,
    AgentTaskVerification,
    ClaimEvidenceDerivation,
    ClaimSupportFixtureSet,
    ClaimSupportPolicyChangeImpact,
    EvidenceManifest,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
)
from app.schemas.agent_tasks import (
    AgentTaskCreateRequest,
    ClaimSupportPolicyChangeImpactAlertEventRef,
    ClaimSupportPolicyChangeImpactAlertItemResponse,
    ClaimSupportPolicyChangeImpactAlertResponse,
    ClaimSupportPolicyChangeImpactClosureEventRef,
    ClaimSupportPolicyChangeImpactFixtureCandidateListResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse,
    ClaimSupportPolicyChangeImpactFixturePromotionEventRef,
    ClaimSupportPolicyChangeImpactFixturePromotionResponse,
    ClaimSupportPolicyChangeImpactReplayResponse,
    ClaimSupportPolicyChangeImpactReplayTaskResponse,
    ClaimSupportPolicyChangeImpactResponse,
    ClaimSupportPolicyChangeImpactSummaryResponse,
    ClaimSupportPolicyChangeImpactWorklistItemResponse,
    ClaimSupportPolicyChangeImpactWorklistResponse,
    ClaimSupportPolicyChangeImpactWorklistTaskRef,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_evaluations import (
    default_claim_support_evaluation_fixtures,
    ensure_claim_support_fixture_set,
)
from app.services.claim_support_replay_alert_fixture_corpus import (
    active_replay_alert_fixture_corpus_rows,
    active_replay_alert_fixture_corpus_snapshot_summary,
    ensure_active_replay_alert_fixture_corpus_snapshot,
    replay_alert_fixture_corpus_snapshot_summary,
)
from app.services.claim_support_replay_alert_waivers import (
    apply_replay_alert_fixture_coverage_promotion_to_waiver_ledgers,
    mark_replay_alert_fixture_coverage_waiver_ledger_closed,
    replay_alert_escalation_set_sha256,
    stale_unconverted_escalation_event_ids_from_waiver,
    waiver_artifact_ids_with_coverage_ledgers,
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
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_RECEIPT_SCHEMA = (
    "claim_support_policy_impact_fixture_promotion_receipt"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED.value
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_RECEIPT_SCHEMA = (
    "claim_support_replay_alert_fixture_coverage_waiver_closure_receipt"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver_closure"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED.value
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
    item: ClaimSupportPolicyChangeImpactWorklistItemResponse,
    alert_kind: str,
    requested_by: str,
    stale_after_hours: int,
    generated_at,
    storage_service: StorageService | None,
) -> tuple[SemanticGovernanceEvent, bool]:
    deduplication_key = _alert_escalation_deduplication_key(
        row,
        alert_kind=alert_kind,
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


def _refresh_existing_evidence_manifests_for_fixture_candidates(
    session: Session,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
) -> None:
    verification_task_ids = sorted(
        {
            task_id
            for candidate in candidates
            for task_id in candidate.affected_verification_task_ids
        },
        key=str,
    )
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
        row = _get_impact_row(session, item.change_impact.change_impact_id, for_update=True)
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


def _fixture_promotion_payload(event: SemanticGovernanceEvent) -> dict[str, Any]:
    return dict(
        (event.event_payload_json or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        )
        or {}
    )


def _fixture_promotion_event_ref(
    event: SemanticGovernanceEvent,
    *,
    artifact: AgentTaskArtifact | None,
) -> ClaimSupportPolicyChangeImpactFixturePromotionEventRef:
    promotion_payload = _fixture_promotion_payload(event)
    return ClaimSupportPolicyChangeImpactFixturePromotionEventRef(
        event_id=event.id,
        event_hash=event.event_hash,
        receipt_sha256=event.receipt_sha256,
        fixture_set_id=_uuid_or_none(promotion_payload.get("fixture_set_id")),
        fixture_set_sha256=promotion_payload.get("fixture_set_sha256"),
        artifact_id=event.agent_task_artifact_id,
        artifact_kind=artifact.artifact_kind if artifact is not None else None,
        artifact_path=artifact.storage_path if artifact is not None else None,
        created_at=event.created_at,
    )


def _fixture_promotion_events_by_candidate(
    session: Session,
) -> dict[str, list[ClaimSupportPolicyChangeImpactFixturePromotionEventRef]]:
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    artifacts_by_id = _artifact_rows_by_id(session, events)
    refs_by_candidate: dict[str, list[ClaimSupportPolicyChangeImpactFixturePromotionEventRef]] = {}
    for event in events:
        event_ref = _fixture_promotion_event_ref(
            event,
            artifact=artifacts_by_id.get(event.agent_task_artifact_id),
        )
        promotion_payload = _fixture_promotion_payload(event)
        for candidate in promotion_payload.get("candidates") or []:
            candidate_id = str(candidate.get("candidate_id") or "")
            if candidate_id:
                refs_by_candidate.setdefault(candidate_id, []).append(event_ref)
    return refs_by_candidate


def _fixture_promotion_summary_from_event(
    event: SemanticGovernanceEvent,
) -> dict[str, Any]:
    promotion_payload = _fixture_promotion_payload(event)
    source_change_impact_ids = _string_list(
        promotion_payload.get("source_change_impact_ids") or []
    )
    source_escalation_event_ids = _string_list(
        promotion_payload.get("source_escalation_event_ids") or []
    )
    candidates = list(promotion_payload.get("candidates") or [])
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "fixture_set_id": promotion_payload.get("fixture_set_id"),
        "fixture_set_name": promotion_payload.get("fixture_set_name"),
        "fixture_set_version": promotion_payload.get("fixture_set_version"),
        "fixture_set_sha256": promotion_payload.get("fixture_set_sha256"),
        "fixture_count": int(promotion_payload.get("fixture_count") or 0),
        "candidate_count": int(promotion_payload.get("candidate_count") or len(candidates)),
        "candidate_ids": [
            str(candidate.get("candidate_id"))
            for candidate in candidates
            if candidate.get("candidate_id")
        ],
        "source_change_impact_ids": source_change_impact_ids,
        "source_escalation_event_ids": source_escalation_event_ids,
        "artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "created_at": event.created_at.isoformat(),
    }


def _fixture_promotion_event_summaries(session: Session) -> list[dict[str, Any]]:
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.desc(),
                SemanticGovernanceEvent.event_sequence.desc(),
            )
        )
    )
    return [_fixture_promotion_summary_from_event(event) for event in events]


def _replay_escalation_event_summary(
    event: SemanticGovernanceEvent,
    *,
    stale_cutoff,
) -> dict[str, Any]:
    event_payload = dict(event.event_payload_json or {})
    escalation_payload = dict(
        event_payload.get("claim_support_policy_impact_replay_escalation") or {}
    )
    age_hours = max((utcnow() - event.created_at).total_seconds() / 3600, 0.0)
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "change_impact_id": str(event.subject_id) if event.subject_id else None,
        "artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "alert_kind": escalation_payload.get("alert_kind"),
        "replay_status": escalation_payload.get("replay_status"),
        "created_at": event.created_at.isoformat(),
        "age_hours": round(age_hours, 4),
        "is_stale": event.created_at <= stale_cutoff,
    }


def claim_support_replay_alert_fixture_coverage_summary(
    session: Session,
    *,
    stale_after_hours: int = 24,
    limit: int = 50,
) -> dict[str, Any]:
    stale_after_hours = max(1, stale_after_hours)
    limit = max(1, limit)
    promotion_summaries = _fixture_promotion_event_summaries(session)
    active_corpus_snapshot = active_replay_alert_fixture_corpus_snapshot_summary(
        session,
        ensure_current=True,
    )
    promoted_escalation_event_ids = {
        str(event_id)
        for promotion in promotion_summaries
        for event_id in promotion.get("source_escalation_event_ids") or []
    }
    escalation_events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    stale_cutoff = utcnow() - timedelta(hours=stale_after_hours)
    unconverted_escalations = [
        _replay_escalation_event_summary(event, stale_cutoff=stale_cutoff)
        for event in escalation_events
        if str(event.id) not in promoted_escalation_event_ids
    ]
    stale_unconverted = [row for row in unconverted_escalations if row["is_stale"]]
    stale_unconverted_event_ids = sorted(
        {str(row["event_id"]) for row in stale_unconverted if row.get("event_id")}
    )
    summary_basis = {
        "schema_name": "claim_support_replay_alert_fixture_coverage_summary",
        "schema_version": "1.0",
        "promoted_fixture_set_count": len(promotion_summaries),
        "promoted_candidate_count": sum(
            int(row.get("candidate_count") or 0) for row in promotion_summaries
        ),
        "promoted_escalation_event_count": len(promoted_escalation_event_ids),
        "unconverted_escalation_event_count": len(unconverted_escalations),
        "stale_unconverted_escalation_event_count": len(stale_unconverted),
        "stale_unconverted_escalation_event_ids": stale_unconverted_event_ids,
        "stale_unconverted_escalation_set_sha256": replay_alert_escalation_set_sha256(
            stale_unconverted_event_ids
        ),
        "stale_after_hours": stale_after_hours,
        "latest_promoted_fixture_set": promotion_summaries[0]
        if promotion_summaries
        else None,
        "active_replay_alert_fixture_corpus_snapshot": active_corpus_snapshot,
        "active_replay_alert_fixture_corpus_snapshot_id": (
            active_corpus_snapshot.get("snapshot_id") if active_corpus_snapshot else None
        ),
        "active_replay_alert_fixture_corpus_sha256": (
            active_corpus_snapshot.get("snapshot_sha256")
            if active_corpus_snapshot
            else None
        ),
        "active_replay_alert_fixture_corpus_fixture_count": (
            int(active_corpus_snapshot.get("fixture_count") or 0)
            if active_corpus_snapshot
            else 0
        ),
        "active_replay_alert_fixture_corpus_invalid_promotion_event_count": (
            int(active_corpus_snapshot.get("invalid_promotion_event_count") or 0)
            if active_corpus_snapshot
            else 0
        ),
    }
    return {
        **summary_basis,
        "summary_sha256": payload_sha256(summary_basis),
        "generated_at": utcnow().isoformat(),
        "limit": limit,
        "has_more_unconverted_escalations": len(unconverted_escalations) > limit,
        "promoted_fixture_sets": promotion_summaries[:limit],
        "unconverted_escalation_events": unconverted_escalations[:limit],
        "stale_unconverted_escalation_events": stale_unconverted,
    }


def latest_claim_support_replay_alert_fixture_rows(
    session: Session,
    *,
    include_promoted: bool = True,
    limit: int = 100,
    exclude_case_ids: set[str] | None = None,
    stale_after_hours: int = 24,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    coverage_summary = claim_support_replay_alert_fixture_coverage_summary(
        session,
        stale_after_hours=stale_after_hours,
        limit=limit or 1,
    )
    exclude_case_ids = set(exclude_case_ids or set())
    limit = max(0, limit)
    if not include_promoted or limit == 0:
        return [], {
            **coverage_summary,
            "enabled": include_promoted,
            "included_replay_alert_fixture_count": 0,
            "replay_alert_fixture_count": 0,
            "excluded_case_ids": sorted(exclude_case_ids),
            "fixture_source": "disabled",
        }
    snapshot, corpus_rows, available_fixture_count = active_replay_alert_fixture_corpus_rows(
        session,
        exclude_case_ids=exclude_case_ids,
        limit=limit,
    )
    selected = [dict(row.fixture_json or {}) for row in corpus_rows]
    snapshot_summary = replay_alert_fixture_corpus_snapshot_summary(snapshot)
    replay_alert_fixture_count = int(snapshot.fixture_count) if snapshot is not None else 0
    return selected, {
        **coverage_summary,
        "enabled": include_promoted,
        "fixture_source": (
            "active_replay_alert_fixture_corpus_snapshot"
            if snapshot is not None
            else "none"
        ),
        "active_replay_alert_fixture_corpus_snapshot": snapshot_summary,
        "included_replay_alert_fixture_count": len(selected),
        "replay_alert_fixture_count": replay_alert_fixture_count,
        "available_replay_alert_fixture_count": available_fixture_count,
        "excluded_case_ids": sorted(exclude_case_ids),
        "has_more_replay_alert_fixtures": len(selected) < available_fixture_count,
    }


def _looks_like_technical_report_draft(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    required = {
        "title",
        "goal",
        "target_length",
        "harness_task_id",
        "generator_mode",
        "claims",
        "markdown",
    }
    return required.issubset(payload)


def _draft_payload_from_task(task: AgentTask | None) -> tuple[dict[str, Any] | None, str]:
    if task is None:
        return None, "missing_draft_task"
    result_payload = dict(task.result_json or {})
    candidates = [
        ((result_payload.get("payload") or {}).get("draft") if result_payload else None),
        result_payload.get("draft"),
        result_payload,
    ]
    for candidate in candidates:
        if _looks_like_technical_report_draft(candidate):
            return deepcopy(candidate), "draft_task_payload"
    return None, "draft_task_missing_valid_payload"


def _fallback_draft_payload_from_derivation(
    row: ClaimEvidenceDerivation,
) -> dict[str, Any]:
    claim_text = row.claim_text or row.claim_id
    source_search_result_ids = _string_list(row.source_search_request_result_ids_json)
    support_judgment = dict(row.support_judgment_json or {})
    if not source_search_result_ids:
        source_search_result_ids = _string_list(
            support_judgment.get("source_search_request_result_ids") or []
        )
    section_id = f"section:replay_alert:{row.claim_id}"
    return {
        "document_kind": "technical_report",
        "title": "Claim Support Replay Alert Fixture",
        "goal": "Replay a claim-support policy change impact as evaluation coverage.",
        "audience": "Evaluation",
        "target_length": "short",
        "harness_task_id": str(row.agent_task_id or row.evidence_package_export_id),
        "generator_mode": "structured_fallback",
        "generator_model": None,
        "used_fallback": True,
        "llm_adapter_contract": {},
        "document_refs": [],
        "required_concept_keys": [],
        "sections": [
            {
                "section_id": section_id,
                "title": "Replay Alert Claim",
                "body_markdown": claim_text,
                "claim_ids": [row.claim_id],
            }
        ],
        "claims": [
            {
                "claim_id": row.claim_id,
                "section_id": section_id,
                "rendered_text": claim_text,
                "concept_keys": [],
                "evidence_card_ids": [],
                "graph_edge_ids": _string_list(row.graph_edge_ids_json),
                "fact_ids": _string_list(row.fact_ids_json),
                "assertion_ids": _string_list(row.assertion_ids_json),
                "source_document_ids": _string_list(row.source_document_ids_json),
                "support_level": row.support_verdict,
                "review_policy_status": "candidate_disclosed",
                "source_search_request_ids": _string_list(
                    row.source_search_request_ids_json
                ),
                "source_search_request_result_ids": source_search_result_ids,
                "source_evidence_package_export_ids": _string_list(
                    row.source_evidence_package_export_ids_json
                ),
                "source_evidence_package_sha256s": _string_list(
                    row.source_evidence_package_sha256s_json
                ),
                "source_evidence_trace_sha256s": _string_list(
                    row.source_evidence_trace_sha256s_json
                ),
                "provenance_lock": dict(row.provenance_lock_json or {}),
                "provenance_lock_sha256": row.provenance_lock_sha256,
                "support_verdict": row.support_verdict,
                "support_score": row.support_score,
                "support_judge_run_id": str(row.support_judge_run_id)
                if row.support_judge_run_id
                else None,
                "support_judgment": support_judgment,
                "support_judgment_sha256": row.support_judgment_sha256,
                "derivation_rule": row.derivation_rule,
                "evidence_package_export_id": str(row.evidence_package_export_id),
                "evidence_package_sha256": row.evidence_package_sha256,
                "derivation_sha256": row.derivation_sha256,
                "source_snapshot_sha256s": _string_list(row.source_snapshot_sha256s_json),
            }
        ],
        "blocked_claims": [],
        "evidence_cards": [],
        "source_evidence_package_exports": [],
        "graph_context": [],
        "evidence_package_export_id": str(row.evidence_package_export_id),
        "evidence_package_sha256": row.evidence_package_sha256,
        "source_snapshot_sha256s": _string_list(row.source_snapshot_sha256s_json),
        "support_judge_run_id": str(row.support_judge_run_id)
        if row.support_judge_run_id
        else None,
        "support_judgment_sha256s": [row.support_judgment_sha256]
        if row.support_judgment_sha256
        else [],
        "claim_support_summary": {
            "source": "claim_support_policy_change_impact_replay_alert",
            "source_support_verdict": row.support_verdict,
            "source_support_judgment_sha256": row.support_judgment_sha256,
        },
        "claim_derivations": [],
        "markdown": claim_text,
        "warnings": [
            "Fixture reconstructed from claim_evidence_derivations because the "
            "source draft task did not expose a complete technical-report draft payload."
        ],
        "success_metrics": [],
    }


def _expected_verdict_for_fixture(
    *,
    draft_source: str,
    derivation: ClaimEvidenceDerivation,
) -> str:
    if draft_source != "draft_task_payload":
        return "insufficient_evidence"
    support_judgment = dict(derivation.support_judgment_json or {})
    candidate = derivation.support_verdict or support_judgment.get("verdict")
    if candidate in {"supported", "unsupported", "insufficient_evidence"}:
        return str(candidate)
    return "insufficient_evidence"


def _fixture_candidate_identity_basis(
    *,
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
    derivation: ClaimEvidenceDerivation,
    draft_source: str,
    fixture_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_name": "claim_support_policy_impact_fixture_candidate_identity",
        "schema_version": "1.0",
        "change_impact_id": str(item.change_impact.change_impact_id),
        "impact_payload_sha256": item.change_impact.impact_payload_sha256,
        "alert_kind": item.alert_kind,
        "source_claim_derivation_id": str(derivation.id),
        "source_draft_task_id": str(derivation.agent_task_id)
        if derivation.agent_task_id
        else None,
        "source_support_judgment_sha256": derivation.support_judgment_sha256,
        "draft_source": draft_source,
        "fixture_sha256": fixture_sha256,
    }


def _fixture_candidate_source_basis(
    *,
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
    derivation: ClaimEvidenceDerivation,
    draft_source: str,
    fixture_sha256: str,
    candidate_identity_sha256: str,
) -> dict[str, Any]:
    escalation_event_ids = sorted({str(event.event_id) for event in item.escalation_events})
    return {
        "schema_name": "claim_support_policy_impact_fixture_candidate_source",
        "schema_version": "1.0",
        "candidate_identity_sha256": candidate_identity_sha256,
        "change_impact_id": str(item.change_impact.change_impact_id),
        "impact_payload_sha256": item.change_impact.impact_payload_sha256,
        "alert_kind": item.alert_kind,
        "replay_status": item.replay_status,
        "is_stale": item.is_stale,
        "escalation_event_ids": escalation_event_ids,
        "latest_escalation_event_id": str(item.latest_escalation_event_id)
        if item.latest_escalation_event_id
        else None,
        "affected_verification_task_ids": sorted(
            {str(task_id) for task_id in item.affected_verification_task_ids}
        ),
        "source_claim_derivation_id": str(derivation.id),
        "source_draft_task_id": str(derivation.agent_task_id)
        if derivation.agent_task_id
        else None,
        "source_support_verdict": derivation.support_verdict,
        "source_support_judgment_sha256": derivation.support_judgment_sha256,
        "draft_source": draft_source,
        "fixture_sha256": fixture_sha256,
    }


def _candidate_from_derivation(
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
    *,
    derivation: ClaimEvidenceDerivation,
    draft_task: AgentTask | None,
) -> ClaimSupportPolicyChangeImpactFixtureCandidateResponse:
    draft_payload, draft_source = _draft_payload_from_task(draft_task)
    if draft_payload is None:
        draft_payload = _fallback_draft_payload_from_derivation(derivation)
        draft_source = "reconstructed_claim_derivation"
    expected_verdict = _expected_verdict_for_fixture(
        draft_source=draft_source,
        derivation=derivation,
    )
    case_id = f"replay_alert_{item.change_impact.change_impact_id.hex}_{derivation.id.hex[:12]}"
    hard_case_kind = f"replay_alert_{item.alert_kind}_policy_change_impact"
    fixture = {
        "case_id": case_id,
        "description": (
            "Claim-support policy replay alert promoted into durable judge "
            "evaluation coverage."
        ),
        "hard_case_kind": hard_case_kind,
        "expected_verdict": expected_verdict,
        "claim_id": derivation.claim_id,
        "draft_payload": draft_payload,
    }
    identity_fixture_sha256 = payload_sha256(fixture)
    identity_basis = _fixture_candidate_identity_basis(
        item=item,
        derivation=derivation,
        draft_source=draft_source,
        fixture_sha256=identity_fixture_sha256,
    )
    candidate_id = payload_sha256(identity_basis)
    source_basis = _fixture_candidate_source_basis(
        item=item,
        derivation=derivation,
        draft_source=draft_source,
        fixture_sha256=identity_fixture_sha256,
        candidate_identity_sha256=candidate_id,
    )
    fixture["replay_alert_source"] = {
        **source_basis,
        "candidate_id": candidate_id,
        "candidate_identity": identity_basis,
        "activation_task_id": str(item.change_impact.activation_task_id)
        if item.change_impact.activation_task_id
        else None,
        "affected_verification_task_ids": [
            str(task_id) for task_id in item.affected_verification_task_ids
        ],
    }
    fixture_sha = payload_sha256(fixture)
    return ClaimSupportPolicyChangeImpactFixtureCandidateResponse(
        candidate_id=candidate_id,
        change_impact_id=item.change_impact.change_impact_id,
        alert_kind=item.alert_kind,
        severity=item.severity,
        replay_status=item.replay_status,
        is_stale=item.is_stale,
        source_claim_derivation_id=derivation.id,
        source_draft_task_id=derivation.agent_task_id,
        affected_verification_task_ids=list(item.affected_verification_task_ids),
        escalation_event_ids=[event.event_id for event in item.escalation_events],
        latest_escalation_event_id=item.latest_escalation_event_id,
        case_id=case_id,
        hard_case_kind=hard_case_kind,
        expected_verdict=expected_verdict,
        fixture_sha256=fixture_sha,
        fixture=fixture,
        source_payload_sha256=payload_sha256(source_basis),
        operator_links={
            "source_change_impact": (
                "/agent-tasks/claim-support-policy-change-impacts/"
                f"{item.change_impact.change_impact_id}"
            ),
            "source_draft_task": f"/agent-tasks/{derivation.agent_task_id}"
            if derivation.agent_task_id
            else None,
            "promote": (
                "/agent-tasks/claim-support-policy-change-impacts/"
                "alerts/fixture-promotions"
            ),
        },
    )


def _derivations_for_alert_item(
    session: Session,
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
) -> list[ClaimEvidenceDerivation]:
    derivation_ids = _uuid_list(item.change_impact.impacted_claim_derivation_ids)
    if not derivation_ids:
        return []
    return list(
        session.scalars(
            select(ClaimEvidenceDerivation)
            .where(ClaimEvidenceDerivation.id.in_(derivation_ids))
            .order_by(
                ClaimEvidenceDerivation.created_at.desc(),
                ClaimEvidenceDerivation.id.desc(),
            )
        )
    )


def _draft_tasks_for_derivations(
    session: Session,
    derivations: list[ClaimEvidenceDerivation],
) -> dict[UUID, AgentTask]:
    task_ids = [row.agent_task_id for row in derivations if row.agent_task_id is not None]
    if not task_ids:
        return {}
    return {
        row.id: row
        for row in session.scalars(select(AgentTask).where(AgentTask.id.in_(task_ids)))
    }


def claim_support_policy_change_impact_fixture_candidates(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    include_unescalated: bool = False,
    include_promoted: bool = True,
) -> ClaimSupportPolicyChangeImpactFixtureCandidateListResponse:
    limit = max(1, limit)
    alert_feed = claim_support_policy_change_impact_alerts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
    )
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse] = []
    for item in alert_feed.items:
        if not include_unescalated and not item.escalation_events:
            continue
        derivations = _derivations_for_alert_item(session, item)
        draft_tasks = _draft_tasks_for_derivations(session, derivations)
        candidates.extend(
            _candidate_from_derivation(
                item,
                derivation=derivation,
                draft_task=draft_tasks.get(derivation.agent_task_id),
            )
            for derivation in derivations
        )

    promotion_events_by_candidate = _fixture_promotion_events_by_candidate(session)
    promoted_count = 0
    annotated_candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse] = []
    for candidate in candidates:
        promotion_events = promotion_events_by_candidate.get(candidate.candidate_id, [])
        already_promoted = bool(promotion_events)
        if already_promoted:
            promoted_count += 1
        annotated = candidate.model_copy(
            update={
                "already_promoted": already_promoted,
                "promotion_events": promotion_events,
            }
        )
        if include_promoted or not already_promoted:
            annotated_candidates.append(annotated)

    matching_count = len(annotated_candidates)
    limited_items = annotated_candidates[:limit]
    source_escalation_ids = {
        event_id for candidate in candidates for event_id in candidate.escalation_event_ids
    }
    return ClaimSupportPolicyChangeImpactFixtureCandidateListResponse(
        summary=ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse(
            alert_matching_count=alert_feed.matching_count,
            candidate_count=len(candidates),
            promoted_candidate_count=promoted_count,
            unpromoted_candidate_count=len(candidates) - promoted_count,
            source_escalation_event_count=len(source_escalation_ids),
            stale_after_hours=stale_after_hours,
        ),
        generated_at=alert_feed.generated_at,
        stale_after_hours=alert_feed.stale_after_hours,
        limit=limit,
        matching_count=matching_count,
        item_count=len(limited_items),
        has_more=matching_count > len(limited_items),
        items=limited_items,
    )


def _promotion_event_deduplication_key(
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
) -> str:
    basis = {
        "fixture_set_id": str(fixture_set.id),
        "fixture_set_sha256": fixture_set.fixture_set_sha256,
        "candidate_ids": sorted(candidate.candidate_id for candidate in candidates),
        "fixture_sha256s": sorted(candidate.fixture_sha256 for candidate in candidates),
    }
    return f"claim_support_policy_impact_fixture_promoted:{payload_sha256(basis)}"


def _fixture_promotion_anchor_task_id(
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
) -> UUID | None:
    for candidate in candidates:
        activation_task_id = (
            candidate.fixture.get("replay_alert_source") or {}
        ).get("activation_task_id")
        if activation_task_id:
            return UUID(str(activation_task_id))
    for candidate in candidates:
        if candidate.source_draft_task_id is not None:
            return candidate.source_draft_task_id
    return None


def _record_fixture_promotion_event(
    session: Session,
    *,
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
    requested_by: str,
    storage_service: StorageService | None,
) -> tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool]:
    deduplication_key = _promotion_event_deduplication_key(fixture_set, candidates)
    existing = session.scalar(
        select(SemanticGovernanceEvent)
        .where(SemanticGovernanceEvent.deduplication_key == deduplication_key)
        .limit(1)
    )
    if existing is not None:
        artifact = (
            session.get(AgentTaskArtifact, existing.agent_task_artifact_id)
            if existing.agent_task_artifact_id is not None
            else None
        )
        return existing, artifact, False

    semantic_basis = active_semantic_basis(session)
    anchor_task_id = _fixture_promotion_anchor_task_id(candidates)
    source_change_impact_ids = sorted({str(row.change_impact_id) for row in candidates})
    source_escalation_event_ids = sorted(
        {str(event_id) for row in candidates for event_id in row.escalation_event_ids}
    )
    candidate_payloads = [
        {
            "candidate_id": row.candidate_id,
            "candidate_identity_sha256": (
                (row.fixture.get("replay_alert_source") or {}).get(
                    "candidate_identity_sha256"
                )
                or row.candidate_id
            ),
            "case_id": row.case_id,
            "fixture_sha256": row.fixture_sha256,
            "source_payload_sha256": row.source_payload_sha256,
            "change_impact_id": str(row.change_impact_id),
            "source_claim_derivation_id": str(row.source_claim_derivation_id)
            if row.source_claim_derivation_id
            else None,
            "source_draft_task_id": str(row.source_draft_task_id)
            if row.source_draft_task_id
            else None,
            "escalation_event_ids": [str(event_id) for event_id in row.escalation_event_ids],
            "latest_escalation_event_id": str(row.latest_escalation_event_id)
            if row.latest_escalation_event_id
            else None,
            "hard_case_kind": row.hard_case_kind,
            "expected_verdict": row.expected_verdict,
        }
        for row in candidates
    ]
    receipt_basis = {
        "schema_name": CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "fixture_set_id": str(fixture_set.id),
        "fixture_set_name": fixture_set.fixture_set_name,
        "fixture_set_version": fixture_set.fixture_set_version,
        "fixture_set_sha256": fixture_set.fixture_set_sha256,
        "fixture_count": fixture_set.fixture_count,
        "candidate_count": len(candidates),
        "source_change_impact_ids": source_change_impact_ids,
        "source_escalation_event_ids": source_escalation_event_ids,
        "candidates": candidate_payloads,
        "semantic_basis": semantic_basis,
        "recorded_by": requested_by,
        "recorded_at": utcnow().isoformat(),
        "deduplication_key": deduplication_key,
    }
    receipt_payload = {
        **receipt_basis,
        "receipt_sha256": payload_sha256(receipt_basis),
    }
    artifact: AgentTaskArtifact | None = None
    if anchor_task_id is not None:
        artifact = create_agent_task_artifact(
            session,
            task_id=anchor_task_id,
            artifact_kind=CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND,
            payload=receipt_payload,
            storage_service=storage_service,
            filename=(
                "claim_support_policy_impact_fixture_promotion_"
                f"{fixture_set.id}_{receipt_payload['receipt_sha256'][:12]}.json"
            ),
        )
    event = record_semantic_governance_event(
        session,
        event_kind=CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND,
        governance_scope=(
            f"claim_support_policy:{fixture_set.fixture_set_name}:"
            f"{fixture_set.fixture_set_version}"
        ),
        subject_table="claim_support_fixture_sets",
        subject_id=fixture_set.id,
        task_id=anchor_task_id,
        ontology_snapshot_id=_uuid_or_none(semantic_basis.get("active_ontology_snapshot_id")),
        semantic_graph_snapshot_id=_uuid_or_none(
            semantic_basis.get("active_semantic_graph_snapshot_id")
        ),
        agent_task_artifact_id=artifact.id if artifact is not None else None,
        receipt_sha256=receipt_payload["receipt_sha256"],
        event_payload={
            "claim_support_policy_impact_fixture_promotion": receipt_payload,
            "semantic_basis": semantic_basis,
        },
        deduplication_key=deduplication_key,
        created_by=requested_by,
    )
    return event, artifact, True


def _waiver_stale_unconverted_escalation_event_ids(payload: dict[str, Any]) -> list[str]:
    return stale_unconverted_escalation_event_ids_from_waiver(payload)


def _waiver_stale_unconverted_escalation_count(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("stale_unconverted_escalation_event_count") or 0)
    except (TypeError, ValueError):
        return 0


def _waiver_has_complete_stale_escalation_set(
    payload: dict[str, Any],
    *,
    stale_escalation_event_ids: list[str],
) -> bool:
    summary = dict(payload.get("replay_alert_fixture_summary") or {})
    stale_count = _waiver_stale_unconverted_escalation_count(payload)
    if stale_count <= 0:
        return False
    has_full_stale_set = bool(
        payload.get("stale_unconverted_escalation_event_ids")
        or summary.get("stale_unconverted_escalation_event_ids")
    )
    if summary.get("has_more_unconverted_escalations") and not has_full_stale_set:
        return False
    return len(stale_escalation_event_ids) == stale_count


def _waiver_closure_event_deduplication_key(
    *,
    waiver_artifact_id: UUID,
    waiver_sha256: str,
    promotion_receipt_sha256: str,
) -> str:
    return (
        "claim_support_replay_alert_fixture_coverage_waiver_closed:"
        f"{waiver_artifact_id}:{waiver_sha256}:{promotion_receipt_sha256}"
    )


def _record_replay_alert_fixture_coverage_waiver_closure_event(
    session: Session,
    *,
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
    promotion_event: SemanticGovernanceEvent,
    promotion_artifact: AgentTaskArtifact,
    waiver_artifact: AgentTaskArtifact,
    waived_escalation_event_ids: list[str],
    covered_escalation_event_ids: list[str],
    coverage_promotion_event_ids: list[str] | None = None,
    coverage_promotion_artifact_ids: list[str] | None = None,
    coverage_promotion_receipt_sha256s: list[str] | None = None,
    source_change_impact_ids: list[str] | None = None,
    source_escalation_event_ids: list[str] | None = None,
    requested_by: str,
    storage_service: StorageService | None,
) -> tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool] | None:
    waiver_payload = dict(waiver_artifact.payload_json or {})
    waiver_sha256 = str(waiver_payload.get("waiver_sha256") or "")
    promotion_receipt_sha256 = str(promotion_event.receipt_sha256 or "")
    if not waiver_sha256 or not promotion_receipt_sha256:
        return None

    deduplication_key = _waiver_closure_event_deduplication_key(
        waiver_artifact_id=waiver_artifact.id,
        waiver_sha256=waiver_sha256,
        promotion_receipt_sha256=promotion_receipt_sha256,
    )
    existing = session.scalar(
        select(SemanticGovernanceEvent)
        .where(SemanticGovernanceEvent.deduplication_key == deduplication_key)
        .limit(1)
    )
    if existing is not None:
        artifact = (
            session.get(AgentTaskArtifact, existing.agent_task_artifact_id)
            if existing.agent_task_artifact_id is not None
            else None
        )
        return existing, artifact, False

    semantic_basis = active_semantic_basis(session)
    promotion_payload = (
        (promotion_event.event_payload_json or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        )
        or {}
    )
    receipt_source_change_impact_ids = list(
        source_change_impact_ids
        or []
    ) or list(
        promotion_payload.get("source_change_impact_ids")
        or sorted({str(candidate.change_impact_id) for candidate in candidates})
    )
    receipt_source_escalation_event_ids = list(
        source_escalation_event_ids
        or []
    ) or list(
        promotion_payload.get("source_escalation_event_ids")
        or sorted(
            {
                str(event_id)
                for candidate in candidates
                for event_id in candidate.escalation_event_ids
            }
        )
    )
    receipt_basis = {
        "schema_name": (
            CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_RECEIPT_SCHEMA
        ),
        "schema_version": "1.0",
        "closure_status": "closed_by_fixture_promotion",
        "closed_by": requested_by,
        "closed_at": utcnow().isoformat(),
        "waiver_artifact_id": str(waiver_artifact.id),
        "waiver_task_id": str(waiver_artifact.task_id),
        "waiver_sha256": waiver_sha256,
        "waiver_severity": waiver_payload.get("waiver_severity"),
        "waiver_expires_at": waiver_payload.get("waiver_expires_at"),
        "waiver_stale_unconverted_escalation_event_count": (
            _waiver_stale_unconverted_escalation_count(waiver_payload)
        ),
        "waived_escalation_event_ids": waived_escalation_event_ids,
        "covered_escalation_event_ids": covered_escalation_event_ids,
        "coverage_promotion_event_ids": sorted(coverage_promotion_event_ids or []),
        "coverage_promotion_artifact_ids": sorted(coverage_promotion_artifact_ids or []),
        "coverage_promotion_receipt_sha256s": sorted(
            coverage_promotion_receipt_sha256s or []
        ),
        "source_change_impact_ids": receipt_source_change_impact_ids,
        "source_escalation_event_ids": receipt_source_escalation_event_ids,
        "fixture_set_id": str(fixture_set.id),
        "fixture_set_name": fixture_set.fixture_set_name,
        "fixture_set_version": fixture_set.fixture_set_version,
        "fixture_set_sha256": fixture_set.fixture_set_sha256,
        "promotion_event_id": str(promotion_event.id),
        "promotion_receipt_sha256": promotion_receipt_sha256,
        "promotion_artifact_id": str(promotion_artifact.id),
        "promotion_artifact_kind": promotion_artifact.artifact_kind,
        "promotion_artifact_path": promotion_artifact.storage_path,
        "promotion_payload_sha256": promotion_event.payload_sha256,
        "closure_reason": (
            "Promoted replay-alert fixture coverage covers the stale escalation "
            "event set waived by this verification artifact."
        ),
        "semantic_basis": semantic_basis,
        "deduplication_key": deduplication_key,
    }
    receipt_payload = {
        **receipt_basis,
        "receipt_sha256": payload_sha256(receipt_basis),
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=promotion_artifact.task_id,
        artifact_kind=(
            CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND
        ),
        payload=receipt_payload,
        storage_service=storage_service,
        filename=(
            "claim_support_replay_alert_fixture_coverage_waiver_closure_"
            f"{waiver_artifact.id}_{receipt_payload['receipt_sha256'][:12]}.json"
        ),
    )
    event = record_semantic_governance_event(
        session,
        event_kind=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND,
        governance_scope=(
            f"claim_support_replay_alert_fixture_coverage_waiver:"
            f"{fixture_set.fixture_set_name}:{fixture_set.fixture_set_version}"
        ),
        subject_table="agent_task_artifacts",
        subject_id=waiver_artifact.id,
        task_id=promotion_artifact.task_id,
        ontology_snapshot_id=_uuid_or_none(semantic_basis.get("active_ontology_snapshot_id")),
        semantic_graph_snapshot_id=_uuid_or_none(
            semantic_basis.get("active_semantic_graph_snapshot_id")
        ),
        agent_task_artifact_id=artifact.id,
        receipt_sha256=receipt_payload["receipt_sha256"],
        event_payload={
            "claim_support_replay_alert_fixture_coverage_waiver_closure": (
                receipt_payload
            ),
            "semantic_basis": semantic_basis,
        },
        deduplication_key=deduplication_key,
        created_by=requested_by,
    )
    return event, artifact, True


def _record_replay_alert_fixture_coverage_waiver_closure_events(
    session: Session,
    *,
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
    promotion_event: SemanticGovernanceEvent,
    promotion_artifact: AgentTaskArtifact | None,
    requested_by: str,
    storage_service: StorageService | None,
) -> list[tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool]]:
    if promotion_artifact is None:
        return []

    promoted_escalation_event_ids = {
        str(event_id) for candidate in candidates for event_id in candidate.escalation_event_ids
    }
    if not promoted_escalation_event_ids:
        return []

    recorded: list[tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool]] = []
    ledger_closure_candidates = (
        apply_replay_alert_fixture_coverage_promotion_to_waiver_ledgers(
            session,
            promotion_event=promotion_event,
            promotion_artifact=promotion_artifact,
            promoted_escalation_event_ids=promoted_escalation_event_ids,
        )
    )
    for candidate in ledger_closure_candidates:
        event = _record_replay_alert_fixture_coverage_waiver_closure_event(
            session,
            fixture_set=fixture_set,
            candidates=candidates,
            promotion_event=promotion_event,
            promotion_artifact=promotion_artifact,
            waiver_artifact=candidate.waiver_artifact,
            waived_escalation_event_ids=candidate.waived_escalation_event_ids,
            covered_escalation_event_ids=candidate.covered_escalation_event_ids,
            coverage_promotion_event_ids=candidate.coverage_promotion_event_ids,
            coverage_promotion_artifact_ids=candidate.coverage_promotion_artifact_ids,
            coverage_promotion_receipt_sha256s=(
                candidate.coverage_promotion_receipt_sha256s
            ),
            source_change_impact_ids=[
                str(value) for value in (candidate.ledger.source_change_impact_ids_json or [])
            ],
            source_escalation_event_ids=candidate.waived_escalation_event_ids,
            requested_by=requested_by,
            storage_service=storage_service,
        )
        if event is None:
            continue
        closure_event, closure_artifact, _created = event
        mark_replay_alert_fixture_coverage_waiver_ledger_closed(
            session,
            ledger=candidate.ledger,
            closure_event=closure_event,
            closure_artifact=closure_artifact,
            coverage_promotion_event_ids=candidate.coverage_promotion_event_ids,
            coverage_promotion_artifact_ids=candidate.coverage_promotion_artifact_ids,
            coverage_promotion_receipt_sha256s=(
                candidate.coverage_promotion_receipt_sha256s
            ),
        )
        recorded.append(event)

    ledger_backed_waiver_artifact_ids = waiver_artifact_ids_with_coverage_ledgers(session)
    waiver_artifacts = list(
        session.scalars(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.artifact_kind
                == CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND
            )
            .order_by(AgentTaskArtifact.created_at.asc(), AgentTaskArtifact.id.asc())
        )
    )
    for waiver_artifact in waiver_artifacts:
        if waiver_artifact.id in ledger_backed_waiver_artifact_ids:
            continue
        waiver_payload = dict(waiver_artifact.payload_json or {})
        waived_escalation_event_ids = _waiver_stale_unconverted_escalation_event_ids(
            waiver_payload
        )
        if not _waiver_has_complete_stale_escalation_set(
            waiver_payload,
            stale_escalation_event_ids=waived_escalation_event_ids,
        ):
            continue
        if not set(waived_escalation_event_ids).issubset(promoted_escalation_event_ids):
            continue
        event = _record_replay_alert_fixture_coverage_waiver_closure_event(
            session,
            fixture_set=fixture_set,
            candidates=candidates,
            promotion_event=promotion_event,
            promotion_artifact=promotion_artifact,
            waiver_artifact=waiver_artifact,
            waived_escalation_event_ids=waived_escalation_event_ids,
            covered_escalation_event_ids=waived_escalation_event_ids,
            coverage_promotion_event_ids=[str(promotion_event.id)],
            coverage_promotion_artifact_ids=[str(promotion_artifact.id)],
            coverage_promotion_receipt_sha256s=[
                str(promotion_event.receipt_sha256)
            ]
            if promotion_event.receipt_sha256
            else [],
            requested_by=requested_by,
            storage_service=storage_service,
        )
        if event is not None:
            recorded.append(event)
    return recorded


def promote_claim_support_policy_change_impact_fixture_candidates(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    fixture_set_name: str = "claim_support_replay_alert_promotions",
    fixture_set_version: str = "v1",
    requested_by: str = "docling-system",
    include_unescalated: bool = False,
    storage_service: StorageService | None = None,
    commit: bool = True,
) -> ClaimSupportPolicyChangeImpactFixturePromotionResponse:
    candidate_response = claim_support_policy_change_impact_fixture_candidates(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_unescalated=include_unescalated,
        include_promoted=False,
    )
    candidates = list(candidate_response.items)
    if not candidates:
        active_corpus_snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(session)
        active_corpus_summary = replay_alert_fixture_corpus_snapshot_summary(
            active_corpus_snapshot
        )
        if commit:
            session.commit()
        else:
            session.flush()
        return ClaimSupportPolicyChangeImpactFixturePromotionResponse(
            fixture_set_name=fixture_set_name,
            fixture_set_version=fixture_set_version,
            skipped_candidate_count=candidate_response.summary.promoted_candidate_count,
            candidate_matching_count=candidate_response.matching_count,
            candidate_item_count=candidate_response.item_count,
            has_more_candidates=candidate_response.has_more,
            candidate_summary=candidate_response.summary,
            active_replay_fixture_corpus_snapshot_id=_uuid_or_none(
                active_corpus_summary.get("snapshot_id") if active_corpus_summary else None
            ),
            active_replay_fixture_corpus_sha256=(
                active_corpus_summary.get("snapshot_sha256")
                if active_corpus_summary
                else None
            ),
            active_replay_fixture_corpus_fixture_count=(
                int(active_corpus_summary.get("fixture_count") or 0)
                if active_corpus_summary
                else 0
            ),
        )

    fixtures_by_case_id = {
        str(fixture.get("case_id") or ""): fixture
        for fixture in default_claim_support_evaluation_fixtures()
    }
    for candidate in candidates:
        fixtures_by_case_id[candidate.case_id] = candidate.fixture
    source_change_impact_ids = sorted(
        {candidate.change_impact_id for candidate in candidates},
        key=str,
    )
    source_escalation_event_ids = sorted(
        {event_id for candidate in candidates for event_id in candidate.escalation_event_ids},
        key=str,
    )
    fixture_set = ensure_claim_support_fixture_set(
        session,
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        fixtures=list(fixtures_by_case_id.values()),
        metadata={
            "source": "claim_support_policy_change_impact_replay_alerts",
            "requested_by": requested_by,
            "source_change_impact_ids": [str(value) for value in source_change_impact_ids],
            "source_escalation_event_ids": [
                str(value) for value in source_escalation_event_ids
            ],
            "candidate_ids": [candidate.candidate_id for candidate in candidates],
        },
    )
    event, artifact, created = _record_fixture_promotion_event(
        session,
        fixture_set=fixture_set,
        candidates=candidates,
        requested_by=requested_by,
        storage_service=storage_service,
    )
    waiver_closure_events = _record_replay_alert_fixture_coverage_waiver_closure_events(
        session,
        fixture_set=fixture_set,
        candidates=candidates,
        promotion_event=event,
        promotion_artifact=artifact,
        requested_by=requested_by,
        storage_service=storage_service,
    )
    active_corpus_snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(session)
    active_corpus_summary = replay_alert_fixture_corpus_snapshot_summary(
        active_corpus_snapshot
    )
    _refresh_existing_evidence_manifests_for_fixture_candidates(session, candidates)
    if commit:
        session.commit()
    else:
        session.flush()
    event_ref = _fixture_promotion_event_ref(event, artifact=artifact)
    promoted_candidates = [
        candidate.model_copy(
            update={
                "already_promoted": True,
                "promotion_events": [event_ref],
            }
        )
        for candidate in candidates
    ]
    return ClaimSupportPolicyChangeImpactFixturePromotionResponse(
        fixture_set_id=fixture_set.id,
        fixture_set_name=fixture_set.fixture_set_name,
        fixture_set_version=fixture_set.fixture_set_version,
        fixture_set_sha256=fixture_set.fixture_set_sha256,
        fixture_count=fixture_set.fixture_count,
        promoted_candidate_count=len(candidates),
        skipped_candidate_count=candidate_response.summary.promoted_candidate_count,
        candidate_matching_count=candidate_response.matching_count,
        candidate_item_count=candidate_response.item_count,
        has_more_candidates=candidate_response.has_more,
        candidate_summary=candidate_response.summary,
        source_change_impact_ids=source_change_impact_ids,
        source_escalation_event_ids=source_escalation_event_ids,
        promotion_event_id=event.id,
        promotion_receipt_sha256=event.receipt_sha256,
        artifact_id=artifact.id if artifact is not None else None,
        artifact_kind=artifact.artifact_kind if artifact is not None else None,
        artifact_path=artifact.storage_path if artifact is not None else None,
        created=created,
        active_replay_fixture_corpus_snapshot_id=_uuid_or_none(
            active_corpus_summary.get("snapshot_id") if active_corpus_summary else None
        ),
        active_replay_fixture_corpus_sha256=(
            active_corpus_summary.get("snapshot_sha256") if active_corpus_summary else None
        ),
        active_replay_fixture_corpus_fixture_count=(
            int(active_corpus_summary.get("fixture_count") or 0)
            if active_corpus_summary
            else 0
        ),
        waiver_closure_count=len(waiver_closure_events),
        waiver_closure_event_ids=[event.id for event, _, _ in waiver_closure_events],
        waiver_closure_artifact_ids=[
            artifact.id
            for _, artifact, _ in waiver_closure_events
            if artifact is not None
        ],
        waiver_closure_receipt_sha256s=[
            event.receipt_sha256
            for event, _, _ in waiver_closure_events
            if event.receipt_sha256
        ],
        closed_waiver_artifact_ids=[
            UUID(
                str(
                    (
                        (event.event_payload_json or {}).get(
                            "claim_support_replay_alert_fixture_coverage_waiver_closure"
                        )
                        or {}
                    ).get("waiver_artifact_id")
                )
            )
            for event, _, _ in waiver_closure_events
            if (
                (
                    (event.event_payload_json or {}).get(
                        "claim_support_replay_alert_fixture_coverage_waiver_closure"
                    )
                    or {}
                ).get("waiver_artifact_id")
            )
        ],
        candidates=promoted_candidates,
    )


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
