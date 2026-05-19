from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import improvement_case_intake as intake
from app.services.improvement_cases import (
    ImprovementCaseObservation,
    import_improvement_case_observations,
    load_improvement_case_registry,
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
                        "routing_status": "active_owner",
                        "route_reason": "Raw hotspot remains the honest next owner surface.",
                        "route_to_case_ids": [],
                        "route_to_paths": [],
                        "route_to_plan_paths": [],
                        "selected_for_routed_queue": True,
                        "verification_command": (
                            "uv run docling-system-architecture-quality-report"
                        ),
                        "stop_condition": "Risk decreases.",
                    }
                ],
                "raw_improvement_case_candidates": [
                    {
                        "source_ref": "architecture-quality:hotspot:app/db/models.py",
                        "title": "Architecture hotspot: app/db/models.py",
                        "observed_failure": "Compatibility facade still has high fan-in.",
                        "cause_class": "unclear_ownership",
                        "artifact_target_path": "app/db/models.py",
                        "routing_status": "compatibility_facade_trap",
                        "route_reason": "Compatibility facade is already reduced.",
                        "route_to_case_ids": ["IC-ROUTE-DB"],
                        "route_to_paths": ["app/db/model_domains/audit_and_evidence.py"],
                        "route_to_plan_paths": [
                            "docs/db_models_residual_owner_family_milestone_plan.md"
                        ],
                        "selected_for_routed_queue": False,
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
    assert "routing_status=active_owner" in observations[0].source_notes
    assert "route_to_paths=none" in observations[0].source_notes


def test_collect_architecture_quality_report_observations_ignore_raw_candidates(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "architecture_quality_report.json"
    _write_architecture_quality_report(report_path)

    observations = intake.collect_improvement_case_import_observations(
        source="architecture-quality-report",
        source_path=report_path,
    )

    assert len(observations) == 1
    assert {observation.source_ref for observation in observations} == {
        "architecture-quality:hotspot:app/services/evidence.py"
    }


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


def test_run_import_facade_skips_existing_architecture_governance_artifact(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    report_path = tmp_path / "architecture_quality_report.json"
    _write_architecture_quality_report(report_path)
    import_improvement_case_observations(
        [
            ImprovementCaseObservation(
                title="Architecture hotspot: app/services/evidence.py",
                observed_failure="Large, high-churn evidence surface.",
                cause_class="unclear_ownership",
                source_type="architecture_governance",
                source_ref="architecture-probe:largest-file:app/services/evidence.py",
                artifact_type="contract",
                artifact_target_path="app/services/evidence.py",
                artifact_description="Existing evidence owner-governance surface.",
            )
        ],
        path=registry_path,
    )

    result = intake.run_improvement_case_import(
        source="architecture-quality-report",
        source_path=report_path,
        path=registry_path,
    )
    registry = load_improvement_case_registry(registry_path)

    assert result.imported_count == 0
    assert result.skipped[0].reason == "artifact_already_governed"
    assert len(registry.cases) == 1
    assert registry.cases[0].source.source_ref == (
        "architecture-probe:largest-file:app/services/evidence.py"
    )


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
