from __future__ import annotations

from pathlib import Path
from typing import Any

from app.hotspot_prevention_policy import (
    POLICY_SCHEMA_NAME as HOTSPOT_POLICY_SCHEMA_NAME,
)
from app.hotspot_prevention_policy import (
    SCHEMA_VERSION as HOTSPOT_POLICY_SCHEMA_VERSION,
)
from app.hotspot_prevention_policy import HotspotPolicy, load_hotspot_policy

HOTSPOT_ROUTING_TRAP_STATUSES = frozenset(
    {"compatibility_facade_trap", "deferred_reduced_facade"}
)
HOTSPOT_ROUTED_QUEUE_ACTIVE_STATUSES = frozenset({"active_owner"})
HOTSPOT_CANDIDATE_MIN_RISK_SCORE = 40.0


def load_hotspot_policy_safe(
    project_root: Path,
    *,
    loader=load_hotspot_policy,
) -> HotspotPolicy:
    try:
        return loader(project_root=project_root)
    except FileNotFoundError:
        return HotspotPolicy(
            schema_name=HOTSPOT_POLICY_SCHEMA_NAME,
            schema_version=HOTSPOT_POLICY_SCHEMA_VERSION,
            known_hotspots={},
        )


def annotate_hotspots_with_routing(
    hotspots: list[dict[str, Any]],
    *,
    policy: HotspotPolicy,
    case_statuses: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for hotspot in hotspots:
        relative_path = str(hotspot["relative_path"])
        rule = policy.known_hotspots.get(relative_path)
        routing = rule.routing if rule is not None else None
        if routing is None:
            annotated.append(
                {
                    **hotspot,
                    "routing_status": "active_owner",
                    "route_reason": "Raw hotspot remains the honest next owner surface.",
                    "route_to_case_ids": [],
                    "route_to_case_statuses": {},
                    "route_to_paths": [],
                    "route_to_plan_paths": [],
                    "selected_for_routed_queue": True,
                }
            )
            continue
        route_to_case_ids = list(routing.route_to_case_ids)
        annotated.append(
            {
                **hotspot,
                "routing_status": routing.status,
                "route_reason": routing.reason,
                "route_to_case_ids": route_to_case_ids,
                "route_to_case_statuses": {
                    case_id: (case_statuses.get(case_id) or {}).get("status") or "unknown"
                    for case_id in route_to_case_ids
                },
                "route_to_paths": list(routing.route_to_paths),
                "route_to_plan_paths": list(routing.route_to_plan_paths),
                "selected_for_routed_queue": (
                    routing.status in HOTSPOT_ROUTED_QUEUE_ACTIVE_STATUSES
                ),
            }
        )
    return annotated


def _quality_candidate_from_hotspot(hotspot: dict[str, Any]) -> dict[str, Any]:
    candidate = {
        "source_ref": f"architecture-quality:hotspot:{hotspot['relative_path']}",
        "title": f"Architecture hotspot: {hotspot['relative_path']}",
        "artifact_target_path": hotspot["relative_path"],
        "cause_class": "unclear_ownership",
        "observed_failure": (
            f"{hotspot['relative_path']} is an architecture hotspot with risk_score="
            f"{hotspot['risk_score']}, line_count={hotspot['line_count']}, "
            f"changes_90d={hotspot['changes_90d']}, "
            f"hygiene_finding_count={hotspot['hygiene_finding_count']}."
        ),
        "verification_command": "uv run docling-system-architecture-quality-report",
        "stop_condition": (
            "Hotspot risk decreases or the surface has a narrower owner contract."
        ),
    }
    for field in (
        "routing_status",
        "route_reason",
        "route_to_case_ids",
        "route_to_case_statuses",
        "route_to_paths",
        "route_to_plan_paths",
        "selected_for_routed_queue",
    ):
        if field in hotspot:
            candidate[field] = hotspot[field]
    return candidate


def quality_candidates_from_hotspots(
    hotspots: list[dict[str, Any]],
    *,
    min_risk_score: float = HOTSPOT_CANDIDATE_MIN_RISK_SCORE,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for hotspot in hotspots:
        if hotspot["risk_score"] < min_risk_score:
            continue
        candidates.append(_quality_candidate_from_hotspot(hotspot))
    return candidates
