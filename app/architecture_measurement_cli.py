from __future__ import annotations

import argparse
import json

from app.architecture_measurements import (
    build_architecture_governance_report,
    record_architecture_measurement,
    summarize_architecture_measurements,
    write_architecture_governance_report,
)


def _add_history_path_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--history-path",
        default=None,
        help=(
            "Path to JSONL measurement history. Defaults to "
            "storage/architecture_inspections/history.jsonl."
        ),
    )


def run_record(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record an architecture inspection measurement.")
    _add_history_path_arg(parser)
    args = parser.parse_args(argv)

    payload = record_architecture_measurement(history_path=args.history_path)
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["valid"] else 1


def run_summary(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize architecture measurement history.")
    _add_history_path_arg(parser)
    args = parser.parse_args(argv)

    payload = summarize_architecture_measurements(path=args.history_path)
    print(json.dumps(payload, sort_keys=True))
    return 0


def run_report(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a CI-friendly architecture governance report."
    )
    _add_history_path_arg(parser)
    parser.add_argument(
        "--output-path",
        default=None,
        help=(
            "Optional JSON output path. Defaults to stdout only; the CI workflow "
            "writes build/architecture-governance/architecture_governance_report.json."
        ),
    )
    parser.add_argument(
        "--policy-path",
        default=None,
        help="Optional architecture inspection policy path.",
    )
    parser.add_argument(
        "--map-path",
        default=None,
        help="Optional persisted architecture contract map path.",
    )
    parser.add_argument(
        "--fail-on-invalid",
        action="store_true",
        help="Return a non-zero exit code when the embedded inspection is invalid.",
    )
    args = parser.parse_args(argv)

    payload = build_architecture_governance_report(
        history_path=args.history_path,
        policy_path=args.policy_path,
        map_path=args.map_path,
    )
    if args.output_path:
        write_architecture_governance_report(args.output_path, report=payload)
    print(json.dumps(payload, sort_keys=True))
    return 1 if args.fail_on_invalid and not payload["valid"] else 0


if __name__ == "__main__":
    raise SystemExit(run_record())
