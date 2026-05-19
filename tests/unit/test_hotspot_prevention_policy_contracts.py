from __future__ import annotations

import json
import tomllib
from datetime import date
from pathlib import Path

import yaml

from app.hotspot_prevention import (
    POLICY_SCHEMA_NAME,
    REPORT_SCHEMA_NAME,
    build_hotspot_prevention_report,
    collect_git_diff,
    collect_git_numstat,
    load_hotspot_policy,
    parse_numstat,
    run,
    validate_policy_payload,
)
from tests.unit.hotspot_prevention_test_support import _diff_for, _policy_for


def test_current_hotspot_policy_loads_expected_surfaces() -> None:
    policy = load_hotspot_policy()

    assert sorted(policy.known_hotspots) == [
        "app/api/main.py",
        "app/api/routers/agent_tasks.py",
        "app/cli.py",
        "app/db/models.py",
        "app/schemas/agent_tasks.py",
        "app/schemas/search.py",
        "app/services/agent_actions/search_harness.py",
        "app/services/agent_actions/semantic_governance_actions.py",
        "app/services/agent_task_actions.py",
        "app/services/agent_task_context.py",
        "app/services/agent_task_context_search_harness.py",
        "app/services/agent_task_context_semantic_governance.py",
        "app/services/agent_tasks.py",
        "app/services/audit_bundles.py",
        "app/services/claim_support_evaluations.py",
        "app/services/claim_support_policy_governance.py",
        "app/services/claim_support_policy_impact_replay.py",
        "app/services/claim_support_policy_impact_views.py",
        "app/services/claim_support_policy_impacts.py",
        "app/services/claim_support_replay_alert_fixture_corpus.py",
        "app/services/claim_support_replay_alert_promotions.py",
        "app/services/evaluations.py",
        "app/services/evidence.py",
        "app/services/evidence_provenance_exports.py",
        "app/services/search.py",
        "app/services/semantics.py",
        "tests/db_model_contract.py",
        "tests/integration/retrieval_learning_ledger_support.py",
        "tests/integration/technical_report_harness_support.py",
        "tests/integration/test_claim_support_judge_evaluation_roundtrip.py",
        "tests/integration/test_retrieval_learning_ledger.py",
        "tests/integration/test_technical_report_harness_roundtrip.py",
        "tests/unit/agent_task_context_reports_claim_support_support.py",
        "tests/unit/agent_task_context_semantic_graph_promotions_support.py",
        "tests/unit/test_agent_task_context.py",
        "tests/unit/test_agent_task_context_reports_claim_support.py",
        "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
        "tests/unit/test_agent_tasks_api.py",
        "tests/unit/test_architecture_inspection.py",
        "tests/unit/test_cli.py",
        "tests/unit/test_db_model_import_compatibility.py",
        "tests/unit/test_documents_api.py",
        "tests/unit/test_evaluation_service.py",
        "tests/unit/test_hotspot_prevention.py",
        "tests/unit/test_search_api.py", "tests/unit/test_search_service.py",
    ]
    for rule in policy.known_hotspots.values():
        assert rule.preferred_owner_modules
        assert rule.block_new
    assert policy.known_hotspots["app/db/models.py"].routing is not None
    assert policy.known_hotspots["app/db/models.py"].routing.status == "compatibility_facade_trap"
    assert policy.known_hotspots["app/api/main.py"].routing is not None
    assert policy.known_hotspots["app/api/main.py"].routing.status == "accepted_residual"
    assert policy.known_hotspots["app/services/audit_bundles.py"].routing is not None
    assert (
        policy.known_hotspots["app/services/audit_bundles.py"].routing.status
        == "compatibility_facade_trap"
    )
    for path in [
        "app/cli.py",
        "app/api/routers/agent_tasks.py",
        "tests/integration/test_retrieval_learning_ledger.py",
        "tests/unit/test_agent_tasks_api.py",
        "tests/unit/test_architecture_inspection.py",
        "tests/unit/test_search_api.py",
        "tests/unit/test_documents_api.py",
        "tests/unit/test_agent_task_context_reports_claim_support.py",
        "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
        "app/schemas/search.py",
        "tests/unit/test_db_model_import_compatibility.py",
    ]:
        assert policy.known_hotspots[path].routing is not None
        assert policy.known_hotspots[path].routing.status == "deferred_reduced_facade"
    assert policy.known_hotspots["tests/unit/test_cli.py"].routing is not None
    assert policy.known_hotspots["app/services/search.py"].routing is not None
    assert (
        policy.known_hotspots["tests/integration/retrieval_learning_ledger_support.py"].routing
        is not None
    )
    assert (
        policy.known_hotspots["tests/integration/retrieval_learning_ledger_support.py"].routing.status
        == "accepted_residual"
    )
    for path in [
        "tests/unit/agent_task_context_reports_claim_support_support.py",
        "tests/unit/agent_task_context_semantic_graph_promotions_support.py",
    ]:
        assert policy.known_hotspots[path].routing is not None
        assert policy.known_hotspots[path].routing.status == "accepted_residual"


def test_policy_validation_rejects_missing_owner_and_unowned_exception() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": [],
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
                "exceptions": [
                    {
                        "exception_id": "temporary",
                        "follow_up_condition": "remove after split",
                    }
                ],
            }
        },
    }

    issues = validate_policy_payload(payload)

    fields = {issue.field for issue in issues}
    assert "known_hotspots.app/services/evidence.py.preferred_owner_modules" in fields
    assert "known_hotspots.app/services/evidence.py.exceptions[0].case_id" in fields
    assert "known_hotspots.app/services/evidence.py.exceptions[0].owner_module" in fields


def test_policy_validation_rejects_expired_exceptions() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": ["app/services/evidence_new.py"],
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
                "exceptions": [
                    {
                        "exception_id": "temporary",
                        "milestone_id": "residual-weakness-milestone-1",
                        "owner_module": "app/services/evidence_new.py",
                        "expires_on": "2026-05-01",
                    }
                ],
            }
        },
    }

    issues = validate_policy_payload(payload, today=date(2026, 5, 10))

    assert (
        "known_hotspots.app/services/evidence.py.exceptions[0].expires_on",
        "is expired",
    ) in {(issue.field, issue.message) for issue in issues}


def test_policy_validation_rejects_trap_routing_without_successors() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": ["app/services/evidence_*.py"],
                "routing": {
                    "status": "compatibility_facade_trap",
                    "reason": "Facade is already reduced.",
                },
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
            }
        },
    }

    issues = validate_policy_payload(payload)

    assert {
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_case_ids",
            "must contain at least one routed case id",
        ),
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_paths",
            "must contain at least one routed path",
        ),
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_plan_paths",
            "must contain at least one routed plan path",
        ),
    } <= {(issue.field, issue.message) for issue in issues}


def test_report_includes_numstat_line_counts() -> None:
    numstat = "2\t1\tapp/services/evidence.py\n"

    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            ["def _assemble_payload():", "    return {}"],
            deleted_lines=["def _old_helper():"],
        ),
        numstat_text=numstat,
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert parse_numstat(numstat)["app/services/evidence.py"].added_line_count == 2
    assert report["summary"]["added_line_count"] == 2
    assert report["summary"]["deleted_line_count"] == 1
    assert report["changed_files"] == [
        {
            "relative_path": "app/services/evidence.py",
            "added_line_count": 2,
            "deleted_line_count": 1,
            "source": "numstat",
            "known_hotspot": True,
        }
    ]
    assert report["findings"][0]["added_line_count"] == 2
    assert report["findings"][0]["deleted_line_count"] == 1


def test_policy_exception_requires_ownership_and_allows_marked_growth() -> None:
    policy = _policy_for(
        "app/services/evidence.py",
        exceptions=[
            {
                "exception_id": "HPG-TEST-1",
                "milestone_id": "residual-weakness-milestone-1",
                "owner_module": "app/services/evidence_new.py",
                "follow_up_condition": "remove after the facade split lands",
            }
        ],
    )
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            [
                "# hotspot-exception: HPG-TEST-1",
                "def _assemble_payload():",
                "    return {}",
            ],
        ),
        policy=policy,
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["summary"]["exception_count"] == 1
    assert report["findings"][0]["status"] == "allowed_exception"


def test_json_report_shape_and_cli_strict_exit(tmp_path: Path, capsys) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "schema_name": POLICY_SCHEMA_NAME,
                "schema_version": "1.0",
                "known_hotspots": {
                    "app/services/evidence.py": {
                        "target_role": "compatibility facade",
                        "preferred_owner_modules": ["app/services/evidence_new.py"],
                        "block_new": ["private_helper"],
                        "allow": ["import_forwarder", "deletion"],
                    }
                },
            },
            sort_keys=False,
        )
    )
    diff_path = tmp_path / "blocked.diff"
    diff_path.write_text(
        _diff_for(
            "app/services/evidence.py",
            ["def _assemble_payload():", "    return {}"],
        )
    )

    exit_code = run(
        [
            "--policy-path",
            str(policy_path),
            "--diff-file",
            str(diff_path),
            "--strict",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["schema_name"] == REPORT_SCHEMA_NAME
    assert payload["summary"]["blocked_count"] == 1
    assert payload["summary"]["added_line_count"] == 2
    assert payload["findings"][0]["policy_rule"] == "block_new.private_helper"


def test_git_diff_collectors_wire_base_and_staged(monkeypatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, *, cwd, capture_output, text):
        commands.append(command)
        assert cwd == tmp_path
        assert capture_output is True
        assert text is True
        return Completed()

    monkeypatch.setattr("app.hotspot_prevention_diff.subprocess.run", fake_run)

    collect_git_diff(project_root=tmp_path, base="HEAD~1")
    collect_git_numstat(project_root=tmp_path, staged=True)

    assert commands == [
        ["git", "diff", "--no-ext-diff", "--unified=3", "HEAD~1"],
        ["git", "diff", "--no-ext-diff", "--numstat", "--cached"],
    ]


def test_git_diff_collectors_reject_base_with_staged(tmp_path: Path) -> None:
    try:
        collect_git_diff(project_root=tmp_path, base="HEAD", staged=True)
    except ValueError as exc:
        assert "--base and --staged cannot be used together" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_pyproject_exposes_hotspot_prevention_entrypoint() -> None:
    scripts = tomllib.loads(Path("pyproject.toml").read_text())["project"]["scripts"]

    assert scripts["docling-system-hotspot-prevention-check"] == "app.hotspot_prevention:run"
