from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.schemas import agent_task_semantics as semantic_schemas
from app.schemas.agent_task_semantic_graph import (
    BuildDocumentFactGraphTaskInput,
    BuildDocumentFactGraphTaskOutput,
    BuildShadowSemanticGraphTaskInput,
    BuildShadowSemanticGraphTaskOutput,
    DiscoverSemanticBootstrapCandidatesTaskInput,
    DiscoverSemanticBootstrapCandidatesTaskOutput,
    EvaluateSemanticCandidateExtractorTaskInput,
    EvaluateSemanticCandidateExtractorTaskOutput,
    EvaluateSemanticRelationExtractorTaskInput,
    EvaluateSemanticRelationExtractorTaskOutput,
    ExportSemanticSupervisionCorpusTaskInput,
    ExportSemanticSupervisionCorpusTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.semantic_bootstrap import discover_semantic_bootstrap_candidates
from app.services.semantic_candidates import (
    evaluate_semantic_candidate_extractor,
    export_semantic_supervision_corpus,
)
from app.services.semantic_facts import build_document_fact_graph
from app.services.semantic_graph import (
    build_shadow_semantic_graph,
    evaluate_semantic_relation_extractor,
)
from app.services.semantic_ontology import (
    get_active_ontology_snapshot_payload,
    initialize_workspace_ontology,
)
from app.services.semantic_orchestration import build_semantic_success_metrics
from app.services.semantics import get_active_semantic_pass_detail
from app.services.storage import StorageService


def _latest_semantic_pass_executor(
    session: Session,
    _task: AgentTask,
    payload: semantic_schemas.LatestSemanticPassTaskInput,
) -> dict:
    response = get_active_semantic_pass_detail(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "semantic_pass": jsonable_encoder(response),
        "success_metrics": build_semantic_success_metrics(response),
    }


def _initialize_workspace_ontology_executor(
    session: Session,
    task: AgentTask,
    _payload: semantic_schemas.InitializeWorkspaceOntologyTaskInput,
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
    session: Session,
    _task: AgentTask,
    _payload: semantic_schemas.GetActiveOntologySnapshotTaskInput,
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


def build_semantic_analysis_action_definitions() -> dict[str, AgentTaskActionDefinition]:
    return {
        "get_latest_semantic_pass": AgentTaskActionDefinition(
            task_type="get_latest_semantic_pass",
            capability="semantic_memory",
            definition_kind="action",
            description="Fetch the latest active semantic pass for one document.",
            payload_model=semantic_schemas.LatestSemanticPassTaskInput,
            executor=_latest_semantic_pass_executor,
            output_model=semantic_schemas.LatestSemanticPassTaskOutput,
            output_schema_name="get_latest_semantic_pass_output",
            output_schema_version="1.0",
            input_example={"document_id": "00000000-0000-0000-0000-000000000000"},
            context_builder_name="latest_semantic_pass",
        ),
        "initialize_workspace_ontology": AgentTaskActionDefinition(
            task_type="initialize_workspace_ontology",
            capability="semantic_memory",
            definition_kind="workflow",
            description=(
                "Initialize the workspace ontology from the configured upper ontology seed."
            ),
            payload_model=semantic_schemas.InitializeWorkspaceOntologyTaskInput,
            executor=_initialize_workspace_ontology_executor,
            output_model=semantic_schemas.InitializeWorkspaceOntologyTaskOutput,
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
            payload_model=semantic_schemas.GetActiveOntologySnapshotTaskInput,
            executor=_get_active_ontology_snapshot_executor,
            output_model=semantic_schemas.GetActiveOntologySnapshotTaskOutput,
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
                "Evaluate a shadow semantic relation extractor against a "
                "deterministic graph baseline."
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
