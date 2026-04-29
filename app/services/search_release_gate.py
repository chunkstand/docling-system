from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    AgentTaskVerificationOutcome,
    AuditBundleExport,
    AuditBundleValidationReceipt,
    SearchHarnessRelease,
    SearchReplayRun,
)
from app.schemas.search import (
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseReadinessResponse,
    SearchHarnessReleaseResponse,
    SearchHarnessReleaseSummaryResponse,
)
from app.services.search_harness_evaluations import get_search_harness_evaluation_detail
from app.services.semantic_governance import (
    record_search_harness_release_governance_event,
    search_harness_release_semantic_governance_context,
)

READINESS_PROFILE = "search_harness_release_readiness_v1"
RELEASE_AUDIT_BUNDLE_KIND = "search_harness_release_provenance"


@dataclass(frozen=True)
class SearchHarnessReleaseGateOutcome:
    outcome: str
    metrics: dict
    reasons: list[str]
    details: dict


class SearchHarnessReleaseGateThresholds(Protocol):
    max_total_regressed_count: int
    max_mrr_drop: float
    max_zero_result_count_increase: int
    max_foreign_top_result_count_increase: int
    min_total_shared_query_count: int


def _search_harness_release_not_found(release_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "search_harness_release_not_found",
        "Search harness release gate not found.",
        release_id=str(release_id),
    )


def _thresholds_dict(payload: SearchHarnessReleaseGateThresholds) -> dict:
    return {
        "max_total_regressed_count": payload.max_total_regressed_count,
        "max_mrr_drop": payload.max_mrr_drop,
        "max_zero_result_count_increase": payload.max_zero_result_count_increase,
        "max_foreign_top_result_count_increase": (
            payload.max_foreign_top_result_count_increase
        ),
        "min_total_shared_query_count": payload.min_total_shared_query_count,
    }


def _payload_sha256(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _error_detail(exc: HTTPException) -> dict:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return {
        "status_code": exc.status_code,
        "code": detail.get("code") or detail.get("error_code") or "search_harness_release_error",
        "message": detail.get("message") or detail.get("detail") or str(exc.detail),
        "context": detail.get("context") or detail.get("error_context") or {},
    }


def _error_release_gate_outcome(
    evaluation: SearchHarnessEvaluationResponse,
    payload: SearchHarnessReleaseGateThresholds,
    exc: HTTPException,
) -> SearchHarnessReleaseGateOutcome:
    error = _error_detail(exc)
    metrics = {
        "source_count": len(evaluation.sources),
        "total_shared_query_count": evaluation.total_shared_query_count,
        "total_improved_count": evaluation.total_improved_count,
        "total_regressed_count": evaluation.total_regressed_count,
        "total_unchanged_count": evaluation.total_unchanged_count,
        "max_observed_mrr_drop": 0.0,
        "max_observed_zero_result_count_increase": 0,
        "max_observed_foreign_top_result_count_increase": 0,
    }
    details = {
        "evaluation_id": str(evaluation.evaluation_id) if evaluation.evaluation_id else None,
        "evaluation_status": evaluation.status,
        "candidate_harness_name": evaluation.candidate_harness_name,
        "baseline_harness_name": evaluation.baseline_harness_name,
        "per_source": {},
        "thresholds": _thresholds_dict(payload),
        "error": error,
    }
    return SearchHarnessReleaseGateOutcome(
        outcome=AgentTaskVerificationOutcome.ERROR.value,
        metrics=metrics,
        reasons=[error["message"]],
        details=details,
    )


def _to_release_summary(row: SearchHarnessRelease) -> SearchHarnessReleaseSummaryResponse:
    return SearchHarnessReleaseSummaryResponse(
        release_id=row.id,
        evaluation_id=row.search_harness_evaluation_id,
        outcome=row.outcome,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        limit=row.limit,
        source_types=list(row.source_types_json or []),
        thresholds=row.thresholds_json or {},
        metrics=row.metrics_json or {},
        reasons=list(row.reasons_json or []),
        release_package_sha256=row.release_package_sha256,
        requested_by=row.requested_by,
        review_note=row.review_note,
        created_at=row.created_at,
    )


def _to_release_response(row: SearchHarnessRelease) -> SearchHarnessReleaseResponse:
    return SearchHarnessReleaseResponse(
        **_to_release_summary(row).model_dump(),
        details=row.details_json or {},
        evaluation_snapshot=row.evaluation_snapshot_json or {},
    )


def _rank_metrics(row: SearchReplayRun) -> dict:
    return (row.summary_json or {}).get("rank_metrics") or {}


def _load_replay_run(
    session: Session,
    replay_run_id: UUID,
    *,
    label: str,
) -> SearchReplayRun | None:
    replay_run = session.get(SearchReplayRun, replay_run_id)
    if replay_run is None:
        return None
    if replay_run.status != "completed":
        msg = f"{label} replay run {replay_run_id} is not completed."
        raise api_error(
            409,
            "search_replay_run_not_completed",
            msg,
            replay_run_id=str(replay_run_id),
            replay_run_status=replay_run.status,
            label=label,
        )
    return replay_run


def evaluate_search_harness_release_gate(
    session: Session,
    evaluation: SearchHarnessEvaluationResponse,
    payload: SearchHarnessReleaseGateThresholds,
) -> SearchHarnessReleaseGateOutcome:
    reasons: list[str] = []
    per_source: dict[str, dict] = {}
    max_observed_mrr_drop = 0.0
    max_observed_zero_result_increase = 0
    max_observed_foreign_top_result_increase = 0

    if evaluation.status != "completed":
        reasons.append(
            f"search harness evaluation {evaluation.evaluation_id or 'unknown'} "
            f"is {evaluation.status}."
        )

    for source in evaluation.sources:
        baseline_run = _load_replay_run(
            session,
            source.baseline_replay_run_id,
            label=f"{source.source_type} baseline",
        )
        candidate_run = _load_replay_run(
            session,
            source.candidate_replay_run_id,
            label=f"{source.source_type} candidate",
        )
        if baseline_run is None or candidate_run is None:
            missing = "baseline" if baseline_run is None else "candidate"
            reasons.append(f"{source.source_type}: {missing} replay run is missing.")
            continue

        baseline_rank_metrics = _rank_metrics(baseline_run)
        candidate_rank_metrics = _rank_metrics(candidate_run)
        baseline_mrr = float(baseline_rank_metrics.get("mrr") or 0.0)
        candidate_mrr = float(candidate_rank_metrics.get("mrr") or 0.0)
        mrr_drop = max(0.0, baseline_mrr - candidate_mrr)
        zero_result_increase = max(
            0,
            candidate_run.zero_result_count - baseline_run.zero_result_count,
        )
        foreign_top_result_increase = max(
            0,
            int(candidate_rank_metrics.get("foreign_top_result_count") or 0)
            - int(baseline_rank_metrics.get("foreign_top_result_count") or 0),
        )
        max_observed_mrr_drop = max(max_observed_mrr_drop, mrr_drop)
        max_observed_zero_result_increase = max(
            max_observed_zero_result_increase,
            zero_result_increase,
        )
        max_observed_foreign_top_result_increase = max(
            max_observed_foreign_top_result_increase,
            foreign_top_result_increase,
        )
        per_source[source.source_type] = {
            "baseline_replay_run_id": str(baseline_run.id),
            "candidate_replay_run_id": str(candidate_run.id),
            "shared_query_count": source.shared_query_count,
            "regressed_count": source.regressed_count,
            "baseline_mrr": baseline_mrr,
            "candidate_mrr": candidate_mrr,
            "mrr_drop": mrr_drop,
            "baseline_zero_result_count": baseline_run.zero_result_count,
            "candidate_zero_result_count": candidate_run.zero_result_count,
            "zero_result_count_increase": zero_result_increase,
            "foreign_top_result_count_increase": foreign_top_result_increase,
        }

        if source.regressed_count > payload.max_total_regressed_count:
            reasons.append(
                f"{source.source_type}: regressed_count {source.regressed_count} exceeds "
                f"{payload.max_total_regressed_count}."
            )
        if mrr_drop > payload.max_mrr_drop:
            reasons.append(
                f"{source.source_type}: mrr_drop {mrr_drop:.6f} exceeds {payload.max_mrr_drop:.6f}."
            )
        if zero_result_increase > payload.max_zero_result_count_increase:
            reasons.append(
                f"{source.source_type}: zero_result_count_increase {zero_result_increase} exceeds "
                f"{payload.max_zero_result_count_increase}."
            )
        if foreign_top_result_increase > payload.max_foreign_top_result_count_increase:
            reasons.append(
                f"{source.source_type}: foreign_top_result_count_increase "
                f"{foreign_top_result_increase} exceeds "
                f"{payload.max_foreign_top_result_count_increase}."
            )

    if evaluation.total_shared_query_count < payload.min_total_shared_query_count:
        reasons.append(
            "total_shared_query_count "
            f"{evaluation.total_shared_query_count} is below "
            f"{payload.min_total_shared_query_count}."
        )

    metrics = {
        "source_count": len(evaluation.sources),
        "total_shared_query_count": evaluation.total_shared_query_count,
        "total_improved_count": evaluation.total_improved_count,
        "total_regressed_count": evaluation.total_regressed_count,
        "total_unchanged_count": evaluation.total_unchanged_count,
        "max_observed_mrr_drop": max_observed_mrr_drop,
        "max_observed_zero_result_count_increase": max_observed_zero_result_increase,
        "max_observed_foreign_top_result_count_increase": (
            max_observed_foreign_top_result_increase
        ),
    }
    details = {
        "evaluation_id": str(evaluation.evaluation_id) if evaluation.evaluation_id else None,
        "evaluation_status": evaluation.status,
        "candidate_harness_name": evaluation.candidate_harness_name,
        "baseline_harness_name": evaluation.baseline_harness_name,
        "per_source": per_source,
        "thresholds": _thresholds_dict(payload),
    }
    outcome = (
        AgentTaskVerificationOutcome.PASSED.value
        if not reasons
        else AgentTaskVerificationOutcome.FAILED.value
    )
    return SearchHarnessReleaseGateOutcome(
        outcome=outcome,
        metrics=metrics,
        reasons=reasons,
        details=details,
    )


def record_search_harness_release_gate(
    session: Session,
    evaluation: SearchHarnessEvaluationResponse,
    payload: SearchHarnessReleaseGateThresholds,
    *,
    requested_by: str | None = None,
    review_note: str | None = None,
) -> SearchHarnessReleaseResponse:
    if evaluation.evaluation_id is None:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "search_harness_evaluation_missing_id",
            "Cannot create a release gate for an evaluation without a durable evaluation_id.",
        )

    try:
        gate = evaluate_search_harness_release_gate(session, evaluation, payload)
    except HTTPException as exc:
        gate = _error_release_gate_outcome(evaluation, payload, exc)
    thresholds = _thresholds_dict(payload)
    evaluation_snapshot = evaluation.model_dump(mode="json")
    release_package = {
        "schema_name": "search_harness_release_package",
        "schema_version": "1.0",
        "evaluation": evaluation_snapshot,
        "gate": {
            "outcome": gate.outcome,
            "metrics": gate.metrics,
            "reasons": gate.reasons,
            "details": gate.details,
        },
        "thresholds": thresholds,
    }
    release = SearchHarnessRelease(
        id=uuid.uuid4(),
        search_harness_evaluation_id=evaluation.evaluation_id,
        outcome=gate.outcome,
        baseline_harness_name=evaluation.baseline_harness_name,
        candidate_harness_name=evaluation.candidate_harness_name,
        limit=evaluation.limit,
        source_types_json=list(evaluation.source_types),
        thresholds_json=thresholds,
        metrics_json=gate.metrics,
        reasons_json=list(gate.reasons),
        details_json=gate.details,
        evaluation_snapshot_json=evaluation_snapshot,
        release_package_sha256=_payload_sha256(release_package),
        requested_by=requested_by,
        review_note=review_note,
        created_at=utcnow(),
    )
    session.add(release)
    session.flush()
    record_search_harness_release_governance_event(session, release)
    return _to_release_response(release)


def create_search_harness_release_gate(
    session: Session,
    payload: SearchHarnessReleaseGateRequest,
) -> SearchHarnessReleaseResponse:
    evaluation = get_search_harness_evaluation_detail(session, payload.evaluation_id)
    return record_search_harness_release_gate(
        session,
        evaluation,
        payload,
        requested_by=payload.requested_by,
        review_note=payload.review_note,
    )


def _release_package_sha256(row: SearchHarnessRelease) -> str:
    release_package = {
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
    return _payload_sha256(release_package)


def _latest_release_audit_bundle(
    session: Session,
    release_id: UUID,
) -> AuditBundleExport | None:
    return session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.search_harness_release_id == release_id,
            AuditBundleExport.bundle_kind == RELEASE_AUDIT_BUNDLE_KIND,
        )
        .order_by(AuditBundleExport.created_at.desc(), AuditBundleExport.id.asc())
        .limit(1)
    )


def _latest_validation_receipt(
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


def _release_audit_payload(row: AuditBundleExport | None) -> dict:
    if row is None:
        return {}
    bundle = row.bundle_payload_json if isinstance(row.bundle_payload_json, dict) else {}
    payload = bundle.get("payload") or {}
    return payload if isinstance(payload, dict) else {}


def _validation_errors(row: AuditBundleValidationReceipt | None) -> list[dict]:
    if row is None:
        return []
    return [error for error in row.validation_errors_json or [] if isinstance(error, dict)]


def _validation_error_codes(errors: list[dict]) -> list[str]:
    return sorted(
        {
            str(error["code"])
            for error in errors
            if error.get("code") not in {None, ""}
        }
    )


def _failed_audit_check_keys(audit_checklist: dict) -> list[str]:
    return sorted(
        key
        for key, value in audit_checklist.items()
        if key != "complete" and value is False
    )


def _training_audit_bundle_match_checks(payload: dict) -> list[dict]:
    integrity = payload.get("integrity") or {}
    checks = integrity.get("training_audit_bundle_match_checks") or []
    return [row for row in checks if isinstance(row, dict)]


def _readiness_diagnostics(
    *,
    audit_bundle: AuditBundleExport | None,
    validation_receipt: AuditBundleValidationReceipt | None,
    payload: dict,
) -> dict:
    audit_checklist = payload.get("audit_checklist") or {}
    audit_checklist = audit_checklist if isinstance(audit_checklist, dict) else {}
    errors = _validation_errors(validation_receipt)
    match_checks = _training_audit_bundle_match_checks(payload)
    return {
        "schema_name": "search_harness_release_readiness_diagnostics",
        "schema_version": "1.0",
        "release_audit_bundle_id": str(audit_bundle.id) if audit_bundle else None,
        "release_audit_bundle_present": audit_bundle is not None,
        "release_validation_receipt_id": (
            str(validation_receipt.id) if validation_receipt else None
        ),
        "release_validation_status": (
            validation_receipt.validation_status if validation_receipt else None
        ),
        "validation_error_count": len(errors),
        "validation_error_codes": _validation_error_codes(errors),
        "validation_errors": errors,
        "audit_checklist_complete": audit_checklist.get("complete"),
        "audit_checklist_failed": _failed_audit_check_keys(audit_checklist),
        "training_audit_bundle_match_checks": match_checks,
    }


def _lineage_failure_reasons(check: dict) -> list[str]:
    reasons: list[str] = []
    if check.get("hashes_match_training_run") is False:
        reasons.append("training_bundle_hash_mismatch")
    if check.get("claim_support_replay_alert_corpus_lineage_bundle_complete") is False:
        reasons.append("training_bundle_lineage_incomplete")
    if check.get("claim_support_replay_alert_corpus_lineage_current_complete") is False:
        reasons.append("current_corpus_lineage_incomplete")
    if check.get("claim_support_replay_alert_corpus_source_reference_counts_match") is False:
        reasons.append("source_reference_count_mismatch")
    if not reasons and check.get("claim_support_replay_alert_corpus_lineage_complete") is False:
        reasons.append("claim_support_replay_alert_corpus_lineage_incomplete")
    return reasons


def _lineage_remediation(payload: dict) -> dict:
    match_checks = _training_audit_bundle_match_checks(payload)
    affected = []
    for check in match_checks:
        if check.get("claim_support_replay_alert_corpus_lineage_required") is not True:
            continue
        if check.get("claim_support_replay_alert_corpus_lineage_complete") is True:
            continue
        affected.append(
            {
                "retrieval_training_run_id": check.get("retrieval_training_run_id"),
                "training_audit_bundle_id": check.get("audit_bundle_id"),
                "training_dataset_sha256": check.get("training_dataset_sha256"),
                "hashes_match_training_run": check.get("hashes_match_training_run"),
                "bundle_lineage_complete": check.get(
                    "claim_support_replay_alert_corpus_lineage_bundle_complete"
                ),
                "current_lineage_complete": check.get(
                    "claim_support_replay_alert_corpus_lineage_current_complete"
                ),
                "source_reference_count": check.get(
                    "claim_support_replay_alert_corpus_source_reference_count"
                ),
                "payload_source_reference_count": check.get(
                    "payload_claim_support_replay_alert_corpus_source_reference_count"
                ),
                "source_reference_counts_match": check.get(
                    "claim_support_replay_alert_corpus_source_reference_counts_match"
                ),
                "current_failures": list(
                    check.get("claim_support_replay_alert_corpus_current_failures") or []
                ),
                "failure_reasons": _lineage_failure_reasons(check),
                "suggested_operator_action": (
                    "Repair or repromote the governed replay-alert fixture corpus, "
                    "then recreate the release audit bundle and validation receipt."
                ),
            }
        )
    return {
        "schema_name": "search_harness_release_lineage_remediation",
        "schema_version": "1.0",
        "status": "action_required" if affected else "clear",
        "action_required": bool(affected),
        "affected_training_run_count": len(affected),
        "replay_alert_corpus": {
            "affected_training_run_count": len(affected),
            "items": affected,
        },
    }


def _false_check_reasons(checks: dict) -> list[str]:
    return sorted(
        key
        for key, value in checks.items()
        if key != "complete" and value is False
    )


def _readiness_blocker_details(
    *,
    checks: dict,
    retrieval: dict,
    provenance: dict,
    validation_receipts: dict,
    semantic_governance: dict,
    diagnostics: dict,
    lineage_remediation: dict,
) -> list[dict]:
    details: list[dict] = []
    if checks.get("retrieval_ready") is False:
        reasons = []
        if retrieval.get("release_passed") is not True:
            reasons.append("release_gate_not_passed")
        if retrieval.get("evaluation_snapshot_present") is not True:
            reasons.append("evaluation_snapshot_missing")
        if retrieval.get("release_package_hash_matches") is not True:
            reasons.append("release_package_hash_mismatch")
        details.append(
            {
                "blocker": "retrieval_ready",
                "reasons": reasons,
                "suggested_operator_action": (
                    "Inspect the release gate result and recreate the release from a "
                    "passed evaluation with an intact release package."
                ),
            }
        )
    if checks.get("provenance_ready") is False:
        reasons = []
        if provenance.get("release_audit_bundle_present") is not True:
            reasons.append("release_audit_bundle_missing")
        if provenance.get("release_audit_bundle_completed") is not True:
            reasons.append("release_audit_bundle_not_completed")
        details.append(
            {
                "blocker": "provenance_ready",
                "reasons": reasons,
                "release_audit_bundle_id": provenance.get("latest_release_audit_bundle_id"),
                "suggested_operator_action": (
                    "Create or refresh the release audit bundle before using this release "
                    "for document generation."
                ),
            }
        )
    if checks.get("semantic_governance_ready") is False:
        semantic_checks = semantic_governance.get("checks") or {}
        details.append(
            {
                "blocker": "semantic_governance_ready",
                "reasons": _false_check_reasons(semantic_checks),
                "suggested_operator_action": (
                    "Repair the semantic governance policy references and recreate the "
                    "release audit bundle."
                ),
            }
        )
    if checks.get("validation_receipts_ready") is False:
        reasons = []
        if validation_receipts.get("release_validation_receipt_present") is not True:
            reasons.append("release_validation_receipt_missing")
        else:
            if validation_receipts.get("release_validation_receipt_passed") is not True:
                reasons.append("release_validation_receipt_failed")
            if validation_receipts.get("payload_schema_valid") is not True:
                reasons.append("payload_schema_invalid")
            if validation_receipts.get("prov_graph_valid") is not True:
                reasons.append("prov_graph_invalid")
            if validation_receipts.get("bundle_integrity_valid") is not True:
                reasons.append("bundle_integrity_invalid")
            if validation_receipts.get("source_integrity_valid") is not True:
                reasons.append("source_integrity_invalid")
            if validation_receipts.get("semantic_governance_valid") is not True:
                reasons.append("semantic_governance_invalid")
        details.append(
            {
                "blocker": "validation_receipts_ready",
                "reasons": reasons,
                "release_validation_receipt_id": (
                    validation_receipts.get("latest_release_validation_receipt_id")
                ),
                "validation_error_codes": list(
                    validation_receipts.get("validation_error_codes") or []
                ),
                "audit_checklist_failed": list(
                    diagnostics.get("audit_checklist_failed") or []
                ),
                "lineage_remediation_required": bool(
                    lineage_remediation.get("action_required")
                ),
                "suggested_operator_action": (
                    "Resolve validation errors, then recreate the release audit bundle "
                    "and validation receipt."
                ),
            }
        )
    return details


def get_search_harness_release_readiness(
    session: Session,
    release_id: UUID,
) -> SearchHarnessReleaseReadinessResponse:
    release = session.get(SearchHarnessRelease, release_id)
    if release is None:
        raise _search_harness_release_not_found(release_id)

    release_package_hash_matches = (
        _release_package_sha256(release) == release.release_package_sha256
    )
    retrieval = {
        "release_outcome": release.outcome,
        "release_passed": release.outcome == AgentTaskVerificationOutcome.PASSED.value,
        "evaluation_snapshot_present": bool(release.evaluation_snapshot_json),
        "release_package_hash_matches": release_package_hash_matches,
        "candidate_harness_name": release.candidate_harness_name,
        "baseline_harness_name": release.baseline_harness_name,
        "source_types": list(release.source_types_json or []),
    }

    audit_bundle = _latest_release_audit_bundle(session, release.id)
    provenance = {
        "latest_release_audit_bundle_id": str(audit_bundle.id) if audit_bundle else None,
        "release_audit_bundle_present": audit_bundle is not None,
        "release_audit_bundle_completed": (
            audit_bundle is not None and audit_bundle.export_status == "completed"
        ),
        "release_audit_bundle_sha256": audit_bundle.bundle_sha256 if audit_bundle else None,
    }

    validation_receipt = (
        _latest_validation_receipt(session, audit_bundle.id) if audit_bundle is not None else None
    )
    validation_receipts = {
        "latest_release_validation_receipt_id": (
            str(validation_receipt.id) if validation_receipt else None
        ),
        "release_validation_receipt_present": validation_receipt is not None,
        "release_validation_receipt_passed": (
            validation_receipt is not None and validation_receipt.validation_status == "passed"
        ),
        "payload_schema_valid": (
            validation_receipt.payload_schema_valid if validation_receipt else False
        ),
        "prov_graph_valid": validation_receipt.prov_graph_valid if validation_receipt else False,
        "bundle_integrity_valid": (
            validation_receipt.bundle_integrity_valid if validation_receipt else False
        ),
        "source_integrity_valid": (
            validation_receipt.source_integrity_valid if validation_receipt else False
        ),
        "semantic_governance_valid": (
            validation_receipt.semantic_governance_valid if validation_receipt else False
        ),
    }
    validation_errors = _validation_errors(validation_receipt)
    validation_receipts["validation_error_count"] = len(validation_errors)
    validation_receipts["validation_error_codes"] = _validation_error_codes(validation_errors)

    semantic_context = search_harness_release_semantic_governance_context(session, release)
    semantic_governance = semantic_context["policy"]
    release_audit_payload = _release_audit_payload(audit_bundle)
    diagnostics = _readiness_diagnostics(
        audit_bundle=audit_bundle,
        validation_receipt=validation_receipt,
        payload=release_audit_payload,
    )
    lineage_remediation = _lineage_remediation(release_audit_payload)

    checks = {
        "retrieval_ready": (
            retrieval["release_passed"]
            and retrieval["evaluation_snapshot_present"]
            and retrieval["release_package_hash_matches"]
        ),
        "provenance_ready": (
            provenance["release_audit_bundle_present"]
            and provenance["release_audit_bundle_completed"]
        ),
        "semantic_governance_ready": semantic_governance["complete"],
        "validation_receipts_ready": (
            validation_receipts["release_validation_receipt_present"]
            and validation_receipts["release_validation_receipt_passed"]
            and validation_receipts["payload_schema_valid"]
            and validation_receipts["prov_graph_valid"]
            and validation_receipts["bundle_integrity_valid"]
            and validation_receipts["source_integrity_valid"]
            and validation_receipts["semantic_governance_valid"]
        ),
    }
    checks["ready"] = all(checks.values())
    blockers = [key for key, value in checks.items() if key != "ready" and not value]
    blocker_details = _readiness_blocker_details(
        checks=checks,
        retrieval=retrieval,
        provenance=provenance,
        validation_receipts=validation_receipts,
        semantic_governance=semantic_governance,
        diagnostics=diagnostics,
        lineage_remediation=lineage_remediation,
    )
    return SearchHarnessReleaseReadinessResponse(
        release_id=release.id,
        readiness_profile=READINESS_PROFILE,
        ready=checks["ready"],
        blockers=blockers,
        blocker_details=blocker_details,
        retrieval=retrieval,
        provenance=provenance,
        semantic_governance=semantic_governance,
        validation_receipts=validation_receipts,
        diagnostics=diagnostics,
        lineage_remediation=lineage_remediation,
        checks=checks,
        generated_at=utcnow(),
    )


def list_search_harness_releases(
    session: Session,
    *,
    limit: int = 20,
    candidate_harness_name: str | None = None,
    outcome: str | None = None,
) -> list[SearchHarnessReleaseSummaryResponse]:
    statement = select(SearchHarnessRelease).order_by(SearchHarnessRelease.created_at.desc())
    if candidate_harness_name:
        statement = statement.where(
            SearchHarnessRelease.candidate_harness_name == candidate_harness_name
        )
    if outcome:
        statement = statement.where(SearchHarnessRelease.outcome == outcome)
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [_to_release_summary(row) for row in rows]


def get_search_harness_release_detail(
    session: Session,
    release_id: UUID,
) -> SearchHarnessReleaseResponse:
    release = session.get(SearchHarnessRelease, release_id)
    if release is None:
        raise _search_harness_release_not_found(release_id)
    return _to_release_response(release)
