from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    ApplyGraphPromotionsTaskInput,
    ApplyGraphPromotionsTaskOutput,
    ApplyOntologyExtensionTaskInput,
    ApplyOntologyExtensionTaskOutput,
    ApplySemanticRegistryUpdateTaskInput,
    ApplySemanticRegistryUpdateTaskOutput,
    BuildShadowSemanticGraphTaskOutput,
    DiscoverSemanticBootstrapCandidatesTaskOutput,
    DraftGraphPromotionsTaskInput,
    DraftGraphPromotionsTaskOutput,
    DraftOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskOutput,
    DraftSemanticRegistryUpdateTaskInput,
    DraftSemanticRegistryUpdateTaskOutput,
    TriageSemanticGraphDisagreementsTaskOutput,
    TriageSemanticPassTaskOutput,
    VerifyDraftGraphPromotionsTaskInput,
    VerifyDraftGraphPromotionsTaskOutput,
    VerifyDraftOntologyExtensionTaskInput,
    VerifyDraftOntologyExtensionTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context_resolvers import (
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
    verify_draft_semantic_registry_update_task,
)
from app.services.semantic_graph import (
    apply_graph_promotions,
    draft_graph_promotions,
    verify_draft_graph_promotions,
)
from app.services.semantic_ontology import (
    apply_ontology_extension,
    draft_ontology_extension,
    draft_ontology_extension_from_bootstrap_report,
    verify_draft_ontology_extension,
)
from app.services.semantic_orchestration import (
    draft_semantic_registry_update,
    draft_semantic_registry_update_from_bootstrap_report,
    semantic_registry_apply_metrics,
)
from app.services.semantic_registry import (
    get_semantic_registry,
    persist_semantic_ontology_snapshot,
)
from app.services.storage import StorageService

SEMANTIC_GOVERNANCE_AGENT_ACTION_TASK_TYPES = (
    "draft_semantic_registry_update",
    "draft_ontology_extension",
    "draft_graph_promotions",
    "verify_draft_semantic_registry_update",
    "verify_draft_ontology_extension",
    "verify_draft_graph_promotions",
    "apply_semantic_registry_update",
    "apply_ontology_extension",
    "apply_graph_promotions",
)


def _draft_semantic_registry_update_executor(
    session: Session,
    task: AgentTask,
    payload: DraftSemanticRegistryUpdateTaskInput,
) -> dict:
    source_task = session.get(AgentTask, payload.source_task_id)
    if source_task is None:
        raise ValueError(f"Source task not found: {payload.source_task_id}")
    if source_task.task_type == "triage_semantic_pass":
        source_context = resolve_required_dependency_task_output_context(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
            dependency_kind="source_task",
            expected_task_type="triage_semantic_pass",
            expected_schema_name="triage_semantic_pass_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Semantic registry drafts must declare the requested semantic triage task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Source semantic triage task must be rerun after the context "
                "migration before drafting."
            ),
        )
        source_output = TriageSemanticPassTaskOutput.model_validate(source_context.output)
        draft_payload = draft_semantic_registry_update(
            session,
            source_output.gap_report.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_context.task_type,
            proposed_registry_version=payload.proposed_registry_version,
            rationale=payload.rationale,
            candidate_ids=list(payload.candidate_ids),
        )
    elif source_task.task_type == "discover_semantic_bootstrap_candidates":
        source_context = resolve_required_dependency_task_output_context(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
            dependency_kind="source_task",
            expected_task_type="discover_semantic_bootstrap_candidates",
            expected_schema_name="discover_semantic_bootstrap_candidates_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Semantic registry drafts must declare the requested bootstrap candidate task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Source bootstrap candidate task must be rerun after the context "
                "migration before drafting."
            ),
        )
        source_output = DiscoverSemanticBootstrapCandidatesTaskOutput.model_validate(
            source_context.output
        )
        draft_payload = draft_semantic_registry_update_from_bootstrap_report(
            session,
            source_output.report.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_context.task_type,
            proposed_registry_version=payload.proposed_registry_version,
            rationale=payload.rationale,
            candidate_ids=list(payload.candidate_ids),
        )
    else:
        from app.services.agent_task_action_lookup import get_agent_task_action

        unsupported_action = get_agent_task_action(source_task.task_type)
        resolve_required_task_output_context(
            session,
            task_id=payload.source_task_id,
            expected_task_type=source_task.task_type,
            expected_schema_name=unsupported_action.output_schema_name or "",
            expected_schema_version=unsupported_action.output_schema_version or "",
            rerun_message=(
                "Source task must be rerun after the context migration before drafting."
            ),
        )
        raise ValueError(
            f"Unsupported source task for semantic registry draft: {source_task.task_type}"
        )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_registry_draft",
        payload=draft_payload,
        storage_service=StorageService(),
        filename="semantic_registry_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _draft_ontology_extension_executor(
    session: Session,
    task: AgentTask,
    payload: DraftOntologyExtensionTaskInput,
) -> dict:
    source_task = session.get(AgentTask, payload.source_task_id)
    if source_task is None:
        raise ValueError(f"Ontology extension source task not found: {payload.source_task_id}")

    if source_task.task_type == "triage_semantic_pass":
        source_context = resolve_required_dependency_task_output_context(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
            dependency_kind="source_task",
            expected_task_type="triage_semantic_pass",
            expected_schema_name="triage_semantic_pass_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Ontology extension draft must declare the semantic triage task as "
                "a source_task dependency."
            ),
            rerun_message=(
                "Semantic triage task must be rerun after the context migration "
                "before ontology drafting."
            ),
        )
        triage_output = TriageSemanticPassTaskOutput.model_validate(source_context.output)
        draft_payload = draft_ontology_extension(
            session,
            triage_output.gap_report.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_task.task_type,
            proposed_ontology_version=payload.proposed_ontology_version,
            rationale=payload.rationale,
            candidate_ids=payload.candidate_ids,
        )
    elif source_task.task_type == "discover_semantic_bootstrap_candidates":
        source_context = resolve_required_dependency_task_output_context(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
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
        bootstrap_output = DiscoverSemanticBootstrapCandidatesTaskOutput.model_validate(
            source_context.output
        )
        draft_payload = draft_ontology_extension_from_bootstrap_report(
            session,
            bootstrap_output.report.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_task.task_type,
            proposed_ontology_version=payload.proposed_ontology_version,
            rationale=payload.rationale,
            candidate_ids=payload.candidate_ids,
        )
    else:
        raise ValueError(
            "Ontology extension drafting only supports triage_semantic_pass or "
            "discover_semantic_bootstrap_candidates source tasks."
        )

    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="ontology_extension_draft",
        payload=draft_payload,
        storage_service=StorageService(),
        filename="ontology_extension_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _verify_draft_semantic_registry_update_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftSemanticRegistryUpdateTaskInput,
) -> dict:
    result = verify_draft_semantic_registry_update_task(session, task, payload)
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_registry_draft_verification",
        payload=result,
        storage_service=StorageService(),
        filename="semantic_registry_draft_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _verify_draft_ontology_extension_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftOntologyExtensionTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
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
    ) = verify_draft_ontology_extension(
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
    }
    record = create_agent_task_verification_record(
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
        "success_metrics": success_metrics,
        "verification": record.model_dump(mode="json"),
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="ontology_extension_draft_verification",
        payload=result,
        storage_service=StorageService(),
        filename="ontology_extension_draft_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _apply_semantic_registry_update_executor(
    session: Session,
    task: AgentTask,
    payload: ApplySemanticRegistryUpdateTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_semantic_registry_update",
        expected_schema_name="draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested semantic draft task as a draft_task dependency."
        ),
        rerun_message=(
            "Semantic draft task must be rerun after the context migration "
            "before it can be applied."
        ),
    )
    verification_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_draft_semantic_registry_update",
        expected_schema_name="verify_draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested semantic draft "
            "verification as a verification_task dependency."
        ),
        rerun_message=(
            "Semantic draft verification must be rerun after the context "
            "migration before it can be applied."
        ),
    )
    draft_output = DraftSemanticRegistryUpdateTaskOutput.model_validate(draft_context.output)
    verification_output = VerifyDraftSemanticRegistryUpdateTaskOutput.model_validate(
        verification_context.output
    )
    verification = verification_output.verification
    if verification.outcome != "passed":
        raise ValueError("Only passed semantic registry verifications can be applied.")
    if verification.target_task_id != payload.draft_task_id:
        raise ValueError("Verification task does not target the requested semantic draft task.")

    snapshot = persist_semantic_ontology_snapshot(
        session,
        draft_output.draft.effective_registry,
        source_kind="ontology_extension_apply",
        source_task_id=task.id,
        source_task_type=task.task_type,
        activate=True,
    )
    session.commit()
    applied_registry = get_semantic_registry(session)
    apply_payload = {
        "draft_task_id": str(payload.draft_task_id),
        "verification_task_id": str(payload.verification_task_id),
        "applied_registry_version": applied_registry.registry_version,
        "applied_registry_sha256": applied_registry.sha256,
        "reason": payload.reason,
        "config_path": f"db://semantic_ontology_snapshots/{snapshot.id}",
        "applied_operations": [
            operation.model_dump(mode="json") for operation in draft_output.draft.operations
        ],
        "success_metrics": semantic_registry_apply_metrics(
            applied_registry_version=applied_registry.registry_version,
            applied_operations=[
                operation.model_dump(mode="json") for operation in draft_output.draft.operations
            ],
            verification_outcome=verification.outcome,
        ),
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="applied_semantic_registry_update",
        payload=apply_payload,
        storage_service=StorageService(),
        filename="applied_semantic_registry_update.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _apply_ontology_extension_executor(
    session: Session,
    task: AgentTask,
    payload: ApplyOntologyExtensionTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
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
    verification_context = resolve_required_dependency_task_output_context(
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

    apply_payload = apply_ontology_extension(
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
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="applied_ontology_extension",
        payload=apply_payload,
        storage_service=StorageService(),
        filename="applied_ontology_extension.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _draft_graph_promotions_executor(
    session: Session,
    task: AgentTask,
    payload: DraftGraphPromotionsTaskInput,
) -> dict:
    source_task = session.get(AgentTask, payload.source_task_id)
    if source_task is None:
        raise ValueError(f"Graph promotion source task not found: {payload.source_task_id}")
    if source_task.task_type == "build_shadow_semantic_graph":
        source_context = resolve_required_dependency_task_output_context(
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
        source_output = BuildShadowSemanticGraphTaskOutput.model_validate(source_context.output)
        draft_payload = draft_graph_promotions(
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
        source_context = resolve_required_dependency_task_output_context(
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
        source_output = TriageSemanticGraphDisagreementsTaskOutput.model_validate(
            source_context.output
        )
        draft_payload = draft_graph_promotions(
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
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_graph_promotion_draft",
        payload=draft_payload,
        storage_service=StorageService(),
        filename="semantic_graph_promotion_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _verify_draft_graph_promotions_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftGraphPromotionsTaskInput,
) -> dict:
    target_context = resolve_required_dependency_task_output_context(
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
    draft_output = DraftGraphPromotionsTaskOutput.model_validate(target_context.output)
    summary, metrics, reasons, outcome, success_metrics = verify_draft_graph_promotions(
        session,
        draft_output.draft.model_dump(mode="json"),
        min_supporting_document_count=payload.min_supporting_document_count,
        max_conflict_count=payload.max_conflict_count,
        require_current_ontology_snapshot=payload.require_current_ontology_snapshot,
    )
    verification_record = create_agent_task_verification_record(
        session,
        target_task_id=payload.target_task_id,
        verification_task_id=task.id,
        verifier_type="semantic_graph_promotion_gate",
        outcome=outcome,
        metrics=metrics,
        reasons=reasons,
        details=summary,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_graph_promotion_verification",
        payload={
            "draft": draft_output.draft.model_dump(mode="json"),
            "summary": summary,
            "success_metrics": success_metrics,
            "verification": verification_record.model_dump(mode="json"),
        },
        storage_service=StorageService(),
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


def _apply_graph_promotions_executor(
    session: Session,
    task: AgentTask,
    payload: ApplyGraphPromotionsTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
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
    verification_context = resolve_required_dependency_task_output_context(
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
    draft_output = DraftGraphPromotionsTaskOutput.model_validate(draft_context.output)
    verification_output = VerifyDraftGraphPromotionsTaskOutput.model_validate(
        verification_context.output
    )
    if verification_output.verification.outcome != "passed":
        raise ValueError("Only passed graph promotion verifications can be applied.")
    apply_payload = apply_graph_promotions(
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
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="applied_semantic_graph_snapshot",
        payload=apply_payload,
        storage_service=StorageService(),
        filename="applied_semantic_graph_snapshot.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def build_semantic_governance_action_definitions() -> dict[str, AgentTaskActionDefinition]:
    return {
        "draft_semantic_registry_update": AgentTaskActionDefinition(
            task_type="draft_semantic_registry_update",
            capability="semantic_memory",
            definition_kind="draft",
            description=(
                "Draft an additive semantic registry update from semantic triage or "
                "bootstrap candidate discovery."
            ),
            payload_model=DraftSemanticRegistryUpdateTaskInput,
            executor=_draft_semantic_registry_update_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftSemanticRegistryUpdateTaskOutput,
            output_schema_name="draft_semantic_registry_update_output",
            output_schema_version="1.0",
            input_example={
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "rationale": "Add the missing synonym surfaced by semantic triage.",
                "candidate_ids": [],
            },
            context_builder_name="draft_semantic_registry_update",
        ),
        "draft_ontology_extension": AgentTaskActionDefinition(
            task_type="draft_ontology_extension",
            capability="semantic_memory",
            definition_kind="draft",
            description=(
                "Draft an additive ontology extension from semantic triage or bootstrap discovery."
            ),
            payload_model=DraftOntologyExtensionTaskInput,
            executor=_draft_ontology_extension_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftOntologyExtensionTaskOutput,
            output_schema_name="draft_ontology_extension_output",
            output_schema_version="1.0",
            input_example={
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "rationale": "Extend the portable ontology from corpus evidence.",
                "candidate_ids": [],
            },
            context_builder_name="draft_ontology_extension",
        ),
        "draft_graph_promotions": AgentTaskActionDefinition(
            task_type="draft_graph_promotions",
            capability="semantic_memory",
            definition_kind="draft",
            description=(
                "Draft approved cross-document graph edges without mutating live graph "
                "memory."
            ),
            payload_model=DraftGraphPromotionsTaskInput,
            executor=_draft_graph_promotions_executor,
            side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
            output_model=DraftGraphPromotionsTaskOutput,
            output_schema_name="draft_graph_promotions_output",
            output_schema_version="1.0",
            input_example={
                "source_task_id": "00000000-0000-0000-0000-000000000000",
                "edge_ids": [],
                "rationale": "Promote approved cross-document graph memory.",
                "min_score": 0.45,
            },
            context_builder_name="draft_graph_promotions",
        ),
        "verify_draft_semantic_registry_update": AgentTaskActionDefinition(
            task_type="verify_draft_semantic_registry_update",
            capability="semantic_memory",
            definition_kind="verifier",
            description=(
                "Verify an additive semantic registry draft against active "
                "documents without mutating live state."
            ),
            payload_model=VerifyDraftSemanticRegistryUpdateTaskInput,
            executor=_verify_draft_semantic_registry_update_executor,
            output_model=VerifyDraftSemanticRegistryUpdateTaskOutput,
            output_schema_name="verify_draft_semantic_registry_update_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "max_regressed_document_count": 0,
                "max_failed_expectation_increase": 0,
                "min_improved_document_count": 1,
            },
            context_builder_name="verify_draft_semantic_registry_update",
        ),
        "verify_draft_ontology_extension": AgentTaskActionDefinition(
            task_type="verify_draft_ontology_extension",
            capability="semantic_memory",
            definition_kind="verifier",
            description="Verify an additive ontology extension draft against active documents.",
            payload_model=VerifyDraftOntologyExtensionTaskInput,
            executor=_verify_draft_ontology_extension_executor,
            output_model=VerifyDraftOntologyExtensionTaskOutput,
            output_schema_name="verify_draft_ontology_extension_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "max_regressed_document_count": 0,
                "max_failed_expectation_increase": 0,
                "min_improved_document_count": 1,
            },
            context_builder_name="verify_draft_ontology_extension",
        ),
        "verify_draft_graph_promotions": AgentTaskActionDefinition(
            task_type="verify_draft_graph_promotions",
            capability="semantic_memory",
            definition_kind="verifier",
            description=(
                "Verify a graph promotion draft against current ontology and "
                "traceability constraints."
            ),
            payload_model=VerifyDraftGraphPromotionsTaskInput,
            executor=_verify_draft_graph_promotions_executor,
            output_model=VerifyDraftGraphPromotionsTaskOutput,
            output_schema_name="verify_draft_graph_promotions_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "min_supporting_document_count": 2,
                "max_conflict_count": 0,
                "require_current_ontology_snapshot": True,
            },
            context_builder_name="verify_draft_graph_promotions",
        ),
        "apply_semantic_registry_update": AgentTaskActionDefinition(
            task_type="apply_semantic_registry_update",
            capability="semantic_memory",
            definition_kind="promotion",
            description="Apply a verified semantic registry update after approval.",
            payload_model=ApplySemanticRegistryUpdateTaskInput,
            executor=_apply_semantic_registry_update_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplySemanticRegistryUpdateTaskOutput,
            output_schema_name="apply_semantic_registry_update_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified registry update.",
            },
            context_builder_name="apply_semantic_registry_update",
        ),
        "apply_ontology_extension": AgentTaskActionDefinition(
            task_type="apply_ontology_extension",
            capability="semantic_memory",
            definition_kind="promotion",
            description="Apply a verified ontology extension as the new active workspace snapshot.",
            payload_model=ApplyOntologyExtensionTaskInput,
            executor=_apply_ontology_extension_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplyOntologyExtensionTaskOutput,
            output_schema_name="apply_ontology_extension_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified ontology extension.",
            },
            context_builder_name="apply_ontology_extension",
        ),
        "apply_graph_promotions": AgentTaskActionDefinition(
            task_type="apply_graph_promotions",
            capability="semantic_memory",
            definition_kind="promotion",
            description=(
                "Apply a verified semantic graph promotion draft as the new active graph snapshot."
            ),
            payload_model=ApplyGraphPromotionsTaskInput,
            executor=_apply_graph_promotions_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplyGraphPromotionsTaskOutput,
            output_schema_name="apply_graph_promotions_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified semantic graph memory snapshot.",
            },
            context_builder_name="apply_graph_promotions",
        ),
    }
