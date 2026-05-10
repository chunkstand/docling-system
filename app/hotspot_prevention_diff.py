from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.files import repo_root


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
class DiffStat:
    relative_path: str
    added_line_count: int | None
    deleted_line_count: int | None
    source: str


_HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_unified_diff(diff_text: str) -> dict[str, ChangedFile]:
    files: dict[str, list[ChangedLine]] = {}
    deleted_counts: dict[str, int] = {}
    current_path: str | None = None
    new_lineno: int | None = None
    hunk_id = 0

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            current_path = _path_from_diff_header(raw_line)
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


def _path_from_diff_header(raw_line: str) -> str | None:
    candidate = strip_git_prefix(raw_line[4:].split("\t", 1)[0])
    return None if candidate == "/dev/null" else candidate


def strip_git_prefix(path_value: str) -> str:
    value = path_value.strip()
    if value == "/dev/null":
        return value
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value


def parse_numstat(numstat_text: str) -> dict[str, DiffStat]:
    stats: dict[str, DiffStat] = {}
    for raw_line in numstat_text.splitlines():
        parts = raw_line.split("\t")
        if len(parts) < 3:
            continue
        added_raw, deleted_raw, raw_path = parts[0], parts[1], parts[-1]
        relative_path = normalize_numstat_path(raw_path)
        stats[relative_path] = DiffStat(
            relative_path=relative_path,
            added_line_count=None if added_raw == "-" else int(added_raw),
            deleted_line_count=None if deleted_raw == "-" else int(deleted_raw),
            source="numstat",
        )
    return stats


def normalize_numstat_path(raw_path: str) -> str:
    value = raw_path.strip()
    if " => " in value:
        right = value.split(" => ", 1)[1]
        if right.endswith("}"):
            prefix = value.split("{", 1)[0]
            return f"{prefix}{right[:-1]}"
        return right
    return value


def fallback_diff_stats(changed_files: dict[str, ChangedFile]) -> dict[str, DiffStat]:
    return {
        relative_path: DiffStat(
            relative_path=relative_path,
            added_line_count=len(changed_file.added_lines),
            deleted_line_count=changed_file.deleted_line_count,
            source="unified_diff",
        )
        for relative_path, changed_file in changed_files.items()
    }


def collect_git_diff(
    *,
    project_root: Path | None = None,
    base: str | None = None,
    staged: bool = False,
) -> str:
    completed = subprocess.run(
        git_diff_command(base=base, staged=staged),
        cwd=project_root or repo_root(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git diff failed")
    return completed.stdout


def collect_git_numstat(
    *,
    project_root: Path | None = None,
    base: str | None = None,
    staged: bool = False,
) -> str:
    completed = subprocess.run(
        git_diff_command(base=base, staged=staged, numstat=True),
        cwd=project_root or repo_root(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git diff --numstat failed")
    return completed.stdout


def git_diff_command(
    *,
    base: str | None = None,
    staged: bool = False,
    numstat: bool = False,
) -> list[str]:
    if base and staged:
        raise ValueError("--base and --staged cannot be used together")
    command = ["git", "diff", "--no-ext-diff"]
    command.append("--numstat" if numstat else "--unified=3")
    if staged:
        command.append("--cached")
    elif base:
        command.append(base)
    return command
