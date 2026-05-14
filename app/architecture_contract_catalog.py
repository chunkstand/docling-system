from __future__ import annotations

from collections.abc import Mapping

ARCHITECTURE_CONTRACT_NAMES = (
    "architecture_contract_map",
    "api_route_capabilities",
    "agent_action_catalog",
    "capability_surface_contracts",
    "improvement_case_registry",
    "improvement_case_intake",
    "improvement_case_lifecycle",
    "architecture_decisions",
    "architecture_measurement_history",
    "architecture_quality_report",
)


def list_architecture_contract_names() -> tuple[str, ...]:
    return ARCHITECTURE_CONTRACT_NAMES


def ordered_architecture_contracts(
    contracts_by_name: Mapping[str, dict[str, object]],
) -> list[dict[str, object]]:
    expected_contract_names = list_architecture_contract_names()
    missing_contract_names = set(expected_contract_names) - set(contracts_by_name)
    unexpected_contract_names = set(contracts_by_name) - set(expected_contract_names)
    if missing_contract_names or unexpected_contract_names:
        details = []
        if missing_contract_names:
            details.append(f"missing={sorted(missing_contract_names)}")
        if unexpected_contract_names:
            details.append(f"unexpected={sorted(unexpected_contract_names)}")
        raise ValueError("architecture contract catalog drift: " + ", ".join(details))
    return [contracts_by_name[name] for name in expected_contract_names]
