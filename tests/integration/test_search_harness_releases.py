from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.db.models import (
    AuditBundleExport,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalTrainingRun,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchReplayRun,
)
from app.services.semantic_governance import record_semantic_governance_event


def _replay_run(*, replay_run_id, harness_name: str) -> SearchReplayRun:
    now = datetime.now(UTC)
    return SearchReplayRun(
        id=replay_run_id,
        source_type="evaluation_queries",
        status="completed",
        harness_name=harness_name,
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name=harness_name,
        harness_config_json={},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        error_message=None,
        created_at=now,
        completed_at=now + timedelta(seconds=1),
    )


def test_search_harness_release_gate_roundtrip(postgres_integration_harness, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.audit_bundles.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="integration-secret",
            audit_bundle_signing_key_id="integration-key",
        ),
    )
    now = datetime.now(UTC)
    evaluation_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    with postgres_integration_harness.session_factory() as session:
        session.add_all(
            [
                _replay_run(
                    replay_run_id=baseline_replay_run_id,
                    harness_name="default_v1",
                ),
                _replay_run(
                    replay_run_id=candidate_replay_run_id,
                    harness_name="wide_v2",
                ),
                SearchHarnessEvaluation(
                    id=evaluation_id,
                    status="completed",
                    baseline_harness_name="default_v1",
                    candidate_harness_name="wide_v2",
                    limit=4,
                    source_types_json=["evaluation_queries"],
                    harness_overrides_json={},
                    total_shared_query_count=4,
                    total_improved_count=1,
                    total_regressed_count=0,
                    total_unchanged_count=3,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now + timedelta(seconds=2),
                ),
            ]
        )
        session.flush()
        session.add(
            SearchHarnessEvaluationSource(
                id=uuid4(),
                search_harness_evaluation_id=evaluation_id,
                source_index=0,
                source_type="evaluation_queries",
                baseline_replay_run_id=baseline_replay_run_id,
                candidate_replay_run_id=candidate_replay_run_id,
                baseline_status="completed",
                candidate_status="completed",
                baseline_query_count=4,
                candidate_query_count=4,
                baseline_passed_count=4,
                candidate_passed_count=4,
                baseline_zero_result_count=0,
                candidate_zero_result_count=0,
                baseline_table_hit_count=1,
                candidate_table_hit_count=1,
                baseline_top_result_changes=0,
                candidate_top_result_changes=0,
                baseline_mrr=1.0,
                candidate_mrr=1.0,
                baseline_foreign_top_result_count=0,
                candidate_foreign_top_result_count=0,
                acceptance_checks_json={"no_regressions": True},
                shared_query_count=4,
                improved_count=1,
                regressed_count=0,
                unchanged_count=3,
                created_at=now,
            )
        )
        session.commit()

    response = postgres_integration_harness.client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "min_total_shared_query_count": 1,
            "requested_by": "integration",
            "review_note": "roundtrip",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "passed"
    assert body["evaluation_id"] == str(evaluation_id)
    assert body["evaluation_snapshot"]["evaluation_id"] == str(evaluation_id)
    assert body["release_package_sha256"]
    release_id = body["release_id"]

    with postgres_integration_harness.session_factory() as session:
        release = session.get(SearchHarnessRelease, UUID(release_id))
        assert release is not None
        judgment_set_id = uuid4()
        training_run_id = uuid4()
        candidate_id = uuid4()
        session.add(
            RetrievalJudgmentSet(
                id=judgment_set_id,
                set_name="release-audit-learning-set",
                set_kind="mixed",
                source_types_json=["feedback", "replay"],
                source_limit=10,
                criteria_json={"fixture": "release-audit"},
                summary_json={"training_example_count": 4},
                judgment_count=2,
                positive_count=1,
                negative_count=1,
                missing_count=0,
                hard_negative_count=2,
                payload_sha256="judgment-set-sha",
                created_by="integration",
                created_at=now,
            )
        )
        session.add(
            RetrievalTrainingRun(
                id=training_run_id,
                judgment_set_id=judgment_set_id,
                run_kind="materialized_training_dataset",
                status="completed",
                search_harness_evaluation_id=evaluation_id,
                search_harness_release_id=UUID(release_id),
                training_dataset_sha256="training-dataset-sha",
                training_payload_json={"summary": {"training_example_count": 4}},
                summary_json={"training_example_count": 4},
                example_count=4,
                positive_count=1,
                negative_count=1,
                missing_count=0,
                hard_negative_count=2,
                created_by="integration",
                created_at=now,
                completed_at=now + timedelta(seconds=3),
            )
        )
        session.flush()
        candidate = RetrievalLearningCandidateEvaluation(
            id=candidate_id,
            retrieval_training_run_id=training_run_id,
            judgment_set_id=judgment_set_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=UUID(release_id),
            training_dataset_sha256="training-dataset-sha",
            training_example_count=4,
            positive_count=1,
            negative_count=1,
            missing_count=0,
            hard_negative_count=2,
            baseline_harness_name="default_v1",
            candidate_harness_name="wide_v2",
            source_types_json=["evaluation_queries"],
            limit=4,
            status="completed",
            gate_outcome="passed",
            thresholds_json={"max_total_regressed_count": 0},
            metrics_json={"total_shared_query_count": 4},
            reasons_json=[],
            evaluation_snapshot_json=body["evaluation_snapshot"],
            release_snapshot_json=body,
            details_json={"fixture": "release-audit-learning-candidate"},
            learning_package_sha256="learning-package-sha",
            created_by="integration",
            review_note="learning candidate audit",
            created_at=now,
            completed_at=now + timedelta(seconds=4),
        )
        session.add(candidate)
        session.flush()
        event = record_semantic_governance_event(
            session,
            event_kind="retrieval_learning_candidate_evaluated",
            governance_scope=f"retrieval_learning:{training_run_id}",
            subject_table="retrieval_learning_candidate_evaluations",
            subject_id=candidate_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=UUID(release_id),
            event_payload={
                "retrieval_learning_candidate_evaluation": {
                    "candidate_evaluation_id": str(candidate_id),
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": "training-dataset-sha",
                    "learning_package_sha256": "learning-package-sha",
                }
            },
            deduplication_key=f"release-audit-learning-candidate:{candidate_id}",
            created_by="integration",
        )
        candidate.semantic_governance_event_id = event.id
        session.commit()

    list_response = postgres_integration_harness.client.get("/search/harness-releases")
    assert list_response.status_code == 200
    assert list_response.json()[0]["release_id"] == release_id

    detail_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["details"]["per_source"]["evaluation_queries"][
        "shared_query_count"
    ] == 4

    audit_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_response.headers["Location"] == (
        f"/search/audit-bundles/{audit_bundle['bundle_id']}"
    )
    assert audit_bundle["bundle_kind"] == "search_harness_release_provenance"
    assert audit_bundle["integrity"]["complete"] is True
    assert audit_bundle["integrity"]["signature_valid"] is True
    assert audit_bundle["bundle"]["payload"]["audit_checklist"]["complete"] is True
    assert audit_bundle["bundle"]["payload"]["audit_checklist"][
        "learning_candidate_count"
    ] == 1
    assert audit_bundle["bundle"]["payload"]["integrity"][
        "release_package_hash_matches"
    ] is True
    assert audit_bundle["bundle"]["payload"]["integrity"][
        "training_run_count"
    ] == 1
    assert audit_bundle["bundle"]["payload"]["retrieval_learning_candidates"][0][
        "training_dataset_sha256"
    ] == "training-dataset-sha"
    assert audit_bundle["bundle"]["payload"]["retrieval_training_runs"][0][
        "training_dataset_sha256"
    ] == "training-dataset-sha"
    assert audit_bundle["bundle"]["payload"]["semantic_governance_events"][0][
        "event_kind"
    ] == "retrieval_learning_candidate_evaluated"
    assert audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    assert any(
        edge["usedEntity"].startswith("docling:retrieval_training_run:")
        for edge in audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    )
    assert audit_bundle["signing_key_id"] == "integration-key"

    latest_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/audit-bundles/latest"
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["bundle_id"] == audit_bundle["bundle_id"]

    audit_detail_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}"
    )
    assert audit_detail_response.status_code == 200
    assert audit_detail_response.json()["integrity"]["bundle_hash_matches_row"] is True

    with postgres_integration_harness.session_factory() as session:
        row = session.get(AuditBundleExport, audit_bundle["bundle_id"])
        assert row is not None
        assert row.bundle_sha256 == audit_bundle["bundle_sha256"]
        assert row.search_harness_release_id == UUID(audit_bundle["source_id"])
        storage_path = Path(row.storage_path)

    stored_bundle = json.loads(storage_path.read_text())
    stored_bundle["payload"]["release"]["outcome"] = "tampered"
    storage_path.write_text(json.dumps(stored_bundle))

    tampered_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}"
    )
    assert tampered_response.status_code == 200
    tampered_integrity = tampered_response.json()["integrity"]
    assert tampered_integrity["complete"] is False
    assert tampered_integrity["payload_hash_matches_row"] is False
    assert tampered_integrity["bundle_hash_matches_row"] is False
    assert tampered_integrity["stored_payload_matches_file"] is False
