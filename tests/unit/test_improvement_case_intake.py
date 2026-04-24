from __future__ import annotations

import pytest

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

    assert first["imported_count"] == 1
    assert second["imported_count"] == 0
    assert second["skipped"][0]["reason"] == "already_imported"
    assert registry.cases[0].source.source_ref == "hygiene:test"


def test_collect_import_observations_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unknown improvement case import source"):
        intake.collect_improvement_case_import_observations(source="mystery")
