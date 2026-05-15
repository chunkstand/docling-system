# ruff: noqa: E501
from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    ClaimEvidenceDerivation,
    EvidenceManifest,
    EvidencePackageExport,
    TechnicalReportClaimRetrievalFeedback,
)
from app.services.evidence_claim_feedback_payloads import (
    technical_report_claim_feedback_payloads as _technical_report_claim_feedback_payloads,
)
from app.services.evidence_release_readiness import (
    technical_report_readiness_db_gate_for_verification_task as _technical_report_readiness_db_gate_for_verification_task,
)
from app.services.evidence_technical_report_context import (
    draft_task_id_for_audit as _draft_task_id_for_audit,
)
from app.services.evidence_technical_report_context import (
    passed_technical_report_verification as _passed_technical_report_verification,
)
from app.services.evidence_technical_report_context import (
    technical_report_upstream_task_ids as _technical_report_upstream_task_ids,
)
from app.services.semantic_governance import (
    record_technical_report_claim_retrieval_feedback_event,
)


def _claim_retrieval_feedback_rows_for_verification_task(
    session: Session,
    verification_task_id: UUID,
) -> list[TechnicalReportClaimRetrievalFeedback]:
    return list(
        session.scalars(
            select(TechnicalReportClaimRetrievalFeedback)
            .where(
                TechnicalReportClaimRetrievalFeedback.technical_report_verification_task_id
                == verification_task_id
            )
            .order_by(TechnicalReportClaimRetrievalFeedback.claim_id.asc())
        )
    )


def _set_claim_feedback_append_only_link(
    row: TechnicalReportClaimRetrievalFeedback,
    *,
    field_name: str,
    value: UUID | None,
) -> bool:
    if value is None:
        return False
    current_value = getattr(row, field_name)
    if current_value is not None and current_value != value:
        raise ValueError(
            "Technical report claim retrieval feedback live links are append-only: "
            f"{field_name} for feedback row '{row.id}' is already set."
        )
    if current_value == value:
        return False
    setattr(row, field_name, value)
    return True


def persist_technical_report_claim_retrieval_feedback_ledger(
    session: Session,
    *,
    verification_task_id: UUID,
    evidence_manifest: EvidenceManifest | None = None,
    prov_export_artifact: AgentTaskArtifact | None = None,
    ensure_governance: bool = False,
) -> list[TechnicalReportClaimRetrievalFeedback]:
    verification_task = session.get(AgentTask, verification_task_id)
    if verification_task is None:
        raise ValueError(f"Agent task '{verification_task_id}' was not found.")
    if _passed_technical_report_verification(session, verification_task_id) is None:
        raise ValueError(
            "Claim retrieval feedback requires a passed technical report verification task."
        )

    draft_task_id = _draft_task_id_for_audit(verification_task)
    draft_task = session.get(AgentTask, draft_task_id)
    if draft_task is None:
        raise ValueError(f"Draft task '{draft_task_id}' was not found.")
    draft_payload = ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
    related_task_ids = [
        draft_task.id,
        *_technical_report_upstream_task_ids(session, draft_payload),
        verification_task_id,
    ]
    related_task_ids = list(dict.fromkeys(related_task_ids))
    report_exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(
                EvidencePackageExport.agent_task_id.in_(related_task_ids),
                EvidencePackageExport.package_kind == "technical_report_claims",
            )
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    report_export_ids = [row.id for row in report_exports]
    derivations = (
        list(
            session.scalars(
                select(ClaimEvidenceDerivation)
                .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(report_export_ids))
                .order_by(ClaimEvidenceDerivation.claim_id.asc())
            )
        )
        if report_export_ids
        else []
    )
    release_gate = _technical_report_readiness_db_gate_for_verification_task(
        session,
        verification_task_id,
    )
    desired_rows = _technical_report_claim_feedback_payloads(
        session,
        verification_task_id=verification_task_id,
        draft_payload=draft_payload,
        derivations=derivations,
        release_readiness_db_gate=release_gate,
    )
    existing_by_claim_id = {
        row.claim_id: row
        for row in _claim_retrieval_feedback_rows_for_verification_task(
            session,
            verification_task_id,
        )
    }
    now = utcnow()
    for desired in desired_rows:
        existing = existing_by_claim_id.get(desired["claim_id"])
        if existing is not None:
            if (
                existing.feedback_payload_sha256 != desired["feedback_payload_sha256"]
                or existing.source_payload_sha256 != desired["source_payload_sha256"]
            ):
                raise ValueError(
                    "Existing claim retrieval feedback row does not match the "
                    f"current verified claim payload: {desired['claim_id']}"
                )
            changed_links = [
                _set_claim_feedback_append_only_link(
                    existing,
                    field_name="evidence_manifest_id",
                    value=evidence_manifest.id if evidence_manifest is not None else None,
                ),
                _set_claim_feedback_append_only_link(
                    existing,
                    field_name="prov_export_artifact_id",
                    value=prov_export_artifact.id if prov_export_artifact is not None else None,
                ),
                _set_claim_feedback_append_only_link(
                    existing,
                    field_name="release_readiness_db_gate_id",
                    value=release_gate.id if release_gate is not None else None,
                ),
            ]
            changed = any(changed_links)
            if changed:
                existing.updated_at = now
            continue

        row = TechnicalReportClaimRetrievalFeedback(
            id=uuid.uuid4(),
            technical_report_verification_task_id=verification_task_id,
            evidence_manifest_id=(
                evidence_manifest.id if evidence_manifest is not None else None
            ),
            prov_export_artifact_id=(
                prov_export_artifact.id if prov_export_artifact is not None else None
            ),
            release_readiness_db_gate_id=release_gate.id if release_gate is not None else None,
            created_at=now,
            updated_at=now,
            **desired,
        )
        session.add(row)
        existing_by_claim_id[row.claim_id] = row
    session.flush()

    rows = _claim_retrieval_feedback_rows_for_verification_task(
        session,
        verification_task_id,
    )
    if ensure_governance:
        for row in rows:
            if row.semantic_governance_event_id is not None:
                continue
            event = record_technical_report_claim_retrieval_feedback_event(
                session,
                feedback=row,
            )
            row.semantic_governance_event_id = event.id
            row.updated_at = utcnow()
        session.flush()
    return rows


claim_retrieval_feedback_rows_for_verification_task = (
    _claim_retrieval_feedback_rows_for_verification_task
)
set_claim_feedback_append_only_link = _set_claim_feedback_append_only_link
