from __future__ import annotations

from app.cli_commands import (
    search_harness,
    search_harness_audit,
    search_harness_evaluations,
    search_harness_learning,
)


def test_search_harness_cli_facade_reexports_focused_owners() -> None:
    assert (
        search_harness.run_materialize_retrieval_learning_dataset
        is search_harness_learning.run_materialize_retrieval_learning_dataset
    )
    assert search_harness.run_eval_reranker is search_harness_evaluations.run_eval_reranker
    assert (
        search_harness.run_audit_bundle_validation_receipt
        is search_harness_audit.run_audit_bundle_validation_receipt
    )
