from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import compact_strings as _string_list
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    ClaimEvidenceDerivation,
    ClaimSupportFixtureSet,
    EvidenceManifest,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
)
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactAlertItemResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateListResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse,
    ClaimSupportPolicyChangeImpactFixturePromotionEventRef,
    ClaimSupportPolicyChangeImpactFixturePromotionResponse,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_evaluations import (
    default_claim_support_evaluation_fixtures,
    ensure_claim_support_fixture_set,
)
from app.services.claim_support_payloads import (
    claim_support_fixture_promotion_payload as _fixture_promotion_payload,
)
from app.services.claim_support_replay_alert_fixture_corpus import (
    active_replay_alert_fixture_corpus_rows,
    active_replay_alert_fixture_corpus_snapshot_summary,
    ensure_active_replay_alert_fixture_corpus_snapshot,
    replay_alert_fixture_corpus_snapshot_summary,
)
from app.services.claim_support_replay_alert_waivers import (
    apply_replay_alert_fixture_coverage_promotion_to_waiver_ledgers,
    mark_replay_alert_fixture_coverage_waiver_ledger_closed,
    replay_alert_escalation_set_sha256,
    stale_unconverted_escalation_event_ids_from_waiver,
    waiver_artifact_ids_with_coverage_ledgers,
)
from app.services.evidence import payload_sha256
from app.services.semantic_governance import (
    active_semantic_basis,
    record_semantic_governance_event,
)
from app.services.storage import StorageService

CLAIM_SUPPORT_IMPACT_REPLAY_ESCALATION_EVENT_KIND = (
    SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED.value
)
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


def _fixture_promotion_events_by_candidate(
    session: Session,
) -> dict[str, list[ClaimSupportPolicyChangeImpactFixturePromotionEventRef]]:
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
                == CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND
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
            for event_id in (
                active_corpus_snapshot.get("source_escalation_event_ids") or []
            )
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
        "latest_promoted_fixture_set": promotion_summaries[0]
        if promotion_summaries
        else None,
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
    snapshot_summary = replay_alert_fixture_corpus_snapshot_summary(
        snapshot,
        session=session,
    )
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


def _looks_like_technical_report_draft(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    required = {
        "title",
        "goal",
        "target_length",
        "harness_task_id",
        "generator_mode",
        "claims",
        "markdown",
    }
    return required.issubset(payload)


def _draft_payload_from_task(task: AgentTask | None) -> tuple[dict[str, Any] | None, str]:
    if task is None:
        return None, "missing_draft_task"
    result_payload = dict(task.result_json or {})
    candidates = [
        ((result_payload.get("payload") or {}).get("draft") if result_payload else None),
        result_payload.get("draft"),
        result_payload,
    ]
    for candidate in candidates:
        if _looks_like_technical_report_draft(candidate):
            return deepcopy(candidate), "draft_task_payload"
    return None, "draft_task_missing_valid_payload"


def _fallback_draft_payload_from_derivation(
    row: ClaimEvidenceDerivation,
) -> dict[str, Any]:
    claim_text = row.claim_text or row.claim_id
    source_search_result_ids = _string_list(row.source_search_request_result_ids_json)
    support_judgment = dict(row.support_judgment_json or {})
    if not source_search_result_ids:
        source_search_result_ids = _string_list(
            support_judgment.get("source_search_request_result_ids") or []
        )
    section_id = f"section:replay_alert:{row.claim_id}"
    return {
        "document_kind": "technical_report",
        "title": "Claim Support Replay Alert Fixture",
        "goal": "Replay a claim-support policy change impact as evaluation coverage.",
        "audience": "Evaluation",
        "target_length": "short",
        "harness_task_id": str(row.agent_task_id or row.evidence_package_export_id),
        "generator_mode": "structured_fallback",
        "generator_model": None,
        "used_fallback": True,
        "llm_adapter_contract": {},
        "document_refs": [],
        "required_concept_keys": [],
        "sections": [
            {
                "section_id": section_id,
                "title": "Replay Alert Claim",
                "body_markdown": claim_text,
                "claim_ids": [row.claim_id],
            }
        ],
        "claims": [
            {
                "claim_id": row.claim_id,
                "section_id": section_id,
                "rendered_text": claim_text,
                "concept_keys": [],
                "evidence_card_ids": [],
                "graph_edge_ids": _string_list(row.graph_edge_ids_json),
                "fact_ids": _string_list(row.fact_ids_json),
                "assertion_ids": _string_list(row.assertion_ids_json),
                "source_document_ids": _string_list(row.source_document_ids_json),
                "support_level": row.support_verdict,
                "review_policy_status": "candidate_disclosed",
                "source_search_request_ids": _string_list(
                    row.source_search_request_ids_json
                ),
                "source_search_request_result_ids": source_search_result_ids,
                "source_evidence_package_export_ids": _string_list(
                    row.source_evidence_package_export_ids_json
                ),
                "source_evidence_package_sha256s": _string_list(
                    row.source_evidence_package_sha256s_json
                ),
                "source_evidence_trace_sha256s": _string_list(
                    row.source_evidence_trace_sha256s_json
                ),
                "provenance_lock": dict(row.provenance_lock_json or {}),
                "provenance_lock_sha256": row.provenance_lock_sha256,
                "support_verdict": row.support_verdict,
                "support_score": row.support_score,
                "support_judge_run_id": str(row.support_judge_run_id)
                if row.support_judge_run_id
                else None,
                "support_judgment": support_judgment,
                "support_judgment_sha256": row.support_judgment_sha256,
                "derivation_rule": row.derivation_rule,
                "evidence_package_export_id": str(row.evidence_package_export_id),
                "evidence_package_sha256": row.evidence_package_sha256,
                "derivation_sha256": row.derivation_sha256,
                "source_snapshot_sha256s": _string_list(row.source_snapshot_sha256s_json),
            }
        ],
        "blocked_claims": [],
        "evidence_cards": [],
        "source_evidence_package_exports": [],
        "graph_context": [],
        "evidence_package_export_id": str(row.evidence_package_export_id),
        "evidence_package_sha256": row.evidence_package_sha256,
        "source_snapshot_sha256s": _string_list(row.source_snapshot_sha256s_json),
        "support_judge_run_id": str(row.support_judge_run_id)
        if row.support_judge_run_id
        else None,
        "support_judgment_sha256s": [row.support_judgment_sha256]
        if row.support_judgment_sha256
        else [],
        "claim_support_summary": {
            "source": "claim_support_policy_change_impact_replay_alert",
            "source_support_verdict": row.support_verdict,
            "source_support_judgment_sha256": row.support_judgment_sha256,
        },
        "claim_derivations": [],
        "markdown": claim_text,
        "warnings": [
            "Fixture reconstructed from claim_evidence_derivations because the "
            "source draft task did not expose a complete technical-report draft payload."
        ],
        "success_metrics": [],
    }


def _expected_verdict_for_fixture(
    *,
    draft_source: str,
    derivation: ClaimEvidenceDerivation,
) -> str:
    if draft_source != "draft_task_payload":
        return "insufficient_evidence"
    support_judgment = dict(derivation.support_judgment_json or {})
    candidate = derivation.support_verdict or support_judgment.get("verdict")
    if candidate in {"supported", "unsupported", "insufficient_evidence"}:
        return str(candidate)
    return "insufficient_evidence"


def _fixture_candidate_identity_basis(
    *,
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
    derivation: ClaimEvidenceDerivation,
    draft_source: str,
    fixture_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_name": "claim_support_policy_impact_fixture_candidate_identity",
        "schema_version": "1.0",
        "change_impact_id": str(item.change_impact.change_impact_id),
        "impact_payload_sha256": item.change_impact.impact_payload_sha256,
        "alert_kind": item.alert_kind,
        "source_claim_derivation_id": str(derivation.id),
        "source_draft_task_id": str(derivation.agent_task_id)
        if derivation.agent_task_id
        else None,
        "source_support_judgment_sha256": derivation.support_judgment_sha256,
        "draft_source": draft_source,
        "fixture_sha256": fixture_sha256,
    }


def _fixture_candidate_source_basis(
    *,
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
    derivation: ClaimEvidenceDerivation,
    draft_source: str,
    fixture_sha256: str,
    candidate_identity_sha256: str,
) -> dict[str, Any]:
    escalation_event_ids = sorted({str(event.event_id) for event in item.escalation_events})
    return {
        "schema_name": "claim_support_policy_impact_fixture_candidate_source",
        "schema_version": "1.0",
        "candidate_identity_sha256": candidate_identity_sha256,
        "change_impact_id": str(item.change_impact.change_impact_id),
        "impact_payload_sha256": item.change_impact.impact_payload_sha256,
        "alert_kind": item.alert_kind,
        "replay_status": item.replay_status,
        "is_stale": item.is_stale,
        "escalation_event_ids": escalation_event_ids,
        "latest_escalation_event_id": str(item.latest_escalation_event_id)
        if item.latest_escalation_event_id
        else None,
        "affected_verification_task_ids": sorted(
            {str(task_id) for task_id in item.affected_verification_task_ids}
        ),
        "source_claim_derivation_id": str(derivation.id),
        "source_draft_task_id": str(derivation.agent_task_id)
        if derivation.agent_task_id
        else None,
        "source_support_verdict": derivation.support_verdict,
        "source_support_judgment_sha256": derivation.support_judgment_sha256,
        "draft_source": draft_source,
        "fixture_sha256": fixture_sha256,
    }


def _candidate_from_derivation(
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
    *,
    derivation: ClaimEvidenceDerivation,
    draft_task: AgentTask | None,
) -> ClaimSupportPolicyChangeImpactFixtureCandidateResponse:
    draft_payload, draft_source = _draft_payload_from_task(draft_task)
    if draft_payload is None:
        draft_payload = _fallback_draft_payload_from_derivation(derivation)
        draft_source = "reconstructed_claim_derivation"
    expected_verdict = _expected_verdict_for_fixture(
        draft_source=draft_source,
        derivation=derivation,
    )
    case_id = f"replay_alert_{item.change_impact.change_impact_id.hex}_{derivation.id.hex[:12]}"
    hard_case_kind = f"replay_alert_{item.alert_kind}_policy_change_impact"
    fixture = {
        "case_id": case_id,
        "description": (
            "Claim-support policy replay alert promoted into durable judge "
            "evaluation coverage."
        ),
        "hard_case_kind": hard_case_kind,
        "expected_verdict": expected_verdict,
        "claim_id": derivation.claim_id,
        "draft_payload": draft_payload,
    }
    identity_fixture_sha256 = payload_sha256(fixture)
    identity_basis = _fixture_candidate_identity_basis(
        item=item,
        derivation=derivation,
        draft_source=draft_source,
        fixture_sha256=identity_fixture_sha256,
    )
    candidate_id = payload_sha256(identity_basis)
    source_basis = _fixture_candidate_source_basis(
        item=item,
        derivation=derivation,
        draft_source=draft_source,
        fixture_sha256=identity_fixture_sha256,
        candidate_identity_sha256=candidate_id,
    )
    fixture["replay_alert_source"] = {
        **source_basis,
        "candidate_id": candidate_id,
        "candidate_identity": identity_basis,
        "activation_task_id": str(item.change_impact.activation_task_id)
        if item.change_impact.activation_task_id
        else None,
        "affected_verification_task_ids": [
            str(task_id) for task_id in item.affected_verification_task_ids
        ],
    }
    fixture_sha = payload_sha256(fixture)
    return ClaimSupportPolicyChangeImpactFixtureCandidateResponse(
        candidate_id=candidate_id,
        change_impact_id=item.change_impact.change_impact_id,
        alert_kind=item.alert_kind,
        severity=item.severity,
        replay_status=item.replay_status,
        is_stale=item.is_stale,
        source_claim_derivation_id=derivation.id,
        source_draft_task_id=derivation.agent_task_id,
        affected_verification_task_ids=list(item.affected_verification_task_ids),
        escalation_event_ids=[event.event_id for event in item.escalation_events],
        latest_escalation_event_id=item.latest_escalation_event_id,
        case_id=case_id,
        hard_case_kind=hard_case_kind,
        expected_verdict=expected_verdict,
        fixture_sha256=fixture_sha,
        fixture=fixture,
        source_payload_sha256=payload_sha256(source_basis),
        operator_links={
            "source_change_impact": (
                "/agent-tasks/claim-support-policy-change-impacts/"
                f"{item.change_impact.change_impact_id}"
            ),
            "source_draft_task": f"/agent-tasks/{derivation.agent_task_id}"
            if derivation.agent_task_id
            else None,
            "promote": (
                "/agent-tasks/claim-support-policy-change-impacts/"
                "alerts/fixture-promotions"
            ),
        },
    )


def _derivations_for_alert_item(
    session: Session,
    item: ClaimSupportPolicyChangeImpactAlertItemResponse,
) -> list[ClaimEvidenceDerivation]:
    derivation_ids = [
        UUID(str(value))
        for value in item.change_impact.impacted_claim_derivation_ids or []
        if value not in {None, ""}
    ]
    if not derivation_ids:
        return []
    return list(
        session.scalars(
            select(ClaimEvidenceDerivation)
            .where(ClaimEvidenceDerivation.id.in_(derivation_ids))
            .order_by(
                ClaimEvidenceDerivation.created_at.desc(),
                ClaimEvidenceDerivation.id.desc(),
            )
        )
    )


def _draft_tasks_for_derivations(
    session: Session,
    derivations: list[ClaimEvidenceDerivation],
) -> dict[UUID, AgentTask]:
    task_ids = [row.agent_task_id for row in derivations if row.agent_task_id is not None]
    if not task_ids:
        return {}
    return {
        row.id: row
        for row in session.scalars(select(AgentTask).where(AgentTask.id.in_(task_ids)))
    }


def claim_support_policy_change_impact_fixture_candidates(
    session: Session,
    *,
    policy_name: str | None = None,
    stale_after_hours: int = 24,
    limit: int = 50,
    include_unescalated: bool = False,
    include_promoted: bool = True,
) -> ClaimSupportPolicyChangeImpactFixtureCandidateListResponse:
    from app.services.claim_support_policy_impacts import (
        claim_support_policy_change_impact_alerts,
    )

    limit = max(1, limit)
    alert_feed = claim_support_policy_change_impact_alerts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
    )
    candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse] = []
    for item in alert_feed.items:
        if not include_unescalated and not item.escalation_events:
            continue
        derivations = _derivations_for_alert_item(session, item)
        draft_tasks = _draft_tasks_for_derivations(session, derivations)
        candidates.extend(
            _candidate_from_derivation(
                item,
                derivation=derivation,
                draft_task=draft_tasks.get(derivation.agent_task_id),
            )
            for derivation in derivations
        )

    promotion_events_by_candidate = _fixture_promotion_events_by_candidate(session)
    promoted_count = 0
    annotated_candidates: list[ClaimSupportPolicyChangeImpactFixtureCandidateResponse] = []
    for candidate in candidates:
        promotion_events = promotion_events_by_candidate.get(candidate.candidate_id, [])
        already_promoted = bool(promotion_events)
        if already_promoted:
            promoted_count += 1
        annotated = candidate.model_copy(
            update={
                "already_promoted": already_promoted,
                "promotion_events": promotion_events,
            }
        )
        if include_promoted or not already_promoted:
            annotated_candidates.append(annotated)

    matching_count = len(annotated_candidates)
    limited_items = annotated_candidates[:limit]
    source_escalation_ids = {
        event_id for candidate in candidates for event_id in candidate.escalation_event_ids
    }
    return ClaimSupportPolicyChangeImpactFixtureCandidateListResponse(
        summary=ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse(
            alert_matching_count=alert_feed.matching_count,
            candidate_count=len(candidates),
            promoted_candidate_count=promoted_count,
            unpromoted_candidate_count=len(candidates) - promoted_count,
            source_escalation_event_count=len(source_escalation_ids),
            stale_after_hours=stale_after_hours,
        ),
        generated_at=alert_feed.generated_at,
        stale_after_hours=alert_feed.stale_after_hours,
        limit=limit,
        matching_count=matching_count,
        item_count=len(limited_items),
        has_more=matching_count > len(limited_items),
        items=limited_items,
    )


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
) -> UUID | None:
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
    receipt_payload = {
        **receipt_basis,
        "receipt_sha256": payload_sha256(receipt_basis),
    }
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
    receipt_source_change_impact_ids = list(
        source_change_impact_ids
        or []
    ) or list(
        promotion_payload.get("source_change_impact_ids")
        or sorted({str(candidate.change_impact_id) for candidate in candidates})
    )
    receipt_source_escalation_event_ids = list(
        source_escalation_event_ids
        or []
    ) or list(
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
        "schema_name": (
            CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_RECEIPT_SCHEMA
        ),
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
        artifact_kind=(
            CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND
        ),
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
            "claim_support_replay_alert_fixture_coverage_waiver_closure": (
                receipt_payload
            ),
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
        active_corpus_snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(
            session,
            storage_service=storage_service,
            recorded_by=requested_by,
        )
        active_corpus_summary = replay_alert_fixture_corpus_snapshot_summary(
            active_corpus_snapshot,
            session=session,
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
            active_replay_fixture_corpus_snapshot_id=_uuid_or_none(
                active_corpus_summary.get("snapshot_id") if active_corpus_summary else None
            ),
            active_replay_fixture_corpus_sha256=(
                active_corpus_summary.get("snapshot_sha256")
                if active_corpus_summary
                else None
            ),
            active_replay_fixture_corpus_fixture_count=(
                int(active_corpus_summary.get("fixture_count") or 0)
                if active_corpus_summary
                else 0
            ),
            active_replay_fixture_corpus_governance_event_id=_uuid_or_none(
                active_corpus_summary.get("semantic_governance_event_id")
                if active_corpus_summary
                else None
            ),
            active_replay_fixture_corpus_governance_artifact_id=_uuid_or_none(
                active_corpus_summary.get("governance_artifact_id")
                if active_corpus_summary
                else None
            ),
            active_replay_fixture_corpus_governance_receipt_sha256=(
                active_corpus_summary.get("governance_receipt_sha256")
                if active_corpus_summary
                else None
            ),
            active_replay_fixture_corpus_governed=bool(
                (
                    (active_corpus_summary or {}).get("governance_integrity")
                    or {}
                ).get("complete")
            )
            if active_corpus_summary
            else False,
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
    event, artifact, created = _record_fixture_promotion_event(
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
    active_corpus_snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(
        session,
        storage_service=storage_service,
        recorded_by=requested_by,
    )
    active_corpus_summary = replay_alert_fixture_corpus_snapshot_summary(
        active_corpus_snapshot,
        session=session,
    )
    _refresh_existing_evidence_manifests_for_fixture_candidates(session, candidates)
    if commit:
        session.commit()
    else:
        session.flush()
    event_ref = _fixture_promotion_event_ref(event, artifact=artifact)
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
        active_replay_fixture_corpus_snapshot_id=_uuid_or_none(
            active_corpus_summary.get("snapshot_id") if active_corpus_summary else None
        ),
        active_replay_fixture_corpus_sha256=(
            active_corpus_summary.get("snapshot_sha256") if active_corpus_summary else None
        ),
        active_replay_fixture_corpus_fixture_count=(
            int(active_corpus_summary.get("fixture_count") or 0)
            if active_corpus_summary
            else 0
        ),
        active_replay_fixture_corpus_governance_event_id=_uuid_or_none(
            active_corpus_summary.get("semantic_governance_event_id")
            if active_corpus_summary
            else None
        ),
        active_replay_fixture_corpus_governance_artifact_id=_uuid_or_none(
            active_corpus_summary.get("governance_artifact_id")
            if active_corpus_summary
            else None
        ),
        active_replay_fixture_corpus_governance_receipt_sha256=(
            active_corpus_summary.get("governance_receipt_sha256")
            if active_corpus_summary
            else None
        ),
        active_replay_fixture_corpus_governed=bool(
            (
                (active_corpus_summary or {}).get("governance_integrity")
                or {}
            ).get("complete")
        )
        if active_corpus_summary
        else False,
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
