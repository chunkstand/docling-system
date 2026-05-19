from __future__ import annotations

import re

from app.hotspot_prevention_classifier_support import (
    ClassifiedLine,
    blocked,
    is_comment_or_blank,
)
from app.hotspot_prevention_diff import ChangedLine


def _is_schema_alias_line(*, prefix: str, stripped: str) -> bool:
    return bool(
        re.match(
            rf"import\s+app\.schemas\.{prefix}_[A-Za-z0-9_]+\s+as\s+_[A-Za-z_][A-Za-z0-9_]*$",
            stripped,
        )
        or re.match(
            rf"from\s+app\.schemas\s+import\s+{prefix}_[A-Za-z0-9_]+\s+as\s+_[A-Za-z_][A-Za-z0-9_]*$",
            stripped,
        )
        or re.match(
            rf"from\s+app\.schemas\.{prefix}_[A-Za-z0-9_]+\s+import\s+__all__\s+as\s+_[A-Za-z_][A-Za-z0-9_]*$",
            stripped,
        )
        or re.match(
            r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*_[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$",
            stripped,
        )
    )


def _is_schema_registry_line(stripped: str) -> bool:
    return bool(
        stripped in {"}", "},"}
        or stripped == "from typing import Any as _Any"
        or re.match(r"_[A-Z][A-Z0-9_]*\s*=\s*[\[{(]$", stripped)
        or re.match(r"_[A-Z][A-Z0-9_]*:\s*tuple\[object,\s*\.\.\.\]\s*=\s*[\[(]$", stripped)
        or re.match(r"_[A-Za-z0-9_]+,?$", stripped)
        or re.match(r"__all__\s*=\s*[\[(].*$", stripped)
        or re.match(r"__all__\s*=\s*sorted\(_EXPORT_REGISTRY\)$", stripped)
        or re.match(r"\*_[A-Za-z0-9_]+\.__all__,?$", stripped)
        or ("for module in _" in stripped and "module.__all__" in stripped)
        or "for name in module.__all__" in stripped
        or (
            "for module in _OWNER_MODULES" in stripped
            and 'getattr(module, "__all__", ())' in stripped
        )
        or stripped == "globals().update("
        or ("globals()[name]" in stripped and "getattr(module, name)" in stripped)
        or re.match(r"def __getattr__\(name: str\) -> _[A-Za-z0-9_]+:$", stripped)
        or stripped == "module = _EXPORT_REGISTRY.get(name)"
        or stripped == "if module is None:"
        or stripped.startswith("raise AttributeError(")
        or stripped == "value = getattr(module, name)"
        or stripped == "globals()[name] = value"
        or stripped == "return value"
        or stripped == "def __dir__() -> list[str]:"
        or stripped == "return sorted(set(globals()) | set(__all__))"
    )


def _is_schema_registry_hunk(lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if not is_comment_or_blank(raw)]
    if not significant:
        return False
    has_registry_marker = False
    for stripped in significant:
        if stripped in {"(", ")", "{", "}", "[", "]", "),", "},", "],"}:
            continue
        if _is_schema_registry_line(stripped):
            has_registry_marker = True
            continue
        return False
    return has_registry_marker


def _is_schema_export_sink_line(
    *,
    export_sink_token: str,
    public_module_name: str,
    stripped: str,
) -> bool:
    return bool(
        re.match(r"(from|import)\s+app\.schemas\._[A-Za-z0-9_.]+", stripped)
        or re.match(rf"(from|import)\s+app\.schemas\.{public_module_name}", stripped)
        or export_sink_token in stripped
        or public_module_name in stripped
    )


def _is_schema_broad_reexport_hunk(*, prefix: str, lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if not is_comment_or_blank(raw)]
    if not significant:
        return False
    return any(
        re.match(
            rf"from\s+app\.schemas\.{prefix}_[A-Za-z0-9_]+\s+import(\s+\(|\s+[A-Za-z_][A-Za-z0-9_]*)",
            stripped,
        )
        or re.match(r"__all__\s*=\s*[\[(]$", stripped)
        or bool(re.match(r"[\"'][A-Za-z_][A-Za-z0-9_]*[\"'],?$", stripped))
        for stripped in significant
    )


def _classify_schema_facade_addition(
    *,
    facade_path: str,
    owner_label: str,
    prefix: str,
    export_sink_token: str,
    public_module_name: str,
    stripped: str,
    line: ChangedLine,
    hunk_lines: tuple[str, ...],
) -> ClassifiedLine | None:
    if _is_schema_registry_hunk(hunk_lines) or _is_schema_registry_line(stripped):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="compatibility_registry_declaration",
            message="compact schema compatibility-registry declaration is allowed",
            policy_rule="allow.compatibility_registry_declaration",
        )
    if _is_schema_alias_line(prefix=prefix, stripped=stripped):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="schema_alias_forwarder",
            message="explicit schema alias forwarders are allowed on the facade",
            policy_rule="allow.schema_alias_forwarder",
        )
    if stripped.startswith("class "):
        return blocked(
            line,
            "schema_definition",
            f"new schema definitions belong in the focused {owner_label} owner modules",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "export_sink_surface",
            f"new schema-facade helpers or export sinks do not belong in {facade_path}",
        )
    if _is_schema_export_sink_line(
        export_sink_token=export_sink_token,
        public_module_name=public_module_name,
        stripped=stripped,
    ):
        return blocked(
            line,
            "export_sink_surface",
            f"new export-sink surfaces do not belong in {facade_path}",
        )
    if _is_schema_broad_reexport_hunk(prefix=prefix, lines=hunk_lines):
        return blocked(
            line,
            "broad_reexport_batch",
            f"broad direct re-export batches do not belong in {facade_path}",
        )
    return blocked(
        line,
        "export_sink_surface",
        "new schema-facade behavior belongs in the focused owner modules or a "
        "compact registry declaration",
    )


def classify_agent_task_schema_facade_addition(
    *,
    stripped: str,
    line: ChangedLine,
    hunk_lines: tuple[str, ...],
) -> ClassifiedLine | None:
    return _classify_schema_facade_addition(
        facade_path="app/schemas/agent_tasks.py",
        owner_label="agent-task schema",
        prefix="agent_task",
        export_sink_token="_agent_task_schema_exports",
        public_module_name="agent_task_public",
        stripped=stripped,
        line=line,
        hunk_lines=hunk_lines,
    )


def classify_search_schema_facade_addition(
    *,
    stripped: str,
    line: ChangedLine,
    hunk_lines: tuple[str, ...],
) -> ClassifiedLine | None:
    return _classify_schema_facade_addition(
        facade_path="app/schemas/search.py",
        owner_label="search schema",
        prefix="search",
        export_sink_token="_search_schema_exports",
        public_module_name="search_public",
        stripped=stripped,
        line=line,
        hunk_lines=hunk_lines,
    )
