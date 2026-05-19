from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AgentTask
from app.schemas import agent_task_semantic_graph as graph_schemas


def draft_graph_promotions_task(
    session: Session,
    task: AgentTask,
    payload: graph_schemas.DraftGraphPromotionsTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    draft_graph_promotions_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    source_task = session.get(AgentTask, payload.source_task_id)
    if source_task is None:
        raise ValueError(f"Graph promotion source task not found: {payload.source_task_id}")
    if source_task.task_type == "build_shadow_semantic_graph":
        source_context = resolve_required_dependency_task_output_context_func(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
            dependency_kind="source_task",
            expected_task_type="build_shadow_semantic_graph",
            expected_schema_name="build_shadow_semantic_graph_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Graph promotion drafts must declare the requested shadow graph task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Source shadow graph task must be rerun after the context migration "
                "before drafting."
            ),
        )
        source_output = graph_schemas.BuildShadowSemanticGraphTaskOutput.model_validate(
            source_context.output
        )
        draft_payload = draft_graph_promotions_func(
            session,
            source_payload=source_output.shadow_graph.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_context.task_type,
            proposed_graph_version=payload.proposed_graph_version,
            rationale=payload.rationale,
            edge_ids=list(payload.edge_ids),
            min_score=payload.min_score,
        )
    elif source_task.task_type == "triage_semantic_graph_disagreements":
        source_context = resolve_required_dependency_task_output_context_func(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
            dependency_kind="source_task",
            expected_task_type="triage_semantic_graph_disagreements",
            expected_schema_name="triage_semantic_graph_disagreements_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Graph promotion drafts must declare the requested graph triage task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Source graph triage task must be rerun after the context migration "
                "before drafting."
            ),
        )
        source_output = graph_schemas.TriageSemanticGraphDisagreementsTaskOutput.model_validate(
            source_context.output
        )
        draft_payload = draft_graph_promotions_func(
            session,
            source_payload=source_output.disagreement_report.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_context.task_type,
            proposed_graph_version=payload.proposed_graph_version,
            rationale=payload.rationale,
            edge_ids=list(payload.edge_ids),
            min_score=payload.min_score,
        )
    else:
        raise ValueError(
            f"Unsupported source task for graph promotion draft: {source_task.task_type}"
        )
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="semantic_graph_promotion_draft",
        payload=draft_payload,
        storage_service=storage_service_factory(),
        filename="semantic_graph_promotion_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def verify_draft_graph_promotions_task(
    session: Session,
    task: AgentTask,
    payload: graph_schemas.VerifyDraftGraphPromotionsTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    verify_draft_graph_promotions_func,
    create_agent_task_verification_record_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    target_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_graph_promotions",
        expected_schema_name="draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Graph promotion verification must declare the requested graph draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target graph promotion draft must be rerun after the context migration "
            "before verification."
        ),
    )
    draft_output = graph_schemas.DraftGraphPromotionsTaskOutput.model_validate(
        target_context.output
    )
    summary, metrics, reasons, outcome, success_metrics = verify_draft_graph_promotions_func(
        session,
        draft_output.draft.model_dump(mode="json"),
        min_supporting_document_count=payload.min_supporting_document_count,
        max_conflict_count=payload.max_conflict_count,
        require_current_ontology_snapshot=payload.require_current_ontology_snapshot,
    )
    verification_record = create_agent_task_verification_record_func(
        session,
        target_task_id=payload.target_task_id,
        verification_task_id=task.id,
        verifier_type="semantic_graph_promotion_gate",
        outcome=outcome,
        metrics=metrics,
        reasons=reasons,
        details=summary,
    )
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="semantic_graph_promotion_verification",
        payload={
            "draft": draft_output.draft.model_dump(mode="json"),
            "summary": summary,
            "success_metrics": success_metrics,
            "verification": verification_record.model_dump(mode="json"),
        },
        storage_service=storage_service_factory(),
        filename="semantic_graph_promotion_verification.json",
    )
    return {
        "draft": draft_output.draft.model_dump(mode="json"),
        "summary": summary,
        "success_metrics": success_metrics,
        "verification": verification_record.model_dump(mode="json"),
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def apply_graph_promotions_task(
    session: Session,
    task: AgentTask,
    payload: graph_schemas.ApplyGraphPromotionsTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    apply_graph_promotions_func,
    create_agent_task_artifact_func,
    storage_service_factory,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_graph_promotions",
        expected_schema_name="draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply graph promotions must declare the requested graph draft task "
            "as a draft_task dependency."
        ),
        rerun_message=(
            "Graph promotion draft task must be rerun after the context migration before apply."
        ),
    )
    verification_context = resolve_required_dependency_task_output_context_func(
        session,
        task_id=task.id,
        depends_on_task_id=payload.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_draft_graph_promotions",
        expected_schema_name="verify_draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply graph promotions must declare the requested graph verification task "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Graph promotion verification task must be rerun after the context "
            "migration before apply."
        ),
    )
    draft_output = graph_schemas.DraftGraphPromotionsTaskOutput.model_validate(draft_context.output)
    verification_output = graph_schemas.VerifyDraftGraphPromotionsTaskOutput.model_validate(
        verification_context.output
    )
    if verification_output.verification.outcome != "passed":
        raise ValueError("Only passed graph promotion verifications can be applied.")
    apply_payload = apply_graph_promotions_func(
        session,
        draft_output.draft.model_dump(mode="json"),
        source_task_id=task.id,
        source_task_type=task.task_type,
        reason=payload.reason,
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
        artifact_kind="applied_semantic_graph_snapshot",
        payload=apply_payload,
        storage_service=storage_service_factory(),
        filename="applied_semantic_graph_snapshot.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
