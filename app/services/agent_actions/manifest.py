from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import ValidationError

from app.db.models import AgentTaskSideEffectLevel
from app.services.agent_actions.types import (
    AGENT_ACTION_CAPABILITIES,
    AGENT_ACTION_DEFINITION_KINDS,
    AGENT_ACTION_KIND_SIDE_EFFECT_LEVELS,
    AGENT_ACTION_SIDE_EFFECT_LEVELS,
    AgentTaskActionDefinition,
)

DEFAULT_AGENT_ACTION_VERIFICATION_COMMAND = (
    "uv run pytest -q tests/unit/test_agent_action_contracts.py"
)


@dataclass(frozen=True)
class AgentActionContractIssue:
    task_type: str
    field: str
    message: str


def _agent_tool_description(action: AgentTaskActionDefinition) -> str:
    return action.agent_tool_description or action.description


def _when_to_use(action: AgentTaskActionDefinition) -> str:
    if action.when_to_use:
        return action.when_to_use
    description = action.description.strip()
    if not description:
        return "Use when the registered task contract explicitly matches the requested work."
    return (
        "Use when an operator or workflow needs to "
        f"{description[0].lower()}{description[1:]}"
    )


def _when_not_to_use(action: AgentTaskActionDefinition) -> str:
    if action.when_not_to_use:
        return action.when_not_to_use
    if action.requires_approval:
        return "Do not use without explicit approval and a verified upstream draft or target task."
    if action.definition_kind == "verifier":
        return "Do not use as a mutating action; this task only evaluates existing state."
    if action.definition_kind == "draft":
        return (
            "Do not use to promote changes directly; pair the draft with a verifier "
            "and promotion action."
        )
    return (
        "Do not use when the requested work falls outside the declared capability "
        "or context builder."
    )


def _required_context_refs(action: AgentTaskActionDefinition) -> list[str]:
    if action.required_context_refs:
        return list(action.required_context_refs)
    if action.context_builder_name == "generic":
        return []
    return [action.context_builder_name]


def _expected_artifacts(action: AgentTaskActionDefinition) -> list[str]:
    if action.expected_artifacts:
        return list(action.expected_artifacts)
    artifacts: list[str] = []
    if action.output_schema_name:
        artifacts.append(action.output_schema_name)
    if action.output_model is not None:
        artifacts.append(action.output_model.__name__)
    return artifacts


def _common_failure_modes(action: AgentTaskActionDefinition) -> list[str]:
    if action.common_failure_modes:
        return list(action.common_failure_modes)
    modes = ["input validation fails", "required context is stale or missing"]
    if action.requires_approval:
        modes.append("approval or verified dependency is missing")
    if action.output_model is not None:
        modes.append("executor output does not match the declared output schema")
    return modes


def _escalation_condition(action: AgentTaskActionDefinition) -> str:
    if action.escalation_condition:
        return action.escalation_condition
    if action.side_effect_level == AgentTaskSideEffectLevel.PROMOTABLE.value:
        return (
            "Escalate before execution when approval, verifier evidence, or target "
            "task identity is ambiguous."
        )
    return (
        "Escalate when required context cannot be resolved or the action would exceed "
        "its side-effect level."
    )


def _agent_facing_contract(action: AgentTaskActionDefinition) -> dict[str, object]:
    return {
        "tool_description": _agent_tool_description(action),
        "when_to_use": _when_to_use(action),
        "when_not_to_use": _when_not_to_use(action),
        "required_context_refs": _required_context_refs(action),
        "expected_artifacts": _expected_artifacts(action),
        "verification_command": (
            action.verification_command or DEFAULT_AGENT_ACTION_VERIFICATION_COMMAND
        ),
        "common_failure_modes": _common_failure_modes(action),
        "escalation_condition": _escalation_condition(action),
    }


def build_agent_action_manifest(
    actions: Iterable[AgentTaskActionDefinition],
) -> list[dict[str, object]]:
    return [
        {
            "task_type": action.task_type,
            "capability": action.capability,
            "definition_kind": action.definition_kind,
            "side_effect_level": action.side_effect_level,
            "requires_approval": action.requires_approval,
            "payload_model": action.payload_model.__name__,
            "output_model": action.output_model.__name__ if action.output_model else None,
            "output_schema_name": action.output_schema_name,
            "output_schema_version": action.output_schema_version,
            "context_builder_name": action.context_builder_name,
            "agent_facing_contract": _agent_facing_contract(action),
        }
        for action in actions
    ]


def build_agent_action_index(
    actions: Iterable[AgentTaskActionDefinition],
) -> dict[str, object]:
    by_capability: dict[str, list[dict[str, object]]] = {}
    for action in sorted(actions, key=lambda row: (row.capability, row.task_type)):
        by_capability.setdefault(action.capability, []).append(
            {
                "task_type": action.task_type,
                "definition_kind": action.definition_kind,
                "side_effect_level": action.side_effect_level,
                "requires_approval": action.requires_approval,
                "context_builder_name": action.context_builder_name,
                "when_to_use": _when_to_use(action),
                "verification_command": (
                    action.verification_command or DEFAULT_AGENT_ACTION_VERIFICATION_COMMAND
                ),
            }
        )
    return {
        "schema_name": "agent_action_index",
        "schema_version": "1.0",
        "capabilities": by_capability,
    }


def validate_agent_action_contracts(
    actions: Iterable[AgentTaskActionDefinition],
    *,
    registry_keys: set[str] | None = None,
    context_builder_names: set[str] | None = None,
) -> list[AgentActionContractIssue]:
    issues: list[AgentActionContractIssue] = []
    seen_task_types: set[str] = set()
    seen_output_schema_names: dict[str, tuple[type[object], str | None]] = {}
    registry_keys = registry_keys or set()

    for action in actions:
        if registry_keys and action.task_type not in registry_keys:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="task_type",
                    message="task type must match a registry key",
                )
            )

        if action.task_type in seen_task_types:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="task_type",
                    message="task type must be unique",
                )
            )
        seen_task_types.add(action.task_type)

        if action.capability not in AGENT_ACTION_CAPABILITIES:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="capability",
                    message="action must declare a known owning capability",
                )
            )

        if action.definition_kind not in AGENT_ACTION_DEFINITION_KINDS:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="definition_kind",
                    message="action must declare a known definition kind",
                )
            )

        if action.side_effect_level not in AGENT_ACTION_SIDE_EFFECT_LEVELS:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="side_effect_level",
                    message="action must declare a known side-effect level",
                )
            )

        expected_side_effect_level = AGENT_ACTION_KIND_SIDE_EFFECT_LEVELS.get(
            action.definition_kind
        )
        if (
            expected_side_effect_level is not None
            and action.side_effect_level != expected_side_effect_level
        ):
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="side_effect_level",
                    message=(
                        f"definition kind '{action.definition_kind}' requires "
                        f"side-effect level '{expected_side_effect_level}'"
                    ),
                )
            )

        if action.output_model is not None:
            if not action.output_schema_name:
                issues.append(
                    AgentActionContractIssue(
                        task_type=action.task_type,
                        field="output_schema_name",
                        message="typed output actions must declare an output schema name",
                    )
                )
            elif (
                action.output_schema_name in seen_output_schema_names
                and seen_output_schema_names[action.output_schema_name]
                != (action.output_model, action.output_schema_version)
            ):
                issues.append(
                    AgentActionContractIssue(
                        task_type=action.task_type,
                        field="output_schema_name",
                        message="shared output schema names must use the same model and version",
                    )
                )
            else:
                seen_output_schema_names[action.output_schema_name] = (
                    action.output_model,
                    action.output_schema_version,
                )

            if not action.output_schema_version:
                issues.append(
                    AgentActionContractIssue(
                        task_type=action.task_type,
                        field="output_schema_version",
                        message="typed output actions must declare an output schema version",
                    )
                )

        if action.output_model is None and (
            action.output_schema_name is not None or action.output_schema_version is not None
        ):
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="output_model",
                    message="schema metadata requires an output model",
                )
            )

        if action.input_example is None:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="input_example",
                    message="action must provide an input example",
                )
            )
        else:
            try:
                action.payload_model.model_validate(action.input_example)
            except ValidationError as exc:
                issues.append(
                    AgentActionContractIssue(
                        task_type=action.task_type,
                        field="input_example",
                        message=str(exc),
                )
            )

        if (
            context_builder_names is not None
            and action.context_builder_name not in context_builder_names
        ):
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="context_builder_name",
                    message="action declares an unknown context builder",
                )
            )

        if len(action.description.strip()) < 20:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="description",
                    message="action description must be specific enough for agent tool selection",
                )
            )
        if any(marker in action.description.lower() for marker in ("todo", "tbd")):
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="description",
                    message="action description must not contain placeholder text",
                )
            )

        agent_contract = _agent_facing_contract(action)
        for field_name in (
            "tool_description",
            "when_to_use",
            "when_not_to_use",
            "verification_command",
            "escalation_condition",
        ):
            if not str(agent_contract[field_name]).strip():
                issues.append(
                    AgentActionContractIssue(
                        task_type=action.task_type,
                        field=f"agent_facing_contract.{field_name}",
                        message="agent-facing contract field must be non-empty",
                    )
                )

        if action.side_effect_level == AgentTaskSideEffectLevel.PROMOTABLE.value:
            if not action.requires_approval:
                issues.append(
                    AgentActionContractIssue(
                        task_type=action.task_type,
                        field="requires_approval",
                        message="promotable actions must require approval",
                    )
                )
        elif action.requires_approval:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="requires_approval",
                    message="only promotable actions should require approval",
                )
            )

    return issues
