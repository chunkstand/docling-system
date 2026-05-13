from __future__ import annotations

import json

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    ApplyHarnessConfigUpdateTaskInput,
    ApplyHarnessConfigUpdateTaskOutput,
    DraftHarnessConfigFromOptimizationTaskInput,
    DraftHarnessConfigUpdateTaskInput,
    DraftHarnessConfigUpdateTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    OptimizeSearchHarnessFromCaseTaskInput,
    OptimizeSearchHarnessFromCaseTaskOutput,
    ReplaySearchRequestTaskInput,
    ReplaySearchRequestTaskOutput,
    RunSearchReplaySuiteTaskOutput,
    TriageReplayRegressionTaskInput,
    TriageReplayRegressionTaskOutput,
    VerifyDraftHarnessConfigTaskInput,
    VerifyDraftHarnessConfigTaskOutput,
    VerifySearchHarnessEvaluationTaskInput,
    VerifySearchHarnessEvaluationTaskOutput,
)
from app.schemas.search import (
    SearchHarnessEvaluationRequest,
    SearchHarnessOptimizationRequest,
    SearchReplayRunRequest,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context_resolvers import (
    resolve_required_dependency_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
    verify_draft_harness_config_task,
    verify_search_harness_evaluation_task,
)
from app.services.eval_workbench import get_eval_failure_case
from app.services.quality import list_quality_eval_candidates
from app.services.search import get_search_harness, list_search_harnesses
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_harness_optimization import run_search_harness_optimization_loop
from app.services.search_harness_overrides import upsert_applied_search_harness_override
from app.services.search_history import replay_search_request
from app.services.search_legibility import get_search_request_explanation
from app.services.search_release_gate import evaluate_search_harness_release_gate
from app.services.search_replays import (
    compare_search_replay_runs,
    get_search_replay_run_detail,
    run_search_replay_suite,
)
from app.services.storage import StorageService

SEARCH_HARNESS_AGENT_ACTION_TASK_TYPES = (
    "optimize_search_harness_from_case",
    "draft_harness_config_update_from_optimization",
    "replay_search_request",
    "run_search_replay_suite",
    "evaluate_search_harness",
    "verify_search_harness_evaluation",
    "draft_harness_config_update",
    "verify_draft_harness_config",
    "triage_replay_regression",
    "apply_harness_config_update",
)


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


def recommend_triage_next_action(
    *,
    total_shared_query_count: int,
    total_regressed_count: int,
    total_improved_count: int,
    reason_count: int,
    quality_candidate_count: int,
) -> tuple[str, str]:
    if total_shared_query_count == 0:
        return "collect_more_evidence", "low"
    if reason_count > 0 or total_regressed_count > 0:
        return "keep_baseline_and_investigate", "high"
    if total_improved_count > 0:
        return "candidate_ready_for_review", "medium"
    if quality_candidate_count > 0:
        return "investigate_unresolved_gaps", "medium"
    return "no_change", "low"


def _replay_query_key(row) -> tuple[str, str, str]:
    return row.query_text, row.mode, json.dumps(row.filters or {}, sort_keys=True)


def _safe_search_request_explanation(session: Session, search_request_id) -> dict | None:
    if search_request_id is None or not hasattr(session, "execute"):
        return None
    try:
        explanation = get_search_request_explanation(session, search_request_id)
    except Exception:
        return None
    return explanation.model_dump(mode="json")


def _repair_case_examples(
    session: Session,
    evaluation,
    *,
    max_examples: int = 5,
) -> tuple[list[dict], list[str], list[str]]:
    if not hasattr(session, "execute"):
        return [], [], []

    examples: list[dict] = []
    affected_result_types: set[str] = set()
    diagnosis_categories: list[str] = []
    for source in evaluation.sources:
        try:
            comparison = compare_search_replay_runs(
                session,
                source.baseline_replay_run_id,
                source.candidate_replay_run_id,
            )
            baseline_detail = get_search_replay_run_detail(session, source.baseline_replay_run_id)
            candidate_detail = get_search_replay_run_detail(session, source.candidate_replay_run_id)
        except Exception:
            continue

        baseline_rows = {_replay_query_key(row): row for row in baseline_detail.query_results}
        candidate_rows = {_replay_query_key(row): row for row in candidate_detail.query_results}
        for changed_query in comparison.changed_queries:
            key = _replay_query_key(changed_query)
            baseline_row = baseline_rows.get(key)
            candidate_row = candidate_rows.get(key)
            if baseline_row is None or candidate_row is None:
                continue

            baseline_explanation = _safe_search_request_explanation(
                session,
                baseline_row.replay_search_request_id,
            )
            candidate_explanation = _safe_search_request_explanation(
                session,
                candidate_row.replay_search_request_id,
            )
            for explanation in (baseline_explanation, candidate_explanation):
                if explanation is None:
                    continue
                diagnosis = explanation.get("diagnosis") or {}
                category = diagnosis.get("category")
                if category and category not in diagnosis_categories:
                    diagnosis_categories.append(category)
                for result in explanation.get("top_result_snapshot") or []:
                    result_type = result.get("result_type")
                    if result_type:
                        affected_result_types.add(result_type)

            examples.append(
                {
                    "source_type": source.source_type,
                    "query_text": changed_query.query_text,
                    "mode": changed_query.mode,
                    "filters": changed_query.filters,
                    "baseline_passed": changed_query.baseline_passed,
                    "candidate_passed": changed_query.candidate_passed,
                    "baseline_result_count": changed_query.baseline_result_count,
                    "candidate_result_count": changed_query.candidate_result_count,
                    "baseline_search_request_id": (
                        str(baseline_row.replay_search_request_id)
                        if baseline_row.replay_search_request_id is not None
                        else None
                    ),
                    "candidate_search_request_id": (
                        str(candidate_row.replay_search_request_id)
                        if candidate_row.replay_search_request_id is not None
                        else None
                    ),
                    "baseline_explanation": baseline_explanation,
                    "candidate_explanation": candidate_explanation,
                }
            )
            if len(examples) >= max_examples:
                return examples, sorted(affected_result_types), diagnosis_categories
    return examples, sorted(affected_result_types), diagnosis_categories


def _repair_case_failure_classification(
    *,
    evaluation,
    verification_outcome,
    quality_candidate_count: int,
) -> str:
    if evaluation.total_regressed_count > 0:
        return "replay_regression"
    if verification_outcome.reasons:
        return "release_gate_failure"
    if quality_candidate_count > 0:
        return "unresolved_quality_gap"
    if evaluation.total_improved_count > 0:
        return "candidate_improvement"
    return "no_actionable_gap"


def build_repair_case_payload(
    session: Session,
    *,
    candidate_harness_name: str,
    baseline_harness_name: str,
    evaluation,
    verification_outcome,
    recommendation: str,
    quality_candidate_count: int,
) -> dict:
    examples, affected_result_types, diagnosis_categories = _repair_case_examples(
        session,
        evaluation,
    )
    classification = _repair_case_failure_classification(
        evaluation=evaluation,
        verification_outcome=verification_outcome,
        quality_candidate_count=quality_candidate_count,
    )
    likely_root_cause = None
    if diagnosis_categories:
        likely_root_cause = "Observed diagnostic categories: " + ", ".join(diagnosis_categories)
    elif classification == "unresolved_quality_gap":
        likely_root_cause = "Quality candidates remain unresolved outside the replay comparison."
    elif classification == "candidate_improvement":
        likely_root_cause = (
            "Candidate harness improves replay outcomes without observed regressions."
        )

    return {
        "schema_name": "search_harness_repair_case",
        "schema_version": "1.0",
        "candidate_harness_name": candidate_harness_name,
        "baseline_harness_name": baseline_harness_name,
        "failure_classification": classification,
        "problem_statement": (
            f"{candidate_harness_name} vs {baseline_harness_name}: "
            f"{evaluation.total_improved_count} improved, "
            f"{evaluation.total_regressed_count} regressed, "
            f"{evaluation.total_unchanged_count} unchanged query outcome(s)."
        ),
        "observed_metric_delta": {
            "total_shared_query_count": evaluation.total_shared_query_count,
            "total_improved_count": evaluation.total_improved_count,
            "total_regressed_count": evaluation.total_regressed_count,
            "total_unchanged_count": evaluation.total_unchanged_count,
            "quality_candidate_count": quality_candidate_count,
        },
        "affected_result_types": affected_result_types,
        "likely_root_cause": likely_root_cause,
        "allowed_repair_surface": [
            "retrieval_profile_overrides",
            "reranker_overrides",
        ],
        "blocked_repair_surfaces": [
            "canonical_document_artifacts",
            "document_ingest_contracts",
            "evaluation_corpus_weakening",
            "yaml_as_source_of_truth",
        ],
        "recommended_next_action": recommendation,
        "diagnostic_examples": examples,
        "evidence_refs": [
            {
                "ref_kind": "harness_evaluation",
                "candidate_harness_name": candidate_harness_name,
                "baseline_harness_name": baseline_harness_name,
                "source_count": len(evaluation.sources),
            },
            *[
                {
                    "ref_kind": "replay_run_pair",
                    "source_type": source.source_type,
                    "baseline_replay_run_id": str(source.baseline_replay_run_id),
                    "candidate_replay_run_id": str(source.candidate_replay_run_id),
                    "shared_query_count": source.shared_query_count,
                    "improved_count": source.improved_count,
                    "regressed_count": source.regressed_count,
                }
                for source in evaluation.sources
            ],
        ],
    }


evaluate_search_harness_verification = evaluate_search_harness_release_gate


def _optimize_search_harness_from_case_executor(
    session: Session,
    task: AgentTask,
    payload: OptimizeSearchHarnessFromCaseTaskInput,
) -> dict:
    case = get_eval_failure_case(session, payload.case_id)
    candidate_harness_name = (
        payload.candidate_harness_name
        or f"case_{str(payload.case_id).replace('-', '_')[:18]}_candidate"
    )
    optimization = run_search_harness_optimization_loop(
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
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="search_harness_optimization",
        payload=jsonable_encoder(optimization),
        storage_service=StorageService(),
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


def _draft_harness_config_from_optimization_executor(
    session: Session,
    task: AgentTask,
    payload: DraftHarnessConfigFromOptimizationTaskInput,
) -> dict:
    source_context = resolve_required_dependency_task_output_context(
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
    source_output = OptimizeSearchHarnessFromCaseTaskOutput.model_validate(source_context.output)
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
    effective_harness = get_search_harness(
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
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft",
        payload=draft_payload,
        storage_service=StorageService(),
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


def _replay_search_request_executor(
    session: Session, _task: AgentTask, payload: ReplaySearchRequestTaskInput
) -> dict:
    response = replay_search_request(session, payload.search_request_id)
    return {
        "search_request_id": str(payload.search_request_id),
        "replay": jsonable_encoder(response),
    }


def _run_search_replay_suite_executor(
    session: Session, _task: AgentTask, payload: SearchReplayRunRequest
) -> dict:
    response = run_search_replay_suite(session, payload)
    return {
        "source_type": payload.source_type,
        "harness_name": payload.harness_name,
        "replay_run": jsonable_encoder(response),
    }


def _evaluate_search_harness_executor(
    session: Session, _task: AgentTask, payload: SearchHarnessEvaluationRequest
) -> dict:
    response = evaluate_search_harness(session, payload)
    return {
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "evaluation": jsonable_encoder(response),
    }


def _verify_search_harness_evaluation_executor(
    session: Session,
    task: AgentTask,
    payload: VerifySearchHarnessEvaluationTaskInput,
) -> dict:
    return verify_search_harness_evaluation_task(session, task, payload)


def _draft_harness_config_update_executor(
    session: Session,
    task: AgentTask,
    payload: DraftHarnessConfigUpdateTaskInput,
) -> dict:
    existing_harness_names = {row.name for row in list_search_harnesses()}
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
    effective_harness = get_search_harness(
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
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft",
        payload=draft_payload,
        storage_service=StorageService(),
        filename="harness_config_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _verify_draft_harness_config_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftHarnessConfigTaskInput,
) -> dict:
    result = verify_draft_harness_config_task(session, task, payload)
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft_verification",
        payload=result,
        storage_service=StorageService(),
        filename="harness_config_draft_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _apply_harness_config_update_executor(
    session: Session,
    task: AgentTask,
    payload: ApplyHarnessConfigUpdateTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
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
    verification_context = resolve_required_dependency_task_output_context(
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

    draft_output = DraftHarnessConfigUpdateTaskOutput.model_validate(draft_context.output)
    verification_output = VerifyDraftHarnessConfigTaskOutput.model_validate(
        verification_context.output
    )

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

    existing_harness_names = {row.name for row in list_search_harnesses()}
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
    config_path = upsert_applied_search_harness_override(draft_harness_name, override_spec)
    effective_harness = get_search_harness(draft_harness_name)
    follow_up_plan = verification_output.follow_up_plan or {}
    follow_up_evaluation_payload: dict = {}
    follow_up_summary_payload: dict = {}
    follow_up_artifact = None
    if follow_up_plan:
        follow_up_evaluation = evaluate_search_harness(
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
        follow_up_summary_payload = build_harness_follow_up_summary(
            verification_evaluation=verification_output.evaluation,
            follow_up_evaluation=follow_up_evaluation_payload,
        )
        follow_up_artifact = create_agent_task_artifact(
            session,
            task_id=task.id,
            artifact_kind="follow_up_evaluation_summary",
            payload={
                **follow_up_summary_payload,
                "follow_up_plan": follow_up_plan,
                "follow_up_evaluation": follow_up_evaluation_payload,
            },
            storage_service=StorageService(),
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
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="applied_harness_config_update",
        payload=apply_payload,
        storage_service=StorageService(),
        filename="applied_harness_config_update.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _triage_replay_regression_executor(
    session: Session,
    task: AgentTask,
    payload: TriageReplayRegressionTaskInput,
) -> dict:
    quality_candidates = list_quality_eval_candidates(
        session,
        limit=payload.quality_candidate_limit,
        include_resolved=payload.include_resolved_candidates,
    )
    evaluation = evaluate_search_harness(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=payload.candidate_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            source_types=payload.source_types,
            limit=payload.replay_limit,
        ),
    )
    verification_outcome = evaluate_search_harness_verification(
        session,
        evaluation,
        VerifySearchHarnessEvaluationTaskInput(
            target_task_id=task.id,
            max_total_regressed_count=payload.max_total_regressed_count,
            max_mrr_drop=payload.max_mrr_drop,
            max_zero_result_count_increase=payload.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=payload.max_foreign_top_result_count_increase,
            min_total_shared_query_count=payload.min_total_shared_query_count,
        ),
    )
    recommendation, confidence = recommend_triage_next_action(
        total_shared_query_count=evaluation.total_shared_query_count,
        total_regressed_count=evaluation.total_regressed_count,
        total_improved_count=evaluation.total_improved_count,
        reason_count=len(verification_outcome.reasons),
        quality_candidate_count=len(quality_candidates),
    )
    top_candidates = quality_candidates[:3]
    repair_case_payload = build_repair_case_payload(
        session,
        candidate_harness_name=payload.candidate_harness_name,
        baseline_harness_name=payload.baseline_harness_name,
        evaluation=evaluation,
        verification_outcome=verification_outcome,
        recommendation=recommendation,
        quality_candidate_count=len(quality_candidates),
    )
    triage_payload = {
        "shadow_mode": True,
        "triage_kind": "replay_regression",
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "source_types": payload.source_types,
        "replay_limit": payload.replay_limit,
        "quality_candidate_count": len(quality_candidates),
        "top_quality_candidates": jsonable_encoder(top_candidates),
        "evaluation": jsonable_encoder(evaluation),
        "verification": {
            "verifier_type": "shadow_mode_triage_gate",
            "outcome": verification_outcome.outcome,
            "metrics": verification_outcome.metrics,
            "reasons": verification_outcome.reasons,
            "details": verification_outcome.details,
        },
        "recommendation": {
            "next_action": recommendation,
            "confidence": confidence,
            "summary": (
                f"{payload.candidate_harness_name} vs {payload.baseline_harness_name} "
                f"across {len(payload.source_types)} source type(s)."
            ),
        },
        "repair_case": repair_case_payload,
    }
    verification_record = create_agent_task_verification_record(
        session,
        target_task_id=task.id,
        verification_task_id=task.id,
        verifier_type="shadow_mode_triage_gate",
        outcome=verification_outcome.outcome,
        metrics=verification_outcome.metrics,
        reasons=verification_outcome.reasons,
        details=verification_outcome.details,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="triage_summary",
        payload=triage_payload,
        storage_service=StorageService(),
        filename="triage_summary.json",
    )
    repair_case_artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="repair_case",
        payload=repair_case_payload,
        storage_service=StorageService(),
        filename="repair_case.json",
    )
    return {
        "shadow_mode": True,
        "triage_kind": "replay_regression",
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "quality_candidate_count": len(quality_candidates),
        "top_quality_candidates": jsonable_encoder(top_candidates),
        "evaluation": jsonable_encoder(evaluation),
        "verification": verification_record.model_dump(mode="json"),
        "recommendation": triage_payload["recommendation"],
        "repair_case": repair_case_payload,
        "repair_case_artifact_id": str(repair_case_artifact.id),
        "repair_case_artifact_kind": repair_case_artifact.artifact_kind,
        "repair_case_artifact_path": repair_case_artifact.storage_path,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def build_search_harness_action_definitions(
) -> dict[str, AgentTaskActionDefinition]:
    return {
        "optimize_search_harness_from_case": AgentTaskActionDefinition(
            task_type="optimize_search_harness_from_case",
            capability="evaluation",
            definition_kind="workflow",
            description=(
                "Run a bounded transient search-harness optimization loop from one "
                "eval failure case."
            ),
            payload_model=OptimizeSearchHarnessFromCaseTaskInput,
            executor=_optimize_search_harness_from_case_executor,
            output_model=OptimizeSearchHarnessFromCaseTaskOutput,
            output_schema_name="optimize_search_harness_from_case_output",
            output_schema_version="1.0",
            input_example={
                "case_id": "00000000-0000-0000-0000-000000000000",
                "base_harness_name": "wide_v2",
                "baseline_harness_name": "wide_v2",
                "limit": 25,
                "iterations": 2,
            },
            context_builder_name="generic",
        ),
        "draft_harness_config_update_from_optimization": AgentTaskActionDefinition(
            task_type="draft_harness_config_update_from_optimization",
            capability="retrieval",
            definition_kind="draft",
            description=(
                "Convert a completed harness optimization task into a review harness "
                "draft without changing live search behavior."
            ),
            payload_model=DraftHarnessConfigFromOptimizationTaskInput,
            executor=_draft_harness_config_from_optimization_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftHarnessConfigUpdateTaskOutput,
            output_schema_name="draft_harness_config_update_output",
            output_schema_version="1.0",
            input_example={
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "draft_harness_name": "case_repair_review",
            },
            context_builder_name="draft_harness_config",
        ),
        "replay_search_request": AgentTaskActionDefinition(
            task_type="replay_search_request",
            capability="retrieval",
            definition_kind="action",
            description="Replay one persisted search request against the current search stack.",
            payload_model=ReplaySearchRequestTaskInput,
            executor=_replay_search_request_executor,
            output_model=ReplaySearchRequestTaskOutput,
            output_schema_name="replay_search_request_output",
            output_schema_version="1.0",
            input_example={"search_request_id": "00000000-0000-0000-0000-000000000000"},
            context_builder_name="generic",
        ),
        "run_search_replay_suite": AgentTaskActionDefinition(
            task_type="run_search_replay_suite",
            capability="retrieval",
            definition_kind="action",
            description="Run a replay suite over persisted evaluation, feedback, or gap sources.",
            payload_model=SearchReplayRunRequest,
            executor=_run_search_replay_suite_executor,
            output_model=RunSearchReplaySuiteTaskOutput,
            output_schema_name="run_search_replay_suite_output",
            output_schema_version="1.0",
            input_example={"source_type": "feedback", "limit": 12, "harness_name": "default_v1"},
            context_builder_name="generic",
        ),
        "evaluate_search_harness": AgentTaskActionDefinition(
            task_type="evaluate_search_harness",
            capability="retrieval",
            definition_kind="action",
            description="Compare a candidate harness against a baseline across replay sources.",
            payload_model=SearchHarnessEvaluationRequest,
            executor=_evaluate_search_harness_executor,
            output_model=EvaluateSearchHarnessTaskOutput,
            output_schema_name="evaluate_search_harness_output",
            output_schema_version="1.0",
            input_example={
                "candidate_harness_name": "wide_v2",
                "baseline_harness_name": "default_v1",
                "source_types": ["evaluation_queries", "feedback"],
                "limit": 12,
            },
            context_builder_name="evaluate_search_harness",
        ),
        "verify_search_harness_evaluation": AgentTaskActionDefinition(
            task_type="verify_search_harness_evaluation",
            capability="retrieval",
            definition_kind="verifier",
            description=(
                "Verify persisted harness-evaluation replay evidence against rollout thresholds."
            ),
            payload_model=VerifySearchHarnessEvaluationTaskInput,
            executor=_verify_search_harness_evaluation_executor,
            output_model=VerifySearchHarnessEvaluationTaskOutput,
            output_schema_name="verify_search_harness_evaluation_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "max_total_regressed_count": 0,
                "max_mrr_drop": 0.0,
                "max_zero_result_count_increase": 0,
                "max_foreign_top_result_count_increase": 0,
                "min_total_shared_query_count": 1,
            },
            context_builder_name="verify_search_harness_evaluation",
        ),
        "draft_harness_config_update": AgentTaskActionDefinition(
            task_type="draft_harness_config_update",
            capability="retrieval",
            definition_kind="draft",
            description=(
                "Draft a derived search harness configuration without changing live "
                "search behavior."
            ),
            payload_model=DraftHarnessConfigUpdateTaskInput,
            executor=_draft_harness_config_update_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftHarnessConfigUpdateTaskOutput,
            output_schema_name="draft_harness_config_update_output",
            output_schema_version="1.0",
            input_example={
                "draft_harness_name": "wide_v2_review",
                "base_harness_name": "wide_v2",
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "rationale": "Raise recall and title weighting for review.",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {
                    "source_filename_token_coverage_bonus": 0.055,
                    "document_title_token_coverage_bonus": 0.05,
                },
            },
            context_builder_name="draft_harness_config",
        ),
        "verify_draft_harness_config": AgentTaskActionDefinition(
            task_type="verify_draft_harness_config",
            capability="retrieval",
            definition_kind="verifier",
            description=(
                "Evaluate a draft harness configuration ephemerally and persist "
                "a verifier verdict."
            ),
            payload_model=VerifyDraftHarnessConfigTaskInput,
            executor=_verify_draft_harness_config_executor,
            output_model=VerifyDraftHarnessConfigTaskOutput,
            output_schema_name="verify_draft_harness_config_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "baseline_harness_name": "wide_v2",
                "source_types": ["evaluation_queries", "feedback"],
                "limit": 12,
                "max_total_regressed_count": 0,
                "max_mrr_drop": 0.0,
                "max_zero_result_count_increase": 0,
                "max_foreign_top_result_count_increase": 0,
                "min_total_shared_query_count": 1,
            },
            context_builder_name="verify_draft_harness_config",
        ),
        "triage_replay_regression": AgentTaskActionDefinition(
            task_type="triage_replay_regression",
            capability="retrieval",
            definition_kind="workflow",
            description=(
                "Run a shadow-mode replay regression triage over quality gaps and "
                "harness evidence."
            ),
            payload_model=TriageReplayRegressionTaskInput,
            executor=_triage_replay_regression_executor,
            output_model=TriageReplayRegressionTaskOutput,
            output_schema_name="triage_replay_regression_output",
            output_schema_version="1.0",
            input_example={
                "candidate_harness_name": "wide_v2",
                "baseline_harness_name": "default_v1",
                "source_types": ["evaluation_queries", "feedback"],
                "replay_limit": 12,
                "quality_candidate_limit": 12,
                "include_resolved_candidates": False,
                "max_total_regressed_count": 0,
                "max_mrr_drop": 0.0,
                "max_zero_result_count_increase": 0,
                "max_foreign_top_result_count_increase": 0,
                "min_total_shared_query_count": 1,
            },
            context_builder_name="triage_replay_regression",
        ),
        "apply_harness_config_update": AgentTaskActionDefinition(
            task_type="apply_harness_config_update",
            capability="retrieval",
            definition_kind="promotion",
            description=(
                "Apply a verified draft harness configuration as a new review harness "
                "after approval."
            ),
            payload_model=ApplyHarnessConfigUpdateTaskInput,
            executor=_apply_harness_config_update_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplyHarnessConfigUpdateTaskOutput,
            output_schema_name="apply_harness_config_update_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified review harness for operator use.",
            },
            context_builder_name="apply_harness_config_update",
        ),
    }
