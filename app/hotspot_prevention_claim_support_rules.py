from __future__ import annotations

import re
from collections.abc import Callable

from app.hotspot_prevention_classifier_support import ClassifiedLine, blocked
from app.hotspot_prevention_diff import ChangedLine

_FUNCTION_OR_CLASS_PREFIXES = ("def _", "async def _", "def ", "async def ", "class ")
ClaimSupportRouteRule = tuple[tuple[str, ...], Callable[[str], bool], str, str]


def _claim_support_route_decision(
    *,
    stripped: str,
    line: ChangedLine,
    routes: tuple[ClaimSupportRouteRule, ...],
    fallback_message: str,
) -> ClassifiedLine | None:
    lowered = stripped.lower()
    for patterns, lowered_matcher, category, message in routes:
        if any(re.match(pattern, stripped) for pattern in patterns) or lowered_matcher(
            lowered
        ):
            return blocked(line, category, message)
    if stripped.startswith(_FUNCTION_OR_CLASS_PREFIXES):
        return blocked(line, "residual_owner_helper", fallback_message)
    return None


_CLAIM_SUPPORT_POLICY_IMPACT_VIEW_ROUTES: tuple[ClaimSupportRouteRule, ...] = (
    (
        (
            r"(async def |def )_(worklist_|hours_since|alert_row_ids)",
            r"(async def |def )claim_support_policy_change_impact_worklist",
        ),
        lambda lowered: "worklist" in lowered and "impact" in lowered,
        "worklist_assembly_logic",
        "claim-support worklist assembly belongs in "
        "app/services/claim_support_policy_impact_worklist.py",
    ),
    (
        (
            r"(async def |def )_(alert_|fresh_alert_worklist_item)",
            (
                r"(async def |def )_("
                r"record_alert_escalation_event|"
                r"refresh_existing_evidence_manifests_for_alert_item)"
            ),
            r"(async def |def )claim_support_policy_change_impact_alerts",
            r"(async def |def )record_claim_support_policy_change_impact_alert_escalations",
        ),
        lambda lowered: "escalation" in lowered
        or "claim_support_policy_impact_replay_escalated" in lowered,
        "alert_escalation_logic",
        "claim-support alert escalation logic belongs in "
        "app/services/claim_support_policy_impact_alerts.py",
    ),
)

_CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ROUTES: tuple[ClaimSupportRouteRule, ...] = (
    (
        (
            r"(async def |def )_(recommended_source_task|validated_replay_work_items)",
            r"(async def |def )_(queue_agent_task|created_task_spec)",
            r"(async def |def )queue_claim_support_policy_change_impact_replay_tasks",
        ),
        lambda lowered: "replay" in lowered
        and ("queue" in lowered or "recommendation" in lowered),
        "replay_queueing_logic",
        "claim-support replay queueing belongs in "
        "app/services/claim_support_policy_impact_replay_queue.py",
    ),
    (
        (
            r"(async def |def )_("
            r"record_replay_closure_governance_event|verify_terminal_replay_"
            r")",
            r"(async def |def )refresh_claim_support_policy_change_impact_replay_status",
            r"(async def |def )refresh_claim_support_policy_change_impacts_for_replay_task",
        ),
        lambda lowered: "replay_closure" in lowered
        or "closed claim support impact replay" in lowered,
        "replay_closure_logic",
        "claim-support replay closure logic belongs in "
        "app/services/claim_support_policy_impact_replay_closure.py",
    ),
)

_CLAIM_SUPPORT_REPLAY_ALERT_PROMOTION_ROUTES: tuple[ClaimSupportRouteRule, ...] = (
    (
        (
            (
                r"(async def |def )_("
                r"draft_payload_from_task|fallback_draft_payload_from_derivation)"
            ),
            r"(async def |def )_(expected_verdict_for_fixture|fixture_candidate_)",
            (
                r"(async def |def )_("
                r"candidate_from_derivation|derivations_for_alert_item|"
                r"draft_tasks_for_derivations)"
            ),
            r"(async def |def )claim_support_policy_change_impact_fixture_candidates",
        ),
        lambda lowered: "candidate" in lowered and "fixture" in lowered,
        "fixture_candidate_derivation_logic",
        "claim-support replay-alert candidate derivation belongs in "
        "app/services/claim_support_replay_alert_fixture_candidates.py",
    ),
    (
        (
            r"(async def |def )_(promotion_event_|fixture_promotion_anchor_task_id)",
            r"(async def |def )_(record_fixture_promotion_event|waiver_)",
            (
                r"(async def |def )_("
                r"record_replay_alert_fixture_coverage_waiver_closure_)"
            ),
            r"(async def |def )promote_claim_support_policy_change_impact_fixture_candidates",
        ),
        lambda lowered: "waiver_closure" in lowered or "fixture_promotion" in lowered,
        "promotion_governance_logic",
        "claim-support replay-alert promotion governance belongs in "
        "app/services/claim_support_replay_alert_promotion_governance.py",
    ),
)

_CLAIM_SUPPORT_EVALUATION_ROUTES: tuple[ClaimSupportRouteRule, ...] = (
    (
        (
            (
                r"(async def |def )_("
                r"(fixture_uuid|source_card|draft_fixture|graph_fixture_case)|"
                r"fixture_from_fixture_set)"
            ),
            (
                r"(async def |def )("
                r"default_claim_support_evaluation_fixtures|"
                r"ensure_claim_support_fixture_set|"
                r"mine_claim_support_failure_fixtures)"
            ),
        ),
        lambda lowered: "fixture_set" in lowered or "mined_failure" in lowered,
        "fixture_authoring_logic",
        "claim-support fixture authoring belongs in "
        "app/services/claim_support_evaluation_fixtures.py",
    ),
    (
        (
            (
                r"(async def |def )_("
                r"(thresholds_payload|normalize_string_list|policy_payload_sha256)|"
                r"policy_row_from_payload|validated_policy_payload)"
            ),
            (
                r"(async def |def )("
                r"build_claim_support_calibration_policy_payload|"
                r"get_active_claim_support_calibration_policy|"
                r"ensure_claim_support_calibration_policy)"
            ),
            (
                r"(async def |def )("
                r"draft_claim_support_calibration_policy|"
                r"resolve_claim_support_calibration_policy|"
                r"activate_claim_support_calibration_policy)"
            ),
        ),
        lambda lowered: "calibration_policy" in lowered
        or "required_hard_case_kinds" in lowered,
        "calibration_policy_logic",
        "claim-support calibration policy logic belongs in "
        "app/services/claim_support_calibration_policies.py",
    ),
    (
        (
            r"(async def |def )_verdict_metrics",
            (
                r"(async def |def )("
                r"evaluate_claim_support_judge_fixture_set|"
                r"persist_claim_support_judge_evaluation)"
            ),
        ),
        lambda lowered: "judge_technical_report_claim_support" in lowered
        or "case_results" in lowered,
        "judge_evaluation_runtime_logic",
        "claim-support judge evaluation runtime belongs in "
        "app/services/claim_support_judge_evaluation_runs.py",
    ),
)

_CLAIM_SUPPORT_POLICY_GOVERNANCE_ROUTES: tuple[ClaimSupportRouteRule, ...] = (
    (
        (
            (
                r"(async def |def )_("
                r"(policy_snapshot|policy_diff|task_snapshot|artifact_snapshot)|"
                r"support_derivation_snapshot|verification_snapshot)"
            ),
            (
                r"(async def |def )("
                r"claim_support_policy_change_impact_payload_sha256|"
                r"build_claim_support_policy_change_impact_payload|"
                r"persist_claim_support_policy_change_impact)"
            ),
        ),
        lambda lowered: "replay_recommendations" in lowered
        or "affected_support_judgment_count" in lowered,
        "change_impact_governance_logic",
        "claim-support change-impact governance belongs in "
        "app/services/claim_support_policy_change_impact_governance.py",
    ),
    (
        (
            (
                r"(async def |def )_("
                r"(signature_payload|fixture_set_snapshot|fixture_set_diff)|"
                r"evaluation_snapshot|prov_jsonld|receipt)"
            ),
            (
                r"(async def |def )("
                r"build_claim_support_policy_activation_governance_payload|"
                r"record_claim_support_policy_activation_governance_event)"
            ),
        ),
        lambda lowered: "activation_governance" in lowered
        or "claim_support_policy_activated" in lowered,
        "activation_governance_logic",
        "claim-support activation governance belongs in "
        "app/services/claim_support_policy_activation_governance.py",
    ),
)

_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_ROUTES: tuple[ClaimSupportRouteRule, ...] = (
    (
        (
            (
                r"(async def |def )_("
                r"fixture_by_candidate|candidate_payloads_for_fixture_set|"
                r"case_identity_sha256)"
            ),
            r"(async def |def )_(promotion_context|active_snapshot|supersede_active_snapshots)",
            (
                r"(async def |def )("
                r"build_replay_alert_fixture_corpus|"
                r"ensure_active_replay_alert_fixture_corpus_snapshot)"
            ),
        ),
        lambda lowered: (
            "replay_alert_fixture_corpus_snapshot" in lowered and "build" in lowered
        ),
        "corpus_build_logic",
        "claim-support replay-alert corpus build logic belongs in "
        "app/services/claim_support_replay_alert_fixture_corpus_build.py",
    ),
    (
        (
            (
                r"(async def |def )_("
                r"snapshot_source_events|snapshot_anchor_task_id|"
                r"snapshot_governance_)"
            ),
            (
                r"(async def |def )_("
                r"snapshot_row_hash_payload_from_db|snapshot_rows_for_integrity)"
            ),
            (
                r"(async def |def )("
                r"record_replay_alert_fixture_corpus_snapshot_governance|"
                r"replay_alert_fixture_corpus_snapshot_governance_integrity)"
            ),
        ),
        lambda lowered: "governance_integrity" in lowered
        or "semantic_governance_event_id" in lowered,
        "corpus_governance_logic",
        "claim-support replay-alert corpus governance belongs in "
        "app/services/claim_support_replay_alert_fixture_corpus_governance.py",
    ),
)


def classify_claim_support_policy_impact_views_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    return _claim_support_route_decision(
        stripped=stripped,
        line=line,
        routes=_CLAIM_SUPPORT_POLICY_IMPACT_VIEW_ROUTES,
        fallback_message=(
            "new claim-support policy impact view helpers belong in focused owner "
            "modules"
        ),
    )


def classify_claim_support_policy_impact_replay_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    return _claim_support_route_decision(
        stripped=stripped,
        line=line,
        routes=_CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ROUTES,
        fallback_message=(
            "new claim-support replay helpers belong in focused replay owner modules"
        ),
    )


def classify_claim_support_replay_alert_promotions_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    return _claim_support_route_decision(
        stripped=stripped,
        line=line,
        routes=_CLAIM_SUPPORT_REPLAY_ALERT_PROMOTION_ROUTES,
        fallback_message=(
            "new replay-alert promotion helpers belong in focused owner modules"
        ),
    )


def classify_claim_support_evaluations_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    return _claim_support_route_decision(
        stripped=stripped,
        line=line,
        routes=_CLAIM_SUPPORT_EVALUATION_ROUTES,
        fallback_message=(
            "new claim-support evaluation helpers belong in focused owner modules"
        ),
    )


def classify_claim_support_policy_governance_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    return _claim_support_route_decision(
        stripped=stripped,
        line=line,
        routes=_CLAIM_SUPPORT_POLICY_GOVERNANCE_ROUTES,
        fallback_message=(
            "new claim-support governance helpers belong in focused owner modules"
        ),
    )


def classify_claim_support_replay_alert_fixture_corpus_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    return _claim_support_route_decision(
        stripped=stripped,
        line=line,
        routes=_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_ROUTES,
        fallback_message=(
            "new replay-alert corpus helpers belong in focused owner modules"
        ),
    )
