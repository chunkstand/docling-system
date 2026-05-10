from __future__ import annotations

import importlib
import json
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli import (
    run_improvement_case_list,
    run_improvement_case_record,
    run_improvement_case_summary,
    run_improvement_case_validate,
)
from app.improvement_case_intake_cli import run_import as run_improvement_case_import


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


def test_improvement_case_cli_entrypoint_and_help_contracts(monkeypatch, capsys) -> None:
    scripts = tomllib.loads(Path("pyproject.toml").read_text())["project"]["scripts"]
    expected_entrypoints = {
        "docling-system-improvement-case-validate": (
            "app.cli:run_improvement_case_validate",
            run_improvement_case_validate,
        ),
        "docling-system-improvement-case-list": (
            "app.cli:run_improvement_case_list",
            run_improvement_case_list,
        ),
        "docling-system-improvement-case-summary": (
            "app.cli:run_improvement_case_summary",
            run_improvement_case_summary,
        ),
        "docling-system-improvement-case-record": (
            "app.cli:run_improvement_case_record",
            run_improvement_case_record,
        ),
    }
    for script_name, (entrypoint, expected_runner) in expected_entrypoints.items():
        assert scripts[script_name] == entrypoint
        module_name, attr_name = entrypoint.split(":", 1)
        resolved_runner = getattr(importlib.import_module(module_name), attr_name)
        assert resolved_runner is expected_runner
        assert resolved_runner.__name__ == expected_runner.__name__

    help_cases = [
        (
            run_improvement_case_validate,
            ["docling-system-improvement-case-validate", "--help"],
            ["Validate the improvement case registry.", "--path"],
        ),
        (
            run_improvement_case_list,
            ["docling-system-improvement-case-list", "--help"],
            ["List improvement cases.", "--status", "--cause-class", "--artifact-type"],
        ),
        (
            run_improvement_case_summary,
            ["docling-system-improvement-case-summary", "--help"],
            ["Summarize improvement cases.", "--path"],
        ),
        (
            run_improvement_case_record,
            ["docling-system-improvement-case-record", "--help"],
            [
                "Record one improvement case.",
                "--title",
                "--observed-failure",
                "--verification-command",
            ],
        ),
    ]
    for runner, argv, expected_tokens in help_cases:
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as exc_info:
            runner()
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        for token in expected_tokens:
            assert token in output


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

    monkeypatch.setattr(
        "app.improvement_case_intake_cli.run_improvement_case_import_workflow",
        fake_import_workflow,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-improvement-case-import",
            "--path",
            str(registry_path),
            "--source",
            "architecture-governance-report",
            "--limit",
            "5",
            "--workflow-version",
            "improvement_v2",
            "--source-path-for",
            "architecture-governance-report=build/architecture-governance/architecture_governance_report.json",
            "--dry-run",
        ],
    )

    run_improvement_case_import()

    output = json.loads(capsys.readouterr().out.strip())
    assert captured == {
        "source": "architecture-governance-report",
        "limit": 5,
        "workflow_version": "improvement_v2",
        "path": str(registry_path),
        "source_path": None,
        "source_paths": {
            "architecture-governance-report": (
                "build/architecture-governance/architecture_governance_report.json"
            )
        },
        "dry_run": True,
    }
    assert output["imported_count"] == 1
    assert output["imported"][0]["source_type"] == "hygiene_finding"


def test_improvement_case_import_cli_rejects_malformed_source_path_for(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-improvement-case-import",
            "--source-path-for",
            "architecture-governance-report",
        ],
    )

    with pytest.raises(SystemExit, match="--source-path-for must use SOURCE=PATH"):
        run_improvement_case_import()


def test_improvement_case_import_cli_rejects_duplicate_source_path_for(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-improvement-case-import",
            "--source-path-for",
            "architecture-governance-report=first.json",
            "--source-path-for",
            "architecture-governance-report=second.json",
        ],
    )

    with pytest.raises(SystemExit, match="Duplicate --source-path-for source"):
        run_improvement_case_import()


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
