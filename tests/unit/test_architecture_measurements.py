from __future__ import annotations

import json
from pathlib import Path

from app.architecture_inspection import ARCHITECTURE_MEASUREMENT_SCHEMA_NAME
from app.architecture_measurement_cli import run_summary
from app.architecture_measurements import (
    ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME,
    load_architecture_measurement_history,
    record_architecture_measurement,
    summarize_architecture_measurements,
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


def test_architecture_measurement_summary_reports_latest_and_deltas(tmp_path: Path) -> None:
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


def test_architecture_measurement_summary_cli_prints_payload(
    capsys,
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.jsonl"
    record_architecture_measurement(_report(), history_path=history_path, commit_sha="abc123")

    exit_code = run_summary(["--history-path", str(history_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_name"] == ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME
    assert payload["record_count"] == 1
