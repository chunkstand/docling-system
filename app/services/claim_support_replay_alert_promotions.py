from __future__ import annotations

from datetime import timedelta
from importlib import import_module
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import compact_strings as _string_list
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.claim_support import ClaimSupportFixtureSet
from app.db.public.semantic_memory import SemanticGovernanceEvent, SemanticGovernanceEventKind
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactFixtureCandidateResponse,
    ClaimSupportPolicyChangeImpactFixturePromotionEventRef,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_payloads import (
    claim_support_fixture_promotion_payload as _fixture_promotion_payload,
)
from app.services.claim_support_replay_alert_fixture_corpus import (
    active_replay_alert_fixture_corpus_rows,
    active_replay_alert_fixture_corpus_snapshot_summary,
    replay_alert_fixture_corpus_snapshot_summary,
)
from app.services.claim_support_replay_alert_waivers import (
    replay_alert_escalation_set_sha256,
)
from app.services.evidence import payload_sha256
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

CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED.value
)


def _fixture_promotion_event_ref(
    event: SemanticGovernanceEvent,
    *,
    artifact: AgentTaskArtifact | None,
) -> ClaimSupportPolicyChangeImpactFixturePromotionEventRef:
    promotion_payload = _fixture_promotion_payload(event)
    return ClaimSupportPolicyChangeImpactFixturePromotionEventRef(
        event_id=event.id,
        event_hash=event.event_hash,
        receipt_sha256=event.receipt_sha256,
        fixture_set_id=_uuid_or_none(promotion_payload.get("fixture_set_id")),
        fixture_set_sha256=promotion_payload.get("fixture_set_sha256"),
        artifact_id=event.agent_task_artifact_id,
        artifact_kind=artifact.artifact_kind if artifact is not None else None,
        artifact_path=artifact.storage_path if artifact is not None else None,
        created_at=event.created_at,
    )


def _refresh_existing_evidence_manifests_for_fixture_candidates(
    session: Session,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
) -> None:
    verification_task_ids = sorted(
        {
            task_id
            for candidate in candidates
            for task_id in candidate.affected_verification_task_ids
        },
        key=str,
    )
    if not verification_task_ids:
        return
    from app.db.public.audit_and_evidence import EvidenceManifest

    existing_manifest_task_ids = list(
        session.scalars(
            select(EvidenceManifest.verification_task_id)
            .where(EvidenceManifest.verification_task_id.in_(verification_task_ids))
            .order_by(EvidenceManifest.created_at.asc())
        )
    )
    if not existing_manifest_task_ids:
        return
    from app.services.evidence import refresh_technical_report_evidence_manifest

    for task_id in dict.fromkeys(existing_manifest_task_ids):
        refresh_technical_report_evidence_manifest(session, task_id=task_id)


def _promotion_event_deduplication_key(
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
) -> str:
    basis = {
        "fixture_set_id": str(fixture_set.id),
        "fixture_set_sha256": fixture_set.fixture_set_sha256,
        "candidate_ids": sorted(candidate.candidate_id for candidate in candidates),
        "fixture_sha256s": sorted(candidate.fixture_sha256 for candidate in candidates),
    }
    return f"claim_support_policy_impact_fixture_promoted:{payload_sha256(basis)}"


def _fixture_promotion_anchor_task_id(
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
):
    for candidate in candidates:
        activation_task_id = (
            candidate.fixture.get("replay_alert_source") or {}
        ).get("activation_task_id")
        if activation_task_id:
            return UUID(str(activation_task_id))
    for candidate in candidates:
        if candidate.source_draft_task_id is not None:
            return candidate.source_draft_task_id
    return None


def _record_fixture_promotion_event(
    session: Session,
    *,
    fixture_set: ClaimSupportFixtureSet,
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse],
    requested_by: str,
    storage_service: StorageService | None,
) -> tuple[SemanticGovernanceEvent, AgentTaskArtifact | None, bool]:
    deduplication_key = _promotion_event_deduplication_key(fixture_set, candidates)
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
    anchor_task_id = _fixture_promotion_anchor_task_id(candidates)
    source_change_impact_ids = sorted({str(row.change_impact_id) for row in candidates})
    source_escalation_event_ids = sorted(
        {str(event_id) for row in candidates for event_id in row.escalation_event_ids}
    )
    candidate_payloads = [
        {
            "candidate_id": row.candidate_id,
            "candidate_identity_sha256": (
                (row.fixture.get("replay_alert_source") or {}).get(
                    "candidate_identity_sha256"
                )
                or row.candidate_id
            ),
            "case_id": row.case_id,
            "fixture_sha256": row.fixture_sha256,
            "source_payload_sha256": row.source_payload_sha256,
            "change_impact_id": str(row.change_impact_id),
            "source_claim_derivation_id": str(row.source_claim_derivation_id)
            if row.source_claim_derivation_id
            else None,
            "source_draft_task_id": str(row.source_draft_task_id)
            if row.source_draft_task_id
            else None,
            "escalation_event_ids": [str(event_id) for event_id in row.escalation_event_ids],
            "latest_escalation_event_id": str(row.latest_escalation_event_id)
            if row.latest_escalation_event_id
            else None,
            "hard_case_kind": row.hard_case_kind,
            "expected_verdict": row.expected_verdict,
        }
        for row in candidates
    ]
    receipt_basis = {
        "schema_name": CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "fixture_set_id": str(fixture_set.id),
        "fixture_set_name": fixture_set.fixture_set_name,
        "fixture_set_version": fixture_set.fixture_set_version,
        "fixture_set_sha256": fixture_set.fixture_set_sha256,
        "fixture_count": fixture_set.fixture_count,
        "candidate_count": len(candidates),
        "source_change_impact_ids": source_change_impact_ids,
        "source_escalation_event_ids": source_escalation_event_ids,
        "candidates": candidate_payloads,
        "semantic_basis": semantic_basis,
        "recorded_by": requested_by,
        "recorded_at": utcnow().isoformat(),
        "deduplication_key": deduplication_key,
    }
    receipt_payload = {**receipt_basis, "receipt_sha256": payload_sha256(receipt_basis)}
    artifact: AgentTaskArtifact | None = None
    if anchor_task_id is not None:
        artifact = create_agent_task_artifact(
            session,
            task_id=anchor_task_id,
            artifact_kind=CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND,
            payload=receipt_payload,
            storage_service=storage_service,
            filename=(
                "claim_support_policy_impact_fixture_promotion_"
                f"{fixture_set.id}_{receipt_payload['receipt_sha256'][:12]}.json"
            ),
        )
    event = record_semantic_governance_event(
        session,
        event_kind=CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND,
        governance_scope=(
            f"claim_support_policy:{fixture_set.fixture_set_name}:"
            f"{fixture_set.fixture_set_version}"
        ),
        subject_table="claim_support_fixture_sets",
        subject_id=fixture_set.id,
        task_id=anchor_task_id,
        ontology_snapshot_id=_uuid_or_none(semantic_basis.get("active_ontology_snapshot_id")),
        semantic_graph_snapshot_id=_uuid_or_none(
            semantic_basis.get("active_semantic_graph_snapshot_id")
        ),
        agent_task_artifact_id=artifact.id if artifact is not None else None,
        receipt_sha256=receipt_payload["receipt_sha256"],
        event_payload={
            "claim_support_policy_impact_fixture_promotion": receipt_payload,
            "semantic_basis": semantic_basis,
        },
        deduplication_key=deduplication_key,
        created_by=requested_by,
    )
    return event, artifact, True


fixture_promotion_event_ref = _fixture_promotion_event_ref
refresh_fixture_manifests = _refresh_existing_evidence_manifests_for_fixture_candidates
record_fixture_promotion_event = _record_fixture_promotion_event


def _fixture_promotion_events_by_candidate(
    session: Session,
) -> dict[str, list[ClaimSupportPolicyChangeImpactFixturePromotionEventRef]]:
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED.value
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    artifact_ids = [
        event.agent_task_artifact_id
        for event in events
        if event.agent_task_artifact_id
    ]
    artifacts_by_id = (
        {
            row.id: row
            for row in session.scalars(
                select(AgentTaskArtifact).where(AgentTaskArtifact.id.in_(artifact_ids))
            )
        }
        if artifact_ids
        else {}
    )
    refs_by_candidate: dict[str, list[ClaimSupportPolicyChangeImpactFixturePromotionEventRef]] = {}
    for event in events:
        event_ref = _fixture_promotion_event_ref(
            event,
            artifact=artifacts_by_id.get(event.agent_task_artifact_id),
        )
        promotion_payload = _fixture_promotion_payload(event)
        for candidate in promotion_payload.get("candidates") or []:
            candidate_id = str(candidate.get("candidate_id") or "")
            if candidate_id:
                refs_by_candidate.setdefault(candidate_id, []).append(event_ref)
    return refs_by_candidate


fixture_promotion_events_by_candidate = _fixture_promotion_events_by_candidate


def _fixture_promotion_summary_from_event(
    event: SemanticGovernanceEvent,
) -> dict[str, Any]:
    promotion_payload = _fixture_promotion_payload(event)
    source_change_impact_ids = _string_list(
        promotion_payload.get("source_change_impact_ids") or []
    )
    source_escalation_event_ids = _string_list(
        promotion_payload.get("source_escalation_event_ids") or []
    )
    candidates = list(promotion_payload.get("candidates") or [])
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "fixture_set_id": promotion_payload.get("fixture_set_id"),
        "fixture_set_name": promotion_payload.get("fixture_set_name"),
        "fixture_set_version": promotion_payload.get("fixture_set_version"),
        "fixture_set_sha256": promotion_payload.get("fixture_set_sha256"),
        "fixture_count": int(promotion_payload.get("fixture_count") or 0),
        "candidate_count": int(promotion_payload.get("candidate_count") or len(candidates)),
        "candidate_ids": [
            str(candidate.get("candidate_id"))
            for candidate in candidates
            if candidate.get("candidate_id")
        ],
        "source_change_impact_ids": source_change_impact_ids,
        "source_escalation_event_ids": source_escalation_event_ids,
        "artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "created_at": event.created_at.isoformat(),
    }


def _fixture_promotion_event_summaries(session: Session) -> list[dict[str, Any]]:
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED.value
            )
            .order_by(
                SemanticGovernanceEvent.created_at.desc(),
                SemanticGovernanceEvent.event_sequence.desc(),
            )
        )
    )
    return [_fixture_promotion_summary_from_event(event) for event in events]


def _replay_escalation_event_summary(
    event: SemanticGovernanceEvent,
    *,
    stale_cutoff,
) -> dict[str, Any]:
    event_payload = dict(event.event_payload_json or {})
    escalation_payload = dict(
        event_payload.get("claim_support_policy_impact_replay_escalation") or {}
    )
    age_hours = max((utcnow() - event.created_at).total_seconds() / 3600, 0.0)
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "change_impact_id": str(event.subject_id) if event.subject_id else None,
        "artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "alert_kind": escalation_payload.get("alert_kind"),
        "replay_status": escalation_payload.get("replay_status"),
        "created_at": event.created_at.isoformat(),
        "age_hours": round(age_hours, 4),
        "is_stale": event.created_at <= stale_cutoff,
    }


def claim_support_replay_alert_fixture_coverage_summary(
    session: Session,
    *,
    stale_after_hours: int = 24,
    limit: int = 50,
) -> dict[str, Any]:
    stale_after_hours = max(1, stale_after_hours)
    limit = max(1, limit)
    promotion_summaries = _fixture_promotion_event_summaries(session)
    active_corpus_snapshot = active_replay_alert_fixture_corpus_snapshot_summary(
        session,
        ensure_current=True,
    )
    if active_corpus_snapshot is not None:
        promoted_escalation_event_ids = {
            str(event_id)
            for event_id in (active_corpus_snapshot.get("source_escalation_event_ids") or [])
        }
    else:
        promoted_escalation_event_ids = {
            str(event_id)
            for promotion in promotion_summaries
            for event_id in promotion.get("source_escalation_event_ids") or []
        }
    escalation_events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    stale_cutoff = utcnow() - timedelta(hours=stale_after_hours)
    unconverted_escalations = [
        _replay_escalation_event_summary(event, stale_cutoff=stale_cutoff)
        for event in escalation_events
        if str(event.id) not in promoted_escalation_event_ids
    ]
    stale_unconverted = [row for row in unconverted_escalations if row["is_stale"]]
    stale_unconverted_event_ids = sorted(
        {str(row["event_id"]) for row in stale_unconverted if row.get("event_id")}
    )
    active_corpus_governance = (
        active_corpus_snapshot.get("governance_integrity")
        if active_corpus_snapshot
        else None
    ) or {}
    active_corpus_governed = (
        bool(active_corpus_governance.get("complete"))
        if active_corpus_snapshot is not None
        else True
    )
    summary_basis = {
        "schema_name": "claim_support_replay_alert_fixture_coverage_summary",
        "schema_version": "1.0",
        "promoted_fixture_set_count": len(promotion_summaries),
        "promoted_candidate_count": sum(
            int(row.get("candidate_count") or 0) for row in promotion_summaries
        ),
        "promoted_escalation_event_count": len(promoted_escalation_event_ids),
        "unconverted_escalation_event_count": len(unconverted_escalations),
        "stale_unconverted_escalation_event_count": len(stale_unconverted),
        "stale_unconverted_escalation_event_ids": stale_unconverted_event_ids,
        "stale_unconverted_escalation_set_sha256": replay_alert_escalation_set_sha256(
            stale_unconverted_event_ids
        ),
        "stale_after_hours": stale_after_hours,
        "latest_promoted_fixture_set": promotion_summaries[0] if promotion_summaries else None,
        "active_replay_alert_fixture_corpus_snapshot": active_corpus_snapshot,
        "active_replay_alert_fixture_corpus_snapshot_id": (
            active_corpus_snapshot.get("snapshot_id") if active_corpus_snapshot else None
        ),
        "active_replay_alert_fixture_corpus_sha256": (
            active_corpus_snapshot.get("snapshot_sha256")
            if active_corpus_snapshot
            else None
        ),
        "active_replay_alert_fixture_corpus_fixture_count": (
            int(active_corpus_snapshot.get("fixture_count") or 0)
            if active_corpus_snapshot
            else 0
        ),
        "active_replay_alert_fixture_corpus_invalid_promotion_event_count": (
            int(active_corpus_snapshot.get("invalid_promotion_event_count") or 0)
            if active_corpus_snapshot
            else 0
        ),
        "active_replay_alert_fixture_corpus_governed": active_corpus_governed,
        "active_replay_alert_fixture_corpus_governance_failures": list(
            active_corpus_governance.get("failures") or []
        ),
        "active_replay_alert_fixture_corpus_governance_event_id": (
            active_corpus_snapshot.get("semantic_governance_event_id")
            if active_corpus_snapshot
            else None
        ),
        "active_replay_alert_fixture_corpus_governance_artifact_id": (
            active_corpus_snapshot.get("governance_artifact_id")
            if active_corpus_snapshot
            else None
        ),
        "active_replay_alert_fixture_corpus_governance_receipt_sha256": (
            active_corpus_snapshot.get("governance_receipt_sha256")
            if active_corpus_snapshot
            else None
        ),
    }
    return {
        **summary_basis,
        "summary_sha256": payload_sha256(summary_basis),
        "generated_at": utcnow().isoformat(),
        "limit": limit,
        "has_more_unconverted_escalations": len(unconverted_escalations) > limit,
        "promoted_fixture_sets": promotion_summaries[:limit],
        "unconverted_escalation_events": unconverted_escalations[:limit],
        "stale_unconverted_escalation_events": stale_unconverted,
    }


def latest_claim_support_replay_alert_fixture_rows(
    session: Session,
    *,
    include_promoted: bool = True,
    limit: int = 100,
    exclude_case_ids: set[str] | None = None,
    stale_after_hours: int = 24,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    coverage_summary = claim_support_replay_alert_fixture_coverage_summary(
        session,
        stale_after_hours=stale_after_hours,
        limit=limit or 1,
    )
    exclude_case_ids = set(exclude_case_ids or set())
    limit = max(0, limit)
    if not include_promoted or limit == 0:
        return [], {
            **coverage_summary,
            "enabled": include_promoted,
            "included_replay_alert_fixture_count": 0,
            "replay_alert_fixture_count": 0,
            "excluded_case_ids": sorted(exclude_case_ids),
            "fixture_source": "disabled",
        }
    snapshot, corpus_rows, available_fixture_count = active_replay_alert_fixture_corpus_rows(
        session,
        exclude_case_ids=exclude_case_ids,
        limit=limit,
    )
    selected = [dict(row.fixture_json or {}) for row in corpus_rows]
    snapshot_summary = replay_alert_fixture_corpus_snapshot_summary(snapshot, session=session)
    replay_alert_fixture_count = int(snapshot.fixture_count) if snapshot is not None else 0
    return selected, {
        **coverage_summary,
        "enabled": include_promoted,
        "fixture_source": (
            "active_replay_alert_fixture_corpus_snapshot"
            if snapshot is not None
            else "none"
        ),
        "active_replay_alert_fixture_corpus_snapshot": snapshot_summary,
        "included_replay_alert_fixture_count": len(selected),
        "replay_alert_fixture_count": replay_alert_fixture_count,
        "available_replay_alert_fixture_count": available_fixture_count,
        "excluded_case_ids": sorted(exclude_case_ids),
        "has_more_replay_alert_fixtures": len(selected) < available_fixture_count,
    }


def claim_support_policy_change_impact_fixture_candidates(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    include_unescalated: bool = False,
    include_promoted: bool = True,
):
    return import_module(
        "app.services.claim_support_replay_alert_fixture_candidates"
    ).claim_support_policy_change_impact_fixture_candidates(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_unescalated=include_unescalated,
        include_promoted=include_promoted,
    )


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
    storage_service=None,
    commit: bool = True,
):
    return import_module(
        "app.services.claim_support_replay_alert_promotion_governance"
    ).promote_claim_support_policy_change_impact_fixture_candidates(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        requested_by=requested_by,
        include_unescalated=include_unescalated,
        storage_service=storage_service,
        commit=commit,
    )
