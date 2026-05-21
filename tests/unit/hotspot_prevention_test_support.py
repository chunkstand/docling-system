from __future__ import annotations

from app.hotspot_prevention import POLICY_SCHEMA_NAME, build_hotspot_policy

EXPECTED_KNOWN_HOTSPOT_PATHS = [
    "app/api/main.py",
    "app/api/routers/agent_tasks.py",
    "app/cli.py",
    "app/cli_commands/search_harness.py",
    "app/db/models.py",
    "app/hotspot_prevention_classifier.py",
    "app/hotspot_prevention_classifier_support.py",
    "app/schemas/agent_tasks.py",
    "app/schemas/search.py",
    "app/services/agent_actions/search_harness.py",
    "app/services/agent_actions/semantic_governance_actions.py",
    "app/services/agent_task_actions.py",
    "app/services/agent_task_context.py",
    "app/services/agent_task_context_search_harness.py",
    "app/services/agent_task_context_semantic_governance.py",
    "app/services/agent_task_verifications.py",
    "app/services/agent_task_worker.py",
    "app/services/agent_tasks.py",
    "app/services/audit_bundles.py",
    "app/services/claim_support_evaluations.py",
    "app/services/claim_support_policy_governance.py",
    "app/services/claim_support_policy_impact_replay.py",
    "app/services/claim_support_policy_impact_views.py",
    "app/services/claim_support_policy_impacts.py",
    "app/services/claim_support_replay_alert_fixture_corpus.py",
    "app/services/claim_support_replay_alert_promotions.py",
    "app/services/evaluations.py",
    "app/services/evidence.py",
    "app/services/evidence_provenance_exports.py",
    "app/services/retrieval_learning_artifacts.py",
    "app/services/search.py",
    "app/services/search_harnesses.py",
    "app/services/semantic_registry.py",
    "app/services/semantics.py",
    "tests/db_model_contract.py",
    "tests/integration/retrieval_learning_ledger_support.py",
    "tests/integration/technical_report_harness_support.py",
    "tests/integration/test_claim_support_judge_evaluation_roundtrip.py",
    "tests/integration/test_retrieval_learning_ledger.py",
    "tests/integration/test_technical_report_harness_roundtrip.py",
    "tests/unit/agent_task_context_reports_claim_support_support.py",
    "tests/unit/agent_task_context_semantic_graph_promotions_support.py",
    "tests/unit/test_agent_task_context.py",
    "tests/unit/test_agent_task_context_reports_claim_support.py",
    "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
    "tests/unit/test_agent_tasks_api.py",
    "tests/unit/test_architecture_inspection.py",
    "tests/unit/test_cli.py",
    "tests/unit/test_cli_search_harness.py",
    "tests/unit/test_db_model_import_compatibility.py",
    "tests/unit/test_documents_api.py",
    "tests/unit/test_evaluation_service.py",
    "tests/unit/test_hotspot_prevention.py",
    "tests/unit/test_hotspot_prevention_policy_contracts.py",
    "tests/unit/test_search_api.py",
    "tests/unit/test_search_service.py",
]

DEFERRED_REDUCED_FACADE_PATHS = [
    "app/cli.py",
    "app/api/routers/agent_tasks.py",
    "app/hotspot_prevention_classifier.py",
    "tests/integration/test_retrieval_learning_ledger.py",
    "tests/unit/test_agent_tasks_api.py",
    "tests/unit/test_architecture_inspection.py",
    "tests/unit/test_search_api.py",
    "tests/unit/test_search_service.py",
    "tests/unit/test_documents_api.py",
    "tests/unit/test_agent_task_context_reports_claim_support.py",
    "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
    "app/services/agent_task_verifications.py",
    "app/services/agent_task_worker.py",
    "app/schemas/search.py",
    "tests/unit/test_db_model_import_compatibility.py",
    "tests/unit/test_cli_search_harness.py",
]

ACCEPTED_RESIDUAL_SUPPORT_PATHS = [
    "tests/unit/agent_task_context_reports_claim_support_support.py",
    "tests/unit/agent_task_context_semantic_graph_promotions_support.py",
]


def _diff_for(path: str, added_lines: list[str], *, deleted_lines: list[str] | None = None) -> str:
    deleted = deleted_lines or []
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(len(deleted), 1)} +1,{max(len(added_lines), 1)} @@",
    ]
    lines.extend(f"-{line}" for line in deleted)
    lines.extend(f"+{line}" for line in added_lines)
    return "\n".join(lines) + "\n"


def _policy_for(path: str, *, exceptions: list[dict] | None = None):
    return build_hotspot_policy(
        {
            "schema_name": POLICY_SCHEMA_NAME,
            "schema_version": "1.0",
            "known_hotspots": {
                path: {
                    "target_role": "compatibility facade",
                    "preferred_owner_modules": ["app/owner/"],
                    "block_new": [
                        "orm_class",
                        "private_helper",
                        "command_implementation",
                        "executor_implementation",
                        "ranking_logic",
                        "broad_new_test_group",
                        "broad_helper",
                        "artifact_assembly",
                    ],
                    "allow": [
                        "import_forwarder",
                        "alias_forwarder",
                        "explicit_forwarding_function",
                        "parser_registration",
                        "compatibility_assertion",
                        "deletion",
                    ],
                    "exceptions": exceptions or [],
                }
            },
        }
    )
