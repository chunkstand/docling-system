from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_search_workflows import (
    DraftHarnessConfigUpdateTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    OptimizeSearchHarnessFromCaseTaskOutput,
    RepairCasePayload,
    TriageReplayRegressionTaskOutput,
    VerifyDraftHarnessConfigTaskInput,
    VerifySearchHarnessEvaluationTaskInput,
    VerifySearchHarnessEvaluationTaskOutput,
)
from app.schemas.search import SearchHarnessEvaluationRequest, SearchHarnessEvaluationResponse
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)
from app.services.agent_task_verification_records import create_agent_task_verification_record
from app.services.search_harness_evaluations import (
    evaluate_search_harness,
    get_search_harness_evaluation_detail,
)
from app.services.search_legibility import get_search_harness_descriptor
from app.services.search_release_gate import (
    SearchHarnessReleaseGateOutcome,
    record_search_harness_release_gate,
)


def verify_search_harness_evaluation_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifySearchHarnessEvaluationTaskInput,
    *,
    evaluate_verification_func: Callable[
        [Session, SearchHarnessEvaluationResponse, VerifySearchHarnessEvaluationTaskInput],
        SearchHarnessReleaseGateOutcome,
    ],
    get_evaluation_detail_func=get_search_harness_evaluation_detail,
    record_release_gate_func=record_search_harness_release_gate,
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
    if evaluation.evaluation_id is not None:
        evaluation = get_evaluation_detail_func(session, evaluation.evaluation_id)
        release = record_release_gate_func(
            session,
            evaluation,
            payload,
            requested_by=f"agent_task:{verification_task.id}",
            review_note="verify_search_harness_evaluation",
        )
        outcome = SearchHarnessReleaseGateOutcome(
            outcome=release.outcome,
            metrics=release.metrics,
            reasons=release.reasons,
            details=release.details,
        )
    else:
        release = None
        outcome = evaluate_verification_func(session, evaluation, payload)
    details = {
        **outcome.details,
        "target_task_id": str(target_context.task_id),
        "target_task_type": target_context.task_type,
    }
    if release is not None:
        details["search_harness_release_id"] = str(release.release_id)
        details["release_package_sha256"] = release.release_package_sha256
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
        release=release,
    )
    return verified_output.model_dump(mode="json")


def verify_draft_harness_config_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifyDraftHarnessConfigTaskInput,
    *,
    evaluate_search_harness_func=evaluate_search_harness,
    evaluate_verification_func: Callable[
        [Session, SearchHarnessEvaluationResponse, VerifySearchHarnessEvaluationTaskInput],
        SearchHarnessReleaseGateOutcome,
    ],
    get_search_harness_descriptor_func=get_search_harness_descriptor,
) -> dict:
    draft_context = resolve_required_task_output_context(
        session,
        task_id=payload.target_task_id,
        expected_task_type=(
            "draft_harness_config_update",
            "draft_harness_config_update_from_optimization",
        ),
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        rerun_message=(
            "Target draft task must be rerun after the context migration before it can be verified."
        ),
    )
    output = DraftHarnessConfigUpdateTaskOutput.model_validate(draft_context.output)
    override_spec = output.draft.override_spec.model_dump(mode="json", exclude_none=True)
    draft_harness_name = output.draft.draft_harness_name
    base_harness_name = output.draft.base_harness_name

    evaluation = SearchHarnessEvaluationResponse.model_validate(
        evaluate_search_harness_func(
            session,
            SearchHarnessEvaluationRequest(
                candidate_harness_name=draft_harness_name,
                baseline_harness_name=payload.baseline_harness_name or base_harness_name,
                source_types=payload.source_types,
                limit=payload.limit,
            ),
            harness_overrides={draft_harness_name: override_spec},
        )
    )
    outcome = evaluate_verification_func(
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
    comprehension_gate = _build_harness_comprehension_gate(
        session,
        draft_output=output,
        override_spec=override_spec,
        evaluation=evaluation,
        verification_payload=payload,
        get_search_harness_descriptor_func=get_search_harness_descriptor_func,
    )
    gate_reasons = [
        f"Comprehension gate failed: {reason}" for reason in comprehension_gate.get("reasons", [])
    ]
    final_reasons = [*outcome.reasons, *gate_reasons]
    final_outcome = (
        "passed"
        if outcome.outcome == "passed" and comprehension_gate["comprehension_passed"]
        else "failed"
    )
    final_metrics = {
        **outcome.metrics,
        "comprehension_passed": comprehension_gate["comprehension_passed"],
        "changed_scope_count": len(
            comprehension_gate["predicted_blast_radius"].get("changed_scopes") or []
        ),
    }
    details = {
        **outcome.details,
        "target_task_id": str(draft_context.task_id),
        "target_task_type": draft_context.task_type,
        "draft_harness_name": draft_harness_name,
        "base_harness_name": base_harness_name,
        "comprehension_gate": comprehension_gate,
    }
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=verification_task.id,
        verifier_type="draft_harness_config_gate",
        outcome=final_outcome,
        metrics=final_metrics,
        reasons=final_reasons,
        details=details,
    )
    return {
        "draft": output.draft.model_dump(mode="json"),
        "evaluation": jsonable_encoder(evaluation),
        "comprehension_gate": comprehension_gate,
        "follow_up_plan": comprehension_gate["follow_up_plan"],
        "verification": record.model_dump(mode="json"),
    }


def _changed_override_scopes(override_spec: dict) -> list[str]:
    changed: list[str] = []
    for scope in ("retrieval_profile_overrides", "reranker_overrides"):
        if override_spec.get(scope):
            changed.append(scope)
    return changed


def _repair_case_from_optimization_output(
    output: OptimizeSearchHarnessFromCaseTaskOutput,
) -> RepairCasePayload:
    case = output.case
    optimization = output.optimization
    return RepairCasePayload(
        candidate_harness_name=optimization.candidate_harness_name,
        baseline_harness_name=optimization.baseline_harness_name,
        failure_classification=case.failure_classification,
        problem_statement=case.problem_statement,
        observed_metric_delta=optimization.best_score,
        affected_result_types=(
            ["table"] if case.failure_classification == "table_recall_gap" else ["chunk", "table"]
        ),
        likely_root_cause=case.diagnosis,
        allowed_repair_surface=case.allowed_repair_surfaces,
        blocked_repair_surfaces=case.blocked_repair_surfaces,
        recommended_next_action="draft_harness_config_update_from_optimization",
        diagnostic_examples=[],
        evidence_refs=[ref.model_dump(mode="json") for ref in case.evidence_refs],
    )


def _load_source_repair_case(session: Session, source_task_id: UUID | None):
    if source_task_id is None:
        return None, ["Draft must reference a source task with a repair case."]
    try:
        source_context = resolve_required_task_output_context(
            session,
            task_id=source_task_id,
            expected_task_type=(
                "triage_replay_regression",
                "optimize_search_harness_from_case",
            ),
            expected_schema_name=(
                "triage_replay_regression_output",
                "optimize_search_harness_from_case_output",
            ),
            expected_schema_version="1.0",
            rerun_message=(
                "Source task must be rerun after the context migration before draft verification."
            ),
        )
    except Exception as exc:
        return None, [f"Unable to load source repair case: {exc}"]
    if source_context.task_type == "triage_replay_regression":
        try:
            source_output = TriageReplayRegressionTaskOutput.model_validate(source_context.output)
        except Exception as exc:
            return None, [f"Unable to load source repair case: {exc}"]
        if source_output.repair_case is None:
            return None, ["Source triage output does not include a repair case."]
        return source_output.repair_case, []
    try:
        optimization_output = OptimizeSearchHarnessFromCaseTaskOutput.model_validate(
            source_context.output
        )
    except Exception as exc:
        return None, [f"Unable to load source repair case: {exc}"]
    return _repair_case_from_optimization_output(optimization_output), []


def _build_harness_comprehension_gate(
    session: Session,
    *,
    draft_output: DraftHarnessConfigUpdateTaskOutput,
    override_spec: dict,
    evaluation: SearchHarnessEvaluationResponse,
    verification_payload: VerifyDraftHarnessConfigTaskInput,
    get_search_harness_descriptor_func=get_search_harness_descriptor,
) -> dict:
    reasons: list[str] = []
    repair_case, repair_case_reasons = _load_source_repair_case(
        session,
        draft_output.draft.source_task_id,
    )
    reasons.extend(repair_case_reasons)

    changed_scopes = _changed_override_scopes(override_spec)
    if not changed_scopes:
        reasons.append("Draft does not change any retrieval or reranker knob.")

    if not (draft_output.draft.rationale or "").strip():
        reasons.append("Draft rationale is required for comprehension verification.")

    if repair_case is not None:
        allowed_scopes = set(repair_case.allowed_repair_surface)
        disallowed_scopes = [scope for scope in changed_scopes if scope not in allowed_scopes]
        if disallowed_scopes:
            reasons.append(
                "Draft changes scopes outside the repair case: "
                + ", ".join(sorted(disallowed_scopes))
            )
        if not repair_case.evidence_refs:
            reasons.append("Repair case has no evidence refs.")

    descriptor = None
    try:
        descriptor = get_search_harness_descriptor_func(
            draft_output.draft.draft_harness_name,
            harness_overrides={draft_output.draft.draft_harness_name: override_spec},
        )
    except Exception as exc:
        reasons.append(f"Unable to build draft harness descriptor: {exc}")

    follow_up_plan = {
        "baseline_harness_name": evaluation.baseline_harness_name,
        "candidate_harness_name": evaluation.candidate_harness_name,
        "source_types": list(verification_payload.source_types),
        "limit": verification_payload.limit,
        "success_condition": "No replay regressions and no release-gate threshold violations.",
    }
    predicted_blast_radius = {
        "changed_scopes": changed_scopes,
        "retrieval_override_keys": sorted(
            (override_spec.get("retrieval_profile_overrides") or {}).keys()
        ),
        "reranker_override_keys": sorted((override_spec.get("reranker_overrides") or {}).keys()),
        "source_types": list(verification_payload.source_types),
        "limit": verification_payload.limit,
    }
    comprehension_passed = not reasons
    repair_case_payload = repair_case.model_dump(mode="json") if repair_case is not None else None
    descriptor_payload = descriptor.model_dump(mode="json") if descriptor is not None else None
    return {
        "comprehension_passed": comprehension_passed,
        "claim_evidence_alignment": (
            "Draft cites a source repair case and stays within its allowed repair surface."
            if comprehension_passed
            else "Draft does not fully align claims, evidence, and allowed repair scope."
        ),
        "change_justification": (
            draft_output.draft.rationale
            or "No operator rationale supplied for the proposed harness change."
        ),
        "predicted_blast_radius": predicted_blast_radius,
        "rollback_condition": (
            "Rollback if follow-up evaluation introduces replay regressions, increases zero-result "
            "count beyond the configured threshold, or violates the release gate."
        ),
        "follow_up_plan": follow_up_plan,
        "reasons": reasons,
        "harness_descriptor": descriptor_payload,
        "repair_case": repair_case_payload,
    }
