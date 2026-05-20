from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.regression_readiness_bootstrap import bootstrap_regression_readiness

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_bootstrap_regression_readiness_promotes_real_fixture_and_turns_gate_green(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.services.runs.semantics_feature_enabled", lambda settings: False)

    storage_root = postgres_integration_harness.storage_service.storage_root
    auto_corpus_path = storage_root / "evaluation_corpus.auto.yaml"
    readiness_output_path = storage_root / "evaluation_data_readiness.latest.json"

    with postgres_integration_harness.session_factory() as session:
        payload = bootstrap_regression_readiness(
            session,
            storage_service=postgres_integration_harness.storage_service,
            bootstrap_document_path=Path("docs/evaluation_bootstrap/regression_doc_03.pdf"),
            manual_corpus_path=Path("docs/evaluation_corpus.yaml"),
            auto_corpus_seed_path=Path("docs/evaluation_corpus.auto.bootstrap.yaml"),
            auto_corpus_path=auto_corpus_path,
            output_path=readiness_output_path,
        )

    assert payload["schema_name"] == "regression_readiness_bootstrap_result"
    assert payload["source_filename"] == "regression_doc_03.pdf"
    assert payload["manual_evaluation"]["status"] == "completed"
    assert payload["manual_evaluation"]["fixture_name"] == "regression_doc_03_blue_mesas_seed"
    assert payload["readiness"]["summary"]["regression_ready"] is True
    assert payload["readiness"]["summary"]["court_grade_ready"] is False
    assert payload["readiness"]["summary"]["regression_blockers"] == []
    assert auto_corpus_path.exists()
    assert readiness_output_path.exists()
    for source_type in (
        "evaluation_queries",
        "live_search_gaps",
        "cross_document_prose_regressions",
    ):
        replay = payload["replay_runs"][source_type]
        assert replay["status"] == "completed"
        assert replay["query_count"] >= 1
