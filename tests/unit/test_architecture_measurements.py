from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.architecture_inspection import ARCHITECTURE_MEASUREMENT_SCHEMA_NAME
from app.architecture_measurement_cli import run_report, run_summary
from app.architecture_measurement_contracts import ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME
from app.architecture_measurements import (
    ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME,
    build_architecture_governance_report,
    load_architecture_measurement_history,
    record_architecture_measurement,
    summarize_architecture_measurements,
    write_architecture_governance_report,
)


def _report(error_count: int = 0, contract_count: int = 4) -> dict:
    violation_count = error_count
    return {
        "valid": error_count == 0,
        "violation_count": violation_count,
        "measurement": {
            "schema_name": ARCHITECTURE_MEASUREMENT_SCHEMA_NAME,
            "schema_version": "1.0",
            "severity_counts": {"error": error_count, "info": 0, "warning": 0},
            "non_ignored_violation_count": violation_count,
            "contract_count": contract_count,
            "inspection_rule_count": 2,
            "rule_violation_counts": {
                "rule-a": error_count,
                "rule-b": 0,
            },
            "contract_violation_counts": {
                "contract-a": error_count,
                "contract-b": 0,
            },
            "api_route_count": 20,
            "agent_action_count": 10,
        },
    }


def test_architecture_measurement_history_records_jsonl(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"

    record = record_architecture_measurement(
        _report(),
        history_path=history_path,
        commit_sha="abc123",
    )
    records = load_architecture_measurement_history(history_path)

    assert record["schema_name"] == ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME
    assert record["commit_sha"] == "abc123"
    assert records == [record]
    assert json.loads(history_path.read_text()) == record


def test_architecture_measurement_summary_reports_latest_and_deltas(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.architecture_measurements.current_git_commit_sha",
        lambda _project_root=None: "second",
    )
    history_path = tmp_path / "history.jsonl"
    record_architecture_measurement(
        _report(error_count=2, contract_count=4),
        history_path=history_path,
        commit_sha="first",
    )
    record_architecture_measurement(
        _report(error_count=0, contract_count=6),
        history_path=history_path,
        commit_sha="second",
    )

    summary = summarize_architecture_measurements(history_path)

    assert summary["schema_name"] == ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME
    assert summary["record_count"] == 2
    assert summary["current_commit_sha"] == "second"
    assert summary["latest_recorded_commit_sha"] == "second"
    assert summary["latest_recorded_at"] is not None
    assert summary["is_current"] is True
    assert summary["recording_required"] is False
    assert summary["latest"]["commit_sha"] == "second"
    assert summary["previous"]["commit_sha"] == "first"
    assert summary["deltas"]["non_ignored_violation_count"] == -2
    assert summary["deltas"]["error_count"] == -2
    assert summary["deltas"]["contract_count"] == 2
    assert summary["latest_rule_violation_counts"] == {"rule-a": 0, "rule-b": 0}
    assert summary["latest_contract_violation_counts"] == {
        "contract-a": 0,
        "contract-b": 0,
    }
    assert summary["deltas"]["rule_violation_counts"] == {
        "rule-a": -2,
        "rule-b": 0,
    }
    assert summary["deltas"]["contract_violation_counts"] == {
        "contract-a": -2,
        "contract-b": 0,
    }


def test_architecture_measurement_summary_reports_stale_history(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.architecture_measurements.current_git_commit_sha",
        lambda _project_root=None: "current",
    )
    history_path = tmp_path / "history.jsonl"
    record_architecture_measurement(
        _report(),
        history_path=history_path,
        commit_sha="old",
    )

    summary = summarize_architecture_measurements(history_path)

    assert summary["current_commit_sha"] == "current"
    assert summary["latest_recorded_commit_sha"] == "old"
    assert summary["is_current"] is False
    assert summary["recording_required"] is True


def test_architecture_measurement_summary_handles_legacy_records(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.architecture_measurements.current_git_commit_sha",
        lambda _project_root=None: "current",
    )
    history_path = tmp_path / "history.jsonl"
    legacy_report = _report(error_count=1)
    legacy_report["measurement"].pop("inspection_rule_count")
    legacy_report["measurement"].pop("rule_violation_counts")
    legacy_report["measurement"].pop("contract_violation_counts")
    record_architecture_measurement(
        legacy_report,
        history_path=history_path,
        commit_sha="legacy",
    )
    record_architecture_measurement(
        _report(error_count=2),
        history_path=history_path,
        commit_sha="current",
    )

    summary = summarize_architecture_measurements(history_path)

    assert summary["record_count"] == 2
    assert summary["is_current"] is True
    assert summary["recording_required"] is False
    assert summary["deltas"]["error_count"] == 1
    assert summary["deltas"]["rule_violation_counts"] == {
        "rule-a": 2,
        "rule-b": 0,
    }
    assert summary["deltas"]["contract_violation_counts"] == {
        "contract-a": 2,
        "contract-b": 0,
    }


def test_architecture_measurement_summary_rejects_non_numeric_count_maps(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.jsonl"
    record = record_architecture_measurement(
        _report(),
        history_path=history_path,
        commit_sha="bad",
    )
    record["measurement"]["rule_violation_counts"] = {"rule-a": "1"}
    history_path.write_text(json.dumps(record) + "\n")

    with pytest.raises(ValueError, match="rule_violation_counts.rule-a"):
        summarize_architecture_measurements(history_path)


def test_architecture_measurement_summary_cli_prints_payload(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.architecture_measurements.current_git_commit_sha",
        lambda _project_root=None: "abc123",
    )
    history_path = tmp_path / "history.jsonl"
    record_architecture_measurement(_report(), history_path=history_path, commit_sha="abc123")

    exit_code = run_summary(["--history-path", str(history_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_name"] == ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME
    assert payload["record_count"] == 1
    assert payload["is_current"] is True
    assert payload["recording_required"] is False


def test_architecture_governance_report_wraps_inspection_and_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.architecture_measurements.current_git_commit_sha",
        lambda _project_root=None: "abc123",
    )
    monkeypatch.setattr(
        "app.architecture_measurements.build_architecture_inspection_report",
        lambda *_args, **_kwargs: {
            "schema_name": "architecture_inspection",
            **_report(),
        },
    )
    history_path = tmp_path / "history.jsonl"
    record_architecture_measurement(_report(), history_path=history_path, commit_sha="abc123")

    report = build_architecture_governance_report(history_path=history_path)

    assert report["schema_name"] == ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME
    assert report["valid"] is True
    assert report["violation_count"] == 0
    assert report["current_commit_sha"] == "abc123"
    assert report["latest_recorded_commit_sha"] == "abc123"
    assert report["is_current"] is True
    assert report["recording_required"] is False
    assert report["inspection"]["schema_name"] == "architecture_inspection"
    assert report["measurement_summary"]["record_count"] == 1


def test_architecture_governance_report_cli_writes_json(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.architecture_measurements.current_git_commit_sha",
        lambda _project_root=None: "abc123",
    )
    monkeypatch.setattr(
        "app.architecture_measurements.build_architecture_inspection_report",
        lambda *_args, **_kwargs: {
            "schema_name": "architecture_inspection",
            **_report(),
        },
    )
    history_path = tmp_path / "history.jsonl"
    output_path = tmp_path / "architecture_governance_report.json"
    record_architecture_measurement(_report(), history_path=history_path, commit_sha="abc123")

    exit_code = run_report(
        [
            "--history-path",
            str(history_path),
            "--output-path",
            str(output_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_name"] == ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME
    assert json.loads(output_path.read_text()) == payload


def test_architecture_governance_report_cli_can_gate_invalid_inspection(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.architecture_measurements.current_git_commit_sha",
        lambda _project_root=None: "abc123",
    )
    monkeypatch.setattr(
        "app.architecture_measurements.build_architecture_inspection_report",
        lambda *_args, **_kwargs: {
            "schema_name": "architecture_inspection",
            **_report(error_count=1),
        },
    )
    history_path = tmp_path / "history.jsonl"
    output_path = tmp_path / "architecture_governance_report.json"
    record_architecture_measurement(_report(), history_path=history_path, commit_sha="abc123")

    exit_code = run_report(
        [
            "--history-path",
            str(history_path),
            "--output-path",
            str(output_path),
            "--fail-on-invalid",
        ]
    )

    assert exit_code == 1
    assert json.loads(output_path.read_text())["valid"] is False


def test_write_architecture_governance_report_uses_default_build_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        "app.architecture_measurements.build_architecture_governance_report",
        lambda **_kwargs: {
            "schema_name": ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME,
            "valid": True,
        },
    )

    path = write_architecture_governance_report(project_root=tmp_path)

    assert path == tmp_path / "build/architecture-governance/architecture_governance_report.json"
    assert json.loads(path.read_text())["schema_name"] == ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME
