from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.agent_task_core import (
    AgentTaskArtifactResponse,
    TaskContextEnvelope,
)
from app.services.storage import StorageService


class AgentOrchestrationContextArtifactCapability(Protocol):
    def get_agent_task_context(self, session: Session, task_id: UUID) -> TaskContextEnvelope: ...

    def get_agent_task_audit_bundle(self, session: Session, task_id: UUID) -> dict: ...

    def get_agent_task_evidence_manifest(self, session: Session, task_id: UUID) -> dict: ...

    def get_agent_task_evidence_trace(self, session: Session, task_id: UUID) -> dict: ...

    def get_agent_task_provenance_export(
        self,
        session: Session,
        task_id: UUID,
        *,
        storage_service: StorageService | None = None,
    ) -> dict: ...

    def list_agent_task_artifacts(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskArtifactResponse]: ...

    def get_agent_task_artifact(
        self,
        session: Session,
        task_id: UUID,
        artifact_id: UUID,
    ) -> AgentTaskArtifactResponse: ...
