from __future__ import annotations

import ast
from pathlib import Path

from fastapi import Depends, FastAPI

import app.api.capabilities as api_capabilities
from app.api.deps import require_api_capability
from app.api.main import create_app
from app.api.route_contracts import (
    PUBLIC_API_ROUTE_EXEMPTIONS,
    build_api_route_capability_manifest,
    validate_api_route_capability_contracts,
)
from app.core.config import DEFAULT_REMOTE_API_CAPABILITIES

ROOT = Path(__file__).resolve().parents[2]
ROUTERS_DIR = ROOT / "app/api/routers"


def test_api_capability_vocabulary_is_closed_and_unique() -> None:
    definitions = api_capabilities.list_api_capability_definitions()
    names = [definition.name for definition in definitions]

    assert len(names) == len(set(names))
    assert set(names) == api_capabilities.API_CAPABILITIES
    assert DEFAULT_REMOTE_API_CAPABILITIES <= api_capabilities.API_CAPABILITIES
    assert api_capabilities.API_CAPABILITY_WILDCARD not in api_capabilities.API_CAPABILITIES


def test_api_route_capability_contracts_are_machine_checkable() -> None:
    issues = validate_api_route_capability_contracts(create_app())

    assert issues == []


def test_api_route_manifest_covers_capabilities_and_public_exemptions() -> None:
    manifest = build_api_route_capability_manifest(create_app())
    route_by_method_path = {(entry.method, entry.path): entry for entry in manifest}
    exempt_routes = {
        (entry.method, entry.path) for entry in manifest if entry.public_exempt
    }
    manifest_capabilities = {
        entry.capability for entry in manifest if entry.capability is not None
    }

    assert exempt_routes == PUBLIC_API_ROUTE_EXEMPTIONS
    assert route_by_method_path[("GET", "/health")].capability is None
    assert route_by_method_path[("POST", "/search")].capability == api_capabilities.SEARCH_QUERY
    assert route_by_method_path[("POST", "/search")].mutation_key_required is True
    assert (
        route_by_method_path[("GET", "/runtime/status")].capability
        == api_capabilities.SYSTEM_READ
    )
    assert (
        route_by_method_path[("GET", "/architecture/inspection")].capability
        == api_capabilities.SYSTEM_READ
    )
    assert (
        route_by_method_path[("GET", "/architecture/measurements/summary")].capability
        == api_capabilities.SYSTEM_READ
    )
    assert api_capabilities.API_CAPABILITIES <= manifest_capabilities


def test_api_route_contract_rejects_unguarded_public_route() -> None:
    app = FastAPI()

    @app.get("/unguarded")
    def unguarded() -> dict[str, bool]:
        return {"ok": True}

    issues = validate_api_route_capability_contracts(app)

    assert any(issue.field == "capability" for issue in issues)


def test_api_route_contract_rejects_unknown_capability() -> None:
    app = FastAPI()

    def unknown_capability_dependency() -> None:
        return None

    unknown_capability_dependency.api_capability = "unknown:capability"

    @app.get("/unknown", dependencies=[Depends(unknown_capability_dependency)])
    def unknown() -> dict[str, bool]:
        return {"ok": True}

    issues = validate_api_route_capability_contracts(app)

    assert any(issue.field == "capability" for issue in issues)


def test_api_route_contract_rejects_mutation_without_mutation_key_gate() -> None:
    app = FastAPI()

    @app.post(
        "/mutating",
        dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE))],
    )
    def mutating() -> dict[str, bool]:
        return {"ok": True}

    issues = validate_api_route_capability_contracts(app)

    assert any(issue.field == "mutation_key" for issue in issues)


def test_require_api_capability_rejects_unknown_capability() -> None:
    try:
        require_api_capability("unknown:capability")
    except ValueError as exc:
        assert "Unknown API capability" in str(exc)
    else:
        raise AssertionError("unknown API capability should be rejected")


def test_routers_do_not_use_literal_api_capability_strings() -> None:
    violations: list[tuple[str, int, str]] = []
    for path in sorted(ROUTERS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Name) or func.id != "require_api_capability":
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            if isinstance(node.args[0].value, str):
                violations.append(
                    (str(path.relative_to(ROOT)), node.lineno, node.args[0].value)
                )

    assert violations == []
