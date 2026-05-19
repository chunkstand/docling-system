from __future__ import annotations

import json
from pathlib import Path

from app.architecture_quality import (
    ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME,
    build_architecture_quality_report,
    build_architecture_quality_summary,
    run,
)


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
