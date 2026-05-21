from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.claim_support import ClaimSupportFixtureSet
from app.db.public.semantic_memory import SemanticGovernanceEvent, SemanticGovernanceEventKind
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactFixtureCandidateResponse,
    ClaimSupportPolicyChangeImpactFixturePromotionResponse,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_evaluations import (
    default_claim_support_evaluation_fixtures,
    ensure_claim_support_fixture_set,
)
from app.services.claim_support_replay_alert_fixture_candidates import (
    claim_support_policy_change_impact_fixture_candidates,
)
from app.services.claim_support_replay_alert_fixture_corpus import (
    active_replay_alert_fixture_corpus_response_fields,
    refresh_active_replay_alert_fixture_corpus_summary,
)
from app.services.claim_support_replay_alert_promotions import (
    fixture_promotion_event_ref,
    record_fixture_promotion_event,
    refresh_fixture_manifests,
)
from app.services.claim_support_replay_alert_waivers import (
    apply_replay_alert_fixture_coverage_promotion_to_waiver_ledgers,
    mark_replay_alert_fixture_coverage_waiver_ledger_closed,
    stale_unconverted_escalation_event_ids_from_waiver,
    waiver_artifact_ids_with_coverage_ledgers,
)
from app.services.evidence_common import payload_sha256
from app.services.semantic_governance import (
    active_semantic_basis,
    record_semantic_governance_event,
)
from app.services.storage import StorageService

CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_RECEIPT_SCHEMA = (
    "claim_support_policy_impact_fixture_promotion_receipt"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED.value
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_RECEIPT_SCHEMA = (
    "claim_support_replay_alert_fixture_coverage_waiver_closure_receipt"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver_closure"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED.value
)
def _waiver_stale_unconverted_escalation_event_ids(payload: dict[str, Any]) -> list[str]:
    return stale_unconverted_escalation_event_ids_from_waiver(payload)


def _waiver_stale_unconverted_escalation_count(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("stale_unconverted_escalation_event_count") or 0)
    except (TypeError, ValueError):
        return 0


def _waiver_has_complete_stale_escalation_set(
    payload: dict[str, Any],
    *,
    stale_escalation_event_ids: list[str],
) -> bool:
    summary = dict(payload.get("replay_alert_fixture_summary") or {})
    stale_count = _waiver_stale_unconverted_escalation_count(payload)
    if stale_count <= 0:
        return False
    has_full_stale_set = bool(
        payload.get("stale_unconverted_escalation_event_ids")
        or summary.get("stale_unconverted_escalation_event_ids")
    )
    if summary.get("has_more_unconverted_escalations") and not has_full_stale_set:
        return False
    return len(stale_escalation_event_ids) == stale_count


def _waiver_closure_event_deduplication_key(
    *,
    waiver_artifact_id: UUID,
    waiver_sha256: str,
    promotion_receipt_sha256: str,
) -> str:
    return (
        "claim_support_replay_alert_fixture_coverage_waiver_closed:"
        f"{waiver_artifact_id}:{waiver_sha256}:{promotion_receipt_sha256}"
    )


def _record_replay_alert_fixture_coverage_waiver_closure_event(
    session: Session,
    *,
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
    promotion_event: SemanticGovernanceEvent,
    promotion_artifact: AgentTaskArtifact,
    waiver_artifact: AgentTaskArtifact,
    waived_escalation_event_ids: list[str],
    covered_escalation_event_ids: list[str],
    coverage_promotion_event_ids: list[str] | None = None,
    coverage_promotion_artifact_ids: list[str] | None = None,
    coverage_promotion_receipt_sha256s: list[str] | None = None,
    source_change_impact_ids: list[str] | None = None,
    source_escalation_event_ids: list[str] | None = None,
    requested_by: str,
    storage_service: StorageService | None,
) -> tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool] | None:
    waiver_payload = dict(waiver_artifact.payload_json or {})
    waiver_sha256 = str(waiver_payload.get("waiver_sha256") or "")
    promotion_receipt_sha256 = str(promotion_event.receipt_sha256 or "")
    if not waiver_sha256 or not promotion_receipt_sha256:
        return None

    deduplication_key = _waiver_closure_event_deduplication_key(
        waiver_artifact_id=waiver_artifact.id,
        waiver_sha256=waiver_sha256,
        promotion_receipt_sha256=promotion_receipt_sha256,
    )
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
        return existing, artifact, False

    semantic_basis = active_semantic_basis(session)
    promotion_payload = (
        (promotion_event.event_payload_json or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        )
        or {}
    )
    receipt_source_change_impact_ids = list(source_change_impact_ids or []) or list(
        promotion_payload.get("source_change_impact_ids")
        or sorted({str(candidate.change_impact_id) for candidate in candidates})
    )
    receipt_source_escalation_event_ids = list(source_escalation_event_ids or []) or list(
        promotion_payload.get("source_escalation_event_ids")
        or sorted(
            {
                str(event_id)
                for candidate in candidates
                for event_id in candidate.escalation_event_ids
            }
        )
    )
    receipt_basis = {
        "schema_name": CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "closure_status": "closed_by_fixture_promotion",
        "closed_by": requested_by,
        "closed_at": utcnow().isoformat(),
        "waiver_artifact_id": str(waiver_artifact.id),
        "waiver_task_id": str(waiver_artifact.task_id),
        "waiver_sha256": waiver_sha256,
        "waiver_severity": waiver_payload.get("waiver_severity"),
        "waiver_expires_at": waiver_payload.get("waiver_expires_at"),
        "waiver_stale_unconverted_escalation_event_count": (
            _waiver_stale_unconverted_escalation_count(waiver_payload)
        ),
        "waived_escalation_event_ids": waived_escalation_event_ids,
        "covered_escalation_event_ids": covered_escalation_event_ids,
        "coverage_promotion_event_ids": sorted(coverage_promotion_event_ids or []),
        "coverage_promotion_artifact_ids": sorted(coverage_promotion_artifact_ids or []),
        "coverage_promotion_receipt_sha256s": sorted(
            coverage_promotion_receipt_sha256s or []
        ),
        "source_change_impact_ids": receipt_source_change_impact_ids,
        "source_escalation_event_ids": receipt_source_escalation_event_ids,
        "fixture_set_id": str(fixture_set.id),
        "fixture_set_name": fixture_set.fixture_set_name,
        "fixture_set_version": fixture_set.fixture_set_version,
        "fixture_set_sha256": fixture_set.fixture_set_sha256,
        "promotion_event_id": str(promotion_event.id),
        "promotion_receipt_sha256": promotion_receipt_sha256,
        "promotion_artifact_id": str(promotion_artifact.id),
        "promotion_artifact_kind": promotion_artifact.artifact_kind,
        "promotion_artifact_path": promotion_artifact.storage_path,
        "promotion_payload_sha256": promotion_event.payload_sha256,
        "closure_reason": (
            "Promoted replay-alert fixture coverage covers the stale escalation "
            "event set waived by this verification artifact."
        ),
        "semantic_basis": semantic_basis,
        "deduplication_key": deduplication_key,
    }
    receipt_payload = {
        **receipt_basis,
        "receipt_sha256": payload_sha256(receipt_basis),
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=promotion_artifact.task_id,
        artifact_kind=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND,
        payload=receipt_payload,
        storage_service=storage_service,
        filename=(
            "claim_support_replay_alert_fixture_coverage_waiver_closure_"
            f"{waiver_artifact.id}_{receipt_payload['receipt_sha256'][:12]}.json"
        ),
    )
    event = record_semantic_governance_event(
        session,
        event_kind=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND,
        governance_scope=(
            f"claim_support_replay_alert_fixture_coverage_waiver:"
            f"{fixture_set.fixture_set_name}:{fixture_set.fixture_set_version}"
        ),
        subject_table="agent_task_artifacts",
        subject_id=waiver_artifact.id,
        task_id=promotion_artifact.task_id,
        ontology_snapshot_id=_uuid_or_none(semantic_basis.get("active_ontology_snapshot_id")),
        semantic_graph_snapshot_id=_uuid_or_none(
            semantic_basis.get("active_semantic_graph_snapshot_id")
        ),
        agent_task_artifact_id=artifact.id,
        receipt_sha256=receipt_payload["receipt_sha256"],
        event_payload={
            "claim_support_replay_alert_fixture_coverage_waiver_closure": receipt_payload,
            "semantic_basis": semantic_basis,
        },
        deduplication_key=deduplication_key,
        created_by=requested_by,
    )
    return event, artifact, True


def _record_replay_alert_fixture_coverage_waiver_closure_events(
    session: Session,
    *,
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
    promotion_event: SemanticGovernanceEvent,
    promotion_artifact: AgentTaskArtifact | None,
    requested_by: str,
    storage_service: StorageService | None,
) -> list[tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool]]:
    if promotion_artifact is None:
        return []

    promoted_escalation_event_ids = {
        str(event_id) for candidate in candidates for event_id in candidate.escalation_event_ids
    }
    if not promoted_escalation_event_ids:
        return []

    recorded: list[tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool]] = []
    ledger_closure_candidates = (
        apply_replay_alert_fixture_coverage_promotion_to_waiver_ledgers(
            session,
            promotion_event=promotion_event,
            promotion_artifact=promotion_artifact,
            promoted_escalation_event_ids=promoted_escalation_event_ids,
        )
    )
    for candidate in ledger_closure_candidates:
        event = _record_replay_alert_fixture_coverage_waiver_closure_event(
            session,
            fixture_set=fixture_set,
            candidates=candidates,
            promotion_event=promotion_event,
            promotion_artifact=promotion_artifact,
            waiver_artifact=candidate.waiver_artifact,
            waived_escalation_event_ids=candidate.waived_escalation_event_ids,
            covered_escalation_event_ids=candidate.covered_escalation_event_ids,
            coverage_promotion_event_ids=candidate.coverage_promotion_event_ids,
            coverage_promotion_artifact_ids=candidate.coverage_promotion_artifact_ids,
            coverage_promotion_receipt_sha256s=(
                candidate.coverage_promotion_receipt_sha256s
            ),
            source_change_impact_ids=[
                str(value) for value in (candidate.ledger.source_change_impact_ids_json or [])
            ],
            source_escalation_event_ids=candidate.waived_escalation_event_ids,
            requested_by=requested_by,
            storage_service=storage_service,
        )
        if event is None:
            continue
        closure_event, closure_artifact, _created = event
        mark_replay_alert_fixture_coverage_waiver_ledger_closed(
            session,
            ledger=candidate.ledger,
            closure_event=closure_event,
            closure_artifact=closure_artifact,
            coverage_promotion_event_ids=candidate.coverage_promotion_event_ids,
            coverage_promotion_artifact_ids=candidate.coverage_promotion_artifact_ids,
            coverage_promotion_receipt_sha256s=(
                candidate.coverage_promotion_receipt_sha256s
            ),
        )
        recorded.append(event)

    ledger_backed_waiver_artifact_ids = waiver_artifact_ids_with_coverage_ledgers(session)
    waiver_artifacts = list(
        session.scalars(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.artifact_kind
                == CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND
            )
            .order_by(AgentTaskArtifact.created_at.asc(), AgentTaskArtifact.id.asc())
        )
    )
    for waiver_artifact in waiver_artifacts:
        if waiver_artifact.id in ledger_backed_waiver_artifact_ids:
            continue
        waiver_payload = dict(waiver_artifact.payload_json or {})
        waived_escalation_event_ids = _waiver_stale_unconverted_escalation_event_ids(
            waiver_payload
        )
        if not _waiver_has_complete_stale_escalation_set(
            waiver_payload,
            stale_escalation_event_ids=waived_escalation_event_ids,
        ):
            continue
        if not set(waived_escalation_event_ids).issubset(promoted_escalation_event_ids):
            continue
        event = _record_replay_alert_fixture_coverage_waiver_closure_event(
            session,
            fixture_set=fixture_set,
            candidates=candidates,
            promotion_event=promotion_event,
            promotion_artifact=promotion_artifact,
            waiver_artifact=waiver_artifact,
            waived_escalation_event_ids=waived_escalation_event_ids,
            covered_escalation_event_ids=waived_escalation_event_ids,
            coverage_promotion_event_ids=[str(promotion_event.id)],
            coverage_promotion_artifact_ids=[str(promotion_artifact.id)],
            coverage_promotion_receipt_sha256s=[
                str(promotion_event.receipt_sha256)
            ]
            if promotion_event.receipt_sha256
            else [],
            requested_by=requested_by,
            storage_service=storage_service,
        )
        if event is not None:
            recorded.append(event)
    return recorded


def promote_claim_support_policy_change_impact_fixture_candidates(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    fixture_set_name: str = "claim_support_replay_alert_promotions",
    fixture_set_version: str = "v1",
    requested_by: str = "docling-system",
    include_unescalated: bool = False,
    storage_service: StorageService | None = None,
    commit: bool = True,
) -> ClaimSupportPolicyChangeImpactFixturePromotionResponse:
    candidate_response = claim_support_policy_change_impact_fixture_candidates(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_unescalated=include_unescalated,
        include_promoted=False,
    )
    candidates = list(candidate_response.items)
    if not candidates:
        active_corpus_summary = refresh_active_replay_alert_fixture_corpus_summary(
            session,
            storage_service=storage_service,
            recorded_by=requested_by,
        )
        if commit:
            session.commit()
        else:
            session.flush()
        return ClaimSupportPolicyChangeImpactFixturePromotionResponse(
            fixture_set_name=fixture_set_name,
            fixture_set_version=fixture_set_version,
            skipped_candidate_count=candidate_response.summary.promoted_candidate_count,
            candidate_matching_count=candidate_response.matching_count,
            candidate_item_count=candidate_response.item_count,
            has_more_candidates=candidate_response.has_more,
            candidate_summary=candidate_response.summary,
            **active_replay_alert_fixture_corpus_response_fields(active_corpus_summary),
        )

    fixtures_by_case_id = {
        str(fixture.get("case_id") or ""): fixture
        for fixture in default_claim_support_evaluation_fixtures()
    }
    for candidate in candidates:
        fixtures_by_case_id[candidate.case_id] = candidate.fixture
    source_change_impact_ids = sorted(
        {candidate.change_impact_id for candidate in candidates},
        key=str,
    )
    source_escalation_event_ids = sorted(
        {event_id for candidate in candidates for event_id in candidate.escalation_event_ids},
        key=str,
    )
    fixture_set = ensure_claim_support_fixture_set(
        session,
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        fixtures=list(fixtures_by_case_id.values()),
        metadata={
            "source": "claim_support_policy_change_impact_replay_alerts",
            "requested_by": requested_by,
            "source_change_impact_ids": [str(value) for value in source_change_impact_ids],
            "source_escalation_event_ids": [
                str(value) for value in source_escalation_event_ids
            ],
            "candidate_ids": [candidate.candidate_id for candidate in candidates],
        },
    )
    event, artifact, created = record_fixture_promotion_event(
        session,
        fixture_set=fixture_set,
        candidates=candidates,
        requested_by=requested_by,
        storage_service=storage_service,
    )
    waiver_closure_events = _record_replay_alert_fixture_coverage_waiver_closure_events(
        session,
        fixture_set=fixture_set,
        candidates=candidates,
        promotion_event=event,
        promotion_artifact=artifact,
        requested_by=requested_by,
        storage_service=storage_service,
    )
    active_corpus_summary = refresh_active_replay_alert_fixture_corpus_summary(
        session,
        storage_service=storage_service,
        recorded_by=requested_by,
    )
    refresh_fixture_manifests(session, candidates)
    if commit:
        session.commit()
    else:
        session.flush()
    event_ref = fixture_promotion_event_ref(event, artifact=artifact)
    promoted_candidates = [
        candidate.model_copy(
            update={
                "already_promoted": True,
                "promotion_events": [event_ref],
            }
        )
        for candidate in candidates
    ]
    return ClaimSupportPolicyChangeImpactFixturePromotionResponse(
        fixture_set_id=fixture_set.id,
        fixture_set_name=fixture_set.fixture_set_name,
        fixture_set_version=fixture_set.fixture_set_version,
        fixture_set_sha256=fixture_set.fixture_set_sha256,
        fixture_count=fixture_set.fixture_count,
        promoted_candidate_count=len(candidates),
        skipped_candidate_count=candidate_response.summary.promoted_candidate_count,
        candidate_matching_count=candidate_response.matching_count,
        candidate_item_count=candidate_response.item_count,
        has_more_candidates=candidate_response.has_more,
        candidate_summary=candidate_response.summary,
        source_change_impact_ids=source_change_impact_ids,
        source_escalation_event_ids=source_escalation_event_ids,
        promotion_event_id=event.id,
        promotion_receipt_sha256=event.receipt_sha256,
        artifact_id=artifact.id if artifact is not None else None,
        artifact_kind=artifact.artifact_kind if artifact is not None else None,
        artifact_path=artifact.storage_path if artifact is not None else None,
        created=created,
        **active_replay_alert_fixture_corpus_response_fields(active_corpus_summary),
        waiver_closure_count=len(waiver_closure_events),
        waiver_closure_event_ids=[event.id for event, _, _ in waiver_closure_events],
        waiver_closure_artifact_ids=[
            artifact.id
            for _, artifact, _ in waiver_closure_events
            if artifact is not None
        ],
        waiver_closure_receipt_sha256s=[
            event.receipt_sha256
            for event, _, _ in waiver_closure_events
            if event.receipt_sha256
        ],
        closed_waiver_artifact_ids=[
            UUID(
                str(
                    (
                        (event.event_payload_json or {}).get(
                            "claim_support_replay_alert_fixture_coverage_waiver_closure"
                        )
                        or {}
                    ).get("waiver_artifact_id")
                )
            )
            for event, _, _ in waiver_closure_events
            if (
                (
                    (event.event_payload_json or {}).get(
                        "claim_support_replay_alert_fixture_coverage_waiver_closure"
                    )
                    or {}
                ).get("waiver_artifact_id")
            )
        ],
        candidates=promoted_candidates,
    )
