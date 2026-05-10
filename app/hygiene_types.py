from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrivateHelper:
    name: str
    relative_path: str
    lineno: int
    body_fingerprint: str


@dataclass(frozen=True)
class FileBudget:
    max_lines: int | None = None
    max_private_helpers: int | None = None
    ratchet_max_lines: int | None = None
    ratchet_max_private_helpers: int | None = None
    owner_case_id: str | None = None
    owner_milestone: str | None = None

    @property
    def owner_reference(self) -> str | None:
        return self.owner_case_id or self.owner_milestone


@dataclass(frozen=True)
class HygienePolicy:
    duplicate_helper_name_allowances: dict[str, frozenset[str]]
    duplicate_helper_body_allowances: frozenset[frozenset[str]]
    default_file_budget: FileBudget
    file_budgets: dict[str, FileBudget]


@dataclass(frozen=True)
class HygieneFinding:
    kind: str
    message: str
    relative_path: str | None = None
    lineno: int | None = None
    severity: str = "error"

    @property
    def blocking(self) -> bool:
        return self.severity == "error"

    def render(self) -> str:
        location = ""
        if self.relative_path is not None:
            location = self.relative_path
            if self.lineno is not None:
                location = f"{location}:{self.lineno}"
            location = f"{location}: "
        return f"{location}{self.kind}: {self.message}"
