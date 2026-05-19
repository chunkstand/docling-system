from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


def test_agent_task_router_blocks_new_route_families() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/api/routers/agent_tasks.py",
            ["@router.get('/agent-tasks/new-family')"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "route_family_implementation"


def test_agent_task_router_allows_registration_and_alias_forwarding() -> None:
    registration_report = build_hotspot_prevention_report(
        _diff_for(
            "app/api/routers/agent_tasks.py",
            ["router.include_router(agent_task_lifecycle.router)"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    alias_report = build_hotspot_prevention_report(
        _diff_for(
            "app/api/routers/agent_tasks.py",
            [
                "from app.api.routers import agent_task_lifecycle",
                "list_agent_tasks = agent_task_lifecycle.list_agent_tasks",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert registration_report["summary"]["blocked_count"] == 0
    assert registration_report["findings"][0]["category"] == "router_registration"
    assert alias_report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in alias_report["findings"]} == {"alias_forwarder"}
