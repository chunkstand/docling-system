from __future__ import annotations

from app.cli_commands.common import lazy_service_attr


def ingest_local_file(*args, **kwargs):
    return lazy_service_attr("app.services.documents", "ingest_local_file")(*args, **kwargs)


def queue_local_ingest_directory(*args, **kwargs):
    return lazy_service_attr("app.services.ingest_batches", "queue_local_ingest_directory")(
        *args,
        **kwargs,
    )


def list_ingest_batches(*args, **kwargs):
    return lazy_service_attr("app.services.ingest_batches", "list_ingest_batches")(
        *args,
        **kwargs,
    )


def get_ingest_batch_detail(*args, **kwargs):
    return lazy_service_attr("app.services.ingest_batches", "get_ingest_batch_detail")(
        *args,
        **kwargs,
    )


def evaluate_run(*args, **kwargs):
    return lazy_service_attr("app.services.evaluations", "evaluate_run")(*args, **kwargs)


def resolve_baseline_run_id(*args, **kwargs):
    return lazy_service_attr("app.services.evaluations", "resolve_baseline_run_id")(
        *args,
        **kwargs,
    )


def run_integrity_audit(*args, **kwargs):
    return lazy_service_attr("app.services.audit", "run_integrity_audit")(*args, **kwargs)


def backfill_legacy_run_audit_fields(*args, **kwargs):
    return lazy_service_attr("app.services.cleanup", "backfill_legacy_run_audit_fields")(
        *args,
        **kwargs,
    )


def get_semantic_backfill_status(*args, **kwargs):
    return lazy_service_attr(
        "app.services.semantic_backfill",
        "get_semantic_backfill_status",
    )(*args, **kwargs)


def execute_semantic_backfill(*args, **kwargs):
    return lazy_service_attr(
        "app.services.semantic_backfill",
        "run_semantic_backfill",
    )(*args, **kwargs)


def replay_search_request(*args, **kwargs):
    return lazy_service_attr("app.services.search_history", "replay_search_request")(
        *args,
        **kwargs,
    )


def list_quality_eval_candidates(*args, **kwargs):
    return lazy_service_attr("app.services.quality", "list_quality_eval_candidates")(
        *args,
        **kwargs,
    )


def build_evaluation_data_readiness_report(*args, **kwargs):
    return lazy_service_attr(
        "app.services.evaluation_data_readiness",
        "build_evaluation_data_readiness_report",
    )(*args, **kwargs)


def run_search_replay_suite(*args, **kwargs):
    return lazy_service_attr("app.services.search_replays", "run_search_replay_suite")(
        *args,
        **kwargs,
    )


def export_ranking_dataset(*args, **kwargs):
    return lazy_service_attr("app.services.search_replays", "export_ranking_dataset")(
        *args,
        **kwargs,
    )


def materialize_retrieval_learning_dataset(*args, **kwargs):
    return lazy_service_attr(
        "app.services.retrieval_learning",
        "materialize_retrieval_learning_dataset",
    )(*args, **kwargs)


def evaluate_retrieval_learning_candidate(*args, **kwargs):
    return lazy_service_attr(
        "app.services.retrieval_learning",
        "evaluate_retrieval_learning_candidate",
    )(*args, **kwargs)


def create_retrieval_reranker_artifact(*args, **kwargs):
    return lazy_service_attr(
        "app.services.retrieval_learning",
        "create_retrieval_reranker_artifact",
    )(*args, **kwargs)


def evaluate_search_harness(*args, **kwargs):
    return lazy_service_attr(
        "app.services.search_harness_evaluations",
        "evaluate_search_harness",
    )(*args, **kwargs)


def list_search_harness_evaluations(*args, **kwargs):
    return lazy_service_attr(
        "app.services.search_harness_evaluations",
        "list_search_harness_evaluations",
    )(*args, **kwargs)


def get_search_harness_evaluation_detail(*args, **kwargs):
    return lazy_service_attr(
        "app.services.search_harness_evaluations",
        "get_search_harness_evaluation_detail",
    )(*args, **kwargs)


def evaluate_search_harness_release_gate(*args, **kwargs):
    return lazy_service_attr(
        "app.services.search_release_gate",
        "evaluate_search_harness_release_gate",
    )(*args, **kwargs)


def record_search_harness_release_gate(*args, **kwargs):
    return lazy_service_attr(
        "app.services.search_release_gate",
        "record_search_harness_release_gate",
    )(*args, **kwargs)


def create_search_harness_release_audit_bundle(*args, **kwargs):
    return lazy_service_attr(
        "app.services.audit_bundles",
        "create_search_harness_release_audit_bundle",
    )(*args, **kwargs)


def create_retrieval_training_run_audit_bundle(*args, **kwargs):
    return lazy_service_attr(
        "app.services.audit_bundles",
        "create_retrieval_training_run_audit_bundle",
    )(*args, **kwargs)


def create_audit_bundle_validation_receipt(*args, **kwargs):
    return lazy_service_attr(
        "app.services.audit_bundles",
        "create_audit_bundle_validation_receipt",
    )(*args, **kwargs)


def run_search_harness_optimization_loop(*args, **kwargs):
    return lazy_service_attr(
        "app.services.search_harness_optimization",
        "run_search_harness_optimization_loop",
    )(*args, **kwargs)


def execute_knowledge_base_reset(*args, **kwargs):
    return lazy_service_attr(
        "app.services.knowledge_base_reset",
        "execute_knowledge_base_reset",
    )(*args, **kwargs)
