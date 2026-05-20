from __future__ import annotations

from app.hotspot_prevention_classifier_support import ClassifiedLine, blocked
from app.hotspot_prevention_diff import ChangedLine
from app.hotspot_prevention_policy import HotspotRule


def classify_hotspot_prevention_classifier_addition(
    *,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    if stripped.startswith("if path "):
        return blocked(
            line,
            "dispatcher_rule_logic",
            "new dispatch branches belong in focused classifier-family owner modules",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "dispatcher_helper",
            "new dispatcher helpers belong in focused classifier-family owner modules",
        )
    if stripped.startswith(("def ", "async def ", "class ")):
        return blocked(
            line,
            "dispatcher_rule_logic",
            "new classifier implementation belongs in focused classifier-family owner modules",
        )
    if "registry_composition" in rule.allow and stripped.startswith(
        ('"app/', '"tests/', "'app/", "'tests/")
    ) and (": " in stripped or stripped.endswith(('",', "',"))):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="registry_composition",
            message="classifier-family routing entries are allowed on the dispatcher",
            policy_rule="allow.registry_composition",
        )
    return None


def classify_hotspot_prevention_classifier_support_addition(
    *,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    del rule
    if stripped.startswith(("class ", "def ", "async def ")):
        return blocked(
            line,
            "broad_helper",
            "new helper growth belongs in a narrower classifier-family owner module",
        )
    return None
