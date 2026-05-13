from __future__ import annotations

from collections.abc import Mapping

from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    resolve_context_builder_registry,
)

SEMANTIC_CONTEXT_BUILDER_SYMBOLS = {
    "latest_semantic_pass": "_build_latest_semantic_pass_context",
    "initialize_workspace_ontology": "_build_initialize_workspace_ontology_context",
    "get_active_ontology_snapshot": "_build_get_active_ontology_snapshot_context",
    "discover_semantic_bootstrap_candidates": (
        "_build_discover_semantic_bootstrap_candidates_context"
    ),
    "export_semantic_supervision_corpus": (
        "_build_export_semantic_supervision_corpus_context"
    ),
    "evaluate_semantic_candidate_extractor": (
        "_build_evaluate_semantic_candidate_extractor_context"
    ),
    "build_shadow_semantic_graph": "_build_build_shadow_semantic_graph_context",
    "evaluate_semantic_relation_extractor": (
        "_build_evaluate_semantic_relation_extractor_context"
    ),
    "prepare_semantic_generation_brief": "_build_prepare_semantic_generation_brief_context",
    "draft_semantic_registry_update": "_build_draft_semantic_registry_update_context",
    "draft_ontology_extension": "_build_draft_ontology_extension_context",
    "draft_graph_promotions": "_build_draft_graph_promotions_context",
    "verify_draft_semantic_registry_update": (
        "_build_verify_draft_semantic_registry_update_context"
    ),
    "verify_draft_ontology_extension": "_build_verify_draft_ontology_extension_context",
    "verify_draft_graph_promotions": "_build_verify_draft_graph_promotions_context",
    "draft_semantic_grounded_document": "_build_draft_semantic_grounded_document_context",
    "verify_semantic_grounded_document": (
        "_build_verify_semantic_grounded_document_context"
    ),
    "triage_semantic_pass": "_build_triage_semantic_pass_context",
    "triage_semantic_candidate_disagreements": (
        "_build_triage_semantic_candidate_disagreements_context"
    ),
    "triage_semantic_graph_disagreements": (
        "_build_triage_semantic_graph_disagreements_context"
    ),
    "apply_semantic_registry_update": "_build_apply_semantic_registry_update_context",
    "apply_ontology_extension": "_build_apply_ontology_extension_context",
    "apply_graph_promotions": "_build_apply_graph_promotions_context",
    "build_document_fact_graph": "_build_build_document_fact_graph_context",
}


def build_semantic_context_builders(
    available_symbols: Mapping[str, object],
) -> dict[str, AgentTaskContextBuilder]:
    return resolve_context_builder_registry(
        available_symbols,
        builder_symbols=SEMANTIC_CONTEXT_BUILDER_SYMBOLS,
        registry_name="semantic",
    )
