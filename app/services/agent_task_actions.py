from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    ApplyGraphPromotionsTaskInput,
    ApplyGraphPromotionsTaskOutput,
    ApplyHarnessConfigUpdateTaskInput,
    ApplyHarnessConfigUpdateTaskOutput,
    ApplyOntologyExtensionTaskInput,
    ApplyOntologyExtensionTaskOutput,
    ApplySemanticRegistryUpdateTaskInput,
    ApplySemanticRegistryUpdateTaskOutput,
    BuildDocumentFactGraphTaskInput,
    BuildDocumentFactGraphTaskOutput,
    BuildShadowSemanticGraphTaskInput,
    BuildShadowSemanticGraphTaskOutput,
    DiscoverSemanticBootstrapCandidatesTaskInput,
    DiscoverSemanticBootstrapCandidatesTaskOutput,
    DraftGraphPromotionsTaskInput,
    DraftGraphPromotionsTaskOutput,
    DraftHarnessConfigUpdateTaskInput,
    DraftHarnessConfigUpdateTaskOutput,
    DraftOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskOutput,
    DraftSemanticGroundedDocumentTaskInput,
    DraftSemanticGroundedDocumentTaskOutput,
    DraftSemanticRegistryUpdateTaskInput,
    DraftSemanticRegistryUpdateTaskOutput,
    EnqueueDocumentReprocessTaskInput,
    EnqueueDocumentReprocessTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    EvaluateSemanticCandidateExtractorTaskInput,
    EvaluateSemanticCandidateExtractorTaskOutput,
    EvaluateSemanticRelationExtractorTaskInput,
    EvaluateSemanticRelationExtractorTaskOutput,
    ExportSemanticSupervisionCorpusTaskInput,
    ExportSemanticSupervisionCorpusTaskOutput,
    GetActiveOntologySnapshotTaskInput,
    GetActiveOntologySnapshotTaskOutput,
    InitializeWorkspaceOntologyTaskInput,
    InitializeWorkspaceOntologyTaskOutput,
    LatestEvaluationTaskInput,
    LatestEvaluationTaskOutput,
    LatestSemanticPassTaskInput,
    LatestSemanticPassTaskOutput,
    PrepareSemanticGenerationBriefTaskInput,
    PrepareSemanticGenerationBriefTaskOutput,
    QualityEvalCandidatesTaskInput,
    QualityEvalCandidatesTaskOutput,
    ReplaySearchRequestTaskInput,
    ReplaySearchRequestTaskOutput,
    RunSearchReplaySuiteTaskOutput,
    TriageReplayRegressionTaskInput,
    TriageReplayRegressionTaskOutput,
    TriageSemanticCandidateDisagreementsTaskInput,
    TriageSemanticCandidateDisagreementsTaskOutput,
    TriageSemanticGraphDisagreementsTaskInput,
    TriageSemanticGraphDisagreementsTaskOutput,
    TriageSemanticPassTaskInput,
    TriageSemanticPassTaskOutput,
    VerifyDraftGraphPromotionsTaskInput,
    VerifyDraftGraphPromotionsTaskOutput,
    VerifyDraftHarnessConfigTaskInput,
    VerifyDraftHarnessConfigTaskOutput,
    VerifyDraftOntologyExtensionTaskInput,
    VerifyDraftOntologyExtensionTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
    VerifySearchHarnessEvaluationTaskInput,
    VerifySearchHarnessEvaluationTaskOutput,
    VerifySemanticGroundedDocumentTaskInput,
    VerifySemanticGroundedDocumentTaskOutput,
)
from app.schemas.search import SearchHarnessEvaluationRequest, SearchReplayRunRequest
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    _build_apply_graph_promotions_context,
    _build_apply_harness_config_update_context,
    _build_apply_ontology_extension_context,
    _build_apply_semantic_registry_update_context,
    _build_build_document_fact_graph_context,
    _build_build_shadow_semantic_graph_context,
    _build_discover_semantic_bootstrap_candidates_context,
    _build_draft_graph_promotions_context,
    _build_draft_harness_config_context,
    _build_draft_ontology_extension_context,
    _build_draft_semantic_grounded_document_context,
    _build_draft_semantic_registry_update_context,
    _build_evaluate_search_harness_context,
    _build_evaluate_semantic_candidate_extractor_context,
    _build_evaluate_semantic_relation_extractor_context,
    _build_export_semantic_supervision_corpus_context,
    _build_generic_task_context,
    _build_get_active_ontology_snapshot_context,
    _build_initialize_workspace_ontology_context,
    _build_latest_semantic_pass_context,
    _build_prepare_semantic_generation_brief_context,
    _build_triage_replay_regression_context,
    _build_triage_semantic_candidate_disagreements_context,
    _build_triage_semantic_graph_disagreements_context,
    _build_triage_semantic_pass_context,
    _build_verify_draft_graph_promotions_context,
    _build_verify_draft_harness_config_context,
    _build_verify_draft_ontology_extension_context,
    _build_verify_draft_semantic_registry_update_context,
    _build_verify_search_harness_evaluation_context,
    _build_verify_semantic_grounded_document_context,
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
    verify_draft_harness_config_task,
    verify_draft_semantic_registry_update_task,
    verify_search_harness_evaluation_task,
    verify_semantic_grounded_document_task,
)
from app.services.documents import (
    get_latest_document_evaluation_detail,
    reprocess_document,
)
from app.services.quality import list_quality_eval_candidates
from app.services.search import get_search_harness, list_search_harnesses
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_harness_overrides import upsert_applied_search_harness_override
from app.services.search_history import replay_search_request
from app.services.search_legibility import get_search_request_explanation
from app.services.search_release_gate import evaluate_search_harness_release_gate
from app.services.search_replays import (
    compare_search_replay_runs,
    get_search_replay_run_detail,
    run_search_replay_suite,
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

evaluate_search_harness_verification = evaluate_search_harness_release_gate


@dataclass(frozen=True)
class AgentTaskActionDefinition:
    task_type: str
    definition_kind: str
    description: str
    payload_model: type[BaseModel]
    executor: Callable[[Session, AgentTask, BaseModel], dict]
    side_effect_level: str = AgentTaskSideEffectLevel.READ_ONLY.value
    requires_approval: bool = False
    output_model: type[BaseModel] | None = None
    output_schema_name: str | None = None
    output_schema_version: str | None = None
    input_example: dict[str, Any] | None = None
    context_builder: Callable[..., object] | None = None


def _latest_evaluation_executor(
    session: Session, _task: AgentTask, payload: LatestEvaluationTaskInput
) -> dict:
    response = get_latest_document_evaluation_detail(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "evaluation": jsonable_encoder(response),
    }


def _quality_eval_candidates_executor(
    session: Session, _task: AgentTask, payload: QualityEvalCandidatesTaskInput
) -> dict:
    response = list_quality_eval_candidates(
        session,
        limit=payload.limit,
        include_resolved=payload.include_resolved,
    )
    return {
        "limit": payload.limit,
        "include_resolved": payload.include_resolved,
        "candidate_count": len(response),
        "candidates": jsonable_encoder(response),
    }


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


def _replay_search_request_executor(
    session: Session, _task: AgentTask, payload: ReplaySearchRequestTaskInput
) -> dict:
    response = replay_search_request(session, payload.search_request_id)
    return {
        "search_request_id": str(payload.search_request_id),
        "replay": jsonable_encoder(response),
    }


def _run_search_replay_suite_executor(
    session: Session, _task: AgentTask, payload: SearchReplayRunRequest
) -> dict:
    response = run_search_replay_suite(session, payload)
    return {
        "source_type": payload.source_type,
        "harness_name": payload.harness_name,
        "replay_run": jsonable_encoder(response),
    }


def _evaluate_search_harness_executor(
    session: Session, _task: AgentTask, payload: SearchHarnessEvaluationRequest
) -> dict:
    response = evaluate_search_harness(session, payload)
    return {
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "evaluation": jsonable_encoder(response),
    }


def _verify_search_harness_evaluation_executor(
    session: Session,
    task: AgentTask,
    payload: VerifySearchHarnessEvaluationTaskInput,
) -> dict:
    return verify_search_harness_evaluation_task(session, task, payload)


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


def _draft_harness_config_update_executor(
    session: Session,
    task: AgentTask,
    payload: DraftHarnessConfigUpdateTaskInput,
) -> dict:
    existing_harness_names = {row.name for row in list_search_harnesses()}
    if payload.draft_harness_name in existing_harness_names:
        msg = f"Draft harness name already exists: {payload.draft_harness_name}"
        raise ValueError(msg)

    override_spec = {
        "base_harness_name": payload.base_harness_name,
        "retrieval_profile_overrides": payload.retrieval_profile_overrides,
        "reranker_overrides": payload.reranker_overrides,
        "override_type": "draft_harness_config_update",
        "override_source": "task_draft",
        "draft_task_id": str(task.id),
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "rationale": payload.rationale,
    }
    effective_harness = get_search_harness(
        payload.draft_harness_name,
        {payload.draft_harness_name: override_spec},
    )
    source_task = session.get(AgentTask, payload.source_task_id) if payload.source_task_id else None
    draft_payload = {
        "draft_harness_name": payload.draft_harness_name,
        "base_harness_name": payload.base_harness_name,
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "source_task_type": source_task.task_type if source_task is not None else None,
        "rationale": payload.rationale,
        "override_spec": override_spec,
        "effective_harness_config": effective_harness.config_snapshot,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft",
        payload=draft_payload,
        storage_service=StorageService(),
        filename="harness_config_draft.json",
    )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _verify_draft_harness_config_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyDraftHarnessConfigTaskInput,
) -> dict:
    result = verify_draft_harness_config_task(session, task, payload)
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="harness_config_draft_verification",
        payload=result,
        storage_service=StorageService(),
        filename="harness_config_draft_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _build_harness_follow_up_summary(
    *,
    verification_evaluation: dict,
    follow_up_evaluation: dict,
) -> dict:
    before_regressed = int(verification_evaluation.get("total_regressed_count") or 0)
    after_regressed = int(follow_up_evaluation.get("total_regressed_count") or 0)
    before_improved = int(verification_evaluation.get("total_improved_count") or 0)
    after_improved = int(follow_up_evaluation.get("total_improved_count") or 0)
    before_shared = int(verification_evaluation.get("total_shared_query_count") or 0)
    after_shared = int(follow_up_evaluation.get("total_shared_query_count") or 0)
    keep_recommendation = after_regressed <= before_regressed
    return {
        "schema_name": "search_harness_follow_up_evidence",
        "schema_version": "1.0",
        "before": {
            "total_shared_query_count": before_shared,
            "total_improved_count": before_improved,
            "total_regressed_count": before_regressed,
        },
        "after": {
            "total_shared_query_count": after_shared,
            "total_improved_count": after_improved,
            "total_regressed_count": after_regressed,
        },
        "delta": {
            "shared_query_count": after_shared - before_shared,
            "improved_count": after_improved - before_improved,
            "regressed_count": after_regressed - before_regressed,
        },
        "recommendation": "keep_override" if keep_recommendation else "rollback_or_revise",
        "summary": (
            "Follow-up replay/evaluation did not increase regressions."
            if keep_recommendation
            else "Follow-up replay/evaluation increased regressions; review the override."
        ),
    }


def _apply_harness_config_update_executor(
    session: Session,
    task: AgentTask,
    payload: ApplyHarnessConfigUpdateTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_harness_config_update",
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested draft task as a draft_task dependency."
        ),
        rerun_message=(
            "Draft task must be rerun after the context migration before it can be applied."
        ),
    )
    verification_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_draft_harness_config",
        expected_schema_name="verify_draft_harness_config_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested verification task as a "
            "verification_task dependency."
        ),
        rerun_message=(
            "Verification task must be rerun after the context migration before it can be applied."
        ),
    )

    draft_output = DraftHarnessConfigUpdateTaskOutput.model_validate(draft_context.output)
    verification_output = VerifyDraftHarnessConfigTaskOutput.model_validate(
        verification_context.output
    )

    verification = verification_output.verification
    if verification.outcome != "passed":
        msg = "Only passed draft harness verifications can be applied."
        raise ValueError(msg)
    if (
        verification_output.comprehension_gate is not None
        and not verification_output.comprehension_gate.comprehension_passed
    ):
        msg = "Only comprehensible draft harness verifications can be applied."
        raise ValueError(msg)
    if verification.target_task_id != payload.draft_task_id:
        msg = "Verification task does not target the requested draft task."
        raise ValueError(msg)

    draft_payload = draft_output.draft
    draft_harness_name = draft_payload.draft_harness_name
    override_spec = draft_payload.override_spec.model_dump(mode="json")
    if verification_output.draft.draft_harness_name != draft_harness_name:
        msg = "Verification task does not match the requested draft harness name."
        raise ValueError(msg)

    existing_harness_names = {row.name for row in list_search_harnesses()}
    if draft_harness_name in existing_harness_names:
        msg = f"Search harness name already exists: {draft_harness_name}"
        raise ValueError(msg)

    override_spec.update(
        {
            "override_type": "applied_harness_config_update",
            "override_source": "applied_override",
            "verification_task_id": str(payload.verification_task_id),
            "applied_by": task.approved_by,
            "applied_at": task.approved_at.isoformat() if task.approved_at else None,
        }
    )
    config_path = upsert_applied_search_harness_override(draft_harness_name, override_spec)
    effective_harness = get_search_harness(draft_harness_name)
    follow_up_plan = verification_output.follow_up_plan or {}
    follow_up_evaluation_payload: dict = {}
    follow_up_summary_payload: dict = {}
    follow_up_artifact = None
    if follow_up_plan:
        follow_up_evaluation = evaluate_search_harness(
            session,
            SearchHarnessEvaluationRequest(
                candidate_harness_name=draft_harness_name,
                baseline_harness_name=follow_up_plan.get("baseline_harness_name")
                or draft_payload.base_harness_name,
                source_types=follow_up_plan.get("source_types")
                or [
                    "evaluation_queries",
                    "feedback",
                    "live_search_gaps",
                    "cross_document_prose_regressions",
                ],
                limit=int(follow_up_plan.get("limit") or 25),
            ),
        )
        follow_up_evaluation_payload = jsonable_encoder(follow_up_evaluation)
        follow_up_summary_payload = _build_harness_follow_up_summary(
            verification_evaluation=verification_output.evaluation,
            follow_up_evaluation=follow_up_evaluation_payload,
        )
        follow_up_artifact = create_agent_task_artifact(
            session,
            task_id=task.id,
            artifact_kind="follow_up_evaluation_summary",
            payload={
                **follow_up_summary_payload,
                "follow_up_plan": follow_up_plan,
                "follow_up_evaluation": follow_up_evaluation_payload,
            },
            storage_service=StorageService(),
            filename="follow_up_evaluation_summary.json",
        )
    apply_payload = {
        "draft_task_id": str(payload.draft_task_id),
        "verification_task_id": str(payload.verification_task_id),
        "draft_harness_name": draft_harness_name,
        "reason": payload.reason,
        "config_path": str(config_path),
        "applied_override": override_spec,
        "effective_harness_config": effective_harness.config_snapshot,
        "follow_up_plan": follow_up_plan,
        "follow_up_evaluation": follow_up_evaluation_payload,
        "follow_up_summary": follow_up_summary_payload,
        "follow_up_artifact_id": str(follow_up_artifact.id) if follow_up_artifact else None,
        "follow_up_artifact_kind": (
            follow_up_artifact.artifact_kind if follow_up_artifact else None
        ),
        "follow_up_artifact_path": follow_up_artifact.storage_path if follow_up_artifact else None,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="applied_harness_config_update",
        payload=apply_payload,
        storage_service=StorageService(),
        filename="applied_harness_config_update.json",
    )
    return {
        **apply_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
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


def _recommend_triage_next_action(
    *,
    total_shared_query_count: int,
    total_regressed_count: int,
    total_improved_count: int,
    reason_count: int,
    quality_candidate_count: int,
) -> tuple[str, str]:
    if total_shared_query_count == 0:
        return "collect_more_evidence", "low"
    if reason_count > 0 or total_regressed_count > 0:
        return "keep_baseline_and_investigate", "high"
    if total_improved_count > 0:
        return "candidate_ready_for_review", "medium"
    if quality_candidate_count > 0:
        return "investigate_unresolved_gaps", "medium"
    return "no_change", "low"


def _replay_query_key(row) -> tuple[str, str, str]:
    import json

    return row.query_text, row.mode, json.dumps(row.filters or {}, sort_keys=True)


def _safe_search_request_explanation(session: Session, search_request_id) -> dict | None:
    if search_request_id is None or not hasattr(session, "execute"):
        return None
    try:
        explanation = get_search_request_explanation(session, search_request_id)
    except Exception:
        return None
    return explanation.model_dump(mode="json")


def _repair_case_examples(
    session: Session,
    evaluation,
    *,
    max_examples: int = 5,
) -> tuple[list[dict], list[str], list[str]]:
    if not hasattr(session, "execute"):
        return [], [], []

    examples: list[dict] = []
    affected_result_types: set[str] = set()
    diagnosis_categories: list[str] = []
    for source in evaluation.sources:
        try:
            comparison = compare_search_replay_runs(
                session,
                source.baseline_replay_run_id,
                source.candidate_replay_run_id,
            )
            baseline_detail = get_search_replay_run_detail(session, source.baseline_replay_run_id)
            candidate_detail = get_search_replay_run_detail(session, source.candidate_replay_run_id)
        except Exception:
            continue

        baseline_rows = {_replay_query_key(row): row for row in baseline_detail.query_results}
        candidate_rows = {_replay_query_key(row): row for row in candidate_detail.query_results}
        for changed_query in comparison.changed_queries:
            key = _replay_query_key(changed_query)
            baseline_row = baseline_rows.get(key)
            candidate_row = candidate_rows.get(key)
            if baseline_row is None or candidate_row is None:
                continue

            baseline_explanation = _safe_search_request_explanation(
                session,
                baseline_row.replay_search_request_id,
            )
            candidate_explanation = _safe_search_request_explanation(
                session,
                candidate_row.replay_search_request_id,
            )
            for explanation in (baseline_explanation, candidate_explanation):
                if explanation is None:
                    continue
                diagnosis = explanation.get("diagnosis") or {}
                category = diagnosis.get("category")
                if category and category not in diagnosis_categories:
                    diagnosis_categories.append(category)
                for result in explanation.get("top_result_snapshot") or []:
                    result_type = result.get("result_type")
                    if result_type:
                        affected_result_types.add(result_type)

            examples.append(
                {
                    "source_type": source.source_type,
                    "query_text": changed_query.query_text,
                    "mode": changed_query.mode,
                    "filters": changed_query.filters,
                    "baseline_passed": changed_query.baseline_passed,
                    "candidate_passed": changed_query.candidate_passed,
                    "baseline_result_count": changed_query.baseline_result_count,
                    "candidate_result_count": changed_query.candidate_result_count,
                    "baseline_search_request_id": (
                        str(baseline_row.replay_search_request_id)
                        if baseline_row.replay_search_request_id is not None
                        else None
                    ),
                    "candidate_search_request_id": (
                        str(candidate_row.replay_search_request_id)
                        if candidate_row.replay_search_request_id is not None
                        else None
                    ),
                    "baseline_explanation": baseline_explanation,
                    "candidate_explanation": candidate_explanation,
                }
            )
            if len(examples) >= max_examples:
                return examples, sorted(affected_result_types), diagnosis_categories
    return examples, sorted(affected_result_types), diagnosis_categories


def _repair_case_failure_classification(
    *,
    evaluation,
    verification_outcome,
    quality_candidate_count: int,
) -> str:
    if evaluation.total_regressed_count > 0:
        return "replay_regression"
    if verification_outcome.reasons:
        return "release_gate_failure"
    if quality_candidate_count > 0:
        return "unresolved_quality_gap"
    if evaluation.total_improved_count > 0:
        return "candidate_improvement"
    return "no_actionable_gap"


def _build_repair_case_payload(
    session: Session,
    *,
    candidate_harness_name: str,
    baseline_harness_name: str,
    evaluation,
    verification_outcome,
    recommendation: str,
    quality_candidate_count: int,
) -> dict:
    examples, affected_result_types, diagnosis_categories = _repair_case_examples(
        session,
        evaluation,
    )
    classification = _repair_case_failure_classification(
        evaluation=evaluation,
        verification_outcome=verification_outcome,
        quality_candidate_count=quality_candidate_count,
    )
    likely_root_cause = None
    if diagnosis_categories:
        likely_root_cause = "Observed diagnostic categories: " + ", ".join(diagnosis_categories)
    elif classification == "unresolved_quality_gap":
        likely_root_cause = "Quality candidates remain unresolved outside the replay comparison."
    elif classification == "candidate_improvement":
        likely_root_cause = (
            "Candidate harness improves replay outcomes without observed regressions."
        )

    return {
        "schema_name": "search_harness_repair_case",
        "schema_version": "1.0",
        "candidate_harness_name": candidate_harness_name,
        "baseline_harness_name": baseline_harness_name,
        "failure_classification": classification,
        "problem_statement": (
            f"{candidate_harness_name} vs {baseline_harness_name}: "
            f"{evaluation.total_improved_count} improved, "
            f"{evaluation.total_regressed_count} regressed, "
            f"{evaluation.total_unchanged_count} unchanged query outcome(s)."
        ),
        "observed_metric_delta": {
            "total_shared_query_count": evaluation.total_shared_query_count,
            "total_improved_count": evaluation.total_improved_count,
            "total_regressed_count": evaluation.total_regressed_count,
            "total_unchanged_count": evaluation.total_unchanged_count,
            "quality_candidate_count": quality_candidate_count,
        },
        "affected_result_types": affected_result_types,
        "likely_root_cause": likely_root_cause,
        "allowed_repair_surface": [
            "retrieval_profile_overrides",
            "reranker_overrides",
        ],
        "blocked_repair_surfaces": [
            "canonical_document_artifacts",
            "document_ingest_contracts",
            "evaluation_corpus_weakening",
            "yaml_as_source_of_truth",
        ],
        "recommended_next_action": recommendation,
        "diagnostic_examples": examples,
        "evidence_refs": [
            {
                "ref_kind": "harness_evaluation",
                "candidate_harness_name": candidate_harness_name,
                "baseline_harness_name": baseline_harness_name,
                "source_count": len(evaluation.sources),
            },
            *[
                {
                    "ref_kind": "replay_run_pair",
                    "source_type": source.source_type,
                    "baseline_replay_run_id": str(source.baseline_replay_run_id),
                    "candidate_replay_run_id": str(source.candidate_replay_run_id),
                    "shared_query_count": source.shared_query_count,
                    "improved_count": source.improved_count,
                    "regressed_count": source.regressed_count,
                }
                for source in evaluation.sources
            ],
        ],
    }


def _triage_replay_regression_executor(
    session: Session,
    task: AgentTask,
    payload: TriageReplayRegressionTaskInput,
) -> dict:
    quality_candidates = list_quality_eval_candidates(
        session,
        limit=payload.quality_candidate_limit,
        include_resolved=payload.include_resolved_candidates,
    )
    evaluation = evaluate_search_harness(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=payload.candidate_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            source_types=payload.source_types,
            limit=payload.replay_limit,
        ),
    )
    verification_outcome = evaluate_search_harness_verification(
        session,
        evaluation,
        VerifySearchHarnessEvaluationTaskInput(
            target_task_id=task.id,
            max_total_regressed_count=payload.max_total_regressed_count,
            max_mrr_drop=payload.max_mrr_drop,
            max_zero_result_count_increase=payload.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=payload.max_foreign_top_result_count_increase,
            min_total_shared_query_count=payload.min_total_shared_query_count,
        ),
    )
    recommendation, confidence = _recommend_triage_next_action(
        total_shared_query_count=evaluation.total_shared_query_count,
        total_regressed_count=evaluation.total_regressed_count,
        total_improved_count=evaluation.total_improved_count,
        reason_count=len(verification_outcome.reasons),
        quality_candidate_count=len(quality_candidates),
    )
    top_candidates = quality_candidates[:3]
    repair_case_payload = _build_repair_case_payload(
        session,
        candidate_harness_name=payload.candidate_harness_name,
        baseline_harness_name=payload.baseline_harness_name,
        evaluation=evaluation,
        verification_outcome=verification_outcome,
        recommendation=recommendation,
        quality_candidate_count=len(quality_candidates),
    )
    triage_payload = {
        "shadow_mode": True,
        "triage_kind": "replay_regression",
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "source_types": payload.source_types,
        "replay_limit": payload.replay_limit,
        "quality_candidate_count": len(quality_candidates),
        "top_quality_candidates": jsonable_encoder(top_candidates),
        "evaluation": jsonable_encoder(evaluation),
        "verification": {
            "verifier_type": "shadow_mode_triage_gate",
            "outcome": verification_outcome.outcome,
            "metrics": verification_outcome.metrics,
            "reasons": verification_outcome.reasons,
            "details": verification_outcome.details,
        },
        "recommendation": {
            "next_action": recommendation,
            "confidence": confidence,
            "summary": (
                f"{payload.candidate_harness_name} vs {payload.baseline_harness_name} "
                f"across {len(payload.source_types)} source type(s)."
            ),
        },
        "repair_case": repair_case_payload,
    }
    verification_record = create_agent_task_verification_record(
        session,
        target_task_id=task.id,
        verification_task_id=task.id,
        verifier_type="shadow_mode_triage_gate",
        outcome=verification_outcome.outcome,
        metrics=verification_outcome.metrics,
        reasons=verification_outcome.reasons,
        details=verification_outcome.details,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="triage_summary",
        payload=triage_payload,
        storage_service=StorageService(),
        filename="triage_summary.json",
    )
    repair_case_artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="repair_case",
        payload=repair_case_payload,
        storage_service=StorageService(),
        filename="repair_case.json",
    )
    return {
        "shadow_mode": True,
        "triage_kind": "replay_regression",
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "quality_candidate_count": len(quality_candidates),
        "top_quality_candidates": jsonable_encoder(top_candidates),
        "evaluation": jsonable_encoder(evaluation),
        "verification": verification_record.model_dump(mode="json"),
        "recommendation": triage_payload["recommendation"],
        "repair_case": repair_case_payload,
        "repair_case_artifact_id": str(repair_case_artifact.id),
        "repair_case_artifact_kind": repair_case_artifact.artifact_kind,
        "repair_case_artifact_path": repair_case_artifact.storage_path,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


_ACTION_REGISTRY: dict[str, AgentTaskActionDefinition] = {
    "get_latest_evaluation": AgentTaskActionDefinition(
        task_type="get_latest_evaluation",
        definition_kind="action",
        description="Fetch the latest persisted evaluation detail for one document.",
        payload_model=LatestEvaluationTaskInput,
        executor=_latest_evaluation_executor,
        output_model=LatestEvaluationTaskOutput,
        output_schema_name="get_latest_evaluation_output",
        output_schema_version="1.0",
        input_example={"document_id": "00000000-0000-0000-0000-000000000000"},
        context_builder=_build_generic_task_context,
    ),
    "get_latest_semantic_pass": AgentTaskActionDefinition(
        task_type="get_latest_semantic_pass",
        definition_kind="action",
        description="Fetch the latest active semantic pass for one document.",
        payload_model=LatestSemanticPassTaskInput,
        executor=_latest_semantic_pass_executor,
        output_model=LatestSemanticPassTaskOutput,
        output_schema_name="get_latest_semantic_pass_output",
        output_schema_version="1.0",
        input_example={"document_id": "00000000-0000-0000-0000-000000000000"},
        context_builder=_build_latest_semantic_pass_context,
    ),
    "initialize_workspace_ontology": AgentTaskActionDefinition(
        task_type="initialize_workspace_ontology",
        definition_kind="workflow",
        description="Initialize the workspace ontology from the configured upper ontology seed.",
        payload_model=InitializeWorkspaceOntologyTaskInput,
        executor=_initialize_workspace_ontology_executor,
        output_model=InitializeWorkspaceOntologyTaskOutput,
        output_schema_name="initialize_workspace_ontology_output",
        output_schema_version="1.0",
        input_example={},
        context_builder=_build_initialize_workspace_ontology_context,
    ),
    "get_active_ontology_snapshot": AgentTaskActionDefinition(
        task_type="get_active_ontology_snapshot",
        definition_kind="action",
        description="Fetch the active workspace ontology snapshot.",
        payload_model=GetActiveOntologySnapshotTaskInput,
        executor=_get_active_ontology_snapshot_executor,
        output_model=GetActiveOntologySnapshotTaskOutput,
        output_schema_name="get_active_ontology_snapshot_output",
        output_schema_version="1.0",
        input_example={},
        context_builder=_build_get_active_ontology_snapshot_context,
    ),
    "discover_semantic_bootstrap_candidates": AgentTaskActionDefinition(
        task_type="discover_semantic_bootstrap_candidates",
        definition_kind="workflow",
        description=(
            "Discover provisional semantic concept candidates directly from active "
            "document corpora without mutating the live registry."
        ),
        payload_model=DiscoverSemanticBootstrapCandidatesTaskInput,
        executor=_discover_semantic_bootstrap_candidates_executor,
        output_model=DiscoverSemanticBootstrapCandidatesTaskOutput,
        output_schema_name="discover_semantic_bootstrap_candidates_output",
        output_schema_version="1.0",
        input_example={
            "document_ids": ["00000000-0000-0000-0000-000000000000"],
            "max_candidates": 12,
            "min_document_count": 1,
            "min_source_count": 2,
            "min_phrase_tokens": 2,
            "max_phrase_tokens": 4,
            "exclude_existing_registry_terms": True,
        },
        context_builder=_build_discover_semantic_bootstrap_candidates_context,
    ),
    "export_semantic_supervision_corpus": AgentTaskActionDefinition(
        task_type="export_semantic_supervision_corpus",
        definition_kind="action",
        description=(
            "Export reviewed semantic, evaluation, continuity, and grounded-verification "
            "signals as a supervision corpus."
        ),
        payload_model=ExportSemanticSupervisionCorpusTaskInput,
        executor=_export_semantic_supervision_corpus_executor,
        output_model=ExportSemanticSupervisionCorpusTaskOutput,
        output_schema_name="export_semantic_supervision_corpus_output",
        output_schema_version="1.0",
        input_example={
            "document_ids": ["00000000-0000-0000-0000-000000000000"],
            "reviewed_only": True,
            "include_generation_verifications": True,
        },
        context_builder=_build_export_semantic_supervision_corpus_context,
    ),
    "evaluate_semantic_candidate_extractor": AgentTaskActionDefinition(
        task_type="evaluate_semantic_candidate_extractor",
        definition_kind="workflow",
        description=(
            "Evaluate a shadow semantic candidate extractor against the lexical baseline "
            "and fixed semantic expectations."
        ),
        payload_model=EvaluateSemanticCandidateExtractorTaskInput,
        executor=_evaluate_semantic_candidate_extractor_executor,
        output_model=EvaluateSemanticCandidateExtractorTaskOutput,
        output_schema_name="evaluate_semantic_candidate_extractor_output",
        output_schema_version="1.0",
        input_example={
            "document_ids": ["00000000-0000-0000-0000-000000000000"],
            "candidate_extractor_name": "concept_ranker_v1",
            "baseline_extractor_name": "registry_lexical_v1",
            "max_candidates_per_source": 3,
            "score_threshold": 0.34,
        },
        context_builder=_build_evaluate_semantic_candidate_extractor_context,
    ),
    "build_shadow_semantic_graph": AgentTaskActionDefinition(
        task_type="build_shadow_semantic_graph",
        definition_kind="workflow",
        description=(
            "Build a shadow cross-document semantic graph memory artifact without "
            "mutating live graph state."
        ),
        payload_model=BuildShadowSemanticGraphTaskInput,
        executor=_build_shadow_semantic_graph_executor,
        output_model=BuildShadowSemanticGraphTaskOutput,
        output_schema_name="build_shadow_semantic_graph_output",
        output_schema_version="1.0",
        input_example={
            "document_ids": ["00000000-0000-0000-0000-000000000000"],
            "relation_extractor_name": "relation_ranker_v1",
            "minimum_review_status": "candidate",
            "min_shared_documents": 2,
            "score_threshold": 0.45,
        },
        context_builder=_build_build_shadow_semantic_graph_context,
    ),
    "evaluate_semantic_relation_extractor": AgentTaskActionDefinition(
        task_type="evaluate_semantic_relation_extractor",
        definition_kind="workflow",
        description=(
            "Evaluate a shadow semantic relation extractor against a deterministic graph baseline."
        ),
        payload_model=EvaluateSemanticRelationExtractorTaskInput,
        executor=_evaluate_semantic_relation_extractor_executor,
        output_model=EvaluateSemanticRelationExtractorTaskOutput,
        output_schema_name="evaluate_semantic_relation_extractor_output",
        output_schema_version="1.0",
        input_example={
            "document_ids": ["00000000-0000-0000-0000-000000000000"],
            "baseline_extractor_name": "cooccurrence_v1",
            "candidate_extractor_name": "relation_ranker_v1",
            "minimum_review_status": "candidate",
            "baseline_min_shared_documents": 2,
            "candidate_score_threshold": 0.45,
            "expected_min_shared_documents": 1,
        },
        context_builder=_build_evaluate_semantic_relation_extractor_context,
    ),
    "prepare_semantic_generation_brief": AgentTaskActionDefinition(
        task_type="prepare_semantic_generation_brief",
        definition_kind="workflow",
        description=(
            "Build a typed semantic generation brief and dossier for knowledge-brief drafting."
        ),
        payload_model=PrepareSemanticGenerationBriefTaskInput,
        executor=_prepare_semantic_generation_brief_executor,
        output_model=PrepareSemanticGenerationBriefTaskOutput,
        output_schema_name="prepare_semantic_generation_brief_output",
        output_schema_version="1.0",
        input_example={
            "title": "Integration Governance Brief",
            "goal": "Summarize the knowledge base guidance on integration governance.",
            "audience": "Operators",
            "document_ids": ["00000000-0000-0000-0000-000000000000"],
            "target_length": "medium",
            "review_policy": "allow_candidate_with_disclosure",
            "include_shadow_candidates": False,
            "candidate_extractor_name": "concept_ranker_v1",
            "candidate_score_threshold": 0.34,
            "max_shadow_candidates": 8,
        },
        context_builder=_build_prepare_semantic_generation_brief_context,
    ),
    "list_quality_eval_candidates": AgentTaskActionDefinition(
        task_type="list_quality_eval_candidates",
        definition_kind="action",
        description="List mined evaluation candidates from failed evals and live search gaps.",
        payload_model=QualityEvalCandidatesTaskInput,
        executor=_quality_eval_candidates_executor,
        output_model=QualityEvalCandidatesTaskOutput,
        output_schema_name="list_quality_eval_candidates_output",
        output_schema_version="1.0",
        input_example={"limit": 12, "include_resolved": False},
        context_builder=_build_generic_task_context,
    ),
    "replay_search_request": AgentTaskActionDefinition(
        task_type="replay_search_request",
        definition_kind="action",
        description="Replay one persisted search request against the current search stack.",
        payload_model=ReplaySearchRequestTaskInput,
        executor=_replay_search_request_executor,
        output_model=ReplaySearchRequestTaskOutput,
        output_schema_name="replay_search_request_output",
        output_schema_version="1.0",
        input_example={"search_request_id": "00000000-0000-0000-0000-000000000000"},
        context_builder=_build_generic_task_context,
    ),
    "run_search_replay_suite": AgentTaskActionDefinition(
        task_type="run_search_replay_suite",
        definition_kind="action",
        description="Run a replay suite over persisted evaluation, feedback, or gap sources.",
        payload_model=SearchReplayRunRequest,
        executor=_run_search_replay_suite_executor,
        output_model=RunSearchReplaySuiteTaskOutput,
        output_schema_name="run_search_replay_suite_output",
        output_schema_version="1.0",
        input_example={"source_type": "feedback", "limit": 12, "harness_name": "default_v1"},
        context_builder=_build_generic_task_context,
    ),
    "evaluate_search_harness": AgentTaskActionDefinition(
        task_type="evaluate_search_harness",
        definition_kind="action",
        description="Compare a candidate harness against a baseline across replay sources.",
        payload_model=SearchHarnessEvaluationRequest,
        executor=_evaluate_search_harness_executor,
        output_model=EvaluateSearchHarnessTaskOutput,
        output_schema_name="evaluate_search_harness_output",
        output_schema_version="1.0",
        input_example={
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "source_types": ["evaluation_queries", "feedback"],
            "limit": 12,
        },
        context_builder=_build_evaluate_search_harness_context,
    ),
    "verify_search_harness_evaluation": AgentTaskActionDefinition(
        task_type="verify_search_harness_evaluation",
        definition_kind="verifier",
        description=(
            "Verify persisted harness-evaluation replay evidence against rollout thresholds."
        ),
        payload_model=VerifySearchHarnessEvaluationTaskInput,
        executor=_verify_search_harness_evaluation_executor,
        output_model=VerifySearchHarnessEvaluationTaskOutput,
        output_schema_name="verify_search_harness_evaluation_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "max_total_regressed_count": 0,
            "max_mrr_drop": 0.0,
            "max_zero_result_count_increase": 0,
            "max_foreign_top_result_count_increase": 0,
            "min_total_shared_query_count": 1,
        },
        context_builder=_build_verify_search_harness_evaluation_context,
    ),
    "draft_harness_config_update": AgentTaskActionDefinition(
        task_type="draft_harness_config_update",
        definition_kind="draft",
        description=(
            "Draft a derived search harness configuration without changing live search behavior."
        ),
        payload_model=DraftHarnessConfigUpdateTaskInput,
        executor=_draft_harness_config_update_executor,
        side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
        output_model=DraftHarnessConfigUpdateTaskOutput,
        output_schema_name="draft_harness_config_update_output",
        output_schema_version="1.0",
        input_example={
            "draft_harness_name": "wide_v2_review",
            "base_harness_name": "wide_v2",
            "source_task_id": "00000000-0000-0000-0000-000000000000",
            "rationale": "Raise recall and title weighting for review.",
            "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
            "reranker_overrides": {
                "source_filename_token_coverage_bonus": 0.055,
                "document_title_token_coverage_bonus": 0.05,
            },
        },
        context_builder=_build_draft_harness_config_context,
    ),
    "draft_semantic_registry_update": AgentTaskActionDefinition(
        task_type="draft_semantic_registry_update",
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
        context_builder=_build_draft_semantic_registry_update_context,
    ),
    "draft_ontology_extension": AgentTaskActionDefinition(
        task_type="draft_ontology_extension",
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
        context_builder=_build_draft_ontology_extension_context,
    ),
    "draft_graph_promotions": AgentTaskActionDefinition(
        task_type="draft_graph_promotions",
        definition_kind="draft",
        description="Draft approved cross-document graph edges without mutating live graph memory.",
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
        context_builder=_build_draft_graph_promotions_context,
    ),
    "verify_draft_harness_config": AgentTaskActionDefinition(
        task_type="verify_draft_harness_config",
        definition_kind="verifier",
        description=(
            "Evaluate a draft harness configuration ephemerally and persist a verifier verdict."
        ),
        payload_model=VerifyDraftHarnessConfigTaskInput,
        executor=_verify_draft_harness_config_executor,
        output_model=VerifyDraftHarnessConfigTaskOutput,
        output_schema_name="verify_draft_harness_config_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "baseline_harness_name": "default_v1",
            "source_types": ["evaluation_queries", "feedback"],
            "limit": 12,
            "max_total_regressed_count": 0,
            "max_mrr_drop": 0.0,
            "max_zero_result_count_increase": 0,
            "max_foreign_top_result_count_increase": 0,
            "min_total_shared_query_count": 1,
        },
        context_builder=_build_verify_draft_harness_config_context,
    ),
    "verify_draft_semantic_registry_update": AgentTaskActionDefinition(
        task_type="verify_draft_semantic_registry_update",
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
        context_builder=_build_verify_draft_semantic_registry_update_context,
    ),
    "verify_draft_ontology_extension": AgentTaskActionDefinition(
        task_type="verify_draft_ontology_extension",
        definition_kind="verifier",
        description=("Verify an additive ontology extension draft against active documents."),
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
        context_builder=_build_verify_draft_ontology_extension_context,
    ),
    "verify_draft_graph_promotions": AgentTaskActionDefinition(
        task_type="verify_draft_graph_promotions",
        definition_kind="verifier",
        description=(
            "Verify a graph promotion draft against current ontology and traceability constraints."
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
        context_builder=_build_verify_draft_graph_promotions_context,
    ),
    "draft_semantic_grounded_document": AgentTaskActionDefinition(
        task_type="draft_semantic_grounded_document",
        definition_kind="draft",
        description=(
            "Draft a semantic-grounded knowledge brief from a typed semantic generation brief."
        ),
        payload_model=DraftSemanticGroundedDocumentTaskInput,
        executor=_draft_semantic_grounded_document_executor,
        side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
        output_model=DraftSemanticGroundedDocumentTaskOutput,
        output_schema_name="draft_semantic_grounded_document_output",
        output_schema_version="1.0",
        input_example={"target_task_id": "00000000-0000-0000-0000-000000000000"},
        context_builder=_build_draft_semantic_grounded_document_context,
    ),
    "verify_semantic_grounded_document": AgentTaskActionDefinition(
        task_type="verify_semantic_grounded_document",
        definition_kind="verifier",
        description=(
            "Verify that a semantic-grounded knowledge brief is fully "
            "traceable to typed semantic support."
        ),
        payload_model=VerifySemanticGroundedDocumentTaskInput,
        executor=_verify_semantic_grounded_document_executor,
        output_model=VerifySemanticGroundedDocumentTaskOutput,
        output_schema_name="verify_semantic_grounded_document_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "max_unsupported_claim_count": 0,
            "require_full_claim_traceability": True,
            "require_full_concept_coverage": True,
        },
        context_builder=_build_verify_semantic_grounded_document_context,
    ),
    "triage_replay_regression": AgentTaskActionDefinition(
        task_type="triage_replay_regression",
        definition_kind="workflow",
        description=(
            "Run a shadow-mode replay regression triage over quality gaps and harness evidence."
        ),
        payload_model=TriageReplayRegressionTaskInput,
        executor=_triage_replay_regression_executor,
        output_model=TriageReplayRegressionTaskOutput,
        output_schema_name="triage_replay_regression_output",
        output_schema_version="1.0",
        input_example={
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "source_types": ["evaluation_queries", "feedback"],
            "replay_limit": 12,
            "quality_candidate_limit": 12,
            "include_resolved_candidates": False,
            "max_total_regressed_count": 0,
            "max_mrr_drop": 0.0,
            "max_zero_result_count_increase": 0,
            "max_foreign_top_result_count_increase": 0,
            "min_total_shared_query_count": 1,
        },
        context_builder=_build_triage_replay_regression_context,
    ),
    "triage_semantic_pass": AgentTaskActionDefinition(
        task_type="triage_semantic_pass",
        definition_kind="workflow",
        description=(
            "Summarize active semantic-pass gaps, continuity changes, and bounded next actions."
        ),
        payload_model=TriageSemanticPassTaskInput,
        executor=_triage_semantic_pass_executor,
        output_model=TriageSemanticPassTaskOutput,
        output_schema_name="triage_semantic_pass_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "low_evidence_threshold": 2,
        },
        context_builder=_build_triage_semantic_pass_context,
    ),
    "triage_semantic_candidate_disagreements": AgentTaskActionDefinition(
        task_type="triage_semantic_candidate_disagreements",
        definition_kind="workflow",
        description=(
            "Compact shadow semantic disagreements into typed issues and "
            "bounded follow-up recommendations."
        ),
        payload_model=TriageSemanticCandidateDisagreementsTaskInput,
        executor=_triage_semantic_candidate_disagreements_executor,
        output_model=TriageSemanticCandidateDisagreementsTaskOutput,
        output_schema_name="triage_semantic_candidate_disagreements_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "min_score": 0.34,
            "include_expected_only": False,
        },
        context_builder=_build_triage_semantic_candidate_disagreements_context,
    ),
    "triage_semantic_graph_disagreements": AgentTaskActionDefinition(
        task_type="triage_semantic_graph_disagreements",
        definition_kind="workflow",
        description=(
            "Compact shadow semantic graph disagreements into typed issues and "
            "promotion follow-ups."
        ),
        payload_model=TriageSemanticGraphDisagreementsTaskInput,
        executor=_triage_semantic_graph_disagreements_executor,
        output_model=TriageSemanticGraphDisagreementsTaskOutput,
        output_schema_name="triage_semantic_graph_disagreements_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "min_score": 0.45,
            "expected_only": True,
        },
        context_builder=_build_triage_semantic_graph_disagreements_context,
    ),
    "enqueue_document_reprocess": AgentTaskActionDefinition(
        task_type="enqueue_document_reprocess",
        definition_kind="promotion",
        description=(
            "Queue a new processing run for an existing document after explicit approval."
        ),
        payload_model=EnqueueDocumentReprocessTaskInput,
        executor=_enqueue_document_reprocess_executor,
        side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
        requires_approval=True,
        output_model=EnqueueDocumentReprocessTaskOutput,
        output_schema_name="enqueue_document_reprocess_output",
        output_schema_version="1.0",
        input_example={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "source_task_id": "00000000-0000-0000-0000-000000000000",
            "reason": "Triaged replay regression needs a fresh parse.",
        },
        context_builder=_build_generic_task_context,
    ),
    "apply_harness_config_update": AgentTaskActionDefinition(
        task_type="apply_harness_config_update",
        definition_kind="promotion",
        description=(
            "Apply a verified draft harness configuration as a new review harness after approval."
        ),
        payload_model=ApplyHarnessConfigUpdateTaskInput,
        executor=_apply_harness_config_update_executor,
        side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
        requires_approval=True,
        output_model=ApplyHarnessConfigUpdateTaskOutput,
        output_schema_name="apply_harness_config_update_output",
        output_schema_version="1.0",
        input_example={
            "draft_task_id": "00000000-0000-0000-0000-000000000000",
            "verification_task_id": "00000000-0000-0000-0000-000000000000",
            "reason": "Publish the verified review harness for operator use.",
        },
        context_builder=_build_apply_harness_config_update_context,
    ),
    "apply_semantic_registry_update": AgentTaskActionDefinition(
        task_type="apply_semantic_registry_update",
        definition_kind="promotion",
        description=("Apply a verified semantic registry update after approval."),
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
        context_builder=_build_apply_semantic_registry_update_context,
    ),
    "apply_ontology_extension": AgentTaskActionDefinition(
        task_type="apply_ontology_extension",
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
        context_builder=_build_apply_ontology_extension_context,
    ),
    "apply_graph_promotions": AgentTaskActionDefinition(
        task_type="apply_graph_promotions",
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
        context_builder=_build_apply_graph_promotions_context,
    ),
    "build_document_fact_graph": AgentTaskActionDefinition(
        task_type="build_document_fact_graph",
        definition_kind="workflow",
        description="Build a minimal semantic fact graph for one document.",
        payload_model=BuildDocumentFactGraphTaskInput,
        executor=_build_document_fact_graph_executor,
        output_model=BuildDocumentFactGraphTaskOutput,
        output_schema_name="build_document_fact_graph_output",
        output_schema_version="1.0",
        input_example={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "minimum_review_status": "approved",
        },
        context_builder=_build_build_document_fact_graph_context,
    ),
}


def list_agent_task_actions() -> list[AgentTaskActionDefinition]:
    return list(_ACTION_REGISTRY.values())


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
