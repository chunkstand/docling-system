from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskSideEffectLevel,
)
from app.schemas.agent_tasks import (
    ApplyClaimSupportCalibrationPolicyTaskInput,
    ApplyClaimSupportCalibrationPolicyTaskOutput,
    ApplyGraphPromotionsTaskInput,
    ApplyGraphPromotionsTaskOutput,
    ApplyHarnessConfigUpdateTaskInput,
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
    DraftClaimSupportCalibrationPolicyTaskInput,
    DraftClaimSupportCalibrationPolicyTaskOutput,
    DraftGraphPromotionsTaskInput,
    DraftGraphPromotionsTaskOutput,
    DraftHarnessConfigFromOptimizationTaskInput,
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
    EvaluateClaimSupportJudgeTaskInput,
    EvaluateClaimSupportJudgeTaskOutput,
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
    InspectEvalFailureCaseTaskInput,
    InspectEvalFailureCaseTaskOutput,
    LatestEvaluationTaskInput,
    LatestEvaluationTaskOutput,
    LatestSemanticPassTaskInput,
    LatestSemanticPassTaskOutput,
    OptimizeSearchHarnessFromCaseTaskInput,
    OptimizeSearchHarnessFromCaseTaskOutput,
    PrepareSemanticGenerationBriefTaskInput,
    PrepareSemanticGenerationBriefTaskOutput,
    QualityEvalCandidatesTaskInput,
    QualityEvalCandidatesTaskOutput,
    QueueClaimSupportPolicyChangeImpactReplayTaskInput,
    QueueClaimSupportPolicyChangeImpactReplayTaskOutput,
    RefreshEvalFailureCasesTaskInput,
    RefreshEvalFailureCasesTaskOutput,
    ReplaySearchRequestTaskInput,
    TriageEvalFailureCaseTaskInput,
    TriageEvalFailureCaseTaskOutput,
    TriageReplayRegressionTaskInput,
    TriageSemanticCandidateDisagreementsTaskInput,
    TriageSemanticCandidateDisagreementsTaskOutput,
    TriageSemanticGraphDisagreementsTaskInput,
    TriageSemanticGraphDisagreementsTaskOutput,
    TriageSemanticPassTaskInput,
    TriageSemanticPassTaskOutput,
    VerifyClaimSupportCalibrationPolicyTaskInput,
    VerifyClaimSupportCalibrationPolicyTaskOutput,
    VerifyDraftGraphPromotionsTaskInput,
    VerifyDraftGraphPromotionsTaskOutput,
    VerifyDraftHarnessConfigTaskInput,
    VerifyDraftHarnessConfigTaskOutput,
    VerifyDraftOntologyExtensionTaskInput,
    VerifyDraftOntologyExtensionTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
    VerifySearchHarnessEvaluationTaskInput,
    VerifySemanticGroundedDocumentTaskInput,
    VerifySemanticGroundedDocumentTaskOutput,
)
from app.schemas.search import (
    SearchHarnessEvaluationRequest,
    SearchHarnessOptimizationRequest,
    SearchReplayRunRequest,
)
from app.services.agent_actions.claim_support_activation import (
    apply_claim_support_calibration_policy_executor as _apply_claim_support_policy_executor,
)
from app.services.agent_actions.claim_support_activation import (
    require_active_replay_alert_fixture_coverage_waiver,
)
from app.services.agent_actions.claim_support_drafting import (
    draft_claim_support_calibration_policy_executor as _draft_claim_support_policy_executor,
)
from app.services.agent_actions.claim_support_evaluation import (
    evaluate_claim_support_judge_executor as _evaluate_claim_support_judge_executor,
)
from app.services.agent_actions.claim_support_evaluation import (
    queue_policy_change_impact_replay_executor as _queue_claim_support_replay_executor,
)
from app.services.agent_actions.claim_support_shared import (
    replay_alert_fixture_coverage_waiver_sha256,
)
from app.services.agent_actions.claim_support_verification import (
    verify_claim_support_calibration_policy_executor as _verify_claim_support_policy_executor,
)
from app.services.agent_actions.evaluation import (
    inspect_eval_failure_case_executor as _inspect_eval_failure_case_executor,
)
from app.services.agent_actions.evaluation import (
    latest_evaluation_executor as _latest_evaluation_executor,
)
from app.services.agent_actions.evaluation import (
    quality_eval_candidates_executor as _quality_eval_candidates_executor,
)
from app.services.agent_actions.evaluation import (
    refresh_eval_failure_cases_executor as _refresh_eval_failure_cases_executor,
)
from app.services.agent_actions.evaluation import (
    triage_eval_failure_case_executor as _triage_eval_failure_case_executor,
)
from app.services.agent_actions.manifest import (
    AgentActionContractIssue,
    build_agent_action_index,
    build_agent_action_manifest,
    validate_agent_action_contracts,
)
from app.services.agent_actions.report_actions import (
    build_report_action_definitions,
)
from app.services.agent_actions.search_harness import (
    build_harness_follow_up_summary,
    build_repair_case_payload,
    build_search_harness_action_definitions,
    harness_override_has_changes,
    recommend_triage_next_action,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
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
    reprocess_document,
)
from app.services.eval_workbench import (
    get_eval_failure_case,
)
from app.services.quality import list_quality_eval_candidates
from app.services.search import get_search_harness, list_search_harnesses
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_harness_optimization import run_search_harness_optimization_loop
from app.services.search_harness_overrides import upsert_applied_search_harness_override
from app.services.search_history import replay_search_request
from app.services.search_release_gate import (
    evaluate_search_harness_release_gate,
)
from app.services.search_replays import (
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
_replay_alert_fixture_coverage_waiver_sha256 = replay_alert_fixture_coverage_waiver_sha256
_require_active_replay_alert_fixture_coverage_waiver = (
    require_active_replay_alert_fixture_coverage_waiver
)


def _optimize_search_harness_from_case_executor(
    session: Session,
    task: AgentTask,
    payload: OptimizeSearchHarnessFromCaseTaskInput,
) -> dict:
    case = get_eval_failure_case(session, payload.case_id)
    candidate_harness_name = (
        payload.candidate_harness_name
        or f"case_{str(payload.case_id).replace('-', '_')[:18]}_candidate"
    )
    optimization = run_search_harness_optimization_loop(
        session,
        SearchHarnessOptimizationRequest(
            base_harness_name=payload.base_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            candidate_harness_name=candidate_harness_name,
            source_types=payload.source_types,
            limit=payload.limit,
            iterations=payload.iterations,
            tune_fields=payload.tune_fields,
            max_total_regressed_count=payload.max_total_regressed_count,
            max_mrr_drop=payload.max_mrr_drop,
            max_zero_result_count_increase=payload.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=payload.max_foreign_top_result_count_increase,
            min_total_shared_query_count=payload.min_total_shared_query_count,
        ),
    )
    best_gate_passed = optimization.best_gate.get("outcome") == "passed"
    best_override_changed = harness_override_has_changes(optimization.best_override_spec)
    can_draft = best_gate_passed and best_override_changed
    recommendation = {
        "next_action": "draft_harness_config_update_from_optimization"
        if can_draft
        else "inspect_optimizer_attempts",
        "confidence": "medium" if can_draft else "low",
        "summary": (
            "Best override is a changed passing candidate."
            if can_draft
            else (
                "Best gate passed but did not change the harness; inspect optimizer attempts."
                if best_gate_passed
                else (
                    f"Best override has score {optimization.best_score} and gate "
                    f"{optimization.best_gate.get('outcome')}."
                )
            )
        ),
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="search_harness_optimization",
        payload=jsonable_encoder(optimization),
        storage_service=StorageService(),
        filename="search_harness_optimization.json",
    )
    return {
        "case": jsonable_encoder(case),
        "optimization": jsonable_encoder(optimization),
        "recommendation": recommendation,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _draft_harness_config_from_optimization_executor(
    session: Session,
    task: AgentTask,
    payload: DraftHarnessConfigFromOptimizationTaskInput,
) -> dict:
    source_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.source_task_id,
        dependency_kind="source_task",
        expected_task_type="optimize_search_harness_from_case",
        expected_schema_name="optimize_search_harness_from_case_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Harness drafts from optimization must declare the optimizer task "
            "as a source_task dependency."
        ),
        rerun_message=("Optimizer task must be rerun after the context migration before drafting."),
    )
    source_output = OptimizeSearchHarnessFromCaseTaskOutput.model_validate(source_context.output)
    optimization = source_output.optimization
    best_override_spec = dict(optimization.best_override_spec or {})
    if not harness_override_has_changes(best_override_spec):
        raise ValueError(
            "Optimization did not produce a changed harness override; "
            "refusing to draft a no-op config update."
        )
    rationale = payload.rationale or (
        "Agent-proposed bounded harness repair from eval failure case optimization."
    )
    best_override_spec = {
        **best_override_spec,
        "override_type": "draft_harness_config_update",
        "override_source": "task_draft",
        "draft_task_id": str(task.id),
        "source_task_id": str(payload.source_task_id),
        "rationale": rationale,
    }
    effective_harness = get_search_harness(
        payload.draft_harness_name,
        {payload.draft_harness_name: best_override_spec},
    )
    draft_payload = {
        "draft_harness_name": payload.draft_harness_name,
        "base_harness_name": optimization.base_harness_name,
        "source_task_id": str(payload.source_task_id),
        "source_task_type": source_context.task_type,
        "rationale": rationale,
        "override_spec": best_override_spec,
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
        "source_case": jsonable_encoder(source_output.case),
        "optimization_summary": {
            "stopped_reason": optimization.stopped_reason,
            "iterations_completed": optimization.iterations_completed,
            "best_score": optimization.best_score,
            "best_gate": optimization.best_gate,
        },
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
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
        expected_task_type=(
            "draft_harness_config_update",
            "draft_harness_config_update_from_optimization",
        ),
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
        follow_up_summary_payload = build_harness_follow_up_summary(
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
    recommendation, confidence = recommend_triage_next_action(
        total_shared_query_count=evaluation.total_shared_query_count,
        total_regressed_count=evaluation.total_regressed_count,
        total_improved_count=evaluation.total_improved_count,
        reason_count=len(verification_outcome.reasons),
        quality_candidate_count=len(quality_candidates),
    )
    top_candidates = quality_candidates[:3]
    repair_case_payload = build_repair_case_payload(
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


_SEARCH_HARNESS_ACTION_REGISTRY = build_search_harness_action_definitions(
    optimize_search_harness_from_case_executor=_optimize_search_harness_from_case_executor,
    draft_harness_config_from_optimization_executor=(
        _draft_harness_config_from_optimization_executor
    ),
    replay_search_request_executor=_replay_search_request_executor,
    run_search_replay_suite_executor=_run_search_replay_suite_executor,
    evaluate_search_harness_executor=_evaluate_search_harness_executor,
    verify_search_harness_evaluation_executor=_verify_search_harness_evaluation_executor,
    draft_harness_config_update_executor=_draft_harness_config_update_executor,
    verify_draft_harness_config_executor=_verify_draft_harness_config_executor,
    triage_replay_regression_executor=_triage_replay_regression_executor,
    apply_harness_config_update_executor=_apply_harness_config_update_executor,
)

_REPORT_ACTION_REGISTRY = build_report_action_definitions()


def _search_harness_action(task_type: str) -> AgentTaskActionDefinition:
    return _SEARCH_HARNESS_ACTION_REGISTRY[task_type]


_ACTION_REGISTRY: dict[str, AgentTaskActionDefinition] = {
    "get_latest_evaluation": AgentTaskActionDefinition(
        task_type="get_latest_evaluation",
        capability="evaluation",
        definition_kind="action",
        description="Fetch the latest persisted evaluation detail for one document.",
        payload_model=LatestEvaluationTaskInput,
        executor=_latest_evaluation_executor,
        output_model=LatestEvaluationTaskOutput,
        output_schema_name="get_latest_evaluation_output",
        output_schema_version="1.0",
        input_example={"document_id": "00000000-0000-0000-0000-000000000000"},
        context_builder_name="generic",
    ),
    "get_latest_semantic_pass": AgentTaskActionDefinition(
        task_type="get_latest_semantic_pass",
        capability="semantic_memory",
        definition_kind="action",
        description="Fetch the latest active semantic pass for one document.",
        payload_model=LatestSemanticPassTaskInput,
        executor=_latest_semantic_pass_executor,
        output_model=LatestSemanticPassTaskOutput,
        output_schema_name="get_latest_semantic_pass_output",
        output_schema_version="1.0",
        input_example={"document_id": "00000000-0000-0000-0000-000000000000"},
        context_builder_name="latest_semantic_pass",
    ),
    "initialize_workspace_ontology": AgentTaskActionDefinition(
        task_type="initialize_workspace_ontology",
        capability="semantic_memory",
        definition_kind="workflow",
        description="Initialize the workspace ontology from the configured upper ontology seed.",
        payload_model=InitializeWorkspaceOntologyTaskInput,
        executor=_initialize_workspace_ontology_executor,
        output_model=InitializeWorkspaceOntologyTaskOutput,
        output_schema_name="initialize_workspace_ontology_output",
        output_schema_version="1.0",
        input_example={},
        context_builder_name="initialize_workspace_ontology",
    ),
    "get_active_ontology_snapshot": AgentTaskActionDefinition(
        task_type="get_active_ontology_snapshot",
        capability="semantic_memory",
        definition_kind="action",
        description="Fetch the active workspace ontology snapshot.",
        payload_model=GetActiveOntologySnapshotTaskInput,
        executor=_get_active_ontology_snapshot_executor,
        output_model=GetActiveOntologySnapshotTaskOutput,
        output_schema_name="get_active_ontology_snapshot_output",
        output_schema_version="1.0",
        input_example={},
        context_builder_name="get_active_ontology_snapshot",
    ),
    "discover_semantic_bootstrap_candidates": AgentTaskActionDefinition(
        task_type="discover_semantic_bootstrap_candidates",
        capability="semantic_memory",
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
        context_builder_name="discover_semantic_bootstrap_candidates",
    ),
    "export_semantic_supervision_corpus": AgentTaskActionDefinition(
        task_type="export_semantic_supervision_corpus",
        capability="semantic_memory",
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
        context_builder_name="export_semantic_supervision_corpus",
    ),
    "evaluate_semantic_candidate_extractor": AgentTaskActionDefinition(
        task_type="evaluate_semantic_candidate_extractor",
        capability="semantic_memory",
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
        context_builder_name="evaluate_semantic_candidate_extractor",
    ),
    "build_shadow_semantic_graph": AgentTaskActionDefinition(
        task_type="build_shadow_semantic_graph",
        capability="semantic_memory",
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
        context_builder_name="build_shadow_semantic_graph",
    ),
    "evaluate_semantic_relation_extractor": AgentTaskActionDefinition(
        task_type="evaluate_semantic_relation_extractor",
        capability="semantic_memory",
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
        context_builder_name="evaluate_semantic_relation_extractor",
    ),
    **_REPORT_ACTION_REGISTRY,
    "evaluate_claim_support_judge": AgentTaskActionDefinition(
        task_type="evaluate_claim_support_judge",
        capability="technical_reports",
        definition_kind="workflow",
        description=(
            "Replay and persist fixed hard-case evaluations for the technical report "
            "claim support judge."
        ),
        payload_model=EvaluateClaimSupportJudgeTaskInput,
        executor=_evaluate_claim_support_judge_executor,
        output_model=EvaluateClaimSupportJudgeTaskOutput,
        output_schema_name="evaluate_claim_support_judge_output",
        output_schema_version="1.0",
        input_example={
            "evaluation_name": "claim_support_judge_calibration",
            "fixture_set_name": "default_claim_support_v1",
            "fixture_set_version": "v1",
            "policy_name": "claim_support_judge_calibration_policy",
            "min_support_score": 0.34,
            "min_overall_accuracy": 1.0,
            "min_verdict_precision": 1.0,
            "min_verdict_recall": 1.0,
        },
        context_builder_name="evaluate_claim_support_judge",
    ),
    "draft_claim_support_calibration_policy": AgentTaskActionDefinition(
        task_type="draft_claim_support_calibration_policy",
        capability="technical_reports",
        definition_kind="draft",
        description="Draft a claim-support calibration policy without changing the active policy.",
        payload_model=DraftClaimSupportCalibrationPolicyTaskInput,
        executor=_draft_claim_support_policy_executor,
        side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
        output_model=DraftClaimSupportCalibrationPolicyTaskOutput,
        output_schema_name="draft_claim_support_calibration_policy_output",
        output_schema_version="1.0",
        input_example={
            "policy_name": "claim_support_judge_calibration_policy",
            "policy_version": "v2",
            "rationale": "Tighten calibration coverage before report-generation promotion.",
            "min_hard_case_kind_count": 4,
            "required_hard_case_kinds": [
                "exact_source_support",
                "wrong_evidence",
                "lexical_overlap_wrong_evidence",
                "missing_traceable_evidence",
            ],
            "required_verdicts": ["supported", "unsupported", "insufficient_evidence"],
        },
        context_builder_name="generic",
    ),
    "verify_claim_support_calibration_policy": AgentTaskActionDefinition(
        task_type="verify_claim_support_calibration_policy",
        capability="technical_reports",
        definition_kind="verifier",
        description="Verify a draft claim-support calibration policy against replay fixtures.",
        payload_model=VerifyClaimSupportCalibrationPolicyTaskInput,
        executor=_verify_claim_support_policy_executor,
        output_model=VerifyClaimSupportCalibrationPolicyTaskOutput,
        output_schema_name="verify_claim_support_calibration_policy_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "fixture_set_name": "default_claim_support_v1",
            "fixture_set_version": "v1",
            "include_replay_alert_fixtures": True,
            "require_replay_alert_fixture_coverage": True,
        },
        context_builder_name="generic",
    ),
    "apply_claim_support_calibration_policy": AgentTaskActionDefinition(
        task_type="apply_claim_support_calibration_policy",
        capability="technical_reports",
        definition_kind="promotion",
        description="Activate a verified claim-support calibration policy after approval.",
        payload_model=ApplyClaimSupportCalibrationPolicyTaskInput,
        executor=_apply_claim_support_policy_executor,
        side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
        requires_approval=True,
        output_model=ApplyClaimSupportCalibrationPolicyTaskOutput,
        output_schema_name="apply_claim_support_calibration_policy_output",
        output_schema_version="1.0",
        input_example={
            "draft_task_id": "00000000-0000-0000-0000-000000000000",
            "verification_task_id": "00000000-0000-0000-0000-000000000000",
            "reason": "Publish the verified claim-support calibration policy.",
            "waiver_activation_approved_by": "reviewer@example.com",
            "waiver_activation_approval_note": (
                "Reviewed active replay-alert fixture coverage waiver before activation."
            ),
        },
        context_builder_name="generic",
    ),
    "queue_claim_support_policy_change_impact_replay": AgentTaskActionDefinition(
        task_type="queue_claim_support_policy_change_impact_replay",
        capability="technical_reports",
        definition_kind="draft",
        description=(
            "Create managed replay tasks for stale technical-report artifacts identified "
            "by a claim-support policy change-impact row."
        ),
        payload_model=QueueClaimSupportPolicyChangeImpactReplayTaskInput,
        executor=_queue_claim_support_replay_executor,
        side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
        output_model=QueueClaimSupportPolicyChangeImpactReplayTaskOutput,
        output_schema_name="queue_claim_support_policy_change_impact_replay_output",
        output_schema_version="1.0",
        input_example={
            "change_impact_id": "00000000-0000-0000-0000-000000000000",
            "requested_by": "docling-system",
        },
        context_builder_name="generic",
    ),
    "prepare_semantic_generation_brief": AgentTaskActionDefinition(
        task_type="prepare_semantic_generation_brief",
        capability="semantic_memory",
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
        context_builder_name="prepare_semantic_generation_brief",
    ),
    "list_quality_eval_candidates": AgentTaskActionDefinition(
        task_type="list_quality_eval_candidates",
        capability="evaluation",
        definition_kind="action",
        description="List mined evaluation candidates from failed evals and live search gaps.",
        payload_model=QualityEvalCandidatesTaskInput,
        executor=_quality_eval_candidates_executor,
        output_model=QualityEvalCandidatesTaskOutput,
        output_schema_name="list_quality_eval_candidates_output",
        output_schema_version="1.0",
        input_example={"limit": 12, "include_resolved": False},
        context_builder_name="generic",
    ),
    "refresh_eval_failure_cases": AgentTaskActionDefinition(
        task_type="refresh_eval_failure_cases",
        capability="evaluation",
        definition_kind="action",
        description="Upsert durable eval observations and failure cases from quality signals.",
        payload_model=RefreshEvalFailureCasesTaskInput,
        executor=_refresh_eval_failure_cases_executor,
        output_model=RefreshEvalFailureCasesTaskOutput,
        output_schema_name="refresh_eval_failure_cases_output",
        output_schema_version="1.0",
        input_example={"limit": 50, "include_resolved": False},
        context_builder_name="generic",
    ),
    "inspect_eval_failure_case": AgentTaskActionDefinition(
        task_type="inspect_eval_failure_case",
        capability="evaluation",
        definition_kind="action",
        description="Load one eval failure case with linked agent-legible evidence.",
        payload_model=InspectEvalFailureCaseTaskInput,
        executor=_inspect_eval_failure_case_executor,
        output_model=InspectEvalFailureCaseTaskOutput,
        output_schema_name="inspect_eval_failure_case_output",
        output_schema_version="1.0",
        input_example={"case_id": "00000000-0000-0000-0000-000000000000"},
        context_builder_name="generic",
    ),
    "triage_eval_failure_case": AgentTaskActionDefinition(
        task_type="triage_eval_failure_case",
        capability="evaluation",
        definition_kind="workflow",
        description="Classify one eval failure case and produce bounded repair next steps.",
        payload_model=TriageEvalFailureCaseTaskInput,
        executor=_triage_eval_failure_case_executor,
        output_model=TriageEvalFailureCaseTaskOutput,
        output_schema_name="triage_eval_failure_case_output",
        output_schema_version="1.0",
        input_example={"case_id": "00000000-0000-0000-0000-000000000000"},
        context_builder_name="generic",
    ),
    "optimize_search_harness_from_case": _search_harness_action(
        "optimize_search_harness_from_case"
    ),
    "draft_harness_config_update_from_optimization": _search_harness_action(
        "draft_harness_config_update_from_optimization"
    ),
    "replay_search_request": _search_harness_action("replay_search_request"),
    "run_search_replay_suite": _search_harness_action("run_search_replay_suite"),
    "evaluate_search_harness": _search_harness_action("evaluate_search_harness"),
    "verify_search_harness_evaluation": _search_harness_action(
        "verify_search_harness_evaluation"
    ),
    "draft_harness_config_update": _search_harness_action("draft_harness_config_update"),
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
        context_builder_name="draft_graph_promotions",
    ),
    "verify_draft_harness_config": _search_harness_action("verify_draft_harness_config"),
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
        context_builder_name="verify_draft_ontology_extension",
    ),
    "verify_draft_graph_promotions": AgentTaskActionDefinition(
        task_type="verify_draft_graph_promotions",
        capability="semantic_memory",
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
        context_builder_name="verify_draft_graph_promotions",
    ),
    "draft_semantic_grounded_document": AgentTaskActionDefinition(
        task_type="draft_semantic_grounded_document",
        capability="semantic_memory",
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
        context_builder_name="draft_semantic_grounded_document",
    ),
    "verify_semantic_grounded_document": AgentTaskActionDefinition(
        task_type="verify_semantic_grounded_document",
        capability="semantic_memory",
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
        context_builder_name="verify_semantic_grounded_document",
    ),
    "triage_replay_regression": _search_harness_action("triage_replay_regression"),
    "triage_semantic_pass": AgentTaskActionDefinition(
        task_type="triage_semantic_pass",
        capability="semantic_memory",
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
        context_builder_name="triage_semantic_pass",
    ),
    "triage_semantic_candidate_disagreements": AgentTaskActionDefinition(
        task_type="triage_semantic_candidate_disagreements",
        capability="semantic_memory",
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
        context_builder_name="triage_semantic_candidate_disagreements",
    ),
    "triage_semantic_graph_disagreements": AgentTaskActionDefinition(
        task_type="triage_semantic_graph_disagreements",
        capability="semantic_memory",
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
        context_builder_name="triage_semantic_graph_disagreements",
    ),
    "enqueue_document_reprocess": AgentTaskActionDefinition(
        task_type="enqueue_document_reprocess",
        capability="document_lifecycle",
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
        context_builder_name="generic",
    ),
    "apply_harness_config_update": _search_harness_action("apply_harness_config_update"),
    "apply_semantic_registry_update": AgentTaskActionDefinition(
        task_type="apply_semantic_registry_update",
        capability="semantic_memory",
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
    "build_document_fact_graph": AgentTaskActionDefinition(
        task_type="build_document_fact_graph",
        capability="semantic_memory",
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
        context_builder_name="build_document_fact_graph",
    ),
}


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
