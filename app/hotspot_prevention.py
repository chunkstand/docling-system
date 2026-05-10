from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.core.files import repo_root
from app.core.time import utcnow

POLICY_SCHEMA_NAME = "hotspot_prevention_policy"
REPORT_SCHEMA_NAME = "hotspot_prevention_report"
SCHEMA_VERSION = "1.0"
DEFAULT_POLICY_PATH = Path("config") / "hotspot_prevention.yaml"


@dataclass(frozen=True)
class PolicyIssue:
    field: str
    message: str


@dataclass(frozen=True)
class HotspotException:
    exception_id: str
    case_id: str | None
    milestone_id: str | None
    owner_module: str
    expires_on: date | None
    follow_up_condition: str | None
    match_tokens: tuple[str, ...]

    def matches(self, added_lines: tuple[str, ...]) -> bool:
        haystack = "\n".join(added_lines)
        return any(token and token in haystack for token in self.match_tokens)


@dataclass(frozen=True)
class HotspotRule:
    relative_path: str
    target_role: str
    preferred_owner_modules: tuple[str, ...]
    block_new: tuple[str, ...]
    allow: tuple[str, ...]
    exceptions: tuple[HotspotException, ...] = ()


@dataclass(frozen=True)
class HotspotPolicy:
    schema_name: str
    schema_version: str
    known_hotspots: dict[str, HotspotRule]


@dataclass(frozen=True)
class ChangedLine:
    new_lineno: int
    text: str
    hunk_id: int


@dataclass(frozen=True)
class ChangedFile:
    relative_path: str
    added_lines: tuple[ChangedLine, ...]
    deleted_line_count: int


@dataclass(frozen=True)
class ClassifiedLine:
    line: ChangedLine
    status: str
    category: str
    message: str
    policy_rule: str


_HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_DEF_RE = re.compile(r"(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_CLASS_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\b")


def _string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def validate_policy_payload(
    payload: dict[str, Any],
    *,
    today: date | None = None,
) -> list[PolicyIssue]:
    issues: list[PolicyIssue] = []
    if payload.get("schema_name") != POLICY_SCHEMA_NAME:
        issues.append(
            PolicyIssue(
                field="schema_name",
                message=f"expected {POLICY_SCHEMA_NAME}",
            )
        )
    if str(payload.get("schema_version") or "") != SCHEMA_VERSION:
        issues.append(
            PolicyIssue(
                field="schema_version",
                message=f"expected {SCHEMA_VERSION}",
            )
        )
    known_hotspots = payload.get("known_hotspots")
    if not isinstance(known_hotspots, dict) or not known_hotspots:
        issues.append(PolicyIssue(field="known_hotspots", message="must be a non-empty map"))
        return issues

    current_day = today or date.today()
    for relative_path, raw_rule in sorted(known_hotspots.items()):
        field_prefix = f"known_hotspots.{relative_path}"
        if not isinstance(raw_rule, dict):
            issues.append(PolicyIssue(field=field_prefix, message="must be a map"))
            continue
        if not str(raw_rule.get("target_role") or "").strip():
            issues.append(PolicyIssue(field=f"{field_prefix}.target_role", message="is required"))
        if not _string_list(raw_rule.get("preferred_owner_modules")):
            issues.append(
                PolicyIssue(
                    field=f"{field_prefix}.preferred_owner_modules",
                    message="must contain at least one owner module",
                )
            )
        if not _string_list(raw_rule.get("block_new")):
            issues.append(
                PolicyIssue(
                    field=f"{field_prefix}.block_new",
                    message="must contain at least one blocked category",
                )
            )
        if not _string_list(raw_rule.get("allow")):
            issues.append(
                PolicyIssue(
                    field=f"{field_prefix}.allow",
                    message="must contain at least one allowed category",
                )
            )
        for index, raw_exception in enumerate(raw_rule.get("exceptions") or []):
            exception_prefix = f"{field_prefix}.exceptions[{index}]"
            if not isinstance(raw_exception, dict):
                issues.append(PolicyIssue(field=exception_prefix, message="must be a map"))
                continue
            if not str(raw_exception.get("exception_id") or "").strip():
                issues.append(
                    PolicyIssue(field=f"{exception_prefix}.exception_id", message="is required")
                )
            case_id = str(raw_exception.get("case_id") or "").strip()
            milestone_id = str(raw_exception.get("milestone_id") or "").strip()
            if not case_id and not milestone_id:
                issues.append(
                    PolicyIssue(
                        field=f"{exception_prefix}.case_id",
                        message="requires case_id or milestone_id",
                    )
                )
            if not str(raw_exception.get("owner_module") or "").strip():
                issues.append(
                    PolicyIssue(field=f"{exception_prefix}.owner_module", message="is required")
                )
            follow_up = str(raw_exception.get("follow_up_condition") or "").strip()
            expires_on_raw = raw_exception.get("expires_on")
            if not follow_up and not expires_on_raw:
                issues.append(
                    PolicyIssue(
                        field=f"{exception_prefix}.expires_on",
                        message="requires expires_on or follow_up_condition",
                    )
                )
            if expires_on_raw:
                try:
                    expires_on = _parse_date(expires_on_raw)
                except ValueError:
                    issues.append(
                        PolicyIssue(
                            field=f"{exception_prefix}.expires_on",
                            message="must be an ISO date",
                        )
                    )
                else:
                    if expires_on is not None and expires_on < current_day:
                        issues.append(
                            PolicyIssue(
                                field=f"{exception_prefix}.expires_on",
                                message="is expired",
                            )
                        )
    return issues


def _build_exception(raw_exception: dict[str, Any]) -> HotspotException:
    exception_id = str(raw_exception.get("exception_id") or "").strip()
    case_id = str(raw_exception.get("case_id") or "").strip() or None
    milestone_id = str(raw_exception.get("milestone_id") or "").strip() or None
    match_tokens = _string_list(raw_exception.get("match_tokens"))
    fallback_tokens = tuple(
        token
        for token in (exception_id, case_id or "", milestone_id or "")
        if token
    )
    return HotspotException(
        exception_id=exception_id,
        case_id=case_id,
        milestone_id=milestone_id,
        owner_module=str(raw_exception.get("owner_module") or "").strip(),
        expires_on=_parse_date(raw_exception.get("expires_on")),
        follow_up_condition=(
            str(raw_exception.get("follow_up_condition") or "").strip() or None
        ),
        match_tokens=match_tokens or fallback_tokens,
    )


def build_hotspot_policy(payload: dict[str, Any]) -> HotspotPolicy:
    issues = validate_policy_payload(payload)
    if issues:
        rendered = "; ".join(f"{issue.field}: {issue.message}" for issue in issues)
        raise ValueError(f"invalid hotspot prevention policy: {rendered}")
    raw_hotspots = payload["known_hotspots"]
    known_hotspots: dict[str, HotspotRule] = {}
    for relative_path, raw_rule in sorted(raw_hotspots.items()):
        known_hotspots[str(relative_path)] = HotspotRule(
            relative_path=str(relative_path),
            target_role=str(raw_rule["target_role"]).strip(),
            preferred_owner_modules=_string_list(raw_rule["preferred_owner_modules"]),
            block_new=_string_list(raw_rule["block_new"]),
            allow=_string_list(raw_rule["allow"]),
            exceptions=tuple(
                _build_exception(raw_exception)
                for raw_exception in raw_rule.get("exceptions") or []
            ),
        )
    return HotspotPolicy(
        schema_name=str(payload["schema_name"]),
        schema_version=str(payload["schema_version"]),
        known_hotspots=known_hotspots,
    )


def load_hotspot_policy(
    policy_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> HotspotPolicy:
    root = project_root or repo_root()
    raw_path = policy_path or DEFAULT_POLICY_PATH
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    payload = yaml.safe_load(resolved_path.read_text()) or {}
    if not isinstance(payload, dict):
        raise ValueError("hotspot prevention policy must be a map")
    return build_hotspot_policy(payload)


def _strip_git_prefix(path_value: str) -> str:
    value = path_value.strip()
    if value == "/dev/null":
        return value
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value


def parse_unified_diff(diff_text: str) -> dict[str, ChangedFile]:
    files: dict[str, list[ChangedLine]] = {}
    deleted_counts: dict[str, int] = {}
    current_path: str | None = None
    new_lineno: int | None = None
    hunk_id = 0

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            candidate = _strip_git_prefix(raw_line[4:].split("\t", 1)[0])
            current_path = None if candidate == "/dev/null" else candidate
            if current_path is not None:
                files.setdefault(current_path, [])
                deleted_counts.setdefault(current_path, 0)
            continue
        if current_path is None:
            continue
        if raw_line.startswith("@@ "):
            match = _HUNK_RE.match(raw_line)
            new_lineno = int(match.group(1)) if match else None
            hunk_id += 1
            continue
        if new_lineno is None:
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            files[current_path].append(
                ChangedLine(new_lineno=new_lineno, text=raw_line[1:], hunk_id=hunk_id)
            )
            new_lineno += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            deleted_counts[current_path] = deleted_counts.get(current_path, 0) + 1
        elif raw_line.startswith(" "):
            new_lineno += 1

    return {
        relative_path: ChangedFile(
            relative_path=relative_path,
            added_lines=tuple(added_lines),
            deleted_line_count=deleted_counts.get(relative_path, 0),
        )
        for relative_path, added_lines in sorted(files.items())
    }


def _is_comment_or_blank(text: str) -> bool:
    stripped = text.strip()
    return not stripped or stripped.startswith("#")


def _is_import_or_alias(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("from ", "import ")):
        return True
    if stripped.startswith("__all__"):
        return True
    return bool(re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_.]*$", stripped))


def _hunk_lines(changed_file: ChangedFile, hunk_id: int) -> tuple[str, ...]:
    return tuple(line.text for line in changed_file.added_lines if line.hunk_id == hunk_id)


def _is_forwarding_hunk(lines: tuple[str, ...]) -> bool:
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


def _allowed_category_for_import(rule: HotspotRule) -> str | None:
    for category in ("import_forwarder", "alias_forwarder", "registry_composition"):
        if category in rule.allow:
            return category
    return None


def _allowed_category_for_forwarder(rule: HotspotRule) -> str | None:
    for category in ("explicit_forwarding_function", "alias_forwarder", "import_forwarder"):
        if category in rule.allow:
            return category
    return None


def _classify_python_addition(
    *,
    rule: HotspotRule,
    changed_file: ChangedFile,
    line: ChangedLine,
) -> ClassifiedLine | None:
    path = changed_file.relative_path
    stripped = line.text.strip()
    if _is_comment_or_blank(line.text):
        return None
    import_category = _allowed_category_for_import(rule)
    if import_category and _is_import_or_alias(line.text):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category=import_category,
            message="facade import or alias maintenance is allowed",
            policy_rule=f"allow.{import_category}",
        )
    hunk_lines = _hunk_lines(changed_file, line.hunk_id)
    forwarding_category = _allowed_category_for_forwarder(rule)
    is_forwarding_def = stripped.startswith(("def ", "async def ")) and _is_forwarding_hunk(
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

    if path == "app/db/models.py":
        if "relationship(" in stripped:
            return _blocked(
                line,
                "relationship_logic",
                "new relationship logic belongs in a model domain",
            )
        class_match = _CLASS_RE.match(stripped)
        if class_match:
            category = "enum" if "Enum" in stripped else "orm_class"
            return _blocked(
                line,
                category,
                "new ORM or enum classes belong in app/db/model_domains/",
            )
        if stripped.startswith(("def ", "async def ")):
            return _blocked(
                line,
                "broad_helper",
                "new model helpers belong in a focused owner module",
            )
    elif path == "app/services/evidence.py":
        if stripped.startswith(("def _", "async def _")):
            return _blocked(
                line,
                "private_helper",
                "new evidence helpers belong in evidence_* modules",
            )
        if stripped.startswith(("def ", "async def ", "class ")):
            return _blocked(
                line,
                "payload_builder",
                "new evidence behavior belongs in evidence_* modules",
            )
        evidence_tokens = ("write_text(", "json.dumps(", "artifact", "payload")
        if any(token in stripped for token in evidence_tokens):
            return _blocked(
                line,
                "artifact_assembly",
                "new evidence assembly belongs in evidence_* modules",
            )
    elif path == "app/cli.py":
        if "add_parser(" in stripped or ".set_defaults(" in stripped:
            if "parser_registration" in rule.allow:
                return ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="parser_registration",
                    message="parser registration is allowed on the CLI facade",
                    policy_rule="allow.parser_registration",
                )
        if stripped.startswith(("def ", "async def ")):
            return _blocked(
                line,
                "command_implementation",
                "new command bodies belong in app/cli_commands/",
            )
        if "ArgumentParser(" in stripped:
            return _blocked(
                line,
                "broad_parser_logic",
                "broad parser logic belongs in app/cli_commands/",
            )
    elif path == "app/services/agent_task_actions.py":
        if stripped.startswith("class "):
            return _blocked(
                line,
                "schema_builder",
                "new action schemas belong in app/services/agent_actions/",
            )
        if stripped.startswith(("def _", "async def _")):
            return _blocked(
                line,
                "action_family_helper",
                "new action-family helpers belong in app/services/agent_actions/",
            )
        if stripped.startswith(("def ", "async def ")):
            return _blocked(
                line,
                "executor_implementation",
                "new executor implementations belong in app/services/agent_actions/",
            )
    elif path == "app/services/search.py":
        if stripped.startswith(("def _", "async def _")):
            return _blocked(
                line,
                "query_feature_helper",
                "new search helpers belong in search_* modules",
            )
        if stripped.startswith(("def ", "async def ")):
            return _blocked(
                line,
                "ranking_logic",
                "new search behavior belongs in search_* modules",
            )
        if any(token in stripped.lower() for token in ("rank", "score", "hydrate", "telemetry")):
            return _blocked(line, "ranking_logic", "new search logic belongs in search_* modules")
    elif path == "tests/unit/test_cli.py":
        if stripped.startswith("def test_"):
            lowered = stripped.lower()
            if any(token in lowered for token in ("compat", "entrypoint", "forward")):
                return ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="compatibility_assertion",
                    message="legacy CLI compatibility assertion is allowed",
                    policy_rule="allow.compatibility_assertion",
                )
            return _blocked(
                line,
                "broad_new_test_group",
                "new CLI command tests belong in focused tests/unit/test_cli_*.py files",
            )
    return None


def _blocked(line: ChangedLine, category: str, message: str) -> ClassifiedLine:
    return ClassifiedLine(
        line=line,
        status="blocked",
        category=category,
        message=message,
        policy_rule=f"block_new.{category}",
    )


def _significant_unclassified_lines(
    lines: tuple[ChangedLine, ...],
    classified_lines: list[ClassifiedLine],
) -> list[ChangedLine]:
    classified_keys = {
        (classified.line.new_lineno, classified.line.text)
        for classified in classified_lines
    }
    significant: list[ChangedLine] = []
    for line in lines:
        if (line.new_lineno, line.text) in classified_keys:
            continue
        if _is_comment_or_blank(line.text) or _is_import_or_alias(line.text):
            continue
        significant.append(line)
    return significant


def _fallback_block_category(rule: HotspotRule) -> str:
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


def _exception_for_additions(
    rule: HotspotRule,
    added_lines: tuple[ChangedLine, ...],
) -> HotspotException | None:
    raw_lines = tuple(line.text for line in added_lines)
    for exception in rule.exceptions:
        if exception.matches(raw_lines):
            return exception
    return None


def _finding_payload(
    *,
    classified: ClassifiedLine,
    rule: HotspotRule,
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
        "message": message,
        "added_line": classified.line.text.strip(),
        "exception_id": exception.exception_id if exception else None,
        "remediation": (
            f"Move the implementation to {', '.join(rule.preferred_owner_modules)} "
            f"and keep {rule.relative_path} as {rule.target_role}."
        ),
    }


def build_hotspot_prevention_report(
    diff_text: str,
    *,
    policy: HotspotPolicy | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root or repo_root()
    loaded_policy = policy or load_hotspot_policy(project_root=root)
    changed_files = parse_unified_diff(diff_text)
    findings: list[dict[str, Any]] = []
    changed_hotspot_count = 0

    for relative_path, rule in loaded_policy.known_hotspots.items():
        changed_file = changed_files.get(relative_path)
        if changed_file is None:
            continue
        changed_hotspot_count += 1
        if not changed_file.added_lines and changed_file.deleted_line_count:
            findings.append(
                {
                    "status": "allowed",
                    "category": "deletion",
                    "relative_path": relative_path,
                    "line": None,
                    "policy_rule": "allow.deletion",
                    "target_role": rule.target_role,
                    "preferred_owner_modules": list(rule.preferred_owner_modules),
                    "message": "deletion-only hotspot reduction is allowed",
                    "added_line": None,
                    "exception_id": None,
                    "remediation": None,
                }
            )
            continue

        exception = _exception_for_additions(rule, changed_file.added_lines)
        classified_lines: list[ClassifiedLine] = []
        for line in changed_file.added_lines:
            classified = _classify_python_addition(
                rule=rule,
                changed_file=changed_file,
                line=line,
            )
            if classified is not None:
                classified_lines.append(classified)
                findings.append(
                    _finding_payload(
                        classified=classified,
                        rule=rule,
                        exception=exception,
                    )
                )

        significant = _significant_unclassified_lines(changed_file.added_lines, classified_lines)
        if len(significant) >= 8:
            category = _fallback_block_category(rule)
            classified = _blocked(
                significant[0],
                category,
                "large unclassified implementation block added to a known hotspot",
            )
            findings.append(
                _finding_payload(
                    classified=classified,
                    rule=rule,
                    exception=exception,
                )
            )

    blocked_count = sum(1 for finding in findings if finding["status"] == "blocked")
    allowed_count = sum(1 for finding in findings if finding["status"] == "allowed")
    exception_count = sum(1 for finding in findings if finding["status"] == "allowed_exception")
    return {
        "schema_name": REPORT_SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utcnow().isoformat(),
        "policy_schema_version": loaded_policy.schema_version,
        "policy_path": str(DEFAULT_POLICY_PATH),
        "project_root": str(root),
        "findings": findings,
        "summary": {
            "known_hotspot_count": len(loaded_policy.known_hotspots),
            "changed_hotspot_count": changed_hotspot_count,
            "finding_count": len(findings),
            "blocked_count": blocked_count,
            "allowed_count": allowed_count,
            "exception_count": exception_count,
            "strict_failed": blocked_count > 0,
        },
    }


def collect_git_diff(
    *,
    project_root: Path | None = None,
    base: str | None = None,
    staged: bool = False,
) -> str:
    root = project_root or repo_root()
    if base and staged:
        raise ValueError("--base and --staged cannot be used together")
    command = ["git", "diff", "--unified=3", "--no-ext-diff"]
    if staged:
        command.append("--cached")
    elif base:
        command.append(base)
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(stderr or "git diff failed")
    return completed.stdout


def render_text_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        (
            "[hotspot-prevention] "
            f"known_hotspots={summary['known_hotspot_count']} "
            f"changed_hotspots={summary['changed_hotspot_count']} "
            f"blocked={summary['blocked_count']} "
            f"allowed={summary['allowed_count']} "
            f"exceptions={summary['exception_count']}"
        )
    ]
    findings = report.get("findings") or []
    if not findings:
        lines.append("[hotspot-prevention] findings: none")
        return "\n".join(lines)
    lines.append("[hotspot-prevention] findings:")
    for finding in findings:
        location = finding["relative_path"]
        if finding.get("line") is not None:
            location = f"{location}:{finding['line']}"
        owner_modules = ", ".join(finding.get("preferred_owner_modules") or [])
        lines.append(
            "  - "
            f"{location}: {finding['status']}/{finding['category']} "
            f"({finding['policy_rule']}): {finding['message']}"
        )
        if owner_modules and finding["status"] == "blocked":
            lines.append(f"    preferred owner: {owner_modules}")
    return "\n".join(lines)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prevent new implementation growth in known architecture hotspots."
    )
    parser.add_argument(
        "--policy-path",
        default=str(DEFAULT_POLICY_PATH),
        help="Hotspot policy path, relative to the repo root unless absolute.",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Compare the working tree against this Git ref.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Check the staged diff instead of the working-tree diff.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when blocked hotspot growth is detected.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--diff-file",
        default=None,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    project_root = repo_root()
    try:
        policy = load_hotspot_policy(Path(args.policy_path), project_root=project_root)
        if args.diff_file:
            diff_text = Path(args.diff_file).read_text()
        else:
            diff_text = collect_git_diff(
                project_root=project_root,
                base=args.base,
                staged=args.staged,
            )
        report = build_hotspot_prevention_report(
            diff_text,
            policy=policy,
            project_root=project_root,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"[hotspot-prevention] {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, sort_keys=True))
    else:
        print(render_text_report(report))
    if args.strict and report["summary"]["blocked_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
