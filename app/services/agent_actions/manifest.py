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


@dataclass(frozen=True)
class AgentActionContractIssue:
    task_type: str
    field: str
    message: str


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
        }
        for action in actions
    ]


def validate_agent_action_contracts(
    actions: Iterable[AgentTaskActionDefinition],
    *,
    registry_keys: set[str] | None = None,
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
