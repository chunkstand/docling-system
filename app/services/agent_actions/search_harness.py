from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db.models import AgentTaskSideEffectLevel
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
    SearchReplayRunRequest,
)
from app.services.agent_actions.types import AgentTaskActionDefinition, AgentTaskExecutor
from app.services.search_legibility import get_search_request_explanation
from app.services.search_replays import (
    compare_search_replay_runs,
    get_search_replay_run_detail,
)

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


def build_search_harness_action_definitions(
    *,
    optimize_search_harness_from_case_executor: AgentTaskExecutor,
    draft_harness_config_from_optimization_executor: AgentTaskExecutor,
    replay_search_request_executor: AgentTaskExecutor,
    run_search_replay_suite_executor: AgentTaskExecutor,
    evaluate_search_harness_executor: AgentTaskExecutor,
    verify_search_harness_evaluation_executor: AgentTaskExecutor,
    draft_harness_config_update_executor: AgentTaskExecutor,
    verify_draft_harness_config_executor: AgentTaskExecutor,
    triage_replay_regression_executor: AgentTaskExecutor,
    apply_harness_config_update_executor: AgentTaskExecutor,
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
            executor=optimize_search_harness_from_case_executor,
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
            executor=draft_harness_config_from_optimization_executor,
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
            executor=replay_search_request_executor,
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
            executor=run_search_replay_suite_executor,
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
            executor=evaluate_search_harness_executor,
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
            executor=verify_search_harness_evaluation_executor,
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
            executor=draft_harness_config_update_executor,
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
            executor=verify_draft_harness_config_executor,
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
            executor=triage_replay_regression_executor,
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
            executor=apply_harness_config_update_executor,
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
