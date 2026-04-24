from __future__ import annotations

from app.services.agent_task_actions import (
    build_agent_task_action_manifest,
    list_agent_task_actions,
    validate_agent_task_action_contracts,
)
from app.services.agent_task_context import list_agent_task_context_builder_names


def test_agent_task_action_contracts_are_machine_checkable() -> None:
    issues = validate_agent_task_action_contracts()
    assert issues == []


def test_agent_task_action_manifest_declares_capability_ownership() -> None:
    manifest = build_agent_task_action_manifest()
    task_types = {row["task_type"] for row in manifest}
    capabilities = {row["capability"] for row in manifest}

    assert len(task_types) == len(manifest)
    assert {
        "document_lifecycle",
        "evaluation",
        "retrieval",
        "semantic_memory",
        "technical_reports",
    } <= capabilities


def test_agent_task_action_context_builder_names_are_registered() -> None:
    builder_names = list_agent_task_context_builder_names()
    missing = [
        (action.task_type, action.context_builder_name)
        for action in list_agent_task_actions()
        if action.context_builder_name not in builder_names
    ]

    assert missing == []
