from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli_commands import search_harness as search_harness_commands


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

    search_harness_commands.run_materialize_retrieval_learning_dataset(
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

    search_harness_commands.run_materialize_retrieval_learning_dataset(
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

    search_harness_commands.run_evaluate_retrieval_learning_candidate(
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
        search_harness_commands.run_evaluate_retrieval_learning_candidate(
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

    search_harness_commands.run_create_retrieval_reranker_artifact(
        session_factory_func=lambda: lambda: FakeSession(),
        create_retrieval_reranker_artifact_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert captured["request"].artifact_name == "reranker-v2"
    assert output["base_harness_name"] == "wide_v1"
    assert output["source_types"] == ["feedback"]


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

    search_harness_commands.run_eval_reranker(
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

    search_harness_commands.run_search_harness_evaluation_list(
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

    search_harness_commands.run_search_harness_evaluation_show(
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

    search_harness_commands.run_gate_search_harness_release(
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
        search_harness_commands.run_gate_search_harness_release(
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


def test_search_harness_release_audit_bundle_cli_prints_bundle(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    class FakeStorageService:
        pass

    release_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-search-harness-release-audit-bundle",
            str(release_id),
            "--created-by",
            "tester",
        ],
    )

    def fake_create(session, requested_release_id, request, *, storage_service):
        assert requested_release_id == release_id
        assert request.created_by == "tester"
        assert isinstance(storage_service, FakeStorageService)
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "release_id": str(requested_release_id),
                "created_by": request.created_by,
            }
        )

    search_harness_commands.run_search_harness_release_audit_bundle(
        session_factory_func=lambda: lambda: FakeSession(),
        storage_service_factory=FakeStorageService,
        create_search_harness_release_audit_bundle_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["release_id"] == str(release_id)
    assert output["created_by"] == "tester"


def test_retrieval_training_run_audit_bundle_cli_prints_bundle(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    class FakeStorageService:
        pass

    training_run_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-retrieval-training-run-audit-bundle",
            str(training_run_id),
            "--created-by",
            "tester",
        ],
    )

    def fake_create(session, requested_training_run_id, request, *, storage_service):
        assert requested_training_run_id == training_run_id
        assert request.created_by == "tester"
        assert isinstance(storage_service, FakeStorageService)
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "training_run_id": str(requested_training_run_id),
                "created_by": request.created_by,
            }
        )

    search_harness_commands.run_retrieval_training_run_audit_bundle(
        session_factory_func=lambda: lambda: FakeSession(),
        storage_service_factory=FakeStorageService,
        create_retrieval_training_run_audit_bundle_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["training_run_id"] == str(training_run_id)
    assert output["created_by"] == "tester"


def test_audit_bundle_validation_receipt_cli_prints_receipt(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    class FakeStorageService:
        pass

    bundle_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-audit-bundle-validation-receipt",
            str(bundle_id),
            "--created-by",
            "tester",
        ],
    )

    def fake_create(session, requested_bundle_id, request, *, storage_service):
        assert requested_bundle_id == bundle_id
        assert request.created_by == "tester"
        assert isinstance(storage_service, FakeStorageService)
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "bundle_id": str(requested_bundle_id),
                "created_by": request.created_by,
            }
        )

    search_harness_commands.run_audit_bundle_validation_receipt(
        session_factory_func=lambda: lambda: FakeSession(),
        storage_service_factory=FakeStorageService,
        create_audit_bundle_validation_receipt_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["bundle_id"] == str(bundle_id)
    assert output["created_by"] == "tester"


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

    search_harness_commands.run_optimize_search_harness(
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
