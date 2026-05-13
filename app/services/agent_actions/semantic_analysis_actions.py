from __future__ import annotations

from app.schemas.agent_tasks import (
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
    GetActiveOntologySnapshotTaskInput,
    GetActiveOntologySnapshotTaskOutput,
    InitializeWorkspaceOntologyTaskInput,
    InitializeWorkspaceOntologyTaskOutput,
    LatestSemanticPassTaskInput,
    LatestSemanticPassTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition, AgentTaskExecutor


def build_semantic_analysis_action_definitions(
    *,
    latest_semantic_pass_executor: AgentTaskExecutor,
    initialize_workspace_ontology_executor: AgentTaskExecutor,
    get_active_ontology_snapshot_executor: AgentTaskExecutor,
    discover_semantic_bootstrap_candidates_executor: AgentTaskExecutor,
    export_semantic_supervision_corpus_executor: AgentTaskExecutor,
    evaluate_semantic_candidate_extractor_executor: AgentTaskExecutor,
    build_shadow_semantic_graph_executor: AgentTaskExecutor,
    evaluate_semantic_relation_extractor_executor: AgentTaskExecutor,
    build_document_fact_graph_executor: AgentTaskExecutor,
) -> dict[str, AgentTaskActionDefinition]:
    return {
        "get_latest_semantic_pass": AgentTaskActionDefinition(
            task_type="get_latest_semantic_pass",
            capability="semantic_memory",
            definition_kind="action",
            description="Fetch the latest active semantic pass for one document.",
            payload_model=LatestSemanticPassTaskInput,
            executor=latest_semantic_pass_executor,
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
            description=(
                "Initialize the workspace ontology from the configured upper ontology seed."
            ),
            payload_model=InitializeWorkspaceOntologyTaskInput,
            executor=initialize_workspace_ontology_executor,
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
            executor=get_active_ontology_snapshot_executor,
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
            executor=discover_semantic_bootstrap_candidates_executor,
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
            executor=export_semantic_supervision_corpus_executor,
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
            executor=evaluate_semantic_candidate_extractor_executor,
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
            executor=build_shadow_semantic_graph_executor,
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
            executor=evaluate_semantic_relation_extractor_executor,
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
            executor=build_document_fact_graph_executor,
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
