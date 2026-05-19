from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


def test_analyzer_allows_search_schema_registry_composition() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/search.py",
            [
                "_OWNER_MODULES = (",
                "    _search_core,",
                "    _search_history,",
                ")",
                "__all__ = [",
                "    *_search_core.__all__,",
                "    *_search_history.__all__,",
                "]",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in report["findings"]} == {
        "compatibility_registry_declaration"
    }


def test_analyzer_allows_compact_search_schema_facade_hunk() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/search.py",
            [
                "from typing import Any as _Any",
                "_OWNER_MODULES: tuple[object, ...] = (",
                "    _search_core,",
                "    _search_history,",
                ")",
                "_EXPORT_REGISTRY = {",
                "    name: module for module in _OWNER_MODULES "
                'for name in getattr(module, "__all__", ())',
                "}",
                "__all__ = sorted(_EXPORT_REGISTRY)",
                "def __getattr__(name: str) -> _Any:",
                "    module = _EXPORT_REGISTRY.get(name)",
                "    if module is None:",
                '        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")',
                "    value = getattr(module, name)",
                "    globals()[name] = value",
                "    return value",
                "def __dir__() -> list[str]:",
                "    return sorted(set(globals()) | set(__all__))",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in report["findings"]} == {
        "compatibility_registry_declaration"
    }


def test_analyzer_allows_search_schema_alias_forwarders() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/search.py",
            [
                "import app.schemas.search_core as _search_core",
                "from app.schemas import search_history as _search_history",
                "SearchRequest = _search_core.SearchRequest",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in report["findings"]} == {"schema_alias_forwarder"}


def test_search_schema_facade_blocks_broad_reexport_batches() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/search.py",
            [
                "from app.schemas.search_core import (",
                "    SearchRequest,",
                "    SearchResult,",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 4
    assert {finding["category"] for finding in report["findings"]} == {"broad_reexport_batch"}


def test_search_schema_facade_blocks_new_export_sink_surfaces() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/search.py",
            [
                "from app.schemas._search_schema_exports import SCHEMA_EXPORTS",
                "def _load_schema_exports():",
                "    return SCHEMA_EXPORTS",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 3
    assert {finding["category"] for finding in report["findings"]} == {"export_sink_surface"}
