# ruff: noqa: E501, F401
from __future__ import annotations

import uuid
from typing import Any
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
    SemanticGovernanceEvent,
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from app.services.evidence_claim_feedback_payloads import (
    claim_feedback_evidence_refs as _claim_feedback_evidence_refs,
)
from app.services.evidence_claim_feedback_payloads import (
    claim_feedback_retrieval_context as _claim_feedback_retrieval_context,
)
from app.services.evidence_claim_feedback_payloads import (
    search_request_result_spans_by_result_id as _search_request_result_spans_by_result_id,
)
from app.services.evidence_claim_feedback_payloads import (
    technical_report_claim_feedback_payloads as _technical_report_claim_feedback_payloads,
)
from app.services.evidence_claim_feedback_payloads import (
    technical_report_claim_feedback_status as _technical_report_claim_feedback_status,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
)
from app.services.evidence_provenance import TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND
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


def _claim_retrieval_feedback_payload(
    row: TechnicalReportClaimRetrievalFeedback,
    *,
    include_live_links: bool = True,
) -> dict[str, Any]:
    payload = {
        "feedback_id": row.id,
        "technical_report_verification_task_id": row.technical_report_verification_task_id,
        "claim_evidence_derivation_id": row.claim_evidence_derivation_id,
        "release_readiness_db_gate_id": row.release_readiness_db_gate_id,
        "claim_id": row.claim_id,
        "claim_text": row.claim_text,
        "support_verdict": row.support_verdict,
        "support_score": row.support_score,
        "feedback_status": row.feedback_status,
        "learning_label": row.learning_label,
        "hard_negative_kind": row.hard_negative_kind,
        "source_search_request_id": row.source_search_request_id,
        "search_request_result_id": row.search_request_result_id,
        "source_search_request_ids": row.source_search_request_ids_json or [],
        "source_search_request_result_ids": (
            row.source_search_request_result_ids_json or []
        ),
        "search_request_result_span_ids": row.search_request_result_span_ids_json or [],
        "retrieval_evidence_span_ids": row.retrieval_evidence_span_ids_json or [],
        "semantic_ontology_snapshot_ids": row.semantic_ontology_snapshot_ids_json or [],
        "semantic_graph_snapshot_ids": row.semantic_graph_snapshot_ids_json or [],
        "retrieval_reranker_artifact_ids": row.retrieval_reranker_artifact_ids_json or [],
        "search_harness_release_ids": row.search_harness_release_ids_json or [],
        "release_audit_bundle_ids": row.release_audit_bundle_ids_json or [],
        "release_validation_receipt_ids": row.release_validation_receipt_ids_json or [],
        "evidence_refs": row.evidence_refs_json or [],
        "retrieval_context": row.retrieval_context_json or {},
        "feedback_payload": row.feedback_payload_json or {},
        "feedback_payload_sha256": row.feedback_payload_sha256,
        "source_payload": row.source_payload_json or {},
        "source_payload_sha256": row.source_payload_sha256,
        "created_at": row.created_at,
    }
    if include_live_links:
        payload.update(
            {
                "evidence_manifest_id": row.evidence_manifest_id,
                "prov_export_artifact_id": row.prov_export_artifact_id,
                "semantic_governance_event_id": row.semantic_governance_event_id,
                "updated_at": row.updated_at,
            }
        )
    return payload


def _technical_report_claim_feedback_row_integrity(
    row: TechnicalReportClaimRetrievalFeedback,
    *,
    session: Session | None = None,
    require_live_links: bool = False,
) -> dict[str, Any]:
    stored_feedback_hash = str(payload_sha256(row.feedback_payload_json or {}))
    stored_source_hash = str(payload_sha256(row.source_payload_json or {}))
    source_payload_hash_matches = stored_source_hash == row.source_payload_sha256
    feedback_payload_hash_matches = stored_feedback_hash == row.feedback_payload_sha256
    feedback_source_hash = (row.feedback_payload_json or {}).get("source_payload_sha256")
    feedback_source_hash_matches = feedback_source_hash == row.source_payload_sha256
    source_payload = row.source_payload_json or {}
    source_payload_column_checks = {
        "claim_id_matches": source_payload.get("claim_id") == row.claim_id,
        "support_verdict_matches": source_payload.get("support_verdict") == row.support_verdict,
        "feedback_status_matches": source_payload.get("feedback_status") == row.feedback_status,
        "learning_label_matches": source_payload.get("learning_label") == row.learning_label,
        "hard_negative_kind_matches": (
            source_payload.get("hard_negative_kind") == row.hard_negative_kind
        ),
        "release_readiness_db_gate_id_matches": (
            source_payload.get("release_readiness_db_gate_id")
            == (str(row.release_readiness_db_gate_id) if row.release_readiness_db_gate_id else None)
        ),
        "source_search_request_ids_match": (
            _string_values(source_payload.get("source_search_request_ids") or [])
            == _string_values(row.source_search_request_ids_json or [])
        ),
        "source_search_request_result_ids_match": (
            _string_values(source_payload.get("source_search_request_result_ids") or [])
            == _string_values(row.source_search_request_result_ids_json or [])
        ),
        "search_request_result_span_ids_match": (
            _string_values(source_payload.get("search_request_result_span_ids") or [])
            == _string_values(row.search_request_result_span_ids_json or [])
        ),
        "retrieval_evidence_span_ids_match": (
            _string_values(source_payload.get("retrieval_evidence_span_ids") or [])
            == _string_values(row.retrieval_evidence_span_ids_json or [])
        ),
    }
    source_payload_columns_match = all(source_payload_column_checks.values())
    live_link_checks: dict[str, bool] = {}
    if require_live_links:
        live_link_checks = {
            "has_evidence_manifest_link": row.evidence_manifest_id is not None,
            "has_prov_export_artifact_link": row.prov_export_artifact_id is not None,
            "has_release_readiness_db_gate_link": row.release_readiness_db_gate_id is not None,
            "has_semantic_governance_event_link": row.semantic_governance_event_id is not None,
            "evidence_manifest_matches_feedback": False,
            "prov_export_artifact_matches_feedback": False,
            "release_readiness_db_gate_matches_feedback": False,
            "semantic_governance_event_matches_feedback": False,
        }
    if require_live_links and session is not None:
        if row.evidence_manifest_id is not None:
            manifest = session.get(EvidenceManifest, row.evidence_manifest_id)
            live_link_checks["evidence_manifest_matches_feedback"] = bool(
                manifest is not None
                and manifest.verification_task_id == row.technical_report_verification_task_id
            )
        if row.prov_export_artifact_id is not None:
            artifact = session.get(AgentTaskArtifact, row.prov_export_artifact_id)
            live_link_checks["prov_export_artifact_matches_feedback"] = bool(
                artifact is not None
                and artifact.task_id == row.technical_report_verification_task_id
                and artifact.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND
            )
        if row.release_readiness_db_gate_id is not None:
            gate = session.get(
                TechnicalReportReleaseReadinessDbGate,
                row.release_readiness_db_gate_id,
            )
            live_link_checks["release_readiness_db_gate_matches_feedback"] = bool(
                gate is not None
                and gate.technical_report_verification_task_id
                == row.technical_report_verification_task_id
                and gate.gate_payload_sha256
                == source_payload.get("release_readiness_db_gate_payload_sha256")
            )
        if row.semantic_governance_event_id is not None:
            event = session.get(SemanticGovernanceEvent, row.semantic_governance_event_id)
            event_payload = (event.event_payload_json if event is not None else None) or {}
            feedback_payload = event_payload.get("technical_report_claim_retrieval_feedback") or {}
            live_link_checks["semantic_governance_event_matches_feedback"] = bool(
                event is not None
                and event.event_kind == "technical_report_claim_retrieval_feedback_recorded"
                and event.subject_table == TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE
                and event.subject_id == row.id
                and event.task_id == row.technical_report_verification_task_id
                and event.evidence_manifest_id == row.evidence_manifest_id
                and event.agent_task_artifact_id == row.prov_export_artifact_id
                and event.receipt_sha256 == row.feedback_payload_sha256
                and feedback_payload.get("feedback_id") == str(row.id)
                and feedback_payload.get("claim_id") == row.claim_id
            )
    live_link_integrity_verified = all(live_link_checks.values()) if require_live_links else True
    core_hash_integrity_verified = bool(
        feedback_payload_hash_matches
        and source_payload_hash_matches
        and feedback_source_hash_matches
    )
    return {
        "schema_name": "technical_report_claim_retrieval_feedback_row_integrity",
        "schema_version": "1.0",
        "feedback_id": str(row.id),
        "claim_id": row.claim_id,
        "stored_feedback_payload_sha256": row.feedback_payload_sha256,
        "expected_feedback_payload_sha256": stored_feedback_hash,
        "stored_source_payload_sha256": row.source_payload_sha256,
        "expected_source_payload_sha256": stored_source_hash,
        "feedback_payload_hash_matches": feedback_payload_hash_matches,
        "source_payload_hash_matches": source_payload_hash_matches,
        "feedback_source_hash_matches": feedback_source_hash_matches,
        "source_payload_column_checks": source_payload_column_checks,
        "source_payload_columns_match": source_payload_columns_match,
        "live_link_checks": live_link_checks,
        "live_link_integrity_required": require_live_links,
        "live_link_integrity_verified": live_link_integrity_verified,
        "core_hash_integrity_verified": core_hash_integrity_verified,
        "has_search_request_ids": bool(row.source_search_request_ids_json),
        "has_search_request_result_ids": bool(row.source_search_request_result_ids_json),
        "complete": bool(
            core_hash_integrity_verified
            and source_payload_columns_match
            and live_link_integrity_verified
        ),
    }


def _technical_report_claim_feedback_integrity_payload(
    draft_payload: dict[str, Any],
    rows: list[TechnicalReportClaimRetrievalFeedback],
    *,
    session: Session | None = None,
    require_live_links: bool = False,
) -> dict[str, Any]:
    claim_ids = sorted(
        str(claim.get("claim_id") or "")
        for claim in draft_payload.get("claims") or []
        if claim.get("claim_id")
    )
    row_claim_ids = sorted(row.claim_id for row in rows)
    missing_claim_ids = sorted(set(claim_ids) - set(row_claim_ids))
    unexpected_claim_ids = sorted(set(row_claim_ids) - set(claim_ids))
    row_integrities = [
        _technical_report_claim_feedback_row_integrity(
            row,
            session=session,
            require_live_links=require_live_links,
        )
        for row in rows
    ]
    coverage_complete = bool(claim_ids) and not missing_claim_ids and not unexpected_claim_ids
    core_hash_integrity_verified = bool(rows) and all(
        row["core_hash_integrity_verified"] for row in row_integrities
    )
    source_payload_columns_match = bool(rows) and all(
        row["source_payload_columns_match"] for row in row_integrities
    )
    live_link_integrity_verified = bool(rows) and all(
        row["live_link_integrity_verified"] for row in row_integrities
    )
    integrity_verified = (
        core_hash_integrity_verified
        and source_payload_columns_match
        and live_link_integrity_verified
    )
    return {
        "schema_name": "technical_report_claim_retrieval_feedback_integrity",
        "schema_version": "1.0",
        "claim_count": len(claim_ids),
        "feedback_row_count": len(rows),
        "coverage_complete": coverage_complete,
        "integrity_verified": integrity_verified,
        "core_hash_integrity_verified": core_hash_integrity_verified,
        "source_payload_columns_match": source_payload_columns_match,
        "live_link_integrity_required": require_live_links,
        "live_link_integrity_verified": live_link_integrity_verified,
        "missing_claim_ids": missing_claim_ids,
        "unexpected_claim_ids": unexpected_claim_ids,
        "missing_claim_count": len(missing_claim_ids),
        "unexpected_claim_count": len(unexpected_claim_ids),
        "feedback_payload_hash_mismatch_count": sum(
            1 for row in row_integrities if not row["feedback_payload_hash_matches"]
        ),
        "source_payload_hash_mismatch_count": sum(
            1 for row in row_integrities if not row["source_payload_hash_matches"]
        ),
        "feedback_source_hash_mismatch_count": sum(
            1 for row in row_integrities if not row["feedback_source_hash_matches"]
        ),
        "source_payload_column_mismatch_count": sum(
            1 for row in row_integrities if not row["source_payload_columns_match"]
        ),
        "live_link_mismatch_count": sum(
            1 for row in row_integrities if not row["live_link_integrity_verified"]
        ),
        "status_counts": {
            status: sum(1 for row in rows if row.feedback_status == status)
            for status in sorted({row.feedback_status for row in rows})
        },
        "learning_label_counts": {
            label: sum(1 for row in rows if row.learning_label == label)
            for label in sorted({row.learning_label for row in rows})
        },
        "row_integrities": row_integrities,
        "complete": coverage_complete and integrity_verified,
    }


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


technical_report_claim_feedback_status = _technical_report_claim_feedback_status
technical_report_claim_feedback_payloads = _technical_report_claim_feedback_payloads
claim_retrieval_feedback_payload = _claim_retrieval_feedback_payload
technical_report_claim_feedback_row_integrity = _technical_report_claim_feedback_row_integrity
technical_report_claim_feedback_integrity_payload = (
    _technical_report_claim_feedback_integrity_payload
)
claim_retrieval_feedback_rows_for_verification_task = (
    _claim_retrieval_feedback_rows_for_verification_task
)
set_claim_feedback_append_only_link = _set_claim_feedback_append_only_link
