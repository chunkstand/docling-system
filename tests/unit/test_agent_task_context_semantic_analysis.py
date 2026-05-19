from __future__ import annotations

from app.services.agent_task_context_semantic_analysis import (
    build_semantic_analysis_context_builders,
)
from app.services.agent_task_context_semantic_analysis_graph import (
    build_semantic_analysis_graph_context_builders,
)


def test_semantic_analysis_context_builders_include_graph_owner_registry() -> None:
    builders = build_semantic_analysis_context_builders()
    graph_builders = build_semantic_analysis_graph_context_builders()

    assert set(builders) == {
        "latest_semantic_pass",
        "initialize_workspace_ontology",
        "get_active_ontology_snapshot",
        "discover_semantic_bootstrap_candidates",
        "export_semantic_supervision_corpus",
        "evaluate_semantic_candidate_extractor",
        "build_document_fact_graph",
        "build_shadow_semantic_graph",
        "evaluate_semantic_relation_extractor",
        "triage_semantic_graph_disagreements",
    }
    for builder_name, builder in graph_builders.items():
        assert builders[builder_name] is builder
