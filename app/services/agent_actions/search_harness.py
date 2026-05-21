from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

import app.services.agent_actions.search_harness_drafting_actions as drafting_owner
import app.services.agent_actions.search_harness_triage_actions as triage_owner
from app.db.public.agent_tasks import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_task_search_workflows import (
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

harness_override_has_changes = drafting_owner.harness_override_has_changes
build_harness_follow_up_summary = drafting_owner.build_harness_follow_up_summary
recommend_triage_next_action = triage_owner.recommend_triage_next_action
_replay_query_key = triage_owner._replay_query_key
_repair_case_failure_classification = triage_owner._repair_case_failure_classification
_safe_search_request_explanation = triage_owner._safe_search_request_explanation
_repair_case_examples = triage_owner._repair_case_examples
build_repair_case_payload = triage_owner.build_repair_case_payload


evaluate_search_harness_verification = evaluate_search_harness_release_gate


def _optimize_search_harness_from_case_executor(
    session: Session,
    task: AgentTask,
    payload: OptimizeSearchHarnessFromCaseTaskInput,
) -> dict:
    return drafting_owner.optimize_search_harness_from_case(
        session,
        task,
        payload,
        get_eval_failure_case_func=get_eval_failure_case,
        run_search_harness_optimization_loop_func=run_search_harness_optimization_loop,
        create_agent_task_artifact_func=create_agent_task_artifact,
        storage_service_factory=StorageService,
    )


def _draft_harness_config_from_optimization_executor(
    session: Session,
    task: AgentTask,
    payload: DraftHarnessConfigFromOptimizationTaskInput,
) -> dict:
    return drafting_owner.draft_harness_config_from_optimization(
        session,
        task,
        payload,
        resolve_required_dependency_task_output_context_func=resolve_required_dependency_task_output_context,
        optimization_output_model=OptimizeSearchHarnessFromCaseTaskOutput,
        get_search_harness_func=get_search_harness,
        create_agent_task_artifact_func=create_agent_task_artifact,
        storage_service_factory=StorageService,
    )


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
    return drafting_owner.draft_harness_config_update(
        session,
        task,
        payload,
        list_search_harnesses_func=list_search_harnesses,
        get_search_harness_func=get_search_harness,
        create_agent_task_artifact_func=create_agent_task_artifact,
        storage_service_factory=StorageService,
    )


def _verify_draft_harness_config_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftHarnessConfigTaskInput,
) -> dict:
    return drafting_owner.verify_draft_harness_config(
        session,
        task,
        payload,
        verify_draft_harness_config_task_func=verify_draft_harness_config_task,
        create_agent_task_artifact_func=create_agent_task_artifact,
        storage_service_factory=StorageService,
    )


def _apply_harness_config_update_executor(
    session: Session,
    task: AgentTask,
    payload: ApplyHarnessConfigUpdateTaskInput,
) -> dict:
    return drafting_owner.apply_harness_config_update(
        session,
        task,
        payload,
        resolve_required_dependency_task_output_context_func=resolve_required_dependency_task_output_context,
        draft_output_model=DraftHarnessConfigUpdateTaskOutput,
        verification_output_model=VerifyDraftHarnessConfigTaskOutput,
        list_search_harnesses_func=list_search_harnesses,
        get_search_harness_func=get_search_harness,
        upsert_applied_search_harness_override_func=upsert_applied_search_harness_override,
        evaluate_search_harness_func=evaluate_search_harness,
        create_agent_task_artifact_func=create_agent_task_artifact,
        storage_service_factory=StorageService,
        build_harness_follow_up_summary_func=build_harness_follow_up_summary,
    )


def _triage_replay_regression_executor(
    session: Session,
    task: AgentTask,
    payload: TriageReplayRegressionTaskInput,
) -> dict:
    return triage_owner.triage_replay_regression(
        session,
        task,
        payload,
        list_quality_eval_candidates_func=list_quality_eval_candidates,
        evaluate_search_harness_func=evaluate_search_harness,
        evaluate_search_harness_verification_func=evaluate_search_harness_verification,
        create_agent_task_verification_record_func=create_agent_task_verification_record,
        create_agent_task_artifact_func=create_agent_task_artifact,
        storage_service_factory=StorageService,
        compare_search_replay_runs_func=compare_search_replay_runs,
        get_search_replay_run_detail_func=get_search_replay_run_detail,
        get_search_request_explanation_func=get_search_request_explanation,
    )


def build_search_harness_action_definitions() -> dict[str, AgentTaskActionDefinition]:
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
