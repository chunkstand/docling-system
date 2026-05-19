from __future__ import annotations

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
    ARCHITECTURE_INSPECTION_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SCHEMA_NAME,
    build_architecture_inspection_report,
    inspect_architecture_contracts,
)
from app.architecture_inspection_rules import (
    build_architecture_rule_manifest,
    list_architecture_rules,
)
from tests.unit.architecture_inspection_test_support import (
    EXPECTED_ARCHITECTURE_RULE_IDS,
)


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
    assert all(row["default_severity"] for row in manifest)


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
