from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask
from app.services.agent_actions.claim_support_actions import (
    build_claim_support_action_definitions,
)
from app.services.agent_actions.document_lifecycle_actions import (
    build_document_lifecycle_action_definitions,
)
from app.services.agent_actions.evaluation_actions import (
    build_evaluation_action_definitions,
)
from app.services.agent_actions.manifest import build_agent_action_manifest
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


def _unsupported_contract_only_executor(
    _session: Session,
    _task: AgentTask,
    _payload: BaseModel,
) -> dict:
    raise NotImplementedError(
        "Contract-only action metadata does not execute agent-task actions."
    )


def list_agent_action_contract_definitions() -> list[AgentTaskActionDefinition]:
    registry = compose_action_registries(
        build_evaluation_action_definitions(),
        build_semantic_analysis_action_definitions(),
        build_report_action_definitions(),
        build_claim_support_action_definitions(),
        build_search_harness_action_definitions(),
        build_semantic_drafting_action_definitions(),
        build_semantic_governance_action_definitions(),
        build_semantic_verification_action_definitions(),
        build_document_lifecycle_action_definitions(
            enqueue_document_reprocess_executor=_unsupported_contract_only_executor
        ),
    )
    return list(registry.values())


def build_agent_action_contract_manifest() -> list[dict[str, object]]:
    return build_agent_action_manifest(list_agent_action_contract_definitions())
