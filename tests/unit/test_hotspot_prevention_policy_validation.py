from __future__ import annotations

from datetime import date

from app.hotspot_prevention import POLICY_SCHEMA_NAME, load_hotspot_policy, validate_policy_payload
from tests.unit.hotspot_prevention_test_support import (
    ACCEPTED_RESIDUAL_SUPPORT_PATHS,
    DEFERRED_REDUCED_FACADE_PATHS,
)


def test_loaded_policy_routes_expected_reduced_and_trapped_surfaces() -> None:
    policy = load_hotspot_policy()

    assert policy.known_hotspots["app/db/models.py"].routing is not None
    assert policy.known_hotspots["app/db/models.py"].routing.status == "accepted_residual"
    assert policy.known_hotspots["app/api/main.py"].routing is not None
    assert policy.known_hotspots["app/api/main.py"].routing.status == "accepted_residual"
    assert policy.known_hotspots["app/services/audit_bundles.py"].routing is not None
    assert (
        policy.known_hotspots["app/services/audit_bundles.py"].routing.status
        == "accepted_residual"
    )
    for path in [
        "app/cli.py",
        "app/schemas/agent_tasks.py",
        "app/services/agent_task_actions.py",
        "app/services/agent_tasks.py",
        "app/services/evidence.py",
        "app/services/search.py",
    ]:
        assert policy.known_hotspots[path].routing is not None
        assert policy.known_hotspots[path].routing.status == "accepted_residual"
    assert policy.known_hotspots["app/services/semantic_registry.py"].routing is not None
    assert (
        policy.known_hotspots["app/services/semantic_registry.py"].routing.status
        == "compatibility_facade_trap"
    )
    assert (
        policy.known_hotspots["app/services/retrieval_learning_artifacts.py"].routing
        is not None
    )
    assert (
        policy.known_hotspots["app/services/retrieval_learning_artifacts.py"].routing.status
        == "compatibility_facade_trap"
    )
    assert policy.known_hotspots["app/services/search_harnesses.py"].routing is not None
    assert (
        policy.known_hotspots["app/services/search_harnesses.py"].routing.status
        == "compatibility_facade_trap"
    )
    assert policy.known_hotspots["app/cli_commands/search_harness.py"].routing is not None
    assert (
        policy.known_hotspots["app/cli_commands/search_harness.py"].routing.status
        == "compatibility_facade_trap"
    )
    for path in DEFERRED_REDUCED_FACADE_PATHS:
        assert policy.known_hotspots[path].routing is not None
        assert policy.known_hotspots[path].routing.status == "deferred_reduced_facade"
    assert policy.known_hotspots["app/hotspot_prevention_classifier_support.py"].routing is None
    assert policy.known_hotspots["tests/unit/test_cli.py"].routing is not None
    assert policy.known_hotspots["app/services/search.py"].routing is not None
    assert (
        policy.known_hotspots["tests/integration/retrieval_learning_ledger_support.py"].routing
        is not None
    )
    assert (
        policy.known_hotspots["tests/integration/retrieval_learning_ledger_support.py"].routing.status
        == "accepted_residual"
    )
    for path in [
        "tests/unit/test_agent_task_context_reports_claim_support.py",
        "tests/unit/test_agent_task_context_semantic_graph_promotions.py",
        *ACCEPTED_RESIDUAL_SUPPORT_PATHS,
    ]:
        assert policy.known_hotspots[path].exceptions == ()

    for path in ACCEPTED_RESIDUAL_SUPPORT_PATHS:
        assert policy.known_hotspots[path].routing is not None
        assert policy.known_hotspots[path].routing.status == "accepted_residual"


def test_policy_validation_rejects_missing_owner_and_unowned_exception() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": [],
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
                "exceptions": [
                    {
                        "exception_id": "temporary",
                        "follow_up_condition": "remove after split",
                    }
                ],
            }
        },
    }

    issues = validate_policy_payload(payload)

    fields = {issue.field for issue in issues}
    assert "known_hotspots.app/services/evidence.py.preferred_owner_modules" in fields
    assert "known_hotspots.app/services/evidence.py.exceptions[0].case_id" in fields
    assert "known_hotspots.app/services/evidence.py.exceptions[0].owner_module" in fields


def test_policy_validation_rejects_expired_exceptions() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": ["app/services/evidence_new.py"],
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
                "exceptions": [
                    {
                        "exception_id": "temporary",
                        "milestone_id": "residual-weakness-milestone-1",
                        "owner_module": "app/services/evidence_new.py",
                        "expires_on": "2026-05-01",
                    }
                ],
            }
        },
    }

    issues = validate_policy_payload(payload, today=date(2026, 5, 10))

    assert (
        "known_hotspots.app/services/evidence.py.exceptions[0].expires_on",
        "is expired",
    ) in {(issue.field, issue.message) for issue in issues}


def test_policy_validation_rejects_trap_routing_without_successors() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": ["app/services/evidence_*.py"],
                "routing": {
                    "status": "compatibility_facade_trap",
                    "reason": "Facade is already reduced.",
                },
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
            }
        },
    }

    issues = validate_policy_payload(payload)

    assert {
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_case_ids",
            "must contain at least one routed case id",
        ),
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_paths",
            "must contain at least one routed path",
        ),
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_plan_paths",
            "must contain at least one routed plan path",
        ),
    } <= {(issue.field, issue.message) for issue in issues}
