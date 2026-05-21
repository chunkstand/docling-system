# ruff: noqa: E501, F401, I001
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.json_utils import json_object_payload as _json_payload
from app.db.public.agent_tasks import AgentTaskArtifact, AgentTaskVerification, KnowledgeOperatorRun
from app.db.public.audit_and_evidence import TechnicalReportReleaseReadinessDbGate
from app.services.evidence_common import int_or_none as _int_or_none
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_constants import (
    DOCUMENT_GENERATION_CONTEXT_PACK_ARTIFACT_KIND,
    DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_ARTIFACT_KIND,
    DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_OPERATOR,
    RELEASE_READINESS_DB_GATE_CHECK_KEY,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
)
from app.services.evidence_provenance import frozen_export_receipt as _frozen_export_receipt
from app.services.evidence_provenance import (
    prov_export_receipt_integrity as _base_prov_export_receipt_integrity,
)
from app.services.evidence_task_payloads import artifact_payload as _artifact_payload
from app.services.evidence_task_payloads import operator_run_summary as _operator_run_summary
from app.services.evidence_task_payloads import verification_payload as _verification_payload
from app.services.report_shared import (
    release_readiness_assessment_ready as _release_readiness_assessment_ready,
)

def _prov_export_receipt_integrity(payload: dict[str, Any] | None) -> dict[str, Any]:
    return _base_prov_export_receipt_integrity(payload, settings_provider=get_settings)

def _verification_check(row: AgentTaskVerification, check_key: str) -> dict[str, Any] | None:
    details = row.details_json or {}
    for check in details.get("checks") or []:
        if isinstance(check, dict) and check.get("check_key") == check_key:
            return dict(check)
    return None


def _verification_check_passed(row: AgentTaskVerification, check_key: str) -> bool:
    check = _verification_check(row, check_key)
    return check is not None and check.get("passed") is True


def _release_readiness_db_gate_payload(
    verification_rows: list[AgentTaskVerification],
    *,
    source_search_request_ids: list[str],
) -> dict[str, Any]:
    expected_request_ids = _string_values(source_search_request_ids)
    latest_row = verification_rows[-1] if verification_rows else None
    check = (
        _verification_check(latest_row, RELEASE_READINESS_DB_GATE_CHECK_KEY)
        if latest_row is not None
        else None
    )
    if latest_row is not None and check is not None:
        observed = check.get("observed")
        summary = dict(observed) if isinstance(observed, dict) else {}
        failure_count = _int_or_none(summary.get("failure_count")) or 0
        source_search_request_count = _int_or_none(summary.get("source_search_request_count")) or 0
        verified_request_count = _int_or_none(summary.get("verified_request_count")) or 0
        verified_request_ids = _string_values(summary.get("verified_request_ids") or [])
        missing_expected_request_ids = [
            request_id
            for request_id in expected_request_ids
            if request_id not in verified_request_ids
        ]
        unexpected_verified_request_ids = [
            request_id
            for request_id in verified_request_ids
            if request_id not in expected_request_ids
        ]
        coverage_complete = (
            source_search_request_count == len(expected_request_ids)
            and verified_request_count == len(expected_request_ids)
            and not missing_expected_request_ids
            and not unexpected_verified_request_ids
        )
        complete = (
            check.get("passed") is True
            and summary.get("complete") is True
            and failure_count == 0
            and coverage_complete
        )
        return {
            "schema_name": TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
            "schema_version": "1.0",
            "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
            "verification_id": str(latest_row.id),
            "verification_task_id": (
                str(latest_row.verification_task_id) if latest_row.verification_task_id else None
            ),
            "passed": check.get("passed") is True,
            "required": check.get("required"),
            "source_search_request_ids": expected_request_ids,
            "source_search_request_count": source_search_request_count,
            "verified_request_ids": verified_request_ids,
            "verified_request_count": verified_request_count,
            "failure_count": failure_count,
            "missing_expected_request_ids": missing_expected_request_ids,
            "unexpected_verified_request_ids": unexpected_verified_request_ids,
            "coverage_complete": coverage_complete,
            "summary": summary,
            "complete": complete,
        }
    missing_check = latest_row is not None and check is None
    return {
        "schema_name": TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
        "schema_version": "1.0",
        "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
        "verification_id": str(latest_row.id) if latest_row is not None else None,
        "verification_task_id": (
            str(latest_row.verification_task_id)
            if latest_row is not None and latest_row.verification_task_id
            else None
        ),
        "passed": False,
        "required": None,
        "missing_check": missing_check,
        "source_search_request_ids": expected_request_ids,
        "source_search_request_count": 0,
        "verified_request_ids": [],
        "verified_request_count": 0,
        "failure_count": 0,
        "missing_expected_request_ids": expected_request_ids,
        "unexpected_verified_request_ids": [],
        "coverage_complete": False,
        "summary": {},
        "complete": False,
    }


def _technical_report_readiness_db_gate_for_verification_task(
    session: Session,
    verification_task_id: UUID,
) -> TechnicalReportReleaseReadinessDbGate | None:
    return session.scalar(
        select(TechnicalReportReleaseReadinessDbGate)
        .where(
            TechnicalReportReleaseReadinessDbGate.technical_report_verification_task_id
            == verification_task_id
        )
        .order_by(TechnicalReportReleaseReadinessDbGate.created_at.asc())
        .limit(1)
    )


def _technical_report_release_readiness_db_gate_record_payload(
    row: TechnicalReportReleaseReadinessDbGate,
    *,
    include_links: bool,
    integrity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_name": "technical_report_release_readiness_db_gate_record",
        "schema_version": "1.0",
        "gate_id": str(row.id),
        "technical_report_verification_task_id": str(
            row.technical_report_verification_task_id
        ),
        "source_verification_id": str(row.source_verification_id),
        "source_verification_task_id": (
            str(row.source_verification_task_id) if row.source_verification_task_id else None
        ),
        "harness_task_id": str(row.harness_task_id) if row.harness_task_id else None,
        "check_key": row.check_key,
        "passed": row.passed,
        "required": row.required,
        "coverage_complete": row.coverage_complete,
        "complete": row.complete,
        "source_search_request_count": row.source_search_request_count,
        "verified_request_count": row.verified_request_count,
        "failure_count": row.failure_count,
        "source_search_request_ids": list(row.source_search_request_ids_json or []),
        "verified_request_ids": list(row.verified_request_ids_json or []),
        "missing_expected_request_ids": list(row.missing_expected_request_ids_json or []),
        "unexpected_verified_request_ids": list(row.unexpected_verified_request_ids_json or []),
        "summary": row.summary_json or {},
        "gate_payload_sha256": row.gate_payload_sha256,
        "integrity": integrity or {},
        "created_at": row.created_at,
    }
    if include_links:
        payload.update(
            {
                "evidence_manifest_id": (
                    str(row.evidence_manifest_id) if row.evidence_manifest_id else None
                ),
                "prov_export_artifact_id": (
                    str(row.prov_export_artifact_id) if row.prov_export_artifact_id else None
                ),
                "semantic_governance_event_id": (
                    str(row.semantic_governance_event_id)
                    if row.semantic_governance_event_id
                    else None
                ),
                "updated_at": row.updated_at,
            }
        )
    return _json_payload(payload)


def _technical_report_release_readiness_db_gate_row_integrity(
    row: TechnicalReportReleaseReadinessDbGate,
    *,
    current_gate_payload: dict[str, Any],
) -> dict[str, Any]:
    stored_gate_payload = _json_payload(row.gate_payload_json or {})
    current_gate_payload = _json_payload(current_gate_payload)
    stored_payload_sha256 = str(payload_sha256(stored_gate_payload))
    current_payload_sha256 = str(payload_sha256(current_gate_payload))
    source_search_request_ids = _string_values(
        stored_gate_payload.get("source_search_request_ids") or []
    )
    verified_request_ids = _string_values(stored_gate_payload.get("verified_request_ids") or [])
    missing_expected_request_ids = _string_values(
        stored_gate_payload.get("missing_expected_request_ids") or []
    )
    unexpected_verified_request_ids = _string_values(
        stored_gate_payload.get("unexpected_verified_request_ids") or []
    )
    row_source_search_request_ids = _string_values(row.source_search_request_ids_json or [])
    row_verified_request_ids = _string_values(row.verified_request_ids_json or [])
    row_missing_expected_request_ids = _string_values(
        row.missing_expected_request_ids_json or []
    )
    row_unexpected_verified_request_ids = _string_values(
        row.unexpected_verified_request_ids_json or []
    )
    checks = {
        "stored_payload_hash_matches": stored_payload_sha256 == row.gate_payload_sha256,
        "stored_payload_matches_current_gate": stored_gate_payload == current_gate_payload,
        "stored_payload_hash_matches_current_gate": (
            row.gate_payload_sha256 == current_payload_sha256
        ),
        "source_verification_id_matches": str(row.source_verification_id)
        == str(stored_gate_payload.get("verification_id") or ""),
        "source_verification_task_id_matches": (
            (str(row.source_verification_task_id) if row.source_verification_task_id else None)
            == stored_gate_payload.get("verification_task_id")
        ),
        "check_key_matches": (
            row.check_key == RELEASE_READINESS_DB_GATE_CHECK_KEY
            and stored_gate_payload.get("check_key") == row.check_key
        ),
        "status_fields_match_payload": (
            stored_gate_payload.get("passed") is row.passed
            and stored_gate_payload.get("required") == row.required
            and stored_gate_payload.get("coverage_complete") is row.coverage_complete
            and stored_gate_payload.get("complete") is row.complete
        ),
        "count_fields_match_payload": (
            (_int_or_none(stored_gate_payload.get("source_search_request_count")) or 0)
            == row.source_search_request_count
            and (_int_or_none(stored_gate_payload.get("verified_request_count")) or 0)
            == row.verified_request_count
            and (_int_or_none(stored_gate_payload.get("failure_count")) or 0)
            == row.failure_count
        ),
        "request_ids_match_payload": (
            source_search_request_ids == row_source_search_request_ids
            and verified_request_ids == row_verified_request_ids
            and missing_expected_request_ids == row_missing_expected_request_ids
            and unexpected_verified_request_ids == row_unexpected_verified_request_ids
        ),
        "request_counts_match_arrays": (
            row.source_search_request_count == len(row_source_search_request_ids)
            and row.verified_request_count == len(row_verified_request_ids)
        ),
        "summary_matches_payload": (
            _json_payload(stored_gate_payload.get("summary") or {})
            == _json_payload(row.summary_json or {})
        ),
        "complete_consistency": (
            not row.complete
            or (
                row.passed
                and row.coverage_complete
                and row.failure_count == 0
                and not row_missing_expected_request_ids
                and not row_unexpected_verified_request_ids
            )
        ),
    }
    return {
        "schema_name": "technical_report_release_readiness_db_gate_row_integrity",
        "schema_version": "1.0",
        "stored_payload_sha256": stored_payload_sha256,
        "recorded_payload_sha256": row.gate_payload_sha256,
        "current_gate_payload_sha256": current_payload_sha256,
        **checks,
        "complete": all(checks.values()),
    }


def _with_release_readiness_db_gate_record(
    context_pack_audit: dict[str, Any],
    row: TechnicalReportReleaseReadinessDbGate | None,
    *,
    include_links: bool,
) -> dict[str, Any]:
    result = _json_payload(context_pack_audit)
    integrity = dict(result.get("integrity") or {})
    if row is None:
        result["release_readiness_db_gate_record"] = None
        result["release_readiness_db_gate_record_integrity"] = {
            "schema_name": "technical_report_release_readiness_db_gate_row_integrity",
            "schema_version": "1.0",
            "complete": False,
            "missing_record": True,
        }
        integrity["has_persisted_release_readiness_db_gate"] = False
        integrity["persisted_release_readiness_db_gate_integrity_verified"] = False
        integrity["complete"] = False
        result["integrity"] = integrity
        return result

    current_gate_payload = dict(result.get("release_readiness_db_gate") or {})
    row_integrity = _technical_report_release_readiness_db_gate_row_integrity(
        row,
        current_gate_payload=current_gate_payload,
    )
    record_payload = _technical_report_release_readiness_db_gate_record_payload(
        row,
        include_links=include_links,
        integrity=row_integrity,
    )
    gate_payload = dict(current_gate_payload)
    gate_payload.update(
        {
            "gate_id": record_payload["gate_id"],
            "gate_payload_sha256": record_payload["gate_payload_sha256"],
            "persisted_table": TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
            "persisted": True,
        }
    )
    if include_links:
        gate_payload.update(
            {
                "evidence_manifest_id": record_payload.get("evidence_manifest_id"),
                "prov_export_artifact_id": record_payload.get("prov_export_artifact_id"),
                "semantic_governance_event_id": record_payload.get(
                    "semantic_governance_event_id"
                ),
            }
        )
    result["release_readiness_db_gate"] = gate_payload
    result["release_readiness_db_gate_record"] = record_payload
    result["release_readiness_db_gate_record_integrity"] = row_integrity
    integrity["has_persisted_release_readiness_db_gate"] = True
    integrity["persisted_release_readiness_db_gate_integrity_verified"] = (
        row_integrity["complete"] is True
    )
    integrity["complete"] = all(
        bool(value) for key, value in integrity.items() if key != "complete"
    )
    result["integrity"] = integrity
    return result


def _release_readiness_db_gate_trace_ref(
    context_pack_audit: dict[str, Any],
) -> dict[str, str] | None:
    record = context_pack_audit.get("release_readiness_db_gate_record")
    if isinstance(record, dict) and record.get("gate_id"):
        return {
            "table": TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
            "id": str(record["gate_id"]),
        }
    gate = context_pack_audit.get("release_readiness_db_gate")
    if isinstance(gate, dict) and gate.get("verification_id"):
        return {
            "table": TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
            "id": str(gate["verification_id"]),
        }
    return None


def _context_pack_sha256s_from_artifacts(
    context_pack_artifacts: list[AgentTaskArtifact],
    evaluation_artifacts: list[AgentTaskArtifact],
    verification_rows: list[AgentTaskVerification],
) -> list[str]:
    values: list[Any] = []
    for artifact in context_pack_artifacts:
        values.append((artifact.payload_json or {}).get("context_pack_sha256"))
    for artifact in evaluation_artifacts:
        values.append((artifact.payload_json or {}).get("context_pack_sha256"))
    for row in verification_rows:
        values.append((row.details_json or {}).get("context_pack_sha256"))
    return _string_values(values)


def _context_pack_audit_refs(payload: dict[str, Any]) -> dict[str, Any]:
    audit_refs = payload.get("audit_refs") or {}
    return audit_refs if isinstance(audit_refs, dict) else {}


def _release_readiness_ref_key(ref: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(ref.get("search_request_id") or ""),
        str(ref.get("search_harness_release_id") or ""),
        str(ref.get("assessment_id") or ref.get("selection_status") or ""),
    )


def _release_readiness_refs_from_context_pack_artifacts(
    context_pack_artifacts: list[AgentTaskArtifact],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for artifact in context_pack_artifacts:
        payload = artifact.payload_json or {}
        for ref in _context_pack_audit_refs(payload).get("release_readiness_assessments") or []:
            if isinstance(ref, dict):
                refs.append(dict(ref))
    return list({_release_readiness_ref_key(ref): ref for ref in refs}.values())


def _source_search_request_ids_from_context_pack_artifacts(
    context_pack_artifacts: list[AgentTaskArtifact],
) -> list[str]:
    values: list[Any] = []
    for artifact in context_pack_artifacts:
        payload = artifact.payload_json or {}
        values.extend(_context_pack_audit_refs(payload).get("source_search_request_ids") or [])
    return _string_values(values)


def _release_readiness_audit_summary(
    *,
    source_search_request_ids: list[str],
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    refs_by_request_id = {
        str(ref.get("search_request_id")): ref for ref in refs if ref.get("search_request_id")
    }
    ready_request_ids = {
        request_id
        for request_id, ref in refs_by_request_id.items()
        if _release_readiness_assessment_ready(ref)
    }
    missing_source_search_request_ids = [
        request_id
        for request_id in source_search_request_ids
        if request_id not in ready_request_ids
    ]
    failed_refs = [
        ref
        for ref in refs
        if ref.get("search_request_id") in source_search_request_ids
        and not _release_readiness_assessment_ready(ref)
    ]
    failed_selection_status_counts: dict[str, int] = {}
    for ref in failed_refs:
        status = str(ref.get("selection_status") or "unknown")
        failed_selection_status_counts[status] = failed_selection_status_counts.get(status, 0) + 1
    return {
        "source_search_request_count": len(source_search_request_ids),
        "readiness_assessment_ref_count": len(refs),
        "ready_assessment_ref_count": len(ready_request_ids),
        "failed_ref_count": len(failed_refs),
        "missing_source_search_request_ids": missing_source_search_request_ids,
        "failed_selection_status_counts": failed_selection_status_counts,
    }


def _technical_report_context_pack_audit_payload(
    *,
    harness_task_id: UUID | None,
    eval_task_ids: list[UUID],
    artifacts: list[AgentTaskArtifact],
    verification_rows: list[AgentTaskVerification],
    operator_runs: list[KnowledgeOperatorRun],
) -> dict[str, Any]:
    eval_task_id_set = set(eval_task_ids)
    context_pack_artifacts = [
        row
        for row in artifacts
        if row.artifact_kind == DOCUMENT_GENERATION_CONTEXT_PACK_ARTIFACT_KIND
    ]
    evaluation_artifacts = [
        row
        for row in artifacts
        if row.artifact_kind == DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_ARTIFACT_KIND
    ]
    context_pack_operator_runs = [
        row
        for row in operator_runs
        if row.operator_name == DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_OPERATOR
        or (row.agent_task_id is not None and row.agent_task_id in eval_task_id_set)
    ]
    sha256s = _context_pack_sha256s_from_artifacts(
        context_pack_artifacts,
        evaluation_artifacts,
        verification_rows,
    )
    release_readiness_assessments = _release_readiness_refs_from_context_pack_artifacts(
        context_pack_artifacts
    )
    source_search_request_ids = _source_search_request_ids_from_context_pack_artifacts(
        context_pack_artifacts
    )
    release_readiness_summary = _release_readiness_audit_summary(
        source_search_request_ids=source_search_request_ids,
        refs=release_readiness_assessments,
    )
    release_readiness_db_gate = _release_readiness_db_gate_payload(
        verification_rows,
        source_search_request_ids=source_search_request_ids,
    )
    release_readiness_db_summary = dict(release_readiness_db_gate.get("summary") or {})
    latest_verification = verification_rows[-1] if verification_rows else None
    integrity = {
        "has_context_pack_artifact": bool(context_pack_artifacts),
        "has_context_pack_evaluation_task": bool(eval_task_ids),
        "has_context_pack_evaluation_artifact": bool(evaluation_artifacts),
        "has_context_pack_verifier_record": bool(verification_rows),
        "has_context_pack_evaluation_operator_run": bool(context_pack_operator_runs),
        "latest_context_pack_evaluation_passed": (
            latest_verification.outcome == "passed" if latest_verification is not None else False
        ),
        "context_pack_hash_verified": any(
            _verification_check_passed(row, "context_pack_hash_integrity")
            for row in verification_rows
        ),
        "context_pack_sha256_consistent": bool(sha256s) and len(sha256s) == 1,
        "has_release_readiness_assessments": bool(release_readiness_assessments),
        "release_readiness_assessments_cover_source_requests": (
            not source_search_request_ids
            or not release_readiness_summary["missing_source_search_request_ids"]
        ),
        "release_readiness_assessments_ready": (
            release_readiness_summary["failed_ref_count"] == 0
            and (
                not source_search_request_ids
                or release_readiness_summary["ready_assessment_ref_count"]
                == len(source_search_request_ids)
            )
        ),
        "release_readiness_assessment_integrity_verified": release_readiness_db_gate["passed"]
        is True,
        "release_readiness_db_gate_verified": release_readiness_db_gate["passed"] is True,
        "release_readiness_db_gate_complete": release_readiness_db_gate["complete"] is True,
        "release_readiness_db_covers_source_requests": release_readiness_db_gate[
            "coverage_complete"
        ]
        is True,
    }
    integrity["complete"] = all(integrity.values())
    return {
        "schema_name": "technical_report_context_pack_audit",
        "schema_version": "1.0",
        "harness_task_id": str(harness_task_id) if harness_task_id is not None else None,
        "evaluation_task_ids": _string_values(eval_task_ids),
        "context_pack_sha256s": sha256s,
        "context_pack_artifacts": [_artifact_payload(row) for row in context_pack_artifacts],
        "evaluation_artifacts": [_artifact_payload(row) for row in evaluation_artifacts],
        "verifications": [_verification_payload(row) for row in verification_rows],
        "operator_runs": [_operator_run_summary(row) for row in context_pack_operator_runs],
        "release_readiness_assessments": release_readiness_assessments,
        "release_readiness_summary": release_readiness_summary,
        "release_readiness_db_gate": release_readiness_db_gate,
        "release_readiness_db_summary": release_readiness_db_summary,
        "integrity": integrity,
    }

prov_export_receipt_integrity = _prov_export_receipt_integrity
verification_check = _verification_check
verification_check_passed = _verification_check_passed
release_readiness_db_gate_payload = _release_readiness_db_gate_payload
technical_report_readiness_db_gate_for_verification_task = _technical_report_readiness_db_gate_for_verification_task
technical_report_release_readiness_db_gate_record_payload = _technical_report_release_readiness_db_gate_record_payload
technical_report_release_readiness_db_gate_row_integrity = _technical_report_release_readiness_db_gate_row_integrity
with_release_readiness_db_gate_record = _with_release_readiness_db_gate_record
release_readiness_db_gate_trace_ref = _release_readiness_db_gate_trace_ref
context_pack_sha256s_from_artifacts = _context_pack_sha256s_from_artifacts
context_pack_audit_refs = _context_pack_audit_refs
release_readiness_ref_key = _release_readiness_ref_key
release_readiness_refs_from_context_pack_artifacts = _release_readiness_refs_from_context_pack_artifacts
source_search_request_ids_from_context_pack_artifacts = _source_search_request_ids_from_context_pack_artifacts
release_readiness_audit_summary = _release_readiness_audit_summary
technical_report_context_pack_audit_payload = _technical_report_context_pack_audit_payload
