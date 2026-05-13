from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
)
from app.schemas.agent_tasks import (
    BuildDocumentFactGraphTaskInput,
    BuildShadowSemanticGraphTaskInput,
    DiscoverSemanticBootstrapCandidatesTaskInput,
    DraftSemanticGroundedDocumentTaskInput,
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
    TriageSemanticPassTaskInput,
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
from app.services.agent_actions.semantic_governance_actions import (
    build_semantic_governance_action_definitions,
)
from app.services.agent_actions.semantic_verification_actions import (
    build_semantic_verification_action_definitions,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
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
    build_shadow_semantic_graph,
    evaluate_semantic_relation_extractor,
    triage_semantic_graph_disagreements,
)
from app.services.semantic_ontology import (
    get_active_ontology_snapshot_payload,
    initialize_workspace_ontology,
)
from app.services.semantic_orchestration import (
    build_semantic_success_metrics,
    triage_semantic_pass,
)
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
    draft_semantic_grounded_document_executor=(
        _draft_semantic_grounded_document_executor
    ),
)
_SEMANTIC_GOVERNANCE_ACTION_REGISTRY = build_semantic_governance_action_definitions()
_SEMANTIC_VERIFICATION_ACTION_REGISTRY = build_semantic_verification_action_definitions(
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
    _SEMANTIC_GOVERNANCE_ACTION_REGISTRY,
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
