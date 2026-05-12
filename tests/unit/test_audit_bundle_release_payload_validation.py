from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.audit_bundle_release_payload_validation import (
    SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
    semantic_governance_chain_checks,
    validate_bundle_source_integrity,
    validate_release_semantic_governance_policy,
)


def test_semantic_governance_chain_checks_reports_external_and_mismatched_links() -> None:
    event_a = str(uuid4())
    event_b = str(uuid4())

    checks = semantic_governance_chain_checks(
        [
            {"event_id": event_a, "event_hash": "hash-a"},
            {
                "event_id": event_b,
                "event_hash": "hash-b",
                "previous_event_id": event_a,
                "previous_event_hash": "wrong-hash",
            },
            {
                "event_id": str(uuid4()),
                "event_hash": "hash-c",
                "previous_event_id": str(uuid4()),
                "previous_event_hash": "missing",
            },
        ]
    )

    assert checks["event_count"] == 3
    assert checks["hash_link_mismatch_count"] == 1
    assert checks["external_previous_event_count"] == 1
    assert checks["hash_links_verified"] is False


def test_validate_release_semantic_governance_policy_rejects_broken_chain() -> None:
    errors = validate_release_semantic_governance_policy(
        {
            "semantic_governance_policy": {
                "schema_name": "search_harness_release_semantic_governance_policy",
                "complete": True,
                "checks": {
                    "complete": True,
                    "has_release_governance_event": True,
                    "hash_links_verified": True,
                },
            },
            "semantic_governance_events": [
                {"event_id": "a", "event_hash": "hash-a"},
                {
                    "event_id": "b",
                    "event_hash": "hash-b",
                    "previous_event_id": "a",
                    "previous_event_hash": "wrong-hash",
                },
            ],
        }
    )

    assert [error["code"] for error in errors] == ["semantic_governance_chain_broken"]


def test_validate_bundle_source_integrity_rejects_release_fk_mismatch() -> None:
    release_id = uuid4()
    row = SimpleNamespace(
        id=uuid4(),
        bundle_kind=SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        source_table="search_harness_releases",
        source_id=release_id,
        search_harness_release_id=uuid4(),
        retrieval_training_run_id=uuid4(),
    )

    errors = validate_bundle_source_integrity(
        row=row,
        bundle={
            "bundle_export": {
                "bundle_kind": SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
                "source_table": "search_harness_releases",
                "source_id": str(release_id),
            },
            "payload": {
                "source": {
                    "source_table": "search_harness_releases",
                    "source_id": str(release_id),
                }
            },
        },
    )

    assert [error["code"] for error in errors] == ["release_source_fk_mismatch"]
