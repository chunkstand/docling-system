from __future__ import annotations

from pathlib import Path

import pytest

from app.services import improvement_case_intake as intake
from app.services.improvement_cases import ImprovementCaseObservation


def _observation(
    *,
    source_type: str = "hygiene_finding",
    source_ref: str = "hygiene:test",
    workflow_version: str = "improvement_v1",
) -> ImprovementCaseObservation:
    return ImprovementCaseObservation(
        title="Observed failure",
        observed_failure="A failure was observed.",
        cause_class="missing_test",
        source_type=source_type,
        source_ref=source_ref,
        workflow_version=workflow_version,
    )


def test_run_import_facade_accepts_typed_request(monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    monkeypatch.setattr(
        intake,
        "collect_improvement_case_import_observations",
        lambda **kwargs: [_observation(workflow_version=kwargs["workflow_version"])],
    )

    result = intake.run_improvement_case_import(
        request=intake.ImprovementCaseImportRequest(
            source="hygiene",
            limit=1,
            workflow_version="improvement_v2",
            path=registry_path,
            dry_run=True,
        )
    )

    assert result.dry_run is True
    assert result.imported_count == 1
    assert result.imported[0].workflow_version == "improvement_v2"
    assert not registry_path.exists()


def test_collect_import_observations_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unknown improvement case import source"):
        intake.collect_improvement_case_import_observations(source="mystery")


def test_import_request_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unknown improvement case import source"):
        intake.ImprovementCaseImportRequest(source="mystery")


def test_import_request_rejects_invalid_source_path_contract(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_path is not supported"):
        intake.ImprovementCaseImportRequest(
            source="hygiene",
            source_path=tmp_path / "report.json",
        )


def test_import_sources_include_architecture_governance_report() -> None:
    assert "architecture-governance-report" in intake.list_improvement_case_import_sources()
    assert "architecture-quality-report" in intake.list_improvement_case_import_sources()
    assert "agent-trace-review-report" in intake.list_improvement_case_import_sources()


def test_import_source_specs_expose_source_behavior() -> None:
    specs = {
        row["source"]: row
        for row in intake.list_improvement_case_import_source_specs()
    }

    assert set(intake.list_improvement_case_import_sources()) == {
        "all",
        *specs,
    }
    assert specs["hygiene"]["source_kind"] == "workspace"
    assert specs["hygiene"]["requires_db_session"] is False
    assert specs["hygiene"]["accepts_source_path"] is False
    assert specs["architecture-governance-report"]["source_kind"] == "file"
    assert specs["architecture-governance-report"]["accepts_source_path"] is True
    assert specs["architecture-quality-report"]["source_kind"] == "file"
    assert specs["architecture-quality-report"]["accepts_source_path"] is True
    assert specs["agent-trace-review-report"]["source_kind"] == "file"
    assert specs["agent-trace-review-report"]["accepts_source_path"] is True
    assert {
        source
        for source, row in specs.items()
        if row["requires_db_session"] is True
    } == {
        "eval-failure-cases",
        "failed-agent-tasks",
        "failed-agent-verifications",
    }


def test_cli_import_boundary_does_not_call_low_level_collectors() -> None:
    cli_source = (Path(__file__).parents[2] / "app" / "cli.py").read_text()
    intake_source = (
        Path(__file__).parents[2] / "app" / "services" / "improvement_case_intake.py"
    ).read_text()

    for forbidden in (
        "collect_architecture_governance_report_observations",
        "collect_eval_failure_case_observations",
        "collect_failed_agent_task_observations",
        "collect_failed_agent_verification_observations",
        "collect_hygiene_import_observations",
        "collect_hygiene_finding_observations",
        "collect_improvement_case_import_observations",
        "import_improvement_case_observations",
    ):
        assert forbidden not in cli_source
    assert "--source-path-for" not in intake_source
