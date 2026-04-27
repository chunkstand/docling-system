from __future__ import annotations

import argparse
import json

from app.services.improvement_case_intake import (
    run_improvement_case_import as run_improvement_case_import_workflow,
)


def _parse_source_path_pairs(raw_values: list[str]) -> dict[str, str]:
    source_paths: dict[str, str] = {}
    for raw_value in raw_values:
        if "=" not in raw_value:
            raise ValueError("--source-path-for must use SOURCE=PATH.")
        source, path = raw_value.split("=", 1)
        if not source or not path:
            raise ValueError("--source-path-for must use SOURCE=PATH.")
        if source in source_paths:
            raise ValueError(f"Duplicate --source-path-for source: {source}.")
        source_paths[source] = path
    return source_paths


def run_import(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import observed failures into the registry.")
    parser.add_argument(
        "--path",
        default=None,
        help="Path to improvement case registry. Defaults to config/improvement_cases.yaml.",
    )
    parser.add_argument("--source", default="hygiene", help="Import source.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--workflow-version", default="improvement_v1")
    parser.add_argument("--source-path", default=None, help="Optional file-backed source path.")
    parser.add_argument(
        "--source-path-for",
        action="append",
        default=[],
        metavar="SOURCE=PATH",
        help="Per-source file-backed import source path.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        payload = run_improvement_case_import_workflow(
            source=args.source,
            limit=args.limit,
            workflow_version=args.workflow_version,
            path=args.path,
            source_path=args.source_path,
            source_paths=_parse_source_path_pairs(args.source_path_for),
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(payload.model_dump(mode="json")))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_import())
