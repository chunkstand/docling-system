from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


def test_retrieval_learning_root_blocks_new_scenario_groups() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/integration/test_retrieval_learning_ledger.py",
            ["def test_candidate_judgment_release_readiness():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_new_test_group"


def test_retrieval_learning_root_allows_smoke_contract_assertions() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/integration/test_retrieval_learning_ledger.py",
            ["def test_retrieval_learning_smoke_contract():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "compatibility_assertion"


def test_retrieval_learning_root_allows_audit_closeout_exception() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/integration/test_retrieval_learning_ledger.py",
            [
                "def test_training_audit_payload_closeout():",
                '    assert training_audit_payload["retrieval_hard_negatives"]',
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["summary"]["exception_count"] == 1
    assert report["findings"][0]["status"] == "allowed_exception"
    assert report["findings"][0]["category"] == "broad_new_test_group"
    assert report["findings"][0]["exception_id"] == "retrieval-learning-smoke-audit-closeout"


def test_retrieval_learning_support_allows_deletion_only_reduction() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/integration/retrieval_learning_ledger_support.py",
            [],
            deleted_lines=["def _legacy_fixture_helper():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "deletion"
