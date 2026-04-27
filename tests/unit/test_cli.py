from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.cli import (
    run_agent_task_actions,
    run_agent_task_analytics,
    run_agent_task_approval_trends,
    run_agent_task_approve,
    run_agent_task_artifact,
    run_agent_task_artifacts,
    run_agent_task_context,
    run_agent_task_cost_summary,
    run_agent_task_create,
    run_agent_task_decision_signals,
    run_agent_task_export_traces,
    run_agent_task_failure_artifact,
    run_agent_task_label,
    run_agent_task_list,
    run_agent_task_outcomes,
    run_agent_task_performance_summary,
    run_agent_task_recommendation_summary,
    run_agent_task_reject,
    run_agent_task_show,
    run_agent_task_trends,
    run_agent_task_value_density,
    run_agent_task_verification_trends,
    run_agent_task_verifications,
    run_agent_task_workflow_versions,
    run_audit,
    run_backfill_legacy_audit,
    run_eval_candidates,
    run_eval_corpus,
    run_eval_reranker,
    run_eval_run,
    run_export_ranking_dataset,
    run_gate_search_harness_release,
    run_improvement_case_import,
    run_improvement_case_list,
    run_improvement_case_record,
    run_improvement_case_summary,
    run_improvement_case_validate,
    run_ingest_batch_list,
    run_ingest_batch_show,
    run_ingest_dir,
    run_ingest_file,
    run_optimize_search_harness,
    run_replay_search,
    run_replay_suite,
    run_search_harness_evaluation_list,
    run_search_harness_evaluation_show,
)


def test_ingest_file_cli_prints_ingest_result(monkeypatch, capsys) -> None:
    document_id = uuid4()
    run_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-file", "/tmp/example.pdf"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr("app.cli.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.cli.ingest_local_file",
        lambda session, file_path, storage_service: (
            SimpleNamespace(
                document_id=document_id,
                run_id=run_id,
                status="queued",
                duplicate=False,
                recovery_run=False,
                active_run_id=None,
                active_run_status=None,
            ),
            202,
        ),
    )

    run_ingest_file()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["document_id"] == str(document_id)
    assert output["run_id"] == str(run_id)
    assert output["status"] == "queued"


def test_ingest_dir_cli_prints_batch_summary(monkeypatch, capsys) -> None:
    batch_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-dir", "/tmp/corpus", "--recursive"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr("app.cli.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.cli.queue_local_ingest_directory",
        lambda session, directory_path, storage_service, recursive: SimpleNamespace(
            model_dump=lambda mode="json", exclude=None: {
                "batch_id": str(batch_id),
                "source_type": "local_directory",
                "status": "completed",
                "root_path": str(directory_path),
                "recursive": recursive,
                "file_count": 2,
                "queued_count": 2,
                "recovery_queued_count": 0,
                "duplicate_count": 0,
                "failed_count": 0,
                "run_status_counts": {"queued": 2},
                "error_message": None,
                "created_at": "2026-04-14T00:00:00Z",
                "completed_at": "2026-04-14T00:00:01Z",
            }
        ),
    )

    run_ingest_dir()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["batch_id"] == str(batch_id)
    assert output["recursive"] is True
    assert output["file_count"] == 2


def test_ingest_batch_list_cli_prints_batches(monkeypatch, capsys) -> None:
    batch_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-batch-list", "--limit", "5"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_ingest_batches",
        lambda session, limit: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "batch_id": str(batch_id),
                    "status": "completed",
                    "file_count": 2,
                }
            )
        ],
    )

    run_ingest_batch_list()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["batch_id"] == str(batch_id)
    assert output[0]["file_count"] == 2


def test_ingest_batch_show_cli_prints_detail(monkeypatch, capsys) -> None:
    batch_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-batch-show", str(batch_id)])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_ingest_batch_detail",
        lambda session, requested_batch_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "batch_id": str(requested_batch_id),
                "status": "completed",
                "items": [
                    {
                        "relative_path": "doc.pdf",
                        "status": "queued",
                    }
                ],
            }
        ),
    )

    run_ingest_batch_show()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["batch_id"] == str(batch_id)
    assert output["items"][0]["relative_path"] == "doc.pdf"


def test_eval_run_cli_prints_summary(monkeypatch, capsys) -> None:
    document_id = uuid4()
    run_id = uuid4()
    active_run_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, model, key):
            if model.__name__ == "DocumentRun" and key == run_id:
                return SimpleNamespace(id=run_id, document_id=document_id)
            if model.__name__ == "Document" and key == document_id:
                return SimpleNamespace(
                    id=document_id, source_filename="report.pdf", active_run_id=active_run_id
                )
            return None

    monkeypatch.setattr(sys, "argv", ["docling-system-eval-run", str(run_id)])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    observed: dict[str, object | None] = {}

    def fake_evaluate_run(session, document, run, baseline_run_id=None):
        observed["baseline_run_id"] = baseline_run_id
        return SimpleNamespace(
            status="completed",
            fixture_name="fixture",
            summary_json={"query_count": 2, "passed_queries": 2},
            error_message=None,
        )

    monkeypatch.setattr("app.cli.evaluate_run", fake_evaluate_run)

    run_eval_run()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["run_id"] == str(run_id)
    assert output["document_id"] == str(document_id)
    assert output["status"] == "completed"
    assert observed["baseline_run_id"] == active_run_id


def test_eval_corpus_cli_evaluates_active_documents_without_manual_fixture(
    monkeypatch, capsys
) -> None:
    document_id = uuid4()
    run_id = uuid4()

    class FakeQuery:
        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return [
                SimpleNamespace(
                    id=document_id,
                    source_filename="autogen_doc.pdf",
                    active_run_id=run_id,
                    updated_at=None,
                )
            ]

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def query(self, _model):
            return FakeQuery()

        def get(self, model, key):
            if model.__name__ == "DocumentRun" and key == run_id:
                return SimpleNamespace(id=run_id)
            return None

    monkeypatch.setattr(sys, "argv", ["docling-system-eval-corpus"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.evaluate_run",
        lambda session, document, run: SimpleNamespace(
            status="completed",
            fixture_name="auto_autogen_doc",
            summary_json={"query_count": 2, "passed_queries": 2},
        ),
    )

    run_eval_corpus()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["document_id"] == str(document_id)
    assert output[0]["run_id"] == str(run_id)
    assert output[0]["fixture_name"] == "auto_autogen_doc"


def test_audit_cli_prints_summary(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-audit"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.run_integrity_audit",
        lambda session: {
            "checked_documents": 2,
            "checked_runs": 3,
            "violation_count": 1,
            "violations": [{"code": "failed_run_missing_failure_artifact"}],
        },
    )

    run_audit()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["checked_documents"] == 2
    assert output["violation_count"] == 1


def test_backfill_legacy_audit_cli_prints_summary(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-backfill-legacy-audit"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.backfill_legacy_run_audit_fields",
        lambda session: {
            "runs_scanned": 27,
            "chunk_count_backfilled": 0,
            "table_count_backfilled": 0,
            "figure_count_backfilled": 14,
            "failure_stage_backfilled": 1,
            "failure_artifacts_updated": 1,
        },
    )

    run_backfill_legacy_audit()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["runs_scanned"] == 27
    assert output["figure_count_backfilled"] == 14


def test_replay_search_cli_prints_summary(monkeypatch, capsys) -> None:
    search_request_id = uuid4()
    replay_request_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    monkeypatch.setattr(sys, "argv", ["docling-system-replay-search", str(search_request_id)])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.replay_search_request",
        lambda session, request_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "original_request": {"search_request_id": str(request_id)},
                "replay_request": {"search_request_id": str(replay_request_id)},
                "diff": {"overlap_count": 2},
            }
        ),
    )

    run_replay_search()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["original_request"]["search_request_id"] == str(search_request_id)
    assert output["replay_request"]["search_request_id"] == str(replay_request_id)


def test_eval_candidates_cli_prints_summary(monkeypatch, capsys) -> None:
    search_request_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    captured = {}

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-eval-candidates", "--limit", "2", "--include-resolved"],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_quality_eval_candidates",
        lambda session, limit=12, include_resolved=False: (
            captured.update({"limit": limit, "include_resolved": include_resolved})
            or [
                SimpleNamespace(
                    model_dump=lambda mode="json": {
                        "candidate_type": "live_search_gap",
                        "reason": "live search returned no results",
                        "query_text": "vent stack",
                        "mode": "hybrid",
                        "filters": {},
                        "evaluation_kind": "retrieval",
                        "expected_result_type": None,
                        "fixture_name": None,
                        "occurrence_count": 2,
                        "latest_seen_at": "2026-04-12T00:00:00Z",
                        "resolution_status": "resolved",
                        "resolved_at": "2026-04-12T00:05:00Z",
                        "resolution_reason": "later live search returned results",
                        "document_id": None,
                        "source_filename": None,
                        "evaluation_id": None,
                        "search_request_id": str(search_request_id),
                    }
                )
            ]
        ),
    )

    run_eval_candidates()

    output = json.loads(capsys.readouterr().out.strip())
    assert captured == {"limit": 2, "include_resolved": True}
    assert output[0]["candidate_type"] == "live_search_gap"
    assert output[0]["search_request_id"] == str(search_request_id)


def test_replay_suite_cli_prints_summary(monkeypatch, capsys) -> None:
    replay_run_id = uuid4()

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
            "docling-system-run-replay-suite",
            "cross_document_prose_regressions",
            "--limit",
            "3",
            "--harness-name",
            "wide_v2",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.run_search_replay_suite",
        lambda session, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "replay_run_id": str(replay_run_id),
                "source_type": payload.source_type,
                "query_count": payload.limit,
                "harness_name": payload.harness_name,
            }
        ),
    )

    run_replay_suite()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["replay_run_id"] == str(replay_run_id)
    assert output["source_type"] == "cross_document_prose_regressions"
    assert output["query_count"] == 3
    assert output["harness_name"] == "wide_v2"


def test_export_ranking_dataset_cli_prints_rows(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-export-ranking-dataset", "--limit", "5"],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.export_ranking_dataset",
        lambda session, limit=200: [
            {"dataset_type": "feedback", "feedback_type": "relevant"},
            {"dataset_type": "replay", "passed": True},
        ],
    )

    run_export_ranking_dataset()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["dataset_type"] == "feedback"
    assert output[1]["dataset_type"] == "replay"


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


def test_agent_task_actions_cli_prints_action_catalog(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-actions"])
    monkeypatch.setattr(
        "app.cli.list_agent_task_action_definitions",
        lambda: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "task_type": "get_latest_evaluation",
                    "description": "Fetch one latest evaluation.",
                }
            )
        ],
    )

    run_agent_task_actions()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["task_type"] == "get_latest_evaluation"


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
        "app.cli.evaluate_search_harness_verification",
        lambda session, evaluation, payload: SimpleNamespace(
            outcome="passed",
            metrics={"total_shared_query_count": 5},
            reasons=[],
            details={"thresholds": payload.model_dump(mode="json")},
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
        "app.cli.evaluate_search_harness_verification",
        lambda session, evaluation, payload: SimpleNamespace(
            outcome="failed",
            metrics={"total_shared_query_count": 0},
            reasons=["no shared queries"],
            details={"thresholds": payload.model_dump(mode="json")},
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


def test_agent_task_create_cli_prints_created_task(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-create",
            "list_quality_eval_candidates",
            "--input-json",
            '{"limit": 5}',
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.create_agent_task",
        lambda session, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(task_id),
                "task_type": payload.task_type,
                "status": "queued",
                "input": payload.input,
            }
        ),
    )

    run_agent_task_create()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["task_type"] == "list_quality_eval_candidates"
    assert output["input"]["limit"] == 5


def test_agent_task_list_cli_prints_tasks(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-list", "--status", "queued", "--limit", "3"],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_agent_tasks",
        lambda session, statuses=None, limit=50: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "task_id": str(task_id),
                    "status": statuses[0],
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_list()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["task_id"] == str(task_id)
    assert output[0]["status"] == "queued"
    assert output[0]["limit"] == 3


def test_agent_task_show_cli_prints_task_detail(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-show", str(task_id)])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_task_detail",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "replay_search_request",
            }
        ),
    )

    run_agent_task_show()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["task_type"] == "replay_search_request"


def test_agent_task_context_cli_prints_json(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-context", str(task_id)])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr("app.cli.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.cli.get_agent_task_context",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "draft_harness_config_update",
                "schema_name": "agent_task_context",
            }
        ),
    )

    run_agent_task_context()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["schema_name"] == "agent_task_context"


def test_agent_task_apply_cli_surfaces_consistent_applied_state(
    monkeypatch, capsys, tmp_path
) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    artifact_path = tmp_path / "applied_harness_config_update.json"
    artifact_path.write_text('{"draft_harness_name": "wide_v2_review"}')

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())

    monkeypatch.setattr(
        "app.cli.get_agent_task_detail",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "apply_harness_config_update",
                "result": {
                    "draft_harness_name": "wide_v2_review",
                    "artifact_id": str(artifact_id),
                },
                "context_summary": {"approval_state": "approved"},
            }
        ),
    )
    monkeypatch.setattr(
        "app.cli.get_agent_task_context",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "apply_harness_config_update",
                "summary": {
                    "approval_state": "approved",
                    "verification_state": "passed",
                },
                "output": {"draft_harness_name": "wide_v2_review"},
            }
        ),
    )
    monkeypatch.setattr(
        "app.cli.get_agent_task_artifact",
        lambda session, incoming_task_id, incoming_artifact_id: SimpleNamespace(
            task_id=incoming_task_id,
            id=incoming_artifact_id,
            storage_path=str(artifact_path),
            payload_json={"draft_harness_name": "wide_v2_review"},
        ),
    )
    monkeypatch.setattr(
        "app.cli.export_agent_task_traces",
        lambda session, limit=50, workflow_version=None, task_type=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "export_count": 1,
                "workflow_version": workflow_version,
                "task_type": task_type,
                "traces": [
                    {
                        "task_type": "apply_harness_config_update",
                        "result": {"draft_harness_name": "wide_v2_review"},
                        "context_summary": {"approval_state": "approved"},
                    }
                ],
            }
        ),
    )

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-show", str(task_id)])
    run_agent_task_show()
    show_output = json.loads(capsys.readouterr().out.strip())
    assert show_output["result"]["draft_harness_name"] == "wide_v2_review"

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-context", str(task_id)])
    run_agent_task_context()
    context_output = json.loads(capsys.readouterr().out.strip())
    assert context_output["output"]["draft_harness_name"] == "wide_v2_review"

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-artifact", str(task_id), str(artifact_id)],
    )
    run_agent_task_artifact()
    artifact_output = json.loads(capsys.readouterr().out.strip())
    assert artifact_output["draft_harness_name"] == "wide_v2_review"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-export-traces",
            "--task-type",
            "apply_harness_config_update",
        ],
    )
    run_agent_task_export_traces()
    export_output = json.loads(capsys.readouterr().out.strip())
    assert export_output["traces"][0]["result"]["draft_harness_name"] == "wide_v2_review"


def test_agent_task_triage_context_cli_prints_recommendation(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-context", str(task_id)])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_task_context",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "triage_replay_regression",
                "freshness_status": "fresh",
                "summary": {
                    "next_action": "candidate_ready_for_review",
                    "verification_state": "passed",
                },
            }
        ),
    )

    run_agent_task_context()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["freshness_status"] == "fresh"
    assert output["summary"]["next_action"] == "candidate_ready_for_review"


def test_agent_task_outcomes_cli_prints_rows(monkeypatch, capsys) -> None:
    task_id = uuid4()
    outcome_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-outcomes", str(task_id), "--limit", "5"],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_agent_task_outcomes",
        lambda session, incoming_task_id, limit=20: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "outcome_id": str(outcome_id),
                    "task_id": str(incoming_task_id),
                    "outcome_label": "useful",
                    "created_by": "operator@example.com",
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_outcomes()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["outcome_id"] == str(outcome_id)
    assert output[0]["task_id"] == str(task_id)
    assert output[0]["limit"] == 5


def test_agent_task_label_cli_prints_row(monkeypatch, capsys) -> None:
    task_id = uuid4()
    outcome_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-label",
            str(task_id),
            "--outcome-label",
            "useful",
            "--created-by",
            "operator@example.com",
            "--note",
            "accurate recommendation",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.create_agent_task_outcome",
        lambda session, incoming_task_id, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "outcome_id": str(outcome_id),
                "task_id": str(incoming_task_id),
                "outcome_label": payload.outcome_label,
                "created_by": payload.created_by,
                "note": payload.note,
            }
        ),
    )

    run_agent_task_label()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["outcome_id"] == str(outcome_id)
    assert output["outcome_label"] == "useful"
    assert output["created_by"] == "operator@example.com"


def test_agent_task_artifacts_cli_prints_artifact_rows(monkeypatch, capsys) -> None:
    task_id = uuid4()
    artifact_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-artifacts", str(task_id), "--limit", "5"],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_agent_task_artifacts",
        lambda session, incoming_task_id, limit=20: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "artifact_id": str(artifact_id),
                    "task_id": str(incoming_task_id),
                    "artifact_kind": "triage_summary",
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_artifacts()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["artifact_id"] == str(artifact_id)
    assert output[0]["task_id"] == str(task_id)
    assert output[0]["limit"] == 5


def test_agent_task_artifact_cli_prints_artifact_payload(monkeypatch, capsys, tmp_path) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    artifact_path = tmp_path / "triage_summary.json"
    artifact_path.write_text('{"shadow_mode": true, "triage_kind": "replay_regression"}')

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-artifact", str(task_id), str(artifact_id)],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_task_artifact",
        lambda session, incoming_task_id, incoming_artifact_id: SimpleNamespace(
            task_id=incoming_task_id,
            id=incoming_artifact_id,
            storage_path=str(artifact_path),
            payload_json={"shadow_mode": True},
        ),
    )

    run_agent_task_artifact()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["triage_kind"] == "replay_regression"


def test_agent_task_verifications_cli_prints_verification_rows(monkeypatch, capsys) -> None:
    task_id = uuid4()
    verification_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-verifications", str(task_id), "--limit", "5"],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_task_verifications",
        lambda session, incoming_task_id, limit=20: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "verification_id": str(verification_id),
                    "target_task_id": str(incoming_task_id),
                    "outcome": "passed",
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_verifications()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["verification_id"] == str(verification_id)
    assert output[0]["target_task_id"] == str(task_id)
    assert output[0]["limit"] == 5


def test_agent_task_failure_artifact_cli_prints_failure_payload(
    monkeypatch, capsys, tmp_path
) -> None:
    task_id = uuid4()
    failure_path = tmp_path / "failure.json"
    failure_path.write_text('{"failure_type": "ValueError", "failure_stage": "execute"}')

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, model, key):
            return SimpleNamespace(failure_artifact_path=str(failure_path))

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-failure-artifact", str(task_id)],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())

    run_agent_task_failure_artifact()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["failure_type"] == "ValueError"
    assert output["failure_stage"] == "execute"


def test_agent_task_approve_cli_prints_updated_task(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-approve",
            str(task_id),
            "--approved-by",
            "operator@example.com",
            "--approval-note",
            "ok",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.approve_agent_task",
        lambda session, incoming_task_id, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "approved_by": payload.approved_by,
                "approval_note": payload.approval_note,
            }
        ),
    )

    run_agent_task_approve()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["approved_by"] == "operator@example.com"
    assert output["approval_note"] == "ok"


def test_agent_task_reject_cli_prints_updated_task(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-reject",
            str(task_id),
            "--rejected-by",
            "reviewer@example.com",
            "--rejection-note",
            "not enough evidence",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.reject_agent_task",
        lambda session, incoming_task_id, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "rejected_by": payload.rejected_by,
                "rejection_note": payload.rejection_note,
                "status": "rejected",
            }
        ),
    )

    run_agent_task_reject()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["rejected_by"] == "reviewer@example.com"
    assert output["rejection_note"] == "not enough evidence"
    assert output["status"] == "rejected"


def test_agent_task_analytics_cli_prints_summary(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-analytics"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_task_analytics_summary",
        lambda session: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_count": 4,
                "labeled_task_count": 2,
                "outcome_label_counts": {"useful": 1, "correct": 1},
            }
        ),
    )

    run_agent_task_analytics()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_count"] == 4
    assert output["labeled_task_count"] == 2


def test_agent_task_workflow_versions_cli_prints_rows(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-workflow-versions"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_agent_task_workflow_summaries",
        lambda session: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "workflow_version": "v1",
                    "task_count": 4,
                }
            )
        ],
    )

    run_agent_task_workflow_versions()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["workflow_version"] == "v1"
    assert output[0]["task_count"] == 4


def test_agent_task_export_traces_cli_prints_payload(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-export-traces",
            "--limit",
            "10",
            "--workflow-version",
            "v1",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.export_agent_task_traces",
        lambda session, limit=50, workflow_version=None, task_type=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "export_count": 1,
                "workflow_version": workflow_version,
                "task_type": task_type,
                "traces": [{"task_type": "triage_replay_regression"}],
            }
        ),
    )

    run_agent_task_export_traces()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["export_count"] == 1
    assert output["workflow_version"] == "v1"


def test_agent_task_trends_cli_prints_payload(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-trends", "--bucket", "week", "--workflow-version", "v1"],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_task_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "bucket": bucket,
                "workflow_version": workflow_version,
                "series": [{"created_count": 1}],
            }
        ),
    )

    run_agent_task_trends()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["bucket"] == "week"
    assert output["workflow_version"] == "v1"


def test_agent_task_recommendation_and_cost_cli_print_payloads(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_task_recommendation_summary",
        lambda session, task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_type": task_type,
                "workflow_version": workflow_version,
                "downstream_improved_count": 1,
            }
        ),
    )
    monkeypatch.setattr(
        "app.cli.get_agent_task_cost_summary",
        lambda session, task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_type": task_type,
                "workflow_version": workflow_version,
                "estimated_usd_total": 0.0,
            }
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-recommendation-summary",
            "--task-type",
            "triage_replay_regression",
        ],
    )
    run_agent_task_recommendation_summary()
    recommendation_output = json.loads(capsys.readouterr().out.strip())
    assert recommendation_output["downstream_improved_count"] == 1

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-cost-summary", "--workflow-version", "v1"],
    )
    run_agent_task_cost_summary()
    cost_output = json.loads(capsys.readouterr().out.strip())
    assert cost_output["workflow_version"] == "v1"


def test_agent_task_remaining_milestone9_clis_print_payloads(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.get_agent_verification_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {"bucket": bucket, "series": [{"passed_count": 1}]}
        ),
    )
    monkeypatch.setattr(
        "app.cli.get_agent_approval_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {"bucket": bucket, "series": [{"approval_count": 1}]}
        ),
    )
    monkeypatch.setattr(
        "app.cli.get_agent_task_performance_summary",
        lambda session, task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {"median_execution_latency_ms": 12.0}
        ),
    )
    monkeypatch.setattr(
        "app.cli.get_agent_task_value_density",
        lambda session: [
            SimpleNamespace(
                model_dump=lambda mode="json": {"task_type": "triage_replay_regression"}
            )
        ],
    )
    monkeypatch.setattr(
        "app.cli.get_agent_task_decision_signals",
        lambda session: [SimpleNamespace(model_dump=lambda mode="json": {"status": "healthy"})],
    )

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-verification-trends"])
    run_agent_task_verification_trends()
    assert json.loads(capsys.readouterr().out.strip())["series"][0]["passed_count"] == 1

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-approval-trends"])
    run_agent_task_approval_trends()
    assert json.loads(capsys.readouterr().out.strip())["series"][0]["approval_count"] == 1

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-performance-summary"])
    run_agent_task_performance_summary()
    assert json.loads(capsys.readouterr().out.strip())["median_execution_latency_ms"] == 12.0

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-value-density"])
    run_agent_task_value_density()
    assert json.loads(capsys.readouterr().out.strip())[0]["task_type"] == "triage_replay_regression"

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-decision-signals"])
    run_agent_task_decision_signals()
    assert json.loads(capsys.readouterr().out.strip())[0]["status"] == "healthy"


def test_improvement_case_validate_cli_prints_validation(monkeypatch, capsys, tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    registry_path.write_text("schema_name: improvement_cases\nschema_version: '1.0'\ncases: []\n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-improvement-case-validate", "--path", str(registry_path)],
    )

    run_improvement_case_validate()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["valid"] is True
    assert output["issue_count"] == 0


def test_improvement_case_validate_cli_reports_invalid_registry(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    registry_path.write_text(
        "\n".join(
            [
                "schema_name: improvement_cases",
                "schema_version: '1.0'",
                "cases:",
                "  - case_id: ''",
                "    title: ''",
                "    status: open",
                "    cause_class: missing_test",
                "    observed_failure: ''",
                "    source:",
                "      source_type: incident",
            ]
        )
        + "\n"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-improvement-case-validate", "--path", str(registry_path)],
    )

    with pytest.raises(SystemExit) as exc_info:
        run_improvement_case_validate()

    output = json.loads(capsys.readouterr().out.strip())
    assert exc_info.value.code == 1
    assert output["valid"] is False
    assert output["issue_count"] >= 1


def test_improvement_case_record_cli_allows_open_observation(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-improvement-case-record",
            "--path",
            str(registry_path),
            "--case-id",
            "IC-20260424-open-cli",
            "--title",
            "Missing eval coverage",
            "--observed-failure",
            "A failed behavior had not yet been converted into an artifact.",
            "--cause-class",
            "missing_test",
            "--source-type",
            "incident",
            "--status",
            "open",
        ],
    )

    run_improvement_case_record()

    created = json.loads(capsys.readouterr().out.strip())
    assert created["case_id"] == "IC-20260424-open-cli"
    assert created["status"] == "open"
    assert created["artifact"]["target_path"] == ""
    assert created["verification"]["catches_old_failure"] is False


def test_improvement_case_record_and_list_cli_roundtrip(
    monkeypatch, capsys, tmp_path
) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-improvement-case-record",
            "--path",
            str(registry_path),
            "--case-id",
            "IC-20260424-cli",
            "--title",
            "Missing route contract",
            "--observed-failure",
            "A router could use an unknown capability.",
            "--cause-class",
            "missing_constraint",
            "--artifact-type",
            "contract",
            "--artifact-path",
            "tests/unit/test_api_route_contracts.py",
            "--artifact-description",
            "Route capability manifest contract.",
            "--verification-command",
            "uv run pytest tests/unit/test_api_route_contracts.py -q",
            "--source-type",
            "bad_diff",
        ],
    )

    run_improvement_case_record()
    created = json.loads(capsys.readouterr().out.strip())

    assert created["case_id"] == "IC-20260424-cli"
    assert created["verification"]["catches_old_failure"] is True

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-improvement-case-list", "--path", str(registry_path)],
    )
    run_improvement_case_list()
    listed = json.loads(capsys.readouterr().out.strip())

    assert listed[0]["case_id"] == "IC-20260424-cli"
    assert listed[0]["artifact_type"] == "contract"


def test_improvement_case_import_cli_delegates_to_service(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    captured = {}

    def fake_import_workflow(**kwargs):
        captured.update(kwargs)
        payload = {
            "schema_name": "improvement_case_import",
            "schema_version": "1.0",
            "dry_run": kwargs["dry_run"],
            "candidate_count": 1,
            "imported_count": 1,
            "skipped_count": 0,
            "imported": [{"source_type": "hygiene_finding"}],
            "skipped": [],
        }
        return SimpleNamespace(model_dump=lambda mode="json": payload)

    monkeypatch.setattr("app.cli.run_improvement_case_import_workflow", fake_import_workflow)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-improvement-case-import",
            "--path",
            str(registry_path),
            "--source",
            "hygiene",
            "--limit",
            "5",
            "--workflow-version",
            "improvement_v2",
            "--source-path",
            "build/architecture-governance/architecture_governance_report.json",
            "--dry-run",
        ],
    )

    run_improvement_case_import()

    output = json.loads(capsys.readouterr().out.strip())
    assert captured == {
        "source": "hygiene",
        "limit": 5,
        "workflow_version": "improvement_v2",
        "path": str(registry_path),
        "source_path": "build/architecture-governance/architecture_governance_report.json",
        "dry_run": True,
    }
    assert output["imported_count"] == 1
    assert output["imported"][0]["source_type"] == "hygiene_finding"


def test_improvement_case_summary_cli_prints_counts(monkeypatch, capsys, tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-improvement-case-record",
            "--path",
            str(registry_path),
            "--case-id",
            "IC-20260424-summary",
            "--title",
            "Bad tool choice",
            "--observed-failure",
            "A command used an unsafe tool for the job.",
            "--cause-class",
            "bad_tool",
            "--artifact-type",
            "runbook",
            "--artifact-path",
            "docs/improvement_loop.md",
            "--artifact-description",
            "Runbook guidance for future tool choice.",
            "--acceptance-condition",
            "Future cases classify bad tool usage explicitly.",
        ],
    )
    run_improvement_case_record()
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-improvement-case-summary", "--path", str(registry_path)],
    )
    run_improvement_case_summary()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["case_count"] == 1
    assert output["cause_class_counts"] == {"bad_tool": 1}
