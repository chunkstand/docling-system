from __future__ import annotations

from app.hotspot_prevention import load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import EXPECTED_KNOWN_HOTSPOT_PATHS


def test_hotspot_policy_contracts_smoke_loads_expected_surfaces() -> None:
    policy = load_hotspot_policy()

    assert sorted(policy.known_hotspots) == EXPECTED_KNOWN_HOTSPOT_PATHS
    for rule in policy.known_hotspots.values():
        assert rule.preferred_owner_modules
        assert rule.block_new
    assert (
        policy.known_hotspots["tests/unit/test_hotspot_prevention_policy_contracts.py"].routing
        is not None
    )
    assert (
        policy.known_hotspots["tests/unit/test_hotspot_prevention_policy_contracts.py"].routing.status
        == "deferred_reduced_facade"
    )
