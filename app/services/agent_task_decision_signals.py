from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import coerce_utc_datetime, utcnow
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.schemas.agent_task_core import AgentTaskDecisionSignalResponse
from app.services.agent_task_decision_signal_integrity import (
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_EXPIRING_HOURS,
    closed_replay_alert_fixture_coverage_waiver_keys,
)
from app.services.agent_task_recommendation_metrics import get_agent_task_value_density
from app.services.claim_support_replay_alert_fixture_corpus import (
    active_replay_alert_fixture_corpus_snapshot_summary,
)


def get_agent_task_decision_signals(
    session: Session,
) -> list[AgentTaskDecisionSignalResponse]:
    rows: list[AgentTaskDecisionSignalResponse] = []
    replay_open_statuses = {"pending", "queued", "in_progress", "blocked"}
    replay_stale_cutoff = utcnow() - timedelta(hours=24)
    promoted_escalation_event_ids: list[UUID] = []
    for event_payload in session.scalars(
        select(SemanticGovernanceEvent.event_payload_json).where(
            SemanticGovernanceEvent.event_kind
            == CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND
        )
    ):
        promotion_payload = (event_payload or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        ) or {}
        for event_id in promotion_payload.get("source_escalation_event_ids") or []:
            try:
                promoted_escalation_event_ids.append(UUID(str(event_id)))
            except (TypeError, ValueError):
                continue
    active_corpus_summary = active_replay_alert_fixture_corpus_snapshot_summary(
        session,
        ensure_current=True,
    )
    if active_corpus_summary is not None:
        promoted_escalation_event_ids = []
        for event_id in active_corpus_summary.get("source_escalation_event_ids") or []:
            try:
                promoted_escalation_event_ids.append(UUID(str(event_id)))
            except (TypeError, ValueError):
                continue
    active_corpus_fixture_count = int((active_corpus_summary or {}).get("fixture_count") or 0)
    invalid_corpus_promotion_event_count = int(
        (active_corpus_summary or {}).get("invalid_promotion_event_count") or 0
    )
    active_corpus_governed = bool(
        ((active_corpus_summary or {}).get("governance_integrity") or {}).get("complete")
    )
    active_corpus_governance_failures = list(
        ((active_corpus_summary or {}).get("governance_integrity") or {}).get("failures") or []
    )
    unconverted_replay_escalation_count = int(
        session.scalar(
            select(func.count())
            .select_from(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND
            )
            .where(SemanticGovernanceEvent.created_at <= replay_stale_cutoff)
            .where(~SemanticGovernanceEvent.id.in_(promoted_escalation_event_ids))
        )
        or 0
    )
    replay_alert_fixture_coverage_waiver_artifacts = list(
        session.scalars(
            select(AgentTaskArtifact).where(
                AgentTaskArtifact.artifact_kind
                == CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND
            )
        )
    )
    waiver_now = utcnow()
    waiver_expiring_cutoff = waiver_now + timedelta(
        hours=CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_EXPIRING_HOURS
    )
    active_waiver_count = 0
    expiring_waiver_count = 0
    expired_waiver_count = 0
    unmanaged_waiver_count = 0
    closed_waiver_count = 0
    high_severity_active_waiver_count = 0
    promotable_waived_escalation_count = 0
    closed_waiver_keys, invalid_waiver_closure_count = (
        closed_replay_alert_fixture_coverage_waiver_keys(session)
    )
    for artifact in replay_alert_fixture_coverage_waiver_artifacts:
        payload = dict(artifact.payload_json or {})
        waiver_sha256 = str(payload.get("waiver_sha256") or "")
        if waiver_sha256 and (artifact.id, waiver_sha256) in closed_waiver_keys:
            closed_waiver_count += 1
            continue
        expires_at = coerce_utc_datetime(payload.get("waiver_expires_at"))
        severity = str(payload.get("waiver_severity") or "").strip().lower()
        try:
            stale_unconverted_count = int(
                payload.get("stale_unconverted_escalation_event_count") or 0
            )
        except (TypeError, ValueError):
            stale_unconverted_count = 0
        if expires_at is None or severity not in {"low", "medium", "high", "critical"}:
            unmanaged_waiver_count += 1
            continue
        if expires_at <= waiver_now:
            expired_waiver_count += 1
            continue
        active_waiver_count += 1
        if expires_at <= waiver_expiring_cutoff:
            expiring_waiver_count += 1
        if severity in {"high", "critical"}:
            high_severity_active_waiver_count += 1
        if stale_unconverted_count:
            promotable_waived_escalation_count += stale_unconverted_count
    blocked_replay_count = int(
        session.scalar(
            select(func.count())
            .select_from(ClaimSupportPolicyChangeImpact)
            .where(ClaimSupportPolicyChangeImpact.replay_status == "blocked")
        )
        or 0
    )
    stale_replay_count = int(
        session.scalar(
            select(func.count())
            .select_from(ClaimSupportPolicyChangeImpact)
            .where(ClaimSupportPolicyChangeImpact.replay_status.in_(replay_open_statuses))
            .where(
                func.coalesce(
                    ClaimSupportPolicyChangeImpact.replay_status_updated_at,
                    ClaimSupportPolicyChangeImpact.created_at,
                )
                <= replay_stale_cutoff
            )
        )
        or 0
    )
    open_replay_count = int(
        session.scalar(
            select(func.count())
            .select_from(ClaimSupportPolicyChangeImpact)
            .where(ClaimSupportPolicyChangeImpact.replay_status.in_(replay_open_statuses))
        )
        or 0
    )
    if blocked_replay_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_policy_change_impact_replay",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="degraded",
                reason=(
                    f"{blocked_replay_count} claim-support policy replay impact(s) "
                    "are blocked from closure."
                ),
                threshold_crossed="blocked_claim_support_replay_impacts>0",
                recommended_action=(
                    "Open the claim-support replay worklist and inspect blocked replay tasks."
                ),
            )
        )
    elif stale_replay_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_policy_change_impact_replay",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="watch",
                reason=(
                    f"{stale_replay_count} open claim-support policy replay impact(s) "
                    "are older than 24 hours."
                ),
                threshold_crossed="stale_claim_support_replay_impacts>0",
                recommended_action=(
                    "Refresh replay status or queue managed replay for stale impact rows."
                ),
            )
        )
    elif open_replay_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_policy_change_impact_replay",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="watch",
                reason=(f"{open_replay_count} claim-support policy replay impact(s) are open."),
                threshold_crossed="open_claim_support_replay_impacts>0",
                recommended_action=(
                    "Monitor the claim-support replay worklist until all impacts close."
                ),
            )
        )
    if unconverted_replay_escalation_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_policy_change_impact_fixture_coverage",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="watch",
                reason=(
                    f"{unconverted_replay_escalation_count} stale claim-support replay "
                    "escalation receipt(s) have not been promoted into fixture coverage."
                ),
                threshold_crossed="stale_unconverted_claim_support_replay_escalations>0",
                recommended_action=(
                    "Run docling-system-claim-support-replay-fixtures --promote for "
                    "stale escalated replay alerts."
                ),
            )
        )
    if active_corpus_fixture_count and not active_corpus_governed:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_corpus",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="degraded",
                reason=(
                    "The active replay-alert fixture corpus snapshot lacks complete "
                    "governance receipt integrity."
                ),
                threshold_crossed=(
                    "invalid_claim_support_replay_alert_fixture_corpus_snapshot_governance"
                ),
                recommended_action=(
                    "Inspect the corpus snapshot governance event, artifact, and "
                    f"receipt failures: {', '.join(active_corpus_governance_failures)}"
                ),
            )
        )
    elif invalid_corpus_promotion_event_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_corpus",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="degraded",
                reason=(
                    f"{invalid_corpus_promotion_event_count} replay-alert fixture "
                    "promotion governance event(s) were excluded from the active "
                    "fixture corpus snapshot."
                ),
                threshold_crossed=(
                    "invalid_claim_support_replay_alert_fixture_corpus_promotions>0"
                ),
                recommended_action=(
                    "Inspect promotion receipts, artifacts, and fixture set hashes "
                    "before relying on replay-alert corpus coverage."
                ),
            )
        )
    elif active_corpus_fixture_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_corpus",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="healthy",
                reason=(
                    f"{active_corpus_fixture_count} replay-alert fixture(s) are "
                    "available in the active corpus snapshot."
                ),
                threshold_crossed=("active_claim_support_replay_alert_fixture_corpus_snapshot"),
                recommended_action=(
                    "Use the active corpus snapshot for future claim-support "
                    "calibration verification."
                ),
            )
        )
    if expired_waiver_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="degraded",
                reason=(
                    f"{expired_waiver_count} claim-support replay-alert fixture "
                    "coverage waiver artifact(s) are expired."
                ),
                threshold_crossed=("expired_claim_support_replay_alert_fixture_coverage_waivers>0"),
                recommended_action=(
                    "Promote replay-alert fixture coverage or rerun verification with "
                    "a fresh lifecycle-managed waiver before activation."
                ),
            )
        )
    if unmanaged_waiver_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="degraded",
                reason=(
                    f"{unmanaged_waiver_count} claim-support replay-alert fixture "
                    "coverage waiver artifact(s) lack expiry or severity metadata."
                ),
                threshold_crossed=(
                    "unmanaged_claim_support_replay_alert_fixture_coverage_waivers>0"
                ),
                recommended_action=(
                    "Rerun verification with lifecycle-managed waiver metadata or "
                    "promote the replay-alert fixtures."
                ),
            )
        )
    if high_severity_active_waiver_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="degraded",
                reason=(
                    f"{high_severity_active_waiver_count} active high-severity "
                    "claim-support replay-alert fixture coverage waiver artifact(s) exist."
                ),
                threshold_crossed=(
                    "high_severity_active_claim_support_replay_alert_fixture_coverage_waivers>0"
                ),
                recommended_action=(
                    "Require second approval before activation and prioritize fixture "
                    "promotion for the waived replay alerts."
                ),
            )
        )
    if expiring_waiver_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="watch",
                reason=(
                    f"{expiring_waiver_count} active claim-support replay-alert fixture "
                    "coverage waiver artifact(s) expire within 24 hours."
                ),
                threshold_crossed=(
                    "expiring_claim_support_replay_alert_fixture_coverage_waivers>0"
                ),
                recommended_action=(
                    "Promote fixture coverage or renew the waiver before it expires."
                ),
            )
        )
    if active_waiver_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="watch",
                reason=(
                    f"{active_waiver_count} active claim-support replay-alert fixture "
                    "coverage waiver artifact(s) exist."
                ),
                threshold_crossed=("active_claim_support_replay_alert_fixture_coverage_waivers>0"),
                recommended_action=(
                    "Review waiver lifecycle metadata and second-approval posture "
                    "before activating or relying on waived verifications."
                ),
            )
        )
    if invalid_waiver_closure_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver_closure",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="degraded",
                reason=(
                    f"{invalid_waiver_closure_count} claim-support replay-alert "
                    "fixture coverage waiver closure receipt(s) failed integrity checks."
                ),
                threshold_crossed=(
                    "invalid_claim_support_replay_alert_fixture_coverage_waiver_closures>0"
                ),
                recommended_action=(
                    "Inspect waiver-closure governance events before treating waiver "
                    "posture as closed."
                ),
            )
        )
    if promotable_waived_escalation_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver_remediation",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="watch",
                reason=(
                    f"{promotable_waived_escalation_count} waived stale replay "
                    "escalation receipt(s) are ready for fixture promotion."
                ),
                threshold_crossed=("waived_claim_support_replay_alert_escalations_promotable>0"),
                recommended_action=(
                    "Run docling-system-claim-support-replay-fixtures --promote to "
                    "replace the waiver with promoted hard-case coverage."
                ),
            )
        )
    if closed_waiver_count:
        rows.append(
            AgentTaskDecisionSignalResponse(
                task_type="claim_support_replay_alert_fixture_coverage_waiver_closure",
                workflow_version="claim_support_policy_change_impact_replay_v1",
                status="healthy",
                reason=(
                    f"{closed_waiver_count} claim-support replay-alert fixture "
                    "coverage waiver artifact(s) are closed by fixture-promotion receipts."
                ),
                threshold_crossed=("closed_claim_support_replay_alert_fixture_coverage_waivers>0"),
                recommended_action=(
                    "Retain waiver-closure receipts with the promotion artifact and "
                    "waiver hash in audit bundles."
                ),
            )
        )
    for value_row in get_agent_task_value_density(session):
        if value_row.recommendation_task_count == 0:
            continue
        if (value_row.downstream_improvement_rate or 0.0) < 0.4:
            rows.append(
                AgentTaskDecisionSignalResponse(
                    task_type=value_row.task_type,
                    workflow_version=value_row.workflow_version,
                    status="degraded",
                    reason="Downstream improvement rate is below 40%.",
                    threshold_crossed="downstream_improvement_rate<0.40",
                    recommended_action="Review recommendation thresholds and verifier gating.",
                )
            )
        elif (
            value_row.median_end_to_end_latency_ms is not None
            and value_row.median_end_to_end_latency_ms > 60_000
        ):
            rows.append(
                AgentTaskDecisionSignalResponse(
                    task_type=value_row.task_type,
                    workflow_version=value_row.workflow_version,
                    status="watch",
                    reason="Median end-to-end latency exceeds 60 seconds.",
                    threshold_crossed="median_end_to_end_latency_ms>60000",
                    recommended_action="Investigate queue, replay, or verification bottlenecks.",
                )
            )
        else:
            rows.append(
                AgentTaskDecisionSignalResponse(
                    task_type=value_row.task_type,
                    workflow_version=value_row.workflow_version,
                    status="healthy",
                    reason="Recommendation quality and latency are within current thresholds.",
                    threshold_crossed="none",
                    recommended_action="Continue collecting outcome labels and replay evidence.",
                )
            )
    return rows


__all__ = ["get_agent_task_decision_signals"]
