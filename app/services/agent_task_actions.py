from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    ApplyHarnessConfigUpdateTaskOutput,
    ApplyHarnessConfigUpdateTaskInput,
    DraftHarnessConfigUpdateTaskOutput,
    DraftHarnessConfigUpdateTaskInput,
    EnqueueDocumentReprocessTaskInput,
    EvaluateSearchHarnessTaskOutput,
    LatestEvaluationTaskInput,
    QualityEvalCandidatesTaskInput,
    ReplaySearchRequestTaskInput,
    TriageReplayRegressionTaskInput,
    VerifyDraftHarnessConfigTaskOutput,
    VerifyDraftHarnessConfigTaskInput,
    VerifySearchHarnessEvaluationTaskInput,
)
from app.schemas.search import SearchHarnessEvaluationRequest, SearchReplayRunRequest
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import resolve_required_dependency_task_output_context
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
    evaluate_search_harness_verification,
    verify_draft_harness_config_task,
    verify_search_harness_evaluation_task,
)
from app.services.documents import (
    get_latest_document_evaluation_detail,
    reprocess_document,
)
from app.services.quality import list_quality_eval_candidates
from app.services.search import get_search_harness, list_search_harnesses
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_harness_overrides import upsert_applied_search_harness_override
from app.services.search_history import replay_search_request
from app.services.search_replays import run_search_replay_suite
from app.services.storage import StorageService


@dataclass(frozen=True)
class AgentTaskActionDefinition:
    task_type: str
    definition_kind: str
    description: str
    payload_model: type[BaseModel]
    executor: Callable[[Session, AgentTask, BaseModel], dict]
    side_effect_level: str = AgentTaskSideEffectLevel.READ_ONLY.value
    requires_approval: bool = False
    output_model: type[BaseModel] | None = None
    output_schema_name: str | None = None
    output_schema_version: str | None = None
    input_example: dict[str, Any] | None = None


def _latest_evaluation_executor(
    session: Session, _task: AgentTask, payload: LatestEvaluationTaskInput
) -> dict:
    response = get_latest_document_evaluation_detail(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "evaluation": jsonable_encoder(response),
    }


def _quality_eval_candidates_executor(
    session: Session, _task: AgentTask, payload: QualityEvalCandidatesTaskInput
) -> dict:
    response = list_quality_eval_candidates(
        session,
        limit=payload.limit,
        include_resolved=payload.include_resolved,
    )
    return {
        "limit": payload.limit,
        "include_resolved": payload.include_resolved,
        "candidate_count": len(response),
        "candidates": jsonable_encoder(response),
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


def _enqueue_document_reprocess_executor(
    session: Session,
    _task: AgentTask,
    payload: EnqueueDocumentReprocessTaskInput,
) -> dict:
    response = reprocess_document(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "reason": payload.reason,
        "reprocess": jsonable_encoder(response),
    }


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
        expected_task_type="draft_harness_config_update",
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
            "Verification task must be rerun after the context migration before it can be "
            "applied."
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
    apply_payload = {
        "draft_task_id": str(payload.draft_task_id),
        "verification_task_id": str(payload.verification_task_id),
        "draft_harness_name": draft_harness_name,
        "reason": payload.reason,
        "config_path": str(config_path),
        "applied_override": override_spec,
        "effective_harness_config": effective_harness.config_snapshot,
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


def _recommend_triage_next_action(
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
    recommendation, confidence = _recommend_triage_next_action(
        total_shared_query_count=evaluation.total_shared_query_count,
        total_regressed_count=evaluation.total_regressed_count,
        total_improved_count=evaluation.total_improved_count,
        reason_count=len(verification_outcome.reasons),
        quality_candidate_count=len(quality_candidates),
    )
    top_candidates = quality_candidates[:3]
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
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


_ACTION_REGISTRY: dict[str, AgentTaskActionDefinition] = {
    "get_latest_evaluation": AgentTaskActionDefinition(
        task_type="get_latest_evaluation",
        definition_kind="action",
        description="Fetch the latest persisted evaluation detail for one document.",
        payload_model=LatestEvaluationTaskInput,
        executor=_latest_evaluation_executor,
        input_example={"document_id": "00000000-0000-0000-0000-000000000000"},
    ),
    "list_quality_eval_candidates": AgentTaskActionDefinition(
        task_type="list_quality_eval_candidates",
        definition_kind="action",
        description="List mined evaluation candidates from failed evals and live search gaps.",
        payload_model=QualityEvalCandidatesTaskInput,
        executor=_quality_eval_candidates_executor,
        input_example={"limit": 12, "include_resolved": False},
    ),
    "replay_search_request": AgentTaskActionDefinition(
        task_type="replay_search_request",
        definition_kind="action",
        description="Replay one persisted search request against the current search stack.",
        payload_model=ReplaySearchRequestTaskInput,
        executor=_replay_search_request_executor,
        input_example={"search_request_id": "00000000-0000-0000-0000-000000000000"},
    ),
    "run_search_replay_suite": AgentTaskActionDefinition(
        task_type="run_search_replay_suite",
        definition_kind="action",
        description="Run a replay suite over persisted evaluation, feedback, or gap sources.",
        payload_model=SearchReplayRunRequest,
        executor=_run_search_replay_suite_executor,
        input_example={"source_type": "feedback", "limit": 12, "harness_name": "default_v1"},
    ),
    "evaluate_search_harness": AgentTaskActionDefinition(
        task_type="evaluate_search_harness",
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
    ),
    "verify_search_harness_evaluation": AgentTaskActionDefinition(
        task_type="verify_search_harness_evaluation",
        definition_kind="verifier",
        description=(
            "Verify persisted harness-evaluation replay evidence against rollout thresholds."
        ),
        payload_model=VerifySearchHarnessEvaluationTaskInput,
        executor=_verify_search_harness_evaluation_executor,
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "max_total_regressed_count": 0,
            "max_mrr_drop": 0.0,
            "max_zero_result_count_increase": 0,
            "max_foreign_top_result_count_increase": 0,
            "min_total_shared_query_count": 1,
        },
    ),
    "draft_harness_config_update": AgentTaskActionDefinition(
        task_type="draft_harness_config_update",
        definition_kind="draft",
        description=(
            "Draft a derived search harness configuration without changing live search behavior."
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
    ),
    "verify_draft_harness_config": AgentTaskActionDefinition(
        task_type="verify_draft_harness_config",
        definition_kind="verifier",
        description=(
            "Evaluate a draft harness configuration ephemerally and persist a verifier verdict."
        ),
        payload_model=VerifyDraftHarnessConfigTaskInput,
        executor=_verify_draft_harness_config_executor,
        output_model=VerifyDraftHarnessConfigTaskOutput,
        output_schema_name="verify_draft_harness_config_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "baseline_harness_name": "default_v1",
            "source_types": ["evaluation_queries", "feedback"],
            "limit": 12,
            "max_total_regressed_count": 0,
            "max_mrr_drop": 0.0,
            "max_zero_result_count_increase": 0,
            "max_foreign_top_result_count_increase": 0,
            "min_total_shared_query_count": 1,
        },
    ),
    "triage_replay_regression": AgentTaskActionDefinition(
        task_type="triage_replay_regression",
        definition_kind="workflow",
        description=(
            "Run a shadow-mode replay regression triage over quality gaps and harness evidence."
        ),
        payload_model=TriageReplayRegressionTaskInput,
        executor=_triage_replay_regression_executor,
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
    ),
    "enqueue_document_reprocess": AgentTaskActionDefinition(
        task_type="enqueue_document_reprocess",
        definition_kind="promotion",
        description=(
            "Queue a new processing run for an existing document after explicit approval."
        ),
        payload_model=EnqueueDocumentReprocessTaskInput,
        executor=_enqueue_document_reprocess_executor,
        side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
        requires_approval=True,
        input_example={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "source_task_id": "00000000-0000-0000-0000-000000000000",
            "reason": "Triaged replay regression needs a fresh parse.",
        },
    ),
    "apply_harness_config_update": AgentTaskActionDefinition(
        task_type="apply_harness_config_update",
        definition_kind="promotion",
        description=(
            "Apply a verified draft harness configuration as a new review harness after approval."
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
    ),
}


def list_agent_task_actions() -> list[AgentTaskActionDefinition]:
    return list(_ACTION_REGISTRY.values())


def get_agent_task_action(task_type: str) -> AgentTaskActionDefinition:
    try:
        return _ACTION_REGISTRY[task_type]
    except KeyError as exc:
        available = ", ".join(sorted(_ACTION_REGISTRY))
        raise ValueError(f"Unknown agent task type '{task_type}'. Available: {available}") from exc


def validate_agent_task_input(task_type: str, raw_input: dict) -> BaseModel:
    action = get_agent_task_action(task_type)
    return action.payload_model.model_validate(raw_input or {})


def validate_agent_task_output(task_type: str, raw_output: dict) -> dict:
    action = get_agent_task_action(task_type)
    if action.output_model is None:
        return raw_output or {}
    validated_output = action.output_model.model_validate(raw_output or {})
    return validated_output.model_dump(mode="json", exclude_none=True)


def execute_agent_task_action(session: Session, task: AgentTask) -> dict:
    action = get_agent_task_action(task.task_type)
    payload = action.payload_model.model_validate(task.input_json or {})
    result = action.executor(session, task, payload)
    validated_output = validate_agent_task_output(task.task_type, result)
    return {
        "task_type": task.task_type,
        "definition_kind": action.definition_kind,
        "side_effect_level": action.side_effect_level,
        "requires_approval": action.requires_approval,
        "output_schema_name": action.output_schema_name,
        "output_schema_version": action.output_schema_version,
        "payload": validated_output,
    }
