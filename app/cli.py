from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from app.db.models import Document, DocumentRun
from app.db.session import get_session_factory
from app.schemas.agent_tasks import VerifySearchHarnessEvaluationTaskInput
from app.schemas.search import (
    AuditBundleValidationReceiptRequest,
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
    RetrievalTrainingRunAuditBundleRequest,
    SearchHarnessEvaluationRequest,
    SearchHarnessOptimizationRequest,
    SearchHarnessReleaseAuditBundleRequest,
    SearchReplayRunRequest,
)
from app.services.improvement_cases import (
    IMPROVEMENT_ARTIFACT_TYPES,
    IMPROVEMENT_CASE_STATUSES,
    IMPROVEMENT_CAUSE_CLASSES,
    IMPROVEMENT_SOURCE_TYPES,
)
from app.services.storage import StorageService


def _lazy_service_attr(module_path: str, name: str):
    module = __import__(module_path, fromlist=[name])
    return getattr(module, name)


def ingest_local_file(*args, **kwargs):
    return _lazy_service_attr("app.services.documents", "ingest_local_file")(*args, **kwargs)


def queue_local_ingest_directory(*args, **kwargs):
    return _lazy_service_attr("app.services.ingest_batches", "queue_local_ingest_directory")(
        *args,
        **kwargs,
    )


def list_ingest_batches(*args, **kwargs):
    return _lazy_service_attr("app.services.ingest_batches", "list_ingest_batches")(
        *args,
        **kwargs,
    )


def get_ingest_batch_detail(*args, **kwargs):
    return _lazy_service_attr("app.services.ingest_batches", "get_ingest_batch_detail")(
        *args,
        **kwargs,
    )


def evaluate_run(*args, **kwargs):
    return _lazy_service_attr("app.services.evaluations", "evaluate_run")(*args, **kwargs)


def resolve_baseline_run_id(*args, **kwargs):
    return _lazy_service_attr("app.services.evaluations", "resolve_baseline_run_id")(
        *args,
        **kwargs,
    )


def run_integrity_audit(*args, **kwargs):
    return _lazy_service_attr("app.services.audit", "run_integrity_audit")(*args, **kwargs)


def backfill_legacy_run_audit_fields(*args, **kwargs):
    return _lazy_service_attr("app.services.cleanup", "backfill_legacy_run_audit_fields")(
        *args,
        **kwargs,
    )


def get_semantic_backfill_status(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.semantic_backfill",
        "get_semantic_backfill_status",
    )(*args, **kwargs)


def execute_semantic_backfill(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.semantic_backfill",
        "run_semantic_backfill",
    )(*args, **kwargs)


def replay_search_request(*args, **kwargs):
    return _lazy_service_attr("app.services.search_history", "replay_search_request")(
        *args,
        **kwargs,
    )


def list_quality_eval_candidates(*args, **kwargs):
    return _lazy_service_attr("app.services.quality", "list_quality_eval_candidates")(
        *args,
        **kwargs,
    )


def build_evaluation_data_readiness_report(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.evaluation_data_readiness",
        "build_evaluation_data_readiness_report",
    )(*args, **kwargs)


def run_search_replay_suite(*args, **kwargs):
    return _lazy_service_attr("app.services.search_replays", "run_search_replay_suite")(
        *args,
        **kwargs,
    )


def export_ranking_dataset(*args, **kwargs):
    return _lazy_service_attr("app.services.search_replays", "export_ranking_dataset")(
        *args,
        **kwargs,
    )


def materialize_retrieval_learning_dataset(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.retrieval_learning",
        "materialize_retrieval_learning_dataset",
    )(*args, **kwargs)


def evaluate_retrieval_learning_candidate(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.retrieval_learning",
        "evaluate_retrieval_learning_candidate",
    )(*args, **kwargs)


def create_retrieval_reranker_artifact(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.retrieval_learning",
        "create_retrieval_reranker_artifact",
    )(*args, **kwargs)


def evaluate_search_harness(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.search_harness_evaluations",
        "evaluate_search_harness",
    )(*args, **kwargs)


def list_search_harness_evaluations(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.search_harness_evaluations",
        "list_search_harness_evaluations",
    )(*args, **kwargs)


def get_search_harness_evaluation_detail(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.search_harness_evaluations",
        "get_search_harness_evaluation_detail",
    )(*args, **kwargs)


def evaluate_search_harness_release_gate(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.search_release_gate",
        "evaluate_search_harness_release_gate",
    )(*args, **kwargs)


def record_search_harness_release_gate(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.search_release_gate",
        "record_search_harness_release_gate",
    )(*args, **kwargs)


def create_search_harness_release_audit_bundle(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.audit_bundles",
        "create_search_harness_release_audit_bundle",
    )(*args, **kwargs)


def create_retrieval_training_run_audit_bundle(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.audit_bundles",
        "create_retrieval_training_run_audit_bundle",
    )(*args, **kwargs)


def create_audit_bundle_validation_receipt(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.audit_bundles",
        "create_audit_bundle_validation_receipt",
    )(*args, **kwargs)


def evaluate_search_harness_verification(*args, **kwargs):
    return evaluate_search_harness_release_gate(*args, **kwargs)


def run_search_harness_optimization_loop(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.search_harness_optimization",
        "run_search_harness_optimization_loop",
    )(*args, **kwargs)


def load_improvement_case_registry(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_cases",
        "load_improvement_case_registry",
    )(*args, **kwargs)


def load_improvement_case_registry_for_validation(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_cases",
        "load_improvement_case_registry_for_validation",
    )(*args, **kwargs)


def validate_improvement_case_registry(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_cases",
        "validate_improvement_case_registry",
    )(*args, **kwargs)


def build_improvement_case_manifest(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_cases",
        "build_improvement_case_manifest",
    )(*args, **kwargs)


def filter_improvement_cases(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_cases",
        "filter_improvement_cases",
    )(*args, **kwargs)


def summarize_improvement_cases(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_cases",
        "summarize_improvement_cases",
    )(*args, **kwargs)


def record_improvement_case(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_cases",
        "record_improvement_case",
    )(*args, **kwargs)


def execute_knowledge_base_reset(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.knowledge_base_reset",
        "execute_knowledge_base_reset",
    )(*args, **kwargs)


def run_ingest_file() -> None:
    parser = argparse.ArgumentParser(description="Queue one or more local PDFs for ingestion.")
    parser.add_argument("pdf_paths", nargs="+", help="One or more PDF file paths.")
    args = parser.parse_args()

    storage_service = StorageService()
    session_factory = get_session_factory()

    with session_factory() as session:
        for raw_path in args.pdf_paths:
            payload, status_code = ingest_local_file(
                session, Path(raw_path).expanduser().resolve(), storage_service
            )
            print(
                json.dumps(
                    {
                        "source_path": str(Path(raw_path).expanduser().resolve()),
                        "status_code": status_code,
                        "document_id": str(payload.document_id),
                        "run_id": str(payload.run_id) if payload.run_id else None,
                        "status": payload.status,
                        "duplicate": payload.duplicate,
                        "recovery_run": payload.recovery_run,
                        "active_run_id": str(payload.active_run_id)
                        if payload.active_run_id
                        else None,
                        "active_run_status": payload.active_run_status,
                    }
                )
            )


def run_ingest_dir() -> None:
    parser = argparse.ArgumentParser(
        description="Queue all PDF files under one local directory for ingestion."
    )
    parser.add_argument("directory_path", help="Directory containing PDF files.")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into nested directories while collecting PDFs.",
    )
    args = parser.parse_args()

    storage_service = StorageService()
    session_factory = get_session_factory()

    with session_factory() as session:
        payload = queue_local_ingest_directory(
            session,
            Path(args.directory_path).expanduser().resolve(),
            storage_service,
            recursive=args.recursive,
        )
        print(json.dumps(payload.model_dump(mode="json", exclude={"items"})))


def run_ingest_batch_list() -> None:
    parser = argparse.ArgumentParser(description="List recent local ingest batches.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of batches.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_ingest_batches(session, limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_ingest_batch_show() -> None:
    parser = argparse.ArgumentParser(description="Show one local ingest batch and its items.")
    parser.add_argument("batch_id", help="Ingest batch UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_ingest_batch_detail(session, UUID(args.batch_id))
    print(json.dumps(payload.model_dump(mode="json")))


def run_eval_run() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate one persisted run against the evaluation corpus."
    )
    parser.add_argument("run_id", help="Document run UUID to evaluate.")
    parser.add_argument(
        "--baseline-run-id", help="Optional baseline run UUID for rank-delta comparison."
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        run = session.get(DocumentRun, UUID(args.run_id))
        if run is None:
            raise SystemExit(f"Run not found: {args.run_id}")
        document = session.get(Document, run.document_id)
        if document is None:
            raise SystemExit(f"Document not found for run: {args.run_id}")
        baseline_run_id = resolve_baseline_run_id(
            run.id,
            document.active_run_id,
            explicit_baseline_run_id=UUID(args.baseline_run_id) if args.baseline_run_id else None,
        )
        evaluation = evaluate_run(session, document, run, baseline_run_id=baseline_run_id)
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


def run_eval_corpus() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate all active documents that match the evaluation corpus."
    )
    parser.parse_args()
    summaries = _lazy_service_attr(
        "app.services.evaluation_corpus_runner",
        "run_eval_corpus_summary",
    )()
    print(json.dumps(summaries))


def run_audit() -> None:
    parser = argparse.ArgumentParser(
        description="Audit durable run and promotion invariants across the local corpus."
    )
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        summary = run_integrity_audit(session)
    print(json.dumps(summary))


def run_backfill_legacy_audit() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill legacy run audit fields so historical rows satisfy current invariants."
        )
    )
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        summary = backfill_legacy_run_audit_fields(session)
    print(json.dumps(summary))


def run_knowledge_base_reset() -> None:
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

    options_cls = _lazy_service_attr(
        "app.services.knowledge_base_reset",
        "KnowledgeBaseResetOptions",
    )
    reset_error_cls = _lazy_service_attr(
        "app.services.knowledge_base_reset",
        "KnowledgeBaseResetError",
    )
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
        payload = execute_knowledge_base_reset(options)
    except reset_error_cls as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(payload, indent=2, default=str))


def run_semantic_backfill_status() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect semantic backfill readiness for the active corpus."
    )
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_semantic_backfill_status(session)
    print(json.dumps(payload.model_dump(mode="json"), default=str))


def run_semantic_backfill() -> None:
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

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = execute_semantic_backfill(
            session,
            request,
            storage_service=StorageService(),
        )
    print(json.dumps(payload.model_dump(mode="json"), default=str))


def run_replay_search() -> None:
    parser = argparse.ArgumentParser(
        description="Replay one persisted search request against the current search stack."
    )
    parser.add_argument("search_request_id", help="Persisted search request UUID to replay.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = replay_search_request(session, UUID(args.search_request_id))
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def run_eval_candidates() -> None:
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

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_quality_eval_candidates(
            session,
            limit=args.limit,
            include_resolved=args.include_resolved,
        )
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_evaluation_data_readiness() -> None:
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

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = build_evaluation_data_readiness_report(
            session,
            manual_corpus_path=args.manual_corpus_path,
            auto_corpus_path=args.auto_corpus_path,
        )
    rendered = json.dumps(payload, indent=None if args.compact else 2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    print(rendered)


def run_replay_suite() -> None:
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

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = run_search_replay_suite(
            session,
            SearchReplayRunRequest(
                source_type=args.source_type,
                limit=args.limit,
                harness_name=args.harness_name,
            ),
        )
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def run_export_ranking_dataset() -> None:
    parser = argparse.ArgumentParser(
        description="Export labeled ranking data from search feedback and replay deltas."
    )
    parser.add_argument("--limit", type=int, default=200, help="Maximum rows per source set.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = export_ranking_dataset(session, limit=args.limit)
    print(json.dumps(payload))


def run_materialize_retrieval_learning_dataset() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize durable retrieval judgments and hard negatives for reranker work."
    )
    parser.add_argument("--limit", type=int, default=200, help="Maximum rows per source set.")
    parser.add_argument(
        "--source-type",
        action="append",
        choices=[
            "feedback",
            "replay",
            "claim_support_replay_alert_corpus",
            "technical_report_claim_feedback",
        ],
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

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = materialize_retrieval_learning_dataset(
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


def run_evaluate_retrieval_learning_candidate() -> None:
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
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        choices=[
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
            "technical_report_claim_feedback",
        ],
        help="Replay source type to include. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    parser.add_argument(
        "--max-total-regressed-count",
        type=int,
        default=0,
        help="Maximum allowed regressed query count across any source.",
    )
    parser.add_argument(
        "--max-mrr-drop",
        type=float,
        default=0.0,
        help="Maximum allowed per-source MRR drop.",
    )
    parser.add_argument(
        "--max-zero-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in zero-result queries.",
    )
    parser.add_argument(
        "--max-foreign-top-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in foreign top results.",
    )
    parser.add_argument(
        "--min-total-shared-query-count",
        type=int,
        default=1,
        help="Minimum number of shared replay queries required for a valid gate.",
    )
    parser.add_argument("--requested-by", default="cli", help="Release gate requester.")
    parser.add_argument("--review-note", default=None, help="Optional review note.")
    args = parser.parse_args()

    request = RetrievalLearningCandidateEvaluationRequest(
        retrieval_training_run_id=args.retrieval_training_run_id,
        candidate_harness_name=args.candidate_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        source_types=args.source_types
        or [
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ],
        limit=args.limit,
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
        requested_by=args.requested_by,
        review_note=args.review_note,
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        payload = evaluate_retrieval_learning_candidate(session, request)
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))
    if payload.gate_outcome != "passed":
        raise SystemExit(1)


def run_create_retrieval_reranker_artifact() -> None:
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
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        choices=[
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
            "technical_report_claim_feedback",
        ],
        help="Replay source type to include. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    parser.add_argument(
        "--max-total-regressed-count",
        type=int,
        default=0,
        help="Maximum allowed regressed query count across any source.",
    )
    parser.add_argument(
        "--max-mrr-drop",
        type=float,
        default=0.0,
        help="Maximum allowed per-source MRR drop.",
    )
    parser.add_argument(
        "--max-zero-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in zero-result queries.",
    )
    parser.add_argument(
        "--max-foreign-top-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in foreign top results.",
    )
    parser.add_argument(
        "--min-total-shared-query-count",
        type=int,
        default=1,
        help="Minimum number of shared replay queries required for a valid gate.",
    )
    parser.add_argument("--requested-by", default="cli", help="Release gate requester.")
    parser.add_argument("--review-note", default=None, help="Optional review note.")
    args = parser.parse_args()

    request = RetrievalRerankerArtifactRequest(
        retrieval_training_run_id=args.retrieval_training_run_id,
        artifact_name=args.artifact_name,
        candidate_harness_name=args.candidate_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        base_harness_name=args.base_harness_name,
        source_types=args.source_types
        or [
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ],
        limit=args.limit,
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
        requested_by=args.requested_by,
        review_note=args.review_note,
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        payload = create_retrieval_reranker_artifact(session, request)
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))
    if payload.gate_outcome != "passed":
        raise SystemExit(1)


def run_eval_reranker() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a candidate search harness against replay and corpus query sets."
    )
    parser.add_argument("candidate_harness_name", help="Candidate search harness name.")
    parser.add_argument(
        "--baseline-harness-name",
        default="default_v1",
        help="Baseline harness name to compare against.",
    )
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        choices=[
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
            "technical_report_claim_feedback",
        ],
        help="Replay source type to include. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = evaluate_search_harness(
            session,
            SearchHarnessEvaluationRequest(
                candidate_harness_name=args.candidate_harness_name,
                baseline_harness_name=args.baseline_harness_name,
                source_types=args.source_types
                or [
                    "evaluation_queries",
                    "feedback",
                    "live_search_gaps",
                    "cross_document_prose_regressions",
                ],
                limit=args.limit,
            ),
        )
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def run_search_harness_evaluation_list() -> None:
    parser = argparse.ArgumentParser(description="List persisted search harness evaluations.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum evaluations to return.")
    parser.add_argument(
        "--candidate-harness-name",
        help="Optional candidate harness name filter.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_search_harness_evaluations(
            session,
            limit=args.limit,
            candidate_harness_name=args.candidate_harness_name,
        )
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_search_harness_evaluation_show() -> None:
    parser = argparse.ArgumentParser(
        description="Show one persisted search harness evaluation with source replay provenance."
    )
    parser.add_argument("evaluation_id", type=UUID, help="Search harness evaluation UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_search_harness_evaluation_detail(session, args.evaluation_id)
    print(json.dumps(payload.model_dump(mode="json")))


def run_gate_search_harness_release() -> None:
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
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        choices=[
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
            "technical_report_claim_feedback",
        ],
        help="Replay source type to include. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    parser.add_argument(
        "--max-total-regressed-count",
        type=int,
        default=0,
        help="Maximum allowed regressed query count across any source.",
    )
    parser.add_argument(
        "--max-mrr-drop",
        type=float,
        default=0.0,
        help="Maximum allowed per-source MRR drop.",
    )
    parser.add_argument(
        "--max-zero-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in zero-result queries.",
    )
    parser.add_argument(
        "--max-foreign-top-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in foreign top results.",
    )
    parser.add_argument(
        "--min-total-shared-query-count",
        type=int,
        default=1,
        help="Minimum number of shared replay queries required for a valid gate.",
    )
    parser.add_argument("--requested-by", default=None, help="Optional release gate requester.")
    parser.add_argument("--review-note", default=None, help="Optional release gate review note.")
    args = parser.parse_args()

    request = SearchHarnessEvaluationRequest(
        candidate_harness_name=args.candidate_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        source_types=args.source_types
        or [
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ],
        limit=args.limit,
    )
    gate_request = VerifySearchHarnessEvaluationTaskInput(
        target_task_id=UUID(int=0),
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
    )

    session_factory = get_session_factory()
    with session_factory() as session:
        evaluation = evaluate_search_harness(session, request)
        release = record_search_harness_release_gate(
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


def run_search_harness_release_audit_bundle() -> None:
    parser = argparse.ArgumentParser(
        description="Export a signed immutable audit bundle for one search harness release gate."
    )
    parser.add_argument("release_id", help="Search harness release UUID.")
    parser.add_argument("--created-by", default=None, help="Optional bundle creator identifier.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    storage_service = StorageService()
    with session_factory() as session:
        bundle = create_search_harness_release_audit_bundle(
            session,
            UUID(args.release_id),
            SearchHarnessReleaseAuditBundleRequest(created_by=args.created_by),
            storage_service=storage_service,
        )
        session.commit()
    print(json.dumps(bundle.model_dump(mode="json")))


def run_retrieval_training_run_audit_bundle() -> None:
    parser = argparse.ArgumentParser(
        description="Export a signed immutable audit bundle for one retrieval training run."
    )
    parser.add_argument("training_run_id", help="Retrieval training run UUID.")
    parser.add_argument("--created-by", default=None, help="Optional bundle creator identifier.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    storage_service = StorageService()
    with session_factory() as session:
        bundle = create_retrieval_training_run_audit_bundle(
            session,
            UUID(args.training_run_id),
            RetrievalTrainingRunAuditBundleRequest(created_by=args.created_by),
            storage_service=storage_service,
        )
        session.commit()
    print(json.dumps(bundle.model_dump(mode="json")))


def run_audit_bundle_validation_receipt() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a signed audit bundle and export a signed receipt."
    )
    parser.add_argument("bundle_id", help="Audit bundle export UUID.")
    parser.add_argument(
        "--created-by",
        default=None,
        help="Optional receipt creator identifier.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    storage_service = StorageService()
    with session_factory() as session:
        receipt = create_audit_bundle_validation_receipt(
            session,
            UUID(args.bundle_id),
            AuditBundleValidationReceiptRequest(created_by=args.created_by),
            storage_service=storage_service,
        )
        session.commit()
    print(json.dumps(receipt.model_dump(mode="json")))


def run_optimize_search_harness() -> None:
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
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        choices=[
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
            "technical_report_claim_feedback",
        ],
        help="Replay source type to include. Can be passed multiple times.",
    )
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
    parser.add_argument(
        "--max-total-regressed-count",
        type=int,
        default=0,
        help="Maximum allowed regressed query count across any source.",
    )
    parser.add_argument(
        "--max-mrr-drop",
        type=float,
        default=0.0,
        help="Maximum allowed per-source MRR drop.",
    )
    parser.add_argument(
        "--max-zero-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in zero-result queries.",
    )
    parser.add_argument(
        "--max-foreign-top-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in foreign top results.",
    )
    parser.add_argument(
        "--min-total-shared-query-count",
        type=int,
        default=1,
        help="Minimum number of shared replay queries required for a valid gate.",
    )
    args = parser.parse_args()

    candidate_harness_name = args.candidate_harness_name or f"{args.base_harness_name}_loop"
    request = SearchHarnessOptimizationRequest(
        base_harness_name=args.base_harness_name,
        baseline_harness_name=args.baseline_harness_name,
        candidate_harness_name=candidate_harness_name,
        source_types=args.source_types
        or [
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ],
        limit=args.limit,
        iterations=args.iterations,
        tune_fields=args.tune_fields or [],
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
    )

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = run_search_harness_optimization_loop(session, request)
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def _improvement_case_issue_payload(issue) -> dict:
    return {
        "case_id": issue.case_id,
        "field": issue.field,
        "message": issue.message,
    }


def _add_improvement_case_path_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--path",
        default=None,
        help="Path to improvement case registry. Defaults to config/improvement_cases.yaml.",
    )


def run_improvement_case_validate() -> None:
    parser = argparse.ArgumentParser(description="Validate the improvement case registry.")
    _add_improvement_case_path_arg(parser)
    args = parser.parse_args()

    registry, load_issues = load_improvement_case_registry_for_validation(args.path)
    issues = [*load_issues]
    if not load_issues:
        issues.extend(validate_improvement_case_registry(registry))
    payload = {
        "schema_name": "improvement_case_validation",
        "schema_version": "1.0",
        "valid": not issues,
        "issue_count": len(issues),
        "issues": [_improvement_case_issue_payload(issue) for issue in issues],
    }
    print(json.dumps(payload))
    if issues:
        raise SystemExit(1)


def run_improvement_case_list() -> None:
    parser = argparse.ArgumentParser(description="List improvement cases.")
    _add_improvement_case_path_arg(parser)
    parser.add_argument("--status", choices=sorted(IMPROVEMENT_CASE_STATUSES))
    parser.add_argument("--cause-class", choices=sorted(IMPROVEMENT_CAUSE_CLASSES))
    parser.add_argument("--artifact-type", choices=sorted(IMPROVEMENT_ARTIFACT_TYPES))
    parser.add_argument("--workflow-version")
    args = parser.parse_args()

    registry = load_improvement_case_registry(args.path)
    filtered = filter_improvement_cases(
        registry,
        status=args.status,
        cause_class=args.cause_class,
        artifact_type=args.artifact_type,
        workflow_version=args.workflow_version,
    )
    print(json.dumps(build_improvement_case_manifest(filtered)))


def run_improvement_case_summary() -> None:
    parser = argparse.ArgumentParser(description="Summarize improvement cases.")
    _add_improvement_case_path_arg(parser)
    args = parser.parse_args()

    registry = load_improvement_case_registry(args.path)
    print(json.dumps(summarize_improvement_cases(registry)))


def run_improvement_case_record() -> None:
    parser = argparse.ArgumentParser(description="Record one improvement case.")
    _add_improvement_case_path_arg(parser)
    parser.add_argument("--case-id")
    parser.add_argument("--title", required=True)
    parser.add_argument("--observed-failure", required=True)
    parser.add_argument("--cause-class", choices=sorted(IMPROVEMENT_CAUSE_CLASSES), required=True)
    parser.add_argument(
        "--artifact-type",
        choices=sorted(IMPROVEMENT_ARTIFACT_TYPES),
    )
    parser.add_argument("--artifact-path")
    parser.add_argument("--artifact-description")
    parser.add_argument(
        "--verification-command",
        action="append",
        default=[],
        dest="verification_commands",
    )
    parser.add_argument(
        "--acceptance-condition",
        action="append",
        default=[],
        dest="acceptance_conditions",
    )
    parser.add_argument(
        "--source-type",
        choices=sorted(IMPROVEMENT_SOURCE_TYPES),
        default="operator_note",
    )
    parser.add_argument("--source-ref")
    parser.add_argument("--status", choices=sorted(IMPROVEMENT_CASE_STATUSES), default="converted")
    parser.add_argument("--workflow-version", default="improvement_v1")
    parser.add_argument("--deployed-ref")
    parser.add_argument("--metric-name")
    parser.add_argument("--metric-value", type=float)
    parser.add_argument("--measurement-window")
    args = parser.parse_args()

    try:
        case = record_improvement_case(
            path=args.path,
            case_id=args.case_id,
            title=args.title,
            observed_failure=args.observed_failure,
            cause_class=args.cause_class,
            artifact_type=args.artifact_type,
            artifact_target_path=args.artifact_path,
            artifact_description=args.artifact_description,
            verification_commands=args.verification_commands,
            acceptance_conditions=args.acceptance_conditions,
            source_type=args.source_type,
            source_ref=args.source_ref,
            status=args.status,
            workflow_version=args.workflow_version,
            deployed_ref=args.deployed_ref,
            metric_name=args.metric_name,
            metric_value=args.metric_value,
            measurement_window=args.measurement_window,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(case.model_dump(mode="json")))
