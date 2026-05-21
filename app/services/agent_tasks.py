from __future__ import annotations

from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.orm import Session

import app.services.agent_task_dependencies as dependency_owner
import app.services.agent_task_lifecycle as lifecycle_owner
import app.services.agent_task_reads as read_owner
from app.api.errors import api_error
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskDependency
from app.schemas.agent_task_core import (
    AgentTaskActionDefinitionResponse,
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskRejectionRequest,
    AgentTaskSummaryResponse,
    AgentTaskTraceExportResponse,
)
from app.services.agent_task_analytics_summary import (
    get_agent_approval_trends as get_agent_approval_trends,
)
from app.services.agent_task_analytics_summary import (
    get_agent_task_analytics_summary as get_agent_task_analytics_summary,
)
from app.services.agent_task_analytics_summary import (
    get_agent_task_trends as get_agent_task_trends,
)
from app.services.agent_task_analytics_summary import (
    get_agent_verification_trends as get_agent_verification_trends,
)
from app.services.agent_task_analytics_summary import (
    list_agent_task_workflow_summaries as list_agent_task_workflow_summaries,
)
from app.services.agent_task_cost_performance import (
    get_agent_task_cost_summary as get_agent_task_cost_summary,
)
from app.services.agent_task_cost_performance import (
    get_agent_task_cost_trends as get_agent_task_cost_trends,
)
from app.services.agent_task_cost_performance import (
    get_agent_task_performance_summary as get_agent_task_performance_summary,
)
from app.services.agent_task_cost_performance import (
    get_agent_task_performance_trends as get_agent_task_performance_trends,
)
from app.services.agent_task_decision_signals import (
    get_agent_task_decision_signals as get_agent_task_decision_signals,
)
from app.services.agent_task_recommendation_metrics import (
    get_agent_task_recommendation_summary as get_agent_task_recommendation_summary,
)
from app.services.agent_task_recommendation_metrics import (
    get_agent_task_recommendation_trends as get_agent_task_recommendation_trends,
)
from app.services.agent_task_recommendation_metrics import (
    get_agent_task_value_density as get_agent_task_value_density,
)

_agent_task_not_found = read_owner.agent_task_not_found
_build_summary = read_owner.build_agent_task_summary
_list_dependency_ids = read_owner.list_dependency_ids
_list_dependency_edges = read_owner.list_dependency_edges
_count_task_attempts = read_owner.count_task_attempts
_count_task_artifacts = read_owner.count_task_artifacts
_list_task_artifacts = read_owner.list_task_artifacts
_to_outcome_response = read_owner.to_outcome_response
_count_task_outcomes = read_owner.count_task_outcomes
_list_task_outcomes = read_owner.list_task_outcomes
_build_detail = read_owner.build_agent_task_detail

_initial_task_status = dependency_owner.initial_task_status
_dependency_row_task_id = dependency_owner._dependency_row_task_id
_dependency_row_depends_on_task_id = dependency_owner._dependency_row_depends_on_task_id
_validate_dependency_ids = dependency_owner.validate_dependency_ids
_validate_dependency_graph_is_acyclic = dependency_owner.validate_dependency_graph_is_acyclic
_validate_parent_task_id = dependency_owner.validate_parent_task_id
_incomplete_dependency_count = dependency_owner.incomplete_dependency_count
_task_has_incomplete_dependencies = dependency_owner.task_has_incomplete_dependencies
_augment_dependency_kinds_for_action = dependency_owner.augment_dependency_kinds_for_action


def create_agent_task(
    session: Session,
    payload: AgentTaskCreateRequest,
    *,
    commit: bool = True,
) -> AgentTaskDetailResponse:
    from app.services.agent_task_action_lookup import (
        get_agent_task_action,
        validate_agent_task_input,
    )

    now = utcnow()
    dependency_task_ids = list(dict.fromkeys(payload.dependency_task_ids))
    if payload.parent_task_id is not None and payload.parent_task_id in dependency_task_ids:
        raise api_error(
            400,
            "invalid_agent_task_request",
            "A task cannot depend on its parent task explicitly.",
        )
    action = get_agent_task_action(payload.task_type)
    try:
        validated_input = validate_agent_task_input(payload.task_type, payload.input)
    except ValidationError as exc:
        raise api_error(
            422,
            "invalid_agent_task_input",
            "Agent task input did not match the task schema.",
            task_type=payload.task_type,
            validation_errors=jsonable_encoder(exc.errors()),
        ) from exc
    dependency_specs = _augment_dependency_kinds_for_action(
        validated_input=validated_input,
        dependency_task_ids=dependency_task_ids,
    )
    dependency_task_ids = [task_id for task_id, _kind in dependency_specs]
    if payload.parent_task_id is not None and payload.parent_task_id in dependency_task_ids:
        raise api_error(
            400,
            "invalid_agent_task_request",
            "A task cannot depend on its parent task explicitly.",
        )
    effective_side_effect_level = payload.side_effect_level or action.side_effect_level
    if effective_side_effect_level != action.side_effect_level:
        raise api_error(
            400,
            "invalid_agent_task_request",
            (
                f"Task type '{payload.task_type}' requires side_effect_level "
                f"'{action.side_effect_level}'."
            ),
            task_type=payload.task_type,
            required_side_effect_level=action.side_effect_level,
        )
    effective_requires_approval = (
        payload.requires_approval
        if payload.requires_approval is not None
        else action.requires_approval
    )
    if effective_requires_approval != action.requires_approval:
        raise api_error(
            400,
            "invalid_agent_task_request",
            (
                f"Task type '{payload.task_type}' requires requires_approval="
                f"{str(action.requires_approval).lower()}."
            ),
            task_type=payload.task_type,
            requires_approval=action.requires_approval,
        )

    _validate_parent_task_id(session, payload.parent_task_id)
    _validate_dependency_ids(session, dependency_task_ids)
    _validate_dependency_graph_is_acyclic(session, dependency_task_ids)
    has_incomplete_dependencies = _incomplete_dependency_count(session, dependency_task_ids) > 0

    task = AgentTask(
        task_type=payload.task_type,
        status=_initial_task_status(
            requires_approval=effective_requires_approval,
            has_incomplete_dependencies=has_incomplete_dependencies,
        ),
        priority=payload.priority,
        side_effect_level=effective_side_effect_level,
        requires_approval=effective_requires_approval,
        parent_task_id=payload.parent_task_id,
        input_json=validated_input.model_dump(mode="json", exclude_none=True),
        result_json={},
        workflow_version=payload.workflow_version,
        tool_version=payload.tool_version,
        prompt_version=payload.prompt_version,
        model=payload.model,
        model_settings_json=payload.model_settings,
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    session.flush()

    for dependency_task_id, dependency_kind in dependency_specs:
        session.add(
            AgentTaskDependency(
                task_id=task.id,
                depends_on_task_id=dependency_task_id,
                dependency_kind=dependency_kind,
                created_at=now,
            )
        )

    if commit:
        session.commit()
    else:
        session.flush()
    return _build_detail(session, task)


def list_agent_task_action_definitions() -> list[AgentTaskActionDefinitionResponse]:
    from app.services.agent_actions.manifest import build_agent_action_manifest
    from app.services.agent_task_action_lookup import list_agent_task_actions

    rows: list[AgentTaskActionDefinitionResponse] = []
    actions = list_agent_task_actions()
    manifest_by_type = {str(row["task_type"]): row for row in build_agent_action_manifest(actions)}
    for action in actions:
        manifest_row = manifest_by_type[action.task_type]
        rows.append(
            AgentTaskActionDefinitionResponse(
                task_type=action.task_type,
                capability=action.capability,
                definition_kind=action.definition_kind,
                description=action.description,
                side_effect_level=action.side_effect_level,
                requires_approval=action.requires_approval,
                context_builder_name=action.context_builder_name,
                input_schema=action.payload_model.model_json_schema(),
                output_schema_name=action.output_schema_name,
                output_schema_version=action.output_schema_version,
                output_schema=(
                    action.output_model.model_json_schema()
                    if action.output_model is not None
                    else None
                ),
                input_example=action.input_example or {},
                agent_facing_contract=dict(manifest_row["agent_facing_contract"]),
            )
        )
    return rows


def list_agent_tasks(
    session: Session,
    *,
    statuses: list[str] | None = None,
    limit: int = 50,
) -> list[AgentTaskSummaryResponse]:
    return read_owner.list_agent_tasks(session, statuses=statuses, limit=limit)


def get_agent_task_detail(session: Session, task_id: UUID) -> AgentTaskDetailResponse:
    return read_owner.get_agent_task_detail(
        session,
        task_id,
        not_found_error_func=_agent_task_not_found,
    )


def list_agent_task_outcomes(
    session: Session,
    task_id: UUID,
    *,
    limit: int = 20,
) -> list[AgentTaskOutcomeResponse]:
    return read_owner.list_agent_task_outcomes(
        session,
        task_id,
        limit=limit,
        not_found_error_func=_agent_task_not_found,
    )


def create_agent_task_outcome(
    session: Session,
    task_id: UUID,
    payload: AgentTaskOutcomeCreateRequest,
) -> AgentTaskOutcomeResponse:
    return lifecycle_owner.create_agent_task_outcome(
        session,
        task_id,
        payload,
        not_found_error_func=_agent_task_not_found,
        to_outcome_response_func=_to_outcome_response,
    )


def export_agent_task_traces(
    session: Session,
    *,
    limit: int = 50,
    workflow_version: str | None = None,
    task_type: str | None = None,
) -> AgentTaskTraceExportResponse:
    return read_owner.export_agent_task_traces(
        session,
        limit=limit,
        workflow_version=workflow_version,
        task_type=task_type,
        build_detail_func=_build_detail,
    )


def approve_agent_task(
    session: Session,
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
) -> AgentTaskDetailResponse:
    return lifecycle_owner.approve_agent_task(
        session,
        task_id,
        payload,
        build_detail_func=_build_detail,
        has_incomplete_dependencies_func=_task_has_incomplete_dependencies,
        not_found_error_func=_agent_task_not_found,
    )


def reject_agent_task(
    session: Session,
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
) -> AgentTaskDetailResponse:
    return lifecycle_owner.reject_agent_task(
        session,
        task_id,
        payload,
        build_detail_func=_build_detail,
        not_found_error_func=_agent_task_not_found,
    )
