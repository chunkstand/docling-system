from __future__ import annotations

from app.services.claim_support_policy_governance import (
    claim_support_policy_change_impact_payload_sha256,
)


def test_claim_support_policy_change_impact_hash_excludes_recorded_hash() -> None:
    payload = {
        "schema_name": "claim_support_policy_change_impact",
        "schema_version": "1.0",
        "change_impact_id": "00000000-0000-0000-0000-000000000001",
        "impact_summary": {
            "affected_support_judgment_count": 1,
            "replay_recommended_count": 1,
        },
    }
    payload_sha = claim_support_policy_change_impact_payload_sha256(payload)

    payload_with_recorded_hash = {
        **payload,
        "activation_change_impact_payload_sha256": payload_sha,
    }

    assert (
        claim_support_policy_change_impact_payload_sha256(payload_with_recorded_hash)
        == payload_sha
    )

    tampered_payload = {
        **payload_with_recorded_hash,
        "impact_summary": {
            "affected_support_judgment_count": 2,
            "replay_recommended_count": 1,
        },
    }
    assert claim_support_policy_change_impact_payload_sha256(tampered_payload) != payload_sha
