from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.core.files import repo_root

POLICY_SCHEMA_NAME = "hotspot_prevention_policy"
SCHEMA_VERSION = "1.0"
DEFAULT_POLICY_PATH = Path("config") / "hotspot_prevention.yaml"


@dataclass(frozen=True)
class PolicyIssue:
    field: str
    message: str


@dataclass(frozen=True)
class HotspotException:
    exception_id: str
    case_id: str | None
    milestone_id: str | None
    owner_module: str
    expires_on: date | None
    follow_up_condition: str | None
    match_tokens: tuple[str, ...]

    def matches(self, added_lines: tuple[str, ...]) -> bool:
        haystack = "\n".join(added_lines)
        return any(token and token in haystack for token in self.match_tokens)


@dataclass(frozen=True)
class HotspotRule:
    relative_path: str
    target_role: str
    preferred_owner_modules: tuple[str, ...]
    block_new: tuple[str, ...]
    allow: tuple[str, ...]
    exceptions: tuple[HotspotException, ...] = ()


@dataclass(frozen=True)
class HotspotPolicy:
    schema_name: str
    schema_version: str
    known_hotspots: dict[str, HotspotRule]


def string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def parse_policy_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def validate_policy_payload(
    payload: dict[str, Any],
    *,
    today: date | None = None,
) -> list[PolicyIssue]:
    issues: list[PolicyIssue] = []
    if payload.get("schema_name") != POLICY_SCHEMA_NAME:
        issues.append(PolicyIssue(field="schema_name", message=f"expected {POLICY_SCHEMA_NAME}"))
    if str(payload.get("schema_version") or "") != SCHEMA_VERSION:
        issues.append(PolicyIssue(field="schema_version", message=f"expected {SCHEMA_VERSION}"))
    known_hotspots = payload.get("known_hotspots")
    if not isinstance(known_hotspots, dict) or not known_hotspots:
        issues.append(PolicyIssue(field="known_hotspots", message="must be a non-empty map"))
        return issues

    current_day = today or date.today()
    for relative_path, raw_rule in sorted(known_hotspots.items()):
        field_prefix = f"known_hotspots.{relative_path}"
        if not isinstance(raw_rule, dict):
            issues.append(PolicyIssue(field=field_prefix, message="must be a map"))
            continue
        _validate_rule_shape(raw_rule, field_prefix, issues)
        _validate_rule_exceptions(raw_rule, field_prefix, current_day, issues)
    return issues


def _validate_rule_shape(
    raw_rule: dict[str, Any],
    field_prefix: str,
    issues: list[PolicyIssue],
) -> None:
    if not str(raw_rule.get("target_role") or "").strip():
        issues.append(PolicyIssue(field=f"{field_prefix}.target_role", message="is required"))
    if not string_list(raw_rule.get("preferred_owner_modules")):
        issues.append(
            PolicyIssue(
                field=f"{field_prefix}.preferred_owner_modules",
                message="must contain at least one owner module",
            )
        )
    if not string_list(raw_rule.get("block_new")):
        issues.append(
            PolicyIssue(
                field=f"{field_prefix}.block_new",
                message="must contain at least one blocked category",
            )
        )
    if not string_list(raw_rule.get("allow")):
        issues.append(
            PolicyIssue(
                field=f"{field_prefix}.allow",
                message="must contain at least one allowed category",
            )
        )


def _validate_rule_exceptions(
    raw_rule: dict[str, Any],
    field_prefix: str,
    current_day: date,
    issues: list[PolicyIssue],
) -> None:
    for index, raw_exception in enumerate(raw_rule.get("exceptions") or []):
        exception_prefix = f"{field_prefix}.exceptions[{index}]"
        if not isinstance(raw_exception, dict):
            issues.append(PolicyIssue(field=exception_prefix, message="must be a map"))
            continue
        if not str(raw_exception.get("exception_id") or "").strip():
            issues.append(
                PolicyIssue(field=f"{exception_prefix}.exception_id", message="is required")
            )
        case_id = str(raw_exception.get("case_id") or "").strip()
        milestone_id = str(raw_exception.get("milestone_id") or "").strip()
        if not case_id and not milestone_id:
            issues.append(
                PolicyIssue(
                    field=f"{exception_prefix}.case_id",
                    message="requires case_id or milestone_id",
                )
            )
        if not str(raw_exception.get("owner_module") or "").strip():
            issues.append(
                PolicyIssue(field=f"{exception_prefix}.owner_module", message="is required")
            )
        follow_up = str(raw_exception.get("follow_up_condition") or "").strip()
        expires_on_raw = raw_exception.get("expires_on")
        if not follow_up and not expires_on_raw:
            issues.append(
                PolicyIssue(
                    field=f"{exception_prefix}.expires_on",
                    message="requires expires_on or follow_up_condition",
                )
            )
        _validate_exception_expiry(expires_on_raw, exception_prefix, current_day, issues)


def _validate_exception_expiry(
    expires_on_raw: Any,
    exception_prefix: str,
    current_day: date,
    issues: list[PolicyIssue],
) -> None:
    if not expires_on_raw:
        return
    try:
        expires_on = parse_policy_date(expires_on_raw)
    except ValueError:
        issues.append(
            PolicyIssue(
                field=f"{exception_prefix}.expires_on",
                message="must be an ISO date",
            )
        )
        return
    if expires_on is not None and expires_on < current_day:
        issues.append(PolicyIssue(field=f"{exception_prefix}.expires_on", message="is expired"))


def build_hotspot_policy(payload: dict[str, Any]) -> HotspotPolicy:
    issues = validate_policy_payload(payload)
    if issues:
        rendered = "; ".join(f"{issue.field}: {issue.message}" for issue in issues)
        raise ValueError(f"invalid hotspot prevention policy: {rendered}")
    known_hotspots: dict[str, HotspotRule] = {}
    for relative_path, raw_rule in sorted(payload["known_hotspots"].items()):
        known_hotspots[str(relative_path)] = HotspotRule(
            relative_path=str(relative_path),
            target_role=str(raw_rule["target_role"]).strip(),
            preferred_owner_modules=string_list(raw_rule["preferred_owner_modules"]),
            block_new=string_list(raw_rule["block_new"]),
            allow=string_list(raw_rule["allow"]),
            exceptions=tuple(
                build_hotspot_exception(raw_exception)
                for raw_exception in raw_rule.get("exceptions") or []
            ),
        )
    return HotspotPolicy(
        schema_name=str(payload["schema_name"]),
        schema_version=str(payload["schema_version"]),
        known_hotspots=known_hotspots,
    )


def build_hotspot_exception(raw_exception: dict[str, Any]) -> HotspotException:
    exception_id = str(raw_exception.get("exception_id") or "").strip()
    case_id = str(raw_exception.get("case_id") or "").strip() or None
    milestone_id = str(raw_exception.get("milestone_id") or "").strip() or None
    match_tokens = string_list(raw_exception.get("match_tokens"))
    fallback_tokens = tuple(
        token for token in (exception_id, case_id or "", milestone_id or "") if token
    )
    return HotspotException(
        exception_id=exception_id,
        case_id=case_id,
        milestone_id=milestone_id,
        owner_module=str(raw_exception.get("owner_module") or "").strip(),
        expires_on=parse_policy_date(raw_exception.get("expires_on")),
        follow_up_condition=str(raw_exception.get("follow_up_condition") or "").strip() or None,
        match_tokens=match_tokens or fallback_tokens,
    )


def load_hotspot_policy(
    policy_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> HotspotPolicy:
    root = project_root or repo_root()
    raw_path = policy_path or DEFAULT_POLICY_PATH
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    payload = yaml.safe_load(resolved_path.read_text()) or {}
    if not isinstance(payload, dict):
        raise ValueError("hotspot prevention policy must be a map")
    return build_hotspot_policy(payload)
