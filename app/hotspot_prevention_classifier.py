from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.hotspot_prevention_diff import ChangedFile, ChangedLine, DiffStat
from app.hotspot_prevention_policy import HotspotException, HotspotRule


@dataclass(frozen=True)
class ClassifiedLine:
    line: ChangedLine
    status: str
    category: str
    message: str
    policy_rule: str


_CLASS_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\b")


def classify_changed_file(
    *,
    rule: HotspotRule,
    changed_file: ChangedFile,
    diff_stat: DiffStat,
) -> list[dict[str, Any]]:
    if not changed_file.added_lines and changed_file.deleted_line_count:
        return [deletion_finding(rule=rule, diff_stat=diff_stat)]

    exception = exception_for_additions(rule, changed_file.added_lines)
    alias_hunk_ids = alias_only_hunk_ids(rule, changed_file)
    registry_hunk_ids = registry_composition_hunk_ids(rule, changed_file)
    forwarding_body_hunk_ids = forwarding_only_body_hunk_ids(rule, changed_file)
    classified_lines: list[ClassifiedLine] = []
    forwarding_hunk_ids: set[int] = set()
    reported_alias_hunks: set[int] = set()
    reported_registry_hunks: set[int] = set()
    reported_forwarding_body_hunks: set[int] = set()
    findings: list[dict[str, Any]] = []
    for line in changed_file.added_lines:
        if line.hunk_id in alias_hunk_ids:
            if line.hunk_id not in reported_alias_hunks:
                import_category = allowed_category_for_import(rule)
                assert import_category is not None
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category=import_category,
                    message="facade import or alias maintenance is allowed",
                    policy_rule=f"allow.{import_category}",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_alias_hunks.add(line.hunk_id)
            continue
        if line.hunk_id in registry_hunk_ids:
            if line.hunk_id not in reported_registry_hunks:
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="registry_composition",
                    message="owner-registry composition is allowed on the facade",
                    policy_rule="allow.registry_composition",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_registry_hunks.add(line.hunk_id)
            continue
        if line.hunk_id in forwarding_body_hunk_ids:
            forwarding_hunk_ids.add(line.hunk_id)
            if (
                line.hunk_id not in reported_forwarding_body_hunks
                and is_forwarding_call_line(line.text.strip())
            ):
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="explicit_forwarding_function",
                    message="narrow forwarding wrapper is allowed",
                    policy_rule="allow.explicit_forwarding_function",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_forwarding_body_hunks.add(line.hunk_id)
            continue
        classified = classify_python_addition(rule=rule, changed_file=changed_file, line=line)
        if classified is None:
            continue
        classified_lines.append(classified)
        if classified.policy_rule == "allow.explicit_forwarding_function":
            forwarding_hunk_ids.add(line.hunk_id)
        findings.append(
            finding_payload(
                classified=classified,
                rule=rule,
                diff_stat=diff_stat,
                exception=exception,
            )
        )

    significant = significant_unclassified_lines(
        changed_file.added_lines,
        classified_lines,
        ignored_hunk_ids=forwarding_hunk_ids | alias_hunk_ids | registry_hunk_ids,
    )
    if len(significant) >= 8:
        classified = blocked(
            significant[0],
            fallback_block_category(rule),
            "large unclassified implementation block added to a known hotspot",
        )
        findings.append(
            finding_payload(
                classified=classified,
                rule=rule,
                diff_stat=diff_stat,
                exception=exception,
            )
        )
    return findings


def forwarding_only_body_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    if allowed_category_for_forwarder(rule) is None:
        return set()
    return hunk_ids_matching(changed_file, is_forwarding_hunk)


def alias_only_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    if allowed_category_for_import(rule) is None:
        return set()
    return hunk_ids_matching(changed_file, is_alias_only_hunk)


def registry_composition_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    if "registry_composition" not in rule.allow:
        return set()
    return hunk_ids_matching(changed_file, is_registry_composition_hunk)


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


def deletion_finding(*, rule: HotspotRule, diff_stat: DiffStat) -> dict[str, Any]:
    return {
        "status": "allowed",
        "category": "deletion",
        "relative_path": rule.relative_path,
        "line": None,
        "policy_rule": "allow.deletion",
        "target_role": rule.target_role,
        "preferred_owner_modules": list(rule.preferred_owner_modules),
        "added_line_count": diff_stat.added_line_count,
        "deleted_line_count": diff_stat.deleted_line_count,
        "message": "deletion-only hotspot reduction is allowed",
        "added_line": None,
        "exception_id": None,
        "remediation": None,
    }


def classify_python_addition(
    *,
    rule: HotspotRule,
    changed_file: ChangedFile,
    line: ChangedLine,
) -> ClassifiedLine | None:
    path = changed_file.relative_path
    stripped = line.text.strip()
    if is_comment_or_blank(line.text):
        return None
    import_category = allowed_category_for_import(rule)
    if import_category and is_import_or_alias(line.text):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category=import_category,
            message="facade import or alias maintenance is allowed",
            policy_rule=f"allow.{import_category}",
        )
    forwarding_category = allowed_category_for_forwarder(rule)
    hunk_lines = tuple(
        row.text for row in changed_file.added_lines if row.hunk_id == line.hunk_id
    )
    is_forwarding_def = stripped.startswith(("def ", "async def ")) and is_forwarding_hunk(
        hunk_lines
    )
    if forwarding_category and is_forwarding_def:
        return ClassifiedLine(
            line=line,
            status="allowed",
            category=forwarding_category,
            message="narrow forwarding wrapper is allowed",
            policy_rule=f"allow.{forwarding_category}",
        )
    return classify_hotspot_implementation(path=path, stripped=stripped, line=line, rule=rule)


def classify_hotspot_implementation(
    *,
    path: str,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    if path == "app/cli.py":
        return classify_cli_addition(stripped=stripped, line=line, rule=rule)
    classifier = {
        "app/db/models.py": classify_model_addition,
        "app/services/evidence.py": classify_evidence_addition,
        "app/services/agent_task_actions.py": classify_agent_action_addition,
        "app/services/agent_task_context.py": classify_agent_task_context_addition,
        "app/services/search.py": classify_search_addition,
        "tests/unit/test_cli.py": classify_cli_test_addition,
    }.get(path)
    return None if classifier is None else classifier(stripped=stripped, line=line)


def classify_model_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if "relationship(" in stripped:
        return blocked(
            line,
            "relationship_logic",
            "new relationship logic belongs in a model domain",
        )
    if _CLASS_RE.match(stripped):
        category = "enum" if "Enum" in stripped else "orm_class"
        return blocked(line, category, "new ORM or enum classes belong in app/db/model_domains/")
    if stripped.startswith(("def ", "async def ")):
        return blocked(line, "broad_helper", "new model helpers belong in a focused owner module")
    return None


def classify_evidence_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if stripped.startswith(("def _", "async def _")):
        return blocked(line, "private_helper", "new evidence helpers belong in evidence_* modules")
    if stripped.startswith(("def ", "async def ", "class ")):
        return blocked(
            line,
            "payload_builder",
            "new evidence behavior belongs in evidence_* modules",
        )
    if any(token in stripped for token in ("write_text(", "json.dumps(", "artifact", "payload")):
        return blocked(
            line,
            "artifact_assembly",
            "new evidence assembly belongs in evidence_* modules",
        )
    return None


def classify_cli_addition(
    *,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    parser_registration = "add_parser(" in stripped or ".set_defaults(" in stripped
    if parser_registration and "parser_registration" in rule.allow:
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="parser_registration",
            message="parser registration is allowed on the CLI facade",
            policy_rule="allow.parser_registration",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "command_implementation",
            "new command bodies belong in app/cli_commands/",
        )
    if "ArgumentParser(" in stripped:
        return blocked(
            line,
            "broad_parser_logic",
            "broad parser logic belongs in app/cli_commands/",
        )
    return None


def classify_agent_action_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if stripped.startswith("class "):
        return blocked(
            line,
            "schema_builder",
            "new action schemas belong in app/services/agent_actions/",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "action_family_helper",
            "new action-family helpers belong in app/services/agent_actions/",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "executor_implementation",
            "new executor implementations belong in app/services/agent_actions/",
        )
    return None


def classify_agent_task_context_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    if stripped.startswith("class "):
        return blocked(
            line,
            "context_builder_implementation",
            "new context contracts belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def _build_", "async def _build_")):
        return blocked(
            line,
            "context_builder_implementation",
            "new context builders belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "context_family_helper",
            "new context helpers belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "context_builder_implementation",
            "new context composition belongs in app/services/agent_task_context_*.py",
        )
    return None


def classify_search_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "query_feature_helper",
            "new search helpers belong in search_* modules",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(line, "ranking_logic", "new search behavior belongs in search_* modules")
    if any(token in stripped.lower() for token in ("rank", "score", "hydrate", "telemetry")):
        return blocked(line, "ranking_logic", "new search logic belongs in search_* modules")
    return None


def classify_cli_test_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if not stripped.startswith("def test_"):
        return None
    lowered = stripped.lower()
    if any(token in lowered for token in ("compat", "entrypoint", "forward")):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="compatibility_assertion",
            message="legacy CLI compatibility assertion is allowed",
            policy_rule="allow.compatibility_assertion",
        )
    return blocked(
        line,
        "broad_new_test_group",
        "new CLI command tests belong in focused tests/unit/test_cli_*.py files",
    )


def is_comment_or_blank(text: str) -> bool:
    stripped = text.strip()
    return not stripped or stripped.startswith("#")


def is_import_or_alias(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("from ", "import ", "__all__")) or bool(
        re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_.]*$", stripped)
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
    for text in lines:
        stripped = text.strip()
        if not stripped or stripped.startswith(("#", "@")) or stripped in {'"""', "'''", ")", "):"}:
            continue
        if stripped.startswith(("def ", "async def ")) or (
            stripped.endswith(":") and "(" in stripped
        ):
            continue
        significant.append(stripped)
    has_forwarding_call = False
    for stripped in significant:
        if re.match(r"return\s+[A-Za-z_][A-Za-z0-9_.]*\(", stripped):
            has_forwarding_call = True
            continue
        if stripped.startswith("raise SystemExit("):
            has_forwarding_call = True
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


def allowed_category_for_import(rule: HotspotRule) -> str | None:
    return first_allowed_category(
        rule,
        "import_forwarder",
        "alias_forwarder",
        "registry_composition",
    )


def allowed_category_for_forwarder(rule: HotspotRule) -> str | None:
    return first_allowed_category(
        rule,
        "explicit_forwarding_function",
        "alias_forwarder",
        "import_forwarder",
    )


def first_allowed_category(rule: HotspotRule, *categories: str) -> str | None:
    for category in categories:
        if category in rule.allow:
            return category
    return None


def significant_unclassified_lines(
    lines: tuple[ChangedLine, ...],
    classified_lines: list[ClassifiedLine],
    *,
    ignored_hunk_ids: set[int] | None = None,
) -> list[ChangedLine]:
    ignored_hunk_ids = ignored_hunk_ids or set()
    classified_keys = {
        (classified.line.new_lineno, classified.line.text)
        for classified in classified_lines
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
    for exception in rule.exceptions:
        if exception.matches(raw_lines):
            return exception
    return None


def blocked(line: ChangedLine, category: str, message: str) -> ClassifiedLine:
    return ClassifiedLine(
        line=line,
        status="blocked",
        category=category,
        message=message,
        policy_rule=f"block_new.{category}",
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
