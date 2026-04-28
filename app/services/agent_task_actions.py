from __future__ import annotations

from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskSideEffectLevel,
    AgentTaskVerification,
    ClaimSupportCalibrationPolicy,
)
from app.schemas.agent_tasks import (
    ApplyClaimSupportCalibrationPolicyTaskInput,
    ApplyClaimSupportCalibrationPolicyTaskOutput,
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
    BuildReportEvidenceCardsTaskInput,
    BuildReportEvidenceCardsTaskOutput,
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
    DraftTechnicalReportTaskInput,
    DraftTechnicalReportTaskOutput,
    EnqueueDocumentReprocessTaskInput,
    EnqueueDocumentReprocessTaskOutput,
    EvaluateClaimSupportJudgeTaskInput,
    EvaluateClaimSupportJudgeTaskOutput,
    EvaluateDocumentGenerationContextPackTaskInput,
    EvaluateDocumentGenerationContextPackTaskOutput,
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
    InspectEvalFailureCaseTaskInput,
    InspectEvalFailureCaseTaskOutput,
    LatestEvaluationTaskInput,
    LatestEvaluationTaskOutput,
    LatestSemanticPassTaskInput,
    LatestSemanticPassTaskOutput,
    OptimizeSearchHarnessFromCaseTaskInput,
    OptimizeSearchHarnessFromCaseTaskOutput,
    PlanTechnicalReportTaskInput,
    PlanTechnicalReportTaskOutput,
    PrepareReportAgentHarnessTaskInput,
    PrepareReportAgentHarnessTaskOutput,
    PrepareSemanticGenerationBriefTaskInput,
    PrepareSemanticGenerationBriefTaskOutput,
    QualityEvalCandidatesTaskInput,
    QualityEvalCandidatesTaskOutput,
    RefreshEvalFailureCasesTaskInput,
    RefreshEvalFailureCasesTaskOutput,
    ReplaySearchRequestTaskInput,
    ReplaySearchRequestTaskOutput,
    RunSearchReplaySuiteTaskOutput,
    TriageEvalFailureCaseTaskInput,
    TriageEvalFailureCaseTaskOutput,
    TriageReplayRegressionTaskInput,
    TriageReplayRegressionTaskOutput,
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
    VerifySearchHarnessEvaluationTaskOutput,
    VerifySemanticGroundedDocumentTaskInput,
    VerifySemanticGroundedDocumentTaskOutput,
    VerifyTechnicalReportTaskInput,
    VerifyTechnicalReportTaskOutput,
)
from app.schemas.search import (
    SearchFilters,
    SearchHarnessEvaluationRequest,
    SearchHarnessOptimizationRequest,
    SearchReplayRunRequest,
    SearchRequest,
)
from app.services.agent_actions.manifest import (
    AgentActionContractIssue,
    build_agent_action_manifest,
    validate_agent_action_contracts,
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
from app.services.claim_support_evaluations import (
    activate_claim_support_calibration_policy,
    default_claim_support_evaluation_fixtures,
    draft_claim_support_calibration_policy,
    ensure_claim_support_fixture_set,
    evaluate_claim_support_judge_fixture_set,
    get_active_claim_support_calibration_policy,
    mine_claim_support_failure_fixtures,
    persist_claim_support_judge_evaluation,
    resolve_claim_support_calibration_policy,
)
from app.services.claim_support_policy_governance import (
    CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
    CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_FILENAME,
    build_claim_support_policy_activation_governance_payload,
    record_claim_support_policy_activation_governance_event,
)
from app.services.documents import (
    get_latest_document_evaluation_detail,
    reprocess_document,
)
from app.services.eval_workbench import (
    get_eval_failure_case,
    inspect_eval_failure_case,
    refresh_eval_failure_cases,
    triage_eval_failure_case,
)
from app.services.evidence import (
    DOCUMENT_GENERATION_CONTEXT_PACK_GATE,
    attach_artifact_to_evidence_export,
    attach_operator_run_to_evidence_export,
    payload_sha256,
    persist_search_evidence_package_export,
    persist_technical_report_evidence_export,
    persist_technical_report_evidence_manifest,
    record_knowledge_operator_run,
    technical_report_search_evidence_closure_payload,
)
from app.services.quality import list_quality_eval_candidates
from app.services.search import execute_search, get_search_harness, list_search_harnesses
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_harness_optimization import run_search_harness_optimization_loop
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
from app.services.technical_reports import (
    apply_technical_report_claim_support_judgments,
    build_report_evidence_cards,
    draft_technical_report,
    evaluate_document_generation_context_pack,
    judge_technical_report_claim_support,
    plan_technical_report,
    prepare_report_agent_harness,
    task_output_context_ref,
    verify_technical_report,
)

evaluate_search_harness_verification = evaluate_search_harness_release_gate


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


def _refresh_eval_failure_cases_executor(
    session: Session,
    _task: AgentTask,
    payload: RefreshEvalFailureCasesTaskInput,
) -> dict:
    response = refresh_eval_failure_cases(
        session,
        limit=payload.limit,
        include_resolved=payload.include_resolved,
    )
    return {"refresh": jsonable_encoder(response)}


def _inspect_eval_failure_case_executor(
    session: Session,
    _task: AgentTask,
    payload: InspectEvalFailureCaseTaskInput,
) -> dict:
    response = inspect_eval_failure_case(session, payload.case_id)
    return {"inspection": jsonable_encoder(response)}


def _triage_eval_failure_case_executor(
    session: Session,
    task: AgentTask,
    payload: TriageEvalFailureCaseTaskInput,
) -> dict:
    response = triage_eval_failure_case(
        session,
        payload.case_id,
        agent_task_id=task.id,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="eval_failure_case_triage",
        payload=jsonable_encoder(response),
        storage_service=StorageService(),
        filename="eval_failure_case_triage.json",
    )
    return {
        "triage": jsonable_encoder(response),
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _harness_override_has_changes(override_spec: dict) -> bool:
    return bool(
        override_spec.get("retrieval_profile_overrides") or override_spec.get("reranker_overrides")
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
    best_override_changed = _harness_override_has_changes(optimization.best_override_spec)
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
    if not _harness_override_has_changes(best_override_spec):
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


def _plan_technical_report_executor(
    session: Session,
    task: AgentTask,
    payload: PlanTechnicalReportTaskInput,
) -> dict:
    plan_payload = plan_technical_report(
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
        artifact_kind="technical_report_plan",
        payload=plan_payload,
        storage_service=StorageService(),
        filename="technical_report_plan.json",
    )
    return {
        "plan": plan_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _unique_strings(values) -> list[str]:
    return [str(value) for value in dict.fromkeys(values) if value is not None and value != ""]


def _source_record_key(source_type, source_id) -> str | None:
    if source_type is None or source_id is None or source_id == "":
        return None
    source_type_value = str(source_type).strip().lower()
    if source_type_value not in {"chunk", "table"}:
        return None
    return f"source:{source_type_value}:{source_id}"


def _int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _source_page_span(
    *,
    document_id,
    run_id,
    page_from,
    page_to,
) -> dict | None:
    page_from_value = _int_or_none(page_from)
    if page_from_value is None or document_id is None or run_id is None:
        return None
    page_to_value = _int_or_none(page_to) or page_from_value
    return {
        "document_id": str(document_id),
        "run_id": str(run_id),
        "page_from": page_from_value,
        "page_to": page_to_value,
        "key": (f"page:{document_id}:{run_id}:{page_from_value}:{page_to_value}"),
    }


def _unique_page_spans(spans: list[dict]) -> list[dict]:
    return list({span["key"]: span for span in spans if span and span.get("key")}.values())


def _page_spans_overlap(card_span: dict, source_span: dict) -> bool:
    if card_span.get("document_id") != source_span.get("document_id") or card_span.get(
        "run_id"
    ) != source_span.get("run_id"):
        return False
    return int(card_span["page_from"]) <= int(source_span["page_to"]) and int(
        source_span["page_from"]
    ) <= int(card_span["page_to"])


def _source_export_summary(export) -> dict:
    package_payload = export.package_payload_json or {}
    search_request = package_payload.get("search_request") or {}
    source_evidence = list(package_payload.get("source_evidence") or [])
    result_payloads = list(package_payload.get("results") or [])
    source_document_run_keys = _unique_strings(
        f"{document_id}:{run_id}"
        for document_id in (export.document_ids_json or [])
        for run_id in (export.run_ids_json or [])
    )
    source_record_keys: list[str] = []
    source_page_spans: list[dict] = []
    source_results: list[dict] = []
    for source_item in source_evidence:
        document = source_item.get("document") or {}
        run = source_item.get("run") or {}
        item_record_keys: list[str] = []
        item_page_spans: list[dict] = []
        item_record_keys.append(
            _source_record_key(source_item.get("result_type"), source_item.get("source_id"))
        )
        for source_type, payload_key in (("chunk", "chunk"), ("table", "table")):
            source_payload = source_item.get(payload_key) or {}
            item_record_keys.append(_source_record_key(source_type, source_payload.get("id")))
            item_page_spans.append(
                _source_page_span(
                    document_id=source_payload.get("document_id") or document.get("id"),
                    run_id=source_payload.get("run_id") or run.get("id"),
                    page_from=source_payload.get("page_from"),
                    page_to=source_payload.get("page_to"),
                )
            )
        for span in source_item.get("retrieval_evidence_spans") or []:
            item_record_keys.append(
                _source_record_key(span.get("source_type"), span.get("source_id"))
            )
            item_page_spans.append(
                _source_page_span(
                    document_id=document.get("id"),
                    run_id=run.get("id"),
                    page_from=span.get("page_from"),
                    page_to=span.get("page_to"),
                )
            )
        item_record_keys = _unique_strings(item_record_keys)
        item_page_spans = _unique_page_spans(item_page_spans)
        source_record_keys.extend(item_record_keys)
        source_page_spans.extend(item_page_spans)
        if source_item.get("search_request_result_id"):
            source_results.append(
                {
                    "search_request_result_id": str(source_item["search_request_result_id"]),
                    "source_record_keys": item_record_keys,
                    "source_page_spans": item_page_spans,
                }
            )
    if not source_results:
        source_results = [
            {
                "search_request_result_id": str(result["search_request_result_id"]),
                "source_record_keys": [],
                "source_page_spans": [],
            }
            for result in result_payloads
            if result.get("search_request_result_id")
        ]
    return {
        "evidence_package_export_id": str(export.id),
        "search_request_id": str(export.search_request_id) if export.search_request_id else None,
        "package_sha256": export.package_sha256,
        "trace_sha256": export.trace_sha256,
        "query_text": search_request.get("query_text"),
        "mode": search_request.get("mode"),
        "document_ids": [str(value) for value in export.document_ids_json or []],
        "run_ids": [str(value) for value in export.run_ids_json or []],
        "source_document_run_keys": source_document_run_keys,
        "source_record_keys": _unique_strings(source_record_keys),
        "source_page_spans": _unique_page_spans(source_page_spans),
        "source_search_request_result_ids": _unique_strings(
            result.get("search_request_result_id") for result in source_results
        ),
        "source_results": source_results,
        "source_result_count": len(source_evidence),
    }


def _card_document_run_keys(card: dict) -> list[str]:
    document_ids = _unique_strings(
        [card.get("document_id"), *(card.get("source_document_ids") or [])]
    )
    run_ids = _unique_strings([card.get("run_id")])
    if not run_ids:
        return []
    return [f"{document_id}:{run_id}" for document_id in document_ids for run_id in run_ids]


def _card_source_record_keys(card: dict) -> list[str]:
    metadata = card.get("metadata") or {}
    source_type = str(card.get("source_type") or "").strip().lower()
    source_record_keys: list[str] = [
        _source_record_key("chunk", card.get("chunk_id") or metadata.get("chunk_id")),
        _source_record_key("table", card.get("table_id") or metadata.get("table_id")),
    ]
    if source_type in {"chunk", "table"}:
        source_record_keys.append(
            _source_record_key(
                source_type,
                card.get("source_locator") or metadata.get("source_locator"),
            )
        )
    return _unique_strings(source_record_keys)


def _card_requires_source_match(card: dict) -> bool:
    source_type = str(card.get("source_type") or "").strip().lower()
    evidence_kind = str(card.get("evidence_kind") or "").strip().lower()
    return (
        source_type in {"chunk", "table", "figure"}
        or evidence_kind in {"source_evidence", "semantic_fact"}
        or bool(card.get("evidence_ids"))
    )


def _card_page_span(card: dict) -> dict | None:
    return _source_page_span(
        document_id=card.get("document_id"),
        run_id=card.get("run_id"),
        page_from=card.get("page_from"),
        page_to=card.get("page_to"),
    )


def _match_card_source_exports(
    card: dict,
    search_export_summaries: list[dict],
) -> tuple[str, list[dict], list[str]]:
    source_record_keys = set(_card_source_record_keys(card))
    if source_record_keys:
        matched_summaries: list[dict] = []
        matched_keys: list[str] = []
        for summary in search_export_summaries:
            summary_keys = set(summary.get("source_record_keys") or [])
            overlap = sorted(source_record_keys & summary_keys)
            if overlap:
                matched_summaries.append(summary)
                matched_keys.extend(overlap)
        if matched_summaries:
            return "matched_source_record", matched_summaries, _unique_strings(matched_keys)

    card_page_span = _card_page_span(card)
    if card_page_span:
        matched_summaries = []
        matched_keys = []
        for summary in search_export_summaries:
            overlapping_source_spans = [
                span
                for span in summary.get("source_page_spans") or []
                if _page_spans_overlap(card_page_span, span)
            ]
            if overlapping_source_spans:
                matched_summaries.append(summary)
                matched_keys.extend(span["key"] for span in overlapping_source_spans)
        if matched_summaries:
            return "matched_page_span", matched_summaries, _unique_strings(matched_keys)

    if not source_record_keys and not card_page_span:
        matched_summaries = []
        for key in _card_document_run_keys(card):
            matched_summaries.extend(
                summary
                for summary in search_export_summaries
                if key in (summary.get("source_document_run_keys") or [])
            )
        if matched_summaries:
            return "matched_document_run_fallback", matched_summaries, _card_document_run_keys(card)

    return "missing", [], []


def _aggregate_source_match_status(statuses: list[str]) -> str | None:
    unique_statuses = _unique_strings(statuses)
    if not unique_statuses:
        return None
    status_order = {
        "missing": 0,
        "matched_document_run_fallback": 1,
        "matched_page_span": 2,
        "matched_source_record": 3,
    }
    return min(unique_statuses, key=lambda status: status_order.get(status, -1))


def _card_targeted_query(card: dict) -> str | None:
    excerpt = str(card.get("excerpt") or "").strip()
    if excerpt:
        return " ".join(excerpt.split())[:1000]
    matched_terms = (card.get("metadata") or {}).get("matched_terms") or []
    query = " ".join(_unique_strings(matched_terms)).strip()
    return query[:1000] or None


def _attach_source_exports_to_evidence_bundle(
    evidence_bundle: dict,
    search_export_summaries: list[dict],
) -> None:
    def matched_result_ids(card: dict, summaries: list[dict]) -> list[str]:
        card_source_record_keys = set(_card_source_record_keys(card))
        card_page_span = _card_page_span(card)
        result_ids: list[str] = []
        for summary in summaries:
            for result in summary.get("source_results") or []:
                result_id = result.get("search_request_result_id")
                if not result_id:
                    continue
                result_record_keys = set(result.get("source_record_keys") or [])
                result_page_spans = list(result.get("source_page_spans") or [])
                if card_source_record_keys and card_source_record_keys & result_record_keys:
                    result_ids.append(result_id)
                    continue
                if card_page_span and any(
                    _page_spans_overlap(card_page_span, span) for span in result_page_spans
                ):
                    result_ids.append(result_id)
                    continue
                if not card_source_record_keys and not card_page_span:
                    result_ids.append(result_id)
        return _unique_strings(result_ids)

    cards_by_id: dict[str, dict] = {}
    for card in evidence_bundle.get("evidence_cards") or []:
        source_match_status, matched_summaries, source_match_keys = _match_card_source_exports(
            card,
            search_export_summaries,
        )
        matched_summaries = list(
            {
                summary["evidence_package_export_id"]: summary for summary in matched_summaries
            }.values()
        )
        card["source_search_request_ids"] = _unique_strings(
            summary.get("search_request_id") for summary in matched_summaries
        )
        card["source_search_request_result_ids"] = matched_result_ids(
            card,
            matched_summaries,
        )
        card["source_evidence_package_export_ids"] = _unique_strings(
            summary.get("evidence_package_export_id") for summary in matched_summaries
        )
        card["source_evidence_package_sha256s"] = _unique_strings(
            summary.get("package_sha256") for summary in matched_summaries
        )
        card["source_evidence_trace_sha256s"] = _unique_strings(
            summary.get("trace_sha256") for summary in matched_summaries
        )
        card["source_evidence_match_keys"] = source_match_keys
        card["source_evidence_match_status"] = source_match_status
        card_metadata = dict(card.get("metadata") or {})
        card_metadata["source_record_keys"] = _card_source_record_keys(card)
        card_metadata["source_page_span"] = _card_page_span(card)
        card["metadata"] = card_metadata
        cards_by_id[str(card.get("evidence_card_id"))] = card

    for claim in evidence_bundle.get("claim_evidence_map") or []:
        claim_cards = [
            cards_by_id[card_id]
            for card_id in _unique_strings(claim.get("evidence_card_ids") or [])
            if card_id in cards_by_id
        ]
        claim["source_search_request_ids"] = _unique_strings(
            value for card in claim_cards for value in (card.get("source_search_request_ids") or [])
        )
        claim["source_search_request_result_ids"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_search_request_result_ids") or [])
        )
        claim["source_evidence_package_export_ids"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_package_export_ids") or [])
        )
        claim["source_evidence_package_sha256s"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_package_sha256s") or [])
        )
        claim["source_evidence_trace_sha256s"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_trace_sha256s") or [])
        )
        claim["source_evidence_match_keys"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_match_keys") or [])
        )
        claim["source_evidence_match_status"] = _aggregate_source_match_status(
            [
                card.get("source_evidence_match_status")
                for card in claim_cards
                if _card_requires_source_match(card)
                if card.get("source_evidence_match_status")
            ]
        )

    evidence_bundle["search_evidence_package_exports"] = search_export_summaries


def _freeze_report_retrieval_evidence(
    session: Session,
    *,
    task_id: UUID,
    evidence_bundle: dict,
) -> list[dict]:
    summaries: list[dict] = []
    seen_search_keys: set[tuple[str, str | None, str | None]] = set()
    for retrieval_row in evidence_bundle.get("retrieval_index") or []:
        document_ids = _unique_strings(retrieval_row.get("document_ids") or [])
        for query in _unique_strings(retrieval_row.get("queries") or []):
            for document_id in document_ids:
                search_key = (query, document_id, None)
                if search_key in seen_search_keys:
                    continue
                seen_search_keys.add(search_key)
                execution = execute_search(
                    session,
                    SearchRequest(
                        query=query,
                        mode="keyword",
                        filters=SearchFilters(document_id=UUID(document_id)),
                        limit=5,
                    ),
                    origin="agent_task_report_retrieval",
                )
                if execution.request_id is None:
                    continue
                export = persist_search_evidence_package_export(
                    session,
                    search_request_id=execution.request_id,
                    agent_task_id=task_id,
                )
                summaries.append(_source_export_summary(export))
    for card in evidence_bundle.get("evidence_cards") or []:
        source_type = str(card.get("source_type") or "").strip().lower()
        if source_type not in {"chunk", "table"}:
            continue
        document_id = str(card.get("document_id") or "")
        if not document_id:
            continue
        query = _card_targeted_query(card)
        if not query:
            continue
        search_key = (query, document_id, source_type)
        if search_key in seen_search_keys:
            continue
        seen_search_keys.add(search_key)
        execution = execute_search(
            session,
            SearchRequest(
                query=query,
                mode="keyword",
                filters=SearchFilters(
                    document_id=UUID(document_id),
                    result_type=source_type,
                ),
                limit=10,
            ),
            origin="agent_task_report_source_card_retrieval",
        )
        if execution.request_id is None:
            continue
        export = persist_search_evidence_package_export(
            session,
            search_request_id=execution.request_id,
            agent_task_id=task_id,
        )
        summaries.append(_source_export_summary(export))
    _attach_source_exports_to_evidence_bundle(evidence_bundle, summaries)
    return summaries


def _build_report_evidence_cards_executor(
    session: Session,
    task: AgentTask,
    payload: BuildReportEvidenceCardsTaskInput,
) -> dict:
    plan_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="plan_technical_report",
        expected_schema_name="plan_technical_report_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Evidence-card construction must declare the report plan as a target_task dependency."
        ),
        rerun_message=(
            "Technical report plan must be rerun after the context migration "
            "before evidence cards can be built."
        ),
    )
    plan_output = PlanTechnicalReportTaskOutput.model_validate(plan_context.output)
    evidence_bundle = build_report_evidence_cards(
        plan_output.plan.model_dump(mode="json"),
        plan_task_id=payload.target_task_id,
    )
    search_evidence_exports = _freeze_report_retrieval_evidence(
        session,
        task_id=task.id,
        evidence_bundle=evidence_bundle,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="technical_report_evidence_cards",
        payload=evidence_bundle,
        storage_service=StorageService(),
        filename="technical_report_evidence_cards.json",
    )
    return {
        "evidence_bundle": evidence_bundle,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "search_evidence_package_export_count": len(search_evidence_exports),
    }


def _prepare_report_agent_harness_executor(
    session: Session,
    task: AgentTask,
    payload: PrepareReportAgentHarnessTaskInput,
) -> dict:
    evidence_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="build_report_evidence_cards",
        expected_schema_name="build_report_evidence_cards_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Report harness packaging must declare the evidence-card task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Report evidence cards must be rerun after the context migration "
            "before harness packaging."
        ),
    )
    evidence_output = BuildReportEvidenceCardsTaskOutput.model_validate(evidence_context.output)
    upstream_context_refs = [
        task_output_context_ref(
            ref_key="evidence_cards_task_output",
            summary="Typed evidence-card bundle consumed by this report harness.",
            task_id=evidence_context.task_id,
            schema_name=evidence_context.output_schema_name,
            schema_version=evidence_context.output_schema_version,
            output=evidence_context.output,
            source_updated_at=evidence_context.task_updated_at,
            freshness_status=evidence_context.freshness_status,
        ),
        *evidence_context.refs,
    ]
    harness_payload = prepare_report_agent_harness(
        evidence_output.evidence_bundle.model_dump(mode="json"),
        harness_task_id=task.id,
        evidence_task_id=payload.target_task_id,
        upstream_context_refs=upstream_context_refs,
    )
    context_pack_payload = harness_payload["document_generation_context_pack"]
    storage_service = StorageService()
    context_pack_artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="document_generation_context_pack",
        payload=context_pack_payload,
        storage_service=storage_service,
        filename="document_generation_context_pack.json",
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="report_agent_harness",
        payload=harness_payload,
        storage_service=storage_service,
        filename="report_agent_harness.json",
    )
    return {
        "harness": harness_payload,
        "context_pack": context_pack_payload,
        "context_pack_artifact_id": str(context_pack_artifact.id),
        "context_pack_artifact_kind": context_pack_artifact.artifact_kind,
        "context_pack_artifact_path": context_pack_artifact.storage_path,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _evaluate_document_generation_context_pack_executor(
    session: Session,
    task: AgentTask,
    payload: EvaluateDocumentGenerationContextPackTaskInput,
) -> dict:
    harness_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_report_agent_harness",
        expected_schema_name="prepare_report_agent_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Context-pack evaluation must declare the report harness as a target_task dependency."
        ),
        rerun_message=(
            "Report agent harness must be rerun after the context-pack migration "
            "before evaluation."
        ),
    )
    harness_output = PrepareReportAgentHarnessTaskOutput.model_validate(harness_context.output)
    context_pack_payload = (
        harness_output.context_pack.model_dump(mode="json")
        if harness_output.context_pack is not None
        else (
            harness_output.harness.document_generation_context_pack.model_dump(mode="json")
            if harness_output.harness.document_generation_context_pack is not None
            else {}
        )
    )
    if not context_pack_payload:
        raise ValueError(
            "Report harness did not include a document_generation_context_pack; rerun the "
            "prepare_report_agent_harness task."
        )
    evaluation_payload = evaluate_document_generation_context_pack(
        context_pack_payload,
        target_task_id=payload.target_task_id,
        min_traceable_claim_ratio=payload.min_traceable_claim_ratio,
        min_context_ref_count=payload.min_context_ref_count,
        max_blocked_step_count=payload.max_blocked_step_count,
        require_source_evidence_packages=payload.require_source_evidence_packages,
        require_fresh_context=payload.require_fresh_context,
    )
    verification = create_agent_task_verification_record(
        session,
        target_task_id=payload.target_task_id,
        verification_task_id=task.id,
        verifier_type="document_generation_context_pack_gate",
        outcome=evaluation_payload["gate_outcome"],
        metrics=evaluation_payload["summary"],
        reasons=evaluation_payload["reasons"],
        details={
            "thresholds": evaluation_payload["thresholds"],
            "checks": evaluation_payload["checks"],
            "trace": evaluation_payload["trace"],
            "context_pack_sha256": evaluation_payload["context_pack_sha256"],
        },
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="document_generation_context_pack_evaluation",
        operator_version="v1",
        agent_task_id=task.id,
        config=evaluation_payload["thresholds"],
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "harness_task_type": harness_context.task_type,
            "context_pack_sha256": evaluation_payload["context_pack_sha256"],
        },
        output_payload=evaluation_payload,
        metrics=evaluation_payload["summary"],
        metadata={
            "audit_role": (
                "records pre-generation quality evaluation for the document generation "
                "context pack"
            ),
        },
        inputs=[
            {
                "input_kind": "document_generation_context_pack",
                "source_table": "agent_tasks",
                "source_id": payload.target_task_id,
                "payload": {
                    "context_pack_sha256": evaluation_payload["context_pack_sha256"],
                    "context_pack_id": evaluation_payload["context_pack_id"],
                },
            }
        ],
        outputs=[
            {
                "output_kind": "document_generation_context_pack_evaluation",
                "target_table": "agent_task_verifications",
                "target_id": verification.verification_id,
                "payload": {
                    "outcome": verification.outcome,
                    "failed_check_count": evaluation_payload["summary"].get(
                        "failed_check_count",
                    ),
                },
            }
        ],
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="document_generation_context_pack_evaluation",
        payload=evaluation_payload,
        storage_service=StorageService(),
        filename="document_generation_context_pack_evaluation.json",
    )
    return {
        "harness": harness_output.harness.model_dump(mode="json"),
        "context_pack": context_pack_payload,
        "evaluation": evaluation_payload,
        "verification": verification.model_dump(mode="json"),
        "context_pack_artifact_id": (
            str(harness_output.context_pack_artifact_id)
            if harness_output.context_pack_artifact_id is not None
            else None
        ),
        "context_pack_artifact_kind": harness_output.context_pack_artifact_kind,
        "context_pack_artifact_path": harness_output.context_pack_artifact_path,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }


def _context_pack_sha256_from_harness_output(
    harness_output: PrepareReportAgentHarnessTaskOutput,
) -> str | None:
    if harness_output.context_pack is not None:
        return harness_output.context_pack.context_pack_sha256
    if harness_output.harness.document_generation_context_pack is not None:
        return harness_output.harness.document_generation_context_pack.context_pack_sha256
    return None


def _require_passed_context_pack_gate(
    session: Session,
    *,
    harness_task_id: UUID,
    harness_output: PrepareReportAgentHarnessTaskOutput,
) -> AgentTaskVerification:
    latest_gate = session.scalar(
        select(AgentTaskVerification)
        .where(
            AgentTaskVerification.target_task_id == harness_task_id,
            AgentTaskVerification.verifier_type == DOCUMENT_GENERATION_CONTEXT_PACK_GATE,
        )
        .order_by(
            AgentTaskVerification.created_at.desc(),
            AgentTaskVerification.id.desc(),
        )
    )
    if latest_gate is None:
        raise ValueError(
            "Technical report drafting requires a passed "
            "evaluate_document_generation_context_pack task for the report harness."
        )
    if latest_gate.outcome != "passed":
        raise ValueError(
            "Technical report drafting requires the latest context-pack gate to pass; "
            f"latest outcome was '{latest_gate.outcome}'."
        )
    if latest_gate.verification_task_id is None:
        raise ValueError(
            "Technical report drafting requires a context-pack gate linked to its "
            "evaluation task."
        )
    evaluation_task = session.get(AgentTask, latest_gate.verification_task_id)
    if (
        evaluation_task is None
        or evaluation_task.task_type != "evaluate_document_generation_context_pack"
    ):
        raise ValueError(
            "Technical report drafting requires a valid "
            "evaluate_document_generation_context_pack verifier task."
        )
    if evaluation_task.status != "completed":
        raise ValueError(
            "Technical report drafting requires a completed context-pack evaluation task."
        )
    expected_sha = _context_pack_sha256_from_harness_output(harness_output)
    observed_sha = (latest_gate.details_json or {}).get("context_pack_sha256")
    if expected_sha and observed_sha != expected_sha:
        raise ValueError(
            "Technical report drafting requires the passed context-pack gate to match "
            "the current report harness context_pack_sha256."
        )
    return latest_gate


def _draft_technical_report_executor(
    session: Session,
    task: AgentTask,
    payload: DraftTechnicalReportTaskInput,
) -> dict:
    harness_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_report_agent_harness",
        expected_schema_name="prepare_report_agent_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Technical report drafting must declare the report harness as a target_task dependency."
        ),
        rerun_message=(
            "Report agent harness must be rerun after the context migration before drafting."
        ),
    )
    harness_output = PrepareReportAgentHarnessTaskOutput.model_validate(harness_context.output)
    context_pack_gate = _require_passed_context_pack_gate(
        session,
        harness_task_id=payload.target_task_id,
        harness_output=harness_output,
    )
    draft_payload = draft_technical_report(
        harness_output.harness.model_dump(mode="json"),
        harness_task_id=payload.target_task_id,
        generator_mode=payload.generator_mode,
        generator_model=payload.generator_model,
        llm_draft_markdown=payload.llm_draft_markdown,
    )
    draft_payload["llm_adapter_contract"] = {
        **(draft_payload.get("llm_adapter_contract") or {}),
        "context_pack_gate": {
            "verification_id": str(context_pack_gate.id),
            "verification_task_id": str(context_pack_gate.verification_task_id),
            "outcome": context_pack_gate.outcome,
            "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                "context_pack_sha256"
            ),
        },
    }
    storage_service = StorageService()
    markdown_path = storage_service.get_agent_task_dir(task.id) / "technical_report_draft.md"
    markdown_path.write_text(draft_payload["markdown"])
    draft_payload["markdown_path"] = str(markdown_path)
    support_judgments_payload = judge_technical_report_claim_support(draft_payload)
    support_operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="technical_report_claim_support_judge",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "judge_kind": support_judgments_payload.get("judge_kind"),
            "min_support_score": support_judgments_payload.get("min_support_score"),
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "harness_task_type": harness_context.task_type,
            "claim_count": len(draft_payload.get("claims") or []),
            "evidence_card_count": len(draft_payload.get("evidence_cards") or []),
            "claims": [
                {
                    "claim_id": claim.get("claim_id"),
                    "rendered_text": claim.get("rendered_text"),
                    "evidence_card_ids": claim.get("evidence_card_ids") or [],
                    "graph_edge_ids": claim.get("graph_edge_ids") or [],
                    "source_search_request_result_ids": (
                        claim.get("source_search_request_result_ids") or []
                    ),
                }
                for claim in draft_payload.get("claims") or []
            ],
        },
        output_payload=support_judgments_payload,
        metrics={
            "claim_count": support_judgments_payload.get("claim_count", 0),
            "supported_claim_count": support_judgments_payload.get(
                "supported_claim_count",
                0,
            ),
            "unsupported_claim_count": support_judgments_payload.get(
                "unsupported_claim_count",
                0,
            ),
            "insufficient_evidence_claim_count": support_judgments_payload.get(
                "insufficient_evidence_claim_count",
                0,
            ),
        },
        metadata={
            "audit_role": (
                "records deterministic claim-level support judgments before "
                "technical report evidence is frozen"
            ),
        },
        inputs=[
            {
                "input_kind": "technical_report_claims_pending_support_judgment",
                "source_table": "agent_tasks",
                "source_id": task.id,
                "payload": {
                    "claim_count": len(draft_payload.get("claims") or []),
                    "evidence_card_count": len(draft_payload.get("evidence_cards") or []),
                },
            }
        ],
        outputs=[
            {
                "output_kind": "technical_report_claim_support_judgments",
                "target_table": "technical_report_claims",
                "payload": {
                    "supported_claim_count": support_judgments_payload.get(
                        "supported_claim_count",
                        0,
                    ),
                    "unsupported_claim_count": support_judgments_payload.get(
                        "unsupported_claim_count",
                        0,
                    ),
                    "insufficient_evidence_claim_count": support_judgments_payload.get(
                        "insufficient_evidence_claim_count",
                        0,
                    ),
                },
            }
        ],
    )
    apply_technical_report_claim_support_judgments(
        draft_payload,
        support_judgments_payload,
        support_judge_run_id=support_operator_run.id if support_operator_run is not None else None,
    )
    evidence_export = persist_technical_report_evidence_export(
        session,
        draft_payload=draft_payload,
        agent_task_id=task.id,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="technical_report_draft",
        payload=draft_payload,
        storage_service=storage_service,
        filename="technical_report_draft.json",
    )
    attach_artifact_to_evidence_export(
        session,
        evidence_package_export_id=evidence_export.id,
        agent_task_artifact_id=artifact.id,
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="generate",
        operator_name="technical_report_draft",
        operator_version="v1",
        agent_task_id=task.id,
        model_name=payload.generator_model,
        config={
            "generator_mode": payload.generator_mode,
            "llm_adapter_contract": draft_payload.get("llm_adapter_contract", {}),
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "harness_task_type": harness_context.task_type,
            "context_pack_gate_verification_id": str(context_pack_gate.id),
            "context_pack_gate_task_id": str(context_pack_gate.verification_task_id),
            "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                "context_pack_sha256"
            ),
            "claim_contract_count": len(
                harness_output.harness.model_dump(mode="json").get("claim_contract") or []
            ),
        },
        output_payload={
            "artifact_id": str(artifact.id),
            "artifact_kind": artifact.artifact_kind,
            "artifact_path": artifact.storage_path,
            "claim_count": len(draft_payload.get("claims") or []),
            "blocked_claim_count": len(draft_payload.get("blocked_claims") or []),
            "evidence_package_export_id": str(evidence_export.id),
            "evidence_package_sha256": evidence_export.package_sha256,
        },
        metrics={
            "claim_count": len(draft_payload.get("claims") or []),
            "blocked_claim_count": len(draft_payload.get("blocked_claims") or []),
            "evidence_card_count": len(draft_payload.get("evidence_cards") or []),
            "claim_derivation_count": len(draft_payload.get("claim_derivations") or []),
        },
        metadata={
            "audit_role": "records the report generation activity and its source harness",
            "evidence_package_export_id": str(evidence_export.id),
        },
        inputs=[
            {
                "input_kind": "report_agent_harness",
                "source_table": "agent_tasks",
                "source_id": payload.target_task_id,
                "payload": {
                    "target_task_type": harness_context.task_type,
                    "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                        "context_pack_sha256"
                    ),
                },
            },
            {
                "input_kind": "document_generation_context_pack_gate",
                "source_table": "agent_task_verifications",
                "source_id": context_pack_gate.id,
                "payload": {
                    "verification_task_id": str(context_pack_gate.verification_task_id),
                    "outcome": context_pack_gate.outcome,
                    "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                        "context_pack_sha256"
                    ),
                },
            }
        ],
        outputs=[
            {
                "output_kind": "technical_report_draft",
                "target_table": "agent_task_artifacts",
                "target_id": artifact.id,
                "artifact_path": artifact.storage_path,
                "payload": {
                    "claim_count": len(draft_payload.get("claims") or []),
                    "markdown_path": draft_payload.get("markdown_path"),
                    "evidence_package_sha256": evidence_export.package_sha256,
                },
            }
        ],
    )
    if operator_run is not None:
        attach_operator_run_to_evidence_export(
            session,
            evidence_package_export_id=evidence_export.id,
            operator_run_id=operator_run.id,
        )
    if support_operator_run is not None:
        attach_operator_run_to_evidence_export(
            session,
            evidence_package_export_id=evidence_export.id,
            operator_run_id=support_operator_run.id,
        )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "evidence_package_export_id": str(evidence_export.id),
        "evidence_package_sha256": evidence_export.package_sha256,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
        "support_judge_run_id": str(support_operator_run.id)
        if support_operator_run is not None
        else None,
        "context_pack_evaluation_task_id": str(context_pack_gate.verification_task_id),
        "context_pack_verification_id": str(context_pack_gate.id),
        "context_pack_sha256": (context_pack_gate.details_json or {}).get("context_pack_sha256"),
    }


def _verify_technical_report_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyTechnicalReportTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_technical_report",
        expected_schema_name="draft_technical_report_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Technical report verification must declare the report draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Technical report draft must be rerun after the context migration before verification."
        ),
    )
    draft_output = DraftTechnicalReportTaskOutput.model_validate(draft_context.output)
    draft_payload = draft_output.draft.model_dump(mode="json")
    draft_payload["llm_adapter_contract"] = {
        **(draft_payload.get("llm_adapter_contract") or {}),
        "harness_context_refs": [ref.model_dump(mode="json") for ref in draft_context.refs],
    }
    outcome = verify_technical_report(
        draft_payload,
        max_unsupported_claim_count=payload.max_unsupported_claim_count,
        require_full_claim_traceability=payload.require_full_claim_traceability,
        require_full_concept_coverage=payload.require_full_concept_coverage,
        require_graph_edges_approved=payload.require_graph_edges_approved,
        block_stale_context=payload.block_stale_context,
        require_claim_support_judgments=payload.require_claim_support_judgments,
        min_claim_support_score=payload.min_claim_support_score,
    )
    source_evidence_closure = technical_report_search_evidence_closure_payload(
        session,
        draft_payload,
    )
    summary = {
        **outcome.summary,
        "source_evidence_package_export_count": source_evidence_closure[
            "expected_source_evidence_package_export_count"
        ],
        "source_evidence_package_trace_complete_count": source_evidence_closure[
            "trace_complete_count"
        ],
        "source_evidence_package_trace_incomplete_count": source_evidence_closure[
            "incomplete_trace_count"
        ],
        "claims_missing_source_evidence_package_export_count": source_evidence_closure[
            "claims_missing_source_evidence_package_export_count"
        ],
        "cited_cards_without_acceptable_source_evidence_match_count": (
            source_evidence_closure["cited_cards_without_acceptable_source_evidence_match_count"]
        ),
        "cited_cards_with_document_run_fallback_match_count": source_evidence_closure[
            "cited_cards_with_document_run_fallback_match_count"
        ],
        "cited_cards_without_recomputed_source_coverage_count": source_evidence_closure[
            "cited_cards_without_recomputed_source_coverage_count"
        ],
        "cited_cards_with_expected_record_without_recomputed_record_match_count": (
            source_evidence_closure[
                "cited_cards_with_expected_record_without_recomputed_record_match_count"
            ]
        ),
        "reported_recomputed_match_mismatch_count": source_evidence_closure[
            "reported_recomputed_match_mismatch_count"
        ],
        "source_record_recall": source_evidence_closure["source_record_recall"],
        "source_evidence_closure_complete": source_evidence_closure["complete"],
    }
    reasons = list(outcome.verification_reasons)
    if payload.require_frozen_source_evidence and not source_evidence_closure["complete"]:
        reasons.append(
            "Every generated claim must be backed by frozen search evidence packages "
            "with complete persisted trace integrity and source-record or page-span "
            "coverage."
        )
    verification_outcome = "failed" if reasons else "passed"
    success_metrics = [
        *outcome.success_metrics,
        {
            "metric_key": "source_evidence_closure",
            "stakeholder": "Luc Moreau / James Cheney",
            "passed": source_evidence_closure["complete"],
            "summary": (
                "Every generated claim is linked to frozen retrieval evidence with "
                "persisted trace integrity."
            ),
            "details": {
                "source_evidence_package_export_count": source_evidence_closure[
                    "expected_source_evidence_package_export_count"
                ],
                "trace_complete_count": source_evidence_closure["trace_complete_count"],
                "incomplete_trace_count": source_evidence_closure["incomplete_trace_count"],
                "weak_source_match_count": source_evidence_closure[
                    "cited_cards_without_acceptable_source_evidence_match_count"
                ],
                "recomputed_source_coverage_gap_count": source_evidence_closure[
                    "cited_cards_without_recomputed_source_coverage_count"
                ],
                "source_record_recall": source_evidence_closure["source_record_recall"],
            },
        },
    ]
    details = {
        **outcome.verification_details,
        "target_task_id": str(draft_context.task_id),
        "target_task_type": draft_context.task_type,
        "source_evidence_closure": source_evidence_closure,
    }
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=task.id,
        verifier_type="technical_report_gate",
        outcome=verification_outcome,
        metrics=summary,
        reasons=reasons,
        details=details,
    )
    result = {
        "draft": draft_payload,
        "summary": summary,
        "success_metrics": success_metrics,
        "verification": record.model_dump(mode="json"),
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="technical_report_verification",
        payload=result,
        storage_service=StorageService(),
        filename="technical_report_verification.json",
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="verify",
        operator_name="technical_report_gate",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            **outcome.verification_details.get("thresholds", {}),
            "require_frozen_source_evidence": payload.require_frozen_source_evidence,
            "require_claim_support_judgments": payload.require_claim_support_judgments,
            "min_claim_support_score": payload.min_claim_support_score,
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "draft_task_type": draft_context.task_type,
            "claim_count": summary.get("claim_count", 0),
        },
        output_payload={
            "verification_id": str(record.verification_id),
            "verification_outcome": verification_outcome,
            "artifact_id": str(artifact.id),
            "artifact_kind": artifact.artifact_kind,
            "artifact_path": artifact.storage_path,
        },
        metrics=summary,
        metadata={
            "verification_outcome": verification_outcome,
            "audit_role": "records the verifier gate for a generated technical report",
        },
        inputs=[
            {
                "input_kind": "technical_report_draft",
                "source_table": "agent_tasks",
                "source_id": payload.target_task_id,
                "payload": {
                    "target_task_type": draft_context.task_type,
                    "context_ref_count": outcome.summary.get("context_ref_count", 0),
                },
            }
        ],
        outputs=[
            {
                "output_kind": "technical_report_verification",
                "target_table": "agent_task_verifications",
                "target_id": record.verification_id,
                "payload": {
                    "outcome": verification_outcome,
                    "reasons": reasons,
                },
            },
            {
                "output_kind": "technical_report_verification_artifact",
                "target_table": "agent_task_artifacts",
                "target_id": artifact.id,
                "artifact_path": artifact.storage_path,
                "payload": {"artifact_kind": artifact.artifact_kind},
            },
        ],
    )
    evidence_manifest = None
    if verification_outcome == "passed":
        evidence_manifest = persist_technical_report_evidence_manifest(
            session,
            task_id=task.id,
        )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
        "evidence_manifest_id": str(evidence_manifest.id)
        if evidence_manifest is not None
        else None,
        "evidence_manifest_sha256": evidence_manifest.manifest_sha256
        if evidence_manifest is not None
        else None,
    }


def _claim_support_thresholds_payload(payload) -> dict:
    return {
        "min_overall_accuracy": payload.min_overall_accuracy,
        "min_verdict_precision": payload.min_verdict_precision,
        "min_verdict_recall": payload.min_verdict_recall,
        "min_support_score": payload.min_support_score,
    }


def _require_policy_row_matches_draft_output(
    policy_row: ClaimSupportCalibrationPolicy,
    draft_output: DraftClaimSupportCalibrationPolicyTaskOutput,
) -> None:
    if policy_row.id != draft_output.policy_id:
        raise ValueError("Draft policy row does not match the requested draft task output.")
    if policy_row.policy_name != draft_output.policy_name:
        raise ValueError("Draft policy name no longer matches the draft task output.")
    if policy_row.policy_version != draft_output.policy_version:
        raise ValueError("Draft policy version no longer matches the draft task output.")
    if policy_row.policy_sha256 != draft_output.policy_sha256:
        raise ValueError("Draft policy hash no longer matches the draft task output.")
    if dict(policy_row.policy_payload_json or {}) != dict(draft_output.policy_payload or {}):
        raise ValueError("Draft policy payload no longer matches the draft task output.")


def _draft_claim_support_calibration_policy_executor(
    session: Session,
    task: AgentTask,
    payload: DraftClaimSupportCalibrationPolicyTaskInput,
) -> dict:
    active_policy = get_active_claim_support_calibration_policy(
        session,
        policy_name=payload.policy_name,
    )
    policy_row = draft_claim_support_calibration_policy(
        session,
        policy_name=payload.policy_name,
        policy_version=payload.policy_version,
        thresholds=_claim_support_thresholds_payload(payload),
        min_hard_case_kind_count=payload.min_hard_case_kind_count,
        required_hard_case_kinds=list(payload.required_hard_case_kinds),
        required_verdicts=list(payload.required_verdicts),
        owner=payload.owner,
        source=payload.source,
        rationale=payload.rationale,
    )
    draft_payload = {
        "policy_id": str(policy_row.id),
        "policy_name": policy_row.policy_name,
        "policy_version": policy_row.policy_version,
        "policy_sha256": policy_row.policy_sha256,
        "policy_payload": policy_row.policy_payload_json,
        "active_policy_id": str(active_policy.id) if active_policy is not None else None,
        "active_policy_sha256": active_policy.policy_sha256 if active_policy is not None else None,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_calibration_policy_draft",
        payload=draft_payload,
        storage_service=StorageService(),
        filename="claim_support_calibration_policy_draft.json",
    )
    return {
        **draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _verify_claim_support_calibration_policy_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyClaimSupportCalibrationPolicyTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_claim_support_calibration_policy",
        expected_schema_name="draft_claim_support_calibration_policy_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Claim-support policy verification must declare the requested policy draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target claim-support policy draft must be rerun after the context migration "
            "before verification."
        ),
    )
    draft_output = DraftClaimSupportCalibrationPolicyTaskOutput.model_validate(
        draft_context.output
    )
    policy_row = session.get(ClaimSupportCalibrationPolicy, draft_output.policy_id)
    if policy_row is None:
        raise ValueError(f"Claim support calibration policy not found: {draft_output.policy_id}")
    _require_policy_row_matches_draft_output(policy_row, draft_output)
    if policy_row.status != "draft":
        raise ValueError("Only draft claim support calibration policies can be verified.")

    explicit_fixture_rows = [fixture.model_dump(mode="json") for fixture in payload.fixtures]
    default_fixture_rows = (
        [] if explicit_fixture_rows else default_claim_support_evaluation_fixtures()
    )
    base_fixture_rows = explicit_fixture_rows or default_fixture_rows
    mined_fixture_rows, mined_failure_manifest = mine_claim_support_failure_fixtures(
        session,
        limit=payload.mined_failure_limit if payload.include_mined_failures else 0,
        exclude_case_ids={
            str(fixture.get("case_id"))
            for fixture in base_fixture_rows
            if fixture.get("case_id")
        },
    )
    fixture_rows = [*base_fixture_rows, *mined_fixture_rows]
    mined_failure_summary_basis = {
        **mined_failure_manifest,
        "enabled": payload.include_mined_failures,
        "explicit_fixture_count": len(explicit_fixture_rows),
        "default_fixture_count": len(default_fixture_rows),
        "combined_fixture_count": len(fixture_rows),
    }
    mined_failure_summary = {
        **mined_failure_summary_basis,
        "summary_sha256": str(payload_sha256(mined_failure_summary_basis)),
    }
    fixture_set_record = ensure_claim_support_fixture_set(
        session,
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows,
        metadata={
            "source": "verify_claim_support_calibration_policy",
            "mined_failure_summary": mined_failure_summary,
        },
    )
    evaluation_payload = evaluate_claim_support_judge_fixture_set(
        evaluation_name="claim_support_calibration_policy_verification",
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows,
        calibration_policy=policy_row.policy_payload_json,
        fixture_set_id=fixture_set_record.id,
        policy_id=policy_row.id,
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="claim_support_calibration_policy_verification",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "policy_id": str(policy_row.id),
            "policy_sha256": policy_row.policy_sha256,
            "fixture_set_id": str(fixture_set_record.id),
            "fixture_set_sha256": fixture_set_record.fixture_set_sha256,
            "mined_failure_manifest_sha256": mined_failure_summary["manifest_sha256"],
            "mined_failure_summary_sha256": mined_failure_summary["summary_sha256"],
            "mined_failure_case_count": mined_failure_summary["mined_failure_case_count"],
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "policy_payload": policy_row.policy_payload_json,
            "fixture_set_name": payload.fixture_set_name,
            "fixture_set_version": payload.fixture_set_version,
            "include_mined_failures": payload.include_mined_failures,
            "mined_failure_limit": payload.mined_failure_limit,
            "mined_failure_summary": mined_failure_summary,
        },
        output_payload=evaluation_payload,
        metrics=evaluation_payload.get("summary") or {},
        metadata={"audit_role": "verifies a draft claim support calibration policy"},
        outputs=[
            {
                "output_kind": "claim_support_policy_verification",
                "target_table": "claim_support_calibration_policies",
                "target_id": str(policy_row.id),
                "payload": {
                    "gate_outcome": evaluation_payload["summary"]["gate_outcome"],
                    "policy_sha256": policy_row.policy_sha256,
                    "fixture_set_sha256": fixture_set_record.fixture_set_sha256,
                },
            }
        ],
    )
    evaluation_row = persist_claim_support_judge_evaluation(
        session,
        evaluation_payload,
        agent_task_id=task.id,
        operator_run_id=operator_run.id if operator_run is not None else None,
    )
    result_evaluation = {
        **evaluation_row.evaluation_payload_json,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    outcome = str(result_evaluation["summary"]["gate_outcome"])
    reasons = list(result_evaluation.get("reasons") or [])
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=task.id,
        verifier_type="claim_support_calibration_policy_gate",
        outcome=outcome,
        metrics=dict(result_evaluation.get("summary") or {}),
        reasons=reasons,
        details={
            "policy_id": str(policy_row.id),
            "policy_sha256": policy_row.policy_sha256,
            "fixture_set_id": str(fixture_set_record.id),
            "fixture_set_sha256": fixture_set_record.fixture_set_sha256,
            "evaluation_id": result_evaluation["evaluation_id"],
            "mined_failure_summary": mined_failure_summary,
        },
    )
    result = {
        "draft_policy": policy_row.policy_payload_json,
        "evaluation": result_evaluation,
        "verification": record.model_dump(mode="json"),
        "mined_failure_summary": mined_failure_summary,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_calibration_policy_verification",
        payload=result,
        storage_service=StorageService(),
        filename="claim_support_calibration_policy_verification.json",
    )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }


def _apply_claim_support_calibration_policy_executor(
    session: Session,
    task: AgentTask,
    payload: ApplyClaimSupportCalibrationPolicyTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_claim_support_calibration_policy",
        expected_schema_name="draft_claim_support_calibration_policy_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Policy apply task must declare the requested claim-support policy draft "
            "as a draft_task dependency."
        ),
        rerun_message=(
            "Claim-support policy draft must be rerun after the context migration "
            "before it can be applied."
        ),
    )
    verification_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_claim_support_calibration_policy",
        expected_schema_name="verify_claim_support_calibration_policy_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Policy apply task must declare the requested claim-support policy verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Claim-support policy verification must be rerun after the context migration "
            "before it can be applied."
        ),
    )
    draft_output = DraftClaimSupportCalibrationPolicyTaskOutput.model_validate(
        draft_context.output
    )
    verification_output = VerifyClaimSupportCalibrationPolicyTaskOutput.model_validate(
        verification_context.output
    )
    verification = verification_output.verification
    if verification.outcome != "passed":
        raise ValueError(
            "Only passed claim-support calibration policy verifications can be applied."
        )
    if verification.target_task_id != payload.draft_task_id:
        raise ValueError(
            "Verification task does not target the requested claim-support policy draft."
        )
    if str(draft_output.policy_id) != str(verification_output.evaluation.get("policy_id")):
        raise ValueError("Verification did not evaluate the requested claim-support policy draft.")
    draft_policy = session.get(ClaimSupportCalibrationPolicy, draft_output.policy_id)
    if draft_policy is None:
        raise ValueError(f"Claim support calibration policy not found: {draft_output.policy_id}")
    _require_policy_row_matches_draft_output(draft_policy, draft_output)
    if draft_policy.status != "draft":
        raise ValueError("Only draft claim support calibration policies can be applied.")

    verification_details = dict(verification.details or {})
    verification_policy_sha256 = str(verification_details.get("policy_sha256") or "")
    evaluation_policy_sha256 = str(verification_output.evaluation.get("policy_sha256") or "")
    if verification_policy_sha256 != draft_output.policy_sha256:
        raise ValueError("Verification policy hash does not match the requested draft policy.")
    if evaluation_policy_sha256 != draft_output.policy_sha256:
        raise ValueError("Verification evaluation hash does not match the requested draft policy.")
    if dict(verification_output.draft_policy or {}) != dict(draft_output.policy_payload or {}):
        raise ValueError("Verification draft policy payload does not match the draft task output.")

    verification_evaluation_id = (
        verification_details.get("evaluation_id")
        or verification_output.evaluation.get("evaluation_id")
    )
    verification_fixture_set_id = verification_details.get("fixture_set_id")
    verification_fixture_set_sha256 = verification_details.get("fixture_set_sha256")
    verification_mined_failure_summary = dict(
        verification_output.mined_failure_summary
        or verification_details.get("mined_failure_summary")
        or {}
    )

    previous_active = get_active_claim_support_calibration_policy(
        session,
        policy_name=draft_output.policy_name,
    )
    activated_policy, retired_policies = activate_claim_support_calibration_policy(
        session,
        policy_id=draft_output.policy_id,
        activation_metadata={
            "activated_by_task_id": str(task.id),
            "verification_task_id": str(payload.verification_task_id),
            "reason": payload.reason,
        },
    )
    apply_payload = {
        "draft_task_id": str(payload.draft_task_id),
        "verification_task_id": str(payload.verification_task_id),
        "reason": payload.reason,
        "approved_by": task.approved_by,
        "approved_at": task.approved_at.isoformat() if task.approved_at else None,
        "approval_note": task.approval_note,
        "previous_active_policy_id": (
            str(previous_active.id) if previous_active is not None else None
        ),
        "previous_active_policy_sha256": (
            previous_active.policy_sha256 if previous_active is not None else None
        ),
        "activated_policy_id": str(activated_policy.id),
        "activated_policy_sha256": activated_policy.policy_sha256,
        "policy_name": activated_policy.policy_name,
        "policy_version": activated_policy.policy_version,
        "draft_policy_sha256": draft_output.policy_sha256,
        "verification_id": str(verification.verification_id),
        "verification_outcome": verification.outcome,
        "verification_reasons": list(verification.reasons),
        "verification_evaluation_id": (
            str(verification_evaluation_id) if verification_evaluation_id else None
        ),
        "verification_fixture_set_id": (
            str(verification_fixture_set_id) if verification_fixture_set_id else None
        ),
        "verification_fixture_set_sha256": (
            str(verification_fixture_set_sha256) if verification_fixture_set_sha256 else None
        ),
        "verification_policy_sha256": verification_policy_sha256,
        "verification_mined_failure_summary": verification_mined_failure_summary,
        "success_metrics": [
            {
                "metric_key": "claim_support_policy_verification_passed",
                "stakeholder": "Luc Moreau / James Cheney",
                "passed": True,
                "summary": "Only a passed verifier record can activate the calibration policy.",
                "details": {
                    "verification_task_id": str(payload.verification_task_id),
                    "verification_id": str(verification.verification_id),
                    "verification_outcome": verification.outcome,
                    "verification_policy_sha256": verification_policy_sha256,
                    "verification_fixture_set_sha256": verification_fixture_set_sha256,
                    "mined_failure_manifest_sha256": (
                        verification_mined_failure_summary.get("manifest_sha256")
                    ),
                    "mined_failure_summary_sha256": (
                        verification_mined_failure_summary.get("summary_sha256")
                    ),
                    "mined_failure_case_count": (
                        verification_mined_failure_summary.get("mined_failure_case_count")
                    ),
                },
            },
            {
                "metric_key": "claim_support_policy_single_active",
                "stakeholder": "Juan Sequeda",
                "passed": True,
                "summary": "Prior active policies for this policy name were retired.",
                "details": {
                    "policy_name": activated_policy.policy_name,
                    "retired_policy_ids": [str(row.id) for row in retired_policies],
                },
            },
        ],
    }
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="orchestrate",
        operator_name="claim_support_calibration_policy_activation",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "draft_task_id": str(payload.draft_task_id),
            "verification_task_id": str(payload.verification_task_id),
        },
        input_payload={
            "draft_policy": draft_output.policy_payload,
            "verification": verification.model_dump(mode="json"),
            "verification_mined_failure_summary": verification_mined_failure_summary,
            "reason": payload.reason,
        },
        output_payload=apply_payload,
        metrics={
            "activated_policy_id": str(activated_policy.id),
            "retired_policy_count": len(retired_policies),
        },
        metadata={"audit_role": "activates a verified claim support calibration policy"},
        outputs=[
            {
                "output_kind": "claim_support_calibration_policy_activation",
                "target_table": "claim_support_calibration_policies",
                "target_id": str(activated_policy.id),
                "payload": {
                    "policy_sha256": activated_policy.policy_sha256,
                    "previous_active_policy_id": (
                        str(previous_active.id) if previous_active is not None else None
                    ),
                },
            }
        ],
    )
    result = {
        **apply_payload,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_calibration_policy_activation",
        payload=result,
        storage_service=StorageService(),
        filename="claim_support_calibration_policy_activation.json",
    )
    governance_payload = build_claim_support_policy_activation_governance_payload(
        session,
        task=task,
        activated_policy=activated_policy,
        previous_active_policy=previous_active,
        retired_policies=retired_policies,
        verification=verification.model_dump(mode="json"),
        verification_output=verification_output.model_dump(mode="json"),
        apply_payload=result,
        activation_artifact=artifact,
        operator_run=operator_run,
    )
    governance_artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind=CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
        payload=governance_payload,
        storage_service=StorageService(),
        filename=CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_FILENAME,
    )
    governance_event = record_claim_support_policy_activation_governance_event(
        session,
        task=task,
        activated_policy=activated_policy,
        governance_artifact=governance_artifact,
        governance_payload=governance_payload,
    )
    governance_receipt = governance_payload.get("activation_governance_receipt") or {}
    governance_integrity = governance_payload.get("integrity") or {}
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "activation_governance_artifact_id": str(governance_artifact.id),
        "activation_governance_artifact_kind": governance_artifact.artifact_kind,
        "activation_governance_artifact_path": governance_artifact.storage_path,
        "activation_governance_payload_sha256": governance_payload.get(
            "activation_governance_payload_sha256"
        ),
        "activation_governance_receipt_sha256": governance_receipt.get("receipt_sha256"),
        "activation_governance_signature_status": governance_receipt.get("signature_status"),
        "activation_governance_prov_jsonld_sha256": governance_integrity.get(
            "prov_jsonld_sha256"
        ),
        "activation_governance_event_id": str(governance_event.id),
        "activation_governance_event_hash": governance_event.event_hash,
    }


def _evaluate_claim_support_judge_executor(
    session: Session,
    task: AgentTask,
    payload: EvaluateClaimSupportJudgeTaskInput,
) -> dict:
    fixture_rows = [fixture.model_dump(mode="json") for fixture in payload.fixtures]
    fixture_set_record = ensure_claim_support_fixture_set(
        session,
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows or None,
        metadata={"source": "evaluate_claim_support_judge"},
    )
    requested_thresholds = {
        "min_overall_accuracy": payload.min_overall_accuracy,
        "min_verdict_precision": payload.min_verdict_precision,
        "min_verdict_recall": payload.min_verdict_recall,
        "min_support_score": payload.min_support_score,
    }
    policy_record = resolve_claim_support_calibration_policy(
        session,
        policy_name=payload.policy_name,
        policy_version=payload.policy_version,
        thresholds=requested_thresholds,
    )
    evaluation_payload = evaluate_claim_support_judge_fixture_set(
        evaluation_name=payload.evaluation_name,
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        fixtures=fixture_rows or None,
        calibration_policy=policy_record.policy_payload_json,
        fixture_set_id=fixture_set_record.id,
        policy_id=policy_record.id,
        min_support_score=payload.min_support_score,
        min_overall_accuracy=payload.min_overall_accuracy,
        min_verdict_precision=payload.min_verdict_precision,
        min_verdict_recall=payload.min_verdict_recall,
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="technical_report_claim_support_judge_evaluation",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "evaluation_name": payload.evaluation_name,
            "fixture_set_name": payload.fixture_set_name,
            "fixture_set_version": payload.fixture_set_version,
            "fixture_set_id": str(fixture_set_record.id),
            "policy_id": str(policy_record.id),
            "policy_name": policy_record.policy_name,
            "policy_version": policy_record.policy_version,
            "policy_sha256": policy_record.policy_sha256,
            "thresholds": evaluation_payload.get("thresholds") or {},
        },
        input_payload={
            "fixture_set_name": payload.fixture_set_name,
            "fixture_set_version": payload.fixture_set_version,
            "policy_name": payload.policy_name,
            "policy_version": payload.policy_version or "active",
            "custom_fixture_count": len(payload.fixtures),
            "min_support_score": payload.min_support_score,
        },
        output_payload=evaluation_payload,
        metrics=evaluation_payload.get("summary") or {},
        metadata={
            "audit_role": ("records replay evaluation of the technical report claim support judge"),
        },
        outputs=[
            {
                "output_kind": "claim_support_judge_evaluation",
                "target_table": "claim_support_evaluations",
                "target_id": evaluation_payload["evaluation_id"],
                "payload": {
                    "gate_outcome": evaluation_payload["summary"]["gate_outcome"],
                    "case_count": evaluation_payload["summary"]["case_count"],
                    "overall_accuracy": evaluation_payload["summary"]["overall_accuracy"],
                    "fixture_set_sha256": evaluation_payload["fixture_set_sha256"],
                    "policy_sha256": evaluation_payload["policy_sha256"],
                },
            }
        ],
    )
    evaluation_row = persist_claim_support_judge_evaluation(
        session,
        evaluation_payload,
        agent_task_id=task.id,
        operator_run_id=operator_run.id if operator_run is not None else None,
    )
    result_payload = {
        **evaluation_row.evaluation_payload_json,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="claim_support_judge_evaluation",
        payload=result_payload,
        storage_service=StorageService(),
        filename="claim_support_judge_evaluation.json",
    )
    return {
        **result_payload,
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
    "plan_technical_report": AgentTaskActionDefinition(
        task_type="plan_technical_report",
        capability="technical_reports",
        definition_kind="workflow",
        description=(
            "Plan a technical report from semantic evidence, graph memory, "
            "and retrieval requirements."
        ),
        payload_model=PlanTechnicalReportTaskInput,
        executor=_plan_technical_report_executor,
        output_model=PlanTechnicalReportTaskOutput,
        output_schema_name="plan_technical_report_output",
        output_schema_version="1.0",
        input_example={
            "title": "Integration Governance Technical Report",
            "goal": "Write a technical report grounded in ingested integration evidence.",
            "audience": "Operators",
            "document_ids": ["00000000-0000-0000-0000-000000000000"],
            "target_length": "medium",
            "review_policy": "allow_candidate_with_disclosure",
        },
        context_builder_name="plan_technical_report",
    ),
    "build_report_evidence_cards": AgentTaskActionDefinition(
        task_type="build_report_evidence_cards",
        capability="technical_reports",
        definition_kind="workflow",
        description="Bind a technical report plan to typed evidence cards and graph refs.",
        payload_model=BuildReportEvidenceCardsTaskInput,
        executor=_build_report_evidence_cards_executor,
        output_model=BuildReportEvidenceCardsTaskOutput,
        output_schema_name="build_report_evidence_cards_output",
        output_schema_version="1.0",
        input_example={"target_task_id": "00000000-0000-0000-0000-000000000000"},
        context_builder_name="build_report_evidence_cards",
    ),
    "prepare_report_agent_harness": AgentTaskActionDefinition(
        task_type="prepare_report_agent_harness",
        capability="technical_reports",
        definition_kind="workflow",
        description=(
            "Package the LLM wake-up context with tools, skills, evidence cards, "
            "graph memory, and verifier gates."
        ),
        payload_model=PrepareReportAgentHarnessTaskInput,
        executor=_prepare_report_agent_harness_executor,
        output_model=PrepareReportAgentHarnessTaskOutput,
        output_schema_name="prepare_report_agent_harness_output",
        output_schema_version="1.0",
        input_example={"target_task_id": "00000000-0000-0000-0000-000000000000"},
        context_builder_name="prepare_report_agent_harness",
    ),
    "evaluate_document_generation_context_pack": AgentTaskActionDefinition(
        task_type="evaluate_document_generation_context_pack",
        capability="technical_reports",
        definition_kind="verifier",
        description=(
            "Evaluate the reusable document-generation context pack before report drafting."
        ),
        payload_model=EvaluateDocumentGenerationContextPackTaskInput,
        executor=_evaluate_document_generation_context_pack_executor,
        output_model=EvaluateDocumentGenerationContextPackTaskOutput,
        output_schema_name="evaluate_document_generation_context_pack_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "min_traceable_claim_ratio": 1.0,
            "min_context_ref_count": 1,
            "max_blocked_step_count": 0,
            "require_source_evidence_packages": True,
            "require_fresh_context": False,
        },
        context_builder_name="evaluate_document_generation_context_pack",
    ),
    "draft_technical_report": AgentTaskActionDefinition(
        task_type="draft_technical_report",
        capability="technical_reports",
        definition_kind="draft",
        description="Draft a verification-ready technical report from a report agent harness.",
        payload_model=DraftTechnicalReportTaskInput,
        executor=_draft_technical_report_executor,
        side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
        output_model=DraftTechnicalReportTaskOutput,
        output_schema_name="draft_technical_report_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "generator_mode": "structured_fallback",
        },
        context_builder_name="draft_technical_report",
    ),
    "verify_technical_report": AgentTaskActionDefinition(
        task_type="verify_technical_report",
        capability="technical_reports",
        definition_kind="verifier",
        description=(
            "Verify technical report claim traceability, graph approval, citations, "
            "and wake-up context."
        ),
        payload_model=VerifyTechnicalReportTaskInput,
        executor=_verify_technical_report_executor,
        output_model=VerifyTechnicalReportTaskOutput,
        output_schema_name="verify_technical_report_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "max_unsupported_claim_count": 0,
            "require_full_claim_traceability": True,
            "require_full_concept_coverage": True,
            "require_graph_edges_approved": True,
            "block_stale_context": False,
        },
        context_builder_name="verify_technical_report",
    ),
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
        executor=_draft_claim_support_calibration_policy_executor,
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
        executor=_verify_claim_support_calibration_policy_executor,
        output_model=VerifyClaimSupportCalibrationPolicyTaskOutput,
        output_schema_name="verify_claim_support_calibration_policy_output",
        output_schema_version="1.0",
        input_example={
            "target_task_id": "00000000-0000-0000-0000-000000000000",
            "fixture_set_name": "default_claim_support_v1",
            "fixture_set_version": "v1",
        },
        context_builder_name="generic",
    ),
    "apply_claim_support_calibration_policy": AgentTaskActionDefinition(
        task_type="apply_claim_support_calibration_policy",
        capability="technical_reports",
        definition_kind="promotion",
        description="Activate a verified claim-support calibration policy after approval.",
        payload_model=ApplyClaimSupportCalibrationPolicyTaskInput,
        executor=_apply_claim_support_calibration_policy_executor,
        side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
        requires_approval=True,
        output_model=ApplyClaimSupportCalibrationPolicyTaskOutput,
        output_schema_name="apply_claim_support_calibration_policy_output",
        output_schema_version="1.0",
        input_example={
            "draft_task_id": "00000000-0000-0000-0000-000000000000",
            "verification_task_id": "00000000-0000-0000-0000-000000000000",
            "reason": "Publish the verified claim-support calibration policy.",
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
    "optimize_search_harness_from_case": AgentTaskActionDefinition(
        task_type="optimize_search_harness_from_case",
        capability="evaluation",
        definition_kind="workflow",
        description=(
            "Run a bounded transient search-harness optimization loop from one eval failure case."
        ),
        payload_model=OptimizeSearchHarnessFromCaseTaskInput,
        executor=_optimize_search_harness_from_case_executor,
        output_model=OptimizeSearchHarnessFromCaseTaskOutput,
        output_schema_name="optimize_search_harness_from_case_output",
        output_schema_version="1.0",
        input_example={
            "case_id": "00000000-0000-0000-0000-000000000000",
            "base_harness_name": "wide_v2",
            "baseline_harness_name": "wide_v2",
            "limit": 25,
            "iterations": 2,
        },
        context_builder_name="generic",
    ),
    "draft_harness_config_update_from_optimization": AgentTaskActionDefinition(
        task_type="draft_harness_config_update_from_optimization",
        capability="retrieval",
        definition_kind="draft",
        description=(
            "Convert a completed harness optimization task into a review harness "
            "draft without changing live search behavior."
        ),
        payload_model=DraftHarnessConfigFromOptimizationTaskInput,
        executor=_draft_harness_config_from_optimization_executor,
        side_effect_level=AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
        output_model=DraftHarnessConfigUpdateTaskOutput,
        output_schema_name="draft_harness_config_update_output",
        output_schema_version="1.0",
        input_example={
            "source_task_id": "00000000-0000-0000-0000-000000000000",
            "draft_harness_name": "case_repair_review",
        },
        context_builder_name="draft_harness_config",
    ),
    "replay_search_request": AgentTaskActionDefinition(
        task_type="replay_search_request",
        capability="retrieval",
        definition_kind="action",
        description="Replay one persisted search request against the current search stack.",
        payload_model=ReplaySearchRequestTaskInput,
        executor=_replay_search_request_executor,
        output_model=ReplaySearchRequestTaskOutput,
        output_schema_name="replay_search_request_output",
        output_schema_version="1.0",
        input_example={"search_request_id": "00000000-0000-0000-0000-000000000000"},
        context_builder_name="generic",
    ),
    "run_search_replay_suite": AgentTaskActionDefinition(
        task_type="run_search_replay_suite",
        capability="retrieval",
        definition_kind="action",
        description="Run a replay suite over persisted evaluation, feedback, or gap sources.",
        payload_model=SearchReplayRunRequest,
        executor=_run_search_replay_suite_executor,
        output_model=RunSearchReplaySuiteTaskOutput,
        output_schema_name="run_search_replay_suite_output",
        output_schema_version="1.0",
        input_example={"source_type": "feedback", "limit": 12, "harness_name": "default_v1"},
        context_builder_name="generic",
    ),
    "evaluate_search_harness": AgentTaskActionDefinition(
        task_type="evaluate_search_harness",
        capability="retrieval",
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
        context_builder_name="evaluate_search_harness",
    ),
    "verify_search_harness_evaluation": AgentTaskActionDefinition(
        task_type="verify_search_harness_evaluation",
        capability="retrieval",
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
        context_builder_name="verify_search_harness_evaluation",
    ),
    "draft_harness_config_update": AgentTaskActionDefinition(
        task_type="draft_harness_config_update",
        capability="retrieval",
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
        context_builder_name="draft_harness_config",
    ),
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
    "verify_draft_harness_config": AgentTaskActionDefinition(
        task_type="verify_draft_harness_config",
        capability="retrieval",
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
            "baseline_harness_name": "wide_v2",
            "source_types": ["evaluation_queries", "feedback"],
            "limit": 12,
            "max_total_regressed_count": 0,
            "max_mrr_drop": 0.0,
            "max_zero_result_count_increase": 0,
            "max_foreign_top_result_count_increase": 0,
            "min_total_shared_query_count": 1,
        },
        context_builder_name="verify_draft_harness_config",
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
    "triage_replay_regression": AgentTaskActionDefinition(
        task_type="triage_replay_regression",
        capability="retrieval",
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
        context_builder_name="triage_replay_regression",
    ),
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
    "apply_harness_config_update": AgentTaskActionDefinition(
        task_type="apply_harness_config_update",
        capability="retrieval",
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
        context_builder_name="apply_harness_config_update",
    ),
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


def validate_agent_task_action_contracts() -> list[AgentActionContractIssue]:
    issues = validate_agent_action_contracts(
        list_agent_task_actions(),
        registry_keys=set(_ACTION_REGISTRY),
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
