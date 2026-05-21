# ruff: noqa: F401, I001
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask, AgentTaskDependency, AgentTaskVerification
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.services.evidence_constants import DOCUMENT_GENERATION_CONTEXT_PACK_GATE

def _passed_technical_report_verification(
    session: Session,
    verification_task_id: UUID,
) -> AgentTaskVerification | None:
    return session.scalar(
        select(AgentTaskVerification)
        .where(
            AgentTaskVerification.verification_task_id == verification_task_id,
            AgentTaskVerification.verifier_type == "technical_report_gate",
            AgentTaskVerification.outcome == "passed",
        )
        .order_by(AgentTaskVerification.created_at.desc())
    )


def _latest_passed_technical_report_verification_task_id(
    session: Session,
    draft_task_id: UUID,
) -> UUID | None:
    row = session.scalar(
        select(AgentTaskVerification)
        .where(
            AgentTaskVerification.target_task_id == draft_task_id,
            AgentTaskVerification.verifier_type == "technical_report_gate",
            AgentTaskVerification.outcome == "passed",
        )
        .order_by(AgentTaskVerification.created_at.desc())
    )
    return row.verification_task_id if row is not None else None


def _verification_task_id_for_manifest(session: Session, task: AgentTask) -> UUID:
    if task.task_type == "verify_technical_report":
        if _passed_technical_report_verification(session, task.id) is None:
            raise ValueError(
                "Evidence manifests require a passed technical report verification task."
            )
        return task.id
    if task.task_type == "draft_technical_report":
        verification_task_id = _latest_passed_technical_report_verification_task_id(
            session,
            task.id,
        )
        if verification_task_id is None:
            raise ValueError(
                "Evidence manifests require a passed technical report verification task."
            )
        return verification_task_id
    raise ValueError("Evidence manifests are supported for technical report tasks only.")

def _context_pack_eval_task_ids_for_harness(session: Session, harness_task_id: UUID) -> list[UUID]:
    task_ids = list(
        session.scalars(
            select(AgentTask.id)
            .join(AgentTaskDependency, AgentTaskDependency.task_id == AgentTask.id)
            .where(
                AgentTask.task_type == "evaluate_document_generation_context_pack",
                AgentTaskDependency.depends_on_task_id == harness_task_id,
                AgentTaskDependency.dependency_kind == "target_task",
            )
            .order_by(AgentTask.created_at.asc(), AgentTask.id.asc())
        )
    )
    verification_task_ids = list(
        session.scalars(
            select(AgentTaskVerification.verification_task_id)
            .where(
                AgentTaskVerification.target_task_id == harness_task_id,
                AgentTaskVerification.verifier_type == DOCUMENT_GENERATION_CONTEXT_PACK_GATE,
                AgentTaskVerification.verification_task_id.is_not(None),
            )
            .order_by(AgentTaskVerification.created_at.asc(), AgentTaskVerification.id.asc())
        )
    )
    return list(
        dict.fromkeys(
            [
                *task_ids,
                *[task_id for task_id in verification_task_ids if task_id],
            ]
        )
    )


def _context_pack_verification_rows(
    session: Session,
    *,
    harness_task_id: UUID | None,
    eval_task_ids: list[UUID],
) -> list[AgentTaskVerification]:
    filters = [AgentTaskVerification.verifier_type == DOCUMENT_GENERATION_CONTEXT_PACK_GATE]
    if harness_task_id is not None and eval_task_ids:
        filters.append(
            or_(
                AgentTaskVerification.target_task_id == harness_task_id,
                AgentTaskVerification.verification_task_id.in_(eval_task_ids),
            )
        )
    elif harness_task_id is not None:
        filters.append(AgentTaskVerification.target_task_id == harness_task_id)
    elif eval_task_ids:
        filters.append(AgentTaskVerification.verification_task_id.in_(eval_task_ids))
    else:
        return []
    return list(
        session.scalars(
            select(AgentTaskVerification)
            .where(*filters)
            .order_by(AgentTaskVerification.created_at.asc(), AgentTaskVerification.id.asc())
        )
    )

def _draft_task_id_for_audit(task: AgentTask) -> UUID:
    if task.task_type == "draft_technical_report":
        return task.id
    if task.task_type == "verify_technical_report":
        payload = (task.result_json or {}).get("payload") or {}
        verification = payload.get("verification") or {}
        target_task_id = verification.get("target_task_id")
        if not target_task_id:
            target_task_id = (task.input_json or {}).get("target_task_id")
        if target_task_id:
            return UUID(str(target_task_id))
    raise ValueError("Audit bundles are currently supported for technical report tasks only.")


def _technical_report_upstream_task_ids(
    session: Session,
    draft_payload: dict[str, Any],
) -> list[UUID]:
    related_task_ids: list[UUID] = []
    harness_task_id = _uuid_or_none_safe(draft_payload.get("harness_task_id"))
    if harness_task_id is not None:
        related_task_ids.append(harness_task_id)
        related_task_ids.extend(_context_pack_eval_task_ids_for_harness(session, harness_task_id))
        harness_task = session.get(AgentTask, harness_task_id)
        harness_payload = (
            ((harness_task.result_json or {}).get("payload") or {}).get("harness", {})
            if harness_task is not None
            else {}
        )
        evidence_task_id = _uuid_or_none_safe(
            (harness_payload.get("workflow_state") or {}).get("evidence_task_id")
        )
        if evidence_task_id is not None:
            related_task_ids.append(evidence_task_id)
            evidence_task = session.get(AgentTask, evidence_task_id)
            evidence_payload = (
                ((evidence_task.result_json or {}).get("payload") or {}).get(
                    "evidence_bundle",
                    {},
                )
                if evidence_task is not None
                else {}
            )
            plan_task_id = _uuid_or_none_safe(evidence_payload.get("plan_task_id"))
            if plan_task_id is not None:
                related_task_ids.append(plan_task_id)
    return list(dict.fromkeys(related_task_ids))


passed_technical_report_verification = _passed_technical_report_verification
verification_task_id_for_manifest = _verification_task_id_for_manifest
context_pack_eval_task_ids_for_harness = _context_pack_eval_task_ids_for_harness
context_pack_verification_rows = _context_pack_verification_rows
draft_task_id_for_audit = _draft_task_id_for_audit
technical_report_upstream_task_ids = _technical_report_upstream_task_ids
