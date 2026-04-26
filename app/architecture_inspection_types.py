from __future__ import annotations

from dataclasses import asdict, dataclass

ARCHITECTURE_SEVERITIES = frozenset({"error", "warning", "info", "ignore"})


@dataclass(frozen=True, slots=True)
class ArchitectureViolation:
    contract: str
    field: str
    message: str
    relative_path: str | None = None
    lineno: int | None = None
    symbol: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
