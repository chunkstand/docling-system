from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


def test_analyzer_blocks_search_harness_cli_facade_implementation_growth() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/cli_commands/search_harness.py",
            ["def run_new_search_harness_command():", "    print('x')"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["relative_path"] == "app/cli_commands/search_harness.py"
    assert report["findings"][0]["category"] == "command_implementation"


def test_analyzer_blocks_search_harness_cli_smoke_test_regrowth() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/unit/test_cli_search_harness.py",
            ["def test_new_search_harness_group():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["relative_path"] == "tests/unit/test_cli_search_harness.py"
    assert report["findings"][0]["category"] == "broad_new_test_group"
