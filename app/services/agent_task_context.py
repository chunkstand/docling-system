from __future__ import annotations

import yaml
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact
from app.schemas.agent_task_core import TaskContextEnvelope
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context_core import build_core_context_builders
from app.services.agent_task_context_registry import (
    compose_context_builder_registries,
)
from app.services.agent_task_context_resolvers import (
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)
from app.services.agent_task_context_search_harness import (
    build_search_harness_context_builders,
)
from app.services.agent_task_context_semantic import build_semantic_context_builders
from app.services.agent_task_context_semantic_governance import (
    build_semantic_governance_context_builders,
)
from app.services.agent_task_context_store import (
    get_agent_task_context as get_agent_task_context,
)
from app.services.agent_task_context_store import (
    get_agent_task_context_artifact as get_agent_task_context_artifact,
)
from app.services.agent_task_context_store import (
    get_agent_task_context_yaml_path as get_agent_task_context_yaml_path,
)
from app.services.agent_task_context_store import (
    refresh_task_context_freshness as refresh_task_context_freshness,
)
from app.services.agent_task_context_technical_reports import (
    build_technical_report_context_builders,
)
from app.services.agent_task_generic_context import build_generic_task_context
from app.services.storage import StorageService

__all__ = [
    "build_agent_task_context",
    "get_agent_task_context",
    "get_agent_task_context_artifact",
    "get_agent_task_context_builder",
    "get_agent_task_context_yaml_path",
    "list_agent_task_context_builder_names",
    "refresh_task_context_freshness",
    "resolve_required_dependency_task_output_context",
    "resolve_required_task_output_context",
    "write_agent_task_context",
]

_CONTEXT_BUILDERS = compose_context_builder_registries(
    build_core_context_builders(
        {"build_generic_task_context": build_generic_task_context}
    ),
    build_semantic_context_builders(globals()),
    build_semantic_governance_context_builders(globals()),
    build_technical_report_context_builders(globals()),
    build_search_harness_context_builders(globals()),
)


def get_agent_task_context_builder(name: str | None):
    builder_name = name or "generic"
    try:
        return _CONTEXT_BUILDERS[builder_name]
    except KeyError as exc:
        available = ", ".join(sorted(_CONTEXT_BUILDERS))
        msg = f"Unknown agent task context builder '{builder_name}'. Available: {available}"
        raise ValueError(msg) from exc


def list_agent_task_context_builder_names() -> set[str]:
    return set(_CONTEXT_BUILDERS)


def build_agent_task_context(
    session: Session,
    task: AgentTask,
    result: dict,
) -> TaskContextEnvelope | None:
    from app.services.agent_task_action_lookup import get_agent_task_action

    action = get_agent_task_action(task.task_type)
    if action.output_model is None:
        return None

    payload = (result or {}).get("payload") or {}
    builder = get_agent_task_context_builder(action.context_builder_name)
    return builder(session, task, payload, action=action)


def write_agent_task_context(
    session: Session,
    task: AgentTask,
    result: dict,
    *,
    storage_service: StorageService,
) -> AgentTaskArtifact | None:
    envelope = build_agent_task_context(session, task, result)
    if envelope is None:
        return None

    envelope.task_status = "completed"
    envelope.task_updated_at = utcnow()
    payload = envelope.model_dump(mode="json")
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="context",
        payload=payload,
        storage_service=storage_service,
        filename="context.json",
    )
    yaml_path = storage_service.get_agent_task_context_yaml_path(task.id)
    yaml_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return artifact
