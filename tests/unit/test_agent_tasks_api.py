from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


def test_agent_task_actions_route_lists_supported_actions(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.agent_tasks.list_agent_task_action_definitions",
        lambda: [
            {
                "task_type": "evaluate_search_harness",
                "capability": "retrieval",
                "description": "Compare harnesses.",
                "side_effect_level": "read_only",
                "requires_approval": False,
                "context_builder_name": "evaluate_search_harness",
                "input_schema": {},
                "output_schema_name": "evaluate_search_harness_output",
                "output_schema_version": "1.0",
                "output_schema": {"title": "EvaluateSearchHarnessOutput"},
                "input_example": {},
            }
        ],
    )

    client = TestClient(app)
    response = client.get("/agent-tasks/actions")

    assert response.status_code == 200
    assert response.json()[0]["task_type"] == "evaluate_search_harness"
    assert response.json()[0]["capability"] == "retrieval"
    assert response.json()[0]["context_builder_name"] == "evaluate_search_harness"
    assert response.json()[0]["output_schema_name"] == "evaluate_search_harness_output"


def test_agent_task_actions_route_exposes_output_schema_metadata_for_all_migrated_tasks() -> None:
    client = TestClient(app)
    response = client.get("/agent-tasks/actions")

    assert response.status_code == 200
    definitions = {row["task_type"]: row for row in response.json()}
    for task_type in [
        "get_latest_evaluation",
        "get_latest_semantic_pass",
        "initialize_workspace_ontology",
        "get_active_ontology_snapshot",
        "discover_semantic_bootstrap_candidates",
        "export_semantic_supervision_corpus",
        "evaluate_semantic_candidate_extractor",
        "build_shadow_semantic_graph",
        "evaluate_semantic_relation_extractor",
        "plan_technical_report",
        "build_report_evidence_cards",
        "prepare_report_agent_harness",
        "evaluate_document_generation_context_pack",
        "draft_technical_report",
        "verify_technical_report",
        "queue_claim_support_policy_change_impact_replay",
        "prepare_semantic_generation_brief",
        "list_quality_eval_candidates",
        "replay_search_request",
        "run_search_replay_suite",
        "evaluate_search_harness",
        "verify_search_harness_evaluation",
        "draft_harness_config_update",
        "draft_semantic_grounded_document",
        "verify_draft_harness_config",
        "verify_semantic_grounded_document",
        "triage_replay_regression",
        "triage_semantic_pass",
        "triage_semantic_candidate_disagreements",
        "triage_semantic_graph_disagreements",
        "enqueue_document_reprocess",
        "apply_harness_config_update",
        "draft_semantic_registry_update",
        "draft_ontology_extension",
        "draft_graph_promotions",
        "verify_draft_semantic_registry_update",
        "verify_draft_ontology_extension",
        "verify_draft_graph_promotions",
        "apply_semantic_registry_update",
        "apply_ontology_extension",
        "apply_graph_promotions",
        "build_document_fact_graph",
    ]:
        assert definitions[task_type]["output_schema_name"] is not None
        assert definitions[task_type]["output_schema_version"] == "1.0"
        assert definitions[task_type]["output_schema"]
        assert definitions[task_type]["capability"]
        assert definitions[task_type]["context_builder_name"]
