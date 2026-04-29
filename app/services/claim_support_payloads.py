from __future__ import annotations

from typing import Any

from app.db.models import SemanticGovernanceEvent


def claim_support_fixture_promotion_payload(
    event: SemanticGovernanceEvent,
) -> dict[str, Any]:
    return dict(
        (event.event_payload_json or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        )
        or {}
    )
