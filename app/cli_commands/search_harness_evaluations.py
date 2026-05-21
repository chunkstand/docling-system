from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.cli_commands.common import lazy_service_attr
from app.cli_commands.search_harness_support import (
    add_release_gate_threshold_args,
    add_replay_source_type_argument,
    build_gate_request,
    replay_source_types_or_default,
)
from app.db.session import get_session_factory
from app.schemas.search import SearchHarnessEvaluationRequest


def run_eval_reranker(
    *,
    session_factory_func=get_session_factory,
    evaluate_search_harness_func=None,
) -> None:
    if evaluate_search_harness_func is None:
        evaluate_search_harness_func = lazy_service_attr(
            "app.services.search_harness_evaluations",
            "evaluate_search_harness",
        )
    parser = argparse.ArgumentParser(
        description="Evaluate a candidate search harness against replay and corpus query sets."
    )
    parser.add_argument("candidate_harness_name", help="Candidate search harness name.")
    parser.add_argument(
        "--baseline-harness-name",
        default="default_v1",
        help="Baseline harness name to compare against.",
    )
    add_replay_source_type_argument(parser)
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    args = parser.parse_args()

    request = SearchHarnessEvaluationRequest(
        candidate_harness_name=args.candidate_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        source_types=replay_source_types_or_default(args.source_types),
        limit=args.limit,
    )
    session_factory = session_factory_func()
    with session_factory() as session:
        payload = evaluate_search_harness_func(session, request)
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def run_search_harness_evaluation_list(
    *,
    session_factory_func=get_session_factory,
    list_search_harness_evaluations_func=None,
) -> None:
    if list_search_harness_evaluations_func is None:
        list_search_harness_evaluations_func = lazy_service_attr(
            "app.services.search_harness_evaluations",
            "list_search_harness_evaluations",
        )
    parser = argparse.ArgumentParser(description="List persisted search harness evaluations.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum evaluations to return.")
    parser.add_argument(
        "--candidate-harness-name",
        help="Optional candidate harness name filter.",
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = list_search_harness_evaluations_func(
            session,
            limit=args.limit,
            candidate_harness_name=args.candidate_harness_name,
        )
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_search_harness_evaluation_show(
    *,
    session_factory_func=get_session_factory,
    get_search_harness_evaluation_detail_func=None,
) -> None:
    if get_search_harness_evaluation_detail_func is None:
        get_search_harness_evaluation_detail_func = lazy_service_attr(
            "app.services.search_harness_evaluations",
            "get_search_harness_evaluation_detail",
        )
    parser = argparse.ArgumentParser(
        description="Show one persisted search harness evaluation with source replay provenance."
    )
    parser.add_argument("evaluation_id", type=UUID, help="Search harness evaluation UUID.")
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = get_search_harness_evaluation_detail_func(session, args.evaluation_id)
    print(json.dumps(payload.model_dump(mode="json")))


def run_gate_search_harness_release(
    *,
    session_factory_func=get_session_factory,
    evaluate_search_harness_func=None,
    record_search_harness_release_gate_func=None,
) -> None:
    if evaluate_search_harness_func is None:
        evaluate_search_harness_func = lazy_service_attr(
            "app.services.search_harness_evaluations",
            "evaluate_search_harness",
        )
    if record_search_harness_release_gate_func is None:
        record_search_harness_release_gate_func = lazy_service_attr(
            "app.services.search_release_gate",
            "record_search_harness_release_gate",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a candidate search harness and fail fast when replay/eval guardrails do "
            "not pass."
        )
    )
    parser.add_argument("candidate_harness_name", help="Candidate search harness name.")
    parser.add_argument(
        "--baseline-harness-name",
        default="default_v1",
        help="Baseline harness name to compare against.",
    )
    add_replay_source_type_argument(parser)
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    add_release_gate_threshold_args(parser)
    parser.add_argument("--requested-by", default=None, help="Optional release gate requester.")
    parser.add_argument("--review-note", default=None, help="Optional release gate review note.")
    args = parser.parse_args()

    request = SearchHarnessEvaluationRequest(
        candidate_harness_name=args.candidate_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        source_types=replay_source_types_or_default(args.source_types),
        limit=args.limit,
    )
    gate_request = build_gate_request(args)

    session_factory = session_factory_func()
    with session_factory() as session:
        evaluation = evaluate_search_harness_func(session, request)
        release = record_search_harness_release_gate_func(
            session,
            evaluation,
            gate_request,
            requested_by=args.requested_by,
            review_note=args.review_note,
        )
        session.commit()

    print(
        json.dumps(
            {
                "candidate_harness_name": request.candidate_harness_name,
                "baseline_harness_name": request.baseline_harness_name,
                "evaluation": evaluation.model_dump(mode="json"),
                "release": release.model_dump(mode="json"),
                "gate": {
                    "outcome": release.outcome,
                    "metrics": release.metrics,
                    "reasons": release.reasons,
                    "details": release.details,
                },
            }
        )
    )
    if release.outcome != "passed":
        raise SystemExit(1)
