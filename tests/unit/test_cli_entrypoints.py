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
        "run_regression_readiness_bootstrap",
        "run_court_grade_readiness_bootstrap",
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
        "run_materialize_retrieval_learning_dataset": [],
        "run_evaluate_retrieval_learning_candidate": [],
        "run_create_retrieval_reranker_artifact": [],
        "run_eval_reranker": [],
        "run_search_harness_evaluation_list": [],
        "run_search_harness_evaluation_show": [],
        "run_gate_search_harness_release": [],
        "run_search_harness_release_audit_bundle": [],
        "run_retrieval_training_run_audit_bundle": [],
        "run_audit_bundle_validation_receipt": [],
        "run_optimize_search_harness": [],
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
