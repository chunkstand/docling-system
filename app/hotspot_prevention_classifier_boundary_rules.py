from __future__ import annotations

from app.hotspot_prevention_classifier_support import (
    ClassifiedLine,
    blocked,
    classified_surface_decision,
    classify_cli_test_surface_addition,
    classify_local_test_support_surface_addition,
    classify_residual_test_surface_addition,
)
from app.hotspot_prevention_diff import ChangedLine
from app.hotspot_prevention_policy import HotspotRule


def classify_cli_addition(
    *,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    parser_registration = "add_parser(" in stripped or ".set_defaults(" in stripped
    if parser_registration and "parser_registration" in rule.allow:
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="parser_registration",
            message="parser registration is allowed on the CLI facade",
            policy_rule="allow.parser_registration",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "command_implementation",
            "new command bodies belong in app/cli_commands/",
        )
    if "ArgumentParser(" in stripped:
        return blocked(
            line,
            "broad_parser_logic",
            "broad parser logic belongs in app/cli_commands/",
        )
    if any(
        token in stripped
        for token in (
            "session_factory = get_session_factory()",
            "with session_factory() as session",
            "storage_service = StorageService(",
            "storage_service=StorageService(",
        )
    ):
        return blocked(
            line,
            "session_or_storage_wiring",
            "session or storage wiring belongs in app/cli_commands/",
        )
    if any(
        token in stripped
        for token in (
            "parser.add_argument(",
            "parser.parse_args(",
            "parser.error(",
            "json.dumps(",
            "model_dump(",
        )
    ):
        return blocked(
            line,
            "json_render_or_parser_body_scaffolding",
            "parser-body and JSON-render scaffolding belongs in app/cli_commands/",
        )
    return None


def classify_agent_action_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if stripped.startswith("class "):
        return blocked(
            line,
            "schema_builder",
            "new action schemas belong in app/services/agent_actions/",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "action_family_helper",
            "new action-family helpers belong in app/services/agent_actions/",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "executor_implementation",
            "new executor implementations belong in app/services/agent_actions/",
        )
    return None


def classify_agent_task_context_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    if stripped.startswith("class "):
        return blocked(
            line,
            "context_builder_implementation",
            "new context contracts belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def _build_", "async def _build_")):
        return blocked(
            line,
            "context_builder_implementation",
            "new context builders belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "context_family_helper",
            "new context helpers belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "context_builder_implementation",
            "new context composition belongs in app/services/agent_task_context_*.py",
        )
    return None


def classify_agent_task_router_addition(
    *,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    if stripped.startswith("router.include_router(") and "router_registration" in rule.allow:
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="router_registration",
            message="focused router registration is allowed on the composition surface",
            policy_rule="allow.router_registration",
        )
    if stripped.startswith("@router."):
        return blocked(
            line,
            "route_family_implementation",
            "new route families belong in focused agent-task sibling routers",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "route_family_implementation",
            "new route handlers belong in focused agent-task sibling routers",
        )
    return None


def classify_cli_test_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    return classified_surface_decision(
        line=line,
        decision=classify_cli_test_surface_addition(stripped=stripped),
    )


def classify_residual_test_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    return classified_surface_decision(
        line=line,
        decision=classify_residual_test_surface_addition(stripped=stripped),
    )


def classify_local_test_support_addition(
    *, stripped: str, line: ChangedLine
) -> ClassifiedLine | None:
    return classified_surface_decision(
        line=line,
        decision=classify_local_test_support_surface_addition(stripped=stripped),
    )
