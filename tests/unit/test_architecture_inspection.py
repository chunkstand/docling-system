from __future__ import annotations

import json

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
    ARCHITECTURE_INSPECTION_SCHEMA_NAME,
    build_architecture_contract_map,
    build_architecture_inspection_report,
    inspect_architecture_contracts,
    run,
)


def test_architecture_contract_map_exposes_machine_readable_boundaries() -> None:
    contract_map = build_architecture_contract_map()
    contract_names = {contract["name"] for contract in contract_map["contracts"]}
    facade_names = {facade["name"] for facade in contract_map["capability_facades"]}

    assert contract_map["schema_name"] == ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME
    assert contract_map["system_style"] == "modular_monolith"
    assert {
        "api_route_capabilities",
        "agent_action_catalog",
        "improvement_case_registry",
        "improvement_case_intake",
    } <= contract_names
    assert {
        "run_lifecycle",
        "retrieval",
        "evaluation",
        "semantics",
        "agent_orchestration",
    } <= facade_names
    assert "docs/architecture_boundaries.md" in contract_map["source_documents"]


def test_architecture_inspection_contracts_are_clean() -> None:
    assert inspect_architecture_contracts() == []


def test_architecture_inspection_report_wraps_map_and_violations() -> None:
    report = build_architecture_inspection_report()

    assert report["schema_name"] == ARCHITECTURE_INSPECTION_SCHEMA_NAME
    assert report["valid"] is True
    assert report["violation_count"] == 0
    assert report["violations"] == []
    assert report["architecture_map"]["schema_name"] == ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME


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
