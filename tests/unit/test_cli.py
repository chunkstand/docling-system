from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli import (
    run_audit,
    run_backfill_legacy_audit,
    run_eval_candidates,
    run_eval_reranker,
    run_eval_run,
    run_export_ranking_dataset,
    run_ingest_file,
    run_replay_search,
    run_replay_suite,
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

    monkeypatch.setattr(sys, "argv", ["docling-system-eval-candidates", "--limit", "2"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.cli.list_quality_eval_candidates",
        lambda session, limit=12: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "candidate_type": "live_search_gap",
                    "reason": "live search returned no results",
                    "query_text": "vent stack",
                    "mode": "hybrid",
                    "filters": {},
                    "expected_result_type": None,
                    "fixture_name": None,
                    "occurrence_count": 2,
                    "latest_seen_at": "2026-04-12T00:00:00Z",
                    "document_id": None,
                    "source_filename": None,
                    "evaluation_id": None,
                    "search_request_id": str(search_request_id),
                }
            )
        ],
    )

    run_eval_candidates()

    output = json.loads(capsys.readouterr().out.strip())
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
            "feedback",
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
    assert output["source_type"] == "feedback"
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
            "evaluation_queries",
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
                "sources": [{"source_type": payload.source_types[0], "improved_count": 2}],
            }
        ),
    )

    run_eval_reranker()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["candidate_harness_name"] == "wide_v2"
    assert output["baseline_harness_name"] == "default_v1"
    assert output["sources"][0]["source_type"] == "evaluation_queries"
