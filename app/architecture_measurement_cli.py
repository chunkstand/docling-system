from __future__ import annotations

import argparse
import json

from app.architecture_measurements import (
    record_architecture_measurement,
    summarize_architecture_measurements,
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


if __name__ == "__main__":
    raise SystemExit(run_record())
