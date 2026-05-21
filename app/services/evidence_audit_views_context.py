from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskVerification,
    KnowledgeOperatorRun,
)
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.services.evidence_release_readiness import (
    technical_report_context_pack_audit_payload as _technical_report_context_pack_audit_payload,
)
from app.services.evidence_technical_report_context import (
    context_pack_eval_task_ids_for_harness as _context_pack_eval_task_ids_for_harness,
)
from app.services.evidence_technical_report_context import (
    context_pack_verification_rows as _context_pack_verification_rows,
)
from app.services.evidence_technical_report_context import (
    draft_task_id_for_audit as _draft_task_id_for_audit,
)
from app.services.evidence_technical_report_context import (
    technical_report_upstream_task_ids as _technical_report_upstream_task_ids,
)


def technical_report_audit_inputs_for_task(
    session: Session,
    task: AgentTask,
) -> dict[str, Any]:
    draft_task_id = _draft_task_id_for_audit(task)
    draft_task = session.get(AgentTask, draft_task_id)
    if draft_task is None:
        raise ValueError(f"Draft task '{draft_task_id}' was not found.")

    verification_task = task if task.task_type == "verify_technical_report" else None
    verification_row = None
    if verification_task is not None:
        verification_row = session.scalar(
            select(AgentTaskVerification).where(
                AgentTaskVerification.verification_task_id == verification_task.id
            )
        )

    draft_payload = ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
    related_task_ids = [
        draft_task.id,
        *_technical_report_upstream_task_ids(session, draft_payload),
    ]
    if verification_task is not None:
        related_task_ids.append(verification_task.id)
    related_task_ids = list(dict.fromkeys(related_task_ids))

    artifacts = list(
        session.scalars(
            select(AgentTaskArtifact)
            .where(AgentTaskArtifact.task_id.in_(related_task_ids))
            .order_by(AgentTaskArtifact.created_at.asc())
        )
    )
    operator_runs = list(
        session.scalars(
            select(KnowledgeOperatorRun)
            .where(KnowledgeOperatorRun.agent_task_id.in_(related_task_ids))
            .order_by(KnowledgeOperatorRun.created_at.asc())
        )
    )

    harness_task_id = _uuid_or_none_safe(draft_payload.get("harness_task_id"))
    context_pack_eval_task_ids = (
        _context_pack_eval_task_ids_for_harness(session, harness_task_id)
        if harness_task_id is not None
        else []
    )
    context_pack_verifications = _context_pack_verification_rows(
        session,
        harness_task_id=harness_task_id,
        eval_task_ids=context_pack_eval_task_ids,
    )
    return {
        "draft_task": draft_task,
        "verification_task": verification_task,
        "verification_row": verification_row,
        "draft_payload": draft_payload,
        "related_task_ids": related_task_ids,
        "artifacts": artifacts,
        "operator_runs": operator_runs,
        "harness_task_id": harness_task_id,
        "context_pack_eval_task_ids": context_pack_eval_task_ids,
        "context_pack_verifications": context_pack_verifications,
    }


def technical_report_context_pack_audit_for_verification_task(
    session: Session,
    verification_task_id: UUID,
) -> dict[str, Any]:
    verification_task = session.get(AgentTask, verification_task_id)
    if verification_task is None:
        raise ValueError(f"Agent task '{verification_task_id}' was not found.")

    audit_inputs = technical_report_audit_inputs_for_task(session, verification_task)
    return _technical_report_context_pack_audit_payload(
        harness_task_id=audit_inputs["harness_task_id"],
        eval_task_ids=audit_inputs["context_pack_eval_task_ids"],
        artifacts=audit_inputs["artifacts"],
        verification_rows=audit_inputs["context_pack_verifications"],
        operator_runs=audit_inputs["operator_runs"],
    )
