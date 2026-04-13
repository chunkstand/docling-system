from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentTaskCreateRequest(BaseModel):
    task_type: str = Field(min_length=1)
    priority: int = Field(default=100, ge=0, le=1000)
    side_effect_level: str = Field(
        default="read_only",
        pattern="^(read_only|draft_change|promotable)$",
    )
    requires_approval: bool = False
    parent_task_id: UUID | None = None
    dependency_task_ids: list[UUID] = Field(default_factory=list)
    input: dict = Field(default_factory=dict)
    workflow_version: str = Field(default="v1", min_length=1)
    tool_version: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    model_settings: dict = Field(default_factory=dict)


class AgentTaskApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=1)
    approval_note: str | None = None


class AgentTaskActionDefinitionResponse(BaseModel):
    task_type: str
    description: str
    side_effect_level: str
    requires_approval: bool
    input_schema: dict = Field(default_factory=dict)
    input_example: dict = Field(default_factory=dict)


class AgentTaskSummaryResponse(BaseModel):
    task_id: UUID
    task_type: str
    status: str
    priority: int
    side_effect_level: str
    requires_approval: bool
    parent_task_id: UUID | None = None
    workflow_version: str
    tool_version: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AgentTaskDetailResponse(AgentTaskSummaryResponse):
    dependency_task_ids: list[UUID] = Field(default_factory=list)
    input: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    model_settings: dict = Field(default_factory=dict)
    error_message: str | None = None
    failure_artifact_path: str | None = None
    attempts: int = 0
    locked_at: datetime | None = None
    locked_by: str | None = None
    last_heartbeat_at: datetime | None = None
    next_attempt_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    approval_note: str | None = None
    artifact_count: int = 0
    attempt_count: int = 0


class LatestEvaluationTaskInput(BaseModel):
    document_id: UUID


class ReplaySearchRequestTaskInput(BaseModel):
    search_request_id: UUID


class QualityEvalCandidatesTaskInput(BaseModel):
    limit: int = Field(default=12, ge=1, le=200)
    include_resolved: bool = False
