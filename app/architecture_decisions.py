from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from app.core.files import repo_root

ARCHITECTURE_DECISION_SCHEMA_NAME = "architecture_decisions"
ARCHITECTURE_DECISION_MAP_SCHEMA_NAME = "architecture_decision_map"
ARCHITECTURE_DECISION_SCHEMA_VERSION = "1.0"
DEFAULT_ARCHITECTURE_DECISION_REGISTRY_PATH = Path("docs") / "architecture_decisions.yaml"
DEFAULT_ARCHITECTURE_DECISION_MAP_PATH = Path("docs") / "architecture_decision_map.json"
ARCHITECTURE_DECISION_STATUSES = frozenset({"accepted", "proposed", "superseded", "deprecated"})
CURRENT_CONTRACT_DECISION_STATUSES = frozenset({"accepted"})
REQUIRED_TEXT_FIELDS = ("id", "status", "date", "title", "context", "decision")
REQUIRED_LIST_FIELDS = ("consequences", "linked_contracts", "linked_sources")


@dataclass(frozen=True, slots=True)
class ArchitectureDecisionIssue:
    contract: str
    field: str
    message: str
    relative_path: str | None = None
    lineno: int | None = None
    symbol: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _registry_path(project_root: Path, path: str | Path | None = None) -> Path:
    raw_path = Path(path) if path is not None else DEFAULT_ARCHITECTURE_DECISION_REGISTRY_PATH
    return raw_path if raw_path.is_absolute() else project_root / raw_path


def _map_path(project_root: Path, path: str | Path | None = None) -> Path:
    raw_path = Path(path) if path is not None else DEFAULT_ARCHITECTURE_DECISION_MAP_PATH
    return raw_path if raw_path.is_absolute() else project_root / raw_path


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_registry_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text()) or {}
    return payload if isinstance(payload, dict) else {}


def _architecture_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _decision_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("decisions")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def build_architecture_decision_map(
    project_root: Path | None = None,
    *,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    root = project_root or repo_root()
    resolved_registry_path = _registry_path(root, registry_path)
    payload = _load_registry_payload(resolved_registry_path)
    decisions = []
    contract_links: dict[str, list[str]] = {}

    for row in _decision_rows(payload):
        decision_id = str(row.get("id", "")).strip()
        linked_contracts = sorted(set(_architecture_string_list(row.get("linked_contracts"))))
        linked_sources = sorted(set(_architecture_string_list(row.get("linked_sources"))))
        decisions.append(
            {
                "id": decision_id,
                "status": str(row.get("status", "")).strip(),
                "date": str(row.get("date", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "context": str(row.get("context", "")).strip(),
                "decision": str(row.get("decision", "")).strip(),
                "consequences": _architecture_string_list(row.get("consequences")),
                "linked_contracts": linked_contracts,
                "linked_sources": linked_sources,
            }
        )
        for contract_name in linked_contracts:
            contract_links.setdefault(contract_name, []).append(decision_id)

    return {
        "schema_name": ARCHITECTURE_DECISION_MAP_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_DECISION_SCHEMA_VERSION,
        "registry_source": _relative_path(root, resolved_registry_path),
        "decision_count": len(decisions),
        "decisions": sorted(decisions, key=lambda decision: decision["id"]),
        "contract_decision_links": [
            {
                "contract": contract_name,
                "decision_ids": sorted(decision_ids),
            }
            for contract_name, decision_ids in sorted(contract_links.items())
        ],
    }


def write_architecture_decision_map(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
    registry_path: str | Path | None = None,
) -> Path:
    root = project_root or repo_root()
    resolved_path = _map_path(root, path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(
            build_architecture_decision_map(root, registry_path=registry_path),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return resolved_path


def _base_registry_issues(
    project_root: Path,
    registry_path: Path,
) -> list[ArchitectureDecisionIssue]:
    relative_registry_path = _relative_path(project_root, registry_path)
    if not registry_path.exists():
        return [
            ArchitectureDecisionIssue(
                contract="architecture_decisions",
                field="registry",
                relative_path=relative_registry_path,
                message="Architecture decision registry is missing.",
            )
        ]

    payload = yaml.safe_load(registry_path.read_text()) or {}
    if not isinstance(payload, dict):
        return [
            ArchitectureDecisionIssue(
                contract="architecture_decisions",
                field="registry",
                relative_path=relative_registry_path,
                message="Architecture decision registry must be a YAML mapping.",
            )
        ]

    issues: list[ArchitectureDecisionIssue] = []
    if payload.get("schema_name") != ARCHITECTURE_DECISION_SCHEMA_NAME:
        issues.append(
            ArchitectureDecisionIssue(
                contract="architecture_decisions",
                field="schema_name",
                relative_path=relative_registry_path,
                message="Architecture decision registry has the wrong schema_name.",
            )
        )
    if str(payload.get("schema_version", "")) != ARCHITECTURE_DECISION_SCHEMA_VERSION:
        issues.append(
            ArchitectureDecisionIssue(
                contract="architecture_decisions",
                field="schema_version",
                relative_path=relative_registry_path,
                message="Architecture decision registry has the wrong schema_version.",
            )
        )
    if not isinstance(payload.get("decisions"), list) or not payload.get("decisions"):
        issues.append(
            ArchitectureDecisionIssue(
                contract="architecture_decisions",
                field="decisions",
                relative_path=relative_registry_path,
                message="Architecture decision registry must contain decision records.",
            )
        )
    return issues


def _decision_row_issues(
    project_root: Path,
    registry_path: Path,
    payload: dict[str, Any],
) -> list[ArchitectureDecisionIssue]:
    relative_registry_path = _relative_path(project_root, registry_path)
    issues: list[ArchitectureDecisionIssue] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(payload.get("decisions") or []):
        symbol = str(row.get("id", f"decision[{index}]")).strip() if isinstance(row, dict) else None
        if not isinstance(row, dict):
            issues.append(
                ArchitectureDecisionIssue(
                    contract="architecture_decisions",
                    field="decision",
                    relative_path=relative_registry_path,
                    symbol=f"decision[{index}]",
                    message="Decision records must be YAML mappings.",
                )
            )
            continue

        for field in REQUIRED_TEXT_FIELDS:
            if not str(row.get(field, "")).strip():
                issues.append(
                    ArchitectureDecisionIssue(
                        contract="architecture_decisions",
                        field=field,
                        relative_path=relative_registry_path,
                        symbol=symbol,
                        message=f"Decision records must declare a non-empty {field}.",
                    )
                )

        decision_id = str(row.get("id", "")).strip()
        if decision_id:
            if decision_id in seen_ids:
                issues.append(
                    ArchitectureDecisionIssue(
                        contract="architecture_decisions",
                        field="id",
                        relative_path=relative_registry_path,
                        symbol=decision_id,
                        message="Decision ids must be unique.",
                    )
                )
            seen_ids.add(decision_id)

        status = str(row.get("status", "")).strip()
        if status and status not in ARCHITECTURE_DECISION_STATUSES:
            issues.append(
                ArchitectureDecisionIssue(
                    contract="architecture_decisions",
                    field="status",
                    relative_path=relative_registry_path,
                    symbol=symbol,
                    message="Decision status must be one of the allowed lifecycle states.",
                )
            )

        for field in REQUIRED_LIST_FIELDS:
            if not _architecture_string_list(row.get(field)):
                issues.append(
                    ArchitectureDecisionIssue(
                        contract="architecture_decisions",
                        field=field,
                        relative_path=relative_registry_path,
                        symbol=symbol,
                        message=f"Decision records must declare at least one {field} entry.",
                    )
                )

        for source in _architecture_string_list(row.get("linked_sources")):
            if not (project_root / source).exists():
                issues.append(
                    ArchitectureDecisionIssue(
                        contract="architecture_decisions",
                        field="linked_sources",
                        relative_path=relative_registry_path,
                        symbol=f"{symbol}:{source}",
                        message="Decision linked_sources entries must exist in the repo.",
                    )
                )
    return issues


def _contract_coverage_issues(
    project_root: Path,
    registry_path: Path,
    expected_contracts: tuple[str, ...] | None,
) -> list[ArchitectureDecisionIssue]:
    if expected_contracts is None:
        return []
    payload = _load_registry_payload(registry_path)
    all_linked_contracts = {
        contract_name
        for row in _decision_rows(payload)
        for contract_name in _architecture_string_list(row.get("linked_contracts"))
    }
    current_linked_contracts = {
        contract_name
        for row in _decision_rows(payload)
        if str(row.get("status", "")).strip() in CURRENT_CONTRACT_DECISION_STATUSES
        for contract_name in _architecture_string_list(row.get("linked_contracts"))
    }
    relative_registry_path = _relative_path(project_root, registry_path)
    expected_contract_set = set(expected_contracts)
    issues = [
        ArchitectureDecisionIssue(
            contract="architecture_decisions",
            field="linked_contracts",
            relative_path=relative_registry_path,
            symbol=contract_name,
            message="Architecture contract lacks an accepted linked decision record.",
        )
        for contract_name in sorted(expected_contract_set - current_linked_contracts)
    ]
    issues.extend(
        ArchitectureDecisionIssue(
            contract="architecture_decisions",
            field="linked_contracts",
            relative_path=relative_registry_path,
            symbol=contract_name,
            message="Decision links an unknown architecture contract.",
        )
        for contract_name in sorted(all_linked_contracts - expected_contract_set)
    )
    return issues


def _persisted_map_issues(
    project_root: Path,
    registry_path: Path,
    map_path: Path,
) -> list[ArchitectureDecisionIssue]:
    relative_map_path = _relative_path(project_root, map_path)
    if not map_path.exists():
        return [
            ArchitectureDecisionIssue(
                contract="architecture_decision_map",
                field="persisted_map",
                relative_path=relative_map_path,
                message=(
                    "Committed architecture decision map is missing; run "
                    "`uv run docling-system-architecture-decisions --write-map`."
                ),
            )
        ]
    if json.loads(map_path.read_text()) != build_architecture_decision_map(
        project_root,
        registry_path=registry_path,
    ):
        return [
            ArchitectureDecisionIssue(
                contract="architecture_decision_map",
                field="persisted_map",
                relative_path=relative_map_path,
                message=(
                    "Committed architecture decision map is stale; run "
                    "`uv run docling-system-architecture-decisions --write-map`."
                ),
            )
        ]
    return []


def validate_architecture_decisions(
    project_root: Path | None = None,
    *,
    registry_path: str | Path | None = None,
    map_path: str | Path | None = None,
    expected_contracts: tuple[str, ...] | None = None,
) -> list[ArchitectureDecisionIssue]:
    root = project_root or repo_root()
    resolved_registry_path = _registry_path(root, registry_path)
    resolved_map_path = _map_path(root, map_path)
    issues = _base_registry_issues(root, resolved_registry_path)
    payload = _load_registry_payload(resolved_registry_path)
    issues.extend(_decision_row_issues(root, resolved_registry_path, payload))
    issues.extend(_contract_coverage_issues(root, resolved_registry_path, expected_contracts))
    issues.extend(_persisted_map_issues(root, resolved_registry_path, resolved_map_path))
    return issues


def _default_expected_contracts() -> tuple[str, ...]:
    from app.architecture_inspection import build_architecture_contract_map

    return tuple(
        str(contract["name"])
        for contract in build_architecture_contract_map()["contracts"]
    )


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect architecture decision records and emit a machine-readable map."
    )
    parser.add_argument("--write-map", action="store_true")
    parser.add_argument(
        "--registry-path",
        default=str(DEFAULT_ARCHITECTURE_DECISION_REGISTRY_PATH),
        help="Path to the canonical architecture decision registry.",
    )
    parser.add_argument(
        "--map-path",
        default=str(DEFAULT_ARCHITECTURE_DECISION_MAP_PATH),
        help="Path to the persisted architecture decision map.",
    )
    args = parser.parse_args(argv)

    if args.write_map:
        path = write_architecture_decision_map(
            args.map_path,
            registry_path=args.registry_path,
        )
        print(
            json.dumps(
                {
                    "schema_name": "architecture_decision_map_write",
                    "schema_version": ARCHITECTURE_DECISION_SCHEMA_VERSION,
                    "path": _relative_path(repo_root(), path),
                },
                sort_keys=True,
            )
        )
        return 0

    payload = build_architecture_decision_map(registry_path=args.registry_path)
    issues = validate_architecture_decisions(
        registry_path=args.registry_path,
        map_path=args.map_path,
        expected_contracts=_default_expected_contracts(),
    )
    payload["valid"] = not issues
    payload["issues"] = [issue.to_dict() for issue in issues]
    print(json.dumps(payload, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(run())
