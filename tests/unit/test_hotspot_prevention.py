from __future__ import annotations

import json
import tomllib
from datetime import date
from pathlib import Path

import yaml

from app.hotspot_prevention import (
    POLICY_SCHEMA_NAME,
    REPORT_SCHEMA_NAME,
    build_hotspot_policy,
    build_hotspot_prevention_report,
    collect_git_diff,
    collect_git_numstat,
    load_hotspot_policy,
    parse_numstat,
    run,
    validate_policy_payload,
)


def _diff_for(path: str, added_lines: list[str], *, deleted_lines: list[str] | None = None) -> str:
    deleted = deleted_lines or []
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(len(deleted), 1)} +1,{max(len(added_lines), 1)} @@",
    ]
    lines.extend(f"-{line}" for line in deleted)
    lines.extend(f"+{line}" for line in added_lines)
    return "\n".join(lines) + "\n"


def _policy_for(path: str, *, exceptions: list[dict] | None = None):
    return build_hotspot_policy(
        {
            "schema_name": POLICY_SCHEMA_NAME,
            "schema_version": "1.0",
            "known_hotspots": {
                path: {
                    "target_role": "compatibility facade",
                    "preferred_owner_modules": ["app/owner/"],
                    "block_new": [
                        "orm_class",
                        "private_helper",
                        "command_implementation",
                        "executor_implementation",
                        "ranking_logic",
                        "broad_new_test_group",
                        "broad_helper",
                        "artifact_assembly",
                    ],
                    "allow": [
                        "import_forwarder",
                        "alias_forwarder",
                        "explicit_forwarding_function",
                        "parser_registration",
                        "compatibility_assertion",
                        "deletion",
                    ],
                    "exceptions": exceptions or [],
                }
            },
        }
    )


def test_current_hotspot_policy_loads_expected_surfaces() -> None:
    policy = load_hotspot_policy()

    assert sorted(policy.known_hotspots) == [
        "app/cli.py",
        "app/db/models.py",
        "app/services/agent_task_actions.py",
        "app/services/evidence.py",
        "app/services/search.py",
        "tests/unit/test_cli.py",
    ]
    for rule in policy.known_hotspots.values():
        assert rule.preferred_owner_modules
        assert rule.block_new


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


def test_analyzer_flags_obvious_implementation_growth_for_each_hotspot() -> None:
    cases = [
        ("app/db/models.py", ["class NewRuntimeRow(Base):", "    pass"], "orm_class"),
        (
            "app/services/evidence.py",
            ["def _assemble_payload():", "    return {}"],
            "private_helper",
        ),
        ("app/cli.py", ["def run_new_command():", "    print('x')"], "command_implementation"),
        (
            "app/services/agent_task_actions.py",
            ["def execute_new_action():", "    return None"],
            "executor_implementation",
        ),
        ("app/services/search.py", ["def _rank_new():", "    return 1"], "query_feature_helper"),
        (
            "tests/unit/test_cli.py",
            ["def test_new_command_group():", "    assert True"],
            "broad_new_test_group",
        ),
    ]
    for path, added_lines, category in cases:
        report = build_hotspot_prevention_report(
            _diff_for(path, added_lines),
            policy=load_hotspot_policy(),
            project_root=Path.cwd(),
        )

        assert report["summary"]["blocked_count"] == 1
        assert report["findings"][0]["relative_path"] == path
        assert report["findings"][0]["category"] == category
        assert report["findings"][0]["preferred_owner_modules"]


def test_analyzer_allows_import_forwarding_and_deletion_only_reductions() -> None:
    import_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            ["from app.services.evidence_new import build_new_payload"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    deletion_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            [],
            deleted_lines=["def _old_helper():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert import_report["summary"]["blocked_count"] == 0
    assert import_report["findings"][0]["category"] == "import_forwarder"
    assert deletion_report["summary"]["blocked_count"] == 0
    assert deletion_report["findings"][0]["category"] == "deletion"


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


def test_cli_forwarding_wrapper_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/cli.py",
            [
                "def run_new_command():",
                "    return run_new_command_impl()",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


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
