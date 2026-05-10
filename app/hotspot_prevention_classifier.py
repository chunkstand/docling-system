from __future__ import annotations

import re
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
    classified_lines: list[ClassifiedLine] = []
    findings: list[dict[str, Any]] = []
    for line in changed_file.added_lines:
        classified = classify_python_addition(rule=rule, changed_file=changed_file, line=line)
        if classified is None:
            continue
        classified_lines.append(classified)
        findings.append(
            finding_payload(
                classified=classified,
                rule=rule,
                diff_stat=diff_stat,
                exception=exception,
            )
        )

    significant = significant_unclassified_lines(changed_file.added_lines, classified_lines)
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
    if path == "app/db/models.py":
        return classify_model_addition(stripped=stripped, line=line)
    if path == "app/services/evidence.py":
        return classify_evidence_addition(stripped=stripped, line=line)
    if path == "app/cli.py":
        return classify_cli_addition(stripped=stripped, line=line, rule=rule)
    if path == "app/services/agent_task_actions.py":
        return classify_agent_action_addition(stripped=stripped, line=line)
    if path == "app/services/search.py":
        return classify_search_addition(stripped=stripped, line=line)
    if path == "tests/unit/test_cli.py":
        return classify_cli_test_addition(stripped=stripped, line=line)
    return None


def classify_model_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if "relationship(" in stripped:
        return blocked(
            line,
            "relationship_logic",
            "new relationship logic belongs in a model domain",
        )
    class_match = _CLASS_RE.match(stripped)
    if class_match:
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
    if stripped.startswith(("from ", "import ")):
        return True
    if stripped.startswith("__all__"):
        return True
    return bool(re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_.]*$", stripped))


def is_forwarding_hunk(lines: tuple[str, ...]) -> bool:
    significant: list[str] = []
    for text in lines:
        stripped = text.strip()
        if not stripped or stripped.startswith(("#", "@")):
            continue
        if stripped in {'"""', "'''", ")", "):"}:
            continue
        if stripped.startswith(("def ", "async def ")):
            continue
        if stripped.endswith(":") and "(" in stripped:
            continue
        significant.append(stripped)
    if len(significant) > 3:
        return False
    return any(
        re.match(r"return\s+[A-Za-z_][A-Za-z0-9_.]*\(", stripped)
        or stripped.startswith("raise SystemExit(")
        for stripped in significant
    )


def allowed_category_for_import(rule: HotspotRule) -> str | None:
    for category in ("import_forwarder", "alias_forwarder", "registry_composition"):
        if category in rule.allow:
            return category
    return None


def allowed_category_for_forwarder(rule: HotspotRule) -> str | None:
    for category in ("explicit_forwarding_function", "alias_forwarder", "import_forwarder"):
        if category in rule.allow:
            return category
    return None


def significant_unclassified_lines(
    lines: tuple[ChangedLine, ...],
    classified_lines: list[ClassifiedLine],
) -> list[ChangedLine]:
    classified_keys = {
        (classified.line.new_lineno, classified.line.text)
        for classified in classified_lines
    }
    return [
        line
        for line in lines
        if (line.new_lineno, line.text) not in classified_keys
        and not is_comment_or_blank(line.text)
        and not is_import_or_alias(line.text)
    ]


def fallback_block_category(rule: HotspotRule) -> str:
    for category in (
        "broad_helper",
        "artifact_assembly",
        "broad_parser_logic",
        "executor_implementation",
        "ranking_logic",
        "broad_new_test_group",
    ):
        if category in rule.block_new:
            return category
    return rule.block_new[0]


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
