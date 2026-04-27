from __future__ import annotations

import importlib
import json
from pathlib import Path
from uuid import uuid4

from app.capability_contracts import (
    CAPABILITY_CONTRACT_MAP_SCHEMA_NAME,
    build_capability_contract_map,
    run,
    validate_capability_contracts,
    write_capability_contract_map,
)
from app.schemas.search import SearchRequest
from app.services.capabilities.retrieval import ServicesRetrievalCapability


def test_capability_contract_map_exposes_facade_surfaces() -> None:
    payload = build_capability_contract_map()
    facades = {facade["name"]: facade for facade in payload["facades"]}

    assert payload["schema_name"] == CAPABILITY_CONTRACT_MAP_SCHEMA_NAME
    assert payload["facade_count"] == 6
    assert {
        "run_lifecycle",
        "retrieval",
        "evaluation",
        "semantics",
        "agent_orchestration",
        "system_governance",
    } <= set(facades)
    assert payload["function_count"] == sum(
        facade["function_count"] for facade in payload["facades"]
    )
    assert {
        "execute_search",
        "answer_question",
        "record_search_feedback",
    } <= {row["name"] for row in facades["retrieval"]["functions"]}
    assert {
        "get_agent_task_context",
        "run_worker_loop",
    } <= {row["name"] for row in facades["agent_orchestration"]["functions"]}
    assert {
        "get_architecture_inspection_report",
        "summarize_architecture_measurements",
    } <= {row["name"] for row in facades["system_governance"]["functions"]}


def test_capability_contract_map_captures_owner_modules_and_operation_kind() -> None:
    payload = build_capability_contract_map()
    retrieval = next(facade for facade in payload["facades"] if facade["name"] == "retrieval")
    functions = {row["name"]: row for row in retrieval["functions"]}

    assert "app.services.search" in retrieval["owner_modules"]
    assert functions["execute_search"]["owner_module"] == "app.services.search"
    assert functions["execute_search"]["owner_symbol"] == "execute_search"
    assert functions["execute_search"]["operation_kind"] == "orchestration"
    assert functions["record_search_feedback"]["operation_kind"] == "write"
    assert functions["get_search_request_detail"]["operation_kind"] == "read"
    assert functions["execute_search"]["parameters"][0]["annotation"] == "Session"
    assert functions["execute_search"]["returns"] == "search.SearchExecution"


def test_capability_contract_validation_accepts_current_repo() -> None:
    assert validate_capability_contracts() == []


def test_capability_contract_validation_reports_missing_persisted_map(tmp_path: Path) -> None:
    issues = validate_capability_contracts(map_path=tmp_path / "missing.json")

    assert any(issue.contract == "capability_contract_map" for issue in issues)
    assert any(issue.field == "persisted_map" for issue in issues)


def test_capability_contract_validation_reports_stale_persisted_map(tmp_path: Path) -> None:
    map_path = tmp_path / "capability_contract_map.json"
    map_path.write_text(json.dumps({"schema_name": CAPABILITY_CONTRACT_MAP_SCHEMA_NAME}) + "\n")

    issues = validate_capability_contracts(map_path=map_path)

    assert any(issue.field == "persisted_map" for issue in issues)


def test_capability_contract_cli_can_write_map(capsys, tmp_path: Path) -> None:
    map_path = tmp_path / "capability_contract_map.json"

    exit_code = run(["--write-map", "--map-path", str(map_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema_name"] == "capability_contract_map_write"
    assert json.loads(map_path.read_text()) == build_capability_contract_map()


def test_write_capability_contract_map_roundtrips(tmp_path: Path) -> None:
    map_path = tmp_path / "capability_contract_map.json"

    written_path = write_capability_contract_map(map_path)

    assert written_path == map_path
    assert json.loads(written_path.read_text()) == build_capability_contract_map()


def test_retrieval_capability_maps_public_parent_request_name(monkeypatch) -> None:
    captured: dict = {}

    def fake_execute_search(session, request, **kwargs):
        captured.update(kwargs)
        return object()

    retrieval_module = importlib.import_module("app.services.capabilities.retrieval")
    monkeypatch.setattr(retrieval_module.search, "execute_search", fake_execute_search)

    parent_request_id = uuid4()
    capability = ServicesRetrievalCapability()
    result = capability.execute_search(
        object(),
        SearchRequest(query="test", mode="keyword"),
        origin="api",
        parent_search_request_id=parent_request_id,
    )

    assert result is not None
    assert captured["parent_request_id"] == parent_request_id
    assert "parent_search_request_id" not in captured
