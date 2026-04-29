from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
)
from app.schemas.agent_tasks import (
    InspectEvalFailureCaseTaskInput,
    LatestEvaluationTaskInput,
    QualityEvalCandidatesTaskInput,
    RefreshEvalFailureCasesTaskInput,
    TriageEvalFailureCaseTaskInput,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.documents import (
    get_latest_document_evaluation_detail,
)
from app.services.eval_workbench import (
    inspect_eval_failure_case,
    refresh_eval_failure_cases,
    triage_eval_failure_case,
)
from app.services.quality import list_quality_eval_candidates
from app.services.storage import StorageService


def latest_evaluation_executor(
    session: Session, _task: AgentTask, payload: LatestEvaluationTaskInput
) -> dict:
    response = get_latest_document_evaluation_detail(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "evaluation": jsonable_encoder(response),
    }


def quality_eval_candidates_executor(
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


def refresh_eval_failure_cases_executor(
    session: Session,
    _task: AgentTask,
    payload: RefreshEvalFailureCasesTaskInput,
) -> dict:
    response = refresh_eval_failure_cases(
        session,
        limit=payload.limit,
        include_resolved=payload.include_resolved,
    )
    return {"refresh": jsonable_encoder(response)}


def inspect_eval_failure_case_executor(
    session: Session,
    _task: AgentTask,
    payload: InspectEvalFailureCaseTaskInput,
) -> dict:
    response = inspect_eval_failure_case(session, payload.case_id)
    return {"inspection": jsonable_encoder(response)}


def triage_eval_failure_case_executor(
    session: Session,
    task: AgentTask,
    payload: TriageEvalFailureCaseTaskInput,
) -> dict:
    response = triage_eval_failure_case(
        session,
        payload.case_id,
        agent_task_id=task.id,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="eval_failure_case_triage",
        payload=jsonable_encoder(response),
        storage_service=StorageService(),
        filename="eval_failure_case_triage.json",
    )
    return {
        "triage": jsonable_encoder(response),
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
