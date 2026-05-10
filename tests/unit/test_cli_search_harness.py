from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli import (
    run_eval_reranker,
    run_gate_search_harness_release,
    run_optimize_search_harness,
    run_search_harness_evaluation_list,
    run_search_harness_evaluation_show,
)


def test_eval_reranker_cli_prints_summary(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-eval-reranker",
            "wide_v2",
            "--baseline-harness-name",
            "default_v1",
            "--source-type",
            "cross_document_prose_regressions",
            "--limit",
            "5",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.evaluate_search_harness",
        lambda session, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "baseline_harness_name": payload.baseline_harness_name,
                "candidate_harness_name": payload.candidate_harness_name,
                "limit": payload.limit,
                "sources": [
                    {
                        "source_type": payload.source_types[0],
                        "improved_count": 2,
                        "baseline_zero_result_count": 0,
                        "candidate_zero_result_count": 0,
                    }
                ],
            }
        ),
    )

    run_eval_reranker()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["candidate_harness_name"] == "wide_v2"
    assert output["baseline_harness_name"] == "default_v1"
    assert output["sources"][0]["source_type"] == "cross_document_prose_regressions"


def test_search_harness_evaluation_list_cli_prints_durable_rows(monkeypatch, capsys) -> None:
    evaluation_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-search-harness-evaluation-list",
            "--limit",
            "3",
            "--candidate-harness-name",
            "wide_v2",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_search_harness_evaluations",
        lambda session, *, limit=20, candidate_harness_name=None: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "evaluation_id": str(evaluation_id),
                    "candidate_harness_name": candidate_harness_name,
                    "limit": limit,
                    "status": "completed",
                }
            )
        ],
    )

    run_search_harness_evaluation_list()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["evaluation_id"] == str(evaluation_id)
    assert output[0]["candidate_harness_name"] == "wide_v2"
    assert output[0]["limit"] == 3


def test_search_harness_evaluation_show_cli_prints_detail(monkeypatch, capsys) -> None:
    evaluation_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-search-harness-evaluation-show", str(evaluation_id)],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_search_harness_evaluation_detail",
        lambda session, requested_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "evaluation_id": str(requested_id),
                "candidate_harness_name": "wide_v2",
                "baseline_harness_name": "default_v1",
                "sources": [{"source_type": "evaluation_queries"}],
            }
        ),
    )

    run_search_harness_evaluation_show()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["evaluation_id"] == str(evaluation_id)
    assert output["sources"][0]["source_type"] == "evaluation_queries"


def test_gate_search_harness_release_cli_prints_passed_gate(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-gate-search-harness-release",
            "wide_v2",
            "--baseline-harness-name",
            "default_v1",
            "--source-type",
            "evaluation_queries",
            "--limit",
            "5",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.evaluate_search_harness",
        lambda session, payload: SimpleNamespace(
            candidate_harness_name=payload.candidate_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            model_dump=lambda mode="json": {
                "candidate_harness_name": payload.candidate_harness_name,
                "baseline_harness_name": payload.baseline_harness_name,
                "sources": [{"source_type": payload.source_types[0]}],
            },
        ),
    )
    monkeypatch.setattr(
        "app.cli.record_search_harness_release_gate",
        lambda session, evaluation, payload, requested_by=None, review_note=None: SimpleNamespace(
            outcome="passed",
            metrics={"total_shared_query_count": 5},
            reasons=[],
            details={"thresholds": payload.model_dump(mode="json")},
            model_dump=lambda mode="json": {
                "release_id": str(uuid4()),
                "outcome": "passed",
                "metrics": {"total_shared_query_count": 5},
                "reasons": [],
                "details": {"thresholds": payload.model_dump(mode="json")},
            },
        ),
    )

    run_gate_search_harness_release()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["candidate_harness_name"] == "wide_v2"
    assert output["gate"]["outcome"] == "passed"


def test_gate_search_harness_release_cli_exits_nonzero_on_failed_gate(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-gate-search-harness-release",
            "wide_v2",
            "--baseline-harness-name",
            "default_v1",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.evaluate_search_harness",
        lambda session, payload: SimpleNamespace(
            candidate_harness_name=payload.candidate_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            model_dump=lambda mode="json": {
                "candidate_harness_name": payload.candidate_harness_name,
                "baseline_harness_name": payload.baseline_harness_name,
                "sources": [],
            },
        ),
    )
    monkeypatch.setattr(
        "app.cli.record_search_harness_release_gate",
        lambda session, evaluation, payload, requested_by=None, review_note=None: SimpleNamespace(
            outcome="failed",
            metrics={"total_shared_query_count": 0},
            reasons=["no shared queries"],
            details={"thresholds": payload.model_dump(mode="json")},
            model_dump=lambda mode="json": {
                "release_id": str(uuid4()),
                "outcome": "failed",
                "metrics": {"total_shared_query_count": 0},
                "reasons": ["no shared queries"],
                "details": {"thresholds": payload.model_dump(mode="json")},
            },
        ),
    )

    try:
        run_gate_search_harness_release()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected failed release gate to exit non-zero")

    output = json.loads(capsys.readouterr().out.strip())
    assert output["gate"]["outcome"] == "failed"
    assert output["gate"]["reasons"] == ["no shared queries"]


def test_optimize_search_harness_cli_prints_loop_result(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-optimize-search-harness",
            "wide_v2",
            "--baseline-harness-name",
            "default_v1",
            "--source-type",
            "evaluation_queries",
            "--iterations",
            "1",
            "--field",
            "keyword_candidate_multiplier",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.run_search_harness_optimization_loop",
        lambda session, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "base_harness_name": payload.base_harness_name,
                "baseline_harness_name": payload.baseline_harness_name,
                "candidate_harness_name": payload.candidate_harness_name,
                "iterations_requested": payload.iterations,
                "stopped_reason": "iteration_limit_reached",
                "artifact_path": "/tmp/search_harness_loop.json",
            }
        ),
    )

    run_optimize_search_harness()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["base_harness_name"] == "wide_v2"
    assert output["baseline_harness_name"] == "default_v1"
    assert output["candidate_harness_name"] == "wide_v2_loop"
    assert output["artifact_path"] == "/tmp/search_harness_loop.json"
