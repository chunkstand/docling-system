from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    AgentTaskArtifact,
    ClaimSupportFixtureSet,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
)
from app.services.evidence import payload_sha256

ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME = (
    "active_claim_support_replay_alert_fixtures"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED.value
)


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


def _uuid_or_none(value: object) -> UUID | None:
    if value in {None, ""}:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _string_list(values) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values or []:
        if value in {None, ""}:
            continue
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def _promotion_payload(event: SemanticGovernanceEvent) -> dict[str, Any]:
    return dict(
        (event.event_payload_json or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        )
        or {}
    )


def _hash_matches_embedded_receipt(payload: dict[str, Any], *, hash_field: str) -> bool:
    expected_hash = str(payload.get(hash_field) or "")
    if not expected_hash:
        return False
    basis = dict(payload)
    basis.pop(hash_field, None)
    return payload_sha256(basis) == expected_hash


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
        if artifact is not None:
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
            row_source_change_impact_ids = _string_list(
                [
                    candidate.get("change_impact_id"),
                ]
            )
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
                "promotion_artifact_id": str(artifact.id) if artifact is not None else None,
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


def _active_snapshot(
    session: Session,
) -> ClaimSupportReplayAlertFixtureCorpusSnapshot | None:
    return session.scalar(
        select(ClaimSupportReplayAlertFixtureCorpusSnapshot)
        .where(
            ClaimSupportReplayAlertFixtureCorpusSnapshot.snapshot_name
            == ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME,
            ClaimSupportReplayAlertFixtureCorpusSnapshot.status == "active",
        )
        .order_by(
            ClaimSupportReplayAlertFixtureCorpusSnapshot.created_at.desc(),
            ClaimSupportReplayAlertFixtureCorpusSnapshot.id.desc(),
        )
        .limit(1)
    )


def _supersede_active_snapshots(session: Session) -> None:
    now = utcnow()
    session.execute(
        update(ClaimSupportReplayAlertFixtureCorpusSnapshot)
        .where(
            ClaimSupportReplayAlertFixtureCorpusSnapshot.snapshot_name
            == ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME,
            ClaimSupportReplayAlertFixtureCorpusSnapshot.status == "active",
        )
        .values(status="superseded", superseded_at=now)
    )
    session.flush()


def ensure_active_replay_alert_fixture_corpus_snapshot(
    session: Session,
) -> ClaimSupportReplayAlertFixtureCorpusSnapshot | None:
    build = build_replay_alert_fixture_corpus(session)
    if build is None:
        _supersede_active_snapshots(session)
        return None
    if not build.source_promotion_event_ids and not build.invalid_promotion_event_ids:
        _supersede_active_snapshots(session)
        return None

    active = _active_snapshot(session)
    if active is not None and active.snapshot_sha256 == build.snapshot_sha256:
        return active

    existing = session.scalar(
        select(ClaimSupportReplayAlertFixtureCorpusSnapshot)
        .where(
            ClaimSupportReplayAlertFixtureCorpusSnapshot.snapshot_sha256
            == build.snapshot_sha256
        )
        .limit(1)
    )
    now = utcnow()
    session.execute(
        update(ClaimSupportReplayAlertFixtureCorpusSnapshot)
        .where(
            ClaimSupportReplayAlertFixtureCorpusSnapshot.snapshot_name
            == ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME,
            ClaimSupportReplayAlertFixtureCorpusSnapshot.status == "active",
            ClaimSupportReplayAlertFixtureCorpusSnapshot.snapshot_sha256
            != build.snapshot_sha256,
        )
        .values(status="superseded", superseded_at=now)
    )
    if existing is not None:
        existing.status = "active"
        existing.superseded_at = None
        session.flush()
        return existing

    snapshot = ClaimSupportReplayAlertFixtureCorpusSnapshot(
        snapshot_name=ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME,
        status="active",
        snapshot_sha256=build.snapshot_sha256,
        fixture_count=int(build.snapshot_payload["fixture_count"]),
        promotion_event_count=int(build.snapshot_payload["promotion_event_count"]),
        promotion_fixture_set_count=int(
            build.snapshot_payload["promotion_fixture_set_count"]
        ),
        invalid_promotion_event_count=int(
            build.snapshot_payload["invalid_promotion_event_count"]
        ),
        source_promotion_event_ids_json=build.snapshot_payload[
            "source_promotion_event_ids"
        ],
        source_promotion_artifact_ids_json=build.snapshot_payload[
            "source_promotion_artifact_ids"
        ],
        source_promotion_receipt_sha256s_json=build.snapshot_payload[
            "source_promotion_receipt_sha256s"
        ],
        source_fixture_set_ids_json=build.snapshot_payload["source_fixture_set_ids"],
        source_fixture_set_sha256s_json=build.snapshot_payload[
            "source_fixture_set_sha256s"
        ],
        source_escalation_event_ids_json=build.snapshot_payload[
            "source_escalation_event_ids"
        ],
        invalid_promotion_event_ids_json=build.snapshot_payload[
            "invalid_promotion_event_ids"
        ],
        snapshot_payload_json=build.snapshot_payload,
        created_at=now,
    )
    session.add(snapshot)
    session.flush()
    for index, row in enumerate(build.rows, start=1):
        session.add(
            ClaimSupportReplayAlertFixtureCorpusRow(
                snapshot_id=snapshot.id,
                row_index=index,
                case_id=row["case_id"],
                case_identity_sha256=row["case_identity_sha256"],
                fixture_sha256=row["fixture_sha256"],
                fixture_json=row["fixture"],
                fixture_set_id=_uuid_or_none(row.get("fixture_set_id")),
                promotion_event_id=_uuid_or_none(row.get("promotion_event_id")),
                promotion_artifact_id=_uuid_or_none(row.get("promotion_artifact_id")),
                promotion_receipt_sha256=row.get("promotion_receipt_sha256"),
                source_change_impact_ids_json=row["source_change_impact_ids"],
                source_escalation_event_ids_json=row["source_escalation_event_ids"],
                replay_alert_source_json=row["replay_alert_source"],
                created_at=now,
            )
        )
    session.flush()
    return snapshot


def replay_alert_fixture_corpus_snapshot_summary(
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot | None,
) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "snapshot_id": str(snapshot.id),
        "snapshot_name": snapshot.snapshot_name,
        "status": snapshot.status,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "fixture_count": snapshot.fixture_count,
        "promotion_event_count": snapshot.promotion_event_count,
        "promotion_fixture_set_count": snapshot.promotion_fixture_set_count,
        "invalid_promotion_event_count": snapshot.invalid_promotion_event_count,
        "source_promotion_event_ids": list(snapshot.source_promotion_event_ids_json),
        "source_promotion_artifact_ids": list(snapshot.source_promotion_artifact_ids_json),
        "source_promotion_receipt_sha256s": list(
            snapshot.source_promotion_receipt_sha256s_json
        ),
        "source_fixture_set_ids": list(snapshot.source_fixture_set_ids_json),
        "source_fixture_set_sha256s": list(snapshot.source_fixture_set_sha256s_json),
        "source_escalation_event_ids": list(snapshot.source_escalation_event_ids_json),
        "invalid_promotion_event_ids": list(snapshot.invalid_promotion_event_ids_json),
        "invalid_promotion_events": list(
            (snapshot.snapshot_payload_json or {}).get("invalid_promotion_events") or []
        ),
        "created_at": snapshot.created_at.isoformat(),
        "superseded_at": snapshot.superseded_at.isoformat()
        if snapshot.superseded_at
        else None,
    }


def active_replay_alert_fixture_corpus_snapshot_summary(
    session: Session,
    *,
    ensure_current: bool = True,
) -> dict[str, Any] | None:
    snapshot = (
        ensure_active_replay_alert_fixture_corpus_snapshot(session)
        if ensure_current
        else _active_snapshot(session)
    )
    return replay_alert_fixture_corpus_snapshot_summary(snapshot)


def active_replay_alert_fixture_corpus_rows(
    session: Session,
    *,
    exclude_case_ids: set[str] | None = None,
    limit: int = 100,
) -> tuple[
    ClaimSupportReplayAlertFixtureCorpusSnapshot | None,
    list[ClaimSupportReplayAlertFixtureCorpusRow],
    int,
]:
    snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(session)
    if snapshot is None:
        return None, [], 0
    rows = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .order_by(
                ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc(),
                ClaimSupportReplayAlertFixtureCorpusRow.id.asc(),
            )
        )
    )
    exclude_case_ids = set(exclude_case_ids or set())
    available = [
        row for row in rows if str(row.case_id or "") not in exclude_case_ids
    ]
    return snapshot, available[: max(0, limit)], len(available)
