from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.cli_commands.common import lazy_service_attr
from app.db.session import get_session_factory
from app.services.storage import StorageService


def run_eval_candidates(
    *,
    session_factory_func=get_session_factory,
    list_quality_eval_candidates_func=None,
) -> None:
    if list_quality_eval_candidates_func is None:
        list_quality_eval_candidates_func = lazy_service_attr(
            "app.services.quality",
            "list_quality_eval_candidates",
        )
    parser = argparse.ArgumentParser(
        description="List mined evaluation candidates from failed evals and live search gaps."
    )
    parser.add_argument("--limit", type=int, default=12, help="Maximum number of candidates.")
    parser.add_argument(
        "--include-resolved",
        action="store_true",
        help="Include candidates that later evidence has already resolved.",
    )
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 100:
        parser.error("--limit must be between 1 and 100.")

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = list_quality_eval_candidates_func(
            session,
            limit=args.limit,
            include_resolved=args.include_resolved,
        )
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_evaluation_data_readiness(
    *,
    session_factory_func=get_session_factory,
    build_evaluation_data_readiness_report_func=None,
) -> None:
    if build_evaluation_data_readiness_report_func is None:
        build_evaluation_data_readiness_report_func = lazy_service_attr(
            "app.services.evaluation_data_readiness",
            "build_evaluation_data_readiness_report",
        )
    parser = argparse.ArgumentParser(
        description="Inspect whether the live DB has enough data to run retrieval gates."
    )
    parser.add_argument(
        "--manual-corpus-path",
        type=Path,
        default=Path("docs/evaluation_corpus.yaml"),
        help="Hand-authored evaluation corpus path.",
    )
    parser.add_argument(
        "--auto-corpus-path",
        type=Path,
        default=Path("storage/evaluation_corpus.auto.yaml"),
        help="Auto-generated evaluation corpus path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON readiness report.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = build_evaluation_data_readiness_report_func(
            session,
            manual_corpus_path=args.manual_corpus_path,
            auto_corpus_path=args.auto_corpus_path,
        )
    rendered = json.dumps(payload, indent=None if args.compact else 2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    print(rendered)


def run_regression_readiness_bootstrap(
    *,
    session_factory_func=get_session_factory,
    storage_service_factory=StorageService,
    bootstrap_regression_readiness_func=None,
) -> None:
    if bootstrap_regression_readiness_func is None:
        bootstrap_regression_readiness_func = lazy_service_attr(
            "app.services.regression_readiness_bootstrap",
            "bootstrap_regression_readiness",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Seed a fresh local checkout into regression-ready evaluation state using "
            "tracked bootstrap artifacts and live replay verification."
        )
    )
    parser.add_argument(
        "--bootstrap-document-path",
        type=Path,
        default=Path("docs/evaluation_bootstrap/regression_doc_03.pdf"),
        help="Reviewed PDF fixture to ingest and promote for the bootstrap run.",
    )
    parser.add_argument(
        "--manual-corpus-path",
        type=Path,
        default=Path("docs/evaluation_corpus.yaml"),
        help="Hand-authored manual evaluation corpus path.",
    )
    parser.add_argument(
        "--auto-corpus-seed-path",
        type=Path,
        default=Path("docs/evaluation_corpus.auto.bootstrap.yaml"),
        help="Tracked auto-corpus seed copied into storage before the bootstrap run.",
    )
    parser.add_argument(
        "--auto-corpus-path",
        type=Path,
        default=None,
        help="Override the runtime auto-corpus path. Defaults under the configured storage root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Override the readiness report output path. "
            "Defaults under the configured storage root."
        ),
    )
    parser.add_argument(
        "--live-gap-query",
        default="Blue Mesas readiness narrative explains how milestone six",
        help="Query text used to seed the zero-result live gap before ingest.",
    )
    parser.add_argument(
        "--replay-limit",
        type=int,
        default=25,
        help="Maximum number of replay cases per replay source.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = bootstrap_regression_readiness_func(
            session,
            storage_service=storage_service_factory(),
            bootstrap_document_path=args.bootstrap_document_path,
            manual_corpus_path=args.manual_corpus_path,
            auto_corpus_seed_path=args.auto_corpus_seed_path,
            auto_corpus_path=args.auto_corpus_path,
            output_path=args.output,
            live_gap_query=args.live_gap_query,
            replay_limit=args.replay_limit,
        )
        session.commit()
    print(json.dumps(payload, indent=None if args.compact else 2))


def run_court_grade_readiness_bootstrap(
    *,
    session_factory_func=get_session_factory,
    storage_service_factory=StorageService,
    bootstrap_court_grade_readiness_func=None,
) -> None:
    if bootstrap_court_grade_readiness_func is None:
        bootstrap_court_grade_readiness_func = lazy_service_attr(
            "app.services.court_grade_readiness_bootstrap",
            "bootstrap_court_grade_readiness",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Seed the court-grade readiness lanes on top of the strict "
            "regression-ready baseline using tracked bootstrap artifacts."
        )
    )
    parser.add_argument(
        "--manual-corpus-path",
        type=Path,
        default=Path("docs/evaluation_corpus.yaml"),
        help="Hand-authored manual evaluation corpus path.",
    )
    parser.add_argument(
        "--auto-corpus-path",
        type=Path,
        default=Path("storage/evaluation_corpus.auto.yaml"),
        help="Runtime auto-corpus path generated by the regression bootstrap.",
    )
    parser.add_argument(
        "--operator-feedback-seed-path",
        type=Path,
        default=Path("docs/evaluation_bootstrap/court_grade_operator_feedback.yaml"),
        help="Tracked operator-feedback seed input.",
    )
    parser.add_argument(
        "--claim-feedback-seed-path",
        type=Path,
        default=Path("docs/evaluation_bootstrap/court_grade_claim_feedback.yaml"),
        help="Tracked technical-report claim-feedback seed input.",
    )
    parser.add_argument(
        "--replay-alert-fixture-seed-path",
        type=Path,
        default=Path("docs/evaluation_bootstrap/court_grade_replay_alert_fixtures.yaml"),
        help="Tracked replay-alert fixture seed input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Override the readiness report output path. "
            "Defaults under the configured storage root."
        ),
    )
    parser.add_argument(
        "--replay-limit",
        type=int,
        default=25,
        help="Maximum number of replay cases per replay source.",
    )
    parser.add_argument(
        "--retrieval-learning-limit",
        type=int,
        default=50,
        help="Maximum number of rows per retrieval-learning source family.",
    )
    parser.add_argument(
        "--harness-name",
        default="default_v1",
        help="Harness name to use for the persisted court-grade evaluation.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = bootstrap_court_grade_readiness_func(
            session,
            storage_service=storage_service_factory(),
            manual_corpus_path=args.manual_corpus_path,
            auto_corpus_path=args.auto_corpus_path,
            operator_feedback_seed_path=args.operator_feedback_seed_path,
            claim_feedback_seed_path=args.claim_feedback_seed_path,
            replay_alert_fixture_seed_path=args.replay_alert_fixture_seed_path,
            output_path=args.output,
            replay_limit=args.replay_limit,
            retrieval_learning_limit=args.retrieval_learning_limit,
            harness_name=args.harness_name,
        )
        session.commit()
    print(json.dumps(payload, indent=None if args.compact else 2))
