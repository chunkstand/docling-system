from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    LatestEvaluationTaskInput,
    QualityEvalCandidatesTaskInput,
    ReplaySearchRequestTaskInput,
)
from app.schemas.search import SearchHarnessEvaluationRequest, SearchReplayRunRequest
from app.services.documents import get_latest_document_evaluation_detail
from app.services.quality import list_quality_eval_candidates
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_history import replay_search_request
from app.services.search_replays import run_search_replay_suite


@dataclass(frozen=True)
class AgentTaskActionDefinition:
    task_type: str
    description: str
    payload_model: type[BaseModel]
    executor: callable
    side_effect_level: str = AgentTaskSideEffectLevel.READ_ONLY.value
    requires_approval: bool = False
    input_example: dict[str, Any] | None = None


def _latest_evaluation_executor(session: Session, payload: LatestEvaluationTaskInput) -> dict:
    response = get_latest_document_evaluation_detail(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "evaluation": jsonable_encoder(response),
    }


def _quality_eval_candidates_executor(
    session: Session, payload: QualityEvalCandidatesTaskInput
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


def _replay_search_request_executor(session: Session, payload: ReplaySearchRequestTaskInput) -> dict:
    response = replay_search_request(session, payload.search_request_id)
    return {
        "search_request_id": str(payload.search_request_id),
        "replay": jsonable_encoder(response),
    }


def _run_search_replay_suite_executor(session: Session, payload: SearchReplayRunRequest) -> dict:
    response = run_search_replay_suite(session, payload)
    return {
        "source_type": payload.source_type,
        "harness_name": payload.harness_name,
        "replay_run": jsonable_encoder(response),
    }


def _evaluate_search_harness_executor(
    session: Session, payload: SearchHarnessEvaluationRequest
) -> dict:
    response = evaluate_search_harness(session, payload)
    return {
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "evaluation": jsonable_encoder(response),
    }


_ACTION_REGISTRY: dict[str, AgentTaskActionDefinition] = {
    "get_latest_evaluation": AgentTaskActionDefinition(
        task_type="get_latest_evaluation",
        description="Fetch the latest persisted evaluation detail for one document.",
        payload_model=LatestEvaluationTaskInput,
        executor=_latest_evaluation_executor,
        input_example={"document_id": "00000000-0000-0000-0000-000000000000"},
    ),
    "list_quality_eval_candidates": AgentTaskActionDefinition(
        task_type="list_quality_eval_candidates",
        description="List mined evaluation candidates from failed evals and live search gaps.",
        payload_model=QualityEvalCandidatesTaskInput,
        executor=_quality_eval_candidates_executor,
        input_example={"limit": 12, "include_resolved": False},
    ),
    "replay_search_request": AgentTaskActionDefinition(
        task_type="replay_search_request",
        description="Replay one persisted search request against the current search stack.",
        payload_model=ReplaySearchRequestTaskInput,
        executor=_replay_search_request_executor,
        input_example={"search_request_id": "00000000-0000-0000-0000-000000000000"},
    ),
    "run_search_replay_suite": AgentTaskActionDefinition(
        task_type="run_search_replay_suite",
        description="Run a replay suite over persisted evaluation, feedback, or gap sources.",
        payload_model=SearchReplayRunRequest,
        executor=_run_search_replay_suite_executor,
        input_example={"source_type": "feedback", "limit": 12, "harness_name": "default_v1"},
    ),
    "evaluate_search_harness": AgentTaskActionDefinition(
        task_type="evaluate_search_harness",
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
    result = action.executor(session, payload)
    return {
        "task_type": task.task_type,
        "side_effect_level": action.side_effect_level,
        "requires_approval": action.requires_approval,
        "payload": result,
    }
