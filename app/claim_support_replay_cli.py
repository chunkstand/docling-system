from __future__ import annotations

import argparse
import json

import yaml

from app.db.session import get_session_factory
from app.services.claim_support_policy_impacts import (
    claim_support_policy_change_impact_alerts,
    claim_support_policy_change_impact_fixture_candidates,
    promote_claim_support_policy_change_impact_fixture_candidates,
    record_claim_support_policy_change_impact_alert_escalations,
)
from app.services.storage import StorageService


def _print_claim_support_replay_alert_table(payload: dict) -> None:
    rows = payload.get("items") or []
    print(
        "change_impact_id\talert_kind\tseverity\treplay_status\t"
        "status_age_hours\trecommended_action\tescalation_events"
    )
    for row in rows:
        change_impact = row.get("change_impact") or {}
        print(
            "\t".join(
                [
                    str(change_impact.get("change_impact_id") or ""),
                    str(row.get("alert_kind") or ""),
                    str(row.get("severity") or ""),
                    str(row.get("replay_status") or ""),
                    str(row.get("status_age_hours") or 0),
                    str(row.get("recommended_action") or ""),
                    str(len(row.get("escalation_events") or [])),
                ]
            )
        )


def _validate_claim_support_replay_alert_args(
    parser: argparse.ArgumentParser,
    *,
    stale_after_hours: int,
    limit: int,
) -> None:
    if stale_after_hours < 1 or stale_after_hours > 720:
        parser.error("--stale-after-hours must be between 1 and 720.")
    if limit < 1 or limit > 200:
        parser.error("--limit must be between 1 and 200.")


def run_claim_support_replay_alerts() -> None:
    parser = argparse.ArgumentParser(
        description="Report stale or blocked claim-support policy replay impacts."
    )
    parser.add_argument("--policy-name", default=None)
    parser.add_argument("--stale-after-hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--format", choices=["json", "yaml", "table"], default="json")
    parser.add_argument(
        "--record-escalations",
        action="store_true",
        help="Persist idempotent semantic-governance escalation receipts for returned alerts.",
    )
    parser.add_argument(
        "--requested-by",
        default="docling-system",
        help="Operator identifier recorded when --record-escalations is used.",
    )
    args = parser.parse_args()
    _validate_claim_support_replay_alert_args(
        parser,
        stale_after_hours=args.stale_after_hours,
        limit=args.limit,
    )

    session_factory = get_session_factory()
    with session_factory() as session:
        if args.record_escalations:
            payload = record_claim_support_policy_change_impact_alert_escalations(
                session,
                policy_name=args.policy_name,
                stale_after_hours=args.stale_after_hours,
                limit=args.limit,
                requested_by=args.requested_by,
                storage_service=StorageService(),
            )
        else:
            payload = claim_support_policy_change_impact_alerts(
                session,
                policy_name=args.policy_name,
                stale_after_hours=args.stale_after_hours,
                limit=args.limit,
            )
    payload_json = payload.model_dump(mode="json")
    if args.format == "yaml":
        print(yaml.safe_dump(payload_json, sort_keys=False, allow_unicode=True))
        return
    if args.format == "table":
        _print_claim_support_replay_alert_table(payload_json)
        return
    print(json.dumps(payload_json))


def _print_claim_support_replay_fixture_table(payload: dict) -> None:
    rows = payload.get("items") or payload.get("candidates") or []
    print(
        "candidate_id\tchange_impact_id\talert_kind\tcase_id\t"
        "expected_verdict\talready_promoted\tpromotion_events"
    )
    for row in rows:
        print(
            "\t".join(
                [
                    str(row.get("candidate_id") or ""),
                    str(row.get("change_impact_id") or ""),
                    str(row.get("alert_kind") or ""),
                    str(row.get("case_id") or ""),
                    str(row.get("expected_verdict") or ""),
                    str(bool(row.get("already_promoted"))).lower(),
                    str(len(row.get("promotion_events") or [])),
                ]
            )
        )


def run_claim_support_replay_fixture_candidates() -> None:
    parser = argparse.ArgumentParser(
        description="Report or promote claim-support replay alert fixture candidates."
    )
    parser.add_argument("--policy-name", default=None)
    parser.add_argument("--stale-after-hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--format", choices=["json", "yaml", "table"], default="json")
    parser.add_argument(
        "--include-unescalated",
        action="store_true",
        help="Include stale or blocked alert rows that do not yet have escalation receipts.",
    )
    parser.add_argument(
        "--hide-promoted",
        action="store_true",
        help="Hide candidates that already have fixture-promotion governance events.",
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Create a governed fixture set and fixture-promotion receipt.",
    )
    parser.add_argument(
        "--fixture-set-name",
        default="claim_support_replay_alert_promotions",
    )
    parser.add_argument("--fixture-set-version", default="v1")
    parser.add_argument(
        "--requested-by",
        default="docling-system",
        help="Operator identifier recorded when --promote is used.",
    )
    args = parser.parse_args()
    _validate_claim_support_replay_alert_args(
        parser,
        stale_after_hours=args.stale_after_hours,
        limit=args.limit,
    )

    session_factory = get_session_factory()
    with session_factory() as session:
        if args.promote:
            payload = promote_claim_support_policy_change_impact_fixture_candidates(
                session,
                policy_name=args.policy_name,
                stale_after_hours=args.stale_after_hours,
                limit=args.limit,
                fixture_set_name=args.fixture_set_name,
                fixture_set_version=args.fixture_set_version,
                requested_by=args.requested_by,
                include_unescalated=args.include_unescalated,
                storage_service=StorageService(),
            )
        else:
            payload = claim_support_policy_change_impact_fixture_candidates(
                session,
                policy_name=args.policy_name,
                stale_after_hours=args.stale_after_hours,
                limit=args.limit,
                include_unescalated=args.include_unescalated,
                include_promoted=not args.hide_promoted,
            )
    payload_json = payload.model_dump(mode="json")
    if args.format == "yaml":
        print(yaml.safe_dump(payload_json, sort_keys=False, allow_unicode=True))
        return
    if args.format == "table":
        _print_claim_support_replay_fixture_table(payload_json)
        return
    print(json.dumps(payload_json))
