from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_semantic_graph import (
    ApplyGraphPromotionsTaskOutput,
    DraftGraphPromotionsTaskOutput,
    VerifyDraftGraphPromotionsTaskOutput,
)
from app.services import agent_task_context_resolvers as context_resolvers
from app.services.agent_task_context_store import (
    derive_freshness_status,
    payload_sha256,
    verification_payload,
)


def _build_draft_graph_promotions_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = DraftGraphPromotionsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    source_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft.source_task_id,
        dependency_kind="source_task",
        expected_task_type=output.draft.source_task_type,
        expected_schema_name=(
            "build_shadow_semantic_graph_output"
            if output.draft.source_task_type == "build_shadow_semantic_graph"
            else "triage_semantic_graph_disagreements_output"
        ),
        expected_schema_version="1.0",
        dependency_error_message=(
            "Graph promotion drafts must declare the source graph task as a source_task dependency."
        ),
        rerun_message=(
            "Source graph task must be rerun after the context migration before drafting."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="source_task",
            ref_kind="task_output",
            summary="Typed source graph task that motivated this promotion draft.",
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
                ref_key="semantic_graph_promotion_draft_artifact",
                ref_kind="artifact",
                summary="Persisted semantic graph promotion draft artifact.",
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
            f"Drafted graph promotion {output.draft.proposed_graph_version} with "
            f"{len(output.draft.promoted_edges)} edge(s)."
        ),
        goal="Prepare a reviewable graph-memory update without mutating live graph state.",
        decision="The graph promotion draft is ready for verification against the live ontology.",
        next_action="Create verify_draft_graph_promotions before any apply step.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "promoted_edge_count": len(output.draft.promoted_edges),
            "effective_edge_count": output.draft.effective_graph.edge_count,
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


def _build_verify_draft_graph_promotions_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = VerifyDraftGraphPromotionsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    draft_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_graph_promotions",
        expected_schema_name="draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Graph promotion verification must declare the requested graph draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Graph promotion draft must be rerun after the context migration before verification."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Typed graph promotion draft consumed by this verification task.",
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
                summary="Verifier record for the semantic graph promotion gate.",
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
                ref_key="semantic_graph_promotion_verification_artifact",
                ref_kind="artifact",
                summary="Persisted graph promotion verification artifact.",
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
            f"Graph promotion verification {output.verification.outcome} for "
            f"{output.draft.proposed_graph_version}."
        ),
        goal=(
            "Verify graph-memory promotions against ontology, traceability, and "
            "conflict constraints."
        ),
        decision=(
            "The graph promotion draft is ready for approval and apply."
            if output.verification.outcome == "passed"
            else "Revise the graph promotion draft before any apply step."
        ),
        next_action=(
            "Create apply_graph_promotions after approval."
            if output.verification.outcome == "passed"
            else "Refine the graph promotion draft and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "promoted_edge_count": output.summary.get("promoted_edge_count"),
            "supported_edge_count": output.summary.get("supported_edge_count"),
            "conflict_count": output.summary.get("conflict_count"),
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


def _build_apply_graph_promotions_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = ApplyGraphPromotionsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    draft_context = context_resolvers.resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_graph_promotions",
        expected_schema_name="draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply graph promotions must declare the requested graph draft as "
            "a draft_task dependency."
        ),
        rerun_message=(
            "Graph promotion draft task must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Typed graph promotion draft applied to the active workspace graph snapshot.",
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
        expected_task_type="verify_draft_graph_promotions",
        expected_schema_name="verify_draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply graph promotions must declare the requested graph verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Graph promotion verification task must be rerun after the context "
            "migration before apply."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary="Typed graph promotion verification output authorizing the apply step.",
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
                ref_key="applied_semantic_graph_artifact",
                ref_kind="artifact",
                summary="Persisted apply artifact for the active semantic graph snapshot update.",
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

    verification_output = VerifyDraftGraphPromotionsTaskOutput.model_validate(
        verification_context.output
    )
    summary = task_core.TaskContextSummary(
        headline=f"Applied semantic graph snapshot {output.applied_graph_version}.",
        goal="Publish verified graph-memory promotions after explicit approval.",
        decision=(
            "The active graph snapshot is updated and ready for downstream "
            "generation and orchestration."
        ),
        next_action=(
            "Refresh semantic generation briefs or build new graph-aware tasks "
            "against the active snapshot."
        ),
        approval_state="approved" if task.approved_at is not None else "pending",
        verification_state=verification_output.verification.outcome,
        metrics={
            "applied_edge_count": output.applied_edge_count,
            "supported_edge_count": verification_output.summary.get("supported_edge_count"),
            "conflict_count": verification_output.summary.get("conflict_count"),
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
