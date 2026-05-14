from __future__ import annotations

import os

import pytest

from tests.integration import retrieval_learning_ledger_support as ledger_support

UTC, UUID, AgentTaskArtifact, AuditBundleExport, ClaimSupportReplayAlertFixtureCorpusRow = ledger_support.UTC, ledger_support.UUID, ledger_support.AgentTaskArtifact, ledger_support.AuditBundleExport, ledger_support.ClaimSupportReplayAlertFixtureCorpusRow  # noqa: E501
RetrievalLearningCandidateEvaluation, RetrievalTrainingRun = ledger_support.RetrievalLearningCandidateEvaluation, ledger_support.RetrievalTrainingRun  # noqa: E501
SearchHarnessEvaluation, SearchHarnessEvaluationSource, SearchHarnessReleaseReadinessAssessment = ledger_support.SearchHarnessEvaluation, ledger_support.SearchHarnessEvaluationSource, ledger_support.SearchHarnessReleaseReadinessAssessment  # noqa: E501
SemanticGovernanceEvent, SimpleNamespace = ledger_support.SemanticGovernanceEvent, ledger_support.SimpleNamespace  # noqa: E501
_claim_support_learning_fixture, _make_replay_run, _seed_governed_claim_support_replay_alert_corpus = ledger_support._claim_support_learning_fixture, ledger_support._make_replay_run, ledger_support._seed_governed_claim_support_replay_alert_corpus  # noqa: E501
datetime, materialize_retrieval_learning_dataset, payload_sha256 = ledger_support.datetime, ledger_support.materialize_retrieval_learning_dataset, ledger_support.payload_sha256  # noqa: E501
record_semantic_governance_event, select, uuid4 = ledger_support.record_semantic_governance_event, ledger_support.select, ledger_support.uuid4  # noqa: E501

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_retrieval_training_audit_bundle_flags_tampered_replay_alert_corpus_lineage(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-audit-tampered",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        )
    ]

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["claim_support_replay_alert_corpus"],
            set_name="integration-replay-alert-corpus-audit-tamper",
            created_by="integration",
        )
        training_run_id = response["retrieval_training_run_id"]
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .limit(1)
        )
        assert row is not None
        row.fixture_json = {
            **row.fixture_json,
            "description": "tampered after training materialization",
        }
        session.commit()

    monkeypatch.setattr(
        "app.services.audit_bundles.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="retrieval-training-secret",
            audit_bundle_signing_key_id="retrieval-training-key",
        ),
    )
    audit_response = postgres_integration_harness.client.post(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    audit_payload = audit_bundle["bundle"]["payload"]
    assert audit_payload["audit_checklist"]["complete"] is False
    assert (
        audit_payload["audit_checklist"]["claim_support_replay_alert_corpus_lineage_complete"]
        is False
    )
    corpus_integrity = audit_payload["claim_support_replay_alert_corpus_integrity"]
    assert corpus_integrity["complete"] is False
    assert corpus_integrity["row_fixture_hashes_match"] is False
    receipt_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert receipt_response.status_code == 200
    receipt_payload = receipt_response.json()
    assert receipt_payload["validation_status"] == "failed"
    assert any(
        error["code"] == "claim_support_replay_alert_corpus_lineage_incomplete"
        for error in receipt_payload["validation_errors"]
    )


def test_release_audit_bundle_refreshes_stale_replay_alert_corpus_training_bundle(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    fixture = _claim_support_learning_fixture(
        case_id="replay-alert-release-stale-lineage",
        expected_verdict="supported",
        hard_case_kind="policy_change_supported",
        rendered_text="The policy exception is supported by the cited record.",
        evidence_excerpt="The record states the exception is authorized.",
    )
    monkeypatch.setattr(
        "app.services.audit_bundles.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="retrieval-training-secret",
            audit_bundle_signing_key_id="retrieval-training-key",
        ),
    )

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=[fixture],
        )
        snapshot_id = snapshot.id
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["claim_support_replay_alert_corpus"],
            set_name="integration-replay-alert-release-stale-lineage",
            created_by="integration",
        )
        training_run_id = UUID(response["retrieval_training_run_id"])
        evaluation_id = uuid4()
        baseline_replay_run_id = uuid4()
        candidate_replay_run_id = uuid4()
        session.add_all(
            [
                _make_replay_run(
                    replay_run_id=baseline_replay_run_id,
                    harness_name="default_v1",
                    now=now,
                ),
                _make_replay_run(
                    replay_run_id=candidate_replay_run_id,
                    harness_name="candidate_v2",
                    now=now,
                ),
                SearchHarnessEvaluation(
                    id=evaluation_id,
                    status="completed",
                    baseline_harness_name="default_v1",
                    candidate_harness_name="candidate_v2",
                    limit=5,
                    source_types_json=["evaluation_queries"],
                    harness_overrides_json={},
                    total_shared_query_count=1,
                    total_improved_count=1,
                    total_regressed_count=0,
                    total_unchanged_count=0,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now,
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
                baseline_query_count=1,
                candidate_query_count=1,
                baseline_passed_count=1,
                candidate_passed_count=1,
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
                shared_query_count=1,
                improved_count=1,
                regressed_count=0,
                unchanged_count=0,
                created_at=now,
            )
        )
        session.commit()

    release_response = postgres_integration_harness.client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "min_total_shared_query_count": 1,
            "requested_by": "integration",
            "review_note": "replay-alert release audit lineage",
        },
    )
    assert release_response.status_code == 200
    release_id = UUID(release_response.json()["release_id"])

    with postgres_integration_harness.session_factory() as session:
        training_run = session.get(RetrievalTrainingRun, training_run_id)
        assert training_run is not None
        training_run.search_harness_evaluation_id = evaluation_id
        training_run.search_harness_release_id = release_id
        candidate_id = uuid4()
        candidate = RetrievalLearningCandidateEvaluation(
            id=candidate_id,
            retrieval_training_run_id=training_run_id,
            judgment_set_id=training_run.judgment_set_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            training_dataset_sha256=training_run.training_dataset_sha256,
            training_example_count=training_run.example_count,
            positive_count=training_run.positive_count,
            negative_count=training_run.negative_count,
            missing_count=training_run.missing_count,
            hard_negative_count=training_run.hard_negative_count,
            baseline_harness_name="default_v1",
            candidate_harness_name="candidate_v2",
            source_types_json=["claim_support_replay_alert_corpus"],
            limit=5,
            status="completed",
            gate_outcome="passed",
            thresholds_json={"max_total_regressed_count": 0},
            metrics_json={"total_shared_query_count": 1},
            reasons_json=[],
            evaluation_snapshot_json={"evaluation_id": str(evaluation_id)},
            release_snapshot_json=release_response.json(),
            details_json={"fixture": "replay-alert release lineage"},
            learning_package_sha256="learning-package-sha",
            created_by="integration",
            review_note="replay-alert release audit lineage",
            created_at=now,
            completed_at=now,
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
            search_harness_release_id=release_id,
            event_payload={
                "retrieval_learning_candidate_evaluation": {
                    "candidate_evaluation_id": str(candidate_id),
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": training_run.training_dataset_sha256,
                    "learning_package_sha256": "learning-package-sha",
                }
            },
            deduplication_key=f"release-audit-learning-candidate:{candidate_id}",
            created_by="integration",
        )
        candidate.semantic_governance_event_id = event.id
        session.commit()

    original_training_audit_response = postgres_integration_harness.client.post(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert original_training_audit_response.status_code == 200
    original_training_audit_bundle = original_training_audit_response.json()
    assert (
        original_training_audit_bundle["bundle"]["payload"][
            "claim_support_replay_alert_corpus_integrity"
        ]["complete"]
        is True
    )
    original_receipt_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{original_training_audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert original_receipt_response.status_code == 200
    assert original_receipt_response.json()["validation_status"] == "passed"

    with postgres_integration_harness.session_factory() as session:
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot_id)
            .limit(1)
        )
        assert row is not None
        row.fixture_json = {
            **row.fixture_json,
            "description": "tampered after a signed training bundle was created",
        }
        row.fixture_sha256 = payload_sha256(row.fixture_json)
        session.commit()

    release_audit_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert release_audit_response.status_code == 200
    release_audit_bundle = release_audit_response.json()
    release_payload = release_audit_bundle["bundle"]["payload"]
    assert release_payload["audit_checklist"]["complete"] is False
    assert (
        release_payload["audit_checklist"]["training_audit_bundle_corpus_lineage_complete"] is False
    )
    assert release_payload["integrity"]["training_audit_bundle_corpus_lineage_complete"] is False
    training_bundle_ref = release_payload["retrieval_training_audit_bundles"][0]
    assert training_bundle_ref["bundle_id"] != original_training_audit_bundle["bundle_id"]
    assert (
        training_bundle_ref["payload_claim_support_replay_alert_corpus_lineage_complete"] is False
    )
    assert (
        training_bundle_ref["payload_claim_support_replay_alert_corpus_source_reference_count"] > 0
    )
    match_check = release_payload["integrity"]["training_audit_bundle_match_checks"][0]
    assert match_check["hashes_match_training_run"] is True
    assert match_check["claim_support_replay_alert_corpus_lineage_required"] is True
    assert match_check["claim_support_replay_alert_corpus_lineage_complete"] is False
    assert match_check["claim_support_replay_alert_corpus_lineage_bundle_complete"] is False
    assert match_check["claim_support_replay_alert_corpus_lineage_current_complete"] is False
    assert match_check["claim_support_replay_alert_corpus_source_reference_counts_match"] is True
    assert (
        training_bundle_ref["payload_claim_support_replay_alert_corpus_source_reference_count"]
        == match_check["claim_support_replay_alert_corpus_source_reference_count"]
    )
    training_receipt_ref = release_payload["retrieval_training_audit_bundle_validation_receipts"][0]
    assert training_receipt_ref["validation_status"] == "failed"

    latest_release_receipt_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{release_audit_bundle['bundle_id']}/validation-receipts/latest"
    )
    assert latest_release_receipt_response.status_code == 200
    latest_release_receipt = latest_release_receipt_response.json()
    assert latest_release_receipt["validation_status"] == "failed"
    assert any(
        error["code"] == "training_bundle_corpus_lineage_incomplete"
        for error in latest_release_receipt["validation_errors"]
    )
    readiness_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["ready"] is False
    assert readiness["blockers"] == ["validation_receipts_ready"]
    assert readiness["checks"]["validation_receipts_ready"] is False
    assert len(readiness["blocker_details"]) == 1
    blocker_detail = readiness["blocker_details"][0]
    assert blocker_detail["blocker"] == "validation_receipts_ready"
    assert blocker_detail["reasons"] == [
        "release_validation_receipt_failed",
        "payload_schema_invalid",
    ]
    assert blocker_detail["validation_error_codes"] == [
        "audit_checklist_incomplete",
        "training_bundle_corpus_lineage_incomplete",
    ]
    assert blocker_detail["audit_checklist_failed"] == [
        "training_audit_bundle_corpus_lineage_complete",
        "training_audit_bundle_validation_receipts_complete",
    ]
    assert blocker_detail["lineage_remediation_required"] is True
    assert readiness["validation_receipts"]["release_validation_receipt_passed"] is False
    assert readiness["validation_receipts"]["validation_error_codes"] == [
        "audit_checklist_incomplete",
        "training_bundle_corpus_lineage_incomplete",
    ]
    diagnostics = readiness["diagnostics"]
    assert diagnostics["release_audit_bundle_id"] == release_audit_bundle["bundle_id"]
    assert diagnostics["release_validation_receipt_id"] == latest_release_receipt["receipt_id"]
    assert diagnostics["release_validation_status"] == "failed"
    assert diagnostics["validation_error_codes"] == [
        "audit_checklist_incomplete",
        "training_bundle_corpus_lineage_incomplete",
    ]
    assert (
        "training_audit_bundle_corpus_lineage_complete" in (diagnostics["audit_checklist_failed"])
    )
    diagnostic_match_check = diagnostics["training_audit_bundle_match_checks"][0]
    assert diagnostic_match_check["retrieval_training_run_id"] == str(training_run_id)
    assert diagnostic_match_check["claim_support_replay_alert_corpus_lineage_complete"] is False
    remediation = readiness["lineage_remediation"]
    assert remediation["status"] == "action_required"
    assert remediation["action_required"] is True
    assert remediation["affected_training_run_count"] == 1
    remediation_item = remediation["replay_alert_corpus"]["items"][0]
    assert remediation_item["retrieval_training_run_id"] == str(training_run_id)
    assert remediation_item["training_audit_bundle_id"] == training_bundle_ref["bundle_id"]
    assert remediation_item["bundle_lineage_complete"] is False
    assert remediation_item["current_lineage_complete"] is False
    assert remediation_item["source_reference_counts_match"] is True
    assert remediation_item["failure_reasons"] == [
        "training_bundle_lineage_incomplete",
        "current_corpus_lineage_incomplete",
    ]
    assert "recreate the release audit bundle" in (remediation_item["suggested_operator_action"])

    assessment_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/readiness-assessments",
        json={"created_by": "integration", "review_note": "freeze blocked readiness"},
    )
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    assert assessment["schema_version"] == "1.1"
    assert assessment["readiness_status"] == "blocked"
    assert assessment["ready"] is False
    assert assessment["blockers"] == ["validation_receipts_ready"]
    assert assessment["latest_release_audit_bundle_id"] == (release_audit_bundle["bundle_id"])
    assert (
        assessment["latest_release_validation_receipt_id"] == (latest_release_receipt["receipt_id"])
    )
    assert assessment["blocker_details"][0]["lineage_remediation_required"] is True
    assert assessment["lineage_remediation"]["status"] == "action_required"
    assert assessment["readiness"]["ready"] is False
    assert assessment["readiness"]["latest_readiness_assessment"] is None
    assert assessment["semantic_governance_event_id"]
    assert assessment["integrity"]["complete"] is True
    assert assessment["integrity"]["readiness_payload_hash_matches"] is True
    assert assessment["integrity"]["assessment_payload_hash_matches"] is True
    assert assessment["integrity"]["assessment_payload_embeds_readiness_hash"] is True
    assert assessment["integrity"]["readiness_status_matches"] is True

    latest_assessment_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness-assessments/latest"
    )
    assert latest_assessment_response.status_code == 200
    assert latest_assessment_response.json()["assessment_id"] == (assessment["assessment_id"])
    assert latest_assessment_response.json()["integrity"]["complete"] is True

    readiness_after_assessment_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_after_assessment_response.status_code == 200
    readiness_after_assessment = readiness_after_assessment_response.json()
    assert readiness_after_assessment["latest_readiness_assessment"]["ready"] is False
    assert (
        readiness_after_assessment["latest_readiness_assessment"]["assessment_id"]
        == (assessment["assessment_id"])
    )

    with postgres_integration_harness.session_factory() as session:
        refreshed_training_bundle = session.get(
            AuditBundleExport,
            UUID(training_bundle_ref["bundle_id"]),
        )
        assert refreshed_training_bundle is not None
        refreshed_payload = refreshed_training_bundle.bundle_payload_json["payload"]
        refreshed_integrity = refreshed_payload["claim_support_replay_alert_corpus_integrity"]
        assert refreshed_integrity["complete"] is False
        assert refreshed_integrity["reference_row_identity_hashes_match"] is False
        assert refreshed_integrity["row_fixture_hashes_match"] is True
        assessment_row = session.get(
            SearchHarnessReleaseReadinessAssessment,
            UUID(assessment["assessment_id"]),
        )
        assert assessment_row is not None
        assert assessment_row.ready is False
        assert assessment_row.release_audit_bundle_id == UUID(release_audit_bundle["bundle_id"])
        assert assessment_row.release_validation_receipt_id == UUID(
            latest_release_receipt["receipt_id"]
        )
        event = session.get(
            SemanticGovernanceEvent,
            assessment_row.semantic_governance_event_id,
        )
        assert event is not None
        assert event.event_kind == "search_harness_release_readiness_assessed"
        assert event.search_harness_release_id == release_id


def test_materialize_retrieval_learning_dataset_rejects_tampered_replay_alert_corpus(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-tampered",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        )
    ]

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .limit(1)
        )
        assert row is not None
        row.fixture_sha256 = "tampered-fixture-hash"
        session.flush()

        with pytest.raises(ValueError, match="snapshot governance is incomplete"):
            materialize_retrieval_learning_dataset(
                session,
                limit=10,
                source_types=["claim_support_replay_alert_corpus"],
                set_name="tampered-replay-alert-corpus-learning",
                created_by="integration",
            )
        session.rollback()


def test_materialize_retrieval_learning_dataset_rejects_unusable_replay_alert_result(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    fixture = _claim_support_learning_fixture(
        case_id="replay-alert-missing-object-id",
        expected_verdict="unsupported",
        hard_case_kind="policy_change_unsupported",
        rendered_text="The policy exception is not supported by the cited record.",
        evidence_excerpt="The cited record discusses a different policy.",
    )
    fixture["draft_payload"]["evidence_cards"][0].pop("chunk_id")
    fixtures = [fixture]

    with postgres_integration_harness.session_factory() as session:
        _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )

        with pytest.raises(ValueError, match="evidence_object_id_missing"):
            materialize_retrieval_learning_dataset(
                session,
                limit=10,
                source_types=["claim_support_replay_alert_corpus"],
                set_name="invalid-replay-alert-corpus-result-learning",
                created_by="integration",
            )
        session.rollback()


def test_materialize_retrieval_learning_dataset_rechecks_promotion_artifact_integrity(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-artifact-tampered",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        )
    ]

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .limit(1)
        )
        assert row is not None
        artifact = session.get(AgentTaskArtifact, row.promotion_artifact_id)
        assert artifact is not None
        artifact.payload_json = {
            **artifact.payload_json,
            "candidate_count": 999,
        }
        session.flush()

        with pytest.raises(ValueError, match="promotion_artifact_hash_mismatch"):
            materialize_retrieval_learning_dataset(
                session,
                limit=10,
                source_types=["claim_support_replay_alert_corpus"],
                set_name="tampered-promotion-artifact-learning",
                created_by="integration",
            )
        session.rollback()
