from __future__ import annotations

from importlib import import_module
from uuid import UUID


def default_claim_support_evaluation_fixtures():
    return import_module(
        "app.services.claim_support_evaluation_fixtures"
    ).default_claim_support_evaluation_fixtures()


def ensure_claim_support_fixture_set(
    session,
    *,
    fixture_set_name: str,
    fixture_set_version: str = "v1",
    fixtures=None,
    status: str = "active",
    metadata=None,
):
    return import_module(
        "app.services.claim_support_evaluation_fixtures"
    ).ensure_claim_support_fixture_set(
        session,
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        fixtures=fixtures,
        status=status,
        metadata=metadata,
    )


def mine_claim_support_failure_fixtures(
    session,
    *,
    limit: int = 20,
    exclude_case_ids: set[str] | None = None,
):
    return import_module(
        "app.services.claim_support_evaluation_fixtures"
    ).mine_claim_support_failure_fixtures(
        session,
        limit=limit,
        exclude_case_ids=exclude_case_ids,
    )


def build_claim_support_calibration_policy_payload(**kwargs):
    return import_module(
        "app.services.claim_support_calibration_policies"
    ).build_claim_support_calibration_policy_payload(**kwargs)


def get_active_claim_support_calibration_policy(
    session,
    *,
    policy_name: str = "claim_support_judge_calibration_policy",
):
    return import_module(
        "app.services.claim_support_calibration_policies"
    ).get_active_claim_support_calibration_policy(
        session,
        policy_name=policy_name,
    )


def ensure_claim_support_calibration_policy(
    session,
    *,
    policy_payload=None,
    thresholds=None,
):
    return import_module(
        "app.services.claim_support_calibration_policies"
    ).ensure_claim_support_calibration_policy(
        session,
        policy_payload=policy_payload,
        thresholds=thresholds,
    )


def draft_claim_support_calibration_policy(
    session,
    *,
    policy_name: str,
    policy_version: str,
    thresholds,
    min_hard_case_kind_count: int,
    required_hard_case_kinds: list[str],
    required_verdicts: list[str],
    owner: str,
    source: str,
    rationale: str,
):
    return import_module(
        "app.services.claim_support_calibration_policies"
    ).draft_claim_support_calibration_policy(
        session,
        policy_name=policy_name,
        policy_version=policy_version,
        thresholds=thresholds,
        min_hard_case_kind_count=min_hard_case_kind_count,
        required_hard_case_kinds=required_hard_case_kinds,
        required_verdicts=required_verdicts,
        owner=owner,
        source=source,
        rationale=rationale,
    )


def resolve_claim_support_calibration_policy(
    session,
    *,
    policy_name: str = "claim_support_judge_calibration_policy",
    policy_version: str | None = None,
    thresholds=None,
):
    return import_module(
        "app.services.claim_support_calibration_policies"
    ).resolve_claim_support_calibration_policy(
        session,
        policy_name=policy_name,
        policy_version=policy_version,
        thresholds=thresholds,
    )


def activate_claim_support_calibration_policy(
    session,
    *,
    policy_id: UUID,
    activation_metadata=None,
):
    return import_module(
        "app.services.claim_support_calibration_policies"
    ).activate_claim_support_calibration_policy(
        session,
        policy_id=policy_id,
        activation_metadata=activation_metadata,
    )


def evaluate_claim_support_judge_fixture_set(**kwargs):
    return import_module(
        "app.services.claim_support_judge_evaluation_runs"
    ).evaluate_claim_support_judge_fixture_set(**kwargs)


def persist_claim_support_judge_evaluation(
    session,
    evaluation_payload,
    *,
    agent_task_id: UUID | None = None,
    operator_run_id: UUID | None = None,
):
    return import_module(
        "app.services.claim_support_judge_evaluation_runs"
    ).persist_claim_support_judge_evaluation(
        session,
        evaluation_payload,
        agent_task_id=agent_task_id,
        operator_run_id=operator_run_id,
    )
