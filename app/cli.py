from __future__ import annotations

from app.cli_commands import improvement_cases as improvement_case_commands
from app.cli_commands import ingest as ingest_commands
from app.cli_commands import runtime as runtime_commands
from app.cli_commands import search_harness as search_harness_commands
from app.cli_commands.common import lazy_service_attr as _lazy_service_attr
from app.db.session import get_session_factory
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
    return search_harness_commands.run_materialize_retrieval_learning_dataset(
        session_factory_func=get_session_factory,
        materialize_retrieval_learning_dataset_func=materialize_retrieval_learning_dataset,
    )


def run_evaluate_retrieval_learning_candidate() -> None:
    return search_harness_commands.run_evaluate_retrieval_learning_candidate(
        session_factory_func=get_session_factory,
        evaluate_retrieval_learning_candidate_func=evaluate_retrieval_learning_candidate,
    )


def run_create_retrieval_reranker_artifact() -> None:
    return search_harness_commands.run_create_retrieval_reranker_artifact(
        session_factory_func=get_session_factory,
        create_retrieval_reranker_artifact_func=create_retrieval_reranker_artifact,
    )


def run_eval_reranker() -> None:
    return search_harness_commands.run_eval_reranker(
        session_factory_func=get_session_factory,
        evaluate_search_harness_func=evaluate_search_harness,
    )


def run_search_harness_evaluation_list() -> None:
    return search_harness_commands.run_search_harness_evaluation_list(
        session_factory_func=get_session_factory,
        list_search_harness_evaluations_func=list_search_harness_evaluations,
    )


def run_search_harness_evaluation_show() -> None:
    return search_harness_commands.run_search_harness_evaluation_show(
        session_factory_func=get_session_factory,
        get_search_harness_evaluation_detail_func=get_search_harness_evaluation_detail,
    )


def run_gate_search_harness_release() -> None:
    return search_harness_commands.run_gate_search_harness_release(
        session_factory_func=get_session_factory,
        evaluate_search_harness_func=evaluate_search_harness,
        record_search_harness_release_gate_func=record_search_harness_release_gate,
    )


def run_search_harness_release_audit_bundle() -> None:
    return search_harness_commands.run_search_harness_release_audit_bundle(
        session_factory_func=get_session_factory,
        storage_service_factory=StorageService,
        create_search_harness_release_audit_bundle_func=create_search_harness_release_audit_bundle,
    )


def run_retrieval_training_run_audit_bundle() -> None:
    return search_harness_commands.run_retrieval_training_run_audit_bundle(
        session_factory_func=get_session_factory,
        storage_service_factory=StorageService,
        create_retrieval_training_run_audit_bundle_func=create_retrieval_training_run_audit_bundle,
    )


def run_audit_bundle_validation_receipt() -> None:
    return search_harness_commands.run_audit_bundle_validation_receipt(
        session_factory_func=get_session_factory,
        storage_service_factory=StorageService,
        create_audit_bundle_validation_receipt_func=create_audit_bundle_validation_receipt,
    )


def run_optimize_search_harness() -> None:
    return search_harness_commands.run_optimize_search_harness(
        session_factory_func=get_session_factory,
        run_search_harness_optimization_loop_func=run_search_harness_optimization_loop,
    )
