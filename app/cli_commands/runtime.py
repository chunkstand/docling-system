from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from app.cli_commands.common import lazy_service_attr
from app.db.models import Document, DocumentRun
from app.db.session import get_session_factory
from app.schemas.search import SearchReplayRunRequest
from app.services.storage import StorageService


def run_eval_run(
    *,
    session_factory_func=get_session_factory,
    resolve_baseline_run_id_func=None,
    evaluate_run_func=None,
) -> None:
    if resolve_baseline_run_id_func is None:
        resolve_baseline_run_id_func = lazy_service_attr(
            "app.services.evaluations",
            "resolve_baseline_run_id",
        )
    if evaluate_run_func is None:
        evaluate_run_func = lazy_service_attr("app.services.evaluations", "evaluate_run")
    parser = argparse.ArgumentParser(
        description="Evaluate one persisted run against the evaluation corpus."
    )
    parser.add_argument("run_id", help="Document run UUID to evaluate.")
    parser.add_argument(
        "--baseline-run-id", help="Optional baseline run UUID for rank-delta comparison."
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        run = session.get(DocumentRun, UUID(args.run_id))
        if run is None:
            raise SystemExit(f"Run not found: {args.run_id}")
        document = session.get(Document, run.document_id)
        if document is None:
            raise SystemExit(f"Document not found for run: {args.run_id}")
        baseline_run_id = resolve_baseline_run_id_func(
            run.id,
            document.active_run_id,
            explicit_baseline_run_id=UUID(args.baseline_run_id) if args.baseline_run_id else None,
        )
        evaluation = evaluate_run_func(session, document, run, baseline_run_id=baseline_run_id)
        print(
            json.dumps(
                {
                    "run_id": str(run.id),
                    "document_id": str(document.id),
                    "source_filename": document.source_filename,
                    "status": evaluation.status,
                    "fixture_name": evaluation.fixture_name,
                    "summary": evaluation.summary_json,
                    "error_message": evaluation.error_message,
                }
            )
        )


def run_eval_corpus(*, run_eval_corpus_summary_func=None) -> None:
    if run_eval_corpus_summary_func is None:
        run_eval_corpus_summary_func = lazy_service_attr(
            "app.services.evaluation_corpus_runner",
            "run_eval_corpus_summary",
        )
    parser = argparse.ArgumentParser(
        description="Evaluate all active documents that match the evaluation corpus."
    )
    parser.parse_args()
    print(json.dumps(run_eval_corpus_summary_func()))


def run_audit(*, session_factory_func=get_session_factory, run_integrity_audit_func=None) -> None:
    if run_integrity_audit_func is None:
        run_integrity_audit_func = lazy_service_attr("app.services.audit", "run_integrity_audit")
    parser = argparse.ArgumentParser(
        description="Audit durable run and promotion invariants across the local corpus."
    )
    parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        summary = run_integrity_audit_func(session)
    print(json.dumps(summary))


def run_backfill_legacy_audit(
    *,
    session_factory_func=get_session_factory,
    backfill_legacy_run_audit_fields_func=None,
) -> None:
    if backfill_legacy_run_audit_fields_func is None:
        backfill_legacy_run_audit_fields_func = lazy_service_attr(
            "app.services.cleanup",
            "backfill_legacy_run_audit_fields",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Backfill legacy run audit fields so historical rows satisfy current invariants."
        )
    )
    parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        summary = backfill_legacy_run_audit_fields_func(session)
    print(json.dumps(summary))


def run_knowledge_base_reset(
    *,
    execute_knowledge_base_reset_func=None,
    options_cls=None,
    reset_error_cls=None,
) -> None:
    if execute_knowledge_base_reset_func is None:
        execute_knowledge_base_reset_func = lazy_service_attr(
            "app.services.knowledge_base_reset",
            "execute_knowledge_base_reset",
        )
    if options_cls is None:
        options_cls = lazy_service_attr(
            "app.services.knowledge_base_reset",
            "KnowledgeBaseResetOptions",
        )
    if reset_error_cls is None:
        reset_error_cls = lazy_service_attr(
            "app.services.knowledge_base_reset",
            "KnowledgeBaseResetError",
        )
    parser = argparse.ArgumentParser(
        description=(
            "Safely reset the local knowledge base by archiving the current DB/storage "
            "and cutting over to an empty migrated workspace."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the reset. Without this flag the command only prints a dry-run manifest.",
    )
    parser.add_argument(
        "--confirm",
        default=None,
        help="Required confirmation phrase for execution: CLEAR_KNOWLEDGE_BASE.",
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=None,
        help="Optional archive directory. Defaults under the storage parent reset-archives/.",
    )
    parser.add_argument(
        "--target-database-name",
        "--new-database-name",
        dest="new_database_name",
        default=None,
        help="Optional name for the new empty local database.",
    )
    parser.add_argument(
        "--allow-running-services",
        action="store_true",
        help="Allow execution while API/worker/agent-worker services appear to be running.",
    )
    parser.add_argument(
        "--allow-active-work",
        "--allow-active-runs",
        dest="allow_active_work",
        action="store_true",
        help="Allow execution while queued/processing document runs or agent tasks exist.",
    )
    parser.add_argument(
        "--allow-non-development",
        action="store_true",
        help="Allow execution outside DOCLING_SYSTEM_ENV=development.",
    )
    args = parser.parse_args()

    options = options_cls(
        execute=args.execute,
        confirm=args.confirm,
        allow_running_services=args.allow_running_services,
        allow_active_work=args.allow_active_work,
        allow_non_development=args.allow_non_development,
        archive_root=args.archive_root,
        new_database_name=args.new_database_name,
        project_root=Path.cwd(),
    )
    try:
        payload = execute_knowledge_base_reset_func(options)
    except reset_error_cls as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(payload, indent=2, default=str))


def run_semantic_backfill_status(
    *,
    session_factory_func=get_session_factory,
    get_semantic_backfill_status_func=None,
) -> None:
    if get_semantic_backfill_status_func is None:
        get_semantic_backfill_status_func = lazy_service_attr(
            "app.services.semantic_backfill",
            "get_semantic_backfill_status",
        )
    parser = argparse.ArgumentParser(
        description="Inspect semantic backfill readiness for the active corpus."
    )
    parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = get_semantic_backfill_status_func(session)
    print(json.dumps(payload.model_dump(mode="json"), default=str))


def run_semantic_backfill(
    *,
    session_factory_func=get_session_factory,
    execute_semantic_backfill_func=None,
    storage_service_factory=StorageService,
) -> None:
    if execute_semantic_backfill_func is None:
        execute_semantic_backfill_func = lazy_service_attr(
            "app.services.semantic_backfill",
            "run_semantic_backfill",
        )
    from app.schemas.semantic_backfill import SemanticBackfillRequest

    parser = argparse.ArgumentParser(
        description=(
            "Run semantic passes and optional document fact graph construction "
            "over existing active runs without reparsing PDFs."
        )
    )
    parser.add_argument(
        "--document-id",
        action="append",
        dest="document_ids",
        default=[],
        help="Restrict backfill to a document UUID. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum active documents to scan.")
    parser.add_argument("--force", action="store_true", help="Refresh current semantic passes.")
    parser.add_argument("--dry-run", action="store_true", help="Plan the backfill without writes.")
    parser.add_argument(
        "--skip-ontology-init",
        action="store_true",
        help="Do not initialize the workspace ontology before backfill.",
    )
    parser.add_argument(
        "--skip-fact-graphs",
        action="store_true",
        help="Do not build document fact graphs after semantic passes.",
    )
    parser.add_argument(
        "--minimum-review-status",
        choices=["candidate", "approved"],
        default="candidate",
        help="Minimum semantic assertion review status for fact graph construction.",
    )
    args = parser.parse_args()

    request = SemanticBackfillRequest(
        document_ids=args.document_ids,
        limit=args.limit,
        force=args.force,
        dry_run=args.dry_run,
        initialize_ontology=not args.skip_ontology_init,
        build_fact_graphs=not args.skip_fact_graphs,
        minimum_review_status=args.minimum_review_status,
    )

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = execute_semantic_backfill_func(
            session,
            request,
            storage_service=storage_service_factory(),
        )
    print(json.dumps(payload.model_dump(mode="json"), default=str))


def run_replay_search(
    *,
    session_factory_func=get_session_factory,
    replay_search_request_func=None,
) -> None:
    if replay_search_request_func is None:
        replay_search_request_func = lazy_service_attr(
            "app.services.search_history",
            "replay_search_request",
        )
    parser = argparse.ArgumentParser(
        description="Replay one persisted search request against the current search stack."
    )
    parser.add_argument("search_request_id", help="Persisted search request UUID to replay.")
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = replay_search_request_func(session, UUID(args.search_request_id))
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


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


def run_replay_suite(
    *,
    session_factory_func=get_session_factory,
    run_search_replay_suite_func=None,
) -> None:
    if run_search_replay_suite_func is None:
        run_search_replay_suite_func = lazy_service_attr(
            "app.services.search_replays",
            "run_search_replay_suite",
        )
    parser = argparse.ArgumentParser(
        description="Run a persisted replay suite over evaluation queries, live gaps, or feedback."
    )
    parser.add_argument(
        "source_type",
        choices=[
            "evaluation_queries",
            "live_search_gaps",
            "feedback",
            "cross_document_prose_regressions",
            "technical_report_claim_feedback",
        ],
        help="Replay source to execute.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    parser.add_argument(
        "--harness-name",
        default=None,
        help="Optional search harness name for replay execution.",
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = run_search_replay_suite_func(
            session,
            SearchReplayRunRequest(
                source_type=args.source_type,
                limit=args.limit,
                harness_name=args.harness_name,
            ),
        )
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def run_export_ranking_dataset(
    *,
    session_factory_func=get_session_factory,
    export_ranking_dataset_func=None,
) -> None:
    if export_ranking_dataset_func is None:
        export_ranking_dataset_func = lazy_service_attr(
            "app.services.search_replays",
            "export_ranking_dataset",
        )
    parser = argparse.ArgumentParser(
        description="Export labeled ranking data from search feedback and replay deltas."
    )
    parser.add_argument("--limit", type=int, default=200, help="Maximum rows per source set.")
    args = parser.parse_args()

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = export_ranking_dataset_func(session, limit=args.limit)
    print(json.dumps(payload))
