from __future__ import annotations

import argparse
import json

from app.services.ontology_contract_evaluations import (
    evaluate_ontology_contract,
    write_ontology_evaluation_report,
)
from app.services.ontology_contracts import (
    inspect_ontology_contract,
    load_ontology_contract_payload,
    write_ontology_contract_report,
)


def run_validate(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the canonical ontology contract.")
    parser.add_argument(
        "--contract-path",
        default=None,
        help="Optional path to the canonical ontology contract JSON file.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when required ontology layers, slices, or legacy views are missing or drifted.",
    )
    args = parser.parse_args(argv)

    try:
        payload = load_ontology_contract_payload(args.contract_path)
        report = inspect_ontology_contract(payload, strict=args.strict)
    except ValueError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, sort_keys=True))
        return 1

    print(json.dumps(report, sort_keys=True))
    return 0 if report["valid"] else 1


def run_report(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an ontology contract report.")
    parser.add_argument(
        "--contract-path",
        default=None,
        help="Optional path to the canonical ontology contract JSON file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional markdown output path for the ontology contract report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Include strict validation results in the report and fail on strict errors.",
    )
    args = parser.parse_args(argv)

    try:
        payload = load_ontology_contract_payload(args.contract_path)
        report = inspect_ontology_contract(payload, strict=args.strict)
    except ValueError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, sort_keys=True))
        return 1

    if args.output:
        write_ontology_contract_report(args.output, report=report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["valid"] else 1


def run_eval(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run ontology-specific evaluation against the canonical ontology contract."
    )
    parser.add_argument(
        "--contract-path",
        default=None,
        help="Optional path to the canonical ontology contract JSON file.",
    )
    parser.add_argument(
        "--semantic-evaluation-corpus-path",
        default=None,
        help="Optional path to the semantic evaluation corpus YAML file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path for the ontology evaluation report.",
    )
    args = parser.parse_args(argv)

    try:
        payload = load_ontology_contract_payload(args.contract_path)
        report = evaluate_ontology_contract(
            payload,
            contract_path=args.contract_path,
            semantic_evaluation_corpus_path=args.semantic_evaluation_corpus_path,
        )
    except ValueError as exc:
        print(json.dumps({"overall_passed": False, "errors": [str(exc)]}, sort_keys=True))
        return 1

    if args.output:
        write_ontology_evaluation_report(args.output, report=report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run_validate())
