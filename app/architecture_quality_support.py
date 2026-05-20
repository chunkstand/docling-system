from __future__ import annotations

from typing import Any

from app.architecture_quality_hotspots import HOTSPOT_ROUTING_TRAP_STATUSES
from app.hygiene import HygieneFinding

BROADER_REBASELINE_MIN_LINE_COUNT = 600


def _risk_score(
    *,
    line_count: int,
    public_function_count: int,
    private_function_count: int,
    class_count: int,
    changes_30d: int,
    changes_90d: int,
    hygiene_finding_count: int,
    open_improvement_case_count: int,
) -> float:
    return round(
        (line_count / 150)
        + (public_function_count * 2.0)
        + (private_function_count * 0.75)
        + (class_count * 1.5)
        + (changes_30d * 5.0)
        + (changes_90d * 2.0)
        + (hygiene_finding_count * 8.0)
        + (open_improvement_case_count * 6.0),
        2,
    )


def _broader_rebaseline_surface_priority(relative_path: str) -> int:
    if relative_path.startswith("app/services/"):
        return 0
    if relative_path.startswith("app/"):
        return 1
    if relative_path.startswith("tests/"):
        return 2
    return 3


def _broader_rebaseline_candidate_sort_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _broader_rebaseline_surface_priority(candidate["artifact_target_path"]),
        -candidate["risk_score"],
        -candidate["line_count"],
        -candidate["changes_90d"],
        candidate["artifact_target_path"],
    )


def build_broader_rebaseline_candidates(
    *,
    hotspots: list[dict[str, Any]],
    file_metrics: dict[str, dict[str, int | str]],
    churn_metrics: dict[str, dict[str, int]],
    hygiene_findings_by_path: dict[str, list[HygieneFinding]],
    open_cases_by_path: dict[str, int],
) -> list[dict[str, Any]]:
    if any(row["selected_for_routed_queue"] for row in hotspots):
        return []

    candidates_by_path: dict[str, dict[str, Any]] = {}
    for hotspot in hotspots:
        if hotspot.get("routing_status") not in HOTSPOT_ROUTING_TRAP_STATUSES:
            continue
        route_to_case_statuses = hotspot.get("route_to_case_statuses") or {}
        if not route_to_case_statuses or any(
            status != "deployed" for status in route_to_case_statuses.values()
        ):
            continue
        for route_path in hotspot.get("route_to_paths") or []:
            metrics = file_metrics.get(route_path)
            if not metrics:
                continue
            line_count = int(metrics["line_count"])
            if line_count < BROADER_REBASELINE_MIN_LINE_COUNT:
                continue
            churn = churn_metrics.get(route_path, {})
            hygiene_findings = hygiene_findings_by_path.get(route_path, [])
            public_function_count = int(metrics["public_function_count"])
            private_function_count = int(metrics["private_function_count"])
            class_count = int(metrics["class_count"])
            changes_30d = int(churn.get("changes_30d", 0))
            changes_90d = int(churn.get("changes_90d", 0))
            open_improvement_case_count = int(open_cases_by_path.get(route_path, 0))
            risk_score = _risk_score(
                line_count=line_count,
                public_function_count=public_function_count,
                private_function_count=private_function_count,
                class_count=class_count,
                changes_30d=changes_30d,
                changes_90d=changes_90d,
                hygiene_finding_count=len(hygiene_findings),
                open_improvement_case_count=open_improvement_case_count,
            )
            candidate = {
                "source_ref": f"architecture-quality:broader-rebaseline:{route_path}",
                "title": f"Broader rebaseline candidate: {route_path}",
                "artifact_target_path": route_path,
                "cause_class": "unclear_ownership",
                "observed_failure": (
                    f"{route_path} remains a routed owner candidate with risk_score="
                    f"{risk_score}, line_count={line_count}, changes_90d={changes_90d}, "
                    f"and predecessor hotspot {hotspot['relative_path']} already closed as "
                    f"{hotspot['routing_status']}."
                ),
                "verification_command": "uv run docling-system-architecture-quality-report",
                "stop_condition": (
                    "A fresh broader-reselect packet reduces the routed owner below the "
                    "default 600-line budget or records a narrower honest successor boundary."
                ),
                "risk_score": risk_score,
                "line_count": line_count,
                "public_function_count": public_function_count,
                "private_function_count": private_function_count,
                "class_count": class_count,
                "changes_30d": changes_30d,
                "changes_90d": changes_90d,
                "hygiene_finding_count": len(hygiene_findings),
                "open_improvement_case_count": open_improvement_case_count,
                "source_hotspot_path": hotspot["relative_path"],
                "source_hotspot_risk_score": hotspot["risk_score"],
                "routing_status": hotspot["routing_status"],
                "route_reason": hotspot["route_reason"],
                "route_to_case_ids": hotspot["route_to_case_ids"],
                "route_to_case_statuses": hotspot["route_to_case_statuses"],
                "route_to_plan_paths": hotspot["route_to_plan_paths"],
                "selected_for_broader_rebaseline": True,
            }
            existing = candidates_by_path.get(route_path)
            if existing is None or _broader_rebaseline_candidate_sort_key(
                candidate
            ) < _broader_rebaseline_candidate_sort_key(existing):
                candidates_by_path[route_path] = candidate

    return sorted(
        candidates_by_path.values(),
        key=_broader_rebaseline_candidate_sort_key,
    )


def build_hotspots(
    *,
    file_metrics: dict[str, dict[str, int | str]],
    churn_metrics: dict[str, dict[str, int]],
    hygiene_findings_by_path: dict[str, list[HygieneFinding]],
    open_cases_by_path: dict[str, int],
    max_hotspots: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative_path, metrics in file_metrics.items():
        churn = churn_metrics.get(relative_path, {})
        hygiene_findings = hygiene_findings_by_path.get(relative_path, [])
        line_count = int(metrics["line_count"])
        public_function_count = int(metrics["public_function_count"])
        private_function_count = int(metrics["private_function_count"])
        class_count = int(metrics["class_count"])
        changes_30d = int(churn.get("changes_30d", 0))
        changes_90d = int(churn.get("changes_90d", 0))
        open_improvement_case_count = int(open_cases_by_path.get(relative_path, 0))
        score = _risk_score(
            line_count=line_count,
            public_function_count=public_function_count,
            private_function_count=private_function_count,
            class_count=class_count,
            changes_30d=changes_30d,
            changes_90d=changes_90d,
            hygiene_finding_count=len(hygiene_findings),
            open_improvement_case_count=open_improvement_case_count,
        )
        if score <= 0:
            continue
        rows.append(
            {
                "relative_path": relative_path,
                "risk_score": score,
                "line_count": line_count,
                "public_function_count": public_function_count,
                "private_function_count": private_function_count,
                "class_count": class_count,
                "changes_30d": changes_30d,
                "changes_90d": changes_90d,
                "hygiene_finding_count": len(hygiene_findings),
                "open_improvement_case_count": open_improvement_case_count,
                "hygiene_findings": [
                    {
                        "kind": finding.kind,
                        "message": finding.message,
                        "lineno": finding.lineno,
                    }
                    for finding in hygiene_findings[:5]
                ],
            }
        )
    return sorted(
        rows,
        key=lambda row: (-row["risk_score"], row["relative_path"]),
    )[:max_hotspots]
