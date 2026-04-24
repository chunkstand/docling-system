from __future__ import annotations

from app.services.improvement_cases import (
    ImprovementCase,
    ImprovementCaseArtifact,
    ImprovementCaseObservation,
    ImprovementCaseRegistry,
    ImprovementCaseSource,
    ImprovementCaseVerification,
    build_improvement_case_manifest,
    collect_eval_failure_case_observations,
    collect_failed_agent_task_observations,
    collect_hygiene_finding_observations,
    import_improvement_case_observations,
    load_improvement_case_registry,
    record_improvement_case,
    summarize_improvement_cases,
    validate_improvement_case_registry,
)


def _valid_case(case_id: str = "IC-20260424-route-contract") -> ImprovementCase:
    return ImprovementCase(
        case_id=case_id,
        title="Route capability strings were free-form",
        status="verified",
        cause_class="missing_constraint",
        observed_failure="Routers accepted typo-prone capability literals.",
        source=ImprovementCaseSource(
            source_type="review_comment",
            source_ref="architecture-pass-2026-04-24",
        ),
        artifact=ImprovementCaseArtifact(
            artifact_type="contract",
            target_path="tests/unit/test_api_route_contracts.py",
            description="FastAPI route capability manifest contract tests.",
        ),
        verification=ImprovementCaseVerification(
            commands=["uv run pytest tests/unit/test_api_route_contracts.py -q"],
            catches_old_failure=True,
            allows_good_changes=True,
        ),
        workflow_version="improvement_v1",
    )


def test_improvement_case_registry_accepts_valid_cases() -> None:
    registry = ImprovementCaseRegistry(cases=[_valid_case()])

    issues = validate_improvement_case_registry(registry)
    manifest = build_improvement_case_manifest(registry)

    assert issues == []
    assert manifest[0]["cause_class"] == "missing_constraint"
    assert manifest[0]["artifact_type"] == "contract"


def test_improvement_case_registry_accepts_open_cases_without_artifacts() -> None:
    registry = ImprovementCaseRegistry(
        cases=[
            ImprovementCase(
                case_id="IC-20260424-open",
                title="A failure has been observed but not converted yet",
                status="open",
                cause_class="missing_test",
                observed_failure="A regression escaped without a durable test.",
                source=ImprovementCaseSource(source_type="incident"),
            )
        ]
    )

    issues = validate_improvement_case_registry(registry)

    assert issues == []


def test_improvement_case_registry_rejects_unknown_vocabularies() -> None:
    case = _valid_case()
    case.status = "mystery"
    case.cause_class = "unknown_cause"
    case.source.source_type = "unknown_source"
    case.artifact.artifact_type = "unknown_artifact"

    issues = validate_improvement_case_registry(ImprovementCaseRegistry(cases=[case]))
    fields = {issue.field for issue in issues}

    assert {"status", "cause_class", "source.source_type", "artifact.artifact_type"} <= fields


def test_improvement_case_registry_requires_executable_verification() -> None:
    case = _valid_case()
    case.verification.commands = []
    case.verification.acceptance_conditions = []
    case.verification.catches_old_failure = False
    case.verification.allows_good_changes = False

    issues = validate_improvement_case_registry(ImprovementCaseRegistry(cases=[case]))
    fields = {issue.field for issue in issues}

    assert {
        "verification",
        "verification.catches_old_failure",
        "verification.allows_good_changes",
    } <= fields


def test_improvement_case_registry_requires_real_artifact_after_conversion() -> None:
    case = _valid_case()
    case.status = "converted"
    case.artifact.target_path = "tests/unit/test_missing_contract.py"

    issues = validate_improvement_case_registry(ImprovementCaseRegistry(cases=[case]))

    assert any(issue.field == "artifact.target_path" for issue in issues)


def test_improvement_case_registry_requires_deploy_and_measurement_for_late_statuses() -> None:
    case = _valid_case()
    case.status = "closed"

    issues = validate_improvement_case_registry(ImprovementCaseRegistry(cases=[case]))
    fields = {issue.field for issue in issues}

    assert {"deployment.deployed_ref", "measurement"} <= fields


def test_improvement_case_summary_counts_by_contract_dimensions() -> None:
    registry = ImprovementCaseRegistry(
        cases=[
            _valid_case("IC-20260424-route-contract"),
            _valid_case("IC-20260424-agent-actions"),
            ImprovementCase(
                case_id="IC-20260424-open",
                title="Observed failure",
                status="open",
                cause_class="missing_test",
                observed_failure="A failure is awaiting conversion.",
                source=ImprovementCaseSource(source_type="incident"),
            ),
        ]
    )
    registry.cases[1].cause_class = "missing_context"
    registry.cases[1].artifact.artifact_type = "generated_map"
    registry.cases[1].workflow_version = "improvement_v2"

    summary = summarize_improvement_cases(registry)

    assert summary["case_count"] == 3
    assert summary["cause_class_counts"] == {
        "missing_constraint": 1,
        "missing_context": 1,
        "missing_test": 1,
    }
    assert summary["artifact_type_counts"] == {"contract": 1, "generated_map": 1}
    assert summary["workflow_version_counts"] == {"improvement_v1": 2, "improvement_v2": 1}
    assert summary["actionable_buckets"]["open_unconverted_count"] == 1
    assert summary["actionable_buckets"]["converted_unverified_count"] == 0
    assert summary["actionable_buckets"]["verified_undeployed_count"] == 2


def test_record_improvement_case_writes_valid_registry(tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"

    case = record_improvement_case(
        path=registry_path,
        case_id="IC-20260424-test",
        title="A missing regression test let route drift through",
        observed_failure="Route capability checks were not machine-inspected.",
        cause_class="missing_test",
        artifact_type="test",
        artifact_target_path="tests/unit/test_api_route_contracts.py",
        artifact_description="Route manifest regression tests.",
        verification_commands=["uv run pytest tests/unit/test_api_route_contracts.py -q"],
        source_type="bad_diff",
        source_ref="local",
    )

    registry = load_improvement_case_registry(registry_path)

    assert case.case_id == "IC-20260424-test"
    assert validate_improvement_case_registry(registry) == []
    assert registry.cases[0].artifact.target_path == "tests/unit/test_api_route_contracts.py"


def test_import_improvement_case_observations_dedupes_by_source_ref(tmp_path) -> None:
    registry_path = tmp_path / "improvement_cases.yaml"
    observation = ImprovementCaseObservation(
        title="Failed agent task",
        observed_failure="The task failed because context was missing.",
        cause_class="missing_context",
        source_type="agent_task",
        source_ref="agent_task:123",
    )

    first = import_improvement_case_observations([observation], path=registry_path)
    second = import_improvement_case_observations([observation], path=registry_path)
    registry = load_improvement_case_registry(registry_path)

    assert first["imported_count"] == 1
    assert second["imported_count"] == 0
    assert second["skipped"][0]["reason"] == "already_imported"
    assert registry.cases[0].status == "open"
    assert registry.cases[0].source.source_ref == "agent_task:123"


def test_collect_hygiene_finding_observations_maps_findings_to_open_cases() -> None:
    class Finding:
        kind = "ruff_regression"
        relative_path = "app/example.py"
        lineno = None
        message = "E501 count 1 exceeds baseline 0"

        def render(self) -> str:
            return "app/example.py: ruff_regression: E501 count 1 exceeds baseline 0"

    observations = collect_hygiene_finding_observations([Finding()])

    assert observations[0].source_type == "hygiene_finding"
    assert observations[0].cause_class == "bad_pattern"
    assert observations[0].source_ref.startswith("hygiene:")


def test_collect_db_failure_observations_from_existing_surfaces() -> None:
    class Result:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class Session:
        def __init__(self, rows):
            self.rows = rows

        def execute(self, statement):
            return Result(self.rows)

    class EvalCase:
        id = "eval-1"
        problem_statement = "A retrieval eval failed."
        observed_behavior = "Wrong document ranked first."
        expected_behavior = "Expected document ranked first."
        failure_classification = "eval_coverage_gap"
        diagnosis = None
        surface = "document_evaluation"
        severity = "high"
        status = "open"

    class AgentTask:
        id = "task-1"
        task_type = "triage_replay_regression"
        status = "failed"
        error_message = "Missing context for replay evidence."
        workflow_version = "v1"

    eval_observations = collect_eval_failure_case_observations(Session([EvalCase()]))
    task_observations = collect_failed_agent_task_observations(Session([AgentTask()]))

    assert eval_observations[0].source_type == "eval_failure"
    assert eval_observations[0].source_ref == "eval_failure_case:eval-1"
    assert task_observations[0].source_type == "agent_task"
    assert task_observations[0].cause_class == "missing_context"
