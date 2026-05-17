from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

import app.services.evidence_release_readiness as _release_readiness
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    AgentTaskArtifact,
    EvidenceManifest,
    SemanticGovernanceEvent,
    TechnicalReportReleaseReadinessDbGate,
)
from app.services.evidence_audit_views_context import (
    technical_report_context_pack_audit_for_verification_task,
)
from app.services.evidence_common import int_or_none as _int_or_none
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.services.evidence_constants import RELEASE_READINESS_DB_GATE_CHECK_KEY
from app.services.semantic_governance import (
    record_technical_report_release_readiness_db_gate_event,
)

_technical_report_readiness_db_gate_for_verification_task = (
    _release_readiness.technical_report_readiness_db_gate_for_verification_task
)


def ensure_technical_report_release_readiness_db_gate_governance_event(
    session: Session,
    row: TechnicalReportReleaseReadinessDbGate,
) -> TechnicalReportReleaseReadinessDbGate:
    if row.evidence_manifest_id is None or row.prov_export_artifact_id is None:
        return row
    if row.semantic_governance_event_id is not None:
        event = session.get(SemanticGovernanceEvent, row.semantic_governance_event_id)
        if (
            event is not None
            and event.event_kind == "technical_report_readiness_db_gate_recorded"
            and event.evidence_manifest_id == row.evidence_manifest_id
            and event.agent_task_artifact_id == row.prov_export_artifact_id
        ):
            return row
    event = record_technical_report_release_readiness_db_gate_event(session, gate=row)
    row.semantic_governance_event_id = event.id
    row.updated_at = utcnow()
    session.flush()
    return row


def persist_technical_report_release_readiness_db_gate(
    session: Session,
    *,
    verification_task_id: UUID,
    evidence_manifest: EvidenceManifest | None = None,
    prov_export_artifact: AgentTaskArtifact | None = None,
) -> TechnicalReportReleaseReadinessDbGate | None:
    row = _technical_report_readiness_db_gate_for_verification_task(
        session,
        verification_task_id,
    )
    if row is not None:
        changed = False
        if evidence_manifest is not None and row.evidence_manifest_id != evidence_manifest.id:
            row.evidence_manifest_id = evidence_manifest.id
            changed = True
        if (
            prov_export_artifact is not None
            and row.prov_export_artifact_id != prov_export_artifact.id
        ):
            row.prov_export_artifact_id = prov_export_artifact.id
            changed = True
        if changed:
            row.updated_at = utcnow()
            session.flush()
        return ensure_technical_report_release_readiness_db_gate_governance_event(
            session,
            row,
        )

    context_pack_audit = technical_report_context_pack_audit_for_verification_task(
        session,
        verification_task_id,
    )
    gate_payload = _json_payload(context_pack_audit.get("release_readiness_db_gate") or {})
    source_verification_id = _uuid_or_none_safe(gate_payload.get("verification_id"))
    if source_verification_id is None:
        return None

    now = utcnow()
    row = TechnicalReportReleaseReadinessDbGate(
        id=uuid.uuid4(),
        technical_report_verification_task_id=verification_task_id,
        source_verification_id=source_verification_id,
        source_verification_task_id=_uuid_or_none_safe(gate_payload.get("verification_task_id")),
        harness_task_id=_uuid_or_none_safe(context_pack_audit.get("harness_task_id")),
        evidence_manifest_id=evidence_manifest.id if evidence_manifest is not None else None,
        prov_export_artifact_id=(
            prov_export_artifact.id if prov_export_artifact is not None else None
        ),
        check_key=RELEASE_READINESS_DB_GATE_CHECK_KEY,
        passed=gate_payload.get("passed") is True,
        required=gate_payload.get("required") if gate_payload.get("required") is not None else None,
        coverage_complete=gate_payload.get("coverage_complete") is True,
        complete=gate_payload.get("complete") is True,
        source_search_request_count=_int_or_none(gate_payload.get("source_search_request_count"))
        or 0,
        verified_request_count=_int_or_none(gate_payload.get("verified_request_count")) or 0,
        failure_count=_int_or_none(gate_payload.get("failure_count")) or 0,
        source_search_request_ids_json=_string_values(
            gate_payload.get("source_search_request_ids") or []
        ),
        verified_request_ids_json=_string_values(gate_payload.get("verified_request_ids") or []),
        missing_expected_request_ids_json=_string_values(
            gate_payload.get("missing_expected_request_ids") or []
        ),
        unexpected_verified_request_ids_json=_string_values(
            gate_payload.get("unexpected_verified_request_ids") or []
        ),
        summary_json=_json_payload(gate_payload.get("summary") or {}),
        gate_payload_json=gate_payload,
        gate_payload_sha256=str(payload_sha256(gate_payload)),
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return ensure_technical_report_release_readiness_db_gate_governance_event(
        session,
        row,
    )
