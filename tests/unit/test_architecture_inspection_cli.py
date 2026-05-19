from __future__ import annotations

import json
from pathlib import Path

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
    ARCHITECTURE_INSPECTION_SCHEMA_NAME,
    build_architecture_contract_map,
    run,
)


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
