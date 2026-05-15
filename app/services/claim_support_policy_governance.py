from __future__ import annotations

from importlib import import_module
from typing import Any

from app.core.config import get_settings
from app.core.hashes import hmac_sha256_hex as _signature_value
from app.services.evidence import payload_sha256

CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD = (
    "activation_change_impact_payload_sha256"
)
CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND = (
    "claim_support_policy_activation_governance"
)
CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_FILENAME = (
    "claim_support_policy_activation_governance.json"
)


def _value_sha256(value: Any | None) -> str | None:
    return str(payload_sha256(value)) if value is not None else None


def _signature_payload(receipt_sha256: str) -> dict[str, Any]:
    settings = get_settings()
    signing_key = getattr(settings, "audit_bundle_signing_key", None)
    if not signing_key:
        return {
            "signature_status": "unsigned",
            "signature": None,
            "signature_algorithm": "hmac-sha256",
            "signing_key_id": None,
        }
    signing_key_id = getattr(settings, "audit_bundle_signing_key_id", None) or "local"
    return {
        "signature_status": "signed",
        "signature": _signature_value(receipt_sha256, str(signing_key)),
        "signature_algorithm": "hmac-sha256",
        "signing_key_id": str(signing_key_id),
    }


def _fixture_set_snapshot(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "fixture_set_id": str(row.id),
        "fixture_set_name": row.fixture_set_name,
        "fixture_set_version": row.fixture_set_version,
        "status": row.status,
        "fixture_set_sha256": row.fixture_set_sha256,
        "fixture_count": row.fixture_count,
        "hard_case_kinds": list(row.hard_case_kinds_json or []),
        "verdicts": list(row.verdicts_json or []),
        "metadata": row.metadata_json or {},
        "created_at": row.created_at.isoformat(),
    }


def _fixture_set_diff(
    row,
    mined_failure_summary: dict[str, Any],
) -> dict[str, Any] | None:
    if row is None:
        return None
    default_fixture_count = mined_failure_summary.get("default_fixture_count")
    combined_fixture_count = mined_failure_summary.get("combined_fixture_count")
    diff = {
        "schema_name": "claim_support_fixture_set_diff",
        "schema_version": "1.0",
        "fixture_set_id": str(row.id),
        "fixture_set_sha256": row.fixture_set_sha256,
        "fixture_count": row.fixture_count,
        "hard_case_kinds": list(row.hard_case_kinds_json or []),
        "verdicts": list(row.verdicts_json or []),
        "replay_composition": {
            "default_fixture_count": default_fixture_count,
            "explicit_fixture_count": mined_failure_summary.get("explicit_fixture_count"),
            "mined_failure_case_count": mined_failure_summary.get(
                "mined_failure_case_count"
            ),
            "combined_fixture_count": combined_fixture_count,
            "manifest_sha256": mined_failure_summary.get("manifest_sha256"),
            "summary_sha256": mined_failure_summary.get("summary_sha256"),
        },
        "fixture_count_delta_from_default": (
            combined_fixture_count - default_fixture_count
            if isinstance(default_fixture_count, int)
            and isinstance(combined_fixture_count, int)
            else None
        ),
    }
    return {**diff, "fixture_set_diff_sha256": _value_sha256(diff)}


def _evaluation_snapshot(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "evaluation_id": str(row.id),
        "evaluation_name": row.evaluation_name,
        "agent_task_id": str(row.agent_task_id) if row.agent_task_id else None,
        "operator_run_id": str(row.operator_run_id) if row.operator_run_id else None,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "fixture_set_sha256": row.fixture_set_sha256,
        "policy_id": str(row.policy_id) if row.policy_id else None,
        "policy_sha256": row.policy_sha256,
        "judge_name": row.judge_name,
        "judge_version": row.judge_version,
        "gate_outcome": row.gate_outcome,
        "metrics": row.metrics_json or {},
        "reasons": list(row.reasons_json or []),
        "evaluation_payload_sha256": row.evaluation_payload_sha256,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _activation_governance_event_payload(
    *,
    task,
    governance_artifact,
    activated_policy,
    governance_payload: dict[str, Any],
) -> dict[str, Any]:
    receipt = governance_payload.get("activation_governance_receipt") or {}
    activation = governance_payload.get("activation") or {}
    fixture_replay = governance_payload.get("fixture_replay") or {}
    fixture_set_diff = fixture_replay.get("fixture_set_diff") or {}
    replay_alert_fixture_summary = fixture_replay.get("replay_alert_fixture_summary") or {}
    replay_alert_fixture_coverage_waiver = (
        fixture_replay.get("replay_alert_fixture_coverage_waiver") or {}
    )
    mined_failure_summary = fixture_replay.get("mined_failure_summary") or {}
    change_impact = governance_payload.get("activation_change_impact") or {}
    change_impact_summary = change_impact.get("impact_summary") or {}
    return {
        "claim_support_policy_activation": {
            "task_id": str(task.id),
            "artifact_id": str(governance_artifact.id),
            "artifact_kind": governance_artifact.artifact_kind,
            "artifact_path": governance_artifact.storage_path,
            "activated_policy_id": str(activated_policy.id),
            "activated_policy_sha256": activated_policy.policy_sha256,
            "policy_name": activated_policy.policy_name,
            "policy_version": activated_policy.policy_version,
            "previous_active_policy_id": activation.get("previous_active_policy_id"),
            "retired_policy_ids": list(activation.get("retired_policy_ids") or []),
            "verification_task_id": activation.get("verification_task_id"),
            "verification_id": (
                (governance_payload.get("verification") or {})
                .get("verification", {})
                .get("verification_id")
            ),
            "verification_fixture_set_sha256": (
                (fixture_replay.get("fixture_set") or {}).get("fixture_set_sha256")
            ),
            "verification_fixture_set_diff_sha256": fixture_set_diff.get(
                "fixture_set_diff_sha256"
            ),
            "replay_alert_fixture_summary_sha256": (
                replay_alert_fixture_summary.get("verification_summary_sha256")
            ),
            "replay_alert_fixture_count": (
                replay_alert_fixture_summary.get("included_replay_alert_fixture_count")
            ),
            "replay_alert_fixture_coverage_waiver_sha256": (
                replay_alert_fixture_coverage_waiver.get("waiver_sha256")
            ),
            "replay_alert_fixture_coverage_waiver_artifact_id": (
                replay_alert_fixture_coverage_waiver.get("artifact_id")
            ),
            "replay_alert_fixture_coverage_waiver_severity": (
                replay_alert_fixture_coverage_waiver.get("waiver_severity")
            ),
            "replay_alert_fixture_coverage_waiver_expires_at": (
                replay_alert_fixture_coverage_waiver.get("waiver_expires_at")
            ),
            "waiver_activation_approved_by": (
                (activation.get("waiver_activation_approval") or {}).get("approved_by")
            ),
            "mined_failure_summary_sha256": mined_failure_summary.get("summary_sha256"),
            "activation_governance_payload_sha256": (
                governance_payload.get("activation_governance_payload_sha256")
            ),
            "activation_change_impact_payload_sha256": (
                change_impact.get("activation_change_impact_payload_sha256")
            ),
            "activation_change_impact_id": change_impact.get("change_impact_id"),
            "affected_support_judgment_count": change_impact_summary.get(
                "affected_support_judgment_count"
            ),
            "affected_generated_document_count": change_impact_summary.get(
                "affected_generated_document_count"
            ),
            "affected_technical_report_verification_count": change_impact_summary.get(
                "affected_technical_report_verification_count"
            ),
            "replay_recommended_count": change_impact_summary.get(
                "replay_recommended_count"
            ),
            "receipt_sha256": receipt.get("receipt_sha256"),
            "signature_status": receipt.get("signature_status"),
            "prov_jsonld_sha256": (
                (governance_payload.get("integrity") or {}).get("prov_jsonld_sha256")
            ),
        },
        "activation_change_impact": {
            "change_impact_id": change_impact.get("change_impact_id"),
            "impact_payload_sha256": change_impact.get(
                "activation_change_impact_payload_sha256"
            ),
            "impact_summary": change_impact_summary,
            "impact_reasons": list(change_impact.get("impact_reasons") or []),
        },
        "semantic_basis": governance_payload.get("semantic_basis") or {},
        "integrity": governance_payload.get("integrity") or {},
    }


value_sha256 = _value_sha256
signature_payload = _signature_payload
fixture_set_snapshot = _fixture_set_snapshot
fixture_set_diff = _fixture_set_diff
evaluation_snapshot = _evaluation_snapshot
activation_governance_event_payload = _activation_governance_event_payload


def claim_support_policy_change_impact_payload_sha256(payload: dict[str, Any]) -> str:
    return import_module(
        "app.services.claim_support_policy_change_impact_governance"
    ).claim_support_policy_change_impact_payload_sha256(payload)


def build_claim_support_policy_change_impact_payload(session, **kwargs):
    return import_module(
        "app.services.claim_support_policy_change_impact_governance"
    ).build_claim_support_policy_change_impact_payload(session, **kwargs)


def persist_claim_support_policy_change_impact(session, **kwargs):
    return import_module(
        "app.services.claim_support_policy_change_impact_governance"
    ).persist_claim_support_policy_change_impact(session, **kwargs)


def build_claim_support_policy_activation_governance_payload(session, **kwargs):
    return import_module(
        "app.services.claim_support_policy_activation_governance"
    ).build_claim_support_policy_activation_governance_payload(session, **kwargs)


def record_claim_support_policy_activation_governance_event(session, **kwargs):
    return import_module(
        "app.services.claim_support_policy_activation_governance"
    ).record_claim_support_policy_activation_governance_event(session, **kwargs)
