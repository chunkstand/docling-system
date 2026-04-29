from __future__ import annotations

from uuid import UUID

from app.core.hashes import payload_sha256 as _payload_sha256
from app.db.models import SearchHarnessReleaseReadinessAssessment
from app.schemas.search import (
    SearchHarnessReleaseReadinessAssessmentResponse,
    SearchHarnessReleaseReadinessAssessmentSummaryResponse,
)


def to_readiness_assessment_summary(
    row: SearchHarnessReleaseReadinessAssessment,
) -> SearchHarnessReleaseReadinessAssessmentSummaryResponse:
    return SearchHarnessReleaseReadinessAssessmentSummaryResponse(
        assessment_id=row.id,
        release_id=row.search_harness_release_id,
        readiness_profile=row.readiness_profile,
        readiness_status=row.readiness_status,
        ready=row.ready,
        blockers=list(row.blockers_json or []),
        latest_release_audit_bundle_id=row.release_audit_bundle_id,
        latest_release_validation_receipt_id=row.release_validation_receipt_id,
        semantic_governance_event_id=row.semantic_governance_event_id,
        readiness_payload_sha256=row.readiness_payload_sha256,
        assessment_payload_sha256=row.assessment_payload_sha256,
        created_by=row.created_by,
        review_note=row.review_note,
        created_at=row.created_at,
    )


def _uuid_matches(payload_value: object, row_value: UUID | None) -> bool:
    return payload_value == (str(row_value) if row_value is not None else None)


def readiness_assessment_integrity(
    row: SearchHarnessReleaseReadinessAssessment,
) -> dict:
    readiness_payload = row.readiness_payload_json or {}
    assessment_payload = row.assessment_payload_json or {}
    embedded_readiness = assessment_payload.get("readiness") or {}
    checks = {
        "readiness_payload_hash_matches": (
            _payload_sha256(readiness_payload) == row.readiness_payload_sha256
        ),
        "assessment_payload_hash_matches": (
            _payload_sha256(assessment_payload) == row.assessment_payload_sha256
        ),
        "assessment_payload_embeds_readiness_hash": (
            _payload_sha256(embedded_readiness) == row.readiness_payload_sha256
        ),
        "assessment_id_matches": assessment_payload.get("assessment_id") == str(row.id),
        "release_id_matches": _uuid_matches(
            assessment_payload.get("search_harness_release_id"),
            row.search_harness_release_id,
        ),
        "readiness_release_id_matches": _uuid_matches(
            readiness_payload.get("release_id"),
            row.search_harness_release_id,
        ),
        "release_audit_bundle_id_matches": _uuid_matches(
            assessment_payload.get("latest_release_audit_bundle_id"),
            row.release_audit_bundle_id,
        ),
        "release_validation_receipt_id_matches": _uuid_matches(
            assessment_payload.get("latest_release_validation_receipt_id"),
            row.release_validation_receipt_id,
        ),
        "readiness_status_matches": (
            assessment_payload.get("readiness_status") == row.readiness_status
        ),
        "ready_matches": assessment_payload.get("ready") == row.ready,
        "blockers_match": list(assessment_payload.get("blockers") or [])
        == list(row.blockers_json or []),
    }
    return {
        "schema_name": "search_harness_release_readiness_assessment_integrity",
        "schema_version": "1.0",
        **checks,
        "complete": all(checks.values()),
    }


def search_harness_release_readiness_assessment_integrity(
    row: SearchHarnessReleaseReadinessAssessment,
) -> dict:
    return readiness_assessment_integrity(row)


def to_readiness_assessment_response(
    row: SearchHarnessReleaseReadinessAssessment,
) -> SearchHarnessReleaseReadinessAssessmentResponse:
    summary = to_readiness_assessment_summary(row).model_dump()
    summary["schema_name"] = "search_harness_release_readiness_assessment"
    summary["schema_version"] = "1.1"
    return SearchHarnessReleaseReadinessAssessmentResponse(
        **summary,
        blocker_details=list(row.blocker_details_json or []),
        checks=row.checks_json or {},
        diagnostics=row.diagnostics_json or {},
        lineage_remediation=row.lineage_remediation_json or {},
        readiness=row.readiness_payload_json or {},
        assessment=row.assessment_payload_json or {},
        integrity=readiness_assessment_integrity(row),
    )
