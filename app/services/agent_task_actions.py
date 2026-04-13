from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    EnqueueDocumentReprocessTaskInput,
    LatestEvaluationTaskInput,
    QualityEvalCandidatesTaskInput,
    ReplaySearchRequestTaskInput,
    TriageReplayRegressionTaskInput,
    VerifySearchHarnessEvaluationTaskInput,
)
from app.schemas.search import SearchHarnessEvaluationRequest, SearchReplayRunRequest
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
    evaluate_search_harness_verification,
    verify_search_harness_evaluation_task,
)
from app.services.documents import (
    get_latest_document_evaluation_detail,
    reprocess_document,
)
from app.services.quality import list_quality_eval_candidates
from app.services.search_harness_evaluations import evaluate_search_harness
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


def execute_agent_task_action(session: Session, task: AgentTask) -> dict:
    action = get_agent_task_action(task.task_type)
    payload = action.payload_model.model_validate(task.input_json or {})
    result = action.executor(session, task, payload)
    return {
        "task_type": task.task_type,
        "definition_kind": action.definition_kind,
        "side_effect_level": action.side_effect_level,
        "requires_approval": action.requires_approval,
        "payload": result,
    }
