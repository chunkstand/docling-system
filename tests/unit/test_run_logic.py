from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.db.models import Document, DocumentRun
from app.services.runs import claim_next_run, finalize_run_failure, is_retryable_error, process_run
from app.services.storage import StorageService
from app.services.validation import ValidationReport


def test_value_errors_are_terminal() -> None:
    assert is_retryable_error(ValueError("bad input")) is False


def test_unknown_errors_are_retryable() -> None:
    assert is_retryable_error(RuntimeError("transient")) is True


def test_process_run_uses_prior_active_run_for_evaluation_baseline(
    monkeypatch, tmp_path: Path
) -> None:
    document_id = uuid4()
    candidate_run_id = uuid4()
    prior_active_run_id = uuid4()
    drifted_active_run_id = uuid4()
    source_path = tmp_path / "report.pdf"
    source_path.write_bytes(b"%PDF-1.7\n")

    run = SimpleNamespace(id=candidate_run_id, document_id=document_id)
    document = SimpleNamespace(
        id=document_id,
        source_path=str(source_path),
        active_run_id=prior_active_run_id,
        latest_run_id=prior_active_run_id,
    )
    parsed = SimpleNamespace(
        raw_table_segments=[],
        chunks=[],
        tables=[],
        figures=[],
        title="Report",
        page_count=1,
    )

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == candidate_run_id:
                return run
            if model is Document and key == document_id:
                return document
            return None

        def rollback(self) -> None:
            return None

    observed: dict[str, object | None] = {}

    monkeypatch.setattr("app.services.runs.heartbeat_run", lambda session, run: None)
    monkeypatch.setattr("app.services.runs.increment", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.services.runs._apply_embeddings", lambda parsed, embedding_provider, run: None
    )
    monkeypatch.setattr(
        "app.services.runs._build_lineage_assignments", lambda session, document, parsed: {}
    )
    monkeypatch.setattr(
        "app.services.runs._persist_parsed_artifacts",
        lambda storage_service, document, run, parsed: (
            tmp_path / "docling.json",
            tmp_path / "document.yaml",
        ),
    )
    monkeypatch.setattr(
        "app.services.runs._replace_run_chunks", lambda session, document, run, parsed: None
    )
    monkeypatch.setattr(
        "app.services.runs._replace_run_tables",
        lambda session, document, run, parsed, storage_service, lineage_assignments: None,
    )
    monkeypatch.setattr(
        "app.services.runs._replace_run_figures",
        lambda session, document, run, parsed, storage_service: None,
    )
    monkeypatch.setattr(
        "app.services.runs._mark_run_persisted",
        lambda session, document, run, parsed, json_path, yaml_path: setattr(
            document,
            "active_run_id",
            drifted_active_run_id,
        ),
    )
    monkeypatch.setattr("app.services.runs._mark_run_validating", lambda session, run: None)
    monkeypatch.setattr(
        "app.services.runs.validate_persisted_run",
        lambda session, document, run, parsed: ValidationReport(
            passed=True, summary="ok", details={}
        ),
    )
    monkeypatch.setattr(
        "app.services.runs.ensure_auto_evaluation_fixture",
        lambda session, document, run, title=None: observed.update(
            {"auto_fixture_title": title, "auto_fixture_run_id": run.id}
        ),
    )

    def fake_evaluate_run(session, document, run, baseline_run_id=None):
        observed["baseline_run_id"] = baseline_run_id
        return SimpleNamespace(status="completed", fixture_name="fixture")

    monkeypatch.setattr("app.services.runs.evaluate_run", fake_evaluate_run)
    monkeypatch.setattr(
        "app.services.runs.finalize_run_success",
        lambda session, document, run, parsed, report, **kwargs: setattr(
            document, "active_run_id", run.id
        ),
    )

    process_run(
        session=FakeSession(),
        run_id=candidate_run_id,
        storage_service=object(),
        parser=SimpleNamespace(parse_pdf=lambda _: parsed),
        embedding_provider=None,
    )

    assert observed["baseline_run_id"] == prior_active_run_id
    assert observed["auto_fixture_title"] == "Report"
    assert observed["auto_fixture_run_id"] == candidate_run_id


def test_finalize_run_failure_writes_replayable_failure_artifact(tmp_path: Path) -> None:
    document_id = uuid4()
    run_id = uuid4()
    storage_service = StorageService(storage_root=tmp_path / "storage")
    run = SimpleNamespace(
        id=run_id,
        document_id=document_id,
        attempts=3,
        status="processing",
        validation_results_json={},
        failure_artifact_path=None,
        failure_stage=None,
    )
    document = SimpleNamespace(
        id=document_id,
        source_filename="report.pdf",
        source_path=str(tmp_path / "report.pdf"),
    )

    class FakeSession:
        def __init__(self) -> None:
            self.committed = False

        def commit(self) -> None:
            self.committed = True

        def query(self, *_args, **_kwargs):
            class FakeQuery:
                def filter(self, *_args, **_kwargs):
                    return self

                def update(self, *_args, **_kwargs):
                    return 0

            return FakeQuery()

    session = FakeSession()
    finalize_run_failure(
        session,
        run,
        RuntimeError("boom"),
        failure_stage="parse",
        storage_service=storage_service,
        document=document,
    )

    assert session.committed is True
    assert run.failure_stage == "parse"
    assert run.failure_artifact_path is not None
    artifact_path = Path(run.failure_artifact_path)
    assert artifact_path.exists() is True
    artifact = artifact_path.read_text()
    assert "boom" in artifact
    assert "parse" in artifact


def test_claim_next_run_limits_worker_lease_query_to_one_row() -> None:
    captured = {}

    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeSession:
        def execute(self, query):
            captured["sql"] = str(
                query.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )
            return FakeResult()

        def rollback(self) -> None:
            captured["rolled_back"] = True

    run = claim_next_run(FakeSession(), "worker-1")

    assert run is None
    assert captured["rolled_back"] is True
    assert " LIMIT 1" in captured["sql"]
    assert "FOR UPDATE SKIP LOCKED" in captured["sql"]
