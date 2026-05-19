from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.hotspot_prevention_diff import ChangedFile, ChangedLine, DiffStat
from app.hotspot_prevention_policy import HotspotException, HotspotRule

RESIDUAL_TEST_COMPATIBILITY_PATHS = {
    "tests/db_model_contract.py",
    "tests/integration/test_claim_support_judge_evaluation_roundtrip.py",
    "tests/unit/test_agent_task_context.py",
    "tests/unit/test_agent_tasks_api.py",
    "tests/unit/test_evaluation_service.py",
    "tests/unit/test_search_service.py",
    "tests/integration/test_retrieval_learning_ledger.py",
    "tests/integration/test_technical_report_harness_roundtrip.py",
}

LOCAL_TEST_SUPPORT_PATHS = {
    "tests/integration/retrieval_learning_ledger_support.py",
    "tests/integration/technical_report_harness_support.py",
}

_COMPATIBILITY_TEST_TOKENS = (
    "compat",
    "contract",
    "facade",
    "smoke",
    "roundtrip",
    "registry",
)

@dataclass(frozen=True)
class SurfaceClassification:
    status: str
    category: str
    message: str


@dataclass(frozen=True)
class ClassifiedLine:
    line: ChangedLine
    status: str
    category: str
    message: str
    policy_rule: str


def classify_cli_test_surface_addition(*, stripped: str) -> SurfaceClassification | None:
    if not stripped.startswith("def test_"):
        return None
    lowered = stripped.lower()
    if any(token in lowered for token in ("compat", "entrypoint", "forward")):
        return SurfaceClassification(
            status="allowed",
            category="compatibility_assertion",
            message="legacy CLI compatibility assertion is allowed",
        )
    return SurfaceClassification(
        status="blocked",
        category="broad_new_test_group",
        message="new CLI command tests belong in focused tests/unit/test_cli_*.py files",
    )


def classify_residual_test_surface_addition(*, stripped: str) -> SurfaceClassification | None:
    if stripped.startswith(("class ", "def _", "async def _")):
        return SurfaceClassification(
            status="blocked",
            category="broad_helper",
            message="new helper scaffolding belongs in the focused owner-family test files",
        )
    if stripped.startswith(("def ", "async def ")) and not stripped.startswith("def test_"):
        return SurfaceClassification(
            status="blocked",
            category="broad_helper",
            message="new residual compatibility helpers belong in focused owner-family test files",
        )
    if not stripped.startswith("def test_"):
        return None
    if is_residual_compatibility_test_name(stripped):
        return SurfaceClassification(
            status="allowed",
            category="compatibility_assertion",
            message="residual compatibility or smoke assertions are allowed",
        )
    return SurfaceClassification(
        status="blocked",
        category="broad_new_test_group",
        message="new scenario groups belong in focused owner-family test files",
    )


def deletion_finding(*, rule: HotspotRule, diff_stat: DiffStat) -> dict[str, Any]:
    return {
        "status": "allowed",
        "category": "deletion",
        "relative_path": rule.relative_path,
        "line": None,
        "policy_rule": "allow.deletion",
        "target_role": rule.target_role,
        "added_line_count": diff_stat.added_line_count,
        "deleted_line_count": diff_stat.deleted_line_count,
        "message": "deletion-only hotspot reduction is allowed",
        "preferred_owner_modules": list(rule.preferred_owner_modules),
        "added_line": None,
        "exception_id": None,
        "remediation": None,
    }


def hunk_ids_matching(
    changed_file: ChangedFile,
    predicate: Callable[[tuple[str, ...]], bool],
) -> set[int]:
    lines_by_hunk: dict[int, list[str]] = {}
    for line in changed_file.added_lines:
        lines_by_hunk.setdefault(line.hunk_id, []).append(line.text)
    return {
        hunk_id for hunk_id, hunk_lines in lines_by_hunk.items() if predicate(tuple(hunk_lines))
    }


def _conditional_hunk_ids(
    *,
    enabled: bool,
    changed_file: ChangedFile,
    predicate: Callable[[tuple[str, ...]], bool],
) -> set[int]:
    return set() if not enabled else hunk_ids_matching(changed_file, predicate)


def forwarding_only_body_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return _conditional_hunk_ids(
        enabled=allowed_category_for_forwarder(rule) is not None,
        changed_file=changed_file,
        predicate=is_forwarding_hunk,
    )


def alias_only_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return _conditional_hunk_ids(
        enabled=allowed_category_for_import(rule) is not None,
        changed_file=changed_file,
        predicate=is_alias_only_hunk,
    )


def registry_composition_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return _conditional_hunk_ids(
        enabled="registry_composition" in rule.allow,
        changed_file=changed_file,
        predicate=is_registry_composition_hunk,
    )


def compatibility_test_only_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return _conditional_hunk_ids(
        enabled="compatibility_assertion" in rule.allow,
        changed_file=changed_file,
        predicate=is_compatibility_test_hunk,
    )


def test_signature_continuation_hunk_ids(
    rule: HotspotRule,
    changed_file: ChangedFile,
) -> set[int]:
    return _conditional_hunk_ids(
        enabled="compatibility_assertion" in rule.allow,
        changed_file=changed_file,
        predicate=is_test_signature_continuation_hunk,
    )


def classify_local_test_support_surface_addition(
    *, stripped: str
) -> SurfaceClassification | None:
    if stripped.startswith(("class ", "def ", "async def ")):
        return SurfaceClassification(
            status="blocked",
            category="broad_helper",
            message="new family-local helpers do not belong in the governed support module",
        )
    return None


def is_comment_or_blank(text: str) -> bool:
    stripped = text.strip()
    return not stripped or stripped.startswith("#")


def is_import_or_alias(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("from ", "import ", "__all__")) or bool(
        re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_.]*$", stripped)
    )


def is_multiline_import_continuation(text: str, hunk_lines: tuple[str, ...]) -> bool:
    if not re.match(
        r"[A-Za-z_][A-Za-z0-9_]*(\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?,?$",
        text,
    ):
        return False
    return any(
        re.match(r"(from\s+[A-Za-z_][A-Za-z0-9_.]*\s+import|import)\s+\($", raw.strip())
        for raw in hunk_lines
    )


def is_compatibility_test_hunk(lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if not is_comment_or_blank(raw)]
    if not significant:
        return False
    saw_allowed_test = False
    for stripped in significant:
        if stripped.startswith("def test_"):
            if not is_residual_compatibility_test_name(stripped):
                return False
            saw_allowed_test = True
            continue
        if stripped.startswith(("class ", "def test_")):
            return False
    return saw_allowed_test


def is_test_signature_continuation_hunk(lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if not is_comment_or_blank(raw)]
    if not significant:
        return False
    return all(
        stripped in {"):", ") -> None:"}
        or bool(re.match(r"[A-Za-z_][A-Za-z0-9_]*,?$", stripped))
        for stripped in significant
    )


def is_alias_only_hunk(lines: tuple[str, ...]) -> bool:
    significant = [text.strip() for text in lines if not is_comment_or_blank(text)]
    saw_alias = False
    index = 0
    while index < len(significant):
        stripped = significant[index]
        if is_import_or_alias(stripped):
            saw_alias = True
            index += 1
            continue
        if re.match(r"from\s+[A-Za-z_][A-Za-z0-9_.]*\s+import\s+\($", stripped):
            saw_alias = True
            index += 1
            while index < len(significant) and significant[index] != ")":
                if not re.match(
                    r"[A-Za-z_][A-Za-z0-9_]*(\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?,?$",
                    significant[index],
                ):
                    return False
                index += 1
            if index >= len(significant) or significant[index] != ")":
                return False
            index += 1
            continue
        if not re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*\($", stripped):
            return False
        if index + 2 >= len(significant):
            return False
        target = significant[index + 1]
        closing = significant[index + 2]
        if not re.match(r"[A-Za-z_][A-Za-z0-9_.]*,?$", target):
            return False
        if closing != ")":
            return False
        saw_alias = True
        index += 3
    return saw_alias


def is_forwarding_hunk(lines: tuple[str, ...]) -> bool:
    significant: list[str] = []
    in_signature = False
    for text in lines:
        stripped = text.strip()
        if (
            not stripped
            or stripped.startswith(("#", "@"))
            or stripped in {'"""', "'''", ")"}
            or is_import_or_alias(text)
        ):
            continue
        if stripped.startswith(("def ", "async def ")):
            in_signature = not stripped.endswith(":")
            continue
        if in_signature:
            if stripped.endswith(":") or stripped == "):":
                in_signature = False
            continue
        significant.append(stripped)
    has_forwarding_call = False
    for stripped in significant:
        if re.match(r"\)(\s*->\s*[^:]+)?:", stripped):
            continue
        if re.match(r"return\s+[A-Za-z_][A-Za-z0-9_.]*\(", stripped):
            has_forwarding_call = True
            continue
        if stripped.startswith("raise SystemExit("):
            has_forwarding_call = True
            continue
        if re.match(r"[A-Za-z_][A-Za-z0-9_.]*,?$", stripped):
            continue
        if re.match(
            r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_.]*,?$",
            stripped,
        ):
            continue
        return False
    return has_forwarding_call


def is_forwarding_call_line(stripped: str) -> bool:
    return bool(re.match(r"return\s+[A-Za-z_][A-Za-z0-9_.]*\(", stripped)) or stripped.startswith(
        "raise SystemExit("
    )


def is_agent_task_schema_alias_line(stripped: str) -> bool:
    return bool(
        re.match(
            r"import\s+app\.schemas\.agent_task_[A-Za-z0-9_]+\s+as\s+_[A-Za-z_][A-Za-z0-9_]*$",
            stripped,
        )
        or re.match(
            r"from\s+app\.schemas\s+import\s+agent_task_[A-Za-z0-9_]+\s+as\s+_[A-Za-z_][A-Za-z0-9_]*$",
            stripped,
        )
        or re.match(
            r"from\s+app\.schemas\.agent_task_[A-Za-z0-9_]+\s+import\s+__all__\s+as\s+_[A-Za-z_][A-Za-z0-9_]*$",
            stripped,
        )
        or re.match(
            r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*_[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$",
            stripped,
        )
    )


def is_agent_task_schema_registry_line(stripped: str) -> bool:
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


def is_agent_task_schema_registry_hunk(lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if not is_comment_or_blank(raw)]
    if not significant:
        return False
    has_registry_marker = False
    for stripped in significant:
        if stripped in {"(", ")", "{", "}", "[", "]", "),", "},", "],"}:
            continue
        if is_agent_task_schema_registry_line(stripped):
            has_registry_marker = True
            continue
        return False
    return has_registry_marker


def is_agent_task_schema_export_sink_line(stripped: str) -> bool:
    return bool(
        re.match(r"(from|import)\s+app\.schemas\._[A-Za-z0-9_.]+", stripped)
        or re.match(r"(from|import)\s+app\.schemas\.agent_task_public", stripped)
        or "_agent_task_schema_exports" in stripped
        or "agent_task_public" in stripped
    )


def is_agent_task_schema_broad_reexport_hunk(lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if not is_comment_or_blank(raw)]
    if not significant:
        return False
    return any(
        re.match(
            r"from\s+app\.schemas\.agent_task_[A-Za-z0-9_]+\s+import(\s+\(|\s+[A-Za-z_][A-Za-z0-9_]*)",
            stripped,
        )
        or re.match(r"__all__\s*=\s*[\[(]$", stripped)
        or bool(re.match(r"[\"'][A-Za-z_][A-Za-z0-9_]*[\"'],?$", stripped))
        for stripped in significant
    )


def is_significant_added_text(text: str) -> bool:
    return not is_comment_or_blank(text) and not is_import_or_alias(text)


def is_registry_composition_hunk(lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if is_significant_added_text(raw)]
    if not significant:
        return False
    has_composition_marker = False
    allowed_tokens = (
        "compose_action_registries(",
        "compose_context_builder_registries(",
        "build_",
        "_REGISTRY",
        "_BUILDERS",
        "_executor",
        "globals()",
        "build_generic_task_context",
    )
    for stripped in significant:
        if stripped.startswith(("def ", "async def ", "class ")):
            return False
        if stripped in {"(", ")", "),"}:
            continue
        if any(token in stripped for token in allowed_tokens):
            has_composition_marker = True
            continue
        return False
    return has_composition_marker


def is_residual_compatibility_test_name(stripped: str) -> bool:
    lowered = stripped.lower()
    return any(token in lowered for token in _COMPATIBILITY_TEST_TOKENS)


def allowed_category_for_import(rule: HotspotRule) -> str | None:
    return first_allowed_category(
        rule, "import_forwarder", "alias_forwarder", "registry_composition"
    )


def allowed_category_for_forwarder(rule: HotspotRule) -> str | None:
    return first_allowed_category(
        rule, "explicit_forwarding_function", "alias_forwarder", "import_forwarder"
    )


def first_allowed_category(rule: HotspotRule, *categories: str) -> str | None:
    return next((category for category in categories if category in rule.allow), None)


def significant_unclassified_lines(
    lines: tuple[ChangedLine, ...],
    classified_lines: list[ClassifiedLine],
    *,
    ignored_hunk_ids: set[int] | None = None,
) -> list[ChangedLine]:
    ignored_hunk_ids = ignored_hunk_ids or set()
    classified_keys = {
        (classified.line.new_lineno, classified.line.text) for classified in classified_lines
    }
    return [
        line
        for line in lines
        if line.hunk_id not in ignored_hunk_ids
        and (line.new_lineno, line.text) not in classified_keys
        and is_significant_added_text(line.text)
    ]


def fallback_block_category(rule: HotspotRule) -> str:
    return next(
        (
            category
            for category in (
                "export_sink_surface",
                "broad_reexport_batch",
                "schema_definition",
                "broad_helper",
                "artifact_assembly",
                "broad_parser_logic",
                "executor_implementation",
                "ranking_logic",
                "broad_new_test_group",
            )
            if category in rule.block_new
        ),
        rule.block_new[0],
    )


def exception_for_additions(
    rule: HotspotRule,
    added_lines: tuple[ChangedLine, ...],
) -> HotspotException | None:
    raw_lines = tuple(line.text for line in added_lines)
    return next((exception for exception in rule.exceptions if exception.matches(raw_lines)), None)


def blocked(line: ChangedLine, category: str, message: str) -> ClassifiedLine:
    return ClassifiedLine(line, "blocked", category, message, f"block_new.{category}")


def classified_surface_decision(
    *,
    line: ChangedLine,
    decision: SurfaceClassification | None,
) -> ClassifiedLine | None:
    if decision is None:
        return None
    prefix = "allow" if decision.status == "allowed" else "block_new"
    return ClassifiedLine(
        line=line,
        status=decision.status,
        category=decision.category,
        message=decision.message,
        policy_rule=f"{prefix}.{decision.category}",
    )


def finding_payload(
    *,
    classified: ClassifiedLine,
    rule: HotspotRule,
    diff_stat: DiffStat,
    exception: HotspotException | None = None,
) -> dict[str, Any]:
    status = (
        "allowed_exception"
        if exception is not None and classified.status == "blocked"
        else classified.status
    )
    message = classified.message
    if exception is not None and classified.status == "blocked":
        message = f"{message}; allowed by exception {exception.exception_id}"
    return {
        "status": status,
        "category": classified.category,
        "relative_path": rule.relative_path,
        "line": classified.line.new_lineno,
        "policy_rule": classified.policy_rule,
        "target_role": rule.target_role,
        "preferred_owner_modules": list(rule.preferred_owner_modules),
        "added_line_count": diff_stat.added_line_count,
        "deleted_line_count": diff_stat.deleted_line_count,
        "message": message,
        "added_line": classified.line.text.strip(),
        "exception_id": exception.exception_id if exception else None,
        "remediation": (
            f"Move the implementation to {', '.join(rule.preferred_owner_modules)} "
            f"and keep {rule.relative_path} as {rule.target_role}."
        ),
    }
