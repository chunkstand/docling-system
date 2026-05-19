from __future__ import annotations

import json
from pathlib import Path

from app.architecture_quality import (
    ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME,
    build_architecture_quality_report,
    build_architecture_quality_summary,
    run,
)
from app.hotspot_prevention_policy import load_hotspot_policy


def _inspection_report() -> dict:
    return {
        "valid": True,
        "violation_count": 0,
        "measurement": {},
        "architecture_map": {
            "contracts": [
                {
                    "name": "capability_surface_contracts",
                    "decision_ids": ["ADR-0002"],
                }
            ]
        },
    }


def test_architecture_quality_report_ranks_hotspots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "large.py").write_text(
        "\n".join(["def public_function():", "    return 1"] * 80)
    )
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_search_api.py").write_text("def test_ok(): pass\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "retrieval_repair_loop.md").write_text("Retrieval examples.\n")
    (tmp_path / "config").mkdir()

    monkeypatch.setattr(
        "app.architecture_quality.build_capability_contract_map",
        lambda _root: {
            "facades": [
                {
                    "name": "retrieval",
                    "module": "app.services.capabilities.retrieval",
                    "function_count": 42,
                    "owner_modules": ["app.services.search"],
                    "exported_instance": "retrieval",
                    "protocol_source": "app/services/capabilities/retrieval_contract.py",
                    "implementation_source": "app/services/capabilities/retrieval_services.py",
                }
            ]
        },
    )
    monkeypatch.setattr(
        "app.architecture_quality.collect_git_churn_metrics",
        lambda _root: {"app/large.py": {"changes_30d": 3, "changes_90d": 9}},
    )
    monkeypatch.setattr(
        "app.architecture_quality._open_improvement_cases_by_path",
        lambda _root: {"app/large.py": 1},
    )

    report = build_architecture_quality_report(
        tmp_path,
        inspection_report=_inspection_report(),
        include_hygiene=False,
    )

    assert report["schema_name"] == ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME
    assert report["valid"] is True
    assert report["hotspots"][0]["relative_path"] == "app/large.py"
    assert report["improvement_case_candidates"][0]["source_ref"] == (
        "architecture-quality:hotspot:app/large.py"
    )
    surface = report["agent_legibility"]["surfaces"][0]
    assert surface["criteria"]["bounded_surface"] is False
    assert surface["criteria"]["has_tests"] is True
    assert surface["criteria"]["has_examples"] is True
    assert surface["criteria"]["has_trace_or_replay_command"] is True
    assert surface["criteria"]["has_decision_rationale"] is True


def test_architecture_quality_summary_is_compact(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "small.py").write_text("def ok():\n    return 1\n")
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr(
        "app.architecture_quality.build_capability_contract_map",
        lambda _root: {"facades": []},
    )
    monkeypatch.setattr("app.architecture_quality.collect_git_churn_metrics", lambda _root: {})
    monkeypatch.setattr(
        "app.architecture_quality._open_improvement_cases_by_path",
        lambda _root: {},
    )

    summary = build_architecture_quality_summary(
        tmp_path,
        inspection_report=_inspection_report(),
    )

    assert summary["schema_name"] == "architecture_quality_summary"
    assert "top_hotspot_paths" in summary
    assert "top_routed_hotspot_paths" in summary
    assert "routing_trap_paths" in summary
    assert "stale_facade_hotspot_count" in summary
    assert "hotspots" not in summary


def test_architecture_quality_summary_uses_extended_hotspot_window(
    monkeypatch,
) -> None:
    seen: dict[str, int] = {}

    def _fake_build_report(
        project_root=None,
        *,
        inspection_report=None,
        max_hotspots: int,
        include_hygiene: bool,
    ) -> dict:
        seen["max_hotspots"] = max_hotspots
        assert include_hygiene is False
        return {
            "schema_name": ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME,
            "summary": {
                "top_hotspot_paths": [],
                "top_routed_hotspot_paths": ["tests/unit/test_search_api.py"],
                "routing_trap_paths": ["tests/unit/test_hotspot_prevention.py"],
                "stale_facade_hotspot_count": 1,
                "max_hotspot_risk_score": 1.0,
                "agent_legibility_average_score": 100.0,
                "broad_facade_count": 0,
            },
            "hotspot_count": 1,
        }

    monkeypatch.setattr(
        "app.architecture_quality.build_architecture_quality_report",
        _fake_build_report,
    )

    summary = build_architecture_quality_summary(
        inspection_report=_inspection_report(),
    )

    assert seen["max_hotspots"] == 20
    assert summary["top_routed_hotspot_paths"] == ["tests/unit/test_search_api.py"]


def test_architecture_quality_summary_prefers_routed_queue_over_deferred_facade(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tests_unit = tmp_path / "tests" / "unit"
    tests_unit.mkdir(parents=True)
    (tests_unit / "test_hotspot_prevention.py").write_text(
        "\n".join(
            f"def test_hotspot_prevention_{index}():\n    assert True\n"
            for index in range(120)
        )
    )
    (tests_unit / "test_search_api.py").write_text(
        "\n".join(
            f"def test_search_api_{index}():\n    assert True\n" for index in range(80)
        )
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "hotspot_prevention.yaml").write_text(
        """schema_name: hotspot_prevention_policy
schema_version: "1.0"
known_hotspots:
  tests/unit/test_hotspot_prevention.py:
    target_role: hotspot-prevention analyzer smoke and compatibility tests
    preferred_owner_modules:
      - tests/unit/test_hotspot_prevention_*.py
    routing:
      status: deferred_reduced_facade
      reason: Root hotspot-prevention coverage is already reduced.
      route_to_case_ids:
        - IC-ROUTE-HOTSPOT
      route_to_paths:
        - tests/unit/test_hotspot_prevention_policy_contracts.py
      route_to_plan_paths:
        - docs/hotspot_prevention_family_boundary_milestone_plan.md
    block_new:
      - broad_new_test_group
      - broad_helper
    allow:
      - compatibility_assertion
      - deletion
"""
    )
    monkeypatch.setattr(
        "app.architecture_quality.build_capability_contract_map",
        lambda _root: {"facades": []},
    )
    monkeypatch.setattr(
        "app.architecture_quality.collect_git_churn_metrics",
        lambda _root: {
            "tests/unit/test_hotspot_prevention.py": {
                "changes_30d": 2,
                "changes_90d": 12,
            },
            "tests/unit/test_search_api.py": {
                "changes_30d": 2,
                "changes_90d": 10,
            },
        },
    )
    monkeypatch.setattr(
        "app.architecture_quality._improvement_case_registry_index",
        lambda _root: (
            {},
            {"IC-ROUTE-HOTSPOT": {"status": "deployed", "deployed_ref": "463d3fc"}},
        ),
    )

    summary = build_architecture_quality_summary(
        tmp_path,
        inspection_report=_inspection_report(),
    )

    assert summary["top_hotspot_paths"][0] == "tests/unit/test_hotspot_prevention.py"
    assert summary["top_routed_hotspot_paths"][0] == "tests/unit/test_search_api.py"
    assert "tests/unit/test_hotspot_prevention.py" in summary["routing_trap_paths"]


def test_current_hotspot_policy_routes_hotspot_prevention_root_off_active_queue() -> None:
    policy = load_hotspot_policy()

    assert "tests/unit/test_hotspot_prevention.py" in policy.known_hotspots
    assert policy.known_hotspots["tests/unit/test_hotspot_prevention.py"].routing is not None
    assert (
        policy.known_hotspots["tests/unit/test_hotspot_prevention.py"].routing.status
        == "deferred_reduced_facade"
    )


def test_architecture_quality_cli_prints_json(capsys, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.architecture_quality.build_architecture_quality_summary",
        lambda: {
            "schema_name": "architecture_quality_summary",
            "schema_version": "1.0",
            "hotspot_count": 0,
        },
    )

    exit_code = run(["--summary"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_name"] == "architecture_quality_summary"
