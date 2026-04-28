from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.models import (
    AuditBundleExport,
    AuditBundleValidationReceipt,
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalTrainingRun,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchReplayRun,
)
from app.services.semantic_governance import record_semantic_governance_event


def _payload_sha256(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


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
        judgment_id = uuid4()
        hard_negative_id = uuid4()
        training_payload = {
            "schema_name": "retrieval_learning_dataset",
            "schema_version": "1.0",
            "judgment_set": {
                "judgment_set_id": str(judgment_set_id),
                "set_name": "release-audit-learning-set",
            },
            "summary": {
                "training_example_count": 2,
                "judgment_count": 1,
                "hard_negative_count": 1,
            },
            "judgments": [{"judgment_id": str(judgment_id), "source_payload_sha256": "j-sha"}],
            "hard_negatives": [
                {"hard_negative_id": str(hard_negative_id), "source_payload_sha256": "hn-sha"}
            ],
        }
        training_dataset_sha256 = _payload_sha256(training_payload)
        session.add(
            RetrievalJudgmentSet(
                id=judgment_set_id,
                set_name="release-audit-learning-set",
                set_kind="mixed",
                source_types_json=["feedback", "replay"],
                source_limit=10,
                criteria_json={"fixture": "release-audit"},
                summary_json={"training_example_count": 2},
                judgment_count=1,
                positive_count=1,
                negative_count=0,
                missing_count=0,
                hard_negative_count=1,
                payload_sha256=training_dataset_sha256,
                created_by="integration",
                created_at=now,
            )
        )
        training_run = RetrievalTrainingRun(
            id=training_run_id,
            judgment_set_id=judgment_set_id,
            run_kind="materialized_training_dataset",
            status="completed",
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=UUID(release_id),
            training_dataset_sha256=training_dataset_sha256,
            training_payload_json=training_payload,
            summary_json={"training_example_count": 2},
            example_count=2,
            positive_count=1,
            negative_count=0,
            missing_count=0,
            hard_negative_count=1,
            created_by="integration",
            created_at=now,
            completed_at=now + timedelta(seconds=3),
        )
        session.add(training_run)
        session.flush()
        training_event = record_semantic_governance_event(
            session,
            event_kind="retrieval_training_run_materialized",
            governance_scope=f"retrieval_training:{training_run_id}",
            subject_table="retrieval_training_runs",
            subject_id=training_run_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=UUID(release_id),
            event_payload={
                "retrieval_training_run": {
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": training_dataset_sha256,
                }
            },
            deduplication_key=f"release-audit-training-run:{training_run_id}",
            created_by="integration",
        )
        training_run.semantic_governance_event_id = training_event.id
        session.add(
            RetrievalJudgment(
                id=judgment_id,
                judgment_set_id=judgment_set_id,
                judgment_kind="positive",
                judgment_label="relevant",
                source_type="feedback",
                source_ref_id=None,
                search_feedback_id=None,
                search_replay_query_id=None,
                search_replay_run_id=None,
                evaluation_query_id=None,
                source_search_request_id=None,
                search_request_id=None,
                search_request_result_id=None,
                result_rank=1,
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                score=0.9,
                query_text="fixture query",
                mode="hybrid",
                filters_json={},
                expected_result_type="table",
                expected_top_n=1,
                harness_name="default_v1",
                reranker_name="linear_feature_reranker",
                reranker_version="v1",
                retrieval_profile_name="default_v1",
                rerank_features_json={},
                evidence_refs_json=[{"source": "fixture"}],
                rationale="relevant table",
                payload_json={"fixture": "judgment"},
                source_payload_sha256="j-sha",
                deduplication_key=f"release-audit-judgment:{judgment_id}",
                created_at=now,
            )
        )
        session.flush()
        session.add(
            RetrievalHardNegative(
                id=hard_negative_id,
                judgment_set_id=judgment_set_id,
                judgment_id=judgment_id,
                positive_judgment_id=judgment_id,
                hard_negative_kind="explicit_irrelevant",
                source_type="feedback",
                source_ref_id=None,
                search_feedback_id=None,
                search_replay_query_id=None,
                search_replay_run_id=None,
                evaluation_query_id=None,
                source_search_request_id=None,
                search_request_id=None,
                search_request_result_id=None,
                result_rank=2,
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                score=0.2,
                query_text="fixture query",
                mode="hybrid",
                filters_json={},
                rerank_features_json={},
                expected_result_type="table",
                expected_top_n=1,
                evidence_refs_json=[{"source": "fixture"}],
                reason="wrong chunk",
                details_json={"fixture": "hard-negative"},
                source_payload_sha256="hn-sha",
                deduplication_key=f"release-audit-hard-negative:{hard_negative_id}",
                created_at=now,
            )
        )
        candidate = RetrievalLearningCandidateEvaluation(
            id=candidate_id,
            retrieval_training_run_id=training_run_id,
            judgment_set_id=judgment_set_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=UUID(release_id),
            training_dataset_sha256=training_dataset_sha256,
            training_example_count=2,
            positive_count=1,
            negative_count=0,
            missing_count=0,
            hard_negative_count=1,
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
                    "training_dataset_sha256": training_dataset_sha256,
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
    assert audit_bundle["bundle"]["payload"]["integrity"][
        "training_audit_bundle_count"
    ] == 1
    assert audit_bundle["bundle"]["payload"]["integrity"][
        "training_audit_bundle_hashes_match_training_runs"
    ] is True
    assert audit_bundle["bundle"]["payload"]["integrity"][
        "training_audit_bundle_validation_receipt_count"
    ] == 1
    assert audit_bundle["bundle"]["payload"]["integrity"][
        "training_audit_bundle_validation_receipts_complete"
    ] is True
    assert audit_bundle["bundle"]["payload"]["retrieval_learning_candidates"][0][
        "training_dataset_sha256"
    ] == training_dataset_sha256
    assert audit_bundle["bundle"]["payload"]["retrieval_training_runs"][0][
        "training_dataset_sha256"
    ] == training_dataset_sha256
    assert any(
        row["event_kind"] == "search_harness_release_recorded"
        for row in audit_bundle["bundle"]["payload"]["semantic_governance_events"]
    )
    assert any(
        row["event_kind"] == "retrieval_learning_candidate_evaluated"
        for row in audit_bundle["bundle"]["payload"]["semantic_governance_events"]
    )
    semantic_governance_policy = audit_bundle["bundle"]["payload"][
        "semantic_governance_policy"
    ]
    assert semantic_governance_policy["policy_profile"] == "release_semantic_governance_v1"
    assert semantic_governance_policy["checks"]["has_release_governance_event"] is True
    assert semantic_governance_policy["checks"]["hash_links_verified"] is True
    assert semantic_governance_policy["complete"] is True
    training_audit_bundle_ref = audit_bundle["bundle"]["payload"][
        "retrieval_training_audit_bundles"
    ][0]
    assert training_audit_bundle_ref["bundle_kind"] == "retrieval_training_run_provenance"
    assert training_audit_bundle_ref["source_id"] == str(training_run_id)
    assert training_audit_bundle_ref["payload_source_id"] == str(training_run_id)
    assert training_audit_bundle_ref["payload_training_dataset_sha256"] == (
        training_dataset_sha256
    )
    assert training_audit_bundle_ref["payload_training_dataset_hash_matches"] is True
    training_validation_receipt_ref = audit_bundle["bundle"]["payload"][
        "retrieval_training_audit_bundle_validation_receipts"
    ][0]
    assert training_validation_receipt_ref["audit_bundle_export_id"] == (
        training_audit_bundle_ref["bundle_id"]
    )
    assert training_validation_receipt_ref["validation_profile"] == (
        "audit_bundle_validation_v1"
    )
    assert training_validation_receipt_ref["validation_status"] == "passed"
    assert training_validation_receipt_ref["payload_schema_valid"] is True
    assert training_validation_receipt_ref["prov_graph_valid"] is True
    assert training_validation_receipt_ref["bundle_integrity_valid"] is True
    assert training_validation_receipt_ref["source_integrity_valid"] is True
    assert training_validation_receipt_ref["receipt_sha256"]
    assert training_validation_receipt_ref["prov_jsonld_sha256"]
    assert audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    assert any(
        edge["usedEntity"].startswith("docling:retrieval_training_run:")
        for edge in audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    )
    assert any(
        edge["usedEntity"]
        == f"docling:audit_bundle_export:{training_audit_bundle_ref['bundle_id']}"
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

    auto_latest_validation_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts/latest"
    )
    assert auto_latest_validation_response.status_code == 200
    auto_validation_receipt = auto_latest_validation_response.json()
    assert auto_validation_receipt["validation_status"] == "passed"
    assert auto_validation_receipt["semantic_governance_valid"] is True

    readiness_after_export_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_after_export_response.status_code == 200
    readiness_after_export = readiness_after_export_response.json()
    assert readiness_after_export["ready"] is True
    assert readiness_after_export["checks"] == {
        "retrieval_ready": True,
        "provenance_ready": True,
        "semantic_governance_ready": True,
        "validation_receipts_ready": True,
        "ready": True,
    }
    assert readiness_after_export["validation_receipts"][
        "latest_release_validation_receipt_id"
    ] == auto_validation_receipt["receipt_id"]

    validation_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert validation_response.status_code == 200
    validation_receipt = validation_response.json()
    assert validation_response.headers["Location"] == (
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts/"
        f"{validation_receipt['receipt_id']}"
    )
    assert validation_receipt["validation_status"] == "passed"
    assert validation_receipt["receipt"]["audit_bundle"]["bundle_id"] == (
        audit_bundle["bundle_id"]
    )
    assert validation_receipt["receipt"]["receipt_sha256"] == (
        validation_receipt["receipt_sha256"]
    )
    assert validation_receipt["prov_jsonld"]["@context"]["prov"] == (
        "http://www.w3.org/ns/prov#"
    )
    assert validation_receipt["prov_jsonld"]["@graph"]
    assert validation_receipt["integrity"]["complete"] is True
    assert validation_receipt["semantic_governance_valid"] is True
    assert validation_receipt["receipt"]["validation_checks"][
        "semantic_governance_valid"
    ] is True

    validation_list_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts"
    )
    assert validation_list_response.status_code == 200
    assert validation_list_response.json()[0]["receipt_id"] == (
        validation_receipt["receipt_id"]
    )

    validation_detail_response = postgres_integration_harness.client.get(
        validation_response.headers["Location"]
    )
    assert validation_detail_response.status_code == 200
    assert validation_detail_response.json()["receipt_id"] == validation_receipt["receipt_id"]

    latest_validation_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts/latest"
    )
    assert latest_validation_response.status_code == 200
    assert latest_validation_response.json()["receipt_id"] == validation_receipt["receipt_id"]

    readiness_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["ready"] is True
    assert readiness["checks"] == {
        "retrieval_ready": True,
        "provenance_ready": True,
        "semantic_governance_ready": True,
        "validation_receipts_ready": True,
        "ready": True,
    }
    assert readiness["semantic_governance"]["checks"]["has_release_governance_event"] is True
    assert readiness["validation_receipts"]["semantic_governance_valid"] is True

    with postgres_integration_harness.session_factory() as session:
        row = session.get(AuditBundleExport, audit_bundle["bundle_id"])
        assert row is not None
        assert row.bundle_sha256 == audit_bundle["bundle_sha256"]
        assert row.search_harness_release_id == UUID(audit_bundle["source_id"])
        training_bundle_row = session.get(
            AuditBundleExport,
            UUID(training_audit_bundle_ref["bundle_id"]),
        )
        assert training_bundle_row is not None
        assert training_bundle_row.retrieval_training_run_id == training_run_id
        validation_receipt_rows = (
            session.execute(select(AuditBundleValidationReceipt)).scalars().all()
        )
        assert {row.audit_bundle_export_id for row in validation_receipt_rows} >= {
            UUID(training_audit_bundle_ref["bundle_id"]),
            UUID(audit_bundle["bundle_id"]),
        }
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
