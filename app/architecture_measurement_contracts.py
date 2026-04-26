from __future__ import annotations

from pathlib import Path

ARCHITECTURE_MEASUREMENT_SCHEMA_NAME = "architecture_inspection_measurement"
ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME = "architecture_measurement_record"
ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME = "architecture_measurement_history"
ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME = "architecture_measurement_summary"
DEFAULT_ARCHITECTURE_MEASUREMENT_HISTORY_PATH = (
    Path("storage") / "architecture_inspections" / "history.jsonl"
)

ARCHITECTURE_MEASUREMENT_FIELDS = (
    "schema_name",
    "schema_version",
    "severity_counts",
    "non_ignored_violation_count",
    "contract_count",
    "inspection_rule_count",
    "rule_violation_counts",
    "contract_violation_counts",
    "api_route_count",
    "agent_action_count",
)
ARCHITECTURE_MEASUREMENT_DELTA_FIELDS = (
    "non_ignored_violation_count",
    "error_count",
    "warning_count",
    "info_count",
    "contract_count",
    "rule_violation_counts",
    "contract_violation_counts",
)
ARCHITECTURE_MEASUREMENT_SUMMARY_FIELDS = (
    "schema_name",
    "schema_version",
    "history_schema_name",
    "history_path",
    "record_count",
    "latest",
    "previous",
    "latest_rule_violation_counts",
    "latest_contract_violation_counts",
    "deltas",
)
