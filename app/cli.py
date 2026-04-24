from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

import yaml

from app.db.models import AgentTask, Document, DocumentRun
from app.db.session import get_session_factory
from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskOutcomeCreateRequest,
    AgentTaskRejectionRequest,
    VerifySearchHarnessEvaluationTaskInput,
)
from app.schemas.search import (
    SearchHarnessEvaluationRequest,
    SearchHarnessOptimizationRequest,
    SearchReplayRunRequest,
)
from app.services.improvement_cases import (
    IMPROVEMENT_ARTIFACT_TYPES,
    IMPROVEMENT_CASE_STATUSES,
    IMPROVEMENT_CAUSE_CLASSES,
    IMPROVEMENT_SOURCE_TYPES,
)
from app.services.storage import StorageService


def _parse_json_arg(raw_json: str) -> dict:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("JSON payload must be an object.")
    return payload


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


def evaluate_search_harness_verification(*args, **kwargs):
    return evaluate_search_harness_release_gate(*args, **kwargs)


def run_search_harness_optimization_loop(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.search_harness_optimization",
        "run_search_harness_optimization_loop",
    )(*args, **kwargs)


def list_agent_task_action_definitions(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_tasks",
        "list_agent_task_action_definitions",
    )(*args, **kwargs)


def create_agent_task(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "create_agent_task")(*args, **kwargs)


def list_agent_tasks(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "list_agent_tasks")(*args, **kwargs)


def get_agent_task_detail(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_task_detail")(
        *args,
        **kwargs,
    )


def get_agent_task_context(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_task_context", "get_agent_task_context")(
        *args,
        **kwargs,
    )


def list_agent_task_outcomes(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "list_agent_task_outcomes")(
        *args,
        **kwargs,
    )


def create_agent_task_outcome(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "create_agent_task_outcome")(
        *args,
        **kwargs,
    )


def list_agent_task_artifacts(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_task_artifacts", "list_agent_task_artifacts")(
        *args,
        **kwargs,
    )


def get_agent_task_artifact(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_task_artifacts", "get_agent_task_artifact")(
        *args,
        **kwargs,
    )


def get_agent_task_verifications(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_task_verifications",
        "get_agent_task_verifications",
    )(*args, **kwargs)


def approve_agent_task(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "approve_agent_task")(*args, **kwargs)


def reject_agent_task(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "reject_agent_task")(*args, **kwargs)


def get_agent_task_analytics_summary(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_tasks",
        "get_agent_task_analytics_summary",
    )(*args, **kwargs)


def list_agent_task_workflow_summaries(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_tasks",
        "list_agent_task_workflow_summaries",
    )(*args, **kwargs)


def export_agent_task_traces(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "export_agent_task_traces")(
        *args,
        **kwargs,
    )


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


def run_improvement_case_import_workflow(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.improvement_case_intake",
        "run_improvement_case_import",
    )(*args, **kwargs)


def get_agent_task_trends(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_task_trends")(
        *args,
        **kwargs,
    )


def get_agent_task_recommendation_summary(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_tasks",
        "get_agent_task_recommendation_summary",
    )(*args, **kwargs)


def get_agent_task_recommendation_trends(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_tasks",
        "get_agent_task_recommendation_trends",
    )(*args, **kwargs)


def get_agent_task_cost_summary(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_task_cost_summary")(
        *args,
        **kwargs,
    )


def get_agent_task_cost_trends(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_task_cost_trends")(
        *args,
        **kwargs,
    )


def get_agent_verification_trends(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_verification_trends")(
        *args,
        **kwargs,
    )


def get_agent_approval_trends(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_approval_trends")(
        *args,
        **kwargs,
    )


def get_agent_task_performance_summary(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_tasks",
        "get_agent_task_performance_summary",
    )(*args, **kwargs)


def get_agent_task_performance_trends(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.agent_tasks",
        "get_agent_task_performance_trends",
    )(*args, **kwargs)


def get_agent_task_value_density(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_task_value_density")(
        *args,
        **kwargs,
    )


def get_agent_task_decision_signals(*args, **kwargs):
    return _lazy_service_attr("app.services.agent_tasks", "get_agent_task_decision_signals")(
        *args,
        **kwargs,
    )


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

    session_factory = get_session_factory()
    summaries: list[dict] = []
    with session_factory() as session:
        documents = session.query(Document).order_by(Document.updated_at.desc()).all()
        for document in documents:
            if document.active_run_id is None:
                continue
            run = session.get(DocumentRun, document.active_run_id)
            if run is None:
                continue
            evaluation = evaluate_run(session, document, run)
            summaries.append(
                {
                    "run_id": str(run.id),
                    "document_id": str(document.id),
                    "source_filename": document.source_filename,
                    "status": evaluation.status,
                    "fixture_name": evaluation.fixture_name,
                    "summary": evaluation.summary_json,
                }
            )
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
        gate = evaluate_search_harness_verification(session, evaluation, gate_request)
        session.commit()

    print(
        json.dumps(
            {
                "candidate_harness_name": request.candidate_harness_name,
                "baseline_harness_name": request.baseline_harness_name,
                "evaluation": evaluation.model_dump(mode="json"),
                "gate": {
                    "outcome": gate.outcome,
                    "metrics": gate.metrics,
                    "reasons": gate.reasons,
                    "details": gate.details,
                },
            }
        )
    )
    if gate.outcome != "passed":
        raise SystemExit(1)


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


def run_agent_task_actions() -> None:
    parser = argparse.ArgumentParser(description="List supported agent task action definitions.")
    parser.parse_args()

    payload = list_agent_task_action_definitions()
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_create() -> None:
    parser = argparse.ArgumentParser(description="Create one agent task.")
    parser.add_argument("task_type", help="Registered agent task type.")
    parser.add_argument(
        "--input-json",
        default="{}",
        help="JSON object payload for the registered task input.",
    )
    parser.add_argument("--priority", type=int, default=100, help="Task priority.")
    parser.add_argument(
        "--workflow-version",
        default="v1",
        help="Workflow version label to persist with the task.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type=args.task_type,
                input=_parse_json_arg(args.input_json),
                priority=args.priority,
                workflow_version=args.workflow_version,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_list() -> None:
    parser = argparse.ArgumentParser(description="List agent tasks.")
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Optional task status filter. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of tasks to return.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_tasks(session, statuses=args.statuses, limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_show() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task in detail.")
    parser.add_argument("task_id", help="Agent task UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_detail(session, UUID(args.task_id))
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_context() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task context artifact.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--format", choices=["json", "yaml"], default="json")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_context(session, UUID(args.task_id))
    payload_json = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    if args.format == "yaml":
        print(yaml.safe_dump(payload_json, sort_keys=False, allow_unicode=True))
        return
    print(json.dumps(payload_json))


def run_agent_task_outcomes() -> None:
    parser = argparse.ArgumentParser(description="List outcome labels for one agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum outcome rows to return.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_task_outcomes(session, UUID(args.task_id), limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_label() -> None:
    parser = argparse.ArgumentParser(description="Record one outcome label for a terminal task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument(
        "--outcome-label",
        required=True,
        choices=["useful", "not_useful", "correct", "incorrect"],
        help="Outcome label to record.",
    )
    parser.add_argument("--created-by", required=True, help="Operator identifier.")
    parser.add_argument("--note", default=None, help="Optional note.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = create_agent_task_outcome(
            session,
            UUID(args.task_id),
            AgentTaskOutcomeCreateRequest(
                outcome_label=args.outcome_label,
                created_by=args.created_by,
                note=args.note,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_artifacts() -> None:
    parser = argparse.ArgumentParser(description="List artifact records for one agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum artifact rows to return.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_task_artifacts(session, UUID(args.task_id), limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_artifact() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task artifact payload.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("artifact_id", help="Artifact UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        artifact = get_agent_task_artifact(session, UUID(args.task_id), UUID(args.artifact_id))
    if artifact.storage_path and Path(artifact.storage_path).exists():
        print(Path(artifact.storage_path).read_text())
        return
    print(json.dumps(artifact.payload_json or {}))


def run_agent_task_verifications() -> None:
    parser = argparse.ArgumentParser(description="List verifier records for one agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum verification rows to return.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_verifications(session, UUID(args.task_id), limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_failure_artifact() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task failure artifact payload.")
    parser.add_argument("task_id", help="Agent task UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        task = session.get(AgentTask, UUID(args.task_id))
        if task is None:
            raise SystemExit(f"Agent task not found: {args.task_id}")
        if task.failure_artifact_path is None or not Path(task.failure_artifact_path).exists():
            raise SystemExit(f"Failure artifact not found for agent task: {args.task_id}")
        print(Path(task.failure_artifact_path).read_text())


def run_agent_task_approve() -> None:
    parser = argparse.ArgumentParser(description="Approve one approval-gated agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--approved-by", required=True, help="Approval actor identifier.")
    parser.add_argument("--approval-note", default=None, help="Optional approval note.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = approve_agent_task(
            session,
            UUID(args.task_id),
            AgentTaskApprovalRequest(
                approved_by=args.approved_by,
                approval_note=args.approval_note,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_reject() -> None:
    parser = argparse.ArgumentParser(description="Reject one approval-gated agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--rejected-by", required=True, help="Rejection actor identifier.")
    parser.add_argument("--rejection-note", default=None, help="Optional rejection note.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = reject_agent_task(
            session,
            UUID(args.task_id),
            AgentTaskRejectionRequest(
                rejected_by=args.rejected_by,
                rejection_note=args.rejection_note,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_analytics() -> None:
    parser = argparse.ArgumentParser(description="Show aggregate agent task analytics.")
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_analytics_summary(session)
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_trends() -> None:
    parser = argparse.ArgumentParser(description="Show time-bucketed agent task trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_verification_trends() -> None:
    parser = argparse.ArgumentParser(description="Show time-bucketed verifier trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_verification_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_approval_trends() -> None:
    parser = argparse.ArgumentParser(
        description="Show time-bucketed approval and rejection trends."
    )
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_approval_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_recommendation_summary() -> None:
    parser = argparse.ArgumentParser(description="Show recommendation success summary.")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_recommendation_summary(
            session,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_recommendation_trends() -> None:
    parser = argparse.ArgumentParser(description="Show recommendation success trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_recommendation_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_cost_summary() -> None:
    parser = argparse.ArgumentParser(description="Show agent task cost summary.")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_cost_summary(
            session,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_cost_trends() -> None:
    parser = argparse.ArgumentParser(description="Show agent task cost trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_cost_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_performance_summary() -> None:
    parser = argparse.ArgumentParser(description="Show agent task performance summary.")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_performance_summary(
            session,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_performance_trends() -> None:
    parser = argparse.ArgumentParser(description="Show agent task performance trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_performance_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_value_density() -> None:
    parser = argparse.ArgumentParser(description="Show agent workflow value-density summaries.")
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_value_density(session)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_decision_signals() -> None:
    parser = argparse.ArgumentParser(description="Show workflow decision signals.")
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_decision_signals(session)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_workflow_versions() -> None:
    parser = argparse.ArgumentParser(
        description="Show agent task analytics grouped by workflow version."
    )
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_task_workflow_summaries(session)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_export_traces() -> None:
    parser = argparse.ArgumentParser(description="Export durable agent task traces.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum tasks to export.")
    parser.add_argument(
        "--workflow-version",
        default=None,
        help="Optional workflow version filter.",
    )
    parser.add_argument("--task-type", default=None, help="Optional task type filter.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = export_agent_task_traces(
            session,
            limit=args.limit,
            workflow_version=args.workflow_version,
            task_type=args.task_type,
        )
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


def run_improvement_case_import() -> None:
    parser = argparse.ArgumentParser(
        description="Import observed failures into the improvement case registry."
    )
    _add_improvement_case_path_arg(parser)
    parser.add_argument(
        "--source",
        default="hygiene",
        help=(
            "Import source: all, hygiene, eval-failure-cases, "
            "failed-agent-tasks, or failed-agent-verifications."
        ),
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--workflow-version", default="improvement_v1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        payload = run_improvement_case_import_workflow(
            source=args.source,
            limit=args.limit,
            workflow_version=args.workflow_version,
            path=args.path,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(payload.model_dump(mode="json")))
