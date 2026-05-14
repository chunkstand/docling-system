from __future__ import annotations

import app.cli as cli


def test_runtime_entrypoint_forwarders_delegate_to_runtime_owner(monkeypatch) -> None:
    forwarded: list[str] = []
    runtime_forwarders = [
        "run_eval_run",
        "run_eval_corpus",
        "run_audit",
        "run_backfill_legacy_audit",
        "run_knowledge_base_reset",
        "run_semantic_backfill_status",
        "run_semantic_backfill",
        "run_replay_search",
        "run_eval_candidates",
        "run_evaluation_data_readiness",
        "run_replay_suite",
        "run_export_ranking_dataset",
    ]

    for name in runtime_forwarders:
        monkeypatch.setattr(
            cli.runtime_commands,
            name,
            lambda name=name: forwarded.append(name),
        )

    for name in runtime_forwarders:
        getattr(cli, name)()

    assert forwarded == runtime_forwarders


def test_search_harness_entrypoint_forwarders_delegate_to_search_harness_owner(monkeypatch) -> None:
    forwarded: list[tuple[str, list[str]]] = []
    search_harness_forwarders = {
        "run_materialize_retrieval_learning_dataset": [
            "session_factory_func",
            "materialize_retrieval_learning_dataset_func",
        ],
        "run_evaluate_retrieval_learning_candidate": [
            "session_factory_func",
            "evaluate_retrieval_learning_candidate_func",
        ],
        "run_create_retrieval_reranker_artifact": [
            "session_factory_func",
            "create_retrieval_reranker_artifact_func",
        ],
        "run_eval_reranker": [
            "session_factory_func",
            "evaluate_search_harness_func",
        ],
        "run_search_harness_evaluation_list": [
            "session_factory_func",
            "list_search_harness_evaluations_func",
        ],
        "run_search_harness_evaluation_show": [
            "session_factory_func",
            "get_search_harness_evaluation_detail_func",
        ],
        "run_gate_search_harness_release": [
            "session_factory_func",
            "evaluate_search_harness_func",
            "record_search_harness_release_gate_func",
        ],
        "run_search_harness_release_audit_bundle": [
            "session_factory_func",
            "storage_service_factory",
            "create_search_harness_release_audit_bundle_func",
        ],
        "run_retrieval_training_run_audit_bundle": [
            "session_factory_func",
            "storage_service_factory",
            "create_retrieval_training_run_audit_bundle_func",
        ],
        "run_audit_bundle_validation_receipt": [
            "session_factory_func",
            "storage_service_factory",
            "create_audit_bundle_validation_receipt_func",
        ],
        "run_optimize_search_harness": [
            "session_factory_func",
            "run_search_harness_optimization_loop_func",
        ],
    }

    for name in search_harness_forwarders:
        monkeypatch.setattr(
            cli.search_harness_commands,
            name,
            lambda name=name, **kwargs: forwarded.append((name, sorted(kwargs))),
        )

    for name in search_harness_forwarders:
        getattr(cli, name)()

    assert forwarded == [
        (name, sorted(expected_kwargs))
        for name, expected_kwargs in search_harness_forwarders.items()
    ]
