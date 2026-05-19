from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.models import AgentTask
from app.schemas.agent_task_search_workflows import (
    ApplyHarnessConfigUpdateTaskInput,
    DraftHarnessConfigFromOptimizationTaskInput,
    DraftHarnessConfigUpdateTaskInput,
    OptimizeSearchHarnessFromCaseTaskInput,
    VerifyDraftHarnessConfigTaskInput,
)
from app.schemas.search import SearchHarnessEvaluationRequest, SearchHarnessOptimizationRequest


def harness_override_has_changes(override_spec: dict) -> bool:
    return bool(
        override_spec.get("retrieval_profile_overrides") or override_spec.get("reranker_overrides")
    )


def build_harness_follow_up_summary(
    *,
    verification_evaluation: dict,
    follow_up_evaluation: dict,
) -> dict:
    before_regressed = int(verification_evaluation.get("total_regressed_count") or 0)
    after_regressed = int(follow_up_evaluation.get("total_regressed_count") or 0)
    before_improved = int(verification_evaluation.get("total_improved_count") or 0)
    after_improved = int(follow_up_evaluation.get("total_improved_count") or 0)
    before_shared = int(verification_evaluation.get("total_shared_query_count") or 0)
    after_shared = int(follow_up_evaluation.get("total_shared_query_count") or 0)
    keep_recommendation = after_regressed <= before_regressed
    return {
        "schema_name": "search_harness_follow_up_evidence",
        "schema_version": "1.0",
        "before": {
            "total_shared_query_count": before_shared,
            "total_improved_count": before_improved,
            "total_regressed_count": before_regressed,
        },
        "after": {
            "total_shared_query_count": after_shared,
            "total_improved_count": after_improved,
            "total_regressed_count": after_regressed,
        },
        "delta": {
            "shared_query_count": after_shared - before_shared,
            "improved_count": after_improved - before_improved,
            "regressed_count": after_regressed - before_regressed,
        },
        "recommendation": "keep_override" if keep_recommendation else "rollback_or_revise",
        "summary": (
            "Follow-up replay/evaluation did not increase regressions."
            if keep_recommendation
            else "Follow-up replay/evaluation increased regressions; review the override."
        ),
    }


def optimize_search_harness_from_case(
    session: Session,
    task: AgentTask,
    payload: OptimizeSearchHarnessFromCaseTaskInput,
    *,
    get_eval_failure_case_func,
    run_search_harness_optimization_loop_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    case = get_eval_failure_case_func(session, payload.case_id)
    candidate_harness_name = (
        payload.candidate_harness_name
        or f"case_{str(payload.case_id).replace('-', '_')[:18]}_candidate"
    )
    optimization = run_search_harness_optimization_loop_func(
        session,
        SearchHarnessOptimizationRequest(
            base_harness_name=payload.base_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            candidate_harness_name=candidate_harness_name,
            source_types=payload.source_types,
            limit=payload.limit,
            iterations=payload.iterations,
            tune_fields=payload.tune_fields,
            max_total_regressed_count=payload.max_total_regressed_count,
            max_mrr_drop=payload.max_mrr_drop,
            max_zero_result_count_increase=payload.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=payload.max_foreign_top_result_count_increase,
            min_total_shared_query_count=payload.min_total_shared_query_count,
        ),
    )
    best_gate_passed = optimization.best_gate.get("outcome") == "passed"
    best_override_changed = harness_override_has_changes(optimization.best_override_spec)
    can_draft = best_gate_passed and best_override_changed
    recommendation = {
        "next_action": "draft_harness_config_update_from_optimization"
        if can_draft
        else "inspect_optimizer_attempts",
        "confidence": "medium" if can_draft else "low",
        "summary": (
            "Best override is a changed passing candidate."
            if can_draft
            else (
                "Best gate passed but did not change the harness; inspect optimizer attempts."
                if best_gate_passed
                else (
                    f"Best override has score {optimization.best_score} and gate "
                    f"{optimization.best_gate.get('outcome')}."
                )
            )
        ),
    }
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="search_harness_optimization",
        payload=jsonable_encoder(optimization),
        storage_service=storage_service_factory(),
        filename="search_harness_optimization.json",
    )
    return {
        "case": jsonable_encoder(case),
        "optimization": jsonable_encoder(optimization),
        "recommendation": recommendation,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def draft_harness_config_from_optimization(
    session: Session,
    task: AgentTask,
    payload: DraftHarnessConfigFromOptimizationTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    optimization_output_model,
    get_search_harness_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    source_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.source_task_id,
        dependency_kind="source_task",
        expected_task_type="optimize_search_harness_from_case",
        expected_schema_name="optimize_search_harness_from_case_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Harness drafts from optimization must declare the optimizer task "
            "as a source_task dependency."
        ),
        rerun_message=("Optimizer task must be rerun after the context migration before drafting."),
    )
    source_output = optimization_output_model.model_validate(source_context.output)
    optimization = source_output.optimization
    best_override_spec = dict(optimization.best_override_spec or {})
    if not harness_override_has_changes(best_override_spec):
        raise ValueError(
            "Optimization did not produce a changed harness override; "
            "refusing to draft a no-op config update."
        )
    rationale = payload.rationale or (
        "Agent-proposed bounded harness repair from eval failure case optimization."
    )
    best_override_spec = {
        **best_override_spec,
        "override_type": "draft_harness_config_update",
        "override_source": "task_draft",
        "draft_task_id": str(task.id),
        "source_task_id": str(payload.source_task_id),
        "rationale": rationale,
    }
    effective_harness = get_search_harness_func(
        payload.draft_harness_name,
        {payload.draft_harness_name: best_override_spec},
    )
    draft_payload = {
        "draft_harness_name": payload.draft_harness_name,
        "base_harness_name": optimization.base_harness_name,
        "source_task_id": str(payload.source_task_id),
        "source_task_type": source_context.task_type,
        "rationale": rationale,
        "override_spec": best_override_spec,
        "effective_harness_config": effective_harness.config_snapshot,
    }
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft",
        payload=draft_payload,
        storage_service=storage_service_factory(),
        filename="harness_config_draft.json",
    )
    return {
        "draft": draft_payload,
        "source_case": jsonable_encoder(source_output.case),
        "optimization_summary": {
            "stopped_reason": optimization.stopped_reason,
            "iterations_completed": optimization.iterations_completed,
            "best_score": optimization.best_score,
            "best_gate": optimization.best_gate,
        },
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def draft_harness_config_update(
    session: Session,
    task: AgentTask,
    payload: DraftHarnessConfigUpdateTaskInput,
    *,
    list_search_harnesses_func,
    get_search_harness_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    existing_harness_names = {row.name for row in list_search_harnesses_func()}
    if payload.draft_harness_name in existing_harness_names:
        msg = f"Draft harness name already exists: {payload.draft_harness_name}"
        raise ValueError(msg)

    override_spec = {
        "base_harness_name": payload.base_harness_name,
        "retrieval_profile_overrides": payload.retrieval_profile_overrides,
        "reranker_overrides": payload.reranker_overrides,
        "override_type": "draft_harness_config_update",
        "override_source": "task_draft",
        "draft_task_id": str(task.id),
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "rationale": payload.rationale,
    }
    effective_harness = get_search_harness_func(
        payload.draft_harness_name,
        {payload.draft_harness_name: override_spec},
    )
    source_task = session.get(AgentTask, payload.source_task_id) if payload.source_task_id else None
    draft_payload = {
        "draft_harness_name": payload.draft_harness_name,
        "base_harness_name": payload.base_harness_name,
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "source_task_type": source_task.task_type if source_task is not None else None,
        "rationale": payload.rationale,
        "override_spec": override_spec,
        "effective_harness_config": effective_harness.config_snapshot,
    }
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft",
        payload=draft_payload,
        storage_service=storage_service_factory(),
        filename="harness_config_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def verify_draft_harness_config(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftHarnessConfigTaskInput,
    *,
    verify_draft_harness_config_task_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    result = verify_draft_harness_config_task_func(session, task, payload)
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft_verification",
        payload=result,
        storage_service=storage_service_factory(),
        filename="harness_config_draft_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def apply_harness_config_update(
    session: Session,
    task: AgentTask,
    payload: ApplyHarnessConfigUpdateTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    draft_output_model,
    verification_output_model,
    list_search_harnesses_func,
    get_search_harness_func,
    upsert_applied_search_harness_override_func,
    evaluate_search_harness_func,
    create_agent_task_artifact_func,
    storage_service_factory,
    build_harness_follow_up_summary_func,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type=(
            "draft_harness_config_update",
            "draft_harness_config_update_from_optimization",
        ),
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested draft task as a draft_task dependency."
        ),
        rerun_message=(
            "Draft task must be rerun after the context migration before it can be applied."
        ),
    )
    verification_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_draft_harness_config",
        expected_schema_name="verify_draft_harness_config_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested verification task as a "
            "verification_task dependency."
        ),
        rerun_message=(
            "Verification task must be rerun after the context migration before it can be applied."
        ),
    )

    draft_output = draft_output_model.model_validate(draft_context.output)
    verification_output = verification_output_model.model_validate(verification_context.output)

    verification = verification_output.verification
    if verification.outcome != "passed":
        msg = "Only passed draft harness verifications can be applied."
        raise ValueError(msg)
    if (
        verification_output.comprehension_gate is not None
        and not verification_output.comprehension_gate.comprehension_passed
    ):
        msg = "Only comprehensible draft harness verifications can be applied."
        raise ValueError(msg)
    if verification.target_task_id != payload.draft_task_id:
        msg = "Verification task does not target the requested draft task."
        raise ValueError(msg)

    draft_payload = draft_output.draft
    draft_harness_name = draft_payload.draft_harness_name
    override_spec = draft_payload.override_spec.model_dump(mode="json")
    if verification_output.draft.draft_harness_name != draft_harness_name:
        msg = "Verification task does not match the requested draft harness name."
        raise ValueError(msg)

    existing_harness_names = {row.name for row in list_search_harnesses_func()}
    if draft_harness_name in existing_harness_names:
        msg = f"Search harness name already exists: {draft_harness_name}"
        raise ValueError(msg)

    override_spec.update(
        {
            "override_type": "applied_harness_config_update",
            "override_source": "applied_override",
            "verification_task_id": str(payload.verification_task_id),
            "applied_by": task.approved_by,
            "applied_at": task.approved_at.isoformat() if task.approved_at else None,
        }
    )
    config_path = upsert_applied_search_harness_override_func(draft_harness_name, override_spec)
    effective_harness = get_search_harness_func(draft_harness_name)
    follow_up_plan = verification_output.follow_up_plan or {}
    follow_up_evaluation_payload: dict = {}
    follow_up_summary_payload: dict = {}
    follow_up_artifact = None
    if follow_up_plan:
        follow_up_evaluation = evaluate_search_harness_func(
            session,
            SearchHarnessEvaluationRequest(
                candidate_harness_name=draft_harness_name,
                baseline_harness_name=follow_up_plan.get("baseline_harness_name")
                or draft_payload.base_harness_name,
                source_types=follow_up_plan.get("source_types")
                or [
                    "evaluation_queries",
                    "feedback",
                    "live_search_gaps",
                    "cross_document_prose_regressions",
                ],
                limit=int(follow_up_plan.get("limit") or 25),
            ),
        )
        follow_up_evaluation_payload = jsonable_encoder(follow_up_evaluation)
        follow_up_summary_payload = build_harness_follow_up_summary_func(
            verification_evaluation=verification_output.evaluation,
            follow_up_evaluation=follow_up_evaluation_payload,
        )
        follow_up_artifact = create_agent_task_artifact_func(
            session,
            task_id=task.id,
            artifact_kind="follow_up_evaluation_summary",
            payload={
                **follow_up_summary_payload,
                "follow_up_plan": follow_up_plan,
                "follow_up_evaluation": follow_up_evaluation_payload,
            },
            storage_service=storage_service_factory(),
            filename="follow_up_evaluation_summary.json",
        )
    apply_payload = {
        "draft_task_id": str(payload.draft_task_id),
        "verification_task_id": str(payload.verification_task_id),
        "draft_harness_name": draft_harness_name,
        "reason": payload.reason,
        "config_path": str(config_path),
        "applied_override": override_spec,
        "effective_harness_config": effective_harness.config_snapshot,
        "follow_up_plan": follow_up_plan,
        "follow_up_evaluation": follow_up_evaluation_payload,
        "follow_up_summary": follow_up_summary_payload,
        "follow_up_artifact_id": str(follow_up_artifact.id) if follow_up_artifact else None,
        "follow_up_artifact_kind": (
            follow_up_artifact.artifact_kind if follow_up_artifact else None
        ),
        "follow_up_artifact_path": follow_up_artifact.storage_path if follow_up_artifact else None,
    }
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="applied_harness_config_update",
        payload=apply_payload,
        storage_service=storage_service_factory(),
        filename="applied_harness_config_update.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
