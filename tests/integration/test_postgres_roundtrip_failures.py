from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest

from tests.integration.pdf_fixtures import valid_test_pdf_bytes
from tests.integration.postgres_roundtrip_support import (
    FailingParser,
    StubParser,
    _build_parsed_document,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_failed_reprocess_does_not_replace_active_run(postgres_integration_harness) -> None:
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    original_run_id = UUID(create_response.json()["run_id"])

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    reprocess_response = client.post(f"/documents/{document_id}/reprocess")
    assert reprocess_response.status_code == 202
    failed_run_id = UUID(reprocess_response.json()["run_id"])
    assert failed_run_id != original_run_id

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document(title=None)))

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["active_run_id"] == str(original_run_id)
    assert detail["latest_run_id"] == str(failed_run_id)
    assert detail["latest_validation_status"] == "failed"
    assert detail["latest_run_promoted"] is False
    assert detail["latest_error_message"] == "Validation failed."

    runs_response = client.get(f"/documents/{document_id}/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    failed_run = next(run for run in runs if run["run_id"] == str(failed_run_id))
    assert failed_run["status"] == "failed"
    assert failed_run["failure_stage"] == "validation"
    assert failed_run["has_failure_artifact"] is True
    assert failed_run["is_active_run"] is False

    failure_artifact_response = client.get(f"/runs/{failed_run_id}/failure-artifact")
    assert failure_artifact_response.status_code == 200
    failure_artifact = failure_artifact_response.json()
    assert failure_artifact["failure_stage"] == "validation"
    assert failure_artifact["error_message"] == "Validation failed."

    search_response = client.post(
        "/search",
        json={"query": "integration threshold", "mode": "keyword", "limit": 5},
    )
    assert search_response.status_code == 200
    assert search_response.json()
    assert all(result["run_id"] == str(original_run_id) for result in search_response.json())


def test_corrupted_artifact_during_validation_does_not_promote_run(
    monkeypatch,
    postgres_integration_harness,
) -> None:
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    runs_module = __import__("app.services.runs", fromlist=["_mark_run_validating"])
    original_mark_run_validating = runs_module._mark_run_validating

    def corrupting_mark_run_validating(session, run) -> None:
        original_mark_run_validating(session, run)
        assert run.docling_json_path is not None
        Path(run.docling_json_path).write_text('{"corrupted": true}')

    monkeypatch.setattr("app.services.runs._mark_run_validating", corrupting_mark_run_validating)

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == run_id

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["active_run_id"] is None
    assert detail["latest_run_id"] == str(run_id)
    assert detail["latest_validation_status"] == "failed"
    assert detail["latest_run_promoted"] is False
    assert detail["latest_error_message"] == "Validation failed."

    runs_response = client.get(f"/documents/{document_id}/runs")
    assert runs_response.status_code == 200
    failed_run = next(run for run in runs_response.json() if run["run_id"] == str(run_id))
    assert failed_run["status"] == "failed"
    assert failed_run["failure_stage"] == "validation"

    failure_artifact_response = client.get(f"/runs/{run_id}/failure-artifact")
    assert failure_artifact_response.status_code == 200
    failure_artifact = failure_artifact_response.json()
    assert failure_artifact["failure_stage"] == "validation"
    assert failure_artifact["error_message"] == "Validation failed."


def test_terminal_parse_failure_reports_failed_validation_status(
    postgres_integration_harness,
) -> None:
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        FailingParser(ValueError("parse exploded"))
    )
    assert processed_run_id == run_id

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["active_run_id"] is None
    assert detail["latest_run_id"] == str(run_id)
    assert detail["latest_validation_status"] == "failed"
    assert detail["latest_run_promoted"] is False
    assert detail["latest_error_message"] == "parse exploded"

    runs_response = client.get(f"/documents/{document_id}/runs")
    assert runs_response.status_code == 200
    failed_run = next(run for run in runs_response.json() if run["run_id"] == str(run_id))
    assert failed_run["status"] == "failed"
    assert failed_run["failure_stage"] == "parse"
    assert failed_run["validation_status"] == "failed"

    failure_artifact_response = client.get(f"/runs/{run_id}/failure-artifact")
    assert failure_artifact_response.status_code == 200
    failure_artifact = failure_artifact_response.json()
    assert failure_artifact["failure_stage"] == "parse"
    assert failure_artifact["error_message"] == "parse exploded"
    assert failure_artifact["validation_status"] == "failed"

    quality_response = client.get("/quality/summary")
    assert quality_response.status_code == 200
    assert quality_response.json()["failed_run_count"] == 1
