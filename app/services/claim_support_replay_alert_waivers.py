from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _uuid_or_none
from app.core.coercion import sorted_unique_strings as _string_list
from app.core.time import coerce_utc_datetime as _coerce_utc_datetime
from app.core.time import utcnow
from app.db.models import (
    AgentTaskArtifact,
    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation,
    ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
    SemanticGovernanceEvent,
)
from app.services.evidence import payload_sha256


def replay_alert_escalation_set_sha256(escalation_event_ids: list[str]) -> str:
    return str(
        payload_sha256(
            {
                "schema_name": "claim_support_replay_alert_escalation_set",
                "schema_version": "1.0",
                "escalation_event_ids": sorted(escalation_event_ids),
            }
        )
    )


def _waiver_stale_escalation_rows(waiver_payload: dict[str, Any]) -> list[dict[str, Any]]:
    direct_rows = waiver_payload.get("stale_unconverted_escalation_events")
    if isinstance(direct_rows, list):
        return [row for row in direct_rows if isinstance(row, dict)]
    summary = dict(waiver_payload.get("replay_alert_fixture_summary") or {})
    summary_rows = summary.get("stale_unconverted_escalation_events")
    if isinstance(summary_rows, list):
        return [row for row in summary_rows if isinstance(row, dict)]
    rows = summary.get("unconverted_escalation_events") or []
    return [
        row
        for row in rows
        if isinstance(row, dict) and row.get("is_stale") and row.get("event_id")
    ]


def stale_unconverted_escalation_event_ids_from_waiver(
    waiver_payload: dict[str, Any],
) -> list[str]:
    ids = waiver_payload.get("stale_unconverted_escalation_event_ids")
    if isinstance(ids, list):
        return _string_list(ids)
    summary = dict(waiver_payload.get("replay_alert_fixture_summary") or {})
    summary_ids = summary.get("stale_unconverted_escalation_event_ids")
    if isinstance(summary_ids, list):
        return _string_list(summary_ids)
    return _string_list(
        row.get("event_id") for row in _waiver_stale_escalation_rows(waiver_payload)
    )


def _event_payload_for_escalation(session: Session, event_id: str) -> dict[str, Any]:
    event_uuid = _uuid_or_none(event_id)
    if event_uuid is None:
        return {}
    event = session.get(SemanticGovernanceEvent, event_uuid)
    if event is None:
        return {}
    payload = (event.event_payload_json or {}).get(
        "claim_support_policy_impact_replay_escalation"
    )
    return dict(payload or {})


def record_replay_alert_fixture_coverage_waiver_ledger(
    session: Session,
    *,
    waiver_artifact: AgentTaskArtifact,
    waiver_payload: dict[str, Any],
) -> ClaimSupportReplayAlertFixtureCoverageWaiverLedger:
    waiver_sha256 = str(waiver_payload.get("waiver_sha256") or "")
    existing = session.scalar(
        select(ClaimSupportReplayAlertFixtureCoverageWaiverLedger)
        .where(
            ClaimSupportReplayAlertFixtureCoverageWaiverLedger.waiver_artifact_id
            == waiver_artifact.id,
            ClaimSupportReplayAlertFixtureCoverageWaiverLedger.waiver_sha256
            == waiver_sha256,
        )
        .limit(1)
    )
    if existing is not None:
        return existing

    stale_rows = _waiver_stale_escalation_rows(waiver_payload)
    rows_by_id = {str(row.get("event_id")): row for row in stale_rows if row.get("event_id")}
    stale_event_ids = stale_unconverted_escalation_event_ids_from_waiver(waiver_payload)
    event_payloads_by_id = {
        event_id: _event_payload_for_escalation(session, event_id)
        for event_id in stale_event_ids
    }
    source_change_impact_ids = _string_list(
        (rows_by_id.get(event_id) or {}).get("change_impact_id")
        or event_payloads_by_id.get(event_id, {}).get("change_impact_id")
        for event_id in stale_event_ids
    )
    source_verification_task_ids = _string_list(
        [
            waiver_payload.get("verification_task_id"),
            *[
                task_id
                for event_payload in event_payloads_by_id.values()
                for task_id in (event_payload.get("affected_verification_task_ids") or [])
            ],
        ]
    )
    now = utcnow()
    ledger_basis = {
        "schema_name": "claim_support_replay_alert_fixture_coverage_waiver_ledger",
        "schema_version": "1.0",
        "waiver_artifact_id": str(waiver_artifact.id),
        "waiver_sha256": waiver_sha256,
        "verification_task_id": waiver_payload.get("verification_task_id"),
        "target_task_id": waiver_payload.get("target_task_id"),
        "policy_id": waiver_payload.get("policy_id"),
        "fixture_set_id": waiver_payload.get("fixture_set_id"),
        "stale_unconverted_escalation_event_ids": stale_event_ids,
        "stale_unconverted_escalation_event_count": len(stale_event_ids),
        "source_change_impact_ids": source_change_impact_ids,
        "source_verification_task_ids": source_verification_task_ids,
    }
    ledger = ClaimSupportReplayAlertFixtureCoverageWaiverLedger(
        waiver_artifact_id=waiver_artifact.id,
        verification_task_id=UUID(str(waiver_payload["verification_task_id"])),
        target_task_id=_uuid_or_none(waiver_payload.get("target_task_id")),
        policy_id=_uuid_or_none(waiver_payload.get("policy_id")),
        fixture_set_id=_uuid_or_none(waiver_payload.get("fixture_set_id")),
        waiver_sha256=waiver_sha256,
        waiver_severity=waiver_payload.get("waiver_severity"),
        waived_by=waiver_payload.get("waived_by"),
        waiver_expires_at=_coerce_utc_datetime(waiver_payload.get("waiver_expires_at")),
        waiver_review_due_at=_coerce_utc_datetime(
            waiver_payload.get("waiver_review_due_at")
        ),
        waiver_remediation_owner=waiver_payload.get("waiver_remediation_owner"),
        waived_escalation_event_count=len(stale_event_ids),
        covered_escalation_event_count=0,
        coverage_complete=len(stale_event_ids) == 0,
        coverage_status="no_action_required" if not stale_event_ids else "open",
        waived_escalation_set_sha256=replay_alert_escalation_set_sha256(stale_event_ids),
        covered_escalation_set_sha256=replay_alert_escalation_set_sha256([]),
        source_change_impact_ids_json=source_change_impact_ids,
        source_verification_task_ids_json=source_verification_task_ids,
        ledger_payload_sha256=str(payload_sha256(ledger_basis)),
        created_at=now,
        updated_at=now,
    )
    session.add(ledger)
    session.flush()

    for event_id in stale_event_ids:
        row = rows_by_id.get(event_id) or {}
        event_payload = event_payloads_by_id.get(event_id, {})
        change_impact_id = row.get("change_impact_id") or event_payload.get(
            "change_impact_id"
        )
        session.add(
            ClaimSupportReplayAlertFixtureCoverageWaiverEscalation(
                ledger_id=ledger.id,
                waiver_artifact_id=waiver_artifact.id,
                escalation_event_id=UUID(str(event_id)),
                change_impact_id=_uuid_or_none(change_impact_id),
                escalation_event_hash=row.get("event_hash"),
                escalation_receipt_sha256=row.get("receipt_sha256"),
                alert_kind=row.get("alert_kind") or event_payload.get("alert_kind"),
                replay_status=row.get("replay_status") or event_payload.get("replay_status"),
                covered=False,
                created_at=now,
            )
        )
    session.flush()
    return ledger


@dataclass(frozen=True)
class ReplayAlertWaiverClosureCandidate:
    ledger: ClaimSupportReplayAlertFixtureCoverageWaiverLedger
    waiver_artifact: AgentTaskArtifact
    waived_escalation_event_ids: list[str]
    covered_escalation_event_ids: list[str]
    coverage_promotion_event_ids: list[str]
    coverage_promotion_artifact_ids: list[str]
    coverage_promotion_receipt_sha256s: list[str]


def apply_replay_alert_fixture_coverage_promotion_to_waiver_ledgers(
    session: Session,
    *,
    promotion_event: SemanticGovernanceEvent,
    promotion_artifact: AgentTaskArtifact | None,
    promoted_escalation_event_ids: set[str],
) -> list[ReplayAlertWaiverClosureCandidate]:
    if promotion_artifact is None or not promoted_escalation_event_ids:
        return []
    now = utcnow()
    closure_candidates: list[ReplayAlertWaiverClosureCandidate] = []
    ledgers = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCoverageWaiverLedger)
            .where(
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.coverage_complete.is_(
                    False
                ),
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.waived_escalation_event_count
                > 0,
            )
            .order_by(
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.created_at.asc(),
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.id.asc(),
            )
        )
    )
    for ledger in ledgers:
        rows = list(
            session.scalars(
                select(ClaimSupportReplayAlertFixtureCoverageWaiverEscalation)
                .where(
                    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.ledger_id
                    == ledger.id
                )
                .order_by(
                    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.created_at.asc(),
                    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.id.asc(),
                )
            )
        )
        if not rows:
            continue
        changed = False
        for row in rows:
            if str(row.escalation_event_id) not in promoted_escalation_event_ids:
                continue
            if not row.covered:
                row.covered = True
                row.covered_by_promotion_event_id = promotion_event.id
                row.covered_by_promotion_artifact_id = promotion_artifact.id
                row.covered_by_promotion_receipt_sha256 = promotion_event.receipt_sha256
                row.covered_at = now
                changed = True

        covered_rows = [row for row in rows if row.covered]
        covered_ids = sorted(str(row.escalation_event_id) for row in covered_rows)
        all_ids = sorted(str(row.escalation_event_id) for row in rows)
        if changed:
            ledger.covered_escalation_event_count = len(covered_ids)
            ledger.covered_escalation_set_sha256 = replay_alert_escalation_set_sha256(
                covered_ids
            )
            ledger.coverage_status = (
                "closed" if len(covered_ids) == len(all_ids) else "partially_covered"
            )
            ledger.promotion_event_ids_json = _string_list(
                [
                    *(ledger.promotion_event_ids_json or []),
                    promotion_event.id,
                ]
            )
            ledger.promotion_artifact_ids_json = _string_list(
                [
                    *(ledger.promotion_artifact_ids_json or []),
                    promotion_artifact.id,
                ]
            )
            ledger.promotion_receipt_sha256s_json = _string_list(
                [
                    *(ledger.promotion_receipt_sha256s_json or []),
                    promotion_event.receipt_sha256,
                ]
            )
            ledger.updated_at = now
        if len(covered_ids) != len(all_ids):
            continue
        waiver_artifact = session.get(AgentTaskArtifact, ledger.waiver_artifact_id)
        if waiver_artifact is None:
            continue
        closure_candidates.append(
            ReplayAlertWaiverClosureCandidate(
                ledger=ledger,
                waiver_artifact=waiver_artifact,
                waived_escalation_event_ids=all_ids,
                covered_escalation_event_ids=covered_ids,
                coverage_promotion_event_ids=_string_list(
                    row.covered_by_promotion_event_id for row in covered_rows
                ),
                coverage_promotion_artifact_ids=_string_list(
                    row.covered_by_promotion_artifact_id for row in covered_rows
                ),
                coverage_promotion_receipt_sha256s=_string_list(
                    row.covered_by_promotion_receipt_sha256 for row in covered_rows
                ),
            )
        )
    session.flush()
    return closure_candidates


def waiver_artifact_ids_with_coverage_ledgers(session: Session) -> set[UUID]:
    return set(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCoverageWaiverLedger.waiver_artifact_id)
        )
    )


def mark_replay_alert_fixture_coverage_waiver_ledger_closed(
    session: Session,
    *,
    ledger: ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
    closure_event: SemanticGovernanceEvent,
    closure_artifact: AgentTaskArtifact | None,
    coverage_promotion_event_ids: list[str],
    coverage_promotion_artifact_ids: list[str],
    coverage_promotion_receipt_sha256s: list[str],
) -> None:
    now = utcnow()
    ledger.coverage_complete = True
    ledger.coverage_status = "closed"
    ledger.covered_escalation_event_count = ledger.waived_escalation_event_count
    ledger.closure_event_id = closure_event.id
    ledger.closure_artifact_id = closure_artifact.id if closure_artifact is not None else None
    ledger.closure_receipt_sha256 = closure_event.receipt_sha256
    ledger.promotion_event_ids_json = _string_list(coverage_promotion_event_ids)
    ledger.promotion_artifact_ids_json = _string_list(coverage_promotion_artifact_ids)
    ledger.promotion_receipt_sha256s_json = _string_list(coverage_promotion_receipt_sha256s)
    ledger.closed_at = now
    ledger.updated_at = now
    session.flush()
