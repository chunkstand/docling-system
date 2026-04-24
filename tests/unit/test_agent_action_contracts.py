from __future__ import annotations

from dataclasses import replace

from app.services.agent_actions.manifest import validate_agent_action_contracts
from app.services.agent_actions.types import (
    AGENT_ACTION_CAPABILITIES,
    AGENT_ACTION_DEFINITION_KINDS,
    AGENT_ACTION_KIND_SIDE_EFFECT_LEVELS,
    AGENT_ACTION_SIDE_EFFECT_LEVELS,
)
from app.services.agent_task_actions import (
    build_agent_task_action_manifest,
    list_agent_task_actions,
    validate_agent_task_action_contracts,
)
from app.services.agent_task_context import list_agent_task_context_builder_names


def test_agent_task_action_contracts_are_machine_checkable() -> None:
    issues = validate_agent_task_action_contracts()
    assert issues == []


def test_agent_task_action_contract_validator_rejects_unknown_vocabularies() -> None:
    action = replace(
        list_agent_task_actions()[0],
        capability="unknown",
        definition_kind="mystery",
        side_effect_level="dangerous",
    )

    issues = validate_agent_action_contracts([action])
    fields = {issue.field for issue in issues}

    assert {"capability", "definition_kind", "side_effect_level"} <= fields


def test_agent_task_action_contract_validator_rejects_registry_drift() -> None:
    action = replace(list_agent_task_actions()[0], task_type="not_registered")

    issues = validate_agent_action_contracts([action], registry_keys={"registered"})

    assert any(issue.field == "task_type" for issue in issues)


def test_agent_task_action_manifest_uses_known_contract_vocabularies() -> None:
    manifest = build_agent_task_action_manifest()
    task_types = {row["task_type"] for row in manifest}
    capabilities = {row["capability"] for row in manifest}
    definition_kinds = {row["definition_kind"] for row in manifest}
    side_effect_levels = {row["side_effect_level"] for row in manifest}

    assert len(task_types) == len(manifest)
    assert capabilities <= AGENT_ACTION_CAPABILITIES
    assert AGENT_ACTION_CAPABILITIES <= capabilities
    assert definition_kinds <= AGENT_ACTION_DEFINITION_KINDS
    assert side_effect_levels <= AGENT_ACTION_SIDE_EFFECT_LEVELS


def test_agent_task_definition_kinds_have_expected_side_effect_levels() -> None:
    mismatches = [
        (
            action.task_type,
            action.definition_kind,
            action.side_effect_level,
            AGENT_ACTION_KIND_SIDE_EFFECT_LEVELS[action.definition_kind],
        )
        for action in list_agent_task_actions()
        if action.side_effect_level != AGENT_ACTION_KIND_SIDE_EFFECT_LEVELS[action.definition_kind]
    ]

    assert mismatches == []


def test_agent_task_action_context_builder_names_are_registered() -> None:
    builder_names = list_agent_task_context_builder_names()
    missing = [
        (action.task_type, action.context_builder_name)
        for action in list_agent_task_actions()
        if action.context_builder_name not in builder_names
    ]

    assert missing == []
