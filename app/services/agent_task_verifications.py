from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskVerification,
)
from app.schemas.agent_tasks import (
    AgentTaskVerificationResponse,
    DraftHarnessConfigUpdateTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    VerifyDraftHarnessConfigTaskInput,
    VerifySearchHarnessEvaluationTaskOutput,
    VerifySearchHarnessEvaluationTaskInput,
)
from app.schemas.search import SearchHarnessEvaluationRequest, SearchHarnessEvaluationResponse
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_release_gate import (
    SearchHarnessReleaseGateOutcome,
    evaluate_search_harness_release_gate,
)

VerificationOutcome = SearchHarnessReleaseGateOutcome


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _to_verification_response(row: AgentTaskVerification) -> AgentTaskVerificationResponse:
    return AgentTaskVerificationResponse(
        verification_id=row.id,
        target_task_id=row.target_task_id,
        verification_task_id=row.verification_task_id,
        verifier_type=row.verifier_type,
        outcome=row.outcome,
        metrics=row.metrics_json or {},
        reasons=[str(reason) for reason in (row.reasons_json or [])],
        details=row.details_json or {},
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def count_agent_task_verifications(session: Session, task_id: UUID) -> int:
    return session.execute(
        select(func.count())
        .select_from(AgentTaskVerification)
        .where(AgentTaskVerification.target_task_id == task_id)
    ).scalar_one()


def list_agent_task_verifications(
    session: Session,
    task_id: UUID,
    *,
    limit: int = 20,
) -> list[AgentTaskVerificationResponse]:
    rows = (
        session.execute(
            select(AgentTaskVerification)
            .where(AgentTaskVerification.target_task_id == task_id)
            .order_by(AgentTaskVerification.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_verification_response(row) for row in rows]


def get_agent_task_verifications(
    session: Session,
    task_id: UUID,
    *,
    limit: int = 20,
) -> list[AgentTaskVerificationResponse]:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    return list_agent_task_verifications(session, task_id, limit=limit)


def _create_verification_record(
    session: Session,
    *,
    target_task_id: UUID,
    verification_task_id: UUID | None,
    verifier_type: str,
    outcome: str,
    metrics: dict,
    reasons: list[str],
    details: dict,
) -> AgentTaskVerificationResponse:
    now = _utcnow()
    row = AgentTaskVerification(
        target_task_id=target_task_id,
        verification_task_id=verification_task_id,
        verifier_type=verifier_type,
        outcome=outcome,
        metrics_json=metrics,
        reasons_json=reasons,
        details_json=details,
        created_at=now,
        completed_at=now,
    )
    session.add(row)
    session.flush()
    return _to_verification_response(row)


def create_agent_task_verification_record(
    session: Session,
    *,
    target_task_id: UUID,
    verification_task_id: UUID | None,
    verifier_type: str,
    outcome: str,
    metrics: dict,
    reasons: list[str],
    details: dict,
) -> AgentTaskVerificationResponse:
    return _create_verification_record(
        session,
        target_task_id=target_task_id,
        verification_task_id=verification_task_id,
        verifier_type=verifier_type,
        outcome=outcome,
        metrics=metrics,
        reasons=reasons,
        details=details,
    )


def evaluate_search_harness_verification(
    session: Session,
    evaluation: SearchHarnessEvaluationResponse,
    payload: VerifySearchHarnessEvaluationTaskInput,
) -> SearchHarnessReleaseGateOutcome:
    return evaluate_search_harness_release_gate(session, evaluation, payload)


def verify_search_harness_evaluation_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifySearchHarnessEvaluationTaskInput,
) -> dict:
    target_context = resolve_required_dependency_task_output_context(
        session,
        task_id=verification_task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="evaluate_search_harness",
        expected_schema_name="evaluate_search_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Verification task must declare the requested evaluation task as a "
            "target_task dependency."
        ),
        rerun_message=(
            "Target evaluation task must be rerun after the context migration before it can "
            "be verified."
        ),
    )
    output = EvaluateSearchHarnessTaskOutput.model_validate(target_context.output)
    evaluation = output.evaluation
    outcome = evaluate_search_harness_verification(session, evaluation, payload)
    details = {
        **outcome.details,
        "target_task_id": str(target_context.task_id),
        "target_task_type": target_context.task_type,
    }
    record = create_agent_task_verification_record(
        session,
        target_task_id=target_context.task_id,
        verification_task_id=verification_task.id,
        verifier_type="search_harness_evaluation_gate",
        outcome=outcome.outcome,
        metrics=outcome.metrics,
        reasons=outcome.reasons,
        details=details,
    )
    verified_output = VerifySearchHarnessEvaluationTaskOutput(
        evaluation=evaluation,
        verification=record,
    )
    return verified_output.model_dump(mode="json")


def verify_draft_harness_config_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifyDraftHarnessConfigTaskInput,
) -> dict:
    draft_context = resolve_required_task_output_context(
        session,
        task_id=payload.target_task_id,
        expected_task_type="draft_harness_config_update",
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        rerun_message=(
            "Target draft task must be rerun after the context migration before it can be "
            "verified."
        ),
    )
    output = DraftHarnessConfigUpdateTaskOutput.model_validate(draft_context.output)
    override_spec = output.draft.override_spec.model_dump(mode="json", exclude_none=True)
    draft_harness_name = output.draft.draft_harness_name
    base_harness_name = output.draft.base_harness_name

    evaluation = evaluate_search_harness(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=draft_harness_name,
            baseline_harness_name=payload.baseline_harness_name or base_harness_name,
            source_types=payload.source_types,
            limit=payload.limit,
        ),
        harness_overrides={draft_harness_name: override_spec},
    )
    outcome = evaluate_search_harness_verification(
        session,
        evaluation,
        VerifySearchHarnessEvaluationTaskInput(
            target_task_id=payload.target_task_id,
            max_total_regressed_count=payload.max_total_regressed_count,
            max_mrr_drop=payload.max_mrr_drop,
            max_zero_result_count_increase=payload.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=payload.max_foreign_top_result_count_increase,
            min_total_shared_query_count=payload.min_total_shared_query_count,
        ),
    )
    details = {
        **outcome.details,
        "target_task_id": str(draft_context.task_id),
        "target_task_type": draft_context.task_type,
        "draft_harness_name": draft_harness_name,
        "base_harness_name": base_harness_name,
    }
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=verification_task.id,
        verifier_type="draft_harness_config_gate",
        outcome=outcome.outcome,
        metrics=outcome.metrics,
        reasons=outcome.reasons,
        details=details,
    )
    return {
        "draft": output.draft.model_dump(mode="json"),
        "evaluation": jsonable_encoder(evaluation),
        "verification": record.model_dump(mode="json"),
    }
