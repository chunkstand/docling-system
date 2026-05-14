from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
)
from app.schemas.agent_task_reports import PlanTechnicalReportTaskInput
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.storage import StorageService
from app.services.technical_reports import (
    plan_technical_report,
)


def plan_technical_report_executor(
    session: Session,
    task: AgentTask,
    payload: PlanTechnicalReportTaskInput,
) -> dict:
    plan_payload = plan_technical_report(
        session,
        title=payload.title,
        goal=payload.goal,
        audience=payload.audience,
        document_ids=list(payload.document_ids),
        concept_keys=list(payload.concept_keys),
        category_keys=list(payload.category_keys),
        target_length=payload.target_length,
        review_policy=payload.review_policy,
        include_shadow_candidates=payload.include_shadow_candidates,
        candidate_extractor_name=payload.candidate_extractor_name,
        candidate_score_threshold=payload.candidate_score_threshold,
        max_shadow_candidates=payload.max_shadow_candidates,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="technical_report_plan",
        payload=plan_payload,
        storage_service=StorageService(),
        filename="technical_report_plan.json",
    )
    return {
        "plan": plan_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
