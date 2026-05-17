# ruff: noqa: E501
from __future__ import annotations

from typing import Any

from app.db.models import ClaimEvidenceDerivation, EvidencePackageExport
from app.services.evidence_common import payload_sha256
from app.services.evidence_technical_report_exports import (
    build_technical_report_derivation_package,
)
from app.services.evidence_technical_report_exports import (
    claim_derivation_provenance_lock_contract_mismatches as _claim_derivation_provenance_lock_contract_mismatches,
)
from app.services.evidence_technical_report_exports import (
    claim_derivation_support_judgment_contract_mismatches as _claim_derivation_support_judgment_contract_mismatches,
)


def _technical_report_integrity_payload(
    draft_payload: dict[str, Any],
    exports: list[EvidencePackageExport],
    derivations: list[ClaimEvidenceDerivation],
) -> dict[str, Any]:
    from app.schemas.agent_task_reports import TechnicalReportDraftPayload

    canonical_draft_payload = (
        TechnicalReportDraftPayload.model_validate(draft_payload).model_dump(mode="json")
        if draft_payload
        else {}
    )
    recomputed_package = build_technical_report_derivation_package(canonical_draft_payload)
    expected_package_sha256 = str(recomputed_package.get("package_sha256") or "")
    expected_derivations_by_claim_id = {
        str(row.get("claim_id")): row
        for row in recomputed_package.get("claim_derivations", [])
        if row.get("claim_id")
    }
    draft_package_sha256 = draft_payload.get("evidence_package_sha256")
    draft_package_hash_matches = bool(draft_package_sha256) and (
        draft_package_sha256 == expected_package_sha256
    )
    export_package_hash_mismatch_count = sum(
        1 for row in exports if row.package_sha256 != expected_package_sha256
    )
    export_package_hash_matches = bool(exports) and export_package_hash_mismatch_count == 0
    stored_claim_ids = {row.claim_id for row in derivations}
    missing_claim_derivation_ids = sorted(
        claim_id
        for claim_id in expected_derivations_by_claim_id
        if claim_id not in stored_claim_ids
    )
    mismatched_claim_ids: list[str] = []
    package_mismatched_claim_ids: list[str] = []
    provenance_lock_mismatched_claim_ids: list[str] = []
    provenance_lock_contract_mismatched_claim_ids: list[str] = []
    missing_provenance_lock_claim_ids: list[str] = []
    support_judgment_mismatched_claim_ids: list[str] = []
    support_judgment_contract_mismatched_claim_ids: list[str] = []
    missing_support_judgment_claim_ids: list[str] = []
    failed_support_judgment_claim_ids: list[str] = []
    for row in derivations:
        expected_derivation = expected_derivations_by_claim_id.get(str(row.claim_id))
        expected_derivation_sha256 = (
            str(expected_derivation.get("derivation_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if row.derivation_sha256 != expected_derivation_sha256:
            mismatched_claim_ids.append(str(row.claim_id))
        if row.evidence_package_sha256 != expected_package_sha256:
            package_mismatched_claim_ids.append(str(row.claim_id))
        expected_provenance_lock_sha256 = (
            str(expected_derivation.get("provenance_lock_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if not row.provenance_lock_json or not row.provenance_lock_sha256:
            missing_provenance_lock_claim_ids.append(str(row.claim_id))
        elif (
            row.provenance_lock_sha256 != payload_sha256(row.provenance_lock_json)
            or row.provenance_lock_sha256 != expected_provenance_lock_sha256
        ):
            provenance_lock_mismatched_claim_ids.append(str(row.claim_id))
        if _claim_derivation_provenance_lock_contract_mismatches(row):
            provenance_lock_contract_mismatched_claim_ids.append(str(row.claim_id))
        expected_support_judgment_sha256 = (
            str(expected_derivation.get("support_judgment_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if (
            not row.support_verdict
            or row.support_score is None
            or not row.support_judge_run_id
            or not row.support_judgment_json
            or not row.support_judgment_sha256
        ):
            missing_support_judgment_claim_ids.append(str(row.claim_id))
        elif (
            row.support_judgment_sha256 != payload_sha256(row.support_judgment_json)
            or row.support_judgment_sha256 != expected_support_judgment_sha256
        ):
            support_judgment_mismatched_claim_ids.append(str(row.claim_id))
        if _claim_derivation_support_judgment_contract_mismatches(row):
            support_judgment_contract_mismatched_claim_ids.append(str(row.claim_id))
        if row.support_verdict != "supported":
            failed_support_judgment_claim_ids.append(str(row.claim_id))

    return {
        "expected_evidence_package_sha256": expected_package_sha256,
        "draft_evidence_package_sha256": draft_package_sha256,
        "draft_package_hash_matches": draft_package_hash_matches,
        "export_package_hash_matches": export_package_hash_matches,
        "export_package_hash_mismatch_count": export_package_hash_mismatch_count,
        "expected_claim_derivation_count": len(expected_derivations_by_claim_id),
        "stored_claim_derivation_count": len(derivations),
        "claim_derivation_count_matches": len(derivations) == len(expected_derivations_by_claim_id),
        "claim_derivation_hash_mismatch_count": len(mismatched_claim_ids),
        "claim_package_hash_mismatch_count": len(package_mismatched_claim_ids),
        "claim_provenance_lock_mismatch_count": len(provenance_lock_mismatched_claim_ids),
        "claim_provenance_lock_contract_mismatch_count": len(
            provenance_lock_contract_mismatched_claim_ids
        ),
        "missing_claim_provenance_lock_count": len(missing_provenance_lock_claim_ids),
        "claim_support_judgment_mismatch_count": len(support_judgment_mismatched_claim_ids),
        "claim_support_judgment_contract_mismatch_count": len(
            support_judgment_contract_mismatched_claim_ids
        ),
        "missing_claim_support_judgment_count": len(missing_support_judgment_claim_ids),
        "failed_claim_support_judgment_count": len(failed_support_judgment_claim_ids),
        "missing_claim_derivation_count": len(missing_claim_derivation_ids),
        "mismatched_claim_ids": sorted(mismatched_claim_ids),
        "package_mismatched_claim_ids": sorted(package_mismatched_claim_ids),
        "provenance_lock_mismatched_claim_ids": sorted(provenance_lock_mismatched_claim_ids),
        "provenance_lock_contract_mismatched_claim_ids": sorted(
            provenance_lock_contract_mismatched_claim_ids
        ),
        "missing_provenance_lock_claim_ids": sorted(missing_provenance_lock_claim_ids),
        "support_judgment_mismatched_claim_ids": sorted(support_judgment_mismatched_claim_ids),
        "support_judgment_contract_mismatched_claim_ids": sorted(
            support_judgment_contract_mismatched_claim_ids
        ),
        "missing_support_judgment_claim_ids": sorted(missing_support_judgment_claim_ids),
        "failed_support_judgment_claim_ids": sorted(failed_support_judgment_claim_ids),
        "missing_claim_derivation_ids": missing_claim_derivation_ids,
    }


technical_report_integrity_payload = _technical_report_integrity_payload
