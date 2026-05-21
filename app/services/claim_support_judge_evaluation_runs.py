from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.public.claim_support import ClaimSupportEvaluation, ClaimSupportEvaluationCase
from app.services.claim_support_calibration_policies import (
    DEFAULT_MIN_HARD_CASE_KIND_COUNT,
    thresholds_payload,
    validated_policy_payload,
)
from app.services.claim_support_evaluation_fixtures import (
    CLAIM_SUPPORT_JUDGE_NAME,
    CLAIM_SUPPORT_JUDGE_VERSION,
    CLAIM_SUPPORT_VERDICTS,
    DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_NAME,
    DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_VERSION,
    default_claim_support_evaluation_fixtures,
    normalize_string_list,
)
from app.services.claim_support_evaluation_fixtures import (
    fixture_set_payload as build_fixture_set_payload,
)
from app.services.evidence import payload_sha256
from app.services.technical_reports import judge_technical_report_claim_support

CLAIM_SUPPORT_EVALUATION_SCHEMA_NAME = "claim_support_judge_evaluation"
CLAIM_SUPPORT_EVALUATION_SCHEMA_VERSION = "1.0"


def _verdict_metrics(case_results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    metrics: dict[str, dict[str, object]] = {}
    for verdict in CLAIM_SUPPORT_VERDICTS:
        true_positive = sum(
            1
            for row in case_results
            if row["expected_verdict"] == verdict and row["predicted_verdict"] == verdict
        )
        false_positive = sum(
            1
            for row in case_results
            if row["expected_verdict"] != verdict and row["predicted_verdict"] == verdict
        )
        false_negative = sum(
            1
            for row in case_results
            if row["expected_verdict"] == verdict and row["predicted_verdict"] != verdict
        )
        expected_count = true_positive + false_negative
        predicted_count = true_positive + false_positive
        precision = true_positive / predicted_count if predicted_count else 1.0
        recall = true_positive / expected_count if expected_count else 1.0
        metrics[verdict] = {
            "expected_count": expected_count,
            "predicted_count": predicted_count,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
        }
    return metrics


def evaluate_claim_support_judge_fixture_set(
    *,
    evaluation_id: UUID | None = None,
    evaluation_name: str = "claim_support_judge_calibration",
    fixture_set_name: str = DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_NAME,
    fixture_set_version: str = DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_VERSION,
    fixtures: list[dict[str, object]] | None = None,
    calibration_policy: dict[str, object] | None = None,
    fixture_set_id: UUID | None = None,
    policy_id: UUID | None = None,
    min_support_score: float = 0.34,
    min_overall_accuracy: float = 1.0,
    min_verdict_precision: float = 1.0,
    min_verdict_recall: float = 1.0,
) -> dict[str, object]:
    evaluation_id = evaluation_id or uuid.uuid4()
    fixture_rows = list(fixtures or default_claim_support_evaluation_fixtures())
    requested_thresholds = thresholds_payload(
        min_overall_accuracy=min_overall_accuracy,
        min_verdict_precision=min_verdict_precision,
        min_verdict_recall=min_verdict_recall,
        min_support_score=min_support_score,
    )
    policy_payload = validated_policy_payload(
        calibration_policy,
        thresholds=requested_thresholds,
    )
    policy_sha256 = str(policy_payload["policy_sha256"])
    thresholds = dict(policy_payload.get("thresholds") or requested_thresholds)
    min_support_score = float(thresholds["min_support_score"])
    min_overall_accuracy = float(thresholds["min_overall_accuracy"])
    min_verdict_precision = float(thresholds["min_verdict_precision"])
    min_verdict_recall = float(thresholds["min_verdict_recall"])
    fixture_payload = build_fixture_set_payload(
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        fixtures=fixture_rows,
    )
    fixture_set_sha256 = str(fixture_payload["fixture_set_sha256"])
    case_results: list[dict[str, object]] = []
    for index, fixture in enumerate(fixture_rows):
        support_payload = judge_technical_report_claim_support(
            fixture["draft_payload"],
            min_claim_support_score=min_support_score,
        )
        claim_id = fixture.get("claim_id")
        judgment = next(
            (
                row
                for row in support_payload.get("claim_judgments") or []
                if not claim_id or row.get("claim_id") == claim_id
            ),
            {},
        )
        expected_verdict = str(fixture.get("expected_verdict") or "")
        predicted_verdict = str(judgment.get("verdict") or "insufficient_evidence")
        passed = expected_verdict == predicted_verdict
        failure_reasons = [] if passed else [f"expected_{expected_verdict}_got_{predicted_verdict}"]
        claim_payload = next(iter(fixture["draft_payload"].get("claims") or []), {})
        case_results.append(
            {
                "case_index": index,
                "case_id": fixture["case_id"],
                "description": fixture.get("description"),
                "hard_case_kind": fixture.get("hard_case_kind"),
                "expected_verdict": expected_verdict,
                "predicted_verdict": predicted_verdict,
                "support_score": judgment.get("support_score"),
                "passed": passed,
                "failure_reasons": failure_reasons,
                "claim_payload": claim_payload,
                "support_judgment": judgment,
            }
        )

    verdict_metrics = _verdict_metrics(case_results)
    passed_case_count = sum(1 for row in case_results if row["passed"])
    case_count = len(case_results)
    overall_accuracy = passed_case_count / case_count if case_count else 0.0
    hard_case_kinds = sorted(
        {str(row.get("hard_case_kind")) for row in case_results if row.get("hard_case_kind")}
    )
    expected_verdicts = sorted({str(row["expected_verdict"]) for row in case_results})
    required_hard_case_kinds = normalize_string_list(
        policy_payload.get("required_hard_case_kinds") or []
    )
    required_verdicts = normalize_string_list(policy_payload.get("required_verdicts") or [])
    min_hard_case_kind_count = int(
        policy_payload.get("min_hard_case_kind_count") or DEFAULT_MIN_HARD_CASE_KIND_COUNT
    )
    missing_hard_case_kinds = sorted(set(required_hard_case_kinds) - set(hard_case_kinds))
    missing_verdicts = sorted(set(required_verdicts) - set(expected_verdicts))
    reasons: list[str] = []
    if overall_accuracy < min_overall_accuracy:
        reasons.append(
            f"Overall accuracy {overall_accuracy:.4f} is below {min_overall_accuracy:.4f}."
        )
    for verdict, metrics in verdict_metrics.items():
        if metrics["precision"] < min_verdict_precision:
            reasons.append(
                f"{verdict} precision {metrics['precision']:.4f} is below "
                f"{min_verdict_precision:.4f}."
            )
        if metrics["recall"] < min_verdict_recall:
            reasons.append(
                f"{verdict} recall {metrics['recall']:.4f} is below "
                f"{min_verdict_recall:.4f}."
            )

    accuracy_gate_passed = not reasons
    summary = {
        "case_count": case_count,
        "passed_case_count": passed_case_count,
        "failed_case_count": case_count - passed_case_count,
        "overall_accuracy": round(overall_accuracy, 4),
        "gate_outcome": "pending",
        "hard_case_kind_count": len(hard_case_kinds),
        "hard_case_kinds": hard_case_kinds,
        "required_hard_case_kinds": required_hard_case_kinds,
        "missing_hard_case_kinds": missing_hard_case_kinds,
        "expected_verdicts": expected_verdicts,
        "required_verdicts": required_verdicts,
        "missing_verdicts": missing_verdicts,
        "policy_name": str(policy_payload["policy_name"]),
        "policy_version": str(policy_payload["policy_version"]),
        "policy_sha256": policy_sha256,
    }
    hard_case_coverage_passed = (
        summary["hard_case_kind_count"] >= min_hard_case_kind_count
        and not missing_hard_case_kinds
    )
    verdict_coverage_passed = not missing_verdicts
    auditability_passed = bool(fixture_set_sha256 and policy_sha256)
    success_metrics = [
        {
            "metric_key": "claim_support_judge_accuracy_gate",
            "stakeholder": "Omar Khattab",
            "passed": accuracy_gate_passed,
            "summary": "Support-judge verdicts pass fixed replay precision and recall gates.",
            "details": {
                "overall_accuracy": summary["overall_accuracy"],
                "verdict_metrics": verdict_metrics,
            },
        },
        {
            "metric_key": "claim_support_hard_case_coverage",
            "stakeholder": "Rich Sutton / Bitter Lesson",
            "passed": hard_case_coverage_passed,
            "summary": "Support-judge quality satisfies the governed hard-case policy.",
            "details": {
                "hard_case_kinds": hard_case_kinds,
                "hard_case_kind_count": len(hard_case_kinds),
                "min_hard_case_kind_count": min_hard_case_kind_count,
                "required_hard_case_kinds": required_hard_case_kinds,
                "missing_hard_case_kinds": missing_hard_case_kinds,
            },
        },
        {
            "metric_key": "claim_support_verdict_coverage",
            "stakeholder": "Omar Khattab / Jerry Liu",
            "passed": verdict_coverage_passed,
            "summary": "Support-judge fixtures cover every governed verdict class.",
            "details": {
                "expected_verdicts": expected_verdicts,
                "required_verdicts": required_verdicts,
                "missing_verdicts": missing_verdicts,
            },
        },
        {
            "metric_key": "claim_support_eval_auditability",
            "stakeholder": "Luc Moreau / James Cheney",
            "passed": auditability_passed,
            "summary": "The evaluated fixture set and calibration policy are content-addressed.",
            "details": {
                "fixture_set_sha256": fixture_set_sha256,
                "policy_sha256": policy_sha256,
            },
        },
    ]
    if not all(metric["passed"] for metric in success_metrics):
        reasons.extend(metric["summary"] for metric in success_metrics if not metric["passed"])
    summary["gate_outcome"] = "failed" if reasons else "passed"

    return {
        "schema_name": CLAIM_SUPPORT_EVALUATION_SCHEMA_NAME,
        "schema_version": CLAIM_SUPPORT_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": str(evaluation_id),
        "evaluation_name": evaluation_name,
        "fixture_set_id": str(fixture_set_id) if fixture_set_id else None,
        "fixture_set_name": fixture_set_name,
        "fixture_set_version": fixture_set_version,
        "fixture_set_sha256": fixture_set_sha256,
        "policy_id": str(policy_id) if policy_id else None,
        "policy_name": str(policy_payload["policy_name"]),
        "policy_version": str(policy_payload["policy_version"]),
        "policy_sha256": policy_sha256,
        "calibration_policy": policy_payload,
        "judge_name": CLAIM_SUPPORT_JUDGE_NAME,
        "judge_version": CLAIM_SUPPORT_JUDGE_VERSION,
        "thresholds": thresholds,
        "summary": summary,
        "verdict_metrics": verdict_metrics,
        "case_results": case_results,
        "reasons": reasons,
        "success_metrics": success_metrics,
    }


def persist_claim_support_judge_evaluation(
    session: Session,
    evaluation_payload: dict[str, object],
    *,
    agent_task_id: UUID | None = None,
    operator_run_id: UUID | None = None,
) -> ClaimSupportEvaluation:
    now = utcnow()
    evaluation_id = UUID(str(evaluation_payload["evaluation_id"]))
    payload = {
        **evaluation_payload,
        "operator_run_id": str(operator_run_id) if operator_run_id else None,
    }
    fixture_set_id = (
        UUID(str(payload["fixture_set_id"])) if payload.get("fixture_set_id") else None
    )
    policy_id = UUID(str(payload["policy_id"])) if payload.get("policy_id") else None
    row = ClaimSupportEvaluation(
        id=evaluation_id,
        agent_task_id=agent_task_id,
        operator_run_id=operator_run_id,
        fixture_set_id=fixture_set_id,
        policy_id=policy_id,
        evaluation_name=str(payload["evaluation_name"]),
        fixture_set_name=str(payload["fixture_set_name"]),
        fixture_set_version=payload.get("fixture_set_version"),
        fixture_set_sha256=str(payload["fixture_set_sha256"]),
        policy_name=payload.get("policy_name"),
        policy_version=payload.get("policy_version"),
        policy_sha256=payload.get("policy_sha256"),
        judge_name=str(payload["judge_name"]),
        judge_version=str(payload["judge_version"]),
        min_support_score=float(payload["thresholds"]["min_support_score"]),
        status="completed",
        gate_outcome=str(payload["summary"]["gate_outcome"]),
        thresholds_json=dict(payload["thresholds"]),
        metrics_json=dict(payload["summary"]),
        reasons_json=list(payload.get("reasons") or []),
        evaluation_payload_json=payload,
        evaluation_payload_sha256=str(payload_sha256(payload)),
        created_at=now,
        completed_at=now,
    )
    session.add(row)
    for case_result in payload.get("case_results") or []:
        session.add(
            ClaimSupportEvaluationCase(
                id=uuid.uuid4(),
                evaluation_id=evaluation_id,
                case_index=int(case_result["case_index"]),
                case_id=str(case_result["case_id"]),
                hard_case_kind=case_result.get("hard_case_kind"),
                expected_verdict=str(case_result["expected_verdict"]),
                predicted_verdict=str(case_result["predicted_verdict"]),
                support_score=case_result.get("support_score"),
                passed=bool(case_result["passed"]),
                claim_payload_json=dict(case_result.get("claim_payload") or {}),
                support_judgment_json=dict(case_result.get("support_judgment") or {}),
                failure_reasons_json=list(case_result.get("failure_reasons") or []),
                created_at=now,
            )
        )
    session.flush()
    return row
