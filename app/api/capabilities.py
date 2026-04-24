from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ApiCapabilityDefinition:
    name: str
    family: str
    access: str
    description: str


AGENT_TASKS_READ: Final = "agent_tasks:read"
AGENT_TASKS_WRITE: Final = "agent_tasks:write"
CHAT_FEEDBACK: Final = "chat:feedback"
CHAT_QUERY: Final = "chat:query"
DOCUMENTS_INSPECT: Final = "documents:inspect"
DOCUMENTS_REPROCESS: Final = "documents:reprocess"
DOCUMENTS_REVIEW: Final = "documents:review"
DOCUMENTS_UPLOAD: Final = "documents:upload"
QUALITY_READ: Final = "quality:read"
SEARCH_EVALUATE: Final = "search:evaluate"
SEARCH_FEEDBACK: Final = "search:feedback"
SEARCH_HISTORY_READ: Final = "search:history:read"
SEARCH_QUERY: Final = "search:query"
SEARCH_REPLAY: Final = "search:replay"
SYSTEM_READ: Final = "system:read"

API_CAPABILITY_WILDCARD: Final = "*"

API_CAPABILITY_DEFINITIONS: Final = (
    ApiCapabilityDefinition(
        name=AGENT_TASKS_READ,
        family="agent_tasks",
        access="read",
        description="Inspect agent task actions, work queues, context, artifacts, and analytics.",
    ),
    ApiCapabilityDefinition(
        name=AGENT_TASKS_WRITE,
        family="agent_tasks",
        access="write",
        description="Create agent tasks and mutate agent task outcomes or approvals.",
    ),
    ApiCapabilityDefinition(
        name=CHAT_FEEDBACK,
        family="chat",
        access="write",
        description="Record feedback for retrieval-grounded chat answers.",
    ),
    ApiCapabilityDefinition(
        name=CHAT_QUERY,
        family="chat",
        access="execute",
        description="Ask retrieval-grounded chat questions against the active corpus.",
    ),
    ApiCapabilityDefinition(
        name=DOCUMENTS_INSPECT,
        family="documents",
        access="read",
        description="Inspect documents, runs, active content, artifacts, and semantic artifacts.",
    ),
    ApiCapabilityDefinition(
        name=DOCUMENTS_REPROCESS,
        family="documents",
        access="write",
        description="Create a new processing run for an existing document.",
    ),
    ApiCapabilityDefinition(
        name=DOCUMENTS_REVIEW,
        family="documents",
        access="write",
        description="Run or update semantic review workflows for document-derived assertions.",
    ),
    ApiCapabilityDefinition(
        name=DOCUMENTS_UPLOAD,
        family="documents",
        access="write",
        description="Upload a new PDF document for ingestion.",
    ),
    ApiCapabilityDefinition(
        name=QUALITY_READ,
        family="quality",
        access="read",
        description="Read quality, evaluation, and latest document evaluation surfaces.",
    ),
    ApiCapabilityDefinition(
        name=SEARCH_EVALUATE,
        family="search",
        access="execute",
        description="Inspect and run search harness evaluations.",
    ),
    ApiCapabilityDefinition(
        name=SEARCH_FEEDBACK,
        family="search",
        access="write",
        description="Record feedback for logged search requests.",
    ),
    ApiCapabilityDefinition(
        name=SEARCH_HISTORY_READ,
        family="search",
        access="read",
        description="Inspect logged search requests and explanation records.",
    ),
    ApiCapabilityDefinition(
        name=SEARCH_QUERY,
        family="search",
        access="execute",
        description="Run mixed retrieval queries against the active corpus.",
    ),
    ApiCapabilityDefinition(
        name=SEARCH_REPLAY,
        family="search",
        access="execute",
        description="Replay logged searches and inspect replay comparison artifacts.",
    ),
    ApiCapabilityDefinition(
        name=SYSTEM_READ,
        family="system",
        access="read",
        description="Read runtime status and process telemetry.",
    ),
)

API_CAPABILITIES: Final = frozenset(definition.name for definition in API_CAPABILITY_DEFINITIONS)
API_CAPABILITY_BY_NAME: Final = {
    definition.name: definition for definition in API_CAPABILITY_DEFINITIONS
}


def is_known_api_capability(capability: str) -> bool:
    return capability in API_CAPABILITIES


def require_known_api_capability(capability: str) -> str:
    if not is_known_api_capability(capability):
        known = ", ".join(sorted(API_CAPABILITIES))
        raise ValueError(f"Unknown API capability '{capability}'. Known capabilities: {known}")
    return capability


def list_api_capability_definitions() -> tuple[ApiCapabilityDefinition, ...]:
    return API_CAPABILITY_DEFINITIONS
