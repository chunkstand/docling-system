from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskVerification,
)
from app.schemas.agent_tasks import (
    EvaluateDocumentGenerationContextPackTaskInput,
    PrepareReportAgentHarnessTaskOutput,
)
from app.services.agent_actions.report_readiness import (
    enforce_context_pack_release_readiness_db_gate,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
)
from app.services.evidence import (
    DOCUMENT_GENERATION_CONTEXT_PACK_GATE,
)
from app.services.evidence_operator_runs import record_knowledge_operator_run
from app.services.storage import StorageService
from app.services.technical_reports import (
    evaluate_document_generation_context_pack,
)


def evaluate_document_generation_context_pack_executor(
    session: Session,
    task: AgentTask,
    payload: EvaluateDocumentGenerationContextPackTaskInput,
) -> dict:
    harness_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_report_agent_harness",
        expected_schema_name="prepare_report_agent_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Context-pack evaluation must declare the report harness as a target_task dependency."
        ),
        rerun_message=(
            "Report agent harness must be rerun after the context-pack migration before evaluation."
        ),
    )
    harness_output = PrepareReportAgentHarnessTaskOutput.model_validate(harness_context.output)
    context_pack_payload = (
        harness_output.context_pack.model_dump(mode="json")
        if harness_output.context_pack is not None
        else (
            harness_output.harness.document_generation_context_pack.model_dump(mode="json")
            if harness_output.harness.document_generation_context_pack is not None
            else {}
        )
    )
    if not context_pack_payload:
        raise ValueError(
            "Report harness did not include a document_generation_context_pack; rerun the "
            "prepare_report_agent_harness task."
        )
    evaluation_payload = evaluate_document_generation_context_pack(
        context_pack_payload,
        target_task_id=payload.target_task_id,
        min_traceable_claim_ratio=payload.min_traceable_claim_ratio,
        min_context_ref_count=payload.min_context_ref_count,
        max_blocked_step_count=payload.max_blocked_step_count,
        require_source_evidence_packages=payload.require_source_evidence_packages,
        require_release_readiness_assessments=payload.require_release_readiness_assessments,
        require_fresh_context=payload.require_fresh_context,
    )
    enforce_context_pack_release_readiness_db_gate(
        session,
        context_pack_payload=context_pack_payload,
        evaluation_payload=evaluation_payload,
        required=payload.require_release_readiness_assessments,
    )
    verification = create_agent_task_verification_record(
        session,
        target_task_id=payload.target_task_id,
        verification_task_id=task.id,
        verifier_type="document_generation_context_pack_gate",
        outcome=evaluation_payload["gate_outcome"],
        metrics=evaluation_payload["summary"],
        reasons=evaluation_payload["reasons"],
        details={
            "thresholds": evaluation_payload["thresholds"],
            "checks": evaluation_payload["checks"],
            "trace": evaluation_payload["trace"],
            "context_pack_sha256": evaluation_payload["context_pack_sha256"],
        },
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="document_generation_context_pack_evaluation",
        operator_version="v1",
        agent_task_id=task.id,
        config=evaluation_payload["thresholds"],
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "harness_task_type": harness_context.task_type,
            "context_pack_sha256": evaluation_payload["context_pack_sha256"],
        },
        output_payload=evaluation_payload,
        metrics=evaluation_payload["summary"],
        metadata={
            "audit_role": (
                "records pre-generation quality evaluation for the document generation context pack"
            ),
        },
        inputs=[
            {
                "input_kind": "document_generation_context_pack",
                "source_table": "agent_tasks",
                "source_id": payload.target_task_id,
                "payload": {
                    "context_pack_sha256": evaluation_payload["context_pack_sha256"],
                    "context_pack_id": evaluation_payload["context_pack_id"],
                },
            }
        ],
        outputs=[
            {
                "output_kind": "document_generation_context_pack_evaluation",
                "target_table": "agent_task_verifications",
                "target_id": verification.verification_id,
                "payload": {
                    "outcome": verification.outcome,
                    "failed_check_count": evaluation_payload["summary"].get(
                        "failed_check_count",
                    ),
                },
            }
        ],
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="document_generation_context_pack_evaluation",
        payload=evaluation_payload,
        storage_service=StorageService(),
        filename="document_generation_context_pack_evaluation.json",
    )
    return {
        "harness": harness_output.harness.model_dump(mode="json"),
        "context_pack": context_pack_payload,
        "evaluation": evaluation_payload,
        "verification": verification.model_dump(mode="json"),
        "context_pack_artifact_id": (
            str(harness_output.context_pack_artifact_id)
            if harness_output.context_pack_artifact_id is not None
            else None
        ),
        "context_pack_artifact_kind": harness_output.context_pack_artifact_kind,
        "context_pack_artifact_path": harness_output.context_pack_artifact_path,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }


def _context_pack_sha256_from_harness_output(
    harness_output: PrepareReportAgentHarnessTaskOutput,
) -> str | None:
    if harness_output.context_pack is not None:
        return harness_output.context_pack.context_pack_sha256
    if harness_output.harness.document_generation_context_pack is not None:
        return harness_output.harness.document_generation_context_pack.context_pack_sha256
    return None


def require_passed_context_pack_gate(
    session: Session,
    *,
    harness_task_id: UUID,
    harness_output: PrepareReportAgentHarnessTaskOutput,
) -> AgentTaskVerification:
    latest_gate = session.scalar(
        select(AgentTaskVerification)
        .where(
            AgentTaskVerification.target_task_id == harness_task_id,
            AgentTaskVerification.verifier_type == DOCUMENT_GENERATION_CONTEXT_PACK_GATE,
        )
        .order_by(
            AgentTaskVerification.created_at.desc(),
            AgentTaskVerification.id.desc(),
        )
    )
    if latest_gate is None:
        raise ValueError(
            "Technical report drafting requires a passed "
            "evaluate_document_generation_context_pack task for the report harness."
        )
    if latest_gate.outcome != "passed":
        raise ValueError(
            "Technical report drafting requires the latest context-pack gate to pass; "
            f"latest outcome was '{latest_gate.outcome}'."
        )
    if latest_gate.verification_task_id is None:
        raise ValueError(
            "Technical report drafting requires a context-pack gate linked to its evaluation task."
        )
    evaluation_task = session.get(AgentTask, latest_gate.verification_task_id)
    if (
        evaluation_task is None
        or evaluation_task.task_type != "evaluate_document_generation_context_pack"
    ):
        raise ValueError(
            "Technical report drafting requires a valid "
            "evaluate_document_generation_context_pack verifier task."
        )
    if evaluation_task.status != "completed":
        raise ValueError(
            "Technical report drafting requires a completed context-pack evaluation task."
        )
    expected_sha = _context_pack_sha256_from_harness_output(harness_output)
    observed_sha = (latest_gate.details_json or {}).get("context_pack_sha256")
    if expected_sha and observed_sha != expected_sha:
        raise ValueError(
            "Technical report drafting requires the passed context-pack gate to match "
            "the current report harness context_pack_sha256."
        )
    readiness_check_passed = any(
        check.get("check_key") == "release_readiness_assessments" and check.get("passed") is True
        for check in (latest_gate.details_json or {}).get("checks") or []
    )
    if not readiness_check_passed:
        raise ValueError(
            "Technical report drafting requires the context-pack gate to verify ready, "
            "integrity-complete release-readiness assessments."
        )
    readiness_db_check_passed = any(
        check.get("check_key") == "release_readiness_assessment_db_integrity"
        and check.get("passed") is True
        for check in (latest_gate.details_json or {}).get("checks") or []
    )
    if not readiness_db_check_passed:
        raise ValueError(
            "Technical report drafting requires the context-pack gate to verify "
            "release-readiness assessments against the database."
        )
    return latest_gate
