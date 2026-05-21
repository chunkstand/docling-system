from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_semantics import (
    ApplyOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskOutput,
    VerifyDraftOntologyExtensionTaskInput,
    VerifyDraftOntologyExtensionTaskOutput,
)
from app.services.agent_actions.semantic_governance_ontology_draft_support import (
    draft_ontology_extension_from_source_task,
)


def draft_ontology_extension_task(
    session: Session,
    task: AgentTask,
    payload: DraftOntologyExtensionTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    draft_ontology_extension_func,
    draft_ontology_extension_from_bootstrap_report_func,
    draft_ontology_extension_from_operations_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    if payload.operations:
        draft_payload = draft_ontology_extension_from_operations_func(
            session,
            [operation.model_dump(mode="json") for operation in payload.operations],
            source_task_id=None,
            source_task_type=None,
            proposed_ontology_version=payload.proposed_ontology_version,
            rationale=payload.rationale,
        )
    else:
        draft_payload = draft_ontology_extension_from_source_task(
            session,
            task,
            payload,
            resolve_required_dependency_task_output_context_func=(
                resolve_required_dependency_task_output_context_func
            ),
            draft_ontology_extension_func=draft_ontology_extension_func,
            draft_ontology_extension_from_bootstrap_report_func=(
                draft_ontology_extension_from_bootstrap_report_func
            ),
        )

    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="ontology_extension_draft",
        payload=draft_payload,
        storage_service=storage_service_factory(),
        filename="ontology_extension_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def verify_draft_ontology_extension_task(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftOntologyExtensionTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    verify_draft_ontology_extension_func,
    create_agent_task_verification_record_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_ontology_extension",
        expected_schema_name="draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Ontology extension verification must declare the requested ontology draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target ontology draft must be rerun after the context migration before verification."
        ),
    )
    output = DraftOntologyExtensionTaskOutput.model_validate(draft_context.output)
    (
        document_deltas,
        summary,
        metrics,
        reasons,
        outcome,
        success_metrics,
        lifecycle_preview,
    ) = verify_draft_ontology_extension_func(
        session,
        output.draft.model_dump(mode="json"),
        document_ids=payload.document_ids,
        max_regressed_document_count=payload.max_regressed_document_count,
        max_failed_expectation_increase=payload.max_failed_expectation_increase,
        min_improved_document_count=payload.min_improved_document_count,
    )
    details = {
        "thresholds": {
            "max_regressed_document_count": payload.max_regressed_document_count,
            "max_failed_expectation_increase": payload.max_failed_expectation_increase,
            "min_improved_document_count": payload.min_improved_document_count,
        },
        "summary": summary,
        "target_task_id": str(draft_context.task_id),
        "target_task_type": draft_context.task_type,
        "proposed_ontology_version": output.draft.proposed_ontology_version,
        "lifecycle_preview": lifecycle_preview,
    }
    record = create_agent_task_verification_record_func(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=task.id,
        verifier_type="ontology_extension_draft_gate",
        outcome=outcome,
        metrics=metrics,
        reasons=reasons,
        details=details,
    )
    result = {
        "draft": output.draft.model_dump(mode="json"),
        "document_deltas": document_deltas,
        "summary": summary,
        "lifecycle_preview": lifecycle_preview,
        "success_metrics": success_metrics,
        "verification": record.model_dump(mode="json"),
    }
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="ontology_extension_draft_verification",
        payload=result,
        storage_service=storage_service_factory(),
        filename="ontology_extension_draft_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def apply_ontology_extension_task(
    session: Session,
    task: AgentTask,
    payload: ApplyOntologyExtensionTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    apply_ontology_extension_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_ontology_extension",
        expected_schema_name="draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply ontology task must declare the requested ontology draft as "
            "a draft_task dependency."
        ),
        rerun_message=(
            "Ontology draft task must be rerun after the context migration before "
            "it can be applied."
        ),
    )
    verification_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_draft_ontology_extension",
        expected_schema_name="verify_draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply ontology task must declare the requested ontology verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Ontology verification task must be rerun after the context migration "
            "before it can be applied."
        ),
    )
    draft_output = DraftOntologyExtensionTaskOutput.model_validate(draft_context.output)
    verification_output = VerifyDraftOntologyExtensionTaskOutput.model_validate(
        verification_context.output
    )
    verification = verification_output.verification
    if verification.outcome != "passed":
        raise ValueError("Only passed ontology extension verifications can be applied.")
    if verification.target_task_id != payload.draft_task_id:
        raise ValueError("Verification task does not target the requested ontology draft task.")

    apply_payload = apply_ontology_extension_func(
        session,
        draft_output.draft.model_dump(mode="json"),
        source_task_id=task.id,
        source_task_type=task.task_type,
        reason=payload.reason,
        verification_summary=verification_output.summary,
        lifecycle_preview=(
            verification_output.lifecycle_preview.model_dump(mode="json")
            if verification_output.lifecycle_preview is not None
            else None
        ),
    )
    apply_payload.update(
        {
            "draft_task_id": str(payload.draft_task_id),
            "verification_task_id": str(payload.verification_task_id),
        }
    )
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="applied_ontology_extension",
        payload=apply_payload,
        storage_service=storage_service_factory(),
        filename="applied_ontology_extension.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
