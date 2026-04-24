from __future__ import annotations

from app.services.improvement_cases import (
    ImprovementCase,
    ImprovementCaseArtifact,
    ImprovementCaseRegistry,
    ImprovementCaseSource,
    ImprovementCaseVerification,
    build_improvement_case_manifest,
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
        ]
    )
    registry.cases[1].cause_class = "missing_context"
    registry.cases[1].artifact.artifact_type = "generated_map"
    registry.cases[1].workflow_version = "improvement_v2"

    summary = summarize_improvement_cases(registry)

    assert summary["case_count"] == 2
    assert summary["cause_class_counts"] == {"missing_constraint": 1, "missing_context": 1}
    assert summary["artifact_type_counts"] == {"contract": 1, "generated_map": 1}
    assert summary["workflow_version_counts"] == {"improvement_v1": 1, "improvement_v2": 1}


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
