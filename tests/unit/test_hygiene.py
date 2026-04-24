from __future__ import annotations

from pathlib import Path

from app.hygiene import (
    find_ruff_regression_findings,
    run_architecture_contract_checks,
    run_improvement_case_contract_checks,
    run_python_hygiene_checks,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_hygiene_allows_only_explicit_duplicate_helper_names(tmp_path: Path) -> None:
    _write(
        tmp_path / "app" / "alpha.py",
        "def _shared():\n    return 'alpha'\n",
    )
    _write(
        tmp_path / "app" / "beta.py",
        "def _shared():\n    return 'beta'\n",
    )
    _write(
        tmp_path / "config" / "policy.yaml",
        "\n".join(
            [
                "duplicate_helper_names:",
                "  - name: _shared",
                "    modules:",
                "      - app/alpha.py",
                "      - app/beta.py",
                "file_budgets:",
                "  defaults:",
                "    max_lines: 50",
                "    max_private_helpers: 5",
            ]
        )
        + "\n",
    )

    findings = run_python_hygiene_checks(
        tmp_path,
        policy_path=Path("config/policy.yaml"),
    )

    assert findings == []


def test_hygiene_flags_duplicate_bodies_and_budget_growth(tmp_path: Path) -> None:
    _write(
        tmp_path / "app" / "alpha.py",
        "\n".join(
            [
                "def _one():",
                "    return 1",
                "",
                "def _two():",
                "    return 1",
            ]
        )
        + "\n",
    )
    _write(
        tmp_path / "config" / "policy.yaml",
        "\n".join(
            [
                "duplicate_helper_names: []",
                "file_budgets:",
                "  defaults:",
                "    max_lines: 4",
                "    max_private_helpers: 1",
            ]
        )
        + "\n",
    )

    findings = run_python_hygiene_checks(
        tmp_path,
        policy_path=Path("config/policy.yaml"),
    )

    kinds = {finding.kind for finding in findings}
    assert "duplicate_helper_body" in kinds
    assert "duplicate_helper_name" not in kinds
    assert "file_budget" in kinds
    assert "helper_budget" in kinds


def test_hygiene_allows_explicit_duplicate_helper_bodies(tmp_path: Path) -> None:
    _write(
        tmp_path / "app" / "alpha.py",
        "\n".join(
            [
                "def _one():",
                "    return 1",
                "",
                "def _two():",
                "    return 1",
            ]
        )
        + "\n",
    )
    _write(
        tmp_path / "config" / "policy.yaml",
        "\n".join(
            [
                "duplicate_helper_names: []",
                "duplicate_helper_bodies:",
                "  - helpers:",
                "      - app/alpha.py:_one",
                "      - app/alpha.py:_two",
                "file_budgets:",
                "  defaults:",
                "    max_lines: 50",
                "    max_private_helpers: 5",
            ]
        )
        + "\n",
    )

    findings = run_python_hygiene_checks(
        tmp_path,
        policy_path=Path("config/policy.yaml"),
    )

    assert findings == []


def test_hygiene_flags_only_new_ruff_debt() -> None:
    findings = find_ruff_regression_findings(
        current_counts={
            "app/alpha.py": {"I001": 1, "F401": 1},
            "app/beta.py": {"E501": 1},
            "app/gamma.py": {"UP035": 1},
        },
        baseline_counts={
            "app/alpha.py": {"I001": 1},
            "app/beta.py": {"E501": 2},
        },
    )

    rendered = {(finding.relative_path, finding.message) for finding in findings}
    assert rendered == {
        ("app/alpha.py", "F401 count 1 exceeds baseline 0"),
        ("app/gamma.py", "UP035 count 1 exceeds baseline 0"),
    }


def test_hygiene_validates_improvement_case_registry(tmp_path: Path) -> None:
    _write(
        tmp_path / "config" / "improvement_cases.yaml",
        "\n".join(
            [
                "schema_name: improvement_cases",
                "schema_version: '1.0'",
                "cases:",
                "  - case_id: IC-20260424-gap",
                "    title: Missing validation",
                "    status: converted",
                "    cause_class: missing_constraint",
                "    observed_failure: Registry artifacts were not enforced.",
                "    source:",
                "      source_type: review_comment",
                "    artifact:",
                "      artifact_type: contract",
                "      target_path: tests/unit/test_missing.py",
                "      description: Missing artifact.",
                "    verification:",
                "      commands:",
                "        - uv run pytest tests/unit/test_missing.py -q",
            ]
        )
        + "\n",
    )

    findings = run_improvement_case_contract_checks(tmp_path)

    assert findings
    assert findings[0].kind == "improvement_case_contract"
    assert findings[0].relative_path == "config/improvement_cases.yaml"


def test_hygiene_adapts_architecture_contract_violations(monkeypatch) -> None:
    class Violation:
        contract = "test_contract"
        field = "test_field"
        message = "Boundary drifted."
        relative_path = "app/example.py"
        lineno = 12

    monkeypatch.setattr(
        "app.architecture_inspection.inspect_architecture_contracts",
        lambda project_root: [Violation()],
    )

    findings = run_architecture_contract_checks()

    assert findings[0].kind == "architecture_contract"
    assert findings[0].relative_path == "app/example.py"
    assert findings[0].lineno == 12
    assert findings[0].message == "test_contract.test_field: Boundary drifted."
