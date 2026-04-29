from __future__ import annotations

from datetime import UTC, datetime

from app.db.models import (
    ClaimSupportCalibrationPolicy,
)
from app.schemas.agent_tasks import (
    DraftClaimSupportCalibrationPolicyTaskOutput,
)
from app.services.evidence import (
    payload_sha256,
)

CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver"
)


CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_FILENAME = (
    "claim_support_replay_alert_fixture_coverage_waiver.json"
)


CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_EXPIRING_HOURS = 24


CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA = (
    "claim_support_replay_alert_fixture_coverage_waiver"
)


CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_SCHEMA_VERSION = "1.1"


def require_policy_row_matches_draft_output(
    policy_row: ClaimSupportCalibrationPolicy,
    draft_output: DraftClaimSupportCalibrationPolicyTaskOutput,
) -> None:
    if policy_row.id != draft_output.policy_id:
        raise ValueError("Draft policy row does not match the requested draft task output.")
    if policy_row.policy_name != draft_output.policy_name:
        raise ValueError("Draft policy name no longer matches the draft task output.")
    if policy_row.policy_version != draft_output.policy_version:
        raise ValueError("Draft policy version no longer matches the draft task output.")
    if policy_row.policy_sha256 != draft_output.policy_sha256:
        raise ValueError("Draft policy hash no longer matches the draft task output.")
    if dict(policy_row.policy_payload_json or {}) != dict(draft_output.policy_payload or {}):
        raise ValueError("Draft policy payload no longer matches the draft task output.")


def require_utc_datetime(value: object, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO-8601 datetime.") from exc
    else:
        raise ValueError(f"{field_name} is required.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone.")
    return parsed.astimezone(UTC)


def _replay_alert_fixture_coverage_waiver_hash_basis(waiver: dict) -> dict:
    artifact_fields = {
        "artifact_id",
        "artifact_kind",
        "artifact_path",
        "coverage_ledger_id",
        "coverage_status",
        "waived_escalation_event_count",
        "waived_escalation_set_sha256",
        "waiver_sha256",
    }
    return {key: value for key, value in dict(waiver).items() if key not in artifact_fields}


def replay_alert_fixture_coverage_waiver_sha256(waiver: dict) -> str | None:
    return payload_sha256(_replay_alert_fixture_coverage_waiver_hash_basis(waiver))
