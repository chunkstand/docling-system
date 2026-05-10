from __future__ import annotations

import pytest

from app.services.retrieval_learning_replay_alert_sources import (
    claim_support_expected_judgment,
)


def test_claim_support_expected_judgment_supported() -> None:
    assert claim_support_expected_judgment({"expected_verdict": "supported"}) == (
        "positive",
        "claim_support_expected_supported",
        "Claim-support replay-alert fixture expects the claim to be supported.",
    )


def test_claim_support_expected_judgment_rejects_unknown_verdict() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported claim-support replay-alert fixture expected_verdict",
    ):
        claim_support_expected_judgment({"expected_verdict": "needs_review"})
