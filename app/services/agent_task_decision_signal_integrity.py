from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashes import embedded_payload_hash_matches as hash_matches_embedded_receipt
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.semantic_memory import SemanticGovernanceEvent

CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND = (
    "claim_support_policy_impact_replay_escalated"
)
CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND = (
    "claim_support_policy_impact_fixture_promoted"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver_closed"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver_closure"
)
CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_EXPIRING_HOURS = 24


def _uuid_from_value(value: object) -> UUID | None:
    if value in {None, ""}:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _waiver_uuid_values(values: object) -> list[UUID]:
    uuids: list[UUID] = []
    for value in values or []:
        parsed = _uuid_from_value(value)
        if parsed is not None:
            uuids.append(parsed)
    return uuids


def _waiver_string_values(values: object) -> set[str]:
    return {str(value) for value in values or [] if value not in {None, ""}}


def _valid_replay_alert_fixture_coverage_waiver_closure_event(
    session: Session,
    event: SemanticGovernanceEvent,
) -> tuple[UUID, str] | None:
    closure_payload = (event.event_payload_json or {}).get(
        "claim_support_replay_alert_fixture_coverage_waiver_closure"
    ) or {}
    if not isinstance(closure_payload, dict):
        return None
    receipt_sha256 = str(closure_payload.get("receipt_sha256") or "")
    waiver_sha256 = str(closure_payload.get("waiver_sha256") or "")
    promotion_receipt_sha256 = str(closure_payload.get("promotion_receipt_sha256") or "")
    waiver_artifact_id = _uuid_from_value(closure_payload.get("waiver_artifact_id"))
    promotion_artifact_id = _uuid_from_value(closure_payload.get("promotion_artifact_id"))
    promotion_event_id = _uuid_from_value(closure_payload.get("promotion_event_id"))
    if (
        not receipt_sha256
        or not waiver_sha256
        or not promotion_receipt_sha256
        or waiver_artifact_id is None
        or promotion_artifact_id is None
        or promotion_event_id is None
        or event.agent_task_artifact_id is None
        or event.receipt_sha256 != receipt_sha256
        or not hash_matches_embedded_receipt(
            closure_payload,
            hash_field="receipt_sha256",
        )
    ):
        return None

    closure_artifact = session.get(AgentTaskArtifact, event.agent_task_artifact_id)
    waiver_artifact = session.get(AgentTaskArtifact, waiver_artifact_id)
    promotion_artifact = session.get(AgentTaskArtifact, promotion_artifact_id)
    promotion_event = session.get(SemanticGovernanceEvent, promotion_event_id)
    if (
        closure_artifact is None
        or closure_artifact.artifact_kind
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND
        or closure_artifact.payload_json.get("receipt_sha256") != receipt_sha256
        or waiver_artifact is None
        or waiver_artifact.artifact_kind
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND
        or waiver_artifact.payload_json.get("waiver_sha256") != waiver_sha256
        or promotion_artifact is None
        or promotion_artifact.artifact_kind
        != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
        or promotion_artifact.payload_json.get("receipt_sha256") != promotion_receipt_sha256
        or promotion_event is None
        or promotion_event.event_kind != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND
        or promotion_event.receipt_sha256 != promotion_receipt_sha256
        or promotion_event.agent_task_artifact_id != promotion_artifact_id
    ):
        return None

    waived_event_ids = {
        str(value) for value in closure_payload.get("waived_escalation_event_ids") or []
    }
    covered_event_ids = {
        str(value) for value in closure_payload.get("covered_escalation_event_ids") or []
    }
    raw_coverage_promotion_artifact_ids = _waiver_string_values(
        closure_payload.get("coverage_promotion_artifact_ids") or []
    )
    coverage_promotion_artifact_ids = set(_waiver_uuid_values(raw_coverage_promotion_artifact_ids))
    if raw_coverage_promotion_artifact_ids and len(coverage_promotion_artifact_ids) != len(
        raw_coverage_promotion_artifact_ids
    ):
        return None
    if coverage_promotion_artifact_ids:
        coverage_promotion_artifact_ids.add(promotion_artifact_id)
        source_promotion_event_ids: set[str] = set()
        coverage_receipt_sha256s = _waiver_string_values(
            closure_payload.get("coverage_promotion_receipt_sha256s") or []
        )
        actual_receipt_sha256s: set[str] = set()
        for artifact_id in sorted(coverage_promotion_artifact_ids, key=str):
            artifact = session.get(AgentTaskArtifact, artifact_id)
            if (
                artifact is None
                or artifact.artifact_kind
                != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
            ):
                return None
            artifact_receipt_sha256 = str(artifact.payload_json.get("receipt_sha256") or "")
            if artifact_receipt_sha256:
                actual_receipt_sha256s.add(artifact_receipt_sha256)
            source_promotion_event_ids.update(
                str(value)
                for value in artifact.payload_json.get("source_escalation_event_ids") or []
                if value
            )
        if coverage_receipt_sha256s and coverage_receipt_sha256s != actual_receipt_sha256s:
            return None
        raw_coverage_promotion_event_ids = _waiver_string_values(
            closure_payload.get("coverage_promotion_event_ids") or []
        )
        coverage_promotion_event_ids = set(_waiver_uuid_values(raw_coverage_promotion_event_ids))
        if raw_coverage_promotion_event_ids and len(coverage_promotion_event_ids) != len(
            raw_coverage_promotion_event_ids
        ):
            return None
        if not coverage_promotion_event_ids:
            coverage_promotion_event_ids.add(promotion_event_id)
        event_artifact_ids: set[UUID] = set()
        event_receipt_sha256s: set[str] = set()
        for event_id in sorted(coverage_promotion_event_ids, key=str):
            coverage_event = session.get(SemanticGovernanceEvent, event_id)
            if (
                coverage_event is None
                or coverage_event.event_kind
                != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND
                or coverage_event.agent_task_artifact_id is None
                or coverage_event.receipt_sha256 not in actual_receipt_sha256s
            ):
                return None
            event_artifact_ids.add(coverage_event.agent_task_artifact_id)
            if coverage_event.receipt_sha256:
                event_receipt_sha256s.add(str(coverage_event.receipt_sha256))
        if event_artifact_ids != coverage_promotion_artifact_ids:
            return None
        if coverage_receipt_sha256s and coverage_receipt_sha256s != event_receipt_sha256s:
            return None
    else:
        source_promotion_event_ids = {
            str(value)
            for value in promotion_artifact.payload_json.get("source_escalation_event_ids") or []
        }
    if (
        not waived_event_ids
        or not covered_event_ids
        or not waived_event_ids.issubset(covered_event_ids)
        or not covered_event_ids.issubset(source_promotion_event_ids)
    ):
        return None
    return waiver_artifact_id, waiver_sha256


def closed_replay_alert_fixture_coverage_waiver_keys(
    session: Session,
) -> tuple[set[tuple[UUID, str]], int]:
    closed: set[tuple[UUID, str]] = set()
    invalid_count = 0
    for event in session.scalars(
        select(SemanticGovernanceEvent).where(
            SemanticGovernanceEvent.event_kind
            == CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND
        )
    ):
        valid_key = _valid_replay_alert_fixture_coverage_waiver_closure_event(
            session,
            event,
        )
        if valid_key is None:
            invalid_count += 1
            continue
        closed.add(valid_key)
    return closed, invalid_count


__all__ = [
    "CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND",
    "CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND",
    "CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND",
    "CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_EXPIRING_HOURS",
    "closed_replay_alert_fixture_coverage_waiver_keys",
]
