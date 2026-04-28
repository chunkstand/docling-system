from __future__ import annotations

from copy import deepcopy

from app.services.claim_support_evaluations import (
    default_claim_support_evaluation_fixtures,
    evaluate_claim_support_judge_fixture_set,
)


def test_default_claim_support_judge_evaluation_passes_hard_cases() -> None:
    evaluation = evaluate_claim_support_judge_fixture_set()

    assert evaluation["summary"]["gate_outcome"] == "passed"
    assert evaluation["summary"]["overall_accuracy"] == 1.0
    assert evaluation["summary"]["hard_case_kind_count"] >= 4
    assert {row["expected_verdict"] for row in evaluation["case_results"]} == {
        "supported",
        "unsupported",
        "insufficient_evidence",
    }
    assert all(row["passed"] for row in evaluation["case_results"])
    assert all(
        metrics["precision"] == 1.0 and metrics["recall"] == 1.0
        for metrics in evaluation["verdict_metrics"].values()
    )
    assert any(
        metric["metric_key"] == "claim_support_judge_accuracy_gate" and metric["passed"] is True
        for metric in evaluation["success_metrics"]
    )


def test_claim_support_judge_evaluation_fails_when_hard_case_coverage_is_insufficient() -> None:
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])

    evaluation = evaluate_claim_support_judge_fixture_set(
        fixture_set_name="single_fixture_hard_case_gap",
        fixtures=[fixture],
    )

    metrics_by_key = {metric["metric_key"]: metric for metric in evaluation["success_metrics"]}
    assert evaluation["summary"]["gate_outcome"] == "failed"
    assert evaluation["summary"]["overall_accuracy"] == 1.0
    assert evaluation["summary"]["failed_case_count"] == 0
    assert evaluation["summary"]["hard_case_kind_count"] == 1
    assert metrics_by_key["claim_support_judge_accuracy_gate"]["passed"] is True
    assert metrics_by_key["claim_support_hard_case_coverage"]["passed"] is False
    assert "Support-judge quality is measured by reusable hard-case fixtures." in evaluation[
        "reasons"
    ]


def test_claim_support_judge_evaluation_fails_regression_fixture() -> None:
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    fixture["case_id"] = "forced_regression_case"
    fixture["expected_verdict"] = "unsupported"

    evaluation = evaluate_claim_support_judge_fixture_set(
        fixture_set_name="unit_regression_fixture",
        fixtures=[fixture],
    )

    assert evaluation["summary"]["gate_outcome"] == "failed"
    assert evaluation["summary"]["overall_accuracy"] == 0.0
    assert evaluation["case_results"][0]["predicted_verdict"] == "supported"
    assert evaluation["case_results"][0]["failure_reasons"] == [
        "expected_unsupported_got_supported"
    ]
    assert any("Overall accuracy" in reason for reason in evaluation["reasons"])
