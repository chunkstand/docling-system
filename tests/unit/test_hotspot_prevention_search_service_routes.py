from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


def test_search_service_root_blocks_new_scenario_groups() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_search_service.py",
            ["def test_search_service_ranking_regression_matrix():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_new_test_group"


def test_search_service_root_blocks_new_helper_sinks() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_search_service.py",
            ["def _build_search_service_fixture():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_helper"


def test_search_service_root_allows_smoke_contract_assertions() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_search_service.py",
            ["def test_search_service_smoke_contract():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "compatibility_assertion"


def test_search_service_root_allows_import_forwarders() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_search_service.py",
            [
                "from tests.unit.test_search_service_ranking_source_filename import (",
                "    test_execute_search_uses_camel_case_source_filename_exact_match,",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "import_forwarder"
