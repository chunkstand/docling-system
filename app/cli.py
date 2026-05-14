from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.cli_commands import improvement_cases as improvement_case_commands
from app.cli_commands import ingest as ingest_commands
from app.cli_commands import runtime as runtime_commands
from app.cli_commands.common import lazy_service_attr as _lazy_service_attr
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
)
from app.services.storage import StorageService


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


def run_improvement_case_validate() -> None:
    return improvement_case_commands.run_improvement_case_validate()


def run_improvement_case_list() -> None:
    return improvement_case_commands.run_improvement_case_list()


def run_improvement_case_summary() -> None:
    return improvement_case_commands.run_improvement_case_summary()


def run_improvement_case_record() -> None:
    return improvement_case_commands.run_improvement_case_record()


def execute_knowledge_base_reset(*args, **kwargs):
    return _lazy_service_attr(
        "app.services.knowledge_base_reset",
        "execute_knowledge_base_reset",
    )(*args, **kwargs)


def run_ingest_file() -> None:
    return ingest_commands.run_ingest_file(
        ingest_local_file_func=ingest_local_file,
        session_factory_func=get_session_factory,
        storage_service_factory=StorageService,
    )


def run_ingest_dir() -> None:
    return ingest_commands.run_ingest_dir(
        queue_local_ingest_directory_func=queue_local_ingest_directory,
        session_factory_func=get_session_factory,
        storage_service_factory=StorageService,
    )


def run_ingest_batch_list() -> None:
    return ingest_commands.run_ingest_batch_list(
        list_ingest_batches_func=list_ingest_batches,
        session_factory_func=get_session_factory,
    )


def run_ingest_batch_show() -> None:
    return ingest_commands.run_ingest_batch_show(
        get_ingest_batch_detail_func=get_ingest_batch_detail,
        session_factory_func=get_session_factory,
    )


def run_eval_run() -> None:
    return runtime_commands.run_eval_run()


def run_eval_corpus() -> None:
    return runtime_commands.run_eval_corpus()


def run_audit() -> None:
    return runtime_commands.run_audit()


def run_backfill_legacy_audit() -> None:
    return runtime_commands.run_backfill_legacy_audit()


def run_knowledge_base_reset() -> None:
    return runtime_commands.run_knowledge_base_reset()


def run_semantic_backfill_status() -> None:
    return runtime_commands.run_semantic_backfill_status()


def run_semantic_backfill() -> None:
    return runtime_commands.run_semantic_backfill()


def run_replay_search() -> None:
    return runtime_commands.run_replay_search()


def run_eval_candidates() -> None:
    return runtime_commands.run_eval_candidates()


def run_evaluation_data_readiness() -> None:
    return runtime_commands.run_evaluation_data_readiness()


def run_replay_suite() -> None:
    return runtime_commands.run_replay_suite()


def run_export_ranking_dataset() -> None:
    return runtime_commands.run_export_ranking_dataset()


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
