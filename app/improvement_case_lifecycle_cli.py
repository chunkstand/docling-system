from __future__ import annotations

import argparse
import json

from app.services.improvement_case_lifecycle import update_improvement_case
from app.services.improvement_cases import IMPROVEMENT_CASE_STATUSES


def run_update(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update an existing improvement case.")
    parser.add_argument(
        "--path",
        default=None,
        help="Path to improvement case registry. Defaults to config/improvement_cases.yaml.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--status", choices=sorted(IMPROVEMENT_CASE_STATUSES))
    parser.add_argument("--deployed-ref")
    parser.add_argument("--deployment-notes")
    parser.add_argument("--metric-name")
    parser.add_argument("--metric-value", type=float)
    parser.add_argument("--measurement-window")
    parser.add_argument("--measurement-notes")
    args = parser.parse_args(argv)

    try:
        payload = update_improvement_case(
            path=args.path,
            case_id=args.case_id,
            status=args.status,
            deployed_ref=args.deployed_ref,
            deployment_notes=args.deployment_notes,
            metric_name=args.metric_name,
            metric_value=args.metric_value,
            measurement_window=args.measurement_window,
            measurement_notes=args.measurement_notes,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(payload.model_dump(mode="json")))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_update())
