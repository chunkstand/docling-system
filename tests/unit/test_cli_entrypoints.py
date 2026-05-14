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
