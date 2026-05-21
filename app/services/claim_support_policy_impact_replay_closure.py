from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import compact_strings as _string_list
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskStatus, AgentTaskVerification
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.semantic_memory import SemanticGovernanceEvent, SemanticGovernanceEventKind
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_policy_impact_replay import (
    CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_ARTIFACT_KIND,
    CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_FILENAME,
    CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_RECEIPT_SCHEMA,
    CLAIM_SUPPORT_IMPACT_REPLAY_CLOSURE_SCHEMA,
    REPLAY_ACTIVE_STATUSES,
    REPLAY_CLOSURE_HASH_FIELD,
    REPLAY_PLAN_HASH_FIELD,
    replay_conflict,
    replay_response,
    verify_replay_closure_integrity,
    verify_replay_plan_integrity,
    verify_terminal_replay_closure_integrity,
)
from app.services.claim_support_policy_impact_views import (
    REPLAY_OPEN_STATUSES,
    REPLAY_TERMINAL_FAILURE_STATUSES,
    get_impact_row,
    uuid_list,
)
from app.services.evidence import payload_sha256
from app.services.semantic_governance import (
    active_semantic_basis,
    record_semantic_governance_event,
)
from app.services.storage import StorageService


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
    verify_terminal_replay_closure_integrity(row)
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
            SemanticGovernanceEvent.deduplication_key == deduplication_key
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


def refresh_claim_support_policy_change_impact_replay_status(
    session: Session,
    change_impact_id: UUID,
    *,
    storage_service: StorageService | None = None,
    commit: bool = True,
):
    row = get_impact_row(session, change_impact_id, for_update=True)
    verify_replay_plan_integrity(row)
    verify_replay_closure_integrity(row)
    now = utcnow()
    if row.replay_status in {"closed", "no_action_required"} and row.replay_closure_json:
        verify_terminal_replay_closure_integrity(row)
        _record_replay_closure_governance_event(session, row, storage_service=storage_service)
        session.commit() if commit else session.flush()
        return replay_response(row)
    if row.replay_status == "closed":
        raise replay_conflict(
            row.id,
            "claim_support_impact_replay_terminal_closure_missing",
            "Closed claim support impact replay rows must include a closure receipt.",
            replay_status=row.replay_status,
        )
    if row.replay_status == "no_action_required" and row.replay_recommended_count > 0:
        raise replay_conflict(
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
        return replay_response(row)

    replay_task_ids = uuid_list(row.replay_task_ids_json)
    if not replay_task_ids:
        row.replay_status = "pending"
        row.replay_status_updated_at = now
        row.replay_closed_at = None
        row.replay_closure_json = {}
        row.replay_closure_sha256 = None
        session.add(row)
        session.commit() if commit else session.flush()
        return replay_response(row)

    task_rows = (
        session.execute(select(AgentTask).where(AgentTask.id.in_(replay_task_ids)))
        .scalars()
        .all()
    )
    tasks_by_id = {task.id: task for task in task_rows}
    plan_tasks = list((row.replay_task_plan_json or {}).get("tasks") or [])
    if not plan_tasks:
        raise replay_conflict(
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
        raise replay_conflict(
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
    return replay_response(row)


def refresh_claim_support_policy_change_impacts_for_replay_task(
    session: Session,
    task_id: UUID,
    *,
    storage_service: StorageService | None = None,
    commit: bool = True,
):
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
