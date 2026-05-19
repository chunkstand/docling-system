from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


def test_reports_claim_support_root_blocks_new_scenario_groups() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_reports_claim_support.py",
            ["def test_claim_support_operator_trace_matrix():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_new_test_group"


def test_reports_claim_support_root_blocks_new_helper_sinks() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_reports_claim_support.py",
            ["def _build_claim_support_context_fixture():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_helper"


def test_reports_claim_support_root_allows_smoke_contract_assertions() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_reports_claim_support.py",
            ["def test_reports_claim_support_smoke_contract():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "compatibility_assertion"


def test_reports_claim_support_root_allows_support_import_forwarders() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_reports_claim_support.py",
            [
                "from tests.unit.agent_task_context_reports_claim_support_support import (",
                "    build_task_context_payload,",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "import_forwarder"


def test_graph_promotions_root_blocks_new_scenario_groups() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
            ["def test_graph_promotions_edge_conflict_matrix():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_new_test_group"


def test_graph_promotions_root_blocks_new_helper_sinks() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
            ["def _build_graph_promotion_fixture():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_helper"


def test_graph_promotions_root_allows_smoke_contract_assertions() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
            ["def test_graph_promotions_smoke_contract():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "compatibility_assertion"


def test_graph_promotions_root_allows_support_import_forwarders() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
            [
                "from tests.unit.agent_task_context_semantic_graph_promotions_support import (",
                "    build_task_context_payload,",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "import_forwarder"


def test_agent_task_context_support_modules_allow_deletion_only_reduction() -> None:
    for path in [
        "tests/unit/agent_task_context_reports_claim_support_support.py",
        "tests/unit/agent_task_context_semantic_graph_promotions_support.py",
    ]:
        report = build_hotspot_prevention_report(
            _diff_for(path, [], deleted_lines=["def _legacy_helper():", "    return {}"]),
            policy=load_hotspot_policy(),
            project_root=Path.cwd(),
        )

        assert report["summary"]["blocked_count"] == 0
        assert report["findings"][0]["category"] == "deletion"
