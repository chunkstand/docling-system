# ruff: noqa: F401, I001
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTaskArtifact,
    ClaimSupportPolicyChangeImpact,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation,
    ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
    SemanticGovernanceEvent,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_constants import (
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND,
)

def _claim_support_replay_alert_waiver_closure_events_by_impact(
    session: Session,
    rows: list[ClaimSupportPolicyChangeImpact],
) -> dict[UUID, list[SemanticGovernanceEvent]]:
    row_ids = {str(row.id) for row in rows}
    if not row_ids:
        return {}
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    rows_by_id = {str(row.id): row for row in rows}
    for event in events:
        closure_payload = (event.event_payload_json or {}).get(
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ) or {}
        source_change_impact_ids = {
            str(value) for value in closure_payload.get("source_change_impact_ids") or [] if value
        }
        for row_id in sorted(source_change_impact_ids & row_ids):
            events_by_row.setdefault(rows_by_id[row_id].id, []).append(event)
    return events_by_row


def _waiver_closure_event_integrity(
    session: Session,
    event: SemanticGovernanceEvent,
    closure_payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    receipt_sha256 = str(closure_payload.get("receipt_sha256") or "")
    receipt_basis = dict(closure_payload)
    receipt_basis.pop("receipt_sha256", None)
    if not receipt_sha256 or payload_sha256(receipt_basis) != receipt_sha256:
        failures.append("closure_receipt_hash_mismatch")
    if event.receipt_sha256 != receipt_sha256:
        failures.append("event_receipt_hash_mismatch")

    closure_artifact = (
        session.get(AgentTaskArtifact, event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None
    )
    if closure_artifact is None:
        failures.append("closure_artifact_missing")
    elif (
        closure_artifact.artifact_kind
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND
    ):
        failures.append("closure_artifact_kind_mismatch")
    elif closure_artifact.payload_json.get("receipt_sha256") != receipt_sha256:
        failures.append("closure_artifact_receipt_mismatch")

    waiver_artifact_id = closure_payload.get("waiver_artifact_id")
    try:
        waiver_artifact_uuid = UUID(str(waiver_artifact_id)) if waiver_artifact_id else None
    except (TypeError, ValueError):
        waiver_artifact_uuid = None
    waiver_artifact = (
        session.get(AgentTaskArtifact, waiver_artifact_uuid) if waiver_artifact_uuid else None
    )
    if waiver_artifact is None:
        failures.append("waiver_artifact_missing")
    elif (
        waiver_artifact.artifact_kind
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND
    ):
        failures.append("waiver_artifact_kind_mismatch")
    elif waiver_artifact.payload_json.get("waiver_sha256") != closure_payload.get("waiver_sha256"):
        failures.append("waiver_artifact_hash_mismatch")

    promotion_artifact_id = closure_payload.get("promotion_artifact_id")
    try:
        promotion_artifact_uuid = (
            UUID(str(promotion_artifact_id)) if promotion_artifact_id else None
        )
    except (TypeError, ValueError):
        promotion_artifact_uuid = None
    promotion_event_id = closure_payload.get("promotion_event_id")
    try:
        promotion_event_uuid = UUID(str(promotion_event_id)) if promotion_event_id else None
    except (TypeError, ValueError):
        promotion_event_uuid = None
    promotion_artifact = (
        session.get(AgentTaskArtifact, promotion_artifact_uuid) if promotion_artifact_uuid else None
    )
    promotion_event = (
        session.get(SemanticGovernanceEvent, promotion_event_uuid) if promotion_event_uuid else None
    )
    if promotion_artifact is None:
        failures.append("promotion_artifact_missing")
    elif (
        promotion_artifact.artifact_kind
        != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
    ):
        failures.append("promotion_artifact_kind_mismatch")
    elif promotion_artifact.payload_json.get("receipt_sha256") != closure_payload.get(
        "promotion_receipt_sha256"
    ):
        failures.append("promotion_artifact_receipt_mismatch")
    if promotion_event is None:
        failures.append("promotion_event_missing")
    elif promotion_event.event_kind != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND:
        failures.append("promotion_event_kind_mismatch")
    elif promotion_event.agent_task_artifact_id != promotion_artifact_uuid:
        failures.append("promotion_event_artifact_mismatch")
    elif promotion_event.receipt_sha256 != closure_payload.get("promotion_receipt_sha256"):
        failures.append("promotion_event_receipt_mismatch")

    waived_event_ids = set(_string_values(closure_payload.get("waived_escalation_event_ids") or []))
    covered_event_ids = set(
        _string_values(closure_payload.get("covered_escalation_event_ids") or [])
    )
    if not waived_event_ids:
        failures.append("waived_escalation_event_set_missing")
    if not covered_event_ids:
        failures.append("covered_escalation_event_set_missing")
    if waived_event_ids and not waived_event_ids.issubset(covered_event_ids):
        failures.append("covered_escalation_event_set_incomplete")

    raw_coverage_promotion_artifact_ids = set(
        _string_values(closure_payload.get("coverage_promotion_artifact_ids") or [])
    )
    coverage_promotion_artifact_ids = set(_uuid_values(raw_coverage_promotion_artifact_ids))
    if raw_coverage_promotion_artifact_ids and len(coverage_promotion_artifact_ids) != len(
        raw_coverage_promotion_artifact_ids
    ):
        failures.append("coverage_promotion_artifact_id_invalid")
    if promotion_artifact_uuid is not None:
        coverage_promotion_artifact_ids.add(promotion_artifact_uuid)
    promotion_source_escalation_event_ids: set[str] = set()
    actual_coverage_receipt_sha256s: set[str] = set()
    for coverage_artifact_id in sorted(coverage_promotion_artifact_ids, key=str):
        coverage_artifact = session.get(AgentTaskArtifact, coverage_artifact_id)
        if coverage_artifact is None:
            failures.append("coverage_promotion_artifact_missing")
            continue
        if (
            coverage_artifact.artifact_kind
            != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
        ):
            failures.append("coverage_promotion_artifact_kind_mismatch")
            continue
        receipt_sha = str(coverage_artifact.payload_json.get("receipt_sha256") or "")
        if receipt_sha:
            actual_coverage_receipt_sha256s.add(receipt_sha)
        promotion_source_escalation_event_ids.update(
            _string_values(coverage_artifact.payload_json.get("source_escalation_event_ids") or [])
        )
    declared_coverage_receipt_sha256s = set(
        _string_values(closure_payload.get("coverage_promotion_receipt_sha256s") or [])
    )
    if (
        declared_coverage_receipt_sha256s
        and declared_coverage_receipt_sha256s != actual_coverage_receipt_sha256s
    ):
        failures.append("coverage_promotion_receipt_set_mismatch")
    if covered_event_ids and not covered_event_ids.issubset(promotion_source_escalation_event_ids):
        failures.append("covered_escalation_event_not_in_promotion")
    raw_coverage_promotion_event_ids = set(
        _string_values(closure_payload.get("coverage_promotion_event_ids") or [])
    )
    declared_coverage_event_ids = set(_uuid_values(raw_coverage_promotion_event_ids))
    if raw_coverage_promotion_event_ids and len(declared_coverage_event_ids) != len(
        raw_coverage_promotion_event_ids
    ):
        failures.append("coverage_promotion_event_id_invalid")
    if not declared_coverage_event_ids and promotion_event_uuid is not None:
        declared_coverage_event_ids.add(promotion_event_uuid)
    coverage_event_artifact_ids: set[UUID] = set()
    coverage_event_receipt_sha256s: set[str] = set()
    for coverage_event_id in sorted(declared_coverage_event_ids, key=str):
        coverage_event = session.get(SemanticGovernanceEvent, coverage_event_id)
        if coverage_event is None:
            failures.append("coverage_promotion_event_missing")
            continue
        if coverage_event.event_kind != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND:
            failures.append("coverage_promotion_event_kind_mismatch")
            continue
        if coverage_event.agent_task_artifact_id is None:
            failures.append("coverage_promotion_event_artifact_missing")
            continue
        coverage_event_artifact_ids.add(coverage_event.agent_task_artifact_id)
        receipt_sha = str(coverage_event.receipt_sha256 or "")
        if receipt_sha:
            coverage_event_receipt_sha256s.add(receipt_sha)
        if receipt_sha and receipt_sha not in actual_coverage_receipt_sha256s:
            failures.append("coverage_promotion_event_receipt_mismatch")
    if (
        coverage_event_artifact_ids
        and coverage_event_artifact_ids != coverage_promotion_artifact_ids
    ):
        failures.append("coverage_promotion_event_artifact_set_mismatch")
    if (
        declared_coverage_receipt_sha256s
        and coverage_event_receipt_sha256s
        and declared_coverage_receipt_sha256s != coverage_event_receipt_sha256s
    ):
        failures.append("coverage_promotion_event_receipt_set_mismatch")
    return not failures, failures


def _waiver_closure_event_payload(
    session: Session,
    event: SemanticGovernanceEvent,
) -> dict[str, Any]:
    closure_payload = (event.event_payload_json or {}).get(
        "claim_support_replay_alert_fixture_coverage_waiver_closure"
    ) or {}
    integrity_verified, integrity_failures = _waiver_closure_event_integrity(
        session,
        event,
        closure_payload,
    )
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "agent_task_artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "payload_sha256": event.payload_sha256,
        "waiver_artifact_id": closure_payload.get("waiver_artifact_id"),
        "waiver_sha256": closure_payload.get("waiver_sha256"),
        "closure_status": closure_payload.get("closure_status"),
        "promotion_event_id": closure_payload.get("promotion_event_id"),
        "promotion_receipt_sha256": closure_payload.get("promotion_receipt_sha256"),
        "promotion_artifact_id": closure_payload.get("promotion_artifact_id"),
        "coverage_promotion_event_ids": list(
            closure_payload.get("coverage_promotion_event_ids") or []
        ),
        "coverage_promotion_artifact_ids": list(
            closure_payload.get("coverage_promotion_artifact_ids") or []
        ),
        "coverage_promotion_receipt_sha256s": list(
            closure_payload.get("coverage_promotion_receipt_sha256s") or []
        ),
        "fixture_set_id": closure_payload.get("fixture_set_id"),
        "fixture_set_sha256": closure_payload.get("fixture_set_sha256"),
        "covered_escalation_event_ids": list(
            closure_payload.get("covered_escalation_event_ids") or []
        ),
        "integrity_verified": integrity_verified,
        "integrity_failures": integrity_failures,
    }


def _replay_alert_fixture_corpus_snapshot_governance_integrity(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> dict[str, Any]:
    failures: list[str] = []
    snapshot_payload = dict(snapshot.snapshot_payload_json or {})
    if payload_sha256(snapshot_payload) != snapshot.snapshot_sha256:
        failures.append("snapshot_payload_hash_mismatch")
    db_rows = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .order_by(
                ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc(),
                ClaimSupportReplayAlertFixtureCorpusRow.id.asc(),
            )
        )
    )
    declared_rows = [
        dict(row) for row in snapshot_payload.get("rows") or [] if isinstance(row, dict)
    ]
    db_row_payloads = [
        {
            "case_id": row.case_id,
            "case_identity_sha256": row.case_identity_sha256,
            "fixture_sha256": row.fixture_sha256,
            "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
            "promotion_event_id": (str(row.promotion_event_id) if row.promotion_event_id else None),
            "promotion_artifact_id": (
                str(row.promotion_artifact_id) if row.promotion_artifact_id else None
            ),
            "promotion_receipt_sha256": row.promotion_receipt_sha256,
            "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
            "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        }
        for row in db_rows
    ]
    if len(declared_rows) != snapshot.fixture_count:
        failures.append("snapshot_payload_row_count_mismatch")
    if len(db_rows) != snapshot.fixture_count:
        failures.append("snapshot_db_row_count_mismatch")
    if declared_rows != db_row_payloads:
        failures.append("snapshot_db_row_payload_mismatch")
    fixture_hash_mismatch_count = sum(
        1 for row in db_rows if payload_sha256(row.fixture_json or {}) != row.fixture_sha256
    )
    if fixture_hash_mismatch_count:
        failures.append("snapshot_db_fixture_hash_mismatch")
    event = (
        session.get(SemanticGovernanceEvent, snapshot.semantic_governance_event_id)
        if snapshot.semantic_governance_event_id is not None
        else None
    )
    artifact = (
        session.get(AgentTaskArtifact, snapshot.governance_artifact_id)
        if snapshot.governance_artifact_id is not None
        else None
    )
    if event is None:
        failures.append("snapshot_governance_event_missing")
    elif event.event_kind != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND:
        failures.append("snapshot_governance_event_kind_mismatch")
    elif (
        event.subject_table != "claim_support_replay_alert_fixture_corpus_snapshots"
        or event.subject_id != snapshot.id
    ):
        failures.append("snapshot_governance_event_subject_mismatch")
    if artifact is None:
        failures.append("snapshot_governance_artifact_missing")
    elif artifact.artifact_kind != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND:
        failures.append("snapshot_governance_artifact_kind_mismatch")

    if event is not None:
        event_payload = dict(
            (event.event_payload_json or {}).get(
                CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY
            )
            or {}
        )
        receipt_sha256 = str(event_payload.get("receipt_sha256") or "")
        event_basis = dict(event_payload)
        event_basis.pop("receipt_sha256", None)
        if event.receipt_sha256 != snapshot.governance_receipt_sha256:
            failures.append("snapshot_governance_event_receipt_mismatch")
        if event.receipt_sha256 != receipt_sha256:
            failures.append("snapshot_governance_event_payload_receipt_mismatch")
        if not receipt_sha256 or payload_sha256(event_basis) != receipt_sha256:
            failures.append("snapshot_governance_event_payload_hash_mismatch")
        if event_payload.get("snapshot_id") != str(snapshot.id):
            failures.append("snapshot_governance_event_snapshot_id_mismatch")
        if event_payload.get("snapshot_sha256") != snapshot.snapshot_sha256:
            failures.append("snapshot_governance_event_snapshot_hash_mismatch")
    if artifact is not None:
        artifact_payload = dict(artifact.payload_json or {})
        artifact_receipt_sha256 = str(artifact_payload.get("receipt_sha256") or "")
        artifact_basis = dict(artifact_payload)
        artifact_basis.pop("receipt_sha256", None)
        if artifact_receipt_sha256 != snapshot.governance_receipt_sha256:
            failures.append("snapshot_governance_artifact_receipt_mismatch")
        if not artifact_receipt_sha256 or payload_sha256(artifact_basis) != artifact_receipt_sha256:
            failures.append("snapshot_governance_artifact_hash_mismatch")
        if artifact_payload.get("snapshot_id") != str(snapshot.id):
            failures.append("snapshot_governance_artifact_snapshot_id_mismatch")
        if artifact_payload.get("snapshot_sha256") != snapshot.snapshot_sha256:
            failures.append("snapshot_governance_artifact_snapshot_hash_mismatch")
        if event is not None and event.agent_task_artifact_id != artifact.id:
            failures.append("snapshot_governance_event_artifact_mismatch")
    return {
        "complete": not failures,
        "failures": failures,
        "semantic_governance_event_id": (
            str(snapshot.semantic_governance_event_id)
            if snapshot.semantic_governance_event_id
            else None
        ),
        "governance_artifact_id": (
            str(snapshot.governance_artifact_id) if snapshot.governance_artifact_id else None
        ),
        "governance_receipt_sha256": snapshot.governance_receipt_sha256,
        "snapshot_payload_sha256": payload_sha256(snapshot_payload),
        "stored_snapshot_sha256": snapshot.snapshot_sha256,
        "declared_row_count": len(declared_rows),
        "db_row_count": len(db_rows),
        "fixture_hash_mismatch_count": fixture_hash_mismatch_count,
    }


def _replay_alert_fixture_corpus_row_payload(
    row: ClaimSupportReplayAlertFixtureCorpusRow,
) -> dict[str, Any]:
    return {
        "row_id": str(row.id),
        "snapshot_id": str(row.snapshot_id),
        "row_index": row.row_index,
        "case_id": row.case_id,
        "case_identity_sha256": row.case_identity_sha256,
        "fixture_sha256": row.fixture_sha256,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "promotion_event_id": (str(row.promotion_event_id) if row.promotion_event_id else None),
        "promotion_artifact_id": (
            str(row.promotion_artifact_id) if row.promotion_artifact_id else None
        ),
        "promotion_receipt_sha256": row.promotion_receipt_sha256,
        "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        "replay_alert_source": dict(row.replay_alert_source_json or {}),
    }


def _replay_alert_fixture_corpus_snapshot_payload(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> dict[str, Any]:
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
    governance_integrity = _replay_alert_fixture_corpus_snapshot_governance_integrity(
        session,
        snapshot,
    )
    return {
        "snapshot_id": str(snapshot.id),
        "snapshot_name": snapshot.snapshot_name,
        "status": snapshot.status,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "semantic_governance_event_id": (
            str(snapshot.semantic_governance_event_id)
            if snapshot.semantic_governance_event_id
            else None
        ),
        "governance_artifact_id": (
            str(snapshot.governance_artifact_id) if snapshot.governance_artifact_id else None
        ),
        "governance_receipt_sha256": snapshot.governance_receipt_sha256,
        "fixture_count": snapshot.fixture_count,
        "promotion_event_count": snapshot.promotion_event_count,
        "promotion_fixture_set_count": snapshot.promotion_fixture_set_count,
        "invalid_promotion_event_count": snapshot.invalid_promotion_event_count,
        "source_promotion_event_ids": list(snapshot.source_promotion_event_ids_json or []),
        "source_promotion_artifact_ids": list(snapshot.source_promotion_artifact_ids_json or []),
        "source_promotion_receipt_sha256s": list(
            snapshot.source_promotion_receipt_sha256s_json or []
        ),
        "source_fixture_set_ids": list(snapshot.source_fixture_set_ids_json or []),
        "source_fixture_set_sha256s": list(snapshot.source_fixture_set_sha256s_json or []),
        "source_escalation_event_ids": list(snapshot.source_escalation_event_ids_json or []),
        "invalid_promotion_event_ids": list(snapshot.invalid_promotion_event_ids_json or []),
        "invalid_promotion_events": list(
            (snapshot.snapshot_payload_json or {}).get("invalid_promotion_events") or []
        ),
        "rows": [_replay_alert_fixture_corpus_row_payload(row) for row in rows],
        "row_count": len(rows),
        "governance_integrity": governance_integrity,
        "trace_complete": bool(rows) and governance_integrity["complete"],
    }


def _claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event(
    session: Session,
    events: list[SemanticGovernanceEvent],
) -> dict[UUID, list[dict[str, Any]]]:
    event_ids = {event.id for event in events}
    if not event_ids:
        return {}
    snapshots = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusSnapshot).order_by(
                ClaimSupportReplayAlertFixtureCorpusSnapshot.created_at.asc(),
                ClaimSupportReplayAlertFixtureCorpusSnapshot.id.asc(),
            )
        )
    )
    by_event_id: dict[UUID, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        source_event_ids = {
            parsed
            for parsed in (
                _uuid_or_none_safe(value)
                for value in (snapshot.source_promotion_event_ids_json or [])
            )
            if parsed is not None
        }
        matching_event_ids = event_ids & source_event_ids
        if not matching_event_ids:
            continue
        payload = _replay_alert_fixture_corpus_snapshot_payload(session, snapshot)
        for event_id in sorted(matching_event_ids, key=str):
            by_event_id.setdefault(event_id, []).append(payload)
    return by_event_id


def _claim_support_replay_alert_waiver_lifecycle_summary(
    session: Session,
    matching_rows: list[ClaimSupportPolicyChangeImpact],
    waiver_closure_events_by_row: dict[UUID, list[SemanticGovernanceEvent]],
) -> dict[str, Any]:
    row_ids = {str(row.id) for row in matching_rows}
    row_uuids = [row.id for row in matching_rows]
    ledger_ids_from_escalations = set(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.ledger_id).where(
                ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.change_impact_id.in_(
                    row_uuids
                )
            )
        )
    )
    related_ledgers = [
        ledger
        for ledger in session.scalars(
            select(ClaimSupportReplayAlertFixtureCoverageWaiverLedger).order_by(
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.created_at.asc(),
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.id.asc(),
            )
        )
        if row_ids & {str(value) for value in (ledger.source_change_impact_ids_json or []) if value}
        or ledger.id in ledger_ids_from_escalations
    ]
    closure_events_by_id = {
        event.id: event for events in waiver_closure_events_by_row.values() for event in events
    }
    invalid_closure_event_ids: set[UUID] = set()
    for event in closure_events_by_id.values():
        closure_payload = (event.event_payload_json or {}).get(
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ) or {}
        integrity_verified, _failures = _waiver_closure_event_integrity(
            session,
            event,
            closure_payload,
        )
        if not integrity_verified:
            invalid_closure_event_ids.add(event.id)

    for ledger in related_ledgers:
        if not ledger.coverage_complete:
            continue
        if ledger.closure_event_id is None:
            continue
        event = session.get(SemanticGovernanceEvent, ledger.closure_event_id)
        if event is None:
            invalid_closure_event_ids.add(ledger.closure_event_id)
            continue
        closure_payload = (event.event_payload_json or {}).get(
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ) or {}
        integrity_verified, _failures = _waiver_closure_event_integrity(
            session,
            event,
            closure_payload,
        )
        if not integrity_verified:
            invalid_closure_event_ids.add(event.id)

    unresolved_ledgers = [
        ledger
        for ledger in related_ledgers
        if ledger.waived_escalation_event_count > 0 and not ledger.coverage_complete
    ]
    closed_ledgers = [
        ledger
        for ledger in related_ledgers
        if ledger.waived_escalation_event_count > 0 and ledger.coverage_complete
    ]
    invalid_closed_ledgers = [
        ledger
        for ledger in closed_ledgers
        if ledger.closure_event_id is None or ledger.closure_event_id in invalid_closure_event_ids
    ]
    invalid_waiver_closure_count = len(
        {
            *invalid_closure_event_ids,
            *[ledger.id for ledger in invalid_closed_ledgers if ledger.closure_event_id is None],
        }
    )
    waiver_closure_integrity_verified = invalid_waiver_closure_count == 0
    clear = not unresolved_ledgers and waiver_closure_integrity_verified
    return {
        "related_waiver_count": len(related_ledgers),
        "unresolved_waiver_count": len(unresolved_ledgers),
        "closed_waiver_count": len(closed_ledgers),
        "invalid_waiver_closure_count": invalid_waiver_closure_count,
        "waiver_closure_integrity_verified": waiver_closure_integrity_verified,
        "clear": clear,
        "related_waiver_ledger_ids": [str(ledger.id) for ledger in related_ledgers],
        "unresolved_waiver_ledger_ids": [str(ledger.id) for ledger in unresolved_ledgers],
        "closed_waiver_ledger_ids": [str(ledger.id) for ledger in closed_ledgers],
        "invalid_waiver_closure_event_ids": [
            str(event_id) for event_id in sorted(invalid_closure_event_ids, key=str)
        ],
    }


claim_support_replay_alert_waiver_closure_events_by_impact = (
    _claim_support_replay_alert_waiver_closure_events_by_impact
)
waiver_closure_event_integrity = _waiver_closure_event_integrity
waiver_closure_event_payload = _waiver_closure_event_payload
replay_alert_fixture_corpus_snapshot_governance_integrity = (
    _replay_alert_fixture_corpus_snapshot_governance_integrity
)
replay_alert_fixture_corpus_row_payload = _replay_alert_fixture_corpus_row_payload
replay_alert_fixture_corpus_snapshot_payload = _replay_alert_fixture_corpus_snapshot_payload
claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event = (
    _claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event
)
claim_support_replay_alert_waiver_lifecycle_summary = (
    _claim_support_replay_alert_waiver_lifecycle_summary
)
