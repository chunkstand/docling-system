from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import unique_strings as _unique_strings
from app.core.coercion import unique_uuids as _unique_uuids
from app.db.public.audit_and_evidence import AuditBundleExport, AuditBundleValidationReceipt
from app.db.public.retrieval import (
    SearchHarnessRelease,
    SearchHarnessReleaseReadinessAssessment,
    SearchRequestRecord,
)
from app.services.search_release_gate import (
    search_harness_release_readiness_assessment_integrity,
)
from app.services.search_release_shared import (
    latest_audit_bundle_validation_receipt as _latest_release_validation_receipt,
)
from app.services.search_release_shared import (
    latest_release_readiness_assessment as _latest_release_readiness_assessment,
)


def _latest_passed_release_for_search_request(
    session: Session,
    request_row: SearchRequestRecord,
) -> SearchHarnessRelease | None:
    harness_name = str(request_row.harness_name or "").strip()
    if not harness_name:
        return None
    return session.scalar(
        select(SearchHarnessRelease)
        .where(
            SearchHarnessRelease.candidate_harness_name == harness_name,
            SearchHarnessRelease.outcome == "passed",
            SearchHarnessRelease.created_at <= request_row.created_at,
        )
        .order_by(SearchHarnessRelease.created_at.desc(), SearchHarnessRelease.id.asc())
        .limit(1)
    )


def _latest_completed_release_audit_bundle(
    session: Session,
    release_id: UUID,
) -> AuditBundleExport | None:
    return session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.search_harness_release_id == release_id,
            AuditBundleExport.bundle_kind == "search_harness_release_provenance",
            AuditBundleExport.export_status == "completed",
        )
        .order_by(AuditBundleExport.created_at.desc(), AuditBundleExport.id.asc())
        .limit(1)
    )


def _release_readiness_assessment_selection_status(
    *,
    release: SearchHarnessRelease | None,
    assessment: SearchHarnessReleaseReadinessAssessment | None,
    integrity: dict,
    latest_audit_bundle: AuditBundleExport | None,
    latest_validation_receipt: AuditBundleValidationReceipt | None,
) -> str:
    if release is None:
        return "missing_release"
    if assessment is None:
        return "missing_assessment"
    if assessment.ready is not True or assessment.readiness_status != "ready":
        return "blocked_assessment"
    if integrity.get("complete") is not True:
        return "hash_invalid_assessment"
    if (
        latest_audit_bundle is not None
        and assessment.release_audit_bundle_id != latest_audit_bundle.id
    ):
        return "stale_assessment"
    if (
        latest_validation_receipt is not None
        and assessment.release_validation_receipt_id != latest_validation_receipt.id
    ):
        return "stale_assessment"
    return "ready_integrity_complete"


def _release_readiness_assessment_ref(
    *,
    request_row: SearchRequestRecord,
    release: SearchHarnessRelease | None,
    assessment: SearchHarnessReleaseReadinessAssessment | None,
    latest_audit_bundle: AuditBundleExport | None,
    latest_validation_receipt: AuditBundleValidationReceipt | None,
) -> dict:
    integrity = (
        search_harness_release_readiness_assessment_integrity(assessment)
        if assessment is not None
        else {}
    )
    return {
        "schema_name": "document_generation_release_readiness_assessment_ref",
        "schema_version": "1.0",
        "search_request_id": str(request_row.id),
        "search_request_created_at": request_row.created_at.isoformat(),
        "harness_name": request_row.harness_name,
        "search_harness_release_id": str(release.id) if release is not None else None,
        "release_created_at": release.created_at.isoformat() if release is not None else None,
        "assessment_id": str(assessment.id) if assessment is not None else None,
        "readiness_profile": assessment.readiness_profile if assessment is not None else None,
        "readiness_status": assessment.readiness_status if assessment is not None else None,
        "ready": assessment.ready if assessment is not None else False,
        "blockers": list(assessment.blockers_json or []) if assessment is not None else [],
        "latest_release_audit_bundle_id": (
            str(latest_audit_bundle.id) if latest_audit_bundle is not None else None
        ),
        "assessment_release_audit_bundle_id": (
            str(assessment.release_audit_bundle_id)
            if assessment is not None and assessment.release_audit_bundle_id is not None
            else None
        ),
        "latest_release_validation_receipt_id": (
            str(latest_validation_receipt.id) if latest_validation_receipt is not None else None
        ),
        "assessment_release_validation_receipt_id": (
            str(assessment.release_validation_receipt_id)
            if assessment is not None and assessment.release_validation_receipt_id is not None
            else None
        ),
        "readiness_payload_sha256": (
            assessment.readiness_payload_sha256 if assessment is not None else None
        ),
        "assessment_payload_sha256": (
            assessment.assessment_payload_sha256 if assessment is not None else None
        ),
        "integrity": integrity,
        "selection_rule": "latest_passed_release_at_or_before_search_request",
        "selection_status": _release_readiness_assessment_selection_status(
            release=release,
            assessment=assessment,
            integrity=integrity,
            latest_audit_bundle=latest_audit_bundle,
            latest_validation_receipt=latest_validation_receipt,
        ),
    }


def release_readiness_assessment_refs_for_exports(
    session: Session,
    search_export_summaries: list[dict],
) -> list[dict]:
    request_ids = _unique_uuids(
        summary.get("search_request_id") for summary in search_export_summaries
    )
    if not request_ids:
        return []
    request_rows = {
        row.id: row
        for row in session.scalars(
            select(SearchRequestRecord)
            .where(SearchRequestRecord.id.in_(request_ids))
            .order_by(SearchRequestRecord.created_at.asc(), SearchRequestRecord.id.asc())
        )
    }
    refs: list[dict] = []
    for request_id in request_ids:
        request_row = request_rows.get(request_id)
        if request_row is None:
            continue
        release = _latest_passed_release_for_search_request(session, request_row)
        latest_audit_bundle = (
            _latest_completed_release_audit_bundle(session, release.id)
            if release is not None
            else None
        )
        latest_validation_receipt = (
            _latest_release_validation_receipt(session, latest_audit_bundle.id)
            if latest_audit_bundle is not None
            else None
        )
        assessment = (
            _latest_release_readiness_assessment(session, release.id)
            if release is not None
            else None
        )
        refs.append(
            _release_readiness_assessment_ref(
                request_row=request_row,
                release=release,
                assessment=assessment,
                latest_audit_bundle=latest_audit_bundle,
                latest_validation_receipt=latest_validation_receipt,
            )
        )
    return refs


def _context_pack_release_readiness_refs(context_pack_payload: dict) -> list[dict]:
    audit_refs = context_pack_payload.get("audit_refs") or {}
    return [
        dict(ref)
        for ref in audit_refs.get("release_readiness_assessments") or []
        if isinstance(ref, dict)
    ]


def _context_pack_source_search_request_ids(context_pack_payload: dict) -> list[str]:
    audit_refs = context_pack_payload.get("audit_refs") or {}
    return _unique_strings(audit_refs.get("source_search_request_ids") or [])


_RELEASE_READINESS_REF_AUTHORITY_FIELDS = (
    "schema_name",
    "schema_version",
    "search_request_id",
    "search_request_created_at",
    "harness_name",
    "search_harness_release_id",
    "release_created_at",
    "assessment_id",
    "readiness_profile",
    "readiness_status",
    "ready",
    "blockers",
    "latest_release_audit_bundle_id",
    "assessment_release_audit_bundle_id",
    "latest_release_validation_receipt_id",
    "assessment_release_validation_receipt_id",
    "readiness_payload_sha256",
    "assessment_payload_sha256",
    "integrity",
    "selection_rule",
    "selection_status",
)


def _release_readiness_ref_field_mismatches(
    observed_ref: dict,
    expected_ref: dict,
) -> list[dict]:
    return [
        {
            "field": field,
            "observed": observed_ref.get(field),
            "expected": expected_ref.get(field),
        }
        for field in _RELEASE_READINESS_REF_AUTHORITY_FIELDS
        if observed_ref.get(field) != expected_ref.get(field)
    ]


def context_pack_release_readiness_db_summary(
    session: Session,
    context_pack_payload: dict,
) -> dict:
    source_search_request_ids = _context_pack_source_search_request_ids(context_pack_payload)
    refs = _context_pack_release_readiness_refs(context_pack_payload)
    source_search_request_id_set = set(source_search_request_ids)
    refs_by_request_id: dict[str, dict] = {}
    ref_request_id_counts: dict[str, int] = {}
    invalid_ref_indexes: list[int] = []
    for index, ref in enumerate(refs):
        ref_request_id = ref.get("search_request_id")
        if not ref_request_id:
            invalid_ref_indexes.append(index)
            continue
        ref_request_id = str(ref_request_id)
        refs_by_request_id[ref_request_id] = ref
        ref_request_id_counts[ref_request_id] = ref_request_id_counts.get(ref_request_id, 0) + 1
    duplicate_ref_request_ids = _unique_strings(
        request_id
        for request_id, count in ref_request_id_counts.items()
        if request_id in source_search_request_id_set and count > 1
    )
    unexpected_ref_request_ids = _unique_strings(
        request_id
        for request_id in ref_request_id_counts
        if request_id not in source_search_request_id_set
    )
    missing_ref_request_ids: list[str] = []
    invalid_assessment_id_request_ids: list[str] = []
    missing_assessment_row_ids: list[str] = []
    failed_integrity_assessment_ids: list[str] = []
    blocked_assessment_ids: list[str] = []
    stale_assessment_ids: list[str] = []
    hash_mismatch_assessment_ids: list[str] = []
    readiness_hash_mismatch_assessment_ids: list[str] = []
    ref_field_mismatch_request_ids: list[str] = []
    ref_field_mismatches: dict[str, list[dict]] = {}
    release_basis_mismatch_request_ids: list[str] = []
    missing_search_request_ids: list[str] = []
    verified_request_ids: list[str] = []

    for search_request_id in source_search_request_ids:
        if search_request_id in duplicate_ref_request_ids:
            continue
        ref = refs_by_request_id.get(search_request_id)
        if ref is None:
            missing_ref_request_ids.append(search_request_id)
            continue
        try:
            request_uuid = UUID(search_request_id)
        except ValueError:
            missing_search_request_ids.append(search_request_id)
            continue
        request_row = session.get(SearchRequestRecord, request_uuid)
        if request_row is None:
            missing_search_request_ids.append(search_request_id)
            continue
        assessment_id = ref.get("assessment_id")
        try:
            assessment_uuid = UUID(str(assessment_id))
        except (TypeError, ValueError):
            invalid_assessment_id_request_ids.append(search_request_id)
            continue
        assessment = session.get(SearchHarnessReleaseReadinessAssessment, assessment_uuid)
        if assessment is None:
            missing_assessment_row_ids.append(str(assessment_uuid))
            continue
        expected_release = _latest_passed_release_for_search_request(session, request_row)
        if (
            expected_release is None
            or str(assessment.search_harness_release_id) != str(expected_release.id)
            or str(ref.get("search_harness_release_id") or "")
            != str(assessment.search_harness_release_id)
        ):
            release_basis_mismatch_request_ids.append(search_request_id)
            continue
        integrity = search_harness_release_readiness_assessment_integrity(assessment)
        if integrity.get("complete") is not True:
            failed_integrity_assessment_ids.append(str(assessment.id))
            continue
        if assessment.ready is not True or assessment.readiness_status != "ready":
            blocked_assessment_ids.append(str(assessment.id))
            continue
        if ref.get("readiness_payload_sha256") != assessment.readiness_payload_sha256:
            readiness_hash_mismatch_assessment_ids.append(str(assessment.id))
            continue
        if ref.get("assessment_payload_sha256") != assessment.assessment_payload_sha256:
            hash_mismatch_assessment_ids.append(str(assessment.id))
            continue
        latest_audit_bundle = _latest_completed_release_audit_bundle(
            session,
            assessment.search_harness_release_id,
        )
        latest_validation_receipt = (
            _latest_release_validation_receipt(session, latest_audit_bundle.id)
            if latest_audit_bundle is not None
            else None
        )
        if (
            latest_audit_bundle is None
            or assessment.release_audit_bundle_id != latest_audit_bundle.id
            or latest_validation_receipt is None
            or assessment.release_validation_receipt_id != latest_validation_receipt.id
        ):
            stale_assessment_ids.append(str(assessment.id))
            continue
        expected_ref = _release_readiness_assessment_ref(
            request_row=request_row,
            release=expected_release,
            assessment=assessment,
            latest_audit_bundle=latest_audit_bundle,
            latest_validation_receipt=latest_validation_receipt,
        )
        field_mismatches = _release_readiness_ref_field_mismatches(ref, expected_ref)
        if field_mismatches:
            ref_field_mismatch_request_ids.append(search_request_id)
            ref_field_mismatches[search_request_id] = field_mismatches
            continue
        verified_request_ids.append(search_request_id)

    failure_count = sum(
        len(values)
        for values in (
            invalid_ref_indexes,
            duplicate_ref_request_ids,
            unexpected_ref_request_ids,
            missing_ref_request_ids,
            invalid_assessment_id_request_ids,
            missing_assessment_row_ids,
            failed_integrity_assessment_ids,
            blocked_assessment_ids,
            stale_assessment_ids,
            hash_mismatch_assessment_ids,
            readiness_hash_mismatch_assessment_ids,
            ref_field_mismatch_request_ids,
            release_basis_mismatch_request_ids,
            missing_search_request_ids,
        )
    )
    return {
        "source_search_request_count": len(source_search_request_ids),
        "readiness_assessment_ref_count": len(refs),
        "verified_request_count": len(verified_request_ids),
        "failure_count": failure_count,
        "invalid_ref_indexes": invalid_ref_indexes,
        "duplicate_ref_request_ids": duplicate_ref_request_ids,
        "unexpected_ref_request_ids": unexpected_ref_request_ids,
        "missing_ref_request_ids": missing_ref_request_ids,
        "invalid_assessment_id_request_ids": invalid_assessment_id_request_ids,
        "missing_assessment_row_ids": missing_assessment_row_ids,
        "failed_integrity_assessment_ids": failed_integrity_assessment_ids,
        "blocked_assessment_ids": blocked_assessment_ids,
        "stale_assessment_ids": stale_assessment_ids,
        "hash_mismatch_assessment_ids": hash_mismatch_assessment_ids,
        "readiness_hash_mismatch_assessment_ids": readiness_hash_mismatch_assessment_ids,
        "ref_field_mismatch_request_ids": ref_field_mismatch_request_ids,
        "ref_field_mismatches": ref_field_mismatches,
        "release_basis_mismatch_request_ids": release_basis_mismatch_request_ids,
        "missing_search_request_ids": missing_search_request_ids,
        "verified_request_ids": verified_request_ids,
        "complete": failure_count == 0
        and (
            not source_search_request_ids
            or len(verified_request_ids) == len(source_search_request_ids)
        ),
    }


def enforce_context_pack_release_readiness_db_gate(
    session: Session,
    *,
    context_pack_payload: dict,
    evaluation_payload: dict,
    required: bool,
) -> None:
    db_summary = context_pack_release_readiness_db_summary(session, context_pack_payload)
    check = {
        "check_key": "release_readiness_assessment_db_integrity",
        "passed": (not required or not db_summary["source_search_request_count"])
        or db_summary["complete"],
        "observed": db_summary,
        "required": required,
    }
    evaluation_payload.setdefault("checks", []).append(check)
    if not check["passed"]:
        evaluation_payload.setdefault("reasons", []).append(
            f"{check['check_key']} failed: observed {db_summary!r}."
        )
    failed_checks = [
        row for row in evaluation_payload.get("checks") or [] if row.get("passed") is not True
    ]
    summary = evaluation_payload.setdefault("summary", {})
    summary["gate_outcome"] = "failed" if failed_checks else "passed"
    summary["check_count"] = len(evaluation_payload.get("checks") or [])
    summary["passed_check_count"] = summary["check_count"] - len(failed_checks)
    summary["failed_check_count"] = len(failed_checks)
    summary["release_readiness_db_verified_request_count"] = db_summary["verified_request_count"]
    summary["release_readiness_db_failure_count"] = db_summary["failure_count"]
    summary["release_readiness_db_complete"] = db_summary["complete"]
    evaluation_payload["gate_outcome"] = summary["gate_outcome"]
    evaluation_payload.setdefault("trace", {})["release_readiness_db_summary"] = db_summary
