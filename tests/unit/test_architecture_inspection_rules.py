from __future__ import annotations

from pathlib import Path

import pytest

from app.architecture_inspection_types import (
    ArchitectureRule,
    ArchitectureViolation,
)
from tests.unit.architecture_inspection_test_support import (
    inspection_context,
    rule,
    write_python,
)


def test_architecture_rule_rejects_mismatched_violation_contract() -> None:
    inspection_rule = ArchitectureRule(
        rule_id="test-rule",
        contract="expected_contract",
        description="Test rule.",
        source_path="tests/unit/test_architecture_inspection_rules.py",
        checker=lambda _context: [
            ArchitectureViolation(
                contract="other_contract",
                field="field",
                message="wrong contract",
            )
        ],
    )

    with pytest.raises(ValueError, match="expected_contract"):
        inspection_rule.check(None)


def test_architecture_rule_rejects_mismatched_nested_rule_id() -> None:
    inspection_rule = ArchitectureRule(
        rule_id="test-rule",
        contract="expected_contract",
        description="Test rule.",
        source_path="tests/unit/test_architecture_inspection_rules.py",
        checker=lambda _context: [
            ArchitectureViolation(
                contract="expected_contract",
                field="field",
                message="wrong rule",
                rule_id="other-rule",
            )
        ],
    )

    with pytest.raises(ValueError, match="other-rule"):
        inspection_rule.check(None)


def test_architecture_rules_match_module_boundaries_not_name_prefixes(
    tmp_path: Path,
) -> None:
    context = inspection_context(tmp_path)
    write_python(
        tmp_path / "app/api/main.py",
        "import app.services_extra\n",
    )
    write_python(
        tmp_path / "app/services/safe.py",
        "\n".join(
            [
                "import app.api.mainframe",
                "from app.api.routers_extra import helper",
                "from app.services_extra.helpers import _private_helper",
            ]
        )
        + "\n",
    )

    assert rule("api-bootstrap-no-feature-service-imports").check(context) == []
    assert rule("service-layer-no-api-imports").check(context) == []
    assert rule("service-layer-no-private-service-imports").check(context) == []

    write_python(
        tmp_path / "app/api/main.py",
        "from app.services.documents import list_documents\n",
    )
    write_python(
        tmp_path / "app/services/unsafe.py",
        "\n".join(
            [
                "import app.api.main",
                "from app.api.routers.documents import router",
                "from app.services.documents import _private_helper",
            ]
        )
        + "\n",
    )

    assert {
        violation.symbol
        for violation in rule("api-bootstrap-no-feature-service-imports").check(context)
    } == {"app.services.documents"}
    assert {
        violation.symbol
        for violation in rule("service-layer-no-api-imports").check(context)
    } == {"app.api.main", "app.api.routers.documents"}
    private_import_violations = rule("service-layer-no-private-service-imports").check(context)
    assert {violation.symbol for violation in private_import_violations} == {
        "app.services.documents._private_helper"
    }
    assert {violation.rule_id for violation in private_import_violations} == {
        "service-layer-no-private-service-imports"
    }


def test_cli_improvement_intake_rule_uses_ast_not_substring_scan(
    tmp_path: Path,
) -> None:
    inspection_rule = rule("cli-delegates-improvement-intake")
    context = inspection_context(tmp_path)
    write_python(
        tmp_path / "app/cli.py",
        "\n".join(
            [
                "# collect_hygiene_finding_observations is only prose here.",
                'HELP = "import_improvement_case_observations"',
                'safe = _lazy_service_attr("app.services.improvement_cases", "load_registry")',
                "from app.services.other import collect_hygiene_finding_observations",
                (
                    'also_safe = _lazy_service_attr("app.services.other", '
                    '"import_improvement_case_observations")'
                ),
            ]
        )
        + "\n",
    )

    assert inspection_rule.check(context) == []

    write_python(
        tmp_path / "app/cli.py",
        "\n".join(
            [
                "from app.services.improvement_cases import (",
                "    collect_hygiene_finding_observations,",
                ")",
                "from app.services.improvement_case_intake import (",
                "    collect_architecture_governance_report_observations,",
                ")",
                "bad = _lazy_service_attr(",
                '    "app.services.improvement_cases",',
                '    "import_improvement_case_observations",',
                ")",
                "also_bad = _lazy_service_attr(",
                '    "app.services.improvement_case_intake",',
                '    "collect_improvement_case_import_observations",',
                ")",
            ]
        )
        + "\n",
    )

    assert {
        violation.symbol
        for violation in inspection_rule.check(context)
    } == {
        (
            "app.services.improvement_case_intake."
            "collect_architecture_governance_report_observations"
        ),
        (
            "app.services.improvement_case_intake."
            "collect_improvement_case_import_observations"
        ),
        "app.services.improvement_cases.collect_hygiene_finding_observations",
        "app.services.improvement_cases.import_improvement_case_observations",
    }
    assert {violation.rule_id for violation in inspection_rule.check(context)} == {
        "cli-delegates-improvement-intake"
    }
