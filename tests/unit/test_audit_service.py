from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.services.audit import AuditContext, build_integrity_audit


def _timestamp() -> datetime:
    return datetime.now(UTC)


def _context(**overrides) -> AuditContext:
    return AuditContext(
        documents=overrides.get("documents", []),
        runs=overrides.get("runs", []),
        chunks=overrides.get("chunks", []),
        tables=overrides.get("tables", []),
        figures=overrides.get("figures", []),
        evaluations=overrides.get("evaluations", []),
    )


def test_audit_flags_run_count_mismatch(tmp_path: Path) -> None:
    document_id = uuid4()
    run_id = uuid4()
    doc_json = tmp_path / "docling.json"
    doc_yaml = tmp_path / "document.yaml"
    doc_json.write_text("{}")
    doc_yaml.write_text("ok")
    document = SimpleNamespace(id=document_id, active_run_id=run_id, latest_run_id=run_id)
    run = SimpleNamespace(
        id=run_id,
        document_id=document_id,
        status="completed",
        validation_status="passed",
        docling_json_path=str(doc_json),
        yaml_path=str(doc_yaml),
        chunk_count=2,
        table_count=0,
        figure_count=0,
        failure_stage=None,
        failure_artifact_path=None,
    )
    chunk = SimpleNamespace(run_id=run_id)
    evaluation = SimpleNamespace(run_id=run_id, created_at=_timestamp())

    audit = build_integrity_audit(
        _context(documents=[document], runs=[run], chunks=[chunk], evaluations=[evaluation])
    )

    assert audit["violation_count"] == 1
    assert audit["violations"][0]["code"] == "run_chunk_count_mismatch"


def test_audit_flags_missing_latest_evaluation_for_completed_latest_run(tmp_path: Path) -> None:
    document_id = uuid4()
    run_id = uuid4()
    doc_json = tmp_path / "docling.json"
    doc_yaml = tmp_path / "document.yaml"
    doc_json.write_text("{}")
    doc_yaml.write_text("ok")
    document = SimpleNamespace(id=document_id, active_run_id=run_id, latest_run_id=run_id)
    run = SimpleNamespace(
        id=run_id,
        document_id=document_id,
        status="completed",
        validation_status="passed",
        docling_json_path=str(doc_json),
        yaml_path=str(doc_yaml),
        chunk_count=0,
        table_count=0,
        figure_count=0,
        failure_stage=None,
        failure_artifact_path=None,
    )

    audit = build_integrity_audit(_context(documents=[document], runs=[run]))

    assert audit["violation_counts_by_code"]["completed_latest_run_missing_evaluation"] == 1


def test_audit_flags_missing_table_and_figure_artifacts() -> None:
    document_id = uuid4()
    run_id = uuid4()
    table = SimpleNamespace(
        document_id=document_id,
        run_id=run_id,
        json_path="/tmp/missing-table.json",
        yaml_path="/tmp/missing-table.yaml",
    )
    figure = SimpleNamespace(
        document_id=document_id,
        run_id=run_id,
        json_path="/tmp/missing-figure.json",
        yaml_path="/tmp/missing-figure.yaml",
    )

    audit = build_integrity_audit(_context(tables=[table], figures=[figure]))
    codes = {item["code"] for item in audit["violations"]}

    assert "table_missing_json_artifact" in codes
    assert "table_missing_yaml_artifact" in codes
    assert "figure_missing_json_artifact" in codes
    assert "figure_missing_yaml_artifact" in codes


def test_audit_flags_invalid_failure_artifact_schema_and_unknown_stage(tmp_path: Path) -> None:
    document_id = uuid4()
    run_id = uuid4()
    failure_artifact = tmp_path / "failure.json"
    failure_artifact.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "document_id": str(document_id),
                "run_id": str(run_id),
                "status": "failed",
            }
        )
    )
    run = SimpleNamespace(
        id=run_id,
        document_id=document_id,
        status="failed",
        validation_status="failed",
        docling_json_path=None,
        yaml_path=None,
        chunk_count=None,
        table_count=None,
        figure_count=None,
        failure_stage="mystery_stage",
        failure_artifact_path=str(failure_artifact),
    )

    audit = build_integrity_audit(_context(runs=[run]))
    codes = {item["code"] for item in audit["violations"]}

    assert "failed_run_unknown_failure_stage" in codes
    assert "failed_run_failure_artifact_missing_fields" in codes
