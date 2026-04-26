from __future__ import annotations

import json
from pathlib import Path

from app.architecture_decisions import (
    ARCHITECTURE_DECISION_MAP_SCHEMA_NAME,
    ARCHITECTURE_DECISION_SCHEMA_NAME,
    build_architecture_decision_map,
    run,
    validate_architecture_decisions,
    write_architecture_decision_map,
)
from app.architecture_inspection import build_architecture_contract_map


def _architecture_contract_names() -> tuple[str, ...]:
    return tuple(
        str(contract["name"])
        for contract in build_architecture_contract_map()["contracts"]
    )


def test_architecture_decision_map_links_major_contracts() -> None:
    payload = build_architecture_decision_map()
    contract_links = {
        row["contract"]: set(row["decision_ids"])
        for row in payload["contract_decision_links"]
    }

    assert payload["schema_name"] == ARCHITECTURE_DECISION_MAP_SCHEMA_NAME
    assert payload["decision_count"] >= 9
    assert set(_architecture_contract_names()) <= set(contract_links)
    assert "ADR-0009" in contract_links["architecture_decisions"]


def test_architecture_decision_validation_accepts_current_repo() -> None:
    assert validate_architecture_decisions(
        expected_contracts=_architecture_contract_names(),
    ) == []


def test_architecture_decision_validation_reports_missing_registry(tmp_path: Path) -> None:
    issues = validate_architecture_decisions(
        registry_path=tmp_path / "missing.yaml",
        map_path=tmp_path / "missing.json",
    )

    assert any(issue.contract == "architecture_decisions" for issue in issues)
    assert any(issue.field == "registry" for issue in issues)


def test_architecture_decision_validation_reports_missing_contract_link(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "architecture_decisions.yaml"
    map_path = tmp_path / "architecture_decision_map.json"
    registry_path.write_text(
        "\n".join(
            [
                "schema_name: architecture_decisions",
                'schema_version: "1.0"',
                "decisions:",
                "  - id: ADR-9001",
                "    status: accepted",
                '    date: "2026-04-26"',
                "    title: Partial decision coverage",
                "    context: Test fixture.",
                "    decision: Test fixture.",
                "    consequences:",
                "      - Test consequence.",
                "    linked_contracts:",
                "      - api_route_capabilities",
                "    linked_sources:",
                "      - README.md",
            ]
        )
        + "\n"
    )
    write_architecture_decision_map(map_path, registry_path=registry_path)

    issues = validate_architecture_decisions(
        registry_path=registry_path,
        map_path=map_path,
        expected_contracts=("api_route_capabilities", "agent_action_catalog"),
    )

    assert any(issue.field == "linked_contracts" for issue in issues)
    assert any(issue.symbol == "agent_action_catalog" for issue in issues)


def test_architecture_decision_validation_reports_stale_persisted_map(
    tmp_path: Path,
) -> None:
    map_path = tmp_path / "architecture_decision_map.json"
    map_path.write_text(json.dumps({"schema_name": ARCHITECTURE_DECISION_MAP_SCHEMA_NAME}) + "\n")

    issues = validate_architecture_decisions(map_path=map_path)

    assert any(issue.contract == "architecture_decision_map" for issue in issues)
    assert any(issue.field == "persisted_map" for issue in issues)


def test_architecture_decision_cli_can_write_map(capsys, tmp_path: Path) -> None:
    map_path = tmp_path / "architecture_decision_map.json"

    exit_code = run(["--write-map", "--map-path", str(map_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema_name"] == "architecture_decision_map_write"
    assert json.loads(map_path.read_text()) == build_architecture_decision_map()


def test_architecture_decision_cli_prints_valid_map(capsys) -> None:
    exit_code = run([])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema_name"] == ARCHITECTURE_DECISION_MAP_SCHEMA_NAME
    assert output["valid"] is True
    assert output["issues"] == []


def test_architecture_decision_registry_schema_name_is_public() -> None:
    assert ARCHITECTURE_DECISION_SCHEMA_NAME == "architecture_decisions"
