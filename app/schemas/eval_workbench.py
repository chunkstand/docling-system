from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvalEvidenceRef(BaseModel):
    ref_kind: str
    api_path: str | None = None
    summary: str | None = None
    document_id: UUID | None = None
    run_id: UUID | None = None
    evaluation_id: UUID | None = None
    evaluation_query_id: UUID | None = None
    search_request_id: UUID | None = None
    replay_run_id: UUID | None = None
    harness_evaluation_id: UUID | None = None
    agent_task_id: UUID | None = None


class EvalObservationResponse(BaseModel):
    schema_name: str = "eval_observation"
    schema_version: str = "1.0"
    observation_id: UUID
    observation_key: str
    surface: str
    subject_kind: str
    subject_id: UUID | None = None
    status: str
    severity: str
    failure_classification: str
    summary: str
    document_id: UUID | None = None
    run_id: UUID | None = None
    evaluation_id: UUID | None = None
    evaluation_query_id: UUID | None = None
    search_request_id: UUID | None = None
    replay_run_id: UUID | None = None
    harness_evaluation_id: UUID | None = None
    agent_task_id: UUID | None = None
    details: dict = Field(default_factory=dict)
    evidence_refs: list[EvalEvidenceRef] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime


class EvalFailureCaseResponse(BaseModel):
    schema_name: str = "eval_failure_case"
    schema_version: str = "1.0"
    case_id: UUID
    case_key: str
    status: str
    severity: str
    surface: str
    failure_classification: str
    problem_statement: str
    observed_behavior: str
    expected_behavior: str
    diagnosis: str | None = None
    source_observation_id: UUID | None = None
    document_id: UUID | None = None
    run_id: UUID | None = None
    evaluation_id: UUID | None = None
    evaluation_query_id: UUID | None = None
    search_request_id: UUID | None = None
    replay_run_id: UUID | None = None
    harness_evaluation_id: UUID | None = None
    agent_task_id: UUID | None = None
    recommended_next_actions: list[str] = Field(default_factory=list)
    allowed_repair_surfaces: list[str] = Field(default_factory=list)
    blocked_repair_surfaces: list[str] = Field(default_factory=list)
    evidence_refs: list[EvalEvidenceRef] = Field(default_factory=list)
    verification_requirements: dict = Field(default_factory=dict)
    agent_task_payloads: dict = Field(default_factory=dict)
    details: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None = None


class EvalWorkbenchSummaryResponse(BaseModel):
    open_case_count: int = 0
    awaiting_approval_count: int = 0
    high_severity_count: int = 0
    refreshed_case_count: int = 0
    refreshed_observation_count: int = 0


class EvalWorkbenchResponse(BaseModel):
    schema_name: str = "eval_workbench"
    schema_version: str = "1.0"
    generated_at: datetime
    summary: EvalWorkbenchSummaryResponse
    cases: list[EvalFailureCaseResponse] = Field(default_factory=list)
    approval_queue: list[EvalFailureCaseResponse] = Field(default_factory=list)
    recommended_task_payloads: list[dict] = Field(default_factory=list)
    freshness_warnings: list[str] = Field(default_factory=list)


class EvalFailureCaseRefreshResponse(BaseModel):
    schema_name: str = "eval_failure_case_refresh"
    schema_version: str = "1.0"
    refreshed_at: datetime
    observation_count: int = 0
    case_count: int = 0
    open_case_count: int = 0
    cases: list[EvalFailureCaseResponse] = Field(default_factory=list)


class EvalFailureCaseInspectionResponse(BaseModel):
    schema_name: str = "eval_failure_case_inspection"
    schema_version: str = "1.0"
    case: EvalFailureCaseResponse
    observation: EvalObservationResponse | None = None
    linked_evidence: dict = Field(default_factory=dict)
    recommended_workflow: list[dict] = Field(default_factory=list)


class EvalFailureCaseTriageResponse(BaseModel):
    schema_name: str = "eval_failure_case_triage"
    schema_version: str = "1.0"
    case: EvalFailureCaseResponse
    recommendation: dict = Field(default_factory=dict)
    repair_case: dict = Field(default_factory=dict)
    next_task_payloads: list[dict] = Field(default_factory=list)

