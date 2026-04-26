from __future__ import annotations

import json
from pathlib import Path

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
    ARCHITECTURE_INSPECTION_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SCHEMA_NAME,
    build_architecture_contract_map,
    build_architecture_inspection_report,
    inspect_architecture_contracts,
    run,
    write_architecture_contract_map,
)


def test_architecture_contract_map_exposes_machine_readable_boundaries() -> None:
    contract_map = build_architecture_contract_map()
    contract_names = {contract["name"] for contract in contract_map["contracts"]}
    facade_names = {facade["name"] for facade in contract_map["capability_facades"]}

    assert contract_map["schema_name"] == ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME
    assert contract_map["system_style"] == "modular_monolith"
    assert "project_root" not in contract_map
    assert {
        "api_route_capabilities",
        "agent_action_catalog",
        "capability_surface_contracts",
        "improvement_case_registry",
        "improvement_case_intake",
        "improvement_case_lifecycle",
        "architecture_decisions",
        "architecture_measurement_history",
    } <= contract_names
    assert {
        "run_lifecycle",
        "retrieval",
        "evaluation",
        "semantics",
        "agent_orchestration",
    } <= facade_names
    assert all(facade["function_count"] > 0 for facade in contract_map["capability_facades"])
    assert "docs/architecture_boundaries.md" in contract_map["source_documents"]
    assert "docs/architecture_decisions.yaml" in contract_map["source_documents"]


def test_architecture_inspection_contracts_are_clean() -> None:
    assert inspect_architecture_contracts() == []


def test_architecture_inspection_report_wraps_map_and_violations() -> None:
    report = build_architecture_inspection_report()

    assert report["schema_name"] == ARCHITECTURE_INSPECTION_SCHEMA_NAME
    assert report["valid"] is True
    assert report["violation_count"] == 0
    assert report["violations"] == []
    assert report["measurement"]["schema_name"] == ARCHITECTURE_MEASUREMENT_SCHEMA_NAME
    assert report["measurement"]["non_ignored_violation_count"] == 0
    assert report["architecture_map"]["schema_name"] == ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME


def test_architecture_inspection_reports_missing_persisted_map(tmp_path: Path) -> None:
    report = build_architecture_inspection_report(map_path=tmp_path / "missing.json")

    assert report["valid"] is False
    assert report["violation_count"] == 1
    assert report["violations"][0]["contract"] == "architecture_contract_map"
    assert report["violations"][0]["severity"] == "error"


def test_architecture_inspection_policy_can_demote_violation(tmp_path: Path) -> None:
    policy_path = tmp_path / "architecture_policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                "schema_name: architecture_inspection_policy",
                'schema_version: "1.0"',
                "default_severity: error",
                "severity_overrides:",
                "  - match: architecture_contract_map.persisted_map",
                "    severity: warning",
            ]
        )
        + "\n"
    )

    report = build_architecture_inspection_report(
        policy_path=policy_path,
        map_path=tmp_path / "missing.json",
    )

    assert report["valid"] is True
    assert report["violation_count"] == 1
    assert report["violations"][0]["severity"] == "warning"


def test_architecture_contract_map_can_be_persisted(tmp_path: Path) -> None:
    map_path = tmp_path / "architecture_contract_map.json"

    written_path = write_architecture_contract_map(map_path)
    payload = json.loads(written_path.read_text())

    assert written_path == map_path
    assert payload == build_architecture_contract_map()
    assert inspect_architecture_contracts(map_path=map_path) == []


def test_architecture_inspection_cli_prints_json_report(capsys) -> None:
    exit_code = run([])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema_name"] == ARCHITECTURE_INSPECTION_SCHEMA_NAME
    assert output["valid"] is True


def test_architecture_inspection_cli_can_print_map_only(capsys) -> None:
    exit_code = run(["--map-only"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema_name"] == ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME
    assert "violations" not in output


def test_architecture_inspection_cli_can_write_map(capsys, tmp_path: Path) -> None:
    map_path = tmp_path / "architecture_contract_map.json"

    exit_code = run(["--write-map", "--map-path", str(map_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema_name"] == "architecture_contract_map_write"
    assert json.loads(map_path.read_text()) == build_architecture_contract_map()
