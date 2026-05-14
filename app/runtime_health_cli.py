from __future__ import annotations

import argparse
import json
import sys

from app.services.runtime_health import (
    DEFAULT_HEARTBEAT_PROCESS_KINDS,
    build_runtime_health_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate repo-owned runtime health for Compose and operators."
    )
    parser.add_argument(
        "--process-kind",
        action="append",
        choices=sorted(DEFAULT_HEARTBEAT_PROCESS_KINDS),
        help=(
            "Limit the heartbeat freshness check to the listed process kinds. "
            "Repeat the flag to check more than one kind."
        ),
    )
    parser.add_argument(
        "--heartbeat-ttl-seconds",
        type=int,
        default=None,
        help="Override the process heartbeat freshness TTL.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON instead of pretty-printed JSON.",
    )
    return parser


def _resolve_required_process_kinds(process_kinds: list[str] | None) -> tuple[str, ...]:
    if process_kinds:
        return tuple(process_kinds)
    return DEFAULT_HEARTBEAT_PROCESS_KINDS


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    required_process_kinds = _resolve_required_process_kinds(args.process_kind)
    report = build_runtime_health_report(
        include_process_heartbeat_check=True,
        required_process_kinds=required_process_kinds,
        heartbeat_ttl_seconds=args.heartbeat_ttl_seconds,
    )
    separators = (",", ":") if args.compact else None
    indent = None if args.compact else 2
    print(json.dumps(report.model_dump(), indent=indent, separators=separators))
    return 0 if report.status == "ok" else 1


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
