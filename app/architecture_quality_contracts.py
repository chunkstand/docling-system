from __future__ import annotations

from pathlib import Path

ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME = "architecture_quality_report"
ARCHITECTURE_QUALITY_SUMMARY_SCHEMA_NAME = "architecture_quality_summary"
DEFAULT_ARCHITECTURE_QUALITY_REPORT_PATH = (
    Path("build") / "architecture-governance" / "architecture_quality_report.json"
)

ARCHITECTURE_QUALITY_REPORT_FIELDS = (
    "schema_name",
    "schema_version",
    "generated_at",
    "valid",
    "inspection_violation_count",
    "source_roots",
    "hotspot_count",
    "hotspots",
    "agent_legibility",
    "improvement_case_candidates",
    "raw_improvement_case_candidates",
    "summary",
)

ARCHITECTURE_QUALITY_SUMMARY_FIELDS = (
    "schema_name",
    "schema_version",
    "hotspot_count",
    "top_hotspot_paths",
    "top_routed_hotspot_paths",
    "routing_trap_paths",
    "stale_facade_hotspot_count",
    "max_hotspot_risk_score",
    "agent_legibility_average_score",
    "broad_facade_count",
    "legibility_gap_count",
)
