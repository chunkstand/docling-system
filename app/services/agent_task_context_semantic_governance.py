from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

import app.services.agent_task_context_semantic_governance_graph as graph_owner
import app.services.agent_task_context_semantic_governance_ontology as ontology_owner
from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_semantics import (
    ApplySemanticRegistryUpdateTaskOutput,
    DraftSemanticRegistryUpdateTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
)
from app.services import agent_task_context_resolvers as context_resolvers
from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    resolve_context_builder_registry,
)
from app.services.agent_task_context_store import (
    derive_freshness_status,
    get_context_artifact_row,
    payload_sha256,
    verification_payload,
)

SEMANTIC_GOVERNANCE_CONTEXT_BUILDER_SYMBOLS = {
    "draft_semantic_registry_update": "_build_draft_semantic_registry_update_context",
    "draft_ontology_extension": "_build_draft_ontology_extension_context",
    "verify_draft_ontology_extension": "_build_verify_draft_ontology_extension_context",
    "apply_ontology_extension": "_build_apply_ontology_extension_context",
    "draft_graph_promotions": "_build_draft_graph_promotions_context",
    "verify_draft_graph_promotions": "_build_verify_draft_graph_promotions_context",
    "verify_draft_semantic_registry_update": (
        "_build_verify_draft_semantic_registry_update_context"
    ),
    "apply_semantic_registry_update": "_build_apply_semantic_registry_update_context",
    "apply_graph_promotions": "_build_apply_graph_promotions_context",
}

_resolve_ontology_source_task_context = ontology_owner._resolve_ontology_source_task_context
_build_draft_ontology_extension_context = ontology_owner._build_draft_ontology_extension_context
_build_verify_draft_ontology_extension_context = (
    ontology_owner._build_verify_draft_ontology_extension_context
)
_build_apply_ontology_extension_context = ontology_owner._build_apply_ontology_extension_context
_build_draft_graph_promotions_context = graph_owner._build_draft_graph_promotions_context
_build_verify_draft_graph_promotions_context = (
    graph_owner._build_verify_draft_graph_promotions_context
)
_build_apply_graph_promotions_context = graph_owner._build_apply_graph_promotions_context


def _build_draft_semantic_registry_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = DraftSemanticRegistryUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    source_task = session.get(AgentTask, output.draft.source_task_id)
    if source_task is not None:
        from app.services.agent_task_action_lookup import get_agent_task_action

        source_action = get_agent_task_action(source_task.task_type)
        source_context_row = get_context_artifact_row(session, source_task.id)
        observed_payload = (
            task_core.TaskContextEnvelope.model_validate(
                source_context_row.payload_json or {}
            ).output
            if source_context_row is not None
            else source_task.result_json or {}
        )
        refs.append(
            task_core.ContextRef(
                ref_key="source_task",
                ref_kind="task_output",
                summary="Source task that motivated this semantic registry draft.",
                task_id=source_task.id,
                schema_name=source_action.output_schema_name,
                schema_version=source_action.output_schema_version,
                observed_sha256=payload_sha256(observed_payload),
                source_updated_at=source_task.updated_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="draft_artifact",
                ref_kind="artifact",
                summary="Persisted semantic registry draft artifact for operator review.",
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
            f"Draft semantic registry {output.draft.proposed_registry_version} from "
            f"{output.draft.base_registry_version}."
        ),
        goal="Draft additive registry updates without mutating the live semantic contract.",
        decision="Draft created and ready for read-only verification.",
        next_action="Run verify_draft_semantic_registry_update against active documents.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "document_count": len(output.draft.document_ids),
            "operation_count": len(output.draft.operations),
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


def _build_verify_draft_semantic_registry_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = VerifyDraftSemanticRegistryUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    draft_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_semantic_registry_update",
        expected_schema_name="draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic draft verification must declare the requested draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Semantic draft task must be rerun after the context migration before verification."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated semantic registry draft output consumed by this verification.",
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
                summary="Verifier record persisted for the semantic registry draft gate.",
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
                ref_key="verification_artifact",
                ref_kind="artifact",
                summary="Persisted verification artifact for the semantic registry draft.",
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
        headline=(f"Verified semantic registry draft {output.draft.proposed_registry_version}."),
        goal="Validate additive registry updates against active documents before publication.",
        decision=(
            "Verification passed; the draft can move to approval review."
            if output.verification.outcome == "passed"
            else "Verification failed; revise the draft before publishing."
        ),
        next_action=(
            "Create apply_semantic_registry_update if the operator wants to publish the draft."
            if output.verification.outcome == "passed"
            else "Revise the draft registry update and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "document_count": len(output.document_deltas),
            "improved_document_count": output.summary.get("improved_document_count"),
            "regressed_document_count": output.summary.get("regressed_document_count"),
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


def _build_apply_semantic_registry_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = ApplySemanticRegistryUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    draft_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_semantic_registry_update",
        expected_schema_name="draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic registry apply must declare the requested draft as a draft_task dependency."
        ),
        rerun_message=(
            "Semantic registry draft must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated semantic registry draft output applied to the live registry file.",
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
        expected_task_type="verify_draft_semantic_registry_update",
        expected_schema_name="verify_draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic registry apply must declare the requested verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Semantic registry verification must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary=(
                "Migrated semantic registry verification output authorizing the live apply step."
            ),
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
                ref_key="applied_artifact",
                ref_kind="artifact",
                summary="Persisted apply artifact for the live semantic registry update.",
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

    verification_output = VerifyDraftSemanticRegistryUpdateTaskOutput.model_validate(
        verification_context.output
    )
    summary = task_core.TaskContextSummary(
        headline=f"Applied semantic registry {output.applied_registry_version}.",
        goal="Publish a verified semantic registry update after approval.",
        decision="Live semantic registry updated and ready for follow-on reprocessing.",
        next_action=(
            "Create enqueue_document_reprocess for affected documents if "
            "refreshed semantics are needed."
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


def build_semantic_governance_context_builders(
    available_symbols: Mapping[str, object],
) -> dict[str, AgentTaskContextBuilder]:
    return resolve_context_builder_registry(
        {**dict(available_symbols), **globals()},
        builder_symbols=SEMANTIC_GOVERNANCE_CONTEXT_BUILDER_SYMBOLS,
        registry_name="semantic_governance",
    )
