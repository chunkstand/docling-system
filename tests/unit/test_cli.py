from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli import run_audit, run_eval_run, run_ingest_file


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
