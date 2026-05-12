from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.audit_bundle_training_runs import (
    retrieval_training_run_full_payload,
    training_audit_bundle_current_for_training_run,
    training_audit_bundle_hashes_match_training_run,
)


def test_training_audit_bundle_hashes_match_training_run_requires_payload_consistency() -> None:
    training_run_id = uuid4()
    training_run = SimpleNamespace(
        id=training_run_id,
        training_dataset_sha256="dataset-sha",
    )
    matching_bundle = SimpleNamespace(
        bundle_kind="retrieval_training_run_provenance",
        source_table="retrieval_training_runs",
        source_id=training_run_id,
        retrieval_training_run_id=training_run_id,
        bundle_payload_json={
            "payload": {
                "source": {
                    "source_table": "retrieval_training_runs",
                    "source_id": str(training_run_id),
                },
                "retrieval_training_run": {
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": "dataset-sha",
                },
                "integrity": {
                    "training_dataset_hash_matches": True,
                },
            }
        },
    )

    assert training_audit_bundle_hashes_match_training_run(matching_bundle, training_run) is True

    mismatched_bundle = SimpleNamespace(**matching_bundle.__dict__)
    mismatched_bundle.bundle_payload_json = {
        "payload": {
            **matching_bundle.bundle_payload_json["payload"],
            "retrieval_training_run": {
                "retrieval_training_run_id": str(training_run_id),
                "training_dataset_sha256": "wrong-sha",
            },
        }
    }

    assert training_audit_bundle_hashes_match_training_run(mismatched_bundle, training_run) is False


def test_training_audit_bundle_current_for_training_run_requires_current_lineage(
    monkeypatch,
) -> None:
    training_run_id = uuid4()
    training_run = SimpleNamespace(
        id=training_run_id,
        training_dataset_sha256="dataset-sha",
    )
    bundle = SimpleNamespace(
        bundle_kind="retrieval_training_run_provenance",
        source_table="retrieval_training_runs",
        source_id=training_run_id,
        retrieval_training_run_id=training_run_id,
        bundle_payload_json={
            "payload": {
                "source": {
                    "source_table": "retrieval_training_runs",
                    "source_id": str(training_run_id),
                },
                "retrieval_training_run": {
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": "dataset-sha",
                },
                "integrity": {
                    "training_dataset_hash_matches": True,
                },
            }
        },
    )

    monkeypatch.setattr(
        "app.services.audit_bundle_training_runs._training_audit_bundle_claim_support_replay_alert_corpus_lineage_status",
        lambda session, bundle, training_run: {
            "bundle_complete": True,
            "current_complete": True,
            "source_reference_counts_match": True,
        },
    )
    assert training_audit_bundle_current_for_training_run(None, bundle, training_run) is True

    monkeypatch.setattr(
        "app.services.audit_bundle_training_runs._training_audit_bundle_claim_support_replay_alert_corpus_lineage_status",
        lambda session, bundle, training_run: {
            "bundle_complete": True,
            "current_complete": False,
            "source_reference_counts_match": True,
        },
    )
    assert training_audit_bundle_current_for_training_run(None, bundle, training_run) is False


def test_retrieval_training_run_full_payload_includes_training_payload_and_links() -> None:
    training_run_id = uuid4()
    judgment_set_id = uuid4()
    evaluation_id = uuid4()
    release_id = uuid4()
    event_id = uuid4()
    row = SimpleNamespace(
        id=training_run_id,
        judgment_set_id=judgment_set_id,
        status="completed",
        run_kind="reranker_training",
        training_dataset_sha256="dataset-sha",
        example_count=5,
        positive_count=2,
        negative_count=1,
        missing_count=1,
        hard_negative_count=1,
        summary_json={"complete": True},
        created_by="operator",
        created_at=SimpleNamespace(isoformat=lambda: "2026-05-12T00:00:00Z"),
        completed_at=SimpleNamespace(isoformat=lambda: "2026-05-12T00:05:00Z"),
        search_harness_evaluation_id=evaluation_id,
        search_harness_release_id=release_id,
        semantic_governance_event_id=event_id,
        training_payload_json={"judgments": [], "hard_negatives": []},
    )

    payload = retrieval_training_run_full_payload(row)

    assert payload["retrieval_training_run_id"] == str(training_run_id)
    assert payload["judgment_set_id"] == str(judgment_set_id)
    assert payload["search_harness_evaluation_id"] == str(evaluation_id)
    assert payload["search_harness_release_id"] == str(release_id)
    assert payload["semantic_governance_event_id"] == str(event_id)
    assert payload["training_payload"] == {"judgments": [], "hard_negatives": []}
