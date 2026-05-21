from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli_commands import search_harness_learning as learning_commands


def test_materialize_retrieval_learning_dataset_cli_prints_summary(
    monkeypatch, capsys
) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    release_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-materialize-retrieval-learning",
            "--limit",
            "7",
            "--source-type",
            "feedback",
            "--set-name",
            "operator-set",
            "--created-by",
            "tester",
            "--search-harness-release-id",
            str(release_id),
        ],
    )

    def fake_materialize(session, **kwargs):
        assert kwargs["limit"] == 7
        assert kwargs["source_types"] == ["feedback"]
        assert kwargs["set_name"] == "operator-set"
        assert kwargs["created_by"] == "tester"
        assert kwargs["search_harness_release_id"] == release_id
        return {
            "judgment_set_id": str(uuid4()),
            "summary": {"judgment_count": 3, "hard_negative_count": 1},
        }

    learning_commands.run_materialize_retrieval_learning_dataset(
        session_factory_func=lambda: lambda: FakeSession(),
        materialize_retrieval_learning_dataset_func=fake_materialize,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["summary"]["judgment_count"] == 3
    assert output["summary"]["hard_negative_count"] == 1


def test_materialize_retrieval_learning_dataset_cli_accepts_replay_alert_corpus_source(
    monkeypatch,
    capsys,
) -> None:
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
            "docling-system-materialize-retrieval-learning",
            "--source-type",
            "claim_support_replay_alert_corpus",
        ],
    )

    def fake_materialize(session, **kwargs):
        assert kwargs["source_types"] == ["claim_support_replay_alert_corpus"]
        return {
            "judgment_set_id": str(uuid4()),
            "summary": {"judgment_count": 1, "hard_negative_count": 1},
        }

    learning_commands.run_materialize_retrieval_learning_dataset(
        session_factory_func=lambda: lambda: FakeSession(),
        materialize_retrieval_learning_dataset_func=fake_materialize,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["summary"]["judgment_count"] == 1


def test_evaluate_retrieval_learning_candidate_cli_prints_passed_gate(
    monkeypatch, capsys
) -> None:
    captured = {}

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
            "docling-system-evaluate-retrieval-learning-candidate",
            "wide_v2",
            "--source-type",
            "technical_report_claim_feedback",
            "--limit",
            "5",
            "--requested-by",
            "tester",
        ],
    )

    def fake_evaluate(session, request):
        captured["request"] = request
        return SimpleNamespace(
            gate_outcome="passed",
            model_dump=lambda mode="json": {
                "candidate_harness_name": request.candidate_harness_name,
                "source_types": request.source_types,
                "requested_by": request.requested_by,
                "gate_outcome": "passed",
            },
        )

    learning_commands.run_evaluate_retrieval_learning_candidate(
        session_factory_func=lambda: lambda: FakeSession(),
        evaluate_retrieval_learning_candidate_func=fake_evaluate,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert captured["request"].limit == 5
    assert output["candidate_harness_name"] == "wide_v2"
    assert output["source_types"] == ["technical_report_claim_feedback"]
    assert output["requested_by"] == "tester"


def test_evaluate_retrieval_learning_candidate_cli_exits_nonzero_on_failed_gate(
    monkeypatch, capsys
) -> None:
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
            "docling-system-evaluate-retrieval-learning-candidate",
            "wide_v2",
        ],
    )

    def fake_evaluate(session, request):
        return SimpleNamespace(
            gate_outcome="failed",
            model_dump=lambda mode="json": {
                "candidate_harness_name": request.candidate_harness_name,
                "gate_outcome": "failed",
            },
        )

    try:
        learning_commands.run_evaluate_retrieval_learning_candidate(
            session_factory_func=lambda: lambda: FakeSession(),
            evaluate_retrieval_learning_candidate_func=fake_evaluate,
        )
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected failed retrieval-learning gate to exit non-zero")

    output = json.loads(capsys.readouterr().out.strip())
    assert output["gate_outcome"] == "failed"


def test_create_retrieval_reranker_artifact_cli_prints_passed_gate(
    monkeypatch, capsys
) -> None:
    captured = {}

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
            "docling-system-create-retrieval-reranker-artifact",
            "wide_v2",
            "--artifact-name",
            "reranker-v2",
            "--base-harness-name",
            "wide_v1",
            "--source-type",
            "feedback",
        ],
    )

    def fake_create(session, request):
        captured["request"] = request
        return SimpleNamespace(
            gate_outcome="passed",
            model_dump=lambda mode="json": {
                "candidate_harness_name": request.candidate_harness_name,
                "artifact_name": request.artifact_name,
                "base_harness_name": request.base_harness_name,
                "source_types": request.source_types,
                "gate_outcome": "passed",
            },
        )

    learning_commands.run_create_retrieval_reranker_artifact(
        session_factory_func=lambda: lambda: FakeSession(),
        create_retrieval_reranker_artifact_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert captured["request"].artifact_name == "reranker-v2"
    assert output["base_harness_name"] == "wide_v1"
    assert output["source_types"] == ["feedback"]


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

    learning_commands.run_optimize_search_harness(
        session_factory_func=lambda: lambda: FakeSession(),
        run_search_harness_optimization_loop_func=lambda session, payload: SimpleNamespace(
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

    output = json.loads(capsys.readouterr().out.strip())
    assert output["base_harness_name"] == "wide_v2"
    assert output["baseline_harness_name"] == "default_v1"
    assert output["candidate_harness_name"] == "wide_v2_loop"
    assert output["artifact_path"] == "/tmp/search_harness_loop.json"
