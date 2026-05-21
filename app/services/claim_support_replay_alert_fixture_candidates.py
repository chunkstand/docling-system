from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import compact_strings as _string_list
from app.db.public.agent_tasks import AgentTask
from app.db.public.audit_and_evidence import ClaimEvidenceDerivation
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactAlertItemResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateListResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateSummaryResponse,
)
from app.services.claim_support_policy_impact_alerts import (
    claim_support_policy_change_impact_alerts,
)
from app.services.claim_support_replay_alert_promotions import (
    fixture_promotion_events_by_candidate,
)
from app.services.evidence import payload_sha256


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


candidate_from_derivation = _candidate_from_derivation


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

    promotion_events_by_candidate = fixture_promotion_events_by_candidate(session)
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
