from __future__ import annotations

from pathlib import Path

from app.hygiene import find_ruff_regression_findings, run_python_hygiene_checks


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
