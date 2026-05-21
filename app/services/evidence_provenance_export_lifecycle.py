# ruff: noqa: I001
from __future__ import annotations

import json
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.public.agent_tasks import (
    AgentTask, AgentTaskArtifact, AgentTaskArtifactImmutabilityEvent,
)
from app.db.public.audit_and_evidence import EvidencePackageExport
from app.services.evidence_audit_views import (
    persist_technical_report_release_readiness_db_gate,
)
from app.services.evidence_claim_feedback import (
    persist_technical_report_claim_retrieval_feedback_ledger,
)
from app.services.evidence_claim_support_impacts import (
    change_impact_payload as _change_impact_payload,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_manifests import (
    existing_evidence_manifest as _existing_evidence_manifest,
)
from app.services.evidence_provenance import (
    TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
    TECHNICAL_REPORT_PROV_EXPORT_FILENAME,
    frozen_export_receipt as _frozen_export_receipt,
    frozen_export_sha256 as _frozen_export_sha256,
    frozen_prov_export_payload as _base_frozen_prov_export_payload,
)
from app.services.evidence_provenance_export_graph_core import (
    build_agent_task_provenance_export,
)
from app.services.evidence_technical_report_context import (
    draft_task_id_for_audit as _draft_task_id_for_audit,
    technical_report_upstream_task_ids as _technical_report_upstream_task_ids,
    verification_task_id_for_manifest as _verification_task_id_for_manifest,
)
from app.services.semantic_governance import (
    record_technical_report_prov_export_governance_event,
)
from app.services.storage import StorageService


def existing_prov_export_artifact(
    session: Session,
    task_id: UUID,
) -> AgentTaskArtifact | None:
    return session.scalar(
        select(AgentTaskArtifact)
        .where(
            AgentTaskArtifact.task_id == task_id,
            AgentTaskArtifact.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        )
        .order_by(AgentTaskArtifact.created_at.asc())
        .limit(1)
    )


def record_prov_export_supersession_attempt(
    session: Session,
    *,
    existing: AgentTaskArtifact,
    attempted_prov_export: dict[str, Any],
) -> AgentTaskArtifactImmutabilityEvent | None:
    existing_payload = _json_payload(existing.payload_json or {})
    existing_sha256 = _frozen_export_sha256(existing_payload)
    attempted_sha256 = payload_sha256(attempted_prov_export)
    if existing_sha256 == attempted_sha256:
        return None

    duplicate = session.scalar(
        select(AgentTaskArtifactImmutabilityEvent)
        .where(
            AgentTaskArtifactImmutabilityEvent.artifact_id == existing.id,
            AgentTaskArtifactImmutabilityEvent.event_kind == "supersession_attempt",
            AgentTaskArtifactImmutabilityEvent.frozen_payload_sha256 == existing_sha256,
            AgentTaskArtifactImmutabilityEvent.attempted_payload_sha256 == attempted_sha256,
        )
        .limit(1)
    )
    if duplicate is not None:
        return duplicate

    existing_receipt = _frozen_export_receipt(existing_payload)
    event = AgentTaskArtifactImmutabilityEvent(
        artifact_id=existing.id,
        task_id=existing.task_id,
        event_kind="supersession_attempt",
        mutation_operation="FREEZE_REUSE",
        frozen_artifact_kind=existing.artifact_kind,
        attempted_artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        frozen_storage_path=existing.storage_path,
        attempted_storage_path=existing.storage_path,
        frozen_payload_sha256=existing_sha256,
        attempted_payload_sha256=attempted_sha256,
        details_json={
            "reason": "A new PROV export was computed after the frozen artifact already existed.",
            "action": "kept_existing_frozen_artifact",
            "existing_receipt_sha256": existing_receipt.get("receipt_sha256"),
            "attempted_prov_hash_basis_sha256": (
                attempted_prov_export.get("prov_integrity") or {}
            ).get("prov_sha256"),
        },
        created_at=utcnow(),
    )
    session.add(event)
    session.flush()
    return event


def technical_report_change_impact_for_governance(
    session: Session,
    verification_task_id: UUID,
) -> dict[str, Any]:
    verification_task = session.get(AgentTask, verification_task_id)
    if verification_task is None:
        return {
            "impacted": True,
            "impact_count": 1,
            "impacts": [
                {
                    "impact_type": "verification_task_missing",
                    "verification_task_id": str(verification_task_id),
                }
            ],
        }

    draft_task_id = _draft_task_id_for_audit(verification_task)
    draft_task = session.get(AgentTask, draft_task_id)
    draft_payload = (
        ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
        if draft_task is not None
        else {}
    )
    related_task_ids = list(
        dict.fromkeys(
            [
                draft_task_id,
                *_technical_report_upstream_task_ids(session, draft_payload),
                verification_task_id,
            ]
        )
    )
    exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(EvidencePackageExport.agent_task_id.in_(related_task_ids))
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    return _change_impact_payload(session, exports)


def persist_agent_task_provenance_export(
    session: Session,
    *,
    task_id: UUID,
    storage_service: StorageService | None = None,
) -> AgentTaskArtifact:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")

    verification_task_id = _verification_task_id_for_manifest(session, task)
    governance_change_impact = technical_report_change_impact_for_governance(
        session,
        verification_task_id,
    )
    existing = existing_prov_export_artifact(session, verification_task_id)
    if existing is not None:
        record_prov_export_supersession_attempt(
            session,
            existing=existing,
            attempted_prov_export=build_agent_task_provenance_export(
                session,
                verification_task_id,
            ),
        )
        _sync_prov_export_governance(
            session,
            verification_task_id=verification_task_id,
            artifact=existing,
            governance_change_impact=governance_change_impact,
        )
        return existing

    artifact_id = uuid.uuid4()
    created_at = utcnow()
    artifact_path = (
        storage_service.get_agent_task_dir(verification_task_id)
        / TECHNICAL_REPORT_PROV_EXPORT_FILENAME
        if storage_service is not None
        else None
    )
    storage_path = str(artifact_path) if artifact_path is not None else None
    prov_export = build_agent_task_provenance_export(session, verification_task_id)
    frozen_payload = _base_frozen_prov_export_payload(
        prov_export,
        artifact_id=artifact_id,
        task_id=verification_task_id,
        created_at=created_at,
        storage_path=storage_path,
        settings_provider=get_settings,
    )
    if artifact_path is not None:
        artifact_path.write_text(json.dumps(frozen_payload, indent=2, sort_keys=True))

    row = AgentTaskArtifact(
        id=artifact_id,
        task_id=verification_task_id,
        artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        storage_path=storage_path,
        payload_json=frozen_payload,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    _sync_prov_export_governance(
        session,
        verification_task_id=verification_task_id,
        artifact=row,
        governance_change_impact=governance_change_impact,
    )
    return row


def get_agent_task_provenance_export(
    session: Session,
    task_id: UUID,
    *,
    storage_service: StorageService | None = None,
) -> dict[str, Any]:
    artifact = persist_agent_task_provenance_export(
        session,
        task_id=task_id,
        storage_service=storage_service,
    )
    return _json_payload(artifact.payload_json or {})


def _sync_prov_export_governance(
    session: Session,
    *,
    verification_task_id: UUID,
    artifact: AgentTaskArtifact,
    governance_change_impact: dict[str, Any],
) -> None:
    evidence_manifest = _existing_evidence_manifest(session, verification_task_id)
    persist_technical_report_release_readiness_db_gate(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=evidence_manifest,
        prov_export_artifact=artifact,
    )
    persist_technical_report_claim_retrieval_feedback_ledger(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=evidence_manifest,
        prov_export_artifact=artifact,
        ensure_governance=True,
    )
    record_technical_report_prov_export_governance_event(
        session,
        artifact=artifact,
        evidence_manifest=evidence_manifest,
        change_impact=governance_change_impact,
    )
