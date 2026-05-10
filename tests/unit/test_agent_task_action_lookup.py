from __future__ import annotations

import ast
from pathlib import Path

from app.services import agent_task_action_lookup
from app.services.agent_task_actions import get_agent_task_action as executor_get_action

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_OWNER_PATHS = (
    REPO_ROOT / "app/services/agent_task_context.py",
    REPO_ROOT / "app/services/agent_task_context_store.py",
    REPO_ROOT / "app/services/agent_tasks.py",
)


def _static_import_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def test_agent_task_action_lookup_preserves_public_action_identity() -> None:
    action = agent_task_action_lookup.get_agent_task_action("evaluate_search_harness")

    assert action is executor_get_action("evaluate_search_harness")
    assert action.context_builder_name == "evaluate_search_harness"


def test_agent_task_action_lookup_preserves_input_validation_defaults() -> None:
    payload = agent_task_action_lookup.validate_agent_task_input(
        "evaluate_search_harness",
        {"candidate_harness_name": "prose_v3"},
    )

    assert payload.baseline_harness_name == "default_v1"


def test_context_and_task_services_use_lookup_seam_not_executor_facade() -> None:
    for path in CONTEXT_OWNER_PATHS:
        imports = _static_import_modules(path)
        assert "app.services.agent_task_actions" not in imports
        assert "app.services.agent_task_action_lookup" in imports
