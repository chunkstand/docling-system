from __future__ import annotations

from importlib import import_module

from app.cli_commands import improvement_cases as improvement_case_commands
from app.cli_commands import ingest as ingest_commands
from app.cli_commands import runtime as runtime_commands
from app.cli_commands import search_harness as search_harness_commands


def evaluate_search_harness_verification(*args, **kwargs):
    return import_module(
        "app.cli_commands.service_forwarders"
    ).evaluate_search_harness_release_gate(*args, **kwargs)


def run_improvement_case_validate() -> None:
    return improvement_case_commands.run_improvement_case_validate()


def run_improvement_case_list() -> None:
    return improvement_case_commands.run_improvement_case_list()


def run_improvement_case_summary() -> None:
    return improvement_case_commands.run_improvement_case_summary()


def run_improvement_case_record() -> None:
    return improvement_case_commands.run_improvement_case_record()


def run_ingest_file() -> None:
    return ingest_commands.run_ingest_file()


def run_ingest_dir() -> None:
    return ingest_commands.run_ingest_dir()


def run_ingest_batch_list() -> None:
    return ingest_commands.run_ingest_batch_list()


def run_ingest_batch_show() -> None:
    return ingest_commands.run_ingest_batch_show()


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


def run_regression_readiness_bootstrap() -> None:
    return runtime_commands.run_regression_readiness_bootstrap()


def run_court_grade_readiness_bootstrap() -> None:
    return runtime_commands.run_court_grade_readiness_bootstrap()


def run_replay_suite() -> None:
    return runtime_commands.run_replay_suite()


def run_export_ranking_dataset() -> None:
    return runtime_commands.run_export_ranking_dataset()


def run_materialize_retrieval_learning_dataset() -> None:
    return search_harness_commands.run_materialize_retrieval_learning_dataset()


def run_evaluate_retrieval_learning_candidate() -> None:
    return search_harness_commands.run_evaluate_retrieval_learning_candidate()


def run_create_retrieval_reranker_artifact() -> None:
    return search_harness_commands.run_create_retrieval_reranker_artifact()


def run_eval_reranker() -> None:
    return search_harness_commands.run_eval_reranker()


def run_search_harness_evaluation_list() -> None:
    return search_harness_commands.run_search_harness_evaluation_list()


def run_search_harness_evaluation_show() -> None:
    return search_harness_commands.run_search_harness_evaluation_show()


def run_gate_search_harness_release() -> None:
    return search_harness_commands.run_gate_search_harness_release()


def run_search_harness_release_audit_bundle() -> None:
    return search_harness_commands.run_search_harness_release_audit_bundle()


def run_retrieval_training_run_audit_bundle() -> None:
    return search_harness_commands.run_retrieval_training_run_audit_bundle()


def run_audit_bundle_validation_receipt() -> None:
    return search_harness_commands.run_audit_bundle_validation_receipt()


def run_optimize_search_harness() -> None:
    return search_harness_commands.run_optimize_search_harness()
