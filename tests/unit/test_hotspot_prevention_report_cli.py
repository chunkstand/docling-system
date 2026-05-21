from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.hotspot_prevention import (
    POLICY_SCHEMA_NAME,
    REPORT_SCHEMA_NAME,
    build_hotspot_prevention_report,
    load_hotspot_policy,
    parse_numstat,
    run,
)
from tests.unit.hotspot_prevention_test_support import _diff_for, _policy_for


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
