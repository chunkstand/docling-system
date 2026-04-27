from __future__ import annotations

import json
from pathlib import Path

import pytest

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
from app.architecture_inspection_rules import (
    ArchitectureInspectionContext,
    build_architecture_rule_manifest,
    list_architecture_rules,
)
from app.architecture_inspection_types import (
    ARCHITECTURE_SEVERITIES,
    ArchitectureRule,
    ArchitectureViolation,
)
from app.architecture_measurement_contracts import (
    ARCHITECTURE_GOVERNANCE_REPORT_FIELDS,
    ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_DELTA_FIELDS,
    ARCHITECTURE_MEASUREMENT_FIELDS,
    ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SUMMARY_FIELDS,
)

EXPECTED_ARCHITECTURE_RULE_IDS = {
    "agent-action-catalog-contracts",
    "api-bootstrap-no-feature-routes",
    "api-bootstrap-no-feature-service-imports",
    "api-route-capability-contracts",
    "architecture-contract-map-drift",
    "architecture-decision-contracts",
    "architecture-doc-required-tokens",
    "boundary-modules-no-orm-model-imports",
    "boundary-modules-use-capability-facades",
    "capability-surface-contracts",
    "cli-delegates-improvement-intake",
    "service-layer-no-api-imports",
    "service-layer-no-private-service-imports",
}


def _write_python(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def _rule(rule_id: str) -> ArchitectureRule:
    return next(rule for rule in list_architecture_rules() if rule.rule_id == rule_id)


def _inspection_context(project_root: Path) -> ArchitectureInspectionContext:
    return ArchitectureInspectionContext(
        project_root=project_root,
        expected_contracts=(),
        current_map={},
        map_path=None,
        default_map_path=Path("docs") / "architecture_contract_map.json",
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
    assert measurement_contract["schema_name"] == ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME
    assert measurement_contract["history_path"] == "storage/architecture_inspections/history.jsonl"
    assert measurement_contract["measurement_fields"] == list(ARCHITECTURE_MEASUREMENT_FIELDS)
    assert measurement_contract["summary_fields"] == list(ARCHITECTURE_MEASUREMENT_SUMMARY_FIELDS)
    assert measurement_contract["delta_fields"] == list(ARCHITECTURE_MEASUREMENT_DELTA_FIELDS)
    assert measurement_contract["report_schema_name"] == ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME
    assert measurement_contract["report_fields"] == list(ARCHITECTURE_GOVERNANCE_REPORT_FIELDS)
    assert (
        measurement_contract["ci_report_path"]
        == "build/architecture-governance/architecture_governance_report.json"
    )
    assert measurement_contract["ci_workflow"] == ".github/workflows/architecture-governance.yml"
    workflow_path = Path(measurement_contract["ci_workflow"])
    assert workflow_path.is_file()
    assert "docling-system-architecture-governance-report" in workflow_path.read_text()
    assert all(rule["contract"] for rule in contract_map["inspection_rules"])
    assert all(rule["description"] for rule in contract_map["inspection_rules"])
    assert all(
        rule["default_severity"] in ARCHITECTURE_SEVERITIES
        for rule in contract_map["inspection_rules"]
    )
    assert all("checker" not in rule for rule in contract_map["inspection_rules"])


def test_architecture_rule_registry_exposes_stable_manifest() -> None:
    rules = list_architecture_rules()
    manifest = build_architecture_rule_manifest()
    rule_ids = [rule.rule_id for rule in rules]

    assert set(rule_ids) == EXPECTED_ARCHITECTURE_RULE_IDS
    assert len(rule_ids) == len(set(rule_ids))
    assert [row["rule_id"] for row in manifest] == rule_ids
    assert all(row["source_path"] for row in manifest)
    assert all(row["contract"] for row in manifest)
    assert all(row["description"] for row in manifest)
    assert all(row["default_severity"] in ARCHITECTURE_SEVERITIES for row in manifest)


def test_architecture_rule_rejects_mismatched_violation_contract() -> None:
    rule = ArchitectureRule(
        rule_id="test-rule",
        contract="expected_contract",
        description="Test rule.",
        source_path="tests/unit/test_architecture_inspection.py",
        checker=lambda _context: [
            ArchitectureViolation(
                contract="other_contract",
                field="field",
                message="wrong contract",
            )
        ],
    )

    with pytest.raises(ValueError, match="expected_contract"):
        rule.check(None)


def test_architecture_rule_rejects_mismatched_nested_rule_id() -> None:
    rule = ArchitectureRule(
        rule_id="test-rule",
        contract="expected_contract",
        description="Test rule.",
        source_path="tests/unit/test_architecture_inspection.py",
        checker=lambda _context: [
            ArchitectureViolation(
                contract="expected_contract",
                field="field",
                message="wrong rule",
                rule_id="other-rule",
            )
        ],
    )

    with pytest.raises(ValueError, match="other-rule"):
        rule.check(None)


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
    assert report["measurement"]["inspection_rule_count"] == len(
        report["architecture_map"]["inspection_rules"]
    )
    assert set(report["measurement"]["rule_violation_counts"]) == {
        rule["rule_id"]
        for rule in report["architecture_map"]["inspection_rules"]
    }
    assert set(report["measurement"]["contract_violation_counts"]) == {
        contract["name"]
        for contract in report["architecture_map"]["contracts"]
    } | {
        rule["contract"]
        for rule in report["architecture_map"]["inspection_rules"]
    }
    assert all(count == 0 for count in report["measurement"]["rule_violation_counts"].values())
    assert report["architecture_map"]["schema_name"] == ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME


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


def test_architecture_rules_match_module_boundaries_not_name_prefixes(
    tmp_path: Path,
) -> None:
    context = _inspection_context(tmp_path)
    _write_python(
        tmp_path / "app/api/main.py",
        "import app.services_extra\n",
    )
    _write_python(
        tmp_path / "app/services/safe.py",
        "\n".join(
            [
                "import app.api.mainframe",
                "from app.api.routers_extra import helper",
                "from app.services_extra.helpers import _private_helper",
            ]
        )
        + "\n",
    )

    assert _rule("api-bootstrap-no-feature-service-imports").check(context) == []
    assert _rule("service-layer-no-api-imports").check(context) == []
    assert _rule("service-layer-no-private-service-imports").check(context) == []

    _write_python(
        tmp_path / "app/api/main.py",
        "from app.services.documents import list_documents\n",
    )
    _write_python(
        tmp_path / "app/services/unsafe.py",
        "\n".join(
            [
                "import app.api.main",
                "from app.api.routers.documents import router",
                "from app.services.documents import _private_helper",
            ]
        )
        + "\n",
    )

    assert {
        violation.symbol
        for violation in _rule("api-bootstrap-no-feature-service-imports").check(context)
    } == {"app.services.documents"}
    assert {
        violation.symbol
        for violation in _rule("service-layer-no-api-imports").check(context)
    } == {"app.api.main", "app.api.routers.documents"}
    private_import_violations = _rule("service-layer-no-private-service-imports").check(context)
    assert {violation.symbol for violation in private_import_violations} == {
        "app.services.documents._private_helper"
    }
    assert {violation.rule_id for violation in private_import_violations} == {
        "service-layer-no-private-service-imports"
    }


def test_cli_improvement_intake_rule_uses_ast_not_substring_scan(
    tmp_path: Path,
) -> None:
    rule = _rule("cli-delegates-improvement-intake")
    context = _inspection_context(tmp_path)
    _write_python(
        tmp_path / "app/cli.py",
        "\n".join(
            [
                "# collect_hygiene_finding_observations is only prose here.",
                'HELP = "import_improvement_case_observations"',
                'safe = _lazy_service_attr("app.services.improvement_cases", "load_registry")',
                "from app.services.other import collect_hygiene_finding_observations",
                (
                    'also_safe = _lazy_service_attr("app.services.other", '
                    '"import_improvement_case_observations")'
                ),
            ]
        )
        + "\n",
    )

    assert rule.check(context) == []

    _write_python(
        tmp_path / "app/cli.py",
        "\n".join(
            [
                "from app.services.improvement_cases import (",
                "    collect_hygiene_finding_observations,",
                ")",
                "bad = _lazy_service_attr(",
                '    "app.services.improvement_cases",',
                '    "import_improvement_case_observations",',
                ")",
            ]
        )
        + "\n",
    )

    assert {
        violation.symbol
        for violation in rule.check(context)
    } == {
        "app.services.improvement_cases.collect_hygiene_finding_observations",
        "app.services.improvement_cases.import_improvement_case_observations",
    }
    assert {violation.rule_id for violation in rule.check(context)} == {
        "cli-delegates-improvement-intake"
    }
