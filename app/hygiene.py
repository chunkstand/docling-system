from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.services.improvement_cases import (
    DEFAULT_IMPROVEMENT_CASES_PATH,
    load_improvement_case_registry_for_validation,
    validate_improvement_case_registry,
)

DEFAULT_POLICY_PATH = Path("config") / "hygiene_policy.yaml"
DEFAULT_RUFF_BASELINE_PATH = Path("config") / "ruff_baseline.yaml"
DEFAULT_VULTURE_CONFIDENCE = 85


@dataclass(frozen=True)
class PrivateHelper:
    name: str
    relative_path: str
    lineno: int
    body_fingerprint: str


@dataclass(frozen=True)
class FileBudget:
    max_lines: int | None = None
    max_private_helpers: int | None = None


@dataclass(frozen=True)
class HygienePolicy:
    duplicate_helper_name_allowances: dict[str, frozenset[str]]
    duplicate_helper_body_allowances: frozenset[frozenset[str]]
    default_file_budget: FileBudget
    file_budgets: dict[str, FileBudget]


@dataclass(frozen=True)
class HygieneFinding:
    kind: str
    message: str
    relative_path: str | None = None
    lineno: int | None = None

    def render(self) -> str:
        location = ""
        if self.relative_path is not None:
            location = self.relative_path
            if self.lineno is not None:
                location = f"{location}:{self.lineno}"
            location = f"{location}: "
        return f"{location}{self.kind}: {self.message}"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _relative_to_project(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def _iter_python_files(project_root: Path, roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for root_name in roots:
        root_path = (project_root / root_name).resolve()
        if not root_path.exists():
            continue
        for path in root_path.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return sorted(set(files))


def _helper_body_fingerprint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    normalized = ast.Module(
        body=[
            node.__class__(
                name="_helper",
                args=node.args,
                body=node.body,
                decorator_list=node.decorator_list,
                returns=node.returns,
                type_comment=node.type_comment,
                type_params=getattr(node, "type_params", []),
            )
        ],
        type_ignores=[],
    )
    return ast.dump(normalized, include_attributes=False)


def collect_private_helpers(
    project_root: Path | None = None,
    *,
    roots: tuple[str, ...] = ("app",),
) -> list[PrivateHelper]:
    root = project_root or _project_root()
    helpers: list[PrivateHelper] = []
    for path in _iter_python_files(root, roots):
        tree = ast.parse(path.read_text())
        relative_path = _relative_to_project(root, path)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("_"):
                continue
            if node.name.startswith("__") and node.name.endswith("__"):
                continue
            helpers.append(
                PrivateHelper(
                    name=node.name,
                    relative_path=relative_path,
                    lineno=node.lineno,
                    body_fingerprint=_helper_body_fingerprint(node),
                )
            )
    return helpers


def load_hygiene_policy(
    policy_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> HygienePolicy:
    root = project_root or _project_root()
    resolved_policy_path = (root / (policy_path or DEFAULT_POLICY_PATH)).resolve()
    payload = yaml.safe_load(resolved_policy_path.read_text()) or {}

    duplicate_allowances: dict[str, frozenset[str]] = {}
    for row in payload.get("duplicate_helper_names") or []:
        name = str(row["name"]).strip()
        modules = frozenset(str(module).strip() for module in row.get("modules") or [])
        duplicate_allowances[name] = modules
    duplicate_body_allowances = frozenset(
        frozenset(str(helper).strip() for helper in row.get("helpers") or [])
        for row in payload.get("duplicate_helper_bodies") or []
    )

    budget_payload = payload.get("file_budgets") or {}
    default_budget = FileBudget(
        max_lines=budget_payload.get("defaults", {}).get("max_lines"),
        max_private_helpers=budget_payload.get("defaults", {}).get("max_private_helpers"),
    )
    file_budgets = {
        str(relative_path): FileBudget(
            max_lines=values.get("max_lines"),
            max_private_helpers=values.get("max_private_helpers"),
        )
        for relative_path, values in (budget_payload.get("overrides") or {}).items()
    }
    return HygienePolicy(
        duplicate_helper_name_allowances=duplicate_allowances,
        duplicate_helper_body_allowances=duplicate_body_allowances,
        default_file_budget=default_budget,
        file_budgets=file_budgets,
    )


def find_duplicate_helper_name_findings(
    helpers: list[PrivateHelper],
    policy: HygienePolicy,
) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    grouped: dict[str, list[PrivateHelper]] = defaultdict(list)
    for helper in helpers:
        grouped[helper.name].append(helper)

    for helper_name, rows in sorted(grouped.items()):
        if len(rows) < 2:
            continue
        actual_modules = frozenset(row.relative_path for row in rows)
        allowed_modules = policy.duplicate_helper_name_allowances.get(helper_name)
        if actual_modules == allowed_modules:
            continue
        module_list = ", ".join(sorted(actual_modules))
        findings.append(
            HygieneFinding(
                kind="duplicate_helper_name",
                message=f"{helper_name} appears in multiple modules: {module_list}",
            )
        )
    return findings


def _helper_identity(helper: PrivateHelper) -> str:
    return f"{helper.relative_path}:{helper.name}"


def find_duplicate_helper_body_findings(
    helpers: list[PrivateHelper],
    policy: HygienePolicy,
) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    grouped: dict[str, list[PrivateHelper]] = defaultdict(list)
    for helper in helpers:
        grouped[helper.body_fingerprint].append(helper)

    for rows in sorted(grouped.values(), key=len, reverse=True):
        if len(rows) < 2:
            continue
        helper_identities = frozenset(_helper_identity(row) for row in rows)
        if helper_identities in policy.duplicate_helper_body_allowances:
            continue
        modules = ", ".join(f"{row.relative_path}:{row.lineno}" for row in rows)
        findings.append(
            HygieneFinding(
                kind="duplicate_helper_body",
                message=f"identical helper bodies found in {modules}",
            )
        )
    return findings


def _normalize_ruff_filename(project_root: Path, filename: str) -> str:
    path = Path(filename)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    try:
        return path.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_ruff_baseline(
    baseline_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, dict[str, int]]:
    root = project_root or _project_root()
    resolved_baseline_path = (root / (baseline_path or DEFAULT_RUFF_BASELINE_PATH)).resolve()
    if not resolved_baseline_path.exists():
        return {}

    payload = yaml.safe_load(resolved_baseline_path.read_text()) or {}
    baseline_payload = payload.get("ruff_baseline") or {}
    return {
        str(relative_path): {
            str(code): int(count) for code, count in sorted((counts or {}).items())
        }
        for relative_path, counts in sorted(baseline_payload.items())
    }


def write_ruff_baseline(
    violation_counts: dict[str, dict[str, int]],
    baseline_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    root = project_root or _project_root()
    resolved_baseline_path = (root / (baseline_path or DEFAULT_RUFF_BASELINE_PATH)).resolve()
    resolved_baseline_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ruff_baseline": {
            relative_path: {code: count for code, count in sorted(counts.items())}
            for relative_path, counts in sorted(violation_counts.items())
        }
    }
    resolved_baseline_path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return resolved_baseline_path


def collect_ruff_violation_counts(
    project_root: Path | None = None,
    *,
    targets: tuple[str, ...] = (".",),
    python_executable: str | None = None,
) -> dict[str, dict[str, int]]:
    root = project_root or _project_root()
    executable = python_executable or sys.executable
    command = [
        executable,
        "-m",
        "ruff",
        "check",
        *targets,
        "--output-format",
        "json",
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 1):
        stderr = completed.stderr.strip()
        raise RuntimeError(stderr or "ruff execution failed")

    try:
        rows = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("ruff returned invalid JSON output") from exc

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        relative_path = _normalize_ruff_filename(root, row["filename"])
        counts[relative_path][row["code"]] += 1

    return {
        relative_path: dict(sorted(code_counts.items()))
        for relative_path, code_counts in sorted(counts.items())
    }


def find_ruff_regression_findings(
    current_counts: dict[str, dict[str, int]],
    baseline_counts: dict[str, dict[str, int]],
) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    for relative_path, code_counts in sorted(current_counts.items()):
        baseline_code_counts = baseline_counts.get(relative_path, {})
        for code, current_count in sorted(code_counts.items()):
            baseline_count = baseline_code_counts.get(code, 0)
            if current_count <= baseline_count:
                continue
            findings.append(
                HygieneFinding(
                    kind="ruff_regression",
                    relative_path=relative_path,
                    message=f"{code} count {current_count} exceeds baseline {baseline_count}",
                )
            )
    return findings


def find_file_budget_findings(
    project_root: Path | None = None,
    *,
    policy: HygienePolicy,
    roots: tuple[str, ...] = ("app",),
) -> list[HygieneFinding]:
    root = project_root or _project_root()
    helper_counts: dict[str, int] = defaultdict(int)
    for helper in collect_private_helpers(root, roots=roots):
        helper_counts[helper.relative_path] += 1

    findings: list[HygieneFinding] = []
    for path in _iter_python_files(root, roots):
        relative_path = _relative_to_project(root, path)
        budget = policy.file_budgets.get(relative_path, policy.default_file_budget)
        line_count = len(path.read_text().splitlines())
        helper_count = helper_counts.get(relative_path, 0)
        if budget.max_lines is not None and line_count > budget.max_lines:
            findings.append(
                HygieneFinding(
                    kind="file_budget",
                    relative_path=relative_path,
                    message=f"{line_count} lines exceeds budget {budget.max_lines}",
                )
            )
        if budget.max_private_helpers is not None and helper_count > budget.max_private_helpers:
            findings.append(
                HygieneFinding(
                    kind="helper_budget",
                    relative_path=relative_path,
                    message=(
                        f"{helper_count} private helpers exceeds budget "
                        f"{budget.max_private_helpers}"
                    ),
                )
            )
    return findings


def run_python_hygiene_checks(
    project_root: Path | None = None,
    *,
    policy_path: Path | None = None,
    roots: tuple[str, ...] = ("app",),
) -> list[HygieneFinding]:
    root = project_root or _project_root()
    policy = load_hygiene_policy(policy_path, project_root=root)
    helpers = collect_private_helpers(root, roots=roots)
    findings = [
        *find_duplicate_helper_name_findings(helpers, policy),
        *find_duplicate_helper_body_findings(helpers, policy),
        *find_file_budget_findings(root, policy=policy, roots=roots),
    ]
    return sorted(
        findings,
        key=lambda row: (row.relative_path or "", row.lineno or 0, row.kind, row.message),
    )


def _registry_relative_path(project_root: Path, path: Path) -> str:
    resolved_path = path if path.is_absolute() else project_root / path
    try:
        return resolved_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(resolved_path)


def run_improvement_case_contract_checks(
    project_root: Path | None = None,
    *,
    registry_path: Path | None = None,
) -> list[HygieneFinding]:
    root = project_root or _project_root()
    path = registry_path or DEFAULT_IMPROVEMENT_CASES_PATH
    registry, load_issues = load_improvement_case_registry_for_validation(
        path,
        project_root=root,
    )
    contract_issues = list(load_issues)
    if not load_issues:
        contract_issues.extend(
            validate_improvement_case_registry(registry, project_root=root)
        )
    relative_path = _registry_relative_path(root, path)
    return [
        HygieneFinding(
            kind="improvement_case_contract",
            relative_path=relative_path,
            message=f"{issue.field}: {issue.message}",
        )
        for issue in contract_issues
    ]


def run_architecture_contract_checks(project_root: Path | None = None) -> list[HygieneFinding]:
    from app.architecture_inspection import inspect_architecture_contracts

    root = project_root or _project_root()
    return [
        HygieneFinding(
            kind="architecture_contract",
            relative_path=violation.relative_path,
            lineno=violation.lineno,
            message=f"{violation.contract}.{violation.field}: {violation.message}",
        )
        for violation in inspect_architecture_contracts(root)
    ]


def _run_external_check(description: str, command: list[str], *, cwd: Path) -> int:
    print(f"[hygiene] {description}: {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd)
    return completed.returncode


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run dead-code and helper hygiene checks.")
    parser.add_argument(
        "--skip-ruff",
        action="store_true",
        help="Skip ruff linting.",
    )
    parser.add_argument(
        "--skip-vulture",
        action="store_true",
        help="Skip the dead-code scan.",
    )
    parser.add_argument(
        "--skip-python-hygiene",
        action="store_true",
        help="Skip duplicate-helper and file-budget checks.",
    )
    parser.add_argument(
        "--skip-improvement-cases",
        action="store_true",
        help="Skip improvement-case registry contract checks.",
    )
    parser.add_argument(
        "--skip-architecture",
        action="store_true",
        help="Skip architecture contract checks.",
    )
    parser.add_argument(
        "--policy-path",
        default=str(DEFAULT_POLICY_PATH),
        help="Path to the hygiene policy file, relative to the repo root.",
    )
    parser.add_argument(
        "--ruff-baseline-path",
        default=str(DEFAULT_RUFF_BASELINE_PATH),
        help="Path to the ruff count baseline file, relative to the repo root.",
    )
    parser.add_argument(
        "--write-ruff-baseline",
        action="store_true",
        help="Write the current ruff violation counts to the baseline file and exit.",
    )
    args = parser.parse_args(argv)

    project_root = _project_root()
    failed = False

    if args.write_ruff_baseline:
        baseline_path = write_ruff_baseline(
            collect_ruff_violation_counts(
                project_root,
                python_executable=sys.executable,
            ),
            baseline_path=Path(args.ruff_baseline_path),
            project_root=project_root,
        )
        print(f"[hygiene] wrote ruff baseline to {baseline_path.relative_to(project_root)}")
        return 0

    if not args.skip_ruff:
        try:
            current_counts = collect_ruff_violation_counts(
                project_root,
                python_executable=sys.executable,
            )
        except RuntimeError as exc:
            print(f"[hygiene] ruff: {exc}")
            failed = True
        else:
            baseline_counts = load_ruff_baseline(
                Path(args.ruff_baseline_path),
                project_root=project_root,
            )
            findings = find_ruff_regression_findings(current_counts, baseline_counts)
            if findings:
                print("[hygiene] ruff regressions:")
                for finding in findings:
                    print(f"  - {finding.render()}")
                failed = True
            else:
                print("[hygiene] ruff regressions: none")

    if not args.skip_vulture:
        vulture_command = [
            sys.executable,
            "-m",
            "vulture",
            "app",
            "config/vulture_whitelist.py",
            "--min-confidence",
            str(DEFAULT_VULTURE_CONFIDENCE),
        ]
        failed = _run_external_check("vulture", vulture_command, cwd=project_root) != 0 or failed

    if not args.skip_python_hygiene:
        findings = run_python_hygiene_checks(
            project_root,
            policy_path=Path(args.policy_path),
        )
        if findings:
            print("[hygiene] duplicate/budget findings:")
            for finding in findings:
                print(f"  - {finding.render()}")
            failed = True
        else:
            print("[hygiene] duplicate/budget findings: none")

    if not args.skip_improvement_cases:
        findings = run_improvement_case_contract_checks(project_root)
        if findings:
            print("[hygiene] improvement-case findings:")
            for finding in findings:
                print(f"  - {finding.render()}")
            failed = True
        else:
            print("[hygiene] improvement-case findings: none")

    if not args.skip_architecture:
        findings = run_architecture_contract_checks(project_root)
        if findings:
            print("[hygiene] architecture findings:")
            for finding in findings:
                print(f"  - {finding.render()}")
            failed = True
        else:
            print("[hygiene] architecture findings: none")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
