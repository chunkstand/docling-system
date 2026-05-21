from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_semantics import (
    ApplyOntologyExtensionTaskOutput,
    DraftOntologyExtensionTaskOutput,
    VerifyDraftOntologyExtensionTaskOutput,
)
from app.services import agent_task_context_resolvers as context_resolvers
from app.services.agent_task_context_store import (
    derive_freshness_status,
    payload_sha256,
    verification_payload,
)


def _resolve_ontology_source_task_context(
    session: Session,
    *,
    task_id: UUID,
    source_task_id: UUID | None,
    source_task_type: str | None,
) -> task_core.TaskContextEnvelope | None:
    if source_task_id is None:
        return None
    resolved_source_task_type = source_task_type
    if resolved_source_task_type is None:
        source_task = session.get(AgentTask, source_task_id)
        resolved_source_task_type = source_task.task_type if source_task is not None else None
    if resolved_source_task_type == "triage_semantic_pass":
        return context_resolvers.resolve_required_dependency_task_output_context(
            session,
            task_id=task_id,
            depends_on_task_id=source_task_id,
            dependency_kind="source_task",
            expected_task_type="triage_semantic_pass",
            expected_schema_name="triage_semantic_pass_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Ontology extension draft must declare the semantic triage task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Semantic triage task must be rerun after the context migration "
                "before ontology drafting."
            ),
        )
    if resolved_source_task_type == "discover_semantic_bootstrap_candidates":
        return context_resolvers.resolve_required_dependency_task_output_context(
            session,
            task_id=task_id,
            depends_on_task_id=source_task_id,
            dependency_kind="source_task",
            expected_task_type="discover_semantic_bootstrap_candidates",
            expected_schema_name="discover_semantic_bootstrap_candidates_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Ontology extension draft must declare the bootstrap discovery task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Bootstrap discovery task must be rerun after the context migration "
                "before ontology drafting."
            ),
        )
    return None


def _build_draft_ontology_extension_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = DraftOntologyExtensionTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    source_context = _resolve_ontology_source_task_context(
        session,
        task_id=task.id,
        source_task_id=output.draft.source_task_id,
        source_task_type=output.draft.source_task_type,
    )
    if source_context is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="source_task",
                ref_kind="task_output",
                summary="Typed source task that motivated this ontology extension draft.",
                task_id=source_context.task_id,
                schema_name=source_context.output_schema_name,
                schema_version=source_context.output_schema_version,
                observed_sha256=payload_sha256(source_context.output),
                source_updated_at=source_context.task_updated_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="ontology_extension_draft_artifact",
                ref_kind="artifact",
                summary="Persisted ontology extension draft artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary = task_core.TaskContextSummary(
        headline=(
            f"Drafted ontology extension {output.draft.proposed_ontology_version} with "
            f"{len(output.draft.operations)} operation(s)."
        ),
        goal="Capture a reviewable ontology extension draft without changing live state.",
        decision="The ontology draft is ready for verification against active documents.",
        next_action=(
            "Create verify_draft_ontology_extension before any ontology publication step."
        ),
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "operation_count": len(output.draft.operations),
            "document_count": len(output.draft.document_ids),
            "success_metric_pass_count": sum(
                1 for item in output.draft.success_metrics if item.passed
            ),
        },
    )
    return task_core.TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=derive_freshness_status(refs) or task_core.ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_verify_draft_ontology_extension_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = VerifyDraftOntologyExtensionTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    draft_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_ontology_extension",
        expected_schema_name="draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Ontology extension verification must declare the requested ontology draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Ontology extension draft must be rerun after the context migration "
            "before verification."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Typed ontology extension draft consumed by this verification task.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
            checked_at=now,
            freshness_status=task_core.ContextFreshnessStatus.FRESH,
        )
    )

    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the ontology extension verification gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="ontology_extension_verification_artifact",
                ref_kind="artifact",
                summary="Persisted ontology extension verification artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary = task_core.TaskContextSummary(
        headline=(
            f"Ontology verification {output.verification.outcome} for "
            f"{output.draft.proposed_ontology_version}."
        ),
        goal="Verify a draft ontology extension against active document semantics.",
        decision=(
            "The ontology draft is ready for approval and apply."
            if output.verification.outcome == "passed"
            else "Revise the ontology draft before any publication step."
        ),
        next_action=(
            "Create apply_ontology_extension after approval."
            if output.verification.outcome == "passed"
            else "Refine the ontology draft and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "improved_document_count": output.summary.get("improved_document_count"),
            "regressed_document_count": output.summary.get("regressed_document_count"),
            "operation_count": len(output.draft.operations),
        },
    )
    return task_core.TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=derive_freshness_status(refs) or task_core.ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_apply_ontology_extension_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = ApplyOntologyExtensionTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    draft_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_ontology_extension",
        expected_schema_name="draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply ontology task must declare the requested ontology draft "
            "as a draft_task dependency."
        ),
        rerun_message=(
            "Ontology draft task must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Typed ontology draft output applied to the active workspace snapshot.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
            checked_at=now,
            freshness_status=task_core.ContextFreshnessStatus.FRESH,
        )
    )

    verification_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_draft_ontology_extension",
        expected_schema_name="verify_draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply ontology task must declare the requested ontology verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Ontology verification task must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary="Typed ontology verification output authorizing the apply step.",
            task_id=verification_context.task_id,
            schema_name=verification_context.output_schema_name,
            schema_version=verification_context.output_schema_version,
            observed_sha256=payload_sha256(verification_context.output),
            source_updated_at=verification_context.task_updated_at,
            checked_at=now,
            freshness_status=task_core.ContextFreshnessStatus.FRESH,
        )
    )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="applied_ontology_artifact",
                ref_kind="artifact",
                summary="Persisted apply artifact for the active ontology snapshot update.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    verification_output = VerifyDraftOntologyExtensionTaskOutput.model_validate(
        verification_context.output
    )
    summary = task_core.TaskContextSummary(
        headline=f"Applied ontology snapshot {output.applied_ontology_version}.",
        goal="Publish a verified ontology extension after approval.",
        decision="The active ontology snapshot is updated and ready for downstream reprocessing.",
        next_action=(
            "Create enqueue_document_reprocess for affected documents or "
            "refresh grounded artifacts against the new ontology."
        ),
        approval_state="approved" if task.approved_at is not None else "pending",
        verification_state=verification_output.verification.outcome,
        metrics={
            "operation_count": len(output.applied_operations),
            "improved_document_count": verification_output.summary.get("improved_document_count"),
            "regressed_document_count": verification_output.summary.get("regressed_document_count"),
        },
    )
    return task_core.TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=derive_freshness_status(refs) or task_core.ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )
