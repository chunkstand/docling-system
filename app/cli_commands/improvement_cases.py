from __future__ import annotations

import argparse
import json

from app.services.improvement_cases import (
    IMPROVEMENT_ARTIFACT_TYPES,
    IMPROVEMENT_CASE_STATUSES,
    IMPROVEMENT_CAUSE_CLASSES,
    IMPROVEMENT_SOURCE_TYPES,
    build_improvement_case_manifest,
    filter_improvement_cases,
    load_improvement_case_registry,
    load_improvement_case_registry_for_validation,
    record_improvement_case,
    summarize_improvement_cases,
    validate_improvement_case_registry,
)


def _improvement_case_issue_payload(issue) -> dict:
    return {
        "case_id": issue.case_id,
        "field": issue.field,
        "message": issue.message,
    }


def _add_improvement_case_path_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--path",
        default=None,
        help="Path to improvement case registry. Defaults to config/improvement_cases.yaml.",
    )


def run_improvement_case_validate() -> None:
    parser = argparse.ArgumentParser(description="Validate the improvement case registry.")
    _add_improvement_case_path_arg(parser)
    args = parser.parse_args()

    registry, load_issues = load_improvement_case_registry_for_validation(args.path)
    issues = [*load_issues]
    if not load_issues:
        issues.extend(validate_improvement_case_registry(registry))
    payload = {
        "schema_name": "improvement_case_validation",
        "schema_version": "1.0",
        "valid": not issues,
        "issue_count": len(issues),
        "issues": [_improvement_case_issue_payload(issue) for issue in issues],
    }
    print(json.dumps(payload))
    if issues:
        raise SystemExit(1)


def run_improvement_case_list() -> None:
    parser = argparse.ArgumentParser(description="List improvement cases.")
    _add_improvement_case_path_arg(parser)
    parser.add_argument("--status", choices=sorted(IMPROVEMENT_CASE_STATUSES))
    parser.add_argument("--cause-class", choices=sorted(IMPROVEMENT_CAUSE_CLASSES))
    parser.add_argument("--artifact-type", choices=sorted(IMPROVEMENT_ARTIFACT_TYPES))
    parser.add_argument("--workflow-version")
    args = parser.parse_args()

    registry = load_improvement_case_registry(args.path)
    filtered = filter_improvement_cases(
        registry,
        status=args.status,
        cause_class=args.cause_class,
        artifact_type=args.artifact_type,
        workflow_version=args.workflow_version,
    )
    print(json.dumps(build_improvement_case_manifest(filtered)))


def run_improvement_case_summary() -> None:
    parser = argparse.ArgumentParser(description="Summarize improvement cases.")
    _add_improvement_case_path_arg(parser)
    args = parser.parse_args()

    registry = load_improvement_case_registry(args.path)
    print(json.dumps(summarize_improvement_cases(registry)))


def run_improvement_case_record() -> None:
    parser = argparse.ArgumentParser(description="Record one improvement case.")
    _add_improvement_case_path_arg(parser)
    parser.add_argument("--case-id")
    parser.add_argument("--title", required=True)
    parser.add_argument("--observed-failure", required=True)
    parser.add_argument("--cause-class", choices=sorted(IMPROVEMENT_CAUSE_CLASSES), required=True)
    parser.add_argument(
        "--artifact-type",
        choices=sorted(IMPROVEMENT_ARTIFACT_TYPES),
    )
    parser.add_argument("--artifact-path")
    parser.add_argument("--artifact-description")
    parser.add_argument(
        "--verification-command",
        action="append",
        default=[],
        dest="verification_commands",
    )
    parser.add_argument(
        "--acceptance-condition",
        action="append",
        default=[],
        dest="acceptance_conditions",
    )
    parser.add_argument(
        "--source-type",
        choices=sorted(IMPROVEMENT_SOURCE_TYPES),
        default="operator_note",
    )
    parser.add_argument("--source-ref")
    parser.add_argument("--status", choices=sorted(IMPROVEMENT_CASE_STATUSES), default="converted")
    parser.add_argument("--workflow-version", default="improvement_v1")
    parser.add_argument("--deployed-ref")
    parser.add_argument("--metric-name")
    parser.add_argument("--metric-value", type=float)
    parser.add_argument("--measurement-window")
    args = parser.parse_args()

    try:
        case = record_improvement_case(
            path=args.path,
            case_id=args.case_id,
            title=args.title,
            observed_failure=args.observed_failure,
            cause_class=args.cause_class,
            artifact_type=args.artifact_type,
            artifact_target_path=args.artifact_path,
            artifact_description=args.artifact_description,
            verification_commands=args.verification_commands,
            acceptance_conditions=args.acceptance_conditions,
            source_type=args.source_type,
            source_ref=args.source_ref,
            status=args.status,
            workflow_version=args.workflow_version,
            deployed_ref=args.deployed_ref,
            metric_name=args.metric_name,
            metric_value=args.metric_value,
            measurement_window=args.measurement_window,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(case.model_dump(mode="json")))
