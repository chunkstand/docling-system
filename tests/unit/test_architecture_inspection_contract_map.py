from __future__ import annotations

import json
from pathlib import Path

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
    build_architecture_contract_map,
    build_architecture_inspection_report,
    inspect_architecture_contracts,
    write_architecture_contract_map,
)
from app.architecture_inspection_types import ARCHITECTURE_SEVERITIES
from app.architecture_measurement_contracts import (
    ARCHITECTURE_GOVERNANCE_REPORT_FIELDS,
    ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_DELTA_FIELDS,
    ARCHITECTURE_MEASUREMENT_FIELDS,
    ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SUMMARY_FIELDS,
)
from app.architecture_quality_contracts import (
    ARCHITECTURE_QUALITY_REPORT_FIELDS,
    ARCHITECTURE_QUALITY_SUMMARY_FIELDS,
)
from tests.unit.architecture_inspection_test_support import (
    EXPECTED_ARCHITECTURE_RULE_IDS,
)


def test_architecture_contract_map_exposes_machine_readable_boundaries() -> None:
    contract_map = build_architecture_contract_map()
    contract_names = {contract["name"] for contract in contract_map["contracts"]}
    facade_names = {facade["name"] for facade in contract_map["capability_facades"]}
    rule_ids = {rule["rule_id"] for rule in contract_map["inspection_rules"]}
    measurement_contract = next(
        contract
        for contract in contract_map["contracts"]
        if contract["name"] == "architecture_measurement_history"
    )
    intake_contract = next(
        contract
        for contract in contract_map["contracts"]
        if contract["name"] == "improvement_case_intake"
    )
    agent_action_contract = next(
        contract
        for contract in contract_map["contracts"]
        if contract["name"] == "agent_action_catalog"
    )
    quality_contract = next(
        contract
        for contract in contract_map["contracts"]
        if contract["name"] == "architecture_quality_report"
    )

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
        "architecture_quality_report",
    } <= contract_names
    assert all(contract.get("decision_ids") for contract in contract_map["contracts"])
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
    assert EXPECTED_ARCHITECTURE_RULE_IDS <= rule_ids
    assert {
        (row["source"], row["source_kind"], row["requires_db_session"])
        for row in intake_contract["import_source_specs"]
    } == {
        ("hygiene", "workspace", False),
        ("architecture-governance-report", "file", False),
        ("architecture-quality-report", "file", False),
        ("agent-trace-review-report", "file", False),
        ("eval-failure-cases", "database", True),
        ("failed-agent-tasks", "database", True),
        ("failed-agent-verifications", "database", True),
    }
    assert intake_contract["source"] == "app.services.improvement_case_contracts"
    assert agent_action_contract["source"] == "app.services.agent_actions.contracts"
    assert measurement_contract["schema_name"] == ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME
    assert measurement_contract["history_path"] == "storage/architecture_inspections/history.jsonl"
    assert measurement_contract["measurement_fields"] == list(ARCHITECTURE_MEASUREMENT_FIELDS)
    assert measurement_contract["summary_fields"] == list(ARCHITECTURE_MEASUREMENT_SUMMARY_FIELDS)
    assert measurement_contract["delta_fields"] == list(ARCHITECTURE_MEASUREMENT_DELTA_FIELDS)
    assert measurement_contract["report_schema_name"] == ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME
    assert measurement_contract["report_fields"] == list(ARCHITECTURE_GOVERNANCE_REPORT_FIELDS)
    assert quality_contract["report_fields"] == list(ARCHITECTURE_QUALITY_REPORT_FIELDS)
    assert quality_contract["summary_fields"] == list(ARCHITECTURE_QUALITY_SUMMARY_FIELDS)
    assert (
        measurement_contract["ci_report_path"]
        == "build/architecture-governance/architecture_governance_report.json"
    )
    assert (
        measurement_contract["ci_history_path"]
        == "build/architecture-governance/architecture_measurement_history.jsonl"
    )
    assert measurement_contract["ci_workflow"] == ".github/workflows/architecture-governance.yml"
    workflow_path = Path(measurement_contract["ci_workflow"])
    workflow_text = workflow_path.read_text()
    assert workflow_path.is_file()
    assert "docling-system-architecture-governance-report" in workflow_text
    assert "--record-current" in workflow_text
    assert measurement_contract["ci_history_path"] in workflow_text
    assert "docling-system-improvement-case-import" in workflow_text
    assert "--source architecture-governance-report" in workflow_text
    assert "--source-path-for architecture-governance-report=" in workflow_text
    assert "--dry-run" in workflow_text
    assert all(rule["contract"] for rule in contract_map["inspection_rules"])
    assert all(rule["description"] for rule in contract_map["inspection_rules"])
    assert all(
        rule["default_severity"] in ARCHITECTURE_SEVERITIES
        for rule in contract_map["inspection_rules"]
    )
    assert all("checker" not in rule for rule in contract_map["inspection_rules"])


def test_architecture_inspection_reports_missing_persisted_map(tmp_path: Path) -> None:
    report = build_architecture_inspection_report(map_path=tmp_path / "missing.json")

    assert report["valid"] is False
    assert report["violation_count"] == 1
    assert report["violations"][0]["contract"] == "architecture_contract_map"
    assert report["violations"][0]["severity"] == "error"
    assert (
        report["measurement"]["rule_violation_counts"]["architecture-contract-map-drift"] == 1
    )
    assert (
        report["measurement"]["contract_violation_counts"]["architecture_contract_map"] == 1
    )


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


def test_architecture_inspection_policy_can_demote_violation_by_rule_id(
    tmp_path: Path,
) -> None:
    policy_path = tmp_path / "architecture_policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                "schema_name: architecture_inspection_policy",
                'schema_version: "1.0"',
                "default_severity: error",
                "severity_overrides:",
                "  - match: rule.architecture-contract-map-drift",
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
    assert report["violations"][0]["rule_id"] == "architecture-contract-map-drift"
    assert report["violations"][0]["severity"] == "warning"


def test_architecture_contract_map_can_be_persisted(tmp_path: Path) -> None:
    map_path = tmp_path / "architecture_contract_map.json"

    written_path = write_architecture_contract_map(map_path)
    payload = json.loads(written_path.read_text())

    assert written_path == map_path
    assert payload == build_architecture_contract_map()
    assert inspect_architecture_contracts(map_path=map_path) == []
