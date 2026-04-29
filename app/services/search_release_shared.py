from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.hashes import payload_sha256
from app.db.models import (
    AuditBundleExport,
    AuditBundleValidationReceipt,
    SearchHarnessRelease,
    SearchHarnessReleaseReadinessAssessment,
)


def search_harness_release_not_found_error(release_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "search_harness_release_not_found",
        "Search harness release gate not found.",
        release_id=str(release_id),
    )


def latest_release_readiness_assessment(
    session: Session,
    release_id: UUID,
) -> SearchHarnessReleaseReadinessAssessment | None:
    return session.scalar(
        select(SearchHarnessReleaseReadinessAssessment)
        .where(SearchHarnessReleaseReadinessAssessment.search_harness_release_id == release_id)
        .order_by(
            SearchHarnessReleaseReadinessAssessment.created_at.desc(),
            SearchHarnessReleaseReadinessAssessment.id.asc(),
        )
        .limit(1)
    )


def latest_audit_bundle_validation_receipt(
    session: Session,
    audit_bundle_id: UUID,
) -> AuditBundleValidationReceipt | None:
    return session.scalar(
        select(AuditBundleValidationReceipt)
        .where(AuditBundleValidationReceipt.audit_bundle_export_id == audit_bundle_id)
        .order_by(
            AuditBundleValidationReceipt.created_at.desc(),
            AuditBundleValidationReceipt.id.asc(),
        )
        .limit(1)
    )


def release_package_sha256(row: SearchHarnessRelease) -> str:
    package = {
        "schema_name": "search_harness_release_package",
        "schema_version": "1.0",
        "evaluation": row.evaluation_snapshot_json or {},
        "gate": {
            "outcome": row.outcome,
            "metrics": row.metrics_json or {},
            "reasons": row.reasons_json or [],
            "details": row.details_json or {},
        },
        "thresholds": row.thresholds_json or {},
    }
    return payload_sha256(package)


def latest_completed_release_audit_bundle(
    session: Session,
    release_id: UUID,
    *,
    bundle_kind: str,
) -> AuditBundleExport | None:
    return session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.search_harness_release_id == release_id,
            AuditBundleExport.bundle_kind == bundle_kind,
            AuditBundleExport.export_status == "completed",
        )
        .order_by(AuditBundleExport.created_at.desc(), AuditBundleExport.id.asc())
        .limit(1)
    )
