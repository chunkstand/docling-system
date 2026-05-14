from __future__ import annotations

import os

import pytest

from tests.integration.retrieval_learning_ledger_support import (
    UTC,
    UUID,
    AgentTask,
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
    SearchRequestResultSpan,
    SimpleNamespace,
    TechnicalReportClaimRetrievalFeedback,
    _claim_support_learning_fixture,
    _make_result,
    _make_search_request,
    _seed_governed_claim_support_replay_alert_corpus,
    datetime,
    materialize_retrieval_learning_dataset,
    payload_sha256,
    select,
    uuid4,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_materialize_retrieval_learning_dataset_from_governed_replay_alert_corpus(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-supported",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        ),
        _claim_support_learning_fixture(
            case_id="replay-alert-unsupported",
            expected_verdict="unsupported",
            hard_case_kind="policy_change_unsupported",
            rendered_text="The policy exception is not supported by the cited record.",
            evidence_excerpt="The cited record discusses a different policy.",
        ),
        _claim_support_learning_fixture(
            case_id="replay-alert-insufficient",
            expected_verdict="insufficient_evidence",
            hard_case_kind="policy_change_insufficient_evidence",
            rendered_text="The policy exception lacks traceable source support.",
            evidence_excerpt="The cited record does not resolve the policy exception.",
        ),
    ]
    expected_chunk_ids = {
        fixture["draft_payload"]["evidence_cards"][0]["chunk_id"]
        for fixture in fixtures
        if fixture["expected_verdict"] in {"supported", "unsupported"}
    }
    source_search_result_ids = {
        fixture["draft_payload"]["evidence_cards"][0]["source_search_request_result_ids"][0]
        for fixture in fixtures
        if fixture["draft_payload"]["evidence_cards"]
    }

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        snapshot_id = str(snapshot.id)
        snapshot_sha256 = snapshot.snapshot_sha256
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["claim_support_replay_alert_corpus"],
            set_name="integration-replay-alert-corpus-learning",
            created_by="integration",
        )
        training_run_id = response["retrieval_training_run_id"]
        judgment_set_id = UUID(response["judgment_set_id"])
        session.commit()

    assert response["summary"]["source_types"] == ["claim_support_replay_alert_corpus"]
    assert response["summary"]["judgment_count"] == 3
    assert response["summary"]["positive_count"] == 1
    assert response["summary"]["negative_count"] == 1
    assert response["summary"]["missing_count"] == 1
    assert response["summary"]["hard_negative_count"] == 1
    assert response["summary"]["training_example_count"] == 4
    assert response["summary"]["judgment_counts_by_source_type"] == {
        "claim_support_replay_alert_corpus": 3
    }

    with postgres_integration_harness.session_factory() as session:
        judgment_set = session.get(RetrievalJudgmentSet, judgment_set_id)
        judgments = list(
            session.scalars(
                select(RetrievalJudgment)
                .where(RetrievalJudgment.judgment_set_id == judgment_set_id)
                .order_by(RetrievalJudgment.deduplication_key.asc())
            )
        )
        hard_negatives = list(
            session.scalars(
                select(RetrievalHardNegative)
                .where(RetrievalHardNegative.judgment_set_id == judgment_set_id)
                .order_by(RetrievalHardNegative.deduplication_key.asc())
            )
        )
        training_run = session.get(RetrievalTrainingRun, UUID(training_run_id))

    assert judgment_set is not None
    assert judgment_set.set_kind == "claim_support_replay_alert_corpus"
    assert judgment_set.source_types_json == ["claim_support_replay_alert_corpus"]
    assert (
        judgment_set.criteria_json["claim_support_replay_alert_corpus"][
            "snapshot_governance_required"
        ]
        is True
    )
    assert training_run is not None
    assert training_run.training_payload_json["judgment_set"]["criteria"][
        "claim_support_replay_alert_corpus"
    ]["row_lineage_required"] == [
        "fixture_expected_verdict",
        "fixture_hard_case_kind",
        "fixture_sha256",
        "promotion_event",
        "promotion_artifact",
        "source_change_impact_ids",
        "source_escalation_events",
    ]
    assert {row.source_type for row in judgments} == {"claim_support_replay_alert_corpus"}
    assert {row.judgment_kind for row in judgments} == {
        "positive",
        "negative",
        "missing",
    }
    assert {str(row.result_id) for row in judgments if row.result_id} == expected_chunk_ids
    assert all(row.result_id is None for row in judgments if row.judgment_kind == "missing")
    assert all(row.evidence_refs_json for row in judgments)
    assert not {
        str(row.result_id)
        for row in judgments
        if row.result_id and str(row.result_id) in source_search_result_ids
    }
    assert all(row.search_request_id is None for row in judgments)
    assert all(row.search_request_result_id is None for row in judgments)
    assert all(row.source_payload_sha256 for row in judgments)
    assert len(hard_negatives) == 1
    assert hard_negatives[0].source_type == "claim_support_replay_alert_corpus"
    assert hard_negatives[0].hard_negative_kind == "explicit_irrelevant"
    assert hard_negatives[0].source_payload_sha256
    source_details = judgments[0].payload_json["source_details"]
    assert source_details["snapshot"]["snapshot_id"] == snapshot_id
    assert source_details["snapshot"]["snapshot_sha256"] == snapshot_sha256
    assert source_details["snapshot"]["governance_integrity"]["complete"] is True
    assert source_details["row"]["source_change_impact_ids"]
    assert source_details["row"]["source_escalation_event_ids"]
    assert source_details["row"]["promotion_event_id"]
    assert source_details["row"]["promotion_artifact_id"]

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
    assert audit_payload["audit_checklist"]["complete"] is True
    assert audit_payload["integrity"]["judgment_count"] == 3
    assert audit_payload["integrity"]["hard_negative_count"] == 1
    assert audit_payload["integrity"]["claim_support_replay_alert_corpus_lineage_complete"] is True
    assert (
        audit_payload["audit_checklist"]["claim_support_replay_alert_corpus_lineage_complete"]
        is True
    )
    assert {row["source_type"] for row in audit_payload["retrieval_judgments"]} == {
        "claim_support_replay_alert_corpus"
    }
    assert all(
        row["payload"]["source_details"]["snapshot"]["snapshot_sha256"] == snapshot_sha256
        for row in audit_payload["retrieval_judgments"]
    )
    assert len(audit_payload["claim_support_replay_alert_corpus_source_references"]) == 4
    assert len(audit_payload["claim_support_replay_alert_corpus_snapshots"]) == 1
    assert len(audit_payload["claim_support_replay_alert_corpus_rows"]) == 3
    assert len(audit_payload["claim_support_replay_alert_promotion_artifacts"]) == 1
    assert len(audit_payload["claim_support_replay_alert_promotion_events"]) == 1
    assert len(audit_payload["claim_support_replay_alert_escalation_events"]) == 3
    assert len(audit_payload["claim_support_replay_alert_snapshot_governance_artifacts"]) == 1
    assert len(audit_payload["claim_support_replay_alert_snapshot_governance_events"]) == 1
    corpus_integrity = audit_payload["claim_support_replay_alert_corpus_integrity"]
    assert corpus_integrity["complete"] is True
    assert corpus_integrity["row_fixture_hashes_match"] is True
    assert corpus_integrity["snapshot_hashes_match"] is True
    assert corpus_integrity["promotion_artifact_hashes_match"] is True
    assert corpus_integrity["snapshot_artifact_hashes_match"] is True
    assert any(
        value.get("prov:type") == "docling:ClaimSupportReplayAlertFixtureCorpusRow"
        for value in audit_payload["prov"]["entity"].values()
    )
    assert any(
        edge["usedEntity"].startswith("docling:claim_support_replay_alert_corpus_row:")
        for edge in audit_payload["prov"]["wasDerivedFrom"]
    )
    assert audit_payload["source_payload_hashes"]
    receipt_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert receipt_response.status_code == 200
    receipt_payload = receipt_response.json()
    assert receipt_payload["validation_status"] == "passed"
    assert receipt_payload["semantic_governance_valid"] is True


def test_materialize_retrieval_learning_dataset_from_claim_feedback_ledger(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    verification_task_id = uuid4()

    with postgres_integration_harness.session_factory() as session:
        request = _make_search_request(now=now)
        result = _make_result(request_id=request.id, rank=1, result_type="chunk", now=now)
        span = SearchRequestResultSpan(
            id=uuid4(),
            search_request_id=request.id,
            search_request_result_id=result.id,
            retrieval_evidence_span_id=None,
            span_rank=1,
            score_kind="lexical",
            score=0.93,
            source_type="chunk",
            source_id=result.chunk_id,
            span_index=0,
            page_from=1,
            page_to=1,
            text_excerpt="The cited result does not support the generated claim.",
            content_sha256="claim-feedback-span-sha",
            source_snapshot_sha256="claim-feedback-source-sha",
            metadata_json={"fixture": "technical_report_claim_feedback"},
            created_at=now,
        )
        verification_task = AgentTask(
            id=verification_task_id,
            task_type="verify_technical_report",
            status="completed",
            input_json={},
            result_json={},
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
        source_payload = {
            "schema_name": "technical_report_claim_retrieval_feedback_source",
            "schema_version": "1.0",
            "technical_report_verification_task_id": str(verification_task_id),
            "claim_id": "claim:unsupported",
            "claim_text": "The generated claim overstates the cited evidence.",
            "support_verdict": "unsupported",
            "support_score": 0.12,
            "feedback_status": "rejected",
            "learning_label": "negative",
            "hard_negative_kind": "explicit_irrelevant",
            "source_search_request_ids": [str(request.id)],
            "source_search_request_result_ids": [str(result.id)],
            "search_request_result_span_ids": [str(span.id)],
            "retrieval_evidence_span_ids": [],
        }
        source_payload_sha256 = str(payload_sha256(source_payload))
        feedback_payload = {
            "schema_name": "technical_report_claim_retrieval_feedback",
            "schema_version": "1.0",
            "feedback_kind": "generation_claim_retrieval_feedback",
            "technical_report_verification_task_id": str(verification_task_id),
            "claim_id": "claim:unsupported",
            "feedback_status": "rejected",
            "learning_label": "negative",
            "hard_negative_kind": "explicit_irrelevant",
            "source_payload_sha256": source_payload_sha256,
            "source": source_payload,
        }
        feedback = TechnicalReportClaimRetrievalFeedback(
            id=uuid4(),
            technical_report_verification_task_id=verification_task_id,
            claim_id="claim:unsupported",
            claim_text="The generated claim overstates the cited evidence.",
            support_verdict="unsupported",
            support_score=0.12,
            feedback_status="rejected",
            learning_label="negative",
            hard_negative_kind="explicit_irrelevant",
            source_search_request_id=request.id,
            search_request_result_id=result.id,
            source_search_request_ids_json=[str(request.id)],
            source_search_request_result_ids_json=[str(result.id)],
            search_request_result_span_ids_json=[str(span.id)],
            retrieval_evidence_span_ids_json=[],
            semantic_ontology_snapshot_ids_json=[],
            semantic_graph_snapshot_ids_json=[],
            retrieval_reranker_artifact_ids_json=[],
            search_harness_release_ids_json=[],
            release_audit_bundle_ids_json=[],
            release_validation_receipt_ids_json=[],
            evidence_refs_json=[
                {
                    "search_request_result_span_id": str(span.id),
                    "search_request_id": str(request.id),
                    "search_request_result_id": str(result.id),
                    "span_rank": 1,
                    "score_kind": "lexical",
                    "score": 0.93,
                    "source_type": "chunk",
                    "source_id": str(result.chunk_id),
                    "span_index": 0,
                    "page_from": 1,
                    "page_to": 1,
                    "text_excerpt": span.text_excerpt,
                    "content_sha256": span.content_sha256,
                    "source_snapshot_sha256": span.source_snapshot_sha256,
                    "metadata": span.metadata_json,
                }
            ],
            retrieval_context_json={
                "primary_query_text": request.query_text,
                "primary_mode": request.mode,
                "primary_harness_name": request.harness_name,
                "primary_reranker_name": request.reranker_name,
                "primary_reranker_version": request.reranker_version,
                "primary_retrieval_profile_name": request.retrieval_profile_name,
                "primary_harness_config": request.harness_config_json,
            },
            feedback_payload_json=feedback_payload,
            feedback_payload_sha256=str(payload_sha256(feedback_payload)),
            source_payload_json=source_payload,
            source_payload_sha256=source_payload_sha256,
            created_at=now,
            updated_at=now,
        )
        session.add_all([request, result, span, verification_task, feedback])
        session.flush()
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["technical_report_claim_feedback"],
            set_name="integration-claim-feedback-learning",
            created_by="integration",
        )
        judgment_set_id = UUID(response["judgment_set_id"])
        request_id = request.id
        result_id = result.id
        session.commit()

    assert response["summary"]["source_types"] == ["technical_report_claim_feedback"]
    assert response["summary"]["judgment_count"] == 1
    assert response["summary"]["negative_count"] == 1
    assert response["summary"]["hard_negative_count"] == 1
    assert response["summary"]["judgment_counts_by_source_type"] == {
        "technical_report_claim_feedback": 1
    }

    with postgres_integration_harness.session_factory() as session:
        judgment = session.scalar(
            select(RetrievalJudgment).where(RetrievalJudgment.judgment_set_id == judgment_set_id)
        )
        hard_negative = session.scalar(
            select(RetrievalHardNegative).where(
                RetrievalHardNegative.judgment_set_id == judgment_set_id
            )
        )
        training_run = session.scalar(
            select(RetrievalTrainingRun).where(
                RetrievalTrainingRun.judgment_set_id == judgment_set_id
            )
        )

    assert judgment is not None
    assert judgment.source_type == "technical_report_claim_feedback"
    assert judgment.judgment_kind == "negative"
    assert judgment.search_request_id == request_id
    assert judgment.search_request_result_id == result_id
    assert judgment.evidence_refs_json
    assert judgment.payload_json["source_details"]["feedback_status"] == "rejected"
    assert hard_negative is not None
    assert hard_negative.source_type == "technical_report_claim_feedback"
    assert hard_negative.hard_negative_kind == "explicit_irrelevant"
    assert hard_negative.search_request_result_id == result_id
    assert training_run is not None
    assert (
        training_run.training_payload_json["judgment_set"]["criteria"][
            "technical_report_claim_feedback"
        ]["feedback_payload_hash_required"]
        is True
    )
