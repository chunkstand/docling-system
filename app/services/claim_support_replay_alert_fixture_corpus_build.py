from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _uuid_or_none
from app.core.coercion import unique_strings as _string_list
from app.core.hashes import embedded_payload_hash_matches as _hash_matches_embedded_receipt
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.claim_support import ClaimSupportFixtureSet
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.claim_support_payloads import (
    claim_support_fixture_promotion_payload as _promotion_payload,
)
from app.services.claim_support_replay_alert_fixture_corpus import (
    ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME,
    CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND,
    CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND,
)
from app.services.evidence_common import payload_sha256


@dataclass(frozen=True)
class ReplayAlertFixtureCorpusBuild:
    snapshot_payload: dict[str, Any]
    snapshot_sha256: str
    rows: list[dict[str, Any]]
    source_promotion_event_ids: list[str]
    invalid_promotion_event_ids: list[str]


@dataclass(frozen=True)
class ReplayAlertFixturePromotionContext:
    promotion_payload: dict[str, Any]
    fixture_set: ClaimSupportFixtureSet
    artifact: AgentTaskArtifact


def _fixture_by_candidate(
    fixture_set: ClaimSupportFixtureSet,
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    case_id = str(candidate.get("case_id") or "")
    candidate_identity = str(
        candidate.get("candidate_identity_sha256")
        or candidate.get("candidate_id")
        or ""
    )
    fixture_sha256 = str(candidate.get("fixture_sha256") or "")
    for fixture in fixture_set.fixtures_json or []:
        if not isinstance(fixture, dict):
            continue
        replay_source = dict(fixture.get("replay_alert_source") or {})
        if case_id and str(fixture.get("case_id") or "") == case_id:
            return dict(fixture)
        if candidate_identity and candidate_identity in {
            str(replay_source.get("candidate_identity_sha256") or ""),
            str(replay_source.get("candidate_id") or ""),
        }:
            return dict(fixture)
        if fixture_sha256 and payload_sha256(fixture) == fixture_sha256:
            return dict(fixture)
    return None


def _candidate_payloads_for_fixture_set(
    fixture_set: ClaimSupportFixtureSet,
    promotion_payload: dict[str, Any],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    candidates = [
        dict(candidate)
        for candidate in promotion_payload.get("candidates") or []
        if isinstance(candidate, dict)
    ]
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for candidate in candidates:
        fixture = _fixture_by_candidate(fixture_set, candidate)
        if fixture is None or not fixture.get("replay_alert_source"):
            continue
        rows.append((candidate, fixture))
    if rows:
        return rows
    return [
        ({}, dict(fixture))
        for fixture in fixture_set.fixtures_json or []
        if isinstance(fixture, dict) and fixture.get("replay_alert_source")
    ]


def _case_identity_sha256(
    fixture: dict[str, Any],
    candidate: dict[str, Any],
    *,
    fixture_sha256: str,
) -> str:
    replay_source = dict(fixture.get("replay_alert_source") or {})
    candidate_identity = (
        replay_source.get("candidate_identity_sha256")
        or candidate.get("candidate_identity_sha256")
        or candidate.get("candidate_id")
    )
    if candidate_identity:
        return str(candidate_identity)
    return str(
        payload_sha256(
            {
                "case_id": fixture.get("case_id"),
                "fixture_sha256": fixture_sha256,
                "replay_alert_source": replay_source,
            }
        )
    )


def _promotion_context(
    session: Session,
    event: SemanticGovernanceEvent,
) -> tuple[ReplayAlertFixturePromotionContext | None, list[str]]:
    failures: list[str] = []
    promotion_payload = _promotion_payload(event)
    if not promotion_payload:
        return None, ["promotion_payload_missing"]
    payload_receipt = str(promotion_payload.get("receipt_sha256") or "")
    if not payload_receipt or not _hash_matches_embedded_receipt(
        promotion_payload,
        hash_field="receipt_sha256",
    ):
        failures.append("promotion_receipt_hash_mismatch")
    if payload_receipt != str(event.receipt_sha256 or ""):
        failures.append("promotion_event_receipt_mismatch")
    fixture_set_id = _uuid_or_none(promotion_payload.get("fixture_set_id"))
    if fixture_set_id is None:
        failures.append("fixture_set_id_missing")
        return None, failures
    if event.subject_table != "claim_support_fixture_sets" or event.subject_id != fixture_set_id:
        failures.append("promotion_event_subject_mismatch")
    fixture_set = session.get(ClaimSupportFixtureSet, fixture_set_id)
    if fixture_set is None:
        failures.append("fixture_set_missing")
        return None, failures
    if promotion_payload.get("fixture_set_sha256") != fixture_set.fixture_set_sha256:
        failures.append("fixture_set_hash_mismatch")
    try:
        promotion_fixture_count = int(promotion_payload.get("fixture_count") or 0)
    except (TypeError, ValueError):
        promotion_fixture_count = 0
    if promotion_fixture_count != fixture_set.fixture_count:
        failures.append("fixture_set_count_mismatch")
    if event.agent_task_artifact_id is None:
        failures.append("promotion_artifact_missing")
        return None, failures
    artifact = session.get(AgentTaskArtifact, event.agent_task_artifact_id)
    if artifact is None:
        failures.append("promotion_artifact_missing")
        return None, failures
    if artifact.artifact_kind != CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND:
        failures.append("promotion_artifact_kind_mismatch")
    artifact_payload = dict(artifact.payload_json or {})
    artifact_receipt = str(artifact_payload.get("receipt_sha256") or "")
    if artifact_receipt != str(event.receipt_sha256 or ""):
        failures.append("promotion_artifact_receipt_mismatch")
    if not _hash_matches_embedded_receipt(artifact_payload, hash_field="receipt_sha256"):
        failures.append("promotion_artifact_hash_mismatch")
    if failures:
        return None, failures
    return (
        ReplayAlertFixturePromotionContext(
            promotion_payload=promotion_payload,
            fixture_set=fixture_set,
            artifact=artifact,
        ),
        [],
    )


def build_replay_alert_fixture_corpus(
    session: Session,
) -> ReplayAlertFixtureCorpusBuild | None:
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    if not events:
        return None

    rows_by_identity: dict[str, dict[str, Any]] = {}
    source_promotion_event_ids: list[str] = []
    source_promotion_artifact_ids: list[str] = []
    source_promotion_receipt_sha256s: list[str] = []
    source_fixture_set_ids: list[str] = []
    source_fixture_set_sha256s: list[str] = []
    source_escalation_event_ids: list[str] = []
    invalid_promotion_event_ids: list[str] = []
    invalid_promotion_events: list[dict[str, Any]] = []

    for event in events:
        context, failures = _promotion_context(session, event)
        if context is None:
            invalid_promotion_event_ids.append(str(event.id))
            invalid_promotion_events.append(
                {
                    "event_id": str(event.id),
                    "event_hash": event.event_hash,
                    "receipt_sha256": event.receipt_sha256,
                    "failures": failures,
                }
            )
            continue
        promotion_payload = context.promotion_payload
        fixture_set = context.fixture_set
        artifact = context.artifact
        event_id = str(event.id)
        source_promotion_event_ids.append(event_id)
        source_promotion_artifact_ids.append(str(artifact.id))
        if event.receipt_sha256:
            source_promotion_receipt_sha256s.append(str(event.receipt_sha256))
        source_fixture_set_ids.append(str(fixture_set.id))
        source_fixture_set_sha256s.append(fixture_set.fixture_set_sha256)
        source_escalation_event_ids.extend(
            _string_list(promotion_payload.get("source_escalation_event_ids") or [])
        )

        candidate_fixture_rows = _candidate_payloads_for_fixture_set(
            fixture_set,
            promotion_payload,
        )
        if promotion_payload.get("candidates") and not candidate_fixture_rows:
            invalid_promotion_event_ids.append(str(event.id))
            invalid_promotion_events.append(
                {
                    "event_id": str(event.id),
                    "event_hash": event.event_hash,
                    "receipt_sha256": event.receipt_sha256,
                    "failures": ["promotion_candidate_fixture_missing"],
                }
            )
            continue

        for candidate, fixture in candidate_fixture_rows:
            fixture_sha256 = str(candidate.get("fixture_sha256") or payload_sha256(fixture))
            case_identity_sha256 = _case_identity_sha256(
                fixture,
                candidate,
                fixture_sha256=fixture_sha256,
            )
            row_source_change_impact_ids = _string_list([candidate.get("change_impact_id")])
            row_source_escalation_event_ids = _string_list(
                [
                    *(candidate.get("escalation_event_ids") or []),
                    candidate.get("latest_escalation_event_id"),
                ]
            )
            rows_by_identity[case_identity_sha256] = {
                "case_id": str(fixture.get("case_id") or candidate.get("case_id") or ""),
                "case_identity_sha256": case_identity_sha256,
                "fixture_sha256": fixture_sha256,
                "fixture": fixture,
                "fixture_set_id": str(fixture_set.id),
                "promotion_event_id": event_id,
                "promotion_artifact_id": str(artifact.id),
                "promotion_receipt_sha256": event.receipt_sha256,
                "source_change_impact_ids": row_source_change_impact_ids,
                "source_escalation_event_ids": row_source_escalation_event_ids,
                "replay_alert_source": dict(fixture.get("replay_alert_source") or {}),
            }

    rows = sorted(
        rows_by_identity.values(),
        key=lambda row: (
            str(row.get("case_id") or ""),
            str(row.get("case_identity_sha256") or ""),
        ),
    )
    row_payloads = [
        {
            "case_id": row["case_id"],
            "case_identity_sha256": row["case_identity_sha256"],
            "fixture_sha256": row["fixture_sha256"],
            "fixture_set_id": row["fixture_set_id"],
            "promotion_event_id": row["promotion_event_id"],
            "promotion_artifact_id": row["promotion_artifact_id"],
            "promotion_receipt_sha256": row["promotion_receipt_sha256"],
            "source_change_impact_ids": row["source_change_impact_ids"],
            "source_escalation_event_ids": row["source_escalation_event_ids"],
        }
        for row in rows
    ]
    snapshot_payload = {
        "schema_name": "claim_support_replay_alert_fixture_corpus_snapshot",
        "schema_version": "1.0",
        "snapshot_name": ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME,
        "fixture_count": len(rows),
        "promotion_event_count": len(_string_list(source_promotion_event_ids)),
        "promotion_fixture_set_count": len(_string_list(source_fixture_set_ids)),
        "invalid_promotion_event_count": len(_string_list(invalid_promotion_event_ids)),
        "source_promotion_event_ids": _string_list(source_promotion_event_ids),
        "source_promotion_artifact_ids": _string_list(source_promotion_artifact_ids),
        "source_promotion_receipt_sha256s": _string_list(
            source_promotion_receipt_sha256s
        ),
        "source_fixture_set_ids": _string_list(source_fixture_set_ids),
        "source_fixture_set_sha256s": _string_list(source_fixture_set_sha256s),
        "source_escalation_event_ids": _string_list(source_escalation_event_ids),
        "invalid_promotion_event_ids": _string_list(invalid_promotion_event_ids),
        "invalid_promotion_events": invalid_promotion_events,
        "rows": row_payloads,
    }
    return ReplayAlertFixtureCorpusBuild(
        snapshot_payload=snapshot_payload,
        snapshot_sha256=str(payload_sha256(snapshot_payload)),
        rows=rows,
        source_promotion_event_ids=snapshot_payload["source_promotion_event_ids"],
        invalid_promotion_event_ids=snapshot_payload["invalid_promotion_event_ids"],
    )
