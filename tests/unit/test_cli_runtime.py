from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli_commands import runtime as runtime_commands


def test_knowledge_base_reset_cli_defaults_to_dry_run(monkeypatch, capsys) -> None:
    captured = {}

    class FakeOptions:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeResetError(Exception):
        pass

    def fake_execute(options):
        captured["options"] = options
        return {"mode": "dry_run", "execute": options.execute}

    monkeypatch.setattr(sys, "argv", ["docling-system-knowledge-base-reset"])

    runtime_commands.run_knowledge_base_reset(
        execute_knowledge_base_reset_func=fake_execute,
        options_cls=FakeOptions,
        reset_error_cls=FakeResetError,
    )

    output = json.loads(capsys.readouterr().out)
    assert output == {"mode": "dry_run", "execute": False}
    assert captured["options"].execute is False


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

    observed: dict[str, object | None] = {}

    def fake_evaluate_run(session, document, run, baseline_run_id=None):
        observed["baseline_run_id"] = baseline_run_id
        return SimpleNamespace(
            status="completed",
            fixture_name="fixture",
            summary_json={"query_count": 2, "passed_queries": 2},
            error_message=None,
        )

    monkeypatch.setattr(sys, "argv", ["docling-system-eval-run", str(run_id)])

    runtime_commands.run_eval_run(
        session_factory_func=lambda: lambda: FakeSession(),
        resolve_baseline_run_id_func=lambda run_id, active_id, explicit_baseline_run_id=None: (
            active_id
        ),
        evaluate_run_func=fake_evaluate_run,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["run_id"] == str(run_id)
    assert output["document_id"] == str(document_id)
    assert output["status"] == "completed"
    assert observed["baseline_run_id"] == active_run_id


def test_eval_corpus_cli_prints_runner_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["docling-system-eval-corpus"])

    runtime_commands.run_eval_corpus(
        run_eval_corpus_summary_func=lambda: [
            {
                "document_id": "doc-id",
                "run_id": "run-id",
                "fixture_name": "auto_autogen_doc",
            }
        ]
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["document_id"] == "doc-id"
    assert output[0]["run_id"] == "run-id"
    assert output[0]["fixture_name"] == "auto_autogen_doc"


def test_audit_cli_prints_summary(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-audit"])

    runtime_commands.run_audit(
        session_factory_func=lambda: lambda: FakeSession(),
        run_integrity_audit_func=lambda session: {
            "checked_documents": 2,
            "checked_runs": 3,
            "violation_count": 1,
            "violations": [{"code": "failed_run_missing_failure_artifact"}],
        },
    )

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

    runtime_commands.run_backfill_legacy_audit(
        session_factory_func=lambda: lambda: FakeSession(),
        backfill_legacy_run_audit_fields_func=lambda session: {
            "runs_scanned": 27,
            "chunk_count_backfilled": 0,
            "table_count_backfilled": 0,
            "figure_count_backfilled": 14,
            "failure_stage_backfilled": 1,
            "failure_artifacts_updated": 1,
        },
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["runs_scanned"] == 27
    assert output["figure_count_backfilled"] == 14


def test_semantic_backfill_status_cli_prints_payload(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-semantic-backfill-status"])

    runtime_commands.run_semantic_backfill_status(
        session_factory_func=lambda: lambda: FakeSession(),
        get_semantic_backfill_status_func=lambda session: SimpleNamespace(
            model_dump=lambda mode="json": {
                "schema_name": "semantic_backfill_status",
                "document_count": 4,
            }
        ),
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["schema_name"] == "semantic_backfill_status"
    assert output["document_count"] == 4


def test_semantic_backfill_cli_prints_payload(monkeypatch, capsys) -> None:
    captured = {}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeStorageService:
        pass

    def fake_execute(session, request, *, storage_service):
        captured["request"] = request
        captured["storage_service"] = storage_service
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "queued_documents": len(request.document_ids),
                "force": request.force,
                "dry_run": request.dry_run,
                "minimum_review_status": request.minimum_review_status,
            }
        )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-semantic-backfill",
            "--document-id",
            str(uuid4()),
            "--document-id",
            str(uuid4()),
            "--limit",
            "3",
            "--force",
            "--dry-run",
            "--skip-ontology-init",
            "--skip-fact-graphs",
            "--minimum-review-status",
            "approved",
        ],
    )

    runtime_commands.run_semantic_backfill(
        session_factory_func=lambda: lambda: FakeSession(),
        execute_semantic_backfill_func=fake_execute,
        storage_service_factory=FakeStorageService,
    )

    output = json.loads(capsys.readouterr().out.strip())
    request = captured["request"]
    assert request.limit == 3
    assert request.force is True
    assert request.dry_run is True
    assert request.initialize_ontology is False
    assert request.build_fact_graphs is False
    assert request.minimum_review_status == "approved"
    assert isinstance(captured["storage_service"], FakeStorageService)
    assert output["queued_documents"] == 2


def test_replay_search_cli_prints_summary(monkeypatch, capsys) -> None:
    search_request_id = uuid4()
    replay_request_id = uuid4()
    committed = {"value": False}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            committed["value"] = True

    monkeypatch.setattr(sys, "argv", ["docling-system-replay-search", str(search_request_id)])

    runtime_commands.run_replay_search(
        session_factory_func=lambda: lambda: FakeSession(),
        replay_search_request_func=lambda session, request_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "original_request": {"search_request_id": str(request_id)},
                "replay_request": {"search_request_id": str(replay_request_id)},
                "diff": {"overlap_count": 2},
            }
        ),
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert committed["value"] is True
    assert output["original_request"]["search_request_id"] == str(search_request_id)
    assert output["replay_request"]["search_request_id"] == str(replay_request_id)


def test_eval_candidates_cli_prints_summary(monkeypatch, capsys) -> None:
    search_request_id = uuid4()
    captured = {}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-eval-candidates", "--limit", "2", "--include-resolved"],
    )

    runtime_commands.run_eval_candidates(
        session_factory_func=lambda: lambda: FakeSession(),
        list_quality_eval_candidates_func=lambda session, limit=12, include_resolved=False: (
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

    output = json.loads(capsys.readouterr().out.strip())
    assert captured == {"limit": 2, "include_resolved": True}
    assert output[0]["candidate_type"] == "live_search_gap"
    assert output[0]["search_request_id"] == str(search_request_id)


def test_evaluation_data_readiness_cli_writes_output(monkeypatch, capsys, tmp_path) -> None:
    written_path = tmp_path / "reports" / "readiness.json"

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-evaluation-data-readiness",
            "--manual-corpus-path",
            "docs/custom_corpus.yaml",
            "--auto-corpus-path",
            "storage/custom.auto.yaml",
            "--output",
            str(written_path),
            "--compact",
        ],
    )

    runtime_commands.run_evaluation_data_readiness(
        session_factory_func=lambda: lambda: FakeSession(),
        build_evaluation_data_readiness_report_func=lambda session, **kwargs: {
            "schema_name": "evaluation_data_readiness_report",
            "manual_corpus_path": str(kwargs["manual_corpus_path"]),
            "auto_corpus_path": str(kwargs["auto_corpus_path"]),
        },
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["schema_name"] == "evaluation_data_readiness_report"
    assert json.loads(written_path.read_text()) == output


def test_replay_suite_cli_prints_summary(monkeypatch, capsys) -> None:
    replay_run_id = uuid4()
    committed = {"value": False}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            committed["value"] = True

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

    runtime_commands.run_replay_suite(
        session_factory_func=lambda: lambda: FakeSession(),
        run_search_replay_suite_func=lambda session, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "replay_run_id": str(replay_run_id),
                "source_type": payload.source_type,
                "query_count": payload.limit,
                "harness_name": payload.harness_name,
            }
        ),
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert committed["value"] is True
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

    runtime_commands.run_export_ranking_dataset(
        session_factory_func=lambda: lambda: FakeSession(),
        export_ranking_dataset_func=lambda session, limit=200: [
            {"dataset_type": "feedback", "feedback_type": "relevant", "limit": limit},
            {"dataset_type": "replay", "passed": True, "limit": limit},
        ],
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["dataset_type"] == "feedback"
    assert output[0]["limit"] == 5
    assert output[1]["dataset_type"] == "replay"
