from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.hygiene_types import HygieneFinding
from app.services import improvement_case_intake as intake
from app.services.improvement_cases import (
    ImprovementCaseObservation,
    load_improvement_case_registry,
)


def _observation(
    source_type: str = "hygiene_finding",
    source_ref: str = "hygiene:test",
    workflow_version: str = "improvement_v1",
):
    return ImprovementCaseObservation(
        title="Observed failure",
        observed_failure="A failure was observed.",
        cause_class="missing_test",
        source_type=source_type,
        source_ref=source_ref,
        workflow_version=workflow_version,
    )


def _write_architecture_governance_report(
    path: Path,
    *,
    valid: bool = True,
    recording_required: bool = False,
    include_top_level_measurement_fields: bool = True,
    schema_name: str = "architecture_governance_report",
    violations: list[dict] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    measurement_summary = {
        "current_commit_sha": "current-sha",
        "latest_recorded_commit_sha": "old-sha" if recording_required else "current-sha",
        "recording_required": recording_required,
    }
    payload = {
        "schema_name": schema_name,
        "schema_version": "1.0",
        "valid": valid,
        "violation_count": len(violations or []),
        "inspection": {
            "violations": violations or [],
        },
        "measurement_summary": measurement_summary,
    }
    if include_top_level_measurement_fields:
        payload.update(measurement_summary)
    path.write_text(json.dumps(payload))


def _write_architecture_quality_report(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_name": "architecture_quality_report",
                "schema_version": "1.0",
                "improvement_case_candidates": [
                    {
                        "source_ref": "architecture-quality:hotspot:app/services/evidence.py",
                        "title": "Architecture hotspot: app/services/evidence.py",
                        "observed_failure": "Large, high-churn evidence surface.",
                        "cause_class": "unclear_ownership",
                        "artifact_target_path": "app/services/evidence.py",
                        "verification_command": (
                            "uv run docling-system-architecture-quality-report"
                        ),
                        "stop_condition": "Risk decreases.",
                    }
                ],
            }
        )
    )


def _write_agent_trace_review_report(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_name": "agent_trace_review_report",
                "schema_version": "1.0",
                "observations": [
                    {
                        "category": "failed_agent_tasks",
                        "title": "Failed agent task",
                        "observed_failure": "The task failed.",
                        "cause_class": "missing_context",
                        "source_type": "agent_task",
                        "source_ref": "agent_task:00000000-0000-0000-0000-000000000000",
                        "source_notes": "task_type=demo",
                    }
                ],
            }
        )
    )


def test_collect_import_observations_keeps_hygiene_source_out_of_db(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        intake,
        "collect_hygiene_import_observations",
        lambda *, limit, workflow_version, project_root=None: [
            _observation(workflow_version=workflow_version)
        ],
    )

    def fail_session_factory():
        raise AssertionError("hygiene import should not open a DB session")

    observations = intake.collect_improvement_case_import_observations(
        source="hygiene",
        limit=5,
        workflow_version="improvement_v2",
        session_factory=fail_session_factory,
    )

    assert observations[0].source_type == "hygiene_finding"
    assert observations[0].workflow_version == "improvement_v2"


def test_hygiene_import_observes_only_blocking_findings(monkeypatch) -> None:
    monkeypatch.setattr(intake, "collect_ruff_violation_counts", lambda root: {})
    monkeypatch.setattr(intake, "load_ruff_baseline", lambda project_root: {})
    monkeypatch.setattr(
        intake,
        "run_python_hygiene_checks",
        lambda root: [
            HygieneFinding(
                kind="file_budget_inherited",
                relative_path="app/inherited.py",
                message="10 lines exceeds target budget 5; ratchet ceiling 10",
                severity="inherited",
            ),
            HygieneFinding(
                kind="file_budget_regression",
                relative_path="app/regression.py",
                message="11 lines exceeds ratchet ceiling 10 and target budget 5",
            ),
        ],
    )
    monkeypatch.setattr(intake, "run_improvement_case_contract_checks", lambda root: [])

    observations = intake.collect_hygiene_import_observations()

    assert len(observations) == 1
    assert observations[0].title == "Hygiene finding: file_budget_regression"
    assert observations[0].source_notes == "app/regression.py"
    assert "app/inherited.py" not in observations[0].observed_failure


def test_collect_architecture_governance_report_observations_from_invalid_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(
        report_path,
        valid=False,
        violations=[
            {
                "rule_id": "api-route-capability-contracts",
                "contract": "api_route_capabilities",
                "field": "capability",
                "relative_path": "app/api/routers/documents.py",
                "lineno": 42,
                "severity": "error",
                "message": "Route is missing a capability dependency.",
            }
        ],
    )

    observations = intake.collect_improvement_case_import_observations(
        source="architecture-governance-report",
        source_path=report_path,
        limit=10,
    )

    assert len(observations) == 1
    assert observations[0].source_type == "architecture_governance"
    assert observations[0].source_ref == (
        "architecture-governance:api-route-capability-contracts:"
        "app/api/routers/documents.py:42"
    )
    assert observations[0].cause_class == "missing_constraint"
    assert "Route is missing a capability dependency" in observations[0].observed_failure


def test_collect_architecture_governance_report_observations_from_stale_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(
        report_path,
        recording_required=True,
        include_top_level_measurement_fields=False,
    )

    observations = intake.collect_improvement_case_import_observations(
        source="architecture-governance-report",
        source_path=report_path,
        limit=10,
    )

    assert len(observations) == 1
    assert observations[0].source_ref == "architecture-governance:measurement-freshness:current-sha"
    assert observations[0].cause_class == "missing_context"
    assert "old-sha" in observations[0].observed_failure
    assert "current_commit_sha=current-sha" in observations[0].source_notes


def test_collect_architecture_governance_report_observations_skips_clean_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(report_path)

    observations = intake.collect_improvement_case_import_observations(
        source="architecture-governance-report",
        source_path=report_path,
    )

    assert observations == []


def test_collect_architecture_governance_report_accepts_keyed_source_path(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(report_path)

    observations = intake.collect_improvement_case_import_observations(
        source="architecture-governance-report",
        source_paths={"architecture-governance-report": report_path},
    )

    assert observations == []


def test_collect_architecture_quality_report_observations_from_candidates(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_quality_report.json"
    _write_architecture_quality_report(report_path)

    observations = intake.collect_improvement_case_import_observations(
        source="architecture-quality-report",
        source_path=report_path,
    )

    assert len(observations) == 1
    assert observations[0].source_type == "architecture_governance"
    assert observations[0].source_ref == (
        "architecture-quality:hotspot:app/services/evidence.py"
    )
    assert observations[0].cause_class == "unclear_ownership"
    assert observations[0].artifact_type == "contract"
    assert observations[0].artifact_target_path == "app/services/evidence.py"
    assert observations[0].verification_commands == [
        "uv run docling-system-architecture-quality-report"
    ]
    assert observations[0].acceptance_conditions == ["Risk decreases."]


def test_collect_agent_trace_review_report_observations(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "agent_trace_review_report.json"
    _write_agent_trace_review_report(report_path)

    observations = intake.collect_improvement_case_import_observations(
        source="agent-trace-review-report",
        source_path=report_path,
    )

    assert len(observations) == 1
    assert observations[0].source_type == "agent_task"
    assert observations[0].source_ref == (
        "agent_task:00000000-0000-0000-0000-000000000000"
    )
    assert "category=failed_agent_tasks" in observations[0].source_notes


def test_collect_architecture_governance_report_requires_explicit_existing_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Architecture governance report not found"):
        intake.collect_improvement_case_import_observations(
            source="architecture-governance-report",
            source_path=tmp_path / "missing.json",
        )


def test_collect_architecture_governance_report_rejects_wrong_schema(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "not_architecture_governance_report.json"
    _write_architecture_governance_report(report_path, schema_name="other_report")

    with pytest.raises(ValueError, match="unexpected schema_name"):
        intake.collect_improvement_case_import_observations(
            source="architecture-governance-report",
            source_path=report_path,
        )


def test_collect_import_observations_rejects_source_path_for_unsupported_source(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="source_path is not supported"):
        intake.collect_improvement_case_import_observations(
            source="hygiene",
            source_path=tmp_path / "architecture_governance_report.json",
        )


def test_collect_import_observations_rejects_unknown_source_path_key(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="unknown import source"):
        intake.collect_improvement_case_import_observations(
            source="all",
            source_paths={"unknown-source": tmp_path / "report.json"},
        )


def test_collect_import_observations_rejects_aggregate_source_path_key(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="cannot target aggregate import source"):
        intake.collect_improvement_case_import_observations(
            source="all",
            source_paths={"all": tmp_path / "report.json"},
        )


def test_collect_import_observations_rejects_unselected_source_path_key(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="unselected import source"):
        intake.collect_improvement_case_import_observations(
            source="hygiene",
            source_paths={
                "architecture-governance-report": tmp_path / "architecture_report.json"
            },
        )


def test_collect_import_observations_rejects_unsupported_source_path_key(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="source_paths is not supported"):
        intake.collect_improvement_case_import_observations(
            source="all",
            source_paths={"hygiene": tmp_path / "hygiene.json"},
        )


def test_collect_import_observations_rejects_legacy_and_keyed_paths(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Use source_path or source_paths"):
        intake.collect_improvement_case_import_observations(
            source="architecture-governance-report",
            source_path=tmp_path / "legacy.json",
            source_paths={"architecture-governance-report": tmp_path / "keyed.json"},
        )


def test_collect_import_observations_routes_db_sources_through_one_session(
    monkeypatch,
) -> None:
    opened = []

    class FakeSession:
        def __enter__(self):
            opened.append("open")
            return self

        def __exit__(self, exc_type, exc, tb):
            opened.append("close")
            return False

    monkeypatch.setattr(
        intake,
        "collect_eval_failure_case_observations",
        lambda session, *, limit, workflow_version: [
            _observation("eval_failure", "eval_failure_case:1")
        ],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_task_observations",
        lambda session, *, limit, workflow_version: [_observation("agent_task", "agent_task:1")],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_verification_observations",
        lambda session, *, limit, workflow_version: [
            _observation("agent_verification", "agent_verification:1")
        ],
    )
    monkeypatch.setattr(
        intake,
        "collect_hygiene_import_observations",
        lambda *, limit, workflow_version, project_root=None: [],
    )

    observations = intake.collect_improvement_case_import_observations(
        source="all",
        limit=3,
        session_factory=lambda: FakeSession(),
    )

    assert opened == ["open", "close"]
    assert [observation.source_type for observation in observations] == [
        "eval_failure",
        "agent_task",
        "agent_verification",
    ]


def test_collect_import_observations_all_rejects_ambiguous_source_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(report_path)
    monkeypatch.setattr(
        intake,
        "collect_hygiene_import_observations",
        lambda *, limit, workflow_version, project_root=None: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_eval_failure_case_observations",
        lambda session, *, limit, workflow_version: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_task_observations",
        lambda session, *, limit, workflow_version: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_verification_observations",
        lambda session, *, limit, workflow_version: [],
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    with pytest.raises(ValueError, match="source_path is ambiguous"):
        intake.collect_improvement_case_import_observations(
            source="all",
            source_path=report_path,
            session_factory=lambda: FakeSession(),
        )


def test_collect_import_observations_routes_keyed_source_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(report_path)
    monkeypatch.setattr(
        intake,
        "collect_hygiene_import_observations",
        lambda *, limit, workflow_version, project_root=None: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_eval_failure_case_observations",
        lambda session, *, limit, workflow_version: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_task_observations",
        lambda session, *, limit, workflow_version: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_verification_observations",
        lambda session, *, limit, workflow_version: [],
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    observations = intake.collect_improvement_case_import_observations(
        source="all",
        source_paths={"architecture-governance-report": report_path},
        session_factory=lambda: FakeSession(),
    )

    assert observations == []


def test_collect_import_observations_all_accepts_explicit_file_sources(
    monkeypatch,
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_quality_report.json"
    _write_architecture_quality_report(report_path)
    monkeypatch.setattr(
        intake,
        "collect_hygiene_import_observations",
        lambda *, limit, workflow_version, project_root=None: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_eval_failure_case_observations",
        lambda session, *, limit, workflow_version: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_task_observations",
        lambda session, *, limit, workflow_version: [],
    )
    monkeypatch.setattr(
        intake,
        "collect_failed_agent_verification_observations",
        lambda session, *, limit, workflow_version: [],
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    observations = intake.collect_improvement_case_import_observations(
        source="all",
        source_paths={"architecture-quality-report": report_path},
        session_factory=lambda: FakeSession(),
    )

    assert [observation.source_ref for observation in observations] == [
        "architecture-quality:hotspot:app/services/evidence.py"
    ]


def test_run_import_facade_writes_and_dedupes_cases(monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    monkeypatch.setattr(
        intake,
        "collect_improvement_case_import_observations",
        lambda **kwargs: [_observation()],
    )

    first = intake.run_improvement_case_import(path=registry_path)
    second = intake.run_improvement_case_import(path=registry_path)
    registry = load_improvement_case_registry(registry_path)

    assert isinstance(first, intake.ImprovementCaseImportResult)
    assert first.schema_name == "improvement_case_import"
    assert first.imported_count == 1
    assert second.imported_count == 0
    assert second.skipped[0].reason == "already_imported"
    assert registry.cases[0].source.source_ref == "hygiene:test"


def test_run_import_facade_writes_architecture_governance_cases(tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(
        report_path,
        valid=False,
        violations=[
            {
                "rule_id": "architecture-contract-map-drift",
                "contract": "architecture_contract_map",
                "field": "persisted_map",
                "relative_path": "docs/architecture_contract_map.json",
                "message": "Committed architecture contract map is stale.",
            }
        ],
    )

    first = intake.run_improvement_case_import(
        source="architecture-governance-report",
        source_path=report_path,
        path=registry_path,
    )
    second = intake.run_improvement_case_import(
        source="architecture-governance-report",
        source_path=report_path,
        path=registry_path,
    )
    registry = load_improvement_case_registry(registry_path)

    assert first.imported_count == 1
    assert second.imported_count == 0
    assert second.skipped[0].reason == "already_imported"
    assert registry.cases[0].source.source_type == "architecture_governance"
    assert registry.cases[0].source.source_ref == (
        "architecture-governance:architecture-contract-map-drift:"
        "docs/architecture_contract_map.json"
    )


def test_run_import_facade_writes_architecture_quality_case_metadata(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    report_path = tmp_path / "architecture_quality_report.json"
    _write_architecture_quality_report(report_path)

    result = intake.run_improvement_case_import(
        source="architecture-quality-report",
        source_path=report_path,
        path=registry_path,
    )
    registry = load_improvement_case_registry(registry_path)

    assert result.imported_count == 1
    assert result.imported[0].artifact_target_path == "app/services/evidence.py"
    assert result.imported[0].verification_commands == [
        "uv run docling-system-architecture-quality-report"
    ]
    assert registry.cases[0].artifact.target_path == "app/services/evidence.py"
    assert registry.cases[0].verification.acceptance_conditions == ["Risk decreases."]


def test_run_import_facade_accepts_keyed_source_paths(tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    report_path = tmp_path / "architecture_governance_report.json"
    _write_architecture_governance_report(
        report_path,
        valid=False,
        violations=[
            {
                "rule_id": "source-path-contract",
                "contract": "improvement_case_intake",
                "field": "source_paths",
                "relative_path": "app/services/improvement_case_intake.py",
                "message": "File-backed import source lost its keyed source path.",
            }
        ],
    )

    result = intake.run_improvement_case_import(
        source="architecture-governance-report",
        source_paths={"architecture-governance-report": report_path},
        path=registry_path,
    )
    registry = load_improvement_case_registry(registry_path)

    assert result.imported_count == 1
    assert registry.cases[0].source.source_ref == (
        "architecture-governance:source-path-contract:"
        "app/services/improvement_case_intake.py"
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
