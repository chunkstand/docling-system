from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.cli_commands.common import lazy_service_attr
from app.cli_commands.search_harness_support import (
    _MATERIALIZE_SOURCE_TYPE_CHOICES,
    add_release_gate_threshold_args,
    add_replay_source_type_argument,
    replay_source_types_or_default,
)
from app.db.session import get_session_factory
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
    SearchHarnessOptimizationRequest,
)


def run_materialize_retrieval_learning_dataset(
    *,
    session_factory_func=get_session_factory,
    materialize_retrieval_learning_dataset_func=None,
) -> None:
    if materialize_retrieval_learning_dataset_func is None:
        materialize_retrieval_learning_dataset_func = lazy_service_attr(
            "app.services.retrieval_learning",
            "materialize_retrieval_learning_dataset",
        )
    parser = argparse.ArgumentParser(
        description="Materialize durable retrieval judgments and hard negatives for reranker work."
    )
    parser.add_argument("--limit", type=int, default=200, help="Maximum rows per source set.")
    parser.add_argument(
        "--source-type",
        action="append",
        choices=list(_MATERIALIZE_SOURCE_TYPE_CHOICES),
        dest="source_types",
        help=(
            "Source family to mine. May be repeated; defaults to feedback and replay. "
            "Use claim_support_replay_alert_corpus for the governed replay-alert fixture corpus "
            "or technical_report_claim_feedback for court-grade claim feedback."
        ),
    )
    parser.add_argument("--set-name", default=None, help="Optional unique judgment set name.")
    parser.add_argument(
        "--created-by",
        default="cli",
        help="Operator or process name to record on the judgment set and governance event.",
    )
    parser.add_argument(
        "--search-harness-evaluation-id",
        type=UUID,
        default=None,
        help="Optional harness evaluation linked to the materialized training run.",
    )
    parser.add_argument(
        "--search-harness-release-id",
        type=UUID,
        default=None,
        help="Optional harness release linked to the materialized training run.",
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = materialize_retrieval_learning_dataset_func(
            session,
            limit=args.limit,
            source_types=args.source_types,
            set_name=args.set_name,
            created_by=args.created_by,
            search_harness_evaluation_id=args.search_harness_evaluation_id,
            search_harness_release_id=args.search_harness_release_id,
        )
        session.commit()
    print(json.dumps(payload))


def run_evaluate_retrieval_learning_candidate(
    *,
    session_factory_func=get_session_factory,
    evaluate_retrieval_learning_candidate_func=None,
) -> None:
    if evaluate_retrieval_learning_candidate_func is None:
        evaluate_retrieval_learning_candidate_func = lazy_service_attr(
            "app.services.retrieval_learning",
            "evaluate_retrieval_learning_candidate",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate and gate a candidate harness with explicit retrieval-learning "
            "training-run provenance."
        )
    )
    parser.add_argument("candidate_harness_name", help="Candidate search harness name.")
    parser.add_argument(
        "--retrieval-training-run-id",
        type=UUID,
        default=None,
        help="Training run to bind to the candidate; defaults to the latest completed run.",
    )
    parser.add_argument(
        "--baseline-harness-name",
        default="default_v1",
        help="Baseline harness name to compare against.",
    )
    add_replay_source_type_argument(parser)
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    add_release_gate_threshold_args(parser)
    parser.add_argument("--requested-by", default="cli", help="Release gate requester.")
    parser.add_argument("--review-note", default=None, help="Optional review note.")
    args = parser.parse_args()

    request = RetrievalLearningCandidateEvaluationRequest(
        retrieval_training_run_id=args.retrieval_training_run_id,
        candidate_harness_name=args.candidate_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        source_types=replay_source_types_or_default(args.source_types),
        limit=args.limit,
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
        requested_by=args.requested_by,
        review_note=args.review_note,
    )
    session_factory = session_factory_func()
    with session_factory() as session:
        payload = evaluate_retrieval_learning_candidate_func(session, request)
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))
    if payload.gate_outcome != "passed":
        raise SystemExit(1)


def run_create_retrieval_reranker_artifact(
    *,
    session_factory_func=get_session_factory,
    create_retrieval_reranker_artifact_func=None,
) -> None:
    if create_retrieval_reranker_artifact_func is None:
        create_retrieval_reranker_artifact_func = lazy_service_attr(
            "app.services.retrieval_learning",
            "create_retrieval_reranker_artifact",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a versioned reranker artifact from a retrieval training run, "
            "evaluate it through a harness release gate, and emit change impact."
        )
    )
    parser.add_argument("candidate_harness_name", help="Candidate search harness name.")
    parser.add_argument(
        "--retrieval-training-run-id",
        type=UUID,
        default=None,
        help="Training run to bind to the artifact; defaults to the latest completed run.",
    )
    parser.add_argument("--artifact-name", default=None, help="Optional artifact name.")
    parser.add_argument(
        "--baseline-harness-name",
        default="default_v1",
        help="Baseline harness name to compare against.",
    )
    parser.add_argument(
        "--base-harness-name",
        default="default_v1",
        help="Base harness used to derive the artifact override.",
    )
    add_replay_source_type_argument(parser)
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    add_release_gate_threshold_args(parser)
    parser.add_argument("--requested-by", default="cli", help="Release gate requester.")
    parser.add_argument("--review-note", default=None, help="Optional review note.")
    args = parser.parse_args()

    request = RetrievalRerankerArtifactRequest(
        retrieval_training_run_id=args.retrieval_training_run_id,
        artifact_name=args.artifact_name,
        candidate_harness_name=args.candidate_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        base_harness_name=args.base_harness_name,
        source_types=replay_source_types_or_default(args.source_types),
        limit=args.limit,
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
        requested_by=args.requested_by,
        review_note=args.review_note,
    )
    session_factory = session_factory_func()
    with session_factory() as session:
        payload = create_retrieval_reranker_artifact_func(session, request)
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))
    if payload.gate_outcome != "passed":
        raise SystemExit(1)


def run_optimize_search_harness(
    *,
    session_factory_func=get_session_factory,
    run_search_harness_optimization_loop_func=None,
) -> None:
    if run_search_harness_optimization_loop_func is None:
        run_search_harness_optimization_loop_func = lazy_service_attr(
            "app.services.search_harness_optimization",
            "run_search_harness_optimization_loop",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded local hill-climbing loop over transient search harness overrides."
        )
    )
    parser.add_argument("base_harness_name", help="Base harness to optimize from.")
    parser.add_argument(
        "--candidate-harness-name",
        help="Transient candidate harness alias. Defaults to <base_harness_name>_loop.",
    )
    parser.add_argument(
        "--baseline-harness-name",
        default="default_v1",
        help="Baseline harness name to compare against.",
    )
    add_replay_source_type_argument(parser)
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=2,
        help="Maximum number of hill-climbing iterations to run.",
    )
    parser.add_argument(
        "--field",
        action="append",
        dest="tune_fields",
        help="Optional tuning field to include. Can be passed multiple times.",
    )
    add_release_gate_threshold_args(parser)
    args = parser.parse_args()

    candidate_harness_name = args.candidate_harness_name or f"{args.base_harness_name}_loop"
    request = SearchHarnessOptimizationRequest(
        base_harness_name=args.base_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        candidate_harness_name=candidate_harness_name,
        source_types=replay_source_types_or_default(args.source_types),
        limit=args.limit,
        iterations=args.iterations,
        tune_fields=args.tune_fields or [],
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
    )

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = run_search_harness_optimization_loop_func(session, request)
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))
