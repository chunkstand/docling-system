from __future__ import annotations

import app.services.claim_support_policy_impact_replay as _impact_replay
import app.services.claim_support_policy_impact_views as _impact_views
import app.services.claim_support_replay_alert_promotions as _replay_alert_promotions

_candidate_from_derivation = _replay_alert_promotions._candidate_from_derivation
list_claim_support_policy_change_impacts = _impact_views.list_claim_support_policy_change_impacts
claim_support_policy_change_impact_alerts = _impact_views.claim_support_policy_change_impact_alerts
get_claim_support_policy_change_impact = _impact_views.get_claim_support_policy_change_impact


def claim_support_replay_alert_fixture_coverage_summary(
    session,
    *,
    stale_after_hours=24,
    limit=50,
):
    return _replay_alert_promotions.claim_support_replay_alert_fixture_coverage_summary(
        session,
        stale_after_hours=stale_after_hours,
        limit=limit,
    )


def latest_claim_support_replay_alert_fixture_rows(
    session,
    *,
    include_promoted=True,
    limit=100,
    exclude_case_ids=None,
    stale_after_hours=24,
):
    return _replay_alert_promotions.latest_claim_support_replay_alert_fixture_rows(
        session,
        include_promoted=include_promoted,
        limit=limit,
        exclude_case_ids=exclude_case_ids,
        stale_after_hours=stale_after_hours,
    )


def claim_support_policy_change_impact_fixture_candidates(
    session,
    *,
    policy_name=None,
    stale_after_hours=24,
    limit=50,
    include_unescalated=False,
    include_promoted=True,
):
    return _replay_alert_promotions.claim_support_policy_change_impact_fixture_candidates(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_unescalated=include_unescalated,
        include_promoted=include_promoted,
    )


def promote_claim_support_policy_change_impact_fixture_candidates(
    session,
    *,
    policy_name=None,
    stale_after_hours=24,
    limit=50,
    fixture_set_name="claim_support_replay_alert_promotions",
    fixture_set_version="v1",
    requested_by="docling-system",
    include_unescalated=False,
    storage_service=None,
    commit=True,
):
    return _replay_alert_promotions.promote_claim_support_policy_change_impact_fixture_candidates(
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


def summarize_claim_support_policy_change_impacts(
    session,
    *,
    policy_name=None,
    stale_after_hours=24,
):
    return _impact_views.summarize_claim_support_policy_change_impacts(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
    )


def claim_support_policy_change_impact_worklist(
    session,
    *,
    policy_name=None,
    stale_after_hours=24,
    limit=50,
    include_closed=False,
    change_impact_ids=None,
):
    return _impact_views.claim_support_policy_change_impact_worklist(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_closed=include_closed,
        change_impact_ids=change_impact_ids,
    )


def record_claim_support_policy_change_impact_alert_escalations(
    session,
    *,
    policy_name=None,
    stale_after_hours=24,
    limit=50,
    requested_by="docling-system",
    storage_service=None,
    commit=True,
):
    return _impact_views.record_claim_support_policy_change_impact_alert_escalations(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        requested_by=requested_by,
        storage_service=storage_service,
        commit=commit,
    )


def queue_claim_support_policy_change_impact_replay_tasks(
    session,
    change_impact_id,
    *,
    requested_by,
    parent_task_id=None,
):
    return _impact_replay.queue_claim_support_policy_change_impact_replay_tasks(
        session,
        change_impact_id,
        requested_by=requested_by,
        parent_task_id=parent_task_id,
    )


def refresh_claim_support_policy_change_impact_replay_status(
    session,
    change_impact_id,
    *,
    storage_service=None,
    commit=True,
):
    return _impact_replay.refresh_claim_support_policy_change_impact_replay_status(
        session,
        change_impact_id,
        storage_service=storage_service,
        commit=commit,
    )


def refresh_claim_support_policy_change_impacts_for_replay_task(
    session,
    task_id,
    *,
    storage_service=None,
    commit=True,
):
    return _impact_replay.refresh_claim_support_policy_change_impacts_for_replay_task(
        session,
        task_id,
        storage_service=storage_service,
        commit=commit,
    )
