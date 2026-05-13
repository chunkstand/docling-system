from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
)
from app.schemas.agent_tasks import (
    ApplyGraphPromotionsTaskInput,
    ApplyOntologyExtensionTaskInput,
    ApplySemanticRegistryUpdateTaskInput,
    BuildDocumentFactGraphTaskInput,
    BuildShadowSemanticGraphTaskInput,
    BuildShadowSemanticGraphTaskOutput,
    DiscoverSemanticBootstrapCandidatesTaskInput,
    DiscoverSemanticBootstrapCandidatesTaskOutput,
    DraftGraphPromotionsTaskInput,
    DraftGraphPromotionsTaskOutput,
    DraftOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskOutput,
    DraftSemanticGroundedDocumentTaskInput,
    DraftSemanticRegistryUpdateTaskInput,
    DraftSemanticRegistryUpdateTaskOutput,
    EnqueueDocumentReprocessTaskInput,
    EvaluateSemanticCandidateExtractorTaskInput,
    EvaluateSemanticCandidateExtractorTaskOutput,
    EvaluateSemanticRelationExtractorTaskInput,
    EvaluateSemanticRelationExtractorTaskOutput,
    ExportSemanticSupervisionCorpusTaskInput,
    GetActiveOntologySnapshotTaskInput,
    InitializeWorkspaceOntologyTaskInput,
    LatestSemanticPassTaskInput,
    LatestSemanticPassTaskOutput,
    PrepareSemanticGenerationBriefTaskInput,
    PrepareSemanticGenerationBriefTaskOutput,
    TriageSemanticCandidateDisagreementsTaskInput,
    TriageSemanticGraphDisagreementsTaskInput,
    TriageSemanticGraphDisagreementsTaskOutput,
    TriageSemanticPassTaskInput,
    TriageSemanticPassTaskOutput,
    VerifyDraftGraphPromotionsTaskInput,
    VerifyDraftGraphPromotionsTaskOutput,
    VerifyDraftOntologyExtensionTaskInput,
    VerifyDraftOntologyExtensionTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
    VerifySemanticGroundedDocumentTaskInput,
)
from app.services.agent_actions.claim_support_actions import (
    build_claim_support_action_definitions,
)
from app.services.agent_actions.claim_support_activation import (
    require_active_replay_alert_fixture_coverage_waiver,
)
from app.services.agent_actions.claim_support_shared import (
    replay_alert_fixture_coverage_waiver_sha256,
)
from app.services.agent_actions.document_lifecycle_actions import (
    build_document_lifecycle_action_definitions,
)
from app.services.agent_actions.evaluation_actions import (
    build_evaluation_action_definitions,
)
from app.services.agent_actions.manifest import (
    AgentActionContractIssue,
    build_agent_action_index,
    build_agent_action_manifest,
    validate_agent_action_contracts,
)
from app.services.agent_actions.registry import compose_action_registries
from app.services.agent_actions.report_actions import (
    build_report_action_definitions,
)
from app.services.agent_actions.search_harness import (
    build_search_harness_action_definitions,
)
from app.services.agent_actions.semantic_analysis_actions import (
    build_semantic_analysis_action_definitions,
)
from app.services.agent_actions.semantic_drafting_actions import (
    build_semantic_drafting_action_definitions,
)
from app.services.agent_actions.semantic_verification_actions import (
    build_semantic_verification_action_definitions,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
    verify_draft_semantic_registry_update_task,
    verify_semantic_grounded_document_task,
)
from app.services.documents import (
    reprocess_document,
)
from app.services.semantic_bootstrap import discover_semantic_bootstrap_candidates
from app.services.semantic_candidates import (
    evaluate_semantic_candidate_extractor,
    export_semantic_supervision_corpus,
    triage_semantic_candidate_disagreements,
)
from app.services.semantic_facts import build_document_fact_graph
from app.services.semantic_generation import (
    draft_semantic_grounded_document,
    prepare_semantic_generation_brief,
)
from app.services.semantic_graph import (
    apply_graph_promotions,
    build_shadow_semantic_graph,
    draft_graph_promotions,
    evaluate_semantic_relation_extractor,
    triage_semantic_graph_disagreements,
    verify_draft_graph_promotions,
)
from app.services.semantic_ontology import (
    apply_ontology_extension,
    draft_ontology_extension,
    draft_ontology_extension_from_bootstrap_report,
    get_active_ontology_snapshot_payload,
    initialize_workspace_ontology,
    verify_draft_ontology_extension,
)
from app.services.semantic_orchestration import (
    build_semantic_success_metrics,
    draft_semantic_registry_update,
    draft_semantic_registry_update_from_bootstrap_report,
    semantic_registry_apply_metrics,
    triage_semantic_pass,
)
from app.services.semantic_registry import get_semantic_registry, persist_semantic_ontology_snapshot
from app.services.semantics import get_active_semantic_pass_detail
from app.services.storage import StorageService

_replay_alert_fixture_coverage_waiver_sha256 = replay_alert_fixture_coverage_waiver_sha256
_require_active_replay_alert_fixture_coverage_waiver = (
    require_active_replay_alert_fixture_coverage_waiver
)


def _latest_semantic_pass_executor(
    session: Session, _task: AgentTask, payload: LatestSemanticPassTaskInput
) -> dict:
    response = get_active_semantic_pass_detail(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "semantic_pass": jsonable_encoder(response),
        "success_metrics": build_semantic_success_metrics(response),
    }


def _initialize_workspace_ontology_executor(
    session: Session, task: AgentTask, _payload: InitializeWorkspaceOntologyTaskInput
) -> dict:
    result = initialize_workspace_ontology(session)
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="active_ontology_snapshot",
        payload=result,
        storage_service=StorageService(),
        filename="active_ontology_snapshot.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _get_active_ontology_snapshot_executor(
    session: Session, _task: AgentTask, _payload: GetActiveOntologySnapshotTaskInput
) -> dict:
    return get_active_ontology_snapshot_payload(session)


def _discover_semantic_bootstrap_candidates_executor(
    session: Session,
    task: AgentTask,
    payload: DiscoverSemanticBootstrapCandidatesTaskInput,
) -> dict:
    report_payload = discover_semantic_bootstrap_candidates(
        session,
        document_ids=list(payload.document_ids),
        max_candidates=payload.max_candidates,
        min_document_count=payload.min_document_count,
        min_source_count=payload.min_source_count,
        min_phrase_tokens=payload.min_phrase_tokens,
        max_phrase_tokens=payload.max_phrase_tokens,
        exclude_existing_registry_terms=payload.exclude_existing_registry_terms,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_bootstrap_candidate_report",
        payload=report_payload,
        storage_service=StorageService(),
        filename="semantic_bootstrap_candidate_report.json",
    )
    return {
        "report": report_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _export_semantic_supervision_corpus_executor(
    session: Session,
    task: AgentTask,
    payload: ExportSemanticSupervisionCorpusTaskInput,
) -> dict:
    storage_service = StorageService()
    jsonl_path = storage_service.get_agent_task_dir(task.id) / "semantic_supervision_corpus.jsonl"
    corpus_payload = export_semantic_supervision_corpus(
        session,
        document_ids=list(payload.document_ids),
        reviewed_only=payload.reviewed_only,
        include_generation_verifications=payload.include_generation_verifications,
        output_path=jsonl_path,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_supervision_corpus",
        payload=corpus_payload,
        storage_service=storage_service,
        filename="semantic_supervision_corpus.json",
    )
    return {
        "corpus": corpus_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _evaluate_semantic_candidate_extractor_executor(
    session: Session,
    task: AgentTask,
    payload: EvaluateSemanticCandidateExtractorTaskInput,
) -> dict:
    evaluation_payload = evaluate_semantic_candidate_extractor(
        session,
        document_ids=list(payload.document_ids),
        baseline_extractor_name=payload.baseline_extractor_name,
        candidate_extractor_name=payload.candidate_extractor_name,
        score_threshold=payload.score_threshold,
        max_candidates_per_source=payload.max_candidates_per_source,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_candidate_evaluation",
        payload=evaluation_payload,
        storage_service=StorageService(),
        filename="semantic_candidate_evaluation.json",
    )
    return {
        **evaluation_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _prepare_semantic_generation_brief_executor(
    session: Session,
    task: AgentTask,
    payload: PrepareSemanticGenerationBriefTaskInput,
) -> dict:
    brief_payload = prepare_semantic_generation_brief(
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
        artifact_kind="semantic_generation_brief",
        payload=brief_payload,
        storage_service=StorageService(),
        filename="semantic_generation_brief.json",
    )
    return {
        "brief": brief_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _draft_semantic_grounded_document_executor(
    session: Session,
    task: AgentTask,
    payload: DraftSemanticGroundedDocumentTaskInput,
) -> dict:
    brief_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_semantic_generation_brief",
        expected_schema_name="prepare_semantic_generation_brief_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Grounded document drafts must declare the requested brief task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target semantic generation brief must be rerun after the context "
            "migration before drafting."
        ),
    )
    brief_output = PrepareSemanticGenerationBriefTaskOutput.model_validate(brief_context.output)
    draft_payload = draft_semantic_grounded_document(
        brief_output.brief.model_dump(mode="json"),
        brief_task_id=payload.target_task_id,
    )

    storage_service = StorageService()
    markdown_path = storage_service.get_agent_task_dir(task.id) / "semantic_grounded_document.md"
    markdown_path.write_text(draft_payload["markdown"])
    draft_payload["markdown_path"] = str(markdown_path)

    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_grounded_document_draft",
        payload=draft_payload,
        storage_service=storage_service,
        filename="semantic_grounded_document_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _verify_semantic_grounded_document_executor(
    session: Session,
    task: AgentTask,
    payload: VerifySemanticGroundedDocumentTaskInput,
) -> dict:
    result = verify_semantic_grounded_document_task(session, task, payload)
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_grounded_document_verification",
        payload=result,
        storage_service=StorageService(),
        filename="semantic_grounded_document_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _enqueue_document_reprocess_executor(
    session: Session,
    _task: AgentTask,
    payload: EnqueueDocumentReprocessTaskInput,
) -> dict:
    response = reprocess_document(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "reason": payload.reason,
        "reprocess": jsonable_encoder(response),
    }


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


def _build_document_fact_graph_executor(
    session: Session,
    task: AgentTask,
    payload: BuildDocumentFactGraphTaskInput,
) -> dict:
    result = build_document_fact_graph(
        session,
        document_id=payload.document_id,
        minimum_review_status=payload.minimum_review_status,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_fact_graph",
        payload=result,
        storage_service=StorageService(),
        filename="semantic_fact_graph.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _build_shadow_semantic_graph_executor(
    session: Session,
    task: AgentTask,
    payload: BuildShadowSemanticGraphTaskInput,
) -> dict:
    shadow_graph = build_shadow_semantic_graph(
        session,
        document_ids=list(payload.document_ids),
        relation_extractor_name=payload.relation_extractor_name,
        minimum_review_status=payload.minimum_review_status,
        min_shared_documents=payload.min_shared_documents,
        score_threshold=payload.score_threshold,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="shadow_semantic_graph",
        payload=shadow_graph,
        storage_service=StorageService(),
        filename="shadow_semantic_graph.json",
    )
    return {
        "shadow_graph": shadow_graph,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _evaluate_semantic_relation_extractor_executor(
    session: Session,
    task: AgentTask,
    payload: EvaluateSemanticRelationExtractorTaskInput,
) -> dict:
    evaluation_payload = evaluate_semantic_relation_extractor(
        session,
        document_ids=list(payload.document_ids),
        baseline_extractor_name=payload.baseline_extractor_name,
        candidate_extractor_name=payload.candidate_extractor_name,
        minimum_review_status=payload.minimum_review_status,
        baseline_min_shared_documents=payload.baseline_min_shared_documents,
        candidate_score_threshold=payload.candidate_score_threshold,
        expected_min_shared_documents=payload.expected_min_shared_documents,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_relation_evaluation",
        payload=evaluation_payload,
        storage_service=StorageService(),
        filename="semantic_relation_evaluation.json",
    )
    return {
        **evaluation_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _triage_semantic_pass_executor(
    session: Session,
    task: AgentTask,
    payload: TriageSemanticPassTaskInput,
) -> dict:
    target_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="get_latest_semantic_pass",
        expected_schema_name="get_latest_semantic_pass_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic triage must declare the requested semantic-pass task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target semantic-pass task must be rerun after the context migration before triage."
        ),
    )
    semantic_output = LatestSemanticPassTaskOutput.model_validate(target_context.output)
    triage_output = triage_semantic_pass(
        semantic_output.semantic_pass,
        low_evidence_threshold=payload.low_evidence_threshold,
    )
    verification_record = create_agent_task_verification_record(
        session,
        target_task_id=payload.target_task_id,
        verification_task_id=task.id,
        verifier_type="semantic_gap_gate",
        outcome=triage_output.verification_outcome,
        metrics=triage_output.verification_metrics,
        reasons=triage_output.verification_reasons,
        details=triage_output.verification_details,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_gap_report",
        payload=triage_output.gap_report,
        storage_service=StorageService(),
        filename="semantic_gap_report.json",
    )
    return {
        "document_id": str(semantic_output.document_id),
        "run_id": str(semantic_output.semantic_pass.run_id),
        "semantic_pass_id": str(semantic_output.semantic_pass.semantic_pass_id),
        "registry_version": semantic_output.semantic_pass.registry_version,
        "evaluation_fixture_name": semantic_output.semantic_pass.evaluation_fixture_name,
        "evaluation_status": semantic_output.semantic_pass.evaluation_status,
        "gap_report": triage_output.gap_report,
        "verification": verification_record.model_dump(mode="json"),
        "recommendation": triage_output.recommendation,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _triage_semantic_graph_disagreements_executor(
    session: Session,
    task: AgentTask,
    payload: TriageSemanticGraphDisagreementsTaskInput,
) -> dict:
    target_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="evaluate_semantic_relation_extractor",
        expected_schema_name="evaluate_semantic_relation_extractor_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Graph disagreement triage must declare the requested graph evaluation "
            "task as a target_task dependency."
        ),
        rerun_message=(
            "Graph evaluation task must be rerun after the context migration before triage."
        ),
    )
    evaluation_output = EvaluateSemanticRelationExtractorTaskOutput.model_validate(
        target_context.output
    )
    disagreement_report = triage_semantic_graph_disagreements(
        evaluation_output.model_dump(mode="json"),
        min_score=payload.min_score,
        expected_only=payload.expected_only,
    )
    verification_record = create_agent_task_verification_record(
        session,
        target_task_id=task.id,
        verification_task_id=task.id,
        verifier_type="semantic_graph_shadow_gate",
        outcome="passed",
        metrics={"issue_count": disagreement_report["issue_count"]},
        reasons=[],
        details={
            "evaluation_task_id": str(payload.target_task_id),
            "issue_count": disagreement_report["issue_count"],
        },
    )
    recommendation = (
        {
            "next_action": "draft_graph_promotions",
            "priority": "high",
        }
        if disagreement_report["issue_count"] > 0
        else {
            "next_action": "observe_only",
            "priority": "low",
        }
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_graph_disagreement_report",
        payload={
            "evaluation_task_id": str(payload.target_task_id),
            "disagreement_report": disagreement_report,
            "verification": verification_record.model_dump(mode="json"),
            "recommendation": recommendation,
        },
        storage_service=StorageService(),
        filename="semantic_graph_disagreement_report.json",
    )
    return {
        "evaluation_task_id": str(payload.target_task_id),
        "disagreement_report": disagreement_report,
        "verification": verification_record.model_dump(mode="json"),
        "recommendation": recommendation,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _triage_semantic_candidate_disagreements_executor(
    session: Session,
    task: AgentTask,
    payload: TriageSemanticCandidateDisagreementsTaskInput,
) -> dict:
    target_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="evaluate_semantic_candidate_extractor",
        expected_schema_name="evaluate_semantic_candidate_extractor_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Candidate disagreement triage must declare the requested evaluation "
            "task as a target_task dependency."
        ),
        rerun_message=(
            "Candidate evaluation task must be rerun after the context migration before triage."
        ),
    )
    evaluation_output = EvaluateSemanticCandidateExtractorTaskOutput.model_validate(
        target_context.output
    )
    disagreement_report, verification_outcome, recommendation = (
        triage_semantic_candidate_disagreements(
            evaluation_output.model_dump(mode="json"),
            min_score=payload.min_score,
            include_expected_only=payload.include_expected_only,
        )
    )
    verification_record = create_agent_task_verification_record(
        session,
        target_task_id=task.id,
        verification_task_id=task.id,
        verifier_type="semantic_candidate_shadow_gate",
        outcome=verification_outcome["outcome"],
        metrics=verification_outcome["metrics"],
        reasons=verification_outcome["reasons"],
        details=verification_outcome["details"],
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="semantic_candidate_disagreement_report",
        payload={
            "evaluation_task_id": str(payload.target_task_id),
            "disagreement_report": disagreement_report,
            "verification": verification_record.model_dump(mode="json"),
            "recommendation": recommendation,
        },
        storage_service=StorageService(),
        filename="semantic_candidate_disagreement_report.json",
    )
    return {
        "evaluation_task_id": str(payload.target_task_id),
        "disagreement_report": disagreement_report,
        "verification": verification_record.model_dump(mode="json"),
        "recommendation": recommendation,
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

_SEARCH_HARNESS_ACTION_REGISTRY = build_search_harness_action_definitions(
)

_EVALUATION_ACTION_REGISTRY = build_evaluation_action_definitions()
_SEMANTIC_ANALYSIS_ACTION_REGISTRY = build_semantic_analysis_action_definitions(
    latest_semantic_pass_executor=_latest_semantic_pass_executor,
    initialize_workspace_ontology_executor=_initialize_workspace_ontology_executor,
    get_active_ontology_snapshot_executor=_get_active_ontology_snapshot_executor,
    discover_semantic_bootstrap_candidates_executor=(
        _discover_semantic_bootstrap_candidates_executor
    ),
    export_semantic_supervision_corpus_executor=(
        _export_semantic_supervision_corpus_executor
    ),
    evaluate_semantic_candidate_extractor_executor=(
        _evaluate_semantic_candidate_extractor_executor
    ),
    build_shadow_semantic_graph_executor=_build_shadow_semantic_graph_executor,
    evaluate_semantic_relation_extractor_executor=(
        _evaluate_semantic_relation_extractor_executor
    ),
    build_document_fact_graph_executor=_build_document_fact_graph_executor,
)
_REPORT_ACTION_REGISTRY = build_report_action_definitions()
_CLAIM_SUPPORT_ACTION_REGISTRY = build_claim_support_action_definitions()
_SEMANTIC_DRAFTING_ACTION_REGISTRY = build_semantic_drafting_action_definitions(
    prepare_semantic_generation_brief_executor=(
        _prepare_semantic_generation_brief_executor
    ),
    draft_semantic_registry_update_executor=_draft_semantic_registry_update_executor,
    draft_ontology_extension_executor=_draft_ontology_extension_executor,
    draft_graph_promotions_executor=_draft_graph_promotions_executor,
    draft_semantic_grounded_document_executor=(
        _draft_semantic_grounded_document_executor
    ),
)
_SEMANTIC_VERIFICATION_ACTION_REGISTRY = build_semantic_verification_action_definitions(
    verify_draft_semantic_registry_update_executor=(
        _verify_draft_semantic_registry_update_executor
    ),
    verify_draft_ontology_extension_executor=_verify_draft_ontology_extension_executor,
    verify_draft_graph_promotions_executor=_verify_draft_graph_promotions_executor,
    verify_semantic_grounded_document_executor=(
        _verify_semantic_grounded_document_executor
    ),
    triage_semantic_pass_executor=_triage_semantic_pass_executor,
    triage_semantic_candidate_disagreements_executor=(
        _triage_semantic_candidate_disagreements_executor
    ),
    triage_semantic_graph_disagreements_executor=(
        _triage_semantic_graph_disagreements_executor
    ),
    apply_semantic_registry_update_executor=_apply_semantic_registry_update_executor,
    apply_ontology_extension_executor=_apply_ontology_extension_executor,
    apply_graph_promotions_executor=_apply_graph_promotions_executor,
)
_DOCUMENT_LIFECYCLE_ACTION_REGISTRY = build_document_lifecycle_action_definitions(
    enqueue_document_reprocess_executor=_enqueue_document_reprocess_executor
)


_ACTION_REGISTRY: dict[str, AgentTaskActionDefinition] = compose_action_registries(
    _EVALUATION_ACTION_REGISTRY,
    _SEMANTIC_ANALYSIS_ACTION_REGISTRY,
    _REPORT_ACTION_REGISTRY,
    _CLAIM_SUPPORT_ACTION_REGISTRY,
    _SEARCH_HARNESS_ACTION_REGISTRY,
    _SEMANTIC_DRAFTING_ACTION_REGISTRY,
    _SEMANTIC_VERIFICATION_ACTION_REGISTRY,
    _DOCUMENT_LIFECYCLE_ACTION_REGISTRY,
)


def list_agent_task_actions() -> list[AgentTaskActionDefinition]:
    return list(_ACTION_REGISTRY.values())


def build_agent_task_action_manifest() -> list[dict[str, object]]:
    return build_agent_action_manifest(list_agent_task_actions())


def build_agent_task_action_index() -> dict[str, object]:
    return build_agent_action_index(list_agent_task_actions())


def validate_agent_task_action_contracts() -> list[AgentActionContractIssue]:
    from app.services.agent_task_context import list_agent_task_context_builder_names

    issues = validate_agent_action_contracts(
        list_agent_task_actions(),
        registry_keys=set(_ACTION_REGISTRY),
        context_builder_names=list_agent_task_context_builder_names(),
    )
    for registry_key, action in _ACTION_REGISTRY.items():
        if registry_key != action.task_type:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="task_type",
                    message=f"registry key '{registry_key}' must match task_type",
                )
            )
    return issues


def get_agent_task_action(task_type: str) -> AgentTaskActionDefinition:
    try:
        return _ACTION_REGISTRY[task_type]
    except KeyError as exc:
        available = ", ".join(sorted(_ACTION_REGISTRY))
        raise ValueError(f"Unknown agent task type '{task_type}'. Available: {available}") from exc


def validate_agent_task_input(task_type: str, raw_input: dict) -> BaseModel:
    action = get_agent_task_action(task_type)
    return action.payload_model.model_validate(raw_input or {})


def validate_agent_task_output(task_type: str, raw_output: dict) -> dict:
    action = get_agent_task_action(task_type)
    if action.output_model is None:
        return raw_output or {}
    validated_output = action.output_model.model_validate(raw_output or {})
    return validated_output.model_dump(mode="json", exclude_none=True)


def execute_agent_task_action(session: Session, task: AgentTask) -> dict:
    action = get_agent_task_action(task.task_type)
    payload = action.payload_model.model_validate(task.input_json or {})
    result = action.executor(session, task, payload)
    validated_output = validate_agent_task_output(task.task_type, result)
    return {
        "task_type": task.task_type,
        "definition_kind": action.definition_kind,
        "side_effect_level": action.side_effect_level,
        "requires_approval": action.requires_approval,
        "output_schema_name": action.output_schema_name,
        "output_schema_version": action.output_schema_version,
        "payload": validated_output,
    }
