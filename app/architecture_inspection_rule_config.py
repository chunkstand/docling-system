from __future__ import annotations

APP_ROUTE_DECORATORS = frozenset({"get", "post", "put", "delete", "patch"})
BOUNDARY_DIRS = ("app/api/routers", "app/workers")
FORBIDDEN_SERVICE_IMPORT_PREFIXES = ("app.api.main", "app.api.routers")
ALLOWED_MAIN_SERVICE_IMPORTS = frozenset({"app.services.runtime"})
FORBIDDEN_BOUNDARY_SERVICE_IMPORTS = frozenset(
    {
        "app.services.agent_task_artifacts",
        "app.services.agent_task_context",
        "app.services.agent_task_verifications",
        "app.services.agent_task_worker",
        "app.services.agent_tasks",
        "app.services.chat",
        "app.services.chunks",
        "app.services.documents",
        "app.services.eval_workbench",
        "app.services.evaluations",
        "app.services.figures",
        "app.services.runs",
        "app.services.search",
        "app.services.search_harness_evaluations",
        "app.services.search_history",
        "app.services.search_legibility",
        "app.services.search_replays",
        "app.services.semantic_backfill",
        "app.services.semantics",
        "app.services.tables",
    }
)
FORBIDDEN_BOUNDARY_DATA_MODEL_IMPORTS = frozenset({"app.db.models"})
FORBIDDEN_CLI_IMPROVEMENT_INTAKE_SYMBOLS = frozenset(
    {
        "collect_eval_failure_case_observations",
        "collect_failed_agent_task_observations",
        "collect_failed_agent_verification_observations",
        "collect_hygiene_finding_observations",
        "import_improvement_case_observations",
    }
)
REQUIRED_ARCHITECTURE_DOC_TOKENS = frozenset(
    {
        "app.services.capabilities",
        "app.api.route_contracts",
        "tests/unit/test_api_architecture.py",
        "tests/unit/test_api_route_contracts.py",
        "tests/unit/test_agent_action_contracts.py",
        "app.db.models",
        "app.architecture_decisions",
        "docs/architecture_decisions.yaml",
        "app.services.improvement_case_intake",
        "ImprovementCaseImportRequest",
        "ImprovementCaseImportResult",
    }
)
