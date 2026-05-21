from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli_commands import search_harness_evaluations as evaluation_commands


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

    evaluation_commands.run_eval_reranker(
        session_factory_func=lambda: lambda: FakeSession(),
        evaluate_search_harness_func=lambda session, payload: SimpleNamespace(
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

    def fake_list_search_harness_evaluations(
        session,
        *,
        limit=20,
        candidate_harness_name=None,
    ):
        return [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "evaluation_id": str(evaluation_id),
                    "candidate_harness_name": candidate_harness_name,
                    "limit": limit,
                    "status": "completed",
                }
            )
        ]

    evaluation_commands.run_search_harness_evaluation_list(
        session_factory_func=lambda: lambda: FakeSession(),
        list_search_harness_evaluations_func=fake_list_search_harness_evaluations,
    )

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

    evaluation_commands.run_search_harness_evaluation_show(
        session_factory_func=lambda: lambda: FakeSession(),
        get_search_harness_evaluation_detail_func=lambda session, requested_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "evaluation_id": str(requested_id),
                "candidate_harness_name": "wide_v2",
                "baseline_harness_name": "default_v1",
                "sources": [{"source_type": "evaluation_queries"}],
            }
        ),
    )

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

    def fake_record_search_harness_release_gate(
        session,
        evaluation,
        payload,
        requested_by=None,
        review_note=None,
    ):
        return SimpleNamespace(
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
        )

    evaluation_commands.run_gate_search_harness_release(
        session_factory_func=lambda: lambda: FakeSession(),
        evaluate_search_harness_func=lambda session, payload: SimpleNamespace(
            candidate_harness_name=payload.candidate_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            model_dump=lambda mode="json": {
                "candidate_harness_name": payload.candidate_harness_name,
                "baseline_harness_name": payload.baseline_harness_name,
                "sources": [{"source_type": payload.source_types[0]}],
            },
        ),
        record_search_harness_release_gate_func=fake_record_search_harness_release_gate,
    )

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

    def fake_record_search_harness_release_gate(
        session,
        evaluation,
        payload,
        requested_by=None,
        review_note=None,
    ):
        return SimpleNamespace(
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
        )

    try:
        evaluation_commands.run_gate_search_harness_release(
            session_factory_func=lambda: lambda: FakeSession(),
            evaluate_search_harness_func=lambda session, payload: SimpleNamespace(
                candidate_harness_name=payload.candidate_harness_name,
                baseline_harness_name=payload.baseline_harness_name,
                model_dump=lambda mode="json": {
                    "candidate_harness_name": payload.candidate_harness_name,
                    "baseline_harness_name": payload.baseline_harness_name,
                    "sources": [],
                },
            ),
            record_search_harness_release_gate_func=fake_record_search_harness_release_gate,
        )
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected failed release gate to exit non-zero")

    output = json.loads(capsys.readouterr().out.strip())
    assert output["gate"]["outcome"] == "failed"
    assert output["gate"]["reasons"] == ["no shared queries"]
