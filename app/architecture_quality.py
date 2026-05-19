from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
    build_architecture_inspection_report,
)
from app.architecture_quality_contracts import (
    ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME,
    ARCHITECTURE_QUALITY_SUMMARY_SCHEMA_NAME,
    DEFAULT_ARCHITECTURE_QUALITY_REPORT_PATH,
)
from app.architecture_quality_hotspots import (
    HOTSPOT_ROUTING_TRAP_STATUSES,
    annotate_hotspots_with_routing,
    load_hotspot_policy_safe,
    quality_candidates_from_hotspots,
)
from app.capability_contracts import build_capability_contract_map
from app.core.files import repo_root
from app.core.time import utcnow
from app.hotspot_prevention_policy import load_hotspot_policy
from app.hygiene import (
    HygieneFinding,
    run_improvement_case_contract_checks,
    run_python_hygiene_checks,
)
from app.services.improvement_cases import load_improvement_case_registry

DEFAULT_QUALITY_ROOTS = ("app", "tests", "docs", "config", ".github")
DEFAULT_CODE_ROOTS = ("app", "tests")
AGENT_LEGIBILITY_BOUNDED_FUNCTION_LIMIT = 25
AGENT_LEGIBILITY_LOW_SCORE_THRESHOLD = 80.0
AGENT_LEGIBILITY_SURFACE_HINTS = {
    "run_lifecycle": {
        "test_paths": ("tests/unit/test_document_service.py", "tests/unit/test_documents_api.py"),
        "example_paths": ("README.md",),
        "trace_commands": ("uv run docling-system-ingest-file --help",),
    },
    "retrieval": {
        "test_paths": (
            "tests/unit/test_search_api.py",
            "tests/unit/test_search_service.py",
            "tests/unit/test_search_history.py",
        ),
        "example_paths": ("docs/retrieval_repair_loop.md",),
        "trace_commands": ("uv run docling-system-run-replay-suite --help",),
    },
    "evaluation": {
        "test_paths": (
            "tests/unit/test_evaluation_service.py",
            "tests/unit/test_eval_workbench_api.py",
        ),
        "example_paths": ("docs/evaluation_data_readiness.md",),
        "trace_commands": ("uv run docling-system-eval-run --help",),
    },
    "semantics": {
        "test_paths": ("tests/unit/test_semantic_backfill_api.py",),
        "example_paths": ("docs/versioning_policy.md",),
        "trace_commands": ("uv run docling-system-semantic-backfill --help",),
    },
    "agent_orchestration": {
        "test_paths": (
            "tests/unit/test_agent_tasks_api.py",
            "tests/unit/test_agent_task_actions.py",
        ),
        "example_paths": ("docs/agentic_architecture_index.md",),
        "trace_commands": ("uv run docling-system-agent-trace-review --help",),
    },
    "system_governance": {
        "test_paths": (
            "tests/unit/test_architecture_inspection.py",
            "tests/unit/test_architecture_quality.py",
        ),
        "example_paths": ("docs/architecture_boundaries.md",),
        "trace_commands": ("uv run docling-system-architecture-quality-report --summary",),
    },
}


def _relative_to_root(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _iter_files(project_root: Path, roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for root_name in roots:
        root_path = project_root / root_name
        if not root_path.exists():
            continue
        if root_path.is_file():
            files.append(root_path)
            continue
        for path in root_path.rglob("*"):
            if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
                continue
            if path.is_file():
                files.append(path)
    return sorted(set(files))


def _count_python_symbols(path: Path) -> tuple[int, int, int]:
    if path.suffix != ".py":
        return 0, 0, 0
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return 0, 0, 0
    public_functions = 0
    private_functions = 0
    class_count = 0
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_count += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                private_functions += 1
            else:
                public_functions += 1
    return public_functions, private_functions, class_count


def collect_file_quality_metrics(
    project_root: Path | None = None,
    *,
    roots: tuple[str, ...] = DEFAULT_CODE_ROOTS,
) -> dict[str, dict[str, int | str]]:
    root = project_root or repo_root()
    metrics: dict[str, dict[str, int | str]] = {}
    for path in _iter_files(root, roots):
        relative_path = _relative_to_root(root, path)
        if path.suffix not in {".py", ".md", ".yaml", ".yml", ".json", ".toml"}:
            continue
        text = path.read_text(errors="ignore")
        public_functions, private_functions, class_count = _count_python_symbols(path)
        metrics[relative_path] = {
            "relative_path": relative_path,
            "line_count": len(text.splitlines()),
            "public_function_count": public_functions,
            "private_function_count": private_functions,
            "class_count": class_count,
        }
    return metrics


def _git_name_counts(
    project_root: Path,
    *,
    since: str,
) -> Counter[str]:
    completed = subprocess.run(
        ["git", "log", f"--since={since}", "--name-only", "--format="],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return Counter()
    return Counter(
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    )


def collect_git_churn_metrics(
    project_root: Path | None = None,
) -> dict[str, dict[str, int]]:
    root = project_root or repo_root()
    churn_30 = _git_name_counts(root, since="30 days ago")
    churn_90 = _git_name_counts(root, since="90 days ago")
    paths = set(churn_30) | set(churn_90)
    return {
        path: {
            "changes_30d": churn_30.get(path, 0),
            "changes_90d": churn_90.get(path, 0),
        }
        for path in sorted(paths)
    }


def _collect_hygiene_findings_by_path(
    project_root: Path,
    *,
    include_hygiene: bool,
) -> dict[str, list[HygieneFinding]]:
    if not include_hygiene:
        return {}
    findings = [
        *run_python_hygiene_checks(project_root),
        *run_improvement_case_contract_checks(project_root),
    ]
    grouped: dict[str, list[HygieneFinding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.relative_path or "global"].append(finding)
    return dict(grouped)


def _improvement_case_registry_index(
    project_root: Path,
) -> tuple[dict[str, int], dict[str, dict[str, str | None]]]:
    registry = load_improvement_case_registry(project_root=project_root)
    counts: dict[str, int] = defaultdict(int)
    case_statuses: dict[str, dict[str, str | None]] = {}
    for case in registry.cases:
        case_statuses[case.case_id] = {
            "status": case.status,
            "deployed_ref": case.deployment.deployed_ref,
        }
        if case.status in {"closed", "suppressed"}:
            continue
        target_path = (case.artifact.target_path or "").strip()
        if target_path:
            counts[target_path] += 1
    return dict(counts), case_statuses


def _open_improvement_cases_by_path(project_root: Path) -> dict[str, int]:
    counts, _case_statuses = _improvement_case_registry_index(project_root)
    return counts


def _risk_score(
    *,
    line_count: int,
    public_function_count: int,
    private_function_count: int,
    class_count: int,
    changes_30d: int,
    changes_90d: int,
    hygiene_finding_count: int,
    open_improvement_case_count: int,
) -> float:
    return round(
        (line_count / 150)
        + (public_function_count * 2.0)
        + (private_function_count * 0.75)
        + (class_count * 1.5)
        + (changes_30d * 5.0)
        + (changes_90d * 2.0)
        + (hygiene_finding_count * 8.0)
        + (open_improvement_case_count * 6.0),
        2,
    )


def _existing_hint_paths(project_root: Path, paths: tuple[str, ...]) -> list[str]:
    return [path for path in paths if (project_root / path).exists()]


def _surface_legibility_score(
    surface: dict[str, Any],
    *,
    project_root: Path,
    decision_ids: list[str],
) -> dict[str, Any]:
    function_count = int(surface.get("function_count") or 0)
    owner_modules = list(surface.get("owner_modules") or [])
    protocol_source = surface.get("protocol_source")
    implementation_source = surface.get("implementation_source")
    hints = AGENT_LEGIBILITY_SURFACE_HINTS.get(str(surface["name"]), {})
    test_paths = _existing_hint_paths(project_root, tuple(hints.get("test_paths", ())))
    example_paths = _existing_hint_paths(project_root, tuple(hints.get("example_paths", ())))
    trace_commands = list(hints.get("trace_commands", ()))
    criteria = {
        "has_public_entrypoint": bool(surface.get("exported_instance")),
        "has_owner_modules": bool(owner_modules),
        "has_protocol_source": bool(protocol_source),
        "has_implementation_source": bool(implementation_source),
        "has_split_contract_source": bool(surface.get("contract_sources")),
        "has_tests": bool(test_paths),
        "has_examples": bool(example_paths),
        "has_trace_or_replay_command": bool(trace_commands),
        "has_decision_rationale": bool(decision_ids),
        "bounded_surface": function_count <= AGENT_LEGIBILITY_BOUNDED_FUNCTION_LIMIT,
    }
    passed = sum(1 for value in criteria.values() if value)
    return {
        "name": surface["name"],
        "module": surface["module"],
        "function_count": function_count,
        "owner_module_count": len(owner_modules),
        "score": round((passed / len(criteria)) * 100, 2),
        "criteria": criteria,
        "test_paths": test_paths,
        "example_paths": example_paths,
        "trace_or_replay_commands": trace_commands,
        "decision_ids": decision_ids,
    }


def _build_hotspots(
    *,
    file_metrics: dict[str, dict[str, int | str]],
    churn_metrics: dict[str, dict[str, int]],
    hygiene_findings_by_path: dict[str, list[HygieneFinding]],
    open_cases_by_path: dict[str, int],
    max_hotspots: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative_path, metrics in file_metrics.items():
        churn = churn_metrics.get(relative_path, {})
        hygiene_findings = hygiene_findings_by_path.get(relative_path, [])
        line_count = int(metrics["line_count"])
        public_function_count = int(metrics["public_function_count"])
        private_function_count = int(metrics["private_function_count"])
        class_count = int(metrics["class_count"])
        changes_30d = int(churn.get("changes_30d", 0))
        changes_90d = int(churn.get("changes_90d", 0))
        open_improvement_case_count = int(open_cases_by_path.get(relative_path, 0))
        score = _risk_score(
            line_count=line_count,
            public_function_count=public_function_count,
            private_function_count=private_function_count,
            class_count=class_count,
            changes_30d=changes_30d,
            changes_90d=changes_90d,
            hygiene_finding_count=len(hygiene_findings),
            open_improvement_case_count=open_improvement_case_count,
        )
        if score <= 0:
            continue
        rows.append(
            {
                "relative_path": relative_path,
                "risk_score": score,
                "line_count": line_count,
                "public_function_count": public_function_count,
                "private_function_count": private_function_count,
                "class_count": class_count,
                "changes_30d": changes_30d,
                "changes_90d": changes_90d,
                "hygiene_finding_count": len(hygiene_findings),
                "open_improvement_case_count": open_improvement_case_count,
                "hygiene_findings": [
                    {
                        "kind": finding.kind,
                        "message": finding.message,
                        "lineno": finding.lineno,
                    }
                    for finding in hygiene_findings[:5]
                ],
            }
        )
    return sorted(
        rows,
        key=lambda row: (-row["risk_score"], row["relative_path"]),
    )[:max_hotspots]


def _legibility_quality_candidates(
    legibility: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for surface in legibility:
        if (
            surface["score"] >= AGENT_LEGIBILITY_LOW_SCORE_THRESHOLD
            and surface["criteria"]["bounded_surface"] is True
        ):
            continue
        module_path = f"{str(surface['module']).replace('.', '/')}.py"
        candidates.append(
            {
                "source_ref": f"architecture-quality:facade:{surface['name']}",
                "title": f"Agent-legibility gap: {surface['name']}",
                "artifact_target_path": module_path,
                "cause_class": "unclear_ownership",
                "observed_failure": (
                    f"{surface['name']} has agent_legibility_score={surface['score']} "
                    f"and function_count={surface['function_count']}."
                ),
                "verification_command": "uv run docling-system-architecture-quality-report",
                "stop_condition": (
                    "Surface is under the bounded function threshold or has explicit "
                    "tests, examples, trace command, and decision rationale."
                ),
            }
        )
    return candidates


def build_architecture_quality_report(
    project_root: Path | None = None,
    *,
    inspection_report: dict[str, Any] | None = None,
    max_hotspots: int = 20,
    include_hygiene: bool = True,
) -> dict[str, Any]:
    root = project_root or repo_root()
    inspection = inspection_report or build_architecture_inspection_report(root)
    capability_contract_map = build_capability_contract_map(root)
    architecture_contracts = {
        str(contract.get("name")): list(contract.get("decision_ids") or [])
        for contract in (inspection.get("architecture_map", {}) or {}).get("contracts", [])
        if isinstance(contract, dict)
    }
    capability_decision_ids = architecture_contracts.get(
        "capability_surface_contracts",
        [],
    )
    file_metrics = collect_file_quality_metrics(root)
    churn_metrics = collect_git_churn_metrics(root)
    hygiene_findings_by_path = _collect_hygiene_findings_by_path(
        root,
        include_hygiene=include_hygiene,
    )
    open_cases_by_path, case_statuses = _improvement_case_registry_index(root)
    hotspots = _build_hotspots(
        file_metrics=file_metrics,
        churn_metrics=churn_metrics,
        hygiene_findings_by_path=hygiene_findings_by_path,
        open_cases_by_path=open_cases_by_path,
        max_hotspots=max_hotspots,
    )
    hotspots = annotate_hotspots_with_routing(
        hotspots,
        policy=load_hotspot_policy_safe(root, loader=load_hotspot_policy),
        case_statuses=case_statuses,
    )
    routed_hotspots = [row for row in hotspots if row["selected_for_routed_queue"]]
    routing_trap_paths = [
        row["relative_path"]
        for row in hotspots
        if row["routing_status"] in HOTSPOT_ROUTING_TRAP_STATUSES
    ]
    legibility = [
        _surface_legibility_score(
            surface,
            project_root=root,
            decision_ids=capability_decision_ids,
        )
        for surface in capability_contract_map["facades"]
    ]
    average_legibility = (
        round(sum(row["score"] for row in legibility) / len(legibility), 2)
        if legibility
        else 0.0
    )
    legibility_candidates = _legibility_quality_candidates(legibility)
    return {
        "schema_name": ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "generated_at": utcnow().isoformat(),
        "valid": inspection["valid"],
        "inspection_violation_count": inspection["violation_count"],
        "source_roots": list(DEFAULT_QUALITY_ROOTS),
        "hotspot_count": len(hotspots),
        "hotspots": hotspots,
        "agent_legibility": {
            "surface_count": len(legibility),
            "average_score": average_legibility,
            "bounded_function_limit": AGENT_LEGIBILITY_BOUNDED_FUNCTION_LIMIT,
            "low_score_threshold": AGENT_LEGIBILITY_LOW_SCORE_THRESHOLD,
            "surfaces": legibility,
        },
        "improvement_case_candidates": [
            *quality_candidates_from_hotspots(routed_hotspots),
            *legibility_candidates,
        ],
        "raw_improvement_case_candidates": [
            *quality_candidates_from_hotspots(hotspots),
            *legibility_candidates,
        ],
        "summary": {
            "top_hotspot_paths": [row["relative_path"] for row in hotspots[:5]],
            "top_routed_hotspot_paths": [
                row["relative_path"] for row in routed_hotspots[:5]
            ],
            "routing_trap_paths": routing_trap_paths,
            "stale_facade_hotspot_count": len(routing_trap_paths),
            "max_hotspot_risk_score": hotspots[0]["risk_score"] if hotspots else 0.0,
            "agent_legibility_average_score": average_legibility,
            "broad_facade_count": sum(
                1 for row in legibility if row["criteria"]["bounded_surface"] is False
            ),
        },
    }


def build_architecture_quality_summary(
    project_root: Path | None = None,
    *,
    inspection_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = build_architecture_quality_report(
        project_root,
        inspection_report=inspection_report,
        max_hotspots=20,
        include_hygiene=False,
    )
    return {
        "schema_name": ARCHITECTURE_QUALITY_SUMMARY_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "hotspot_count": report["hotspot_count"],
        "top_hotspot_paths": report["summary"]["top_hotspot_paths"],
        "top_routed_hotspot_paths": report["summary"]["top_routed_hotspot_paths"],
        "routing_trap_paths": report["summary"]["routing_trap_paths"],
        "stale_facade_hotspot_count": report["summary"]["stale_facade_hotspot_count"],
        "max_hotspot_risk_score": report["summary"]["max_hotspot_risk_score"],
        "agent_legibility_average_score": report["summary"][
            "agent_legibility_average_score"
        ],
        "broad_facade_count": report["summary"]["broad_facade_count"],
    }


def write_architecture_quality_report(
    path: str | Path | None = None,
    *,
    report: dict[str, Any] | None = None,
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    raw_path = Path(path) if path is not None else DEFAULT_ARCHITECTURE_QUALITY_REPORT_PATH
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report or build_architecture_quality_report(root)
    resolved_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return resolved_path


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an architecture quality and hotspot report."
    )
    parser.add_argument("--max-hotspots", type=int, default=20)
    parser.add_argument(
        "--skip-hygiene",
        action="store_true",
        help="Skip Python hygiene findings while ranking hotspots.",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help="Optional JSON output path. Defaults to stdout only.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print the compact quality summary instead of the full report.",
    )
    args = parser.parse_args(argv)

    if args.summary:
        payload = build_architecture_quality_summary()
    else:
        payload = build_architecture_quality_report(
            max_hotspots=args.max_hotspots,
            include_hygiene=not args.skip_hygiene,
        )
    if args.output_path:
        write_architecture_quality_report(args.output_path, report=payload)
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(run())
