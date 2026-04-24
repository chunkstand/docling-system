from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.api.capabilities import API_CAPABILITIES

PUBLIC_API_ROUTE_EXEMPTIONS = frozenset(
    {
        ("GET", "/"),
        ("GET", "/health"),
    }
)
MUTATING_METHODS = frozenset({"DELETE", "PATCH", "POST", "PUT"})


@dataclass(frozen=True, slots=True)
class ApiRouteCapabilityManifestEntry:
    method: str
    path: str
    name: str
    endpoint: str
    capability: str | None
    capabilities: tuple[str, ...]
    public_exempt: bool
    mutation_key_required: bool
    response_model: str | None


@dataclass(frozen=True, slots=True)
class ApiRouteContractIssue:
    method: str
    path: str
    name: str
    field: str
    message: str


def _iter_dependency_calls(dependant: Any) -> Iterator[object]:
    for dependency in getattr(dependant, "dependencies", ()):
        call = getattr(dependency, "call", None)
        if call is not None:
            yield call
        yield from _iter_dependency_calls(dependency)


def _route_capabilities(route: APIRoute) -> tuple[str, ...]:
    capabilities: list[str] = []
    for call in _iter_dependency_calls(route.dependant):
        capability = getattr(call, "api_capability", None)
        if capability is not None and capability not in capabilities:
            capabilities.append(str(capability))
    return tuple(capabilities)


def _route_requires_mutation_key(route: APIRoute) -> bool:
    return any(
        bool(getattr(call, "api_mutation_key_required", False))
        for call in _iter_dependency_calls(route.dependant)
    )


def _response_model_name(route: APIRoute) -> str | None:
    response_model = getattr(route, "response_model", None)
    if response_model is None:
        return None
    return getattr(response_model, "__name__", repr(response_model))


def build_api_route_capability_manifest(
    app: FastAPI,
) -> tuple[ApiRouteCapabilityManifestEntry, ...]:
    entries: list[ApiRouteCapabilityManifestEntry] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(method for method in (route.methods or ()) if method != "OPTIONS")
        capabilities = _route_capabilities(route)
        capability = capabilities[0] if len(capabilities) == 1 else None
        mutation_key_required = _route_requires_mutation_key(route)
        response_model = _response_model_name(route)
        endpoint = f"{route.endpoint.__module__}.{route.endpoint.__name__}"
        for method in methods:
            entries.append(
                ApiRouteCapabilityManifestEntry(
                    method=method,
                    path=route.path,
                    name=route.name,
                    endpoint=endpoint,
                    capability=capability,
                    capabilities=capabilities,
                    public_exempt=(method, route.path) in PUBLIC_API_ROUTE_EXEMPTIONS,
                    mutation_key_required=mutation_key_required,
                    response_model=response_model,
                )
            )
    return tuple(sorted(entries, key=lambda entry: (entry.path, entry.method)))


def validate_api_route_capability_contracts(app: FastAPI) -> list[ApiRouteContractIssue]:
    issues: list[ApiRouteContractIssue] = []
    for entry in build_api_route_capability_manifest(app):
        if len(entry.capabilities) > 1:
            issues.append(
                ApiRouteContractIssue(
                    method=entry.method,
                    path=entry.path,
                    name=entry.name,
                    field="capability",
                    message="Route declares more than one API capability.",
                )
            )
        for capability in entry.capabilities:
            if capability not in API_CAPABILITIES:
                issues.append(
                    ApiRouteContractIssue(
                        method=entry.method,
                        path=entry.path,
                        name=entry.name,
                        field="capability",
                        message=f"Route declares unknown API capability '{capability}'.",
                    )
                )
        if entry.public_exempt:
            continue
        if not entry.capabilities:
            issues.append(
                ApiRouteContractIssue(
                    method=entry.method,
                    path=entry.path,
                    name=entry.name,
                    field="capability",
                    message="Public API route is missing a remote capability gate.",
                )
            )
        if entry.method in MUTATING_METHODS and not entry.mutation_key_required:
            issues.append(
                ApiRouteContractIssue(
                    method=entry.method,
                    path=entry.path,
                    name=entry.name,
                    field="mutation_key",
                    message="Mutating API route is missing the mutation API key gate.",
                )
            )
    return issues
