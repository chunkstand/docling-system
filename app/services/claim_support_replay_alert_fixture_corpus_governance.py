from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _uuid_or_none
from app.core.coercion import unique_strings as _string_list
from app.core.time import utcnow
from app.db.models import (
    AgentTaskArtifact,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    SemanticGovernanceEvent,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_replay_alert_fixture_corpus import (
    ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_RECEIPT_SCHEMA,
)
from app.services.claim_support_replay_alert_fixture_corpus_build import (
    build_replay_alert_fixture_corpus,
)
from app.services.evidence import payload_sha256
from app.services.semantic_governance import (
    active_semantic_basis,
    record_semantic_governance_event,
)
from app.services.storage import StorageService


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


def _snapshot_source_events(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> list[SemanticGovernanceEvent]:
    event_ids = [
        *_string_list(snapshot.source_promotion_event_ids_json),
        *_string_list(snapshot.invalid_promotion_event_ids_json),
    ]
    parsed_event_ids = [_uuid_or_none(value) for value in event_ids]
    parsed_event_ids = [value for value in parsed_event_ids if value is not None]
    if not parsed_event_ids:
        return []
    return list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(SemanticGovernanceEvent.id.in_(parsed_event_ids))
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )


def _snapshot_anchor_task_id(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> UUID | None:
    for event in _snapshot_source_events(session, snapshot):
        if event.agent_task_artifact_id is not None:
            artifact = session.get(AgentTaskArtifact, event.agent_task_artifact_id)
            if artifact is not None:
                return artifact.task_id
        if event.task_id is not None:
            return event.task_id
    return None


def _snapshot_governance_deduplication_key(
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> str:
    return (
        "claim_support_replay_alert_fixture_corpus_snapshot_activated:"
        f"{snapshot.id}:{snapshot.snapshot_sha256}"
    )


def _snapshot_governance_payload(
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
    *,
    artifact_id: UUID | None,
    semantic_basis: dict[str, Any],
    recorded_by: str,
    deduplication_key: str,
) -> dict[str, Any]:
    snapshot_payload = dict(snapshot.snapshot_payload_json or {})
    basis = {
        "schema_name": CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "snapshot_id": str(snapshot.id),
        "snapshot_name": snapshot.snapshot_name,
        "snapshot_status": snapshot.status,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "fixture_count": snapshot.fixture_count,
        "promotion_event_count": snapshot.promotion_event_count,
        "promotion_fixture_set_count": snapshot.promotion_fixture_set_count,
        "invalid_promotion_event_count": snapshot.invalid_promotion_event_count,
        "source_promotion_event_ids": list(snapshot.source_promotion_event_ids_json),
        "source_promotion_artifact_ids": list(
            snapshot.source_promotion_artifact_ids_json
        ),
        "source_promotion_receipt_sha256s": list(
            snapshot.source_promotion_receipt_sha256s_json
        ),
        "source_fixture_set_ids": list(snapshot.source_fixture_set_ids_json),
        "source_fixture_set_sha256s": list(snapshot.source_fixture_set_sha256s_json),
        "source_escalation_event_ids": list(snapshot.source_escalation_event_ids_json),
        "invalid_promotion_event_ids": list(snapshot.invalid_promotion_event_ids_json),
        "invalid_promotion_events": list(
            snapshot_payload.get("invalid_promotion_events") or []
        ),
        "row_count": len(snapshot_payload.get("rows") or []),
        "row_sha256s": [
            str(payload_sha256(row))
            for row in snapshot_payload.get("rows") or []
            if isinstance(row, dict)
        ],
        "governance_artifact_id": str(artifact_id) if artifact_id else None,
        "semantic_basis": semantic_basis,
        "recorded_by": recorded_by,
        "recorded_at": utcnow().isoformat(),
        "deduplication_key": deduplication_key,
    }
    return {**basis, "receipt_sha256": payload_sha256(basis)}


def record_replay_alert_fixture_corpus_snapshot_governance(
    session: Session,
    *,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
    storage_service: StorageService | None = None,
    recorded_by: str = "docling-system",
) -> tuple[SemanticGovernanceEvent | None, AgentTaskArtifact | None, bool]:
    if snapshot.semantic_governance_event_id is not None:
        event = session.get(SemanticGovernanceEvent, snapshot.semantic_governance_event_id)
        artifact = (
            session.get(AgentTaskArtifact, snapshot.governance_artifact_id)
            if snapshot.governance_artifact_id is not None
            else None
        )
        return event, artifact, False

    deduplication_key = _snapshot_governance_deduplication_key(snapshot)
    existing = session.scalar(
        select(SemanticGovernanceEvent)
        .where(SemanticGovernanceEvent.deduplication_key == deduplication_key)
        .limit(1)
    )
    if existing is not None:
        artifact = (
            session.get(AgentTaskArtifact, existing.agent_task_artifact_id)
            if existing.agent_task_artifact_id is not None
            else None
        )
        snapshot.semantic_governance_event_id = existing.id
        snapshot.governance_artifact_id = artifact.id if artifact is not None else None
        snapshot.governance_receipt_sha256 = existing.receipt_sha256
        session.flush()
        return existing, artifact, False

    semantic_basis = active_semantic_basis(session)
    anchor_task_id = _snapshot_anchor_task_id(session, snapshot)
    artifact_id = uuid.uuid4() if anchor_task_id is not None else None
    receipt_payload = _snapshot_governance_payload(
        snapshot,
        artifact_id=artifact_id,
        semantic_basis=semantic_basis,
        recorded_by=recorded_by,
        deduplication_key=deduplication_key,
    )
    artifact: AgentTaskArtifact | None = None
    if anchor_task_id is not None:
        artifact = create_agent_task_artifact(
            session,
            task_id=anchor_task_id,
            artifact_kind=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND,
            payload=receipt_payload,
            storage_service=storage_service,
            filename=(
                "claim_support_replay_alert_fixture_corpus_snapshot_"
                f"{snapshot.id}_{receipt_payload['receipt_sha256'][:12]}.json"
            ),
            artifact_id=artifact_id,
        )

    event = record_semantic_governance_event(
        session,
        event_kind=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND,
        governance_scope=(
            f"claim_support_replay_alert_fixture_corpus:{snapshot.snapshot_name}"
        ),
        subject_table="claim_support_replay_alert_fixture_corpus_snapshots",
        subject_id=snapshot.id,
        task_id=anchor_task_id,
        ontology_snapshot_id=_uuid_or_none(semantic_basis.get("active_ontology_snapshot_id")),
        semantic_graph_snapshot_id=_uuid_or_none(
            semantic_basis.get("active_semantic_graph_snapshot_id")
        ),
        agent_task_artifact_id=artifact.id if artifact is not None else None,
        receipt_sha256=receipt_payload["receipt_sha256"],
        event_payload={
            CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY: (
                receipt_payload
            ),
            "semantic_basis": semantic_basis,
        },
        deduplication_key=deduplication_key,
        created_by=recorded_by,
    )
    snapshot.semantic_governance_event_id = event.id
    snapshot.governance_artifact_id = artifact.id if artifact is not None else None
    snapshot.governance_receipt_sha256 = receipt_payload["receipt_sha256"]
    session.flush()
    return event, artifact, True


def _snapshot_row_hash_payload_from_db(
    row: ClaimSupportReplayAlertFixtureCorpusRow,
) -> dict[str, Any]:
    return {
        "case_id": row.case_id,
        "case_identity_sha256": row.case_identity_sha256,
        "fixture_sha256": row.fixture_sha256,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "promotion_event_id": (
            str(row.promotion_event_id) if row.promotion_event_id else None
        ),
        "promotion_artifact_id": (
            str(row.promotion_artifact_id) if row.promotion_artifact_id else None
        ),
        "promotion_receipt_sha256": row.promotion_receipt_sha256,
        "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
    }


def _snapshot_rows_for_integrity(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> list[ClaimSupportReplayAlertFixtureCorpusRow]:
    return list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .order_by(
                ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc(),
                ClaimSupportReplayAlertFixtureCorpusRow.id.asc(),
            )
        )
    )


def replay_alert_fixture_corpus_snapshot_governance_integrity(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot | None,
) -> dict[str, Any]:
    if snapshot is None:
        return {"complete": False, "failures": ["snapshot_missing"]}
    failures: list[str] = []
    snapshot_payload = dict(snapshot.snapshot_payload_json or {})
    if payload_sha256(snapshot_payload) != snapshot.snapshot_sha256:
        failures.append("snapshot_payload_hash_mismatch")
    declared_rows = [
        dict(row)
        for row in snapshot_payload.get("rows") or []
        if isinstance(row, dict)
    ]
    db_rows = _snapshot_rows_for_integrity(session, snapshot)
    db_row_hash_payloads = [_snapshot_row_hash_payload_from_db(row) for row in db_rows]
    if len(declared_rows) != snapshot.fixture_count:
        failures.append("snapshot_payload_row_count_mismatch")
    if len(db_rows) != snapshot.fixture_count:
        failures.append("snapshot_db_row_count_mismatch")
    if declared_rows != db_row_hash_payloads:
        failures.append("snapshot_db_row_payload_mismatch")
    fixture_hash_mismatch_count = sum(
        1
        for row in db_rows
        if payload_sha256(row.fixture_json or {}) != row.fixture_sha256
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
    elif (
        artifact.artifact_kind
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND
    ):
        failures.append("snapshot_governance_artifact_kind_mismatch")

    event_receipt = {}
    if event is not None:
        event_receipt = dict(
            (event.event_payload_json or {}).get(
                CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY
            )
            or {}
        )
        if event.receipt_sha256 != snapshot.governance_receipt_sha256:
            failures.append("snapshot_governance_event_receipt_mismatch")
        if event.receipt_sha256 != event_receipt.get("receipt_sha256"):
            failures.append("snapshot_governance_event_payload_receipt_mismatch")
        event_receipt_basis = dict(event_receipt)
        event_receipt_basis.pop("receipt_sha256", None)
        if (
            not event_receipt.get("receipt_sha256")
            or payload_sha256(event_receipt_basis) != event_receipt.get("receipt_sha256")
        ):
            failures.append("snapshot_governance_event_payload_hash_mismatch")
        if event_receipt.get("snapshot_sha256") != snapshot.snapshot_sha256:
            failures.append("snapshot_governance_event_snapshot_hash_mismatch")
        if event_receipt.get("snapshot_id") != str(snapshot.id):
            failures.append("snapshot_governance_event_snapshot_id_mismatch")

    if artifact is not None:
        artifact_payload = dict(artifact.payload_json or {})
        if artifact_payload.get("receipt_sha256") != snapshot.governance_receipt_sha256:
            failures.append("snapshot_governance_artifact_receipt_mismatch")
        artifact_basis = dict(artifact_payload)
        artifact_basis.pop("receipt_sha256", None)
        if (
            not artifact_payload.get("receipt_sha256")
            or payload_sha256(artifact_basis) != artifact_payload.get("receipt_sha256")
        ):
            failures.append("snapshot_governance_artifact_hash_mismatch")
        if artifact_payload.get("snapshot_sha256") != snapshot.snapshot_sha256:
            failures.append("snapshot_governance_artifact_snapshot_hash_mismatch")
        if artifact_payload.get("snapshot_id") != str(snapshot.id):
            failures.append("snapshot_governance_artifact_snapshot_id_mismatch")
        if event is not None and event.agent_task_artifact_id != artifact.id:
            failures.append("snapshot_governance_event_artifact_mismatch")

    return {
        "complete": not failures,
        "failures": failures,
        "snapshot_id": str(snapshot.id),
        "snapshot_sha256": snapshot.snapshot_sha256,
        "semantic_governance_event_id": (
            str(snapshot.semantic_governance_event_id)
            if snapshot.semantic_governance_event_id
            else None
        ),
        "governance_artifact_id": (
            str(snapshot.governance_artifact_id)
            if snapshot.governance_artifact_id
            else None
        ),
        "governance_receipt_sha256": snapshot.governance_receipt_sha256,
        "event_receipt_sha256": event.receipt_sha256 if event is not None else None,
        "artifact_receipt_sha256": (
            (artifact.payload_json or {}).get("receipt_sha256")
            if artifact is not None
            else None
        ),
        "snapshot_payload_sha256": payload_sha256(snapshot_payload),
        "stored_snapshot_sha256": snapshot.snapshot_sha256,
        "declared_row_count": len(declared_rows),
        "db_row_count": len(db_rows),
        "fixture_hash_mismatch_count": fixture_hash_mismatch_count,
    }


def ensure_active_replay_alert_fixture_corpus_snapshot(
    session: Session,
    *,
    storage_service: StorageService | None = None,
    recorded_by: str = "docling-system",
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
        record_replay_alert_fixture_corpus_snapshot_governance(
            session,
            snapshot=active,
            storage_service=storage_service,
            recorded_by=recorded_by,
        )
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
        record_replay_alert_fixture_corpus_snapshot_governance(
            session,
            snapshot=existing,
            storage_service=storage_service,
            recorded_by=recorded_by,
        )
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
    record_replay_alert_fixture_corpus_snapshot_governance(
        session,
        snapshot=snapshot,
        storage_service=storage_service,
        recorded_by=recorded_by,
    )
    return snapshot


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
