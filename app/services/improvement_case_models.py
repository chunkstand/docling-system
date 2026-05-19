from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

DEFAULT_IMPROVEMENT_CASES_PATH = Path("config") / "improvement_cases.yaml"
IMPROVEMENT_CASE_SCHEMA_NAME = "improvement_cases"
IMPROVEMENT_CASE_SCHEMA_VERSION = "1.0"

IMPROVEMENT_CAUSE_CLASSES = frozenset(
    {
        "bad_pattern",
        "bad_tool",
        "missing_constraint",
        "missing_context",
        "missing_test",
        "unclear_ownership",
        "unsafe_permission",
    }
)
IMPROVEMENT_ARTIFACT_TYPES = frozenset(
    {
        "contract",
        "eval",
        "generated_map",
        "lint",
        "permission_rule",
        "runbook",
        "script",
        "test",
    }
)
IMPROVEMENT_CASE_STATUSES = frozenset(
    {
        "open",
        "converted",
        "verified",
        "deployed",
        "measured",
        "closed",
        "suppressed",
    }
)
IMPROVEMENT_SOURCE_TYPES = frozenset(
    {
        "agent_task",
        "agent_verification",
        "architecture_governance",
        "bad_diff",
        "eval_failure",
        "flaky_test",
        "hygiene_finding",
        "incident",
        "operator_note",
        "review_comment",
        "runtime_failure",
        "search_replay",
        "tool_confusion",
        "other",
    }
)
DEPLOYED_IMPROVEMENT_STATUSES = frozenset({"deployed", "measured", "closed"})
MEASURED_IMPROVEMENT_STATUSES = frozenset({"measured", "closed"})
CONVERTED_IMPROVEMENT_STATUSES = frozenset(
    {"converted", "verified", "deployed", "measured", "closed"}
)
VERIFIED_IMPROVEMENT_STATUSES = frozenset({"verified", "deployed", "measured", "closed"})


class ImprovementCaseSource(BaseModel):
    source_type: str = ""
    source_ref: str | None = None
    notes: str | None = None


class ImprovementCaseArtifact(BaseModel):
    artifact_type: str = ""
    target_path: str = ""
    description: str = ""


class ImprovementCaseVerification(BaseModel):
    commands: list[str] = Field(default_factory=list)
    acceptance_conditions: list[str] = Field(default_factory=list)
    catches_old_failure: bool = False
    allows_good_changes: bool = False


class ImprovementCaseDeployment(BaseModel):
    deployed_ref: str | None = None
    notes: str | None = None


class ImprovementCaseMeasurement(BaseModel):
    metric_name: str | None = None
    current_value: float | None = None
    measurement_window: str | None = None
    notes: str | None = None


class ImprovementCase(BaseModel):
    case_id: str = ""
    title: str = ""
    status: str = "open"
    cause_class: str = ""
    observed_failure: str = ""
    source: ImprovementCaseSource = Field(default_factory=ImprovementCaseSource)
    artifact: ImprovementCaseArtifact = Field(default_factory=ImprovementCaseArtifact)
    verification: ImprovementCaseVerification = Field(default_factory=ImprovementCaseVerification)
    workflow_version: str = "improvement_v1"
    deployment: ImprovementCaseDeployment = Field(default_factory=ImprovementCaseDeployment)
    measurement: ImprovementCaseMeasurement = Field(default_factory=ImprovementCaseMeasurement)
    created_at: str | None = None
    updated_at: str | None = None


class ImprovementCaseObservation(BaseModel):
    title: str
    observed_failure: str
    cause_class: str
    source_type: str
    source_ref: str
    source_notes: str | None = None
    artifact_type: str | None = None
    artifact_target_path: str | None = None
    artifact_description: str | None = None
    verification_commands: list[str] = Field(default_factory=list)
    acceptance_conditions: list[str] = Field(default_factory=list)
    workflow_version: str = "improvement_v1"


class ImprovementCaseRegistry(BaseModel):
    schema_name: str = IMPROVEMENT_CASE_SCHEMA_NAME
    schema_version: str = IMPROVEMENT_CASE_SCHEMA_VERSION
    cases: list[ImprovementCase] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ImprovementCaseContractIssue:
    case_id: str | None
    field: str
    message: str


def improvement_payload_fingerprint(payload: object) -> str:
    encoded = yaml.safe_dump(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def deterministic_improvement_case_id(source_type: str, source_ref: str) -> str:
    digest = improvement_payload_fingerprint(
        {"source_type": source_type, "source_ref": source_ref}
    )
    return f"IC-{digest[:12].upper()}"


def clip_improvement_case_text(value: object, *, max_length: int = 140) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def classify_improvement_case_cause(*values: object, default: str = "missing_test") -> str:
    text = " ".join(str(value or "").lower() for value in values)
    if any(token in text for token in ("permission", "auth", "credential", "secret")):
        return "unsafe_permission"
    if "tool" in text:
        return "bad_tool"
    if any(token in text for token in ("owner", "ownership", "handoff")):
        return "unclear_ownership"
    if any(token in text for token in ("context", "provenance", "artifact", "source ref")):
        return "missing_context"
    if any(token in text for token in ("test", "eval", "coverage", "fixture")):
        return "missing_test"
    if any(token in text for token in ("contract", "constraint", "schema", "policy", "gate")):
        return "missing_constraint"
    if any(token in text for token in ("pattern", "duplicate", "budget", "lint", "ruff")):
        return "bad_pattern"
    return default
