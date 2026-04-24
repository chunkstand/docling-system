from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.improvement_case_lifecycle_cli import run_update
from app.services.improvement_case_lifecycle import (
    IMPROVEMENT_CASE_UPDATE_SCHEMA_NAME,
    update_improvement_case,
)
from app.services.improvement_cases import (
    ImprovementCase,
    ImprovementCaseArtifact,
    ImprovementCaseRegistry,
    ImprovementCaseSource,
    ImprovementCaseVerification,
    load_improvement_case_registry,
    summarize_improvement_cases,
    validate_improvement_case_registry,
    write_improvement_case_registry,
)


def _verified_case() -> ImprovementCase:
    return ImprovementCase(
        case_id="IC-20260424-hygiene-gate",
        title="Default hygiene gate drifted",
        status="verified",
        cause_class="missing_constraint",
        observed_failure="The default hygiene gate failed on the current repo state.",
        source=ImprovementCaseSource(source_type="hygiene_finding", source_ref="hygiene:test"),
        artifact=ImprovementCaseArtifact(
            artifact_type="lint",
            target_path="config/hygiene_policy.yaml",
            description="Incremental hygiene policy and baseline gate.",
        ),
        verification=ImprovementCaseVerification(
            commands=["uv run docling-system-hygiene-check"],
            catches_old_failure=True,
            allows_good_changes=True,
        ),
        workflow_version="improvement_v1",
        created_at="2026-04-24T00:00:00+00:00",
        updated_at="2026-04-24T00:00:00+00:00",
    )


def _write_registry(path: Path) -> None:
    write_improvement_case_registry(ImprovementCaseRegistry(cases=[_verified_case()]), path)


def test_update_improvement_case_promotes_verified_case_to_measured(tmp_path: Path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    _write_registry(registry_path)

    result = update_improvement_case(
        path=registry_path,
        case_id="IC-20260424-hygiene-gate",
        status="measured",
        deployed_ref="78ec3c8",
        deployment_notes="Merged into main.",
        metric_name="hygiene_architecture_findings",
        metric_value=0,
        measurement_window="2026-04-24 local verification",
        measurement_notes="Hygiene and architecture inspection reported no findings.",
    )
    registry = load_improvement_case_registry(registry_path)
    summary = summarize_improvement_cases(registry)

    assert result.schema_name == IMPROVEMENT_CASE_UPDATE_SCHEMA_NAME
    assert result.case.status == "measured"
    assert result.manifest[0]["deployed_ref"] == "78ec3c8"
    assert validate_improvement_case_registry(registry) == []
    assert summary["measured_case_count"] == 1
    assert summary["actionable_buckets"]["verified_undeployed_count"] == 0


def test_update_improvement_case_rejects_invalid_measured_transition(tmp_path: Path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    _write_registry(registry_path)

    with pytest.raises(ValueError, match="measurement"):
        update_improvement_case(
            path=registry_path,
            case_id="IC-20260424-hygiene-gate",
            status="measured",
            deployed_ref="78ec3c8",
        )

    registry = load_improvement_case_registry(registry_path)
    assert registry.cases[0].status == "verified"


def test_update_improvement_case_rejects_unknown_case(tmp_path: Path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    _write_registry(registry_path)

    with pytest.raises(ValueError, match="Unknown improvement case"):
        update_improvement_case(
            path=registry_path,
            case_id="IC-missing",
            status="deployed",
            deployed_ref="78ec3c8",
        )


def test_improvement_case_update_cli_prints_updated_payload(
    capsys,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    _write_registry(registry_path)

    exit_code = run_update(
        [
            "--path",
            str(registry_path),
            "--case-id",
            "IC-20260424-hygiene-gate",
            "--status",
            "measured",
            "--deployed-ref",
            "78ec3c8",
            "--metric-name",
            "hygiene_architecture_findings",
            "--metric-value",
            "0",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_name"] == IMPROVEMENT_CASE_UPDATE_SCHEMA_NAME
    assert payload["case"]["status"] == "measured"
