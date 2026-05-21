from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_semantic_generation import (
    DraftSemanticGroundedDocumentTaskOutput,
    VerifySemanticGroundedDocumentTaskInput,
    VerifySemanticGroundedDocumentTaskOutput,
)
from app.schemas.agent_task_semantics import (
    DraftSemanticRegistryUpdateTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
)
from app.services.agent_task_context import resolve_required_dependency_task_output_context
from app.services.agent_task_verification_records import create_agent_task_verification_record
from app.services.semantic_generation import verify_semantic_grounded_document
from app.services.semantic_orchestration import (
    semantic_registry_verification_metrics,
    semantic_registry_verification_summary,
)
from app.services.semantics import preview_semantic_registry_update_for_document


def verify_draft_semantic_registry_update_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifyDraftSemanticRegistryUpdateTaskInput,
    *,
    preview_registry_update_for_document_func=preview_semantic_registry_update_for_document,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=verification_task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_semantic_registry_update",
        expected_schema_name="draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Verification task must declare the requested semantic draft "
            "task as a target_task dependency."
        ),
        rerun_message=(
            "Target semantic draft task must be rerun after the context "
            "migration before it can be verified."
        ),
    )
    output = DraftSemanticRegistryUpdateTaskOutput.model_validate(draft_context.output)
    document_ids = payload.document_ids or output.draft.document_ids
    if not document_ids:
        raise ValueError("Semantic registry draft verification requires at least one document.")

    document_deltas = [
        preview_registry_update_for_document_func(
            session,
            document_id,
            output.draft.effective_registry,
        )
        for document_id in document_ids
    ]
    summary = semantic_registry_verification_summary(document_deltas)
    reasons: list[str] = []
    if summary["regressed_document_count"] > payload.max_regressed_document_count:
        reasons.append("Draft regresses more documents than the allowed threshold.")
    if summary["regressed_expectation_count"] > payload.max_failed_expectation_increase:
        reasons.append("Draft increases failed semantic expectations beyond the allowed threshold.")
    if summary["improved_document_count"] < payload.min_improved_document_count:
        reasons.append("Draft does not improve enough documents to justify publication.")
    outcome = "passed" if not reasons else "failed"
    metrics = {
        "document_count": summary["document_count"],
        "improved_document_count": summary["improved_document_count"],
        "regressed_document_count": summary["regressed_document_count"],
        "total_improved_count": summary["improved_expectation_count"],
        "total_regressed_count": summary["regressed_expectation_count"],
        "total_added_concept_count": summary["added_concept_count"],
        "total_removed_concept_count": summary["removed_concept_count"],
    }
    details = {
        "thresholds": {
            "max_regressed_document_count": payload.max_regressed_document_count,
            "max_failed_expectation_increase": payload.max_failed_expectation_increase,
            "min_improved_document_count": payload.min_improved_document_count,
        },
        "summary": summary,
        "target_task_id": str(draft_context.task_id),
        "target_task_type": draft_context.task_type,
        "proposed_registry_version": output.draft.proposed_registry_version,
    }
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=verification_task.id,
        verifier_type="semantic_registry_draft_gate",
        outcome=outcome,
        metrics=metrics,
        reasons=reasons,
        details=details,
    )
    verified_output = VerifyDraftSemanticRegistryUpdateTaskOutput(
        draft=output.draft,
        document_deltas=document_deltas,
        summary=summary,
        success_metrics=semantic_registry_verification_metrics(
            draft=output.draft.model_dump(mode="json"),
            document_deltas=document_deltas,
        ),
        verification=record,
        artifact_id=UUID(int=0),
        artifact_kind="semantic_registry_draft_verification",
        artifact_path=None,
    )
    payload_json = verified_output.model_dump(mode="json")
    payload_json.pop("artifact_id", None)
    payload_json.pop("artifact_kind", None)
    payload_json.pop("artifact_path", None)
    return payload_json


def verify_semantic_grounded_document_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifySemanticGroundedDocumentTaskInput,
    *,
    verify_grounded_document_func=verify_semantic_grounded_document,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=verification_task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_semantic_grounded_document",
        expected_schema_name="draft_semantic_grounded_document_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Verification task must declare the requested grounded-document "
            "draft as a target_task dependency."
        ),
        rerun_message=(
            "Target grounded-document draft must be rerun after the context "
            "migration before it can be verified."
        ),
    )
    output = DraftSemanticGroundedDocumentTaskOutput.model_validate(draft_context.output)
    outcome = verify_grounded_document_func(
        output.draft.model_dump(mode="json"),
        max_unsupported_claim_count=payload.max_unsupported_claim_count,
        require_full_claim_traceability=payload.require_full_claim_traceability,
        require_full_concept_coverage=payload.require_full_concept_coverage,
    )
    details = {
        **outcome.verification_details,
        "thresholds": {
            "max_unsupported_claim_count": payload.max_unsupported_claim_count,
            "require_full_claim_traceability": payload.require_full_claim_traceability,
            "require_full_concept_coverage": payload.require_full_concept_coverage,
        },
        "target_task_id": str(draft_context.task_id),
        "target_task_type": draft_context.task_type,
    }
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=verification_task.id,
        verifier_type="semantic_grounded_document_gate",
        outcome=outcome.verification_outcome,
        metrics=outcome.verification_metrics,
        reasons=outcome.verification_reasons,
        details=details,
    )
    verified_output = VerifySemanticGroundedDocumentTaskOutput(
        draft=output.draft,
        summary=outcome.summary,
        success_metrics=outcome.success_metrics,
        verification=record,
        artifact_id=UUID(int=0),
        artifact_kind="semantic_grounded_document_verification",
        artifact_path=None,
    )
    payload_json = verified_output.model_dump(mode="json")
    payload_json.pop("artifact_id", None)
    payload_json.pop("artifact_kind", None)
    payload_json.pop("artifact_path", None)
    return payload_json
