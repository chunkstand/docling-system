from __future__ import annotations

import os

import pytest

from app.services.claim_support_evaluations import (
    build_claim_support_calibration_policy_payload,
    draft_claim_support_calibration_policy,
    ensure_claim_support_calibration_policy,
    resolve_claim_support_calibration_policy,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_support_active_policy_resolution_rejects_retired_identity(
    postgres_integration_harness,
):
    policy_payload = build_claim_support_calibration_policy_payload()

    with postgres_integration_harness.session_factory() as session:
        policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=policy_payload,
        )
        policy.status = "retired"
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        with pytest.raises(ValueError, match="status retired"):
            ensure_claim_support_calibration_policy(
                session,
                policy_payload=policy_payload,
            )
        with pytest.raises(ValueError, match="status retired"):
            resolve_claim_support_calibration_policy(session)


def test_claim_support_policy_draft_rejects_retired_identity(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        draft_policy = draft_claim_support_calibration_policy(
            session,
            policy_name="claim_support_judge_calibration_policy",
            policy_version="v_retired_redraft",
            thresholds={
                "min_overall_accuracy": 1.0,
                "min_verdict_precision": 1.0,
                "min_verdict_recall": 1.0,
                "min_support_score": 0.34,
            },
            min_hard_case_kind_count=1,
            required_hard_case_kinds=["exact_source_support"],
            required_verdicts=["supported"],
            owner="integration-test",
            source="integration_test",
            rationale="prove retired policy identities cannot be redrafted",
        )
        draft_policy.status = "retired"
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        with pytest.raises(ValueError, match="cannot be redrafted"):
            draft_claim_support_calibration_policy(
                session,
                policy_name="claim_support_judge_calibration_policy",
                policy_version="v_retired_redraft",
                thresholds={
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                    "min_support_score": 0.34,
                },
                min_hard_case_kind_count=1,
                required_hard_case_kinds=["exact_source_support"],
                required_verdicts=["supported"],
                owner="integration-test",
                source="integration_test",
                rationale="prove retired policy identities cannot be redrafted",
            )
