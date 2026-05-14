from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME = "improvement_case_import"
IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION = "1.0"
IMPROVEMENT_CASE_IMPORT_ALL_SOURCE = "all"
ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME = "architecture_quality_report"
AGENT_TRACE_REVIEW_REPORT_SCHEMA_NAME = "agent_trace_review_report"
DEFAULT_ARCHITECTURE_QUALITY_REPORT_PATH = (
    Path("build") / "architecture-governance" / "architecture_quality_report.json"
)
DEFAULT_AGENT_TRACE_REVIEW_REPORT_PATH = (
    Path("build") / "architecture-governance" / "agent_trace_review_report.json"
)


@dataclass(frozen=True, slots=True)
class ImprovementCaseImportSourceContract:
    source: str
    source_kind: Literal["workspace", "file", "database"]
    requires_db_session: bool
    accepts_source_path: bool

    def to_contract(self) -> dict[str, object]:
        return {
            "source": self.source,
            "source_kind": self.source_kind,
            "requires_db_session": self.requires_db_session,
            "accepts_source_path": self.accepts_source_path,
        }


IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS = (
    ImprovementCaseImportSourceContract(
        source="hygiene",
        source_kind="workspace",
        requires_db_session=False,
        accepts_source_path=False,
    ),
    ImprovementCaseImportSourceContract(
        source="architecture-governance-report",
        source_kind="file",
        requires_db_session=False,
        accepts_source_path=True,
    ),
    ImprovementCaseImportSourceContract(
        source="architecture-quality-report",
        source_kind="file",
        requires_db_session=False,
        accepts_source_path=True,
    ),
    ImprovementCaseImportSourceContract(
        source="agent-trace-review-report",
        source_kind="file",
        requires_db_session=False,
        accepts_source_path=True,
    ),
    ImprovementCaseImportSourceContract(
        source="eval-failure-cases",
        source_kind="database",
        requires_db_session=True,
        accepts_source_path=False,
    ),
    ImprovementCaseImportSourceContract(
        source="failed-agent-tasks",
        source_kind="database",
        requires_db_session=True,
        accepts_source_path=False,
    ),
    ImprovementCaseImportSourceContract(
        source="failed-agent-verifications",
        source_kind="database",
        requires_db_session=True,
        accepts_source_path=False,
    ),
)
IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE = {
    contract.source: contract for contract in IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS
}


def list_improvement_case_import_sources() -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                IMPROVEMENT_CASE_IMPORT_ALL_SOURCE,
                *IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE,
            }
        )
    )


def list_improvement_case_import_source_specs() -> tuple[dict[str, object], ...]:
    return tuple(
        contract.to_contract() for contract in IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS
    )
