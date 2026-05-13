from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask
from app.schemas.agent_tasks import EnqueueDocumentReprocessTaskInput
from app.services.agent_actions.claim_support_actions import (
    build_claim_support_action_definitions,
)
from app.services.agent_actions.claim_support_activation import (
    require_active_replay_alert_fixture_coverage_waiver,
)
from app.services.agent_actions.claim_support_shared import (
    replay_alert_fixture_coverage_waiver_sha256,
)
from app.services.agent_actions.document_lifecycle_actions import (
    build_document_lifecycle_action_definitions,
)
from app.services.agent_actions.evaluation_actions import (
    build_evaluation_action_definitions,
)
from app.services.agent_actions.manifest import (
    AgentActionContractIssue,
    build_agent_action_index,
    build_agent_action_manifest,
    validate_agent_action_contracts,
)
from app.services.agent_actions.registry import compose_action_registries
from app.services.agent_actions.report_actions import (
    build_report_action_definitions,
)
from app.services.agent_actions.search_harness import (
    build_search_harness_action_definitions,
)
from app.services.agent_actions.semantic_analysis_actions import (
    build_semantic_analysis_action_definitions,
)
from app.services.agent_actions.semantic_drafting_actions import (
    build_semantic_drafting_action_definitions,
)
from app.services.agent_actions.semantic_governance_actions import (
    build_semantic_governance_action_definitions,
)
from app.services.agent_actions.semantic_verification_actions import (
    build_semantic_verification_action_definitions,
)
from app.services.agent_actions.types import AgentTaskActionDefinition
from app.services.documents import reprocess_document

_replay_alert_fixture_coverage_waiver_sha256 = replay_alert_fixture_coverage_waiver_sha256
_require_active_replay_alert_fixture_coverage_waiver = (
    require_active_replay_alert_fixture_coverage_waiver
)


def _enqueue_document_reprocess_executor(
    session: Session,
    _task: AgentTask,
    payload: EnqueueDocumentReprocessTaskInput,
) -> dict:
    response = reprocess_document(session, payload.document_id)
    return {
        "document_id": str(payload.document_id),
        "source_task_id": str(payload.source_task_id) if payload.source_task_id else None,
        "reason": payload.reason,
        "reprocess": jsonable_encoder(response),
    }


_SEARCH_HARNESS_ACTION_REGISTRY = build_search_harness_action_definitions()
_EVALUATION_ACTION_REGISTRY = build_evaluation_action_definitions()
_SEMANTIC_ANALYSIS_ACTION_REGISTRY = build_semantic_analysis_action_definitions()
_REPORT_ACTION_REGISTRY = build_report_action_definitions()
_CLAIM_SUPPORT_ACTION_REGISTRY = build_claim_support_action_definitions()
_SEMANTIC_DRAFTING_ACTION_REGISTRY = build_semantic_drafting_action_definitions()
_SEMANTIC_GOVERNANCE_ACTION_REGISTRY = build_semantic_governance_action_definitions()
_SEMANTIC_VERIFICATION_ACTION_REGISTRY = build_semantic_verification_action_definitions()
_DOCUMENT_LIFECYCLE_ACTION_REGISTRY = build_document_lifecycle_action_definitions(
    enqueue_document_reprocess_executor=_enqueue_document_reprocess_executor
)

_ACTION_REGISTRY: dict[str, AgentTaskActionDefinition] = compose_action_registries(
    _EVALUATION_ACTION_REGISTRY,
    _SEMANTIC_ANALYSIS_ACTION_REGISTRY,
    _REPORT_ACTION_REGISTRY,
    _CLAIM_SUPPORT_ACTION_REGISTRY,
    _SEARCH_HARNESS_ACTION_REGISTRY,
    _SEMANTIC_DRAFTING_ACTION_REGISTRY,
    _SEMANTIC_GOVERNANCE_ACTION_REGISTRY,
    _SEMANTIC_VERIFICATION_ACTION_REGISTRY,
    _DOCUMENT_LIFECYCLE_ACTION_REGISTRY,
)


def list_agent_task_actions() -> list[AgentTaskActionDefinition]:
    return list(_ACTION_REGISTRY.values())


def build_agent_task_action_manifest() -> list[dict[str, object]]:
    return build_agent_action_manifest(list_agent_task_actions())


def build_agent_task_action_index() -> dict[str, object]:
    return build_agent_action_index(list_agent_task_actions())


def validate_agent_task_action_contracts() -> list[AgentActionContractIssue]:
    from app.services.agent_task_context import list_agent_task_context_builder_names

    issues = validate_agent_action_contracts(
        list_agent_task_actions(),
        registry_keys=set(_ACTION_REGISTRY),
        context_builder_names=list_agent_task_context_builder_names(),
    )
    for registry_key, action in _ACTION_REGISTRY.items():
        if registry_key != action.task_type:
            issues.append(
                AgentActionContractIssue(
                    task_type=action.task_type,
                    field="task_type",
                    message=f"registry key '{registry_key}' must match task_type",
                )
            )
    return issues


def get_agent_task_action(task_type: str) -> AgentTaskActionDefinition:
    try:
        return _ACTION_REGISTRY[task_type]
    except KeyError as exc:
        available = ", ".join(sorted(_ACTION_REGISTRY))
        raise ValueError(f"Unknown agent task type '{task_type}'. Available: {available}") from exc


def validate_agent_task_input(task_type: str, raw_input: dict) -> BaseModel:
    action = get_agent_task_action(task_type)
    return action.payload_model.model_validate(raw_input or {})


def validate_agent_task_output(task_type: str, raw_output: dict) -> dict:
    action = get_agent_task_action(task_type)
    if action.output_model is None:
        return raw_output or {}
    validated_output = action.output_model.model_validate(raw_output or {})
    return validated_output.model_dump(mode="json", exclude_none=True)


def execute_agent_task_action(session: Session, task: AgentTask) -> dict:
    action = get_agent_task_action(task.task_type)
    payload = action.payload_model.model_validate(task.input_json or {})
    result = action.executor(session, task, payload)
    validated_output = validate_agent_task_output(task.task_type, result)
    return {
        "task_type": task.task_type,
        "definition_kind": action.definition_kind,
        "side_effect_level": action.side_effect_level,
        "requires_approval": action.requires_approval,
        "output_schema_name": action.output_schema_name,
        "output_schema_version": action.output_schema_version,
        "payload": validated_output,
    }
