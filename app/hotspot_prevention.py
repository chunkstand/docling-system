from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.core.files import repo_root
from app.core.time import utcnow
from app.hotspot_prevention_classifier import classify_changed_file
from app.hotspot_prevention_diff import (
    DiffStat,
    collect_git_diff,
    collect_git_numstat,
    fallback_diff_stats,
    parse_numstat,
    parse_unified_diff,
)
from app.hotspot_prevention_policy import (
    DEFAULT_POLICY_PATH,
    POLICY_SCHEMA_NAME,  # noqa: F401 - re-exported for tests and callers.
    SCHEMA_VERSION,
    HotspotPolicy,
    build_hotspot_policy,  # noqa: F401 - re-exported for tests and callers.
    load_hotspot_policy,
    validate_policy_payload,  # noqa: F401 - re-exported for tests and callers.
)

REPORT_SCHEMA_NAME = "hotspot_prevention_report"


def build_hotspot_prevention_report(
    diff_text: str,
    *,
    numstat_text: str | None = None,
    policy: HotspotPolicy | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root or repo_root()
    loaded_policy = policy or load_hotspot_policy(project_root=root)
    changed_files = parse_unified_diff(diff_text)
    diff_stats = {
        **fallback_diff_stats(changed_files),
        **(parse_numstat(numstat_text or "") if numstat_text is not None else {}),
    }
    findings: list[dict[str, Any]] = []
    changed_hotspot_count = 0

    for relative_path, rule in loaded_policy.known_hotspots.items():
        changed_file = changed_files.get(relative_path)
        if changed_file is None:
            continue
        changed_hotspot_count += 1
        diff_stat = diff_stats.get(
            relative_path,
            DiffStat(
                relative_path=relative_path,
                added_line_count=len(changed_file.added_lines),
                deleted_line_count=changed_file.deleted_line_count,
                source="unified_diff",
            ),
        )
        findings.extend(
            classify_changed_file(
                rule=rule,
                changed_file=changed_file,
                diff_stat=diff_stat,
            )
        )

    hotspot_stats = _hotspot_stats(diff_stats, loaded_policy)
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
        "changed_files": hotspot_stats,
        "findings": findings,
        "summary": {
            "known_hotspot_count": len(loaded_policy.known_hotspots),
            "changed_hotspot_count": changed_hotspot_count,
            "added_line_count": _line_total(hotspot_stats, "added_line_count"),
            "deleted_line_count": _line_total(hotspot_stats, "deleted_line_count"),
            "finding_count": len(findings),
            "blocked_count": blocked_count,
            "allowed_count": allowed_count,
            "exception_count": exception_count,
            "strict_failed": blocked_count > 0,
        },
    }


def _hotspot_stats(
    diff_stats: dict[str, DiffStat],
    policy: HotspotPolicy,
) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": stat.relative_path,
            "added_line_count": stat.added_line_count,
            "deleted_line_count": stat.deleted_line_count,
            "source": stat.source,
            "known_hotspot": True,
        }
        for stat in sorted(diff_stats.values(), key=lambda row: row.relative_path)
        if stat.relative_path in policy.known_hotspots
    ]


def _line_total(rows: list[dict[str, Any]], field: str) -> int:
    return sum(int(row[field] or 0) for row in rows if row[field] is not None)


def render_text_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        (
            "[hotspot-prevention] "
            f"known_hotspots={summary['known_hotspot_count']} "
            f"changed_hotspots={summary['changed_hotspot_count']} "
            f"added_lines={summary['added_line_count']} "
            f"deleted_lines={summary['deleted_line_count']} "
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
        lines.extend(_render_finding(finding))
    return "\n".join(lines)


def _render_finding(finding: dict[str, Any]) -> list[str]:
    location = finding["relative_path"]
    if finding.get("line") is not None:
        location = f"{location}:{finding['line']}"
    lines = [
        "  - "
        f"{location}: {finding['status']}/{finding['category']} "
        f"({finding['policy_rule']}): {finding['message']}"
    ]
    owner_modules = ", ".join(finding.get("preferred_owner_modules") or [])
    if owner_modules and finding["status"] == "blocked":
        lines.append(f"    preferred owner: {owner_modules}")
    return lines


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prevent new implementation growth in known architecture hotspots."
    )
    parser.add_argument("--policy-path", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument(
        "--base",
        default=None,
        help="Compare the working tree against this Git ref.",
    )
    parser.add_argument("--staged", action="store_true", help="Check the staged diff.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--diff-file", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    project_root = repo_root()
    try:
        report = _build_report_from_args(args, project_root=project_root)
    except (RuntimeError, ValueError) as exc:
        print(f"[hotspot-prevention] {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, sort_keys=True))
    else:
        print(render_text_report(report))
    return 1 if args.strict and report["summary"]["blocked_count"] > 0 else 0


def _build_report_from_args(args: argparse.Namespace, *, project_root: Path) -> dict[str, Any]:
    policy = load_hotspot_policy(Path(args.policy_path), project_root=project_root)
    if args.diff_file:
        diff_text = Path(args.diff_file).read_text()
        numstat_text = None
    else:
        diff_text = collect_git_diff(
            project_root=project_root,
            base=args.base,
            staged=args.staged,
        )
        numstat_text = collect_git_numstat(
            project_root=project_root,
            base=args.base,
            staged=args.staged,
        )
    return build_hotspot_prevention_report(
        diff_text,
        numstat_text=numstat_text,
        policy=policy,
        project_root=project_root,
    )


if __name__ == "__main__":
    raise SystemExit(run())
