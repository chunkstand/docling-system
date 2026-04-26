from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from typing import Any

ARCHITECTURE_SEVERITIES = frozenset({"error", "warning", "info", "ignore"})


@dataclass(frozen=True, slots=True)
class ArchitectureViolation:
    contract: str
    field: str
    message: str
    rule_id: str | None = None
    relative_path: str | None = None
    lineno: int | None = None
    symbol: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ArchitectureRule:
    rule_id: str
    contract: str
    description: str
    source_path: str
    checker: Callable[[Any], list[ArchitectureViolation]]
    default_severity: str = "error"

    def __post_init__(self) -> None:
        if self.default_severity not in ARCHITECTURE_SEVERITIES:
            raise ValueError(f"Unknown architecture severity '{self.default_severity}'.")

    def check(self, context: Any) -> list[ArchitectureViolation]:
        violations: list[ArchitectureViolation] = []
        for violation in self.checker(context):
            if violation.contract != self.contract:
                raise ValueError(
                    f"Rule '{self.rule_id}' emitted violation for contract "
                    f"'{violation.contract}', expected '{self.contract}'."
                )
            if violation.rule_id is not None and violation.rule_id != self.rule_id:
                raise ValueError(
                    f"Rule '{self.rule_id}' emitted violation for rule "
                    f"'{violation.rule_id}'."
                )
            violations.append(
                replace(
                    violation,
                    rule_id=self.rule_id,
                    severity=(
                        self.default_severity
                        if violation.severity == "error"
                        else violation.severity
                    ),
                )
            )
        return violations

    def to_manifest(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "contract": self.contract,
            "description": self.description,
            "source_path": self.source_path,
            "default_severity": self.default_severity,
        }
