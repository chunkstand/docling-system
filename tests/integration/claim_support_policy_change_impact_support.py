from __future__ import annotations

from uuid import UUID, uuid4

from app.core.time import utcnow
from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskStatus,
    AgentTaskVerification,
    KnowledgeOperatorRun,
)
from app.db.public.audit_and_evidence import ClaimEvidenceDerivation, EvidencePackageExport
from app.services.claim_support_policy_governance import (
    CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD,
    claim_support_policy_change_impact_payload_sha256,
)
from app.services.evidence_common import payload_sha256


def _seed_impacted_technical_report_records(session) -> dict[str, UUID | str]:
    now = utcnow()
    harness_task_id = uuid4()
    draft_task_id = uuid4()
    verify_task_id = uuid4()
    support_run_id = uuid4()
    export_id = uuid4()
    draft_artifact_id = uuid4()
    derivation_id = uuid4()
    support_judgment = {
        "schema_name": "technical_report_claim_support_judgment",
        "schema_version": "1.0",
        "judge_kind": "deterministic_v1",
        "claim_id": "claim-impact-1",
        "verdict": "supported",
        "support_score": 0.92,
        "min_support_score": 0.34,
        "evidence_card_ids": ["card-impact-1"],
        "resolved_evidence_card_ids": ["card-impact-1"],
        "graph_edge_ids": [],
        "resolved_graph_edge_ids": [],
        "source_search_request_result_ids": [str(uuid4())],
        "matched_claim_tokens": ["traceable", "evidence"],
        "matched_claim_token_count": 2,
        "claim_token_count": 2,
        "lexical_overlap_ratio": 1.0,
        "support_reasons": ["resolved_evidence_cards"],
        "unsupported_reasons": [],
        "provisional_rule": "integration fixture",
    }
    support_judgment_sha = payload_sha256(support_judgment)
    draft_payload = {
        "schema_name": "draft_technical_report_output",
        "schema_version": "1.0",
        "claims": [
            {
                "claim_id": "claim-impact-1",
                "rendered_text": "A traceable evidence claim.",
                "support_judge_run_id": str(support_run_id),
                "support_judgment_sha256": support_judgment_sha,
                "support_judgment": support_judgment,
            }
        ],
        "claim_support_summary": {
            "support_judge_run_id": str(support_run_id),
            "claims_with_support_judgment_count": 1,
            "supported_claim_count": 1,
        },
    }
    verification_payload = {
        "schema_name": "verify_technical_report_output",
        "schema_version": "1.0",
        "verification_outcome": "passed",
        "summary": {
            "claim_count": 1,
            "claims_with_support_judgment_count": 1,
        },
    }
    session.add_all(
        [
            AgentTask(
                id=harness_task_id,
                task_type="prepare_report_agent_harness",
                status=AgentTaskStatus.COMPLETED.value,
                side_effect_level="read_only",
                input_json={"target_task_id": str(uuid4())},
                result_json={"schema_name": "prepare_report_agent_harness_output"},
                workflow_version="claim_support_policy_impact_fixture",
                created_at=now,
                updated_at=now,
                completed_at=now,
            ),
            AgentTask(
                id=draft_task_id,
                task_type="draft_technical_report",
                status=AgentTaskStatus.COMPLETED.value,
                side_effect_level="draft_change",
                input_json={
                    "target_task_id": str(harness_task_id),
                    "generator_mode": "structured_fallback",
                },
                result_json=draft_payload,
                workflow_version="claim_support_policy_impact_fixture",
                created_at=now,
                updated_at=now,
                completed_at=now,
            ),
            AgentTask(
                id=verify_task_id,
                task_type="verify_technical_report",
                status=AgentTaskStatus.COMPLETED.value,
                side_effect_level="read_only",
                input_json={"target_task_id": str(draft_task_id)},
                result_json=verification_payload,
                workflow_version="claim_support_policy_impact_fixture",
                created_at=now,
                updated_at=now,
                completed_at=now,
            ),
        ]
    )
    session.flush()
    support_output = {
        "schema_name": "technical_report_claim_support_judgments",
        "claim_count": 1,
        "supported_claim_count": 1,
        "claim_judgments": [support_judgment],
    }
    session.add(
        KnowledgeOperatorRun(
            id=support_run_id,
            operator_kind="judge",
            operator_name="technical_report_claim_support_judge",
            operator_version="v1",
            status="completed",
            agent_task_id=draft_task_id,
            output_sha256=payload_sha256(support_output),
            metrics_json={"claim_count": 1, "supported_claim_count": 1},
            metadata_json={"fixture": "claim_support_policy_change_impact"},
            created_at=now,
            started_at=now,
            completed_at=now,
        )
    )
    session.add(
        AgentTaskArtifact(
            id=draft_artifact_id,
            task_id=draft_task_id,
            artifact_kind="technical_report_draft",
            storage_path=f"storage/agent_tasks/{draft_task_id}/technical_report_draft.json",
            payload_json=draft_payload,
            created_at=now,
        )
    )
    session.add(
        EvidencePackageExport(
            id=export_id,
            package_kind="technical_report_claims",
            search_request_id=None,
            agent_task_id=draft_task_id,
            agent_task_artifact_id=draft_artifact_id,
            package_sha256="impact-evidence-package-sha",
            trace_sha256="impact-trace-sha",
            package_payload_json={"claim_ids": ["claim-impact-1"]},
            source_snapshot_sha256s_json=["impact-source-snapshot-sha"],
            operator_run_ids_json=[str(support_run_id)],
            document_ids_json=[],
            run_ids_json=[],
            claim_ids_json=["claim-impact-1"],
            export_status="completed",
            created_at=now,
        )
    )
    session.flush()
    session.add(
        ClaimEvidenceDerivation(
            id=derivation_id,
            evidence_package_export_id=export_id,
            agent_task_id=draft_task_id,
            claim_id="claim-impact-1",
            claim_text="A traceable evidence claim.",
            derivation_rule="integration_fixture_supports_claim",
            evidence_card_ids_json=["card-impact-1"],
            graph_edge_ids_json=[],
            fact_ids_json=[],
            assertion_ids_json=[],
            source_document_ids_json=[],
            source_snapshot_sha256s_json=["impact-source-snapshot-sha"],
            source_search_request_ids_json=[],
            source_search_request_result_ids_json=[],
            source_evidence_package_export_ids_json=[str(export_id)],
            source_evidence_package_sha256s_json=["impact-evidence-package-sha"],
            source_evidence_trace_sha256s_json=["impact-trace-sha"],
            semantic_ontology_snapshot_ids_json=[],
            semantic_graph_snapshot_ids_json=[],
            retrieval_reranker_artifact_ids_json=[],
            search_harness_release_ids_json=[],
            release_audit_bundle_ids_json=[],
            release_validation_receipt_ids_json=[],
            provenance_lock_json={"claim_id": "claim-impact-1"},
            provenance_lock_sha256=payload_sha256({"claim_id": "claim-impact-1"}),
            support_verdict="supported",
            support_score=0.92,
            support_judge_run_id=support_run_id,
            support_judgment_json=support_judgment,
            support_judgment_sha256=support_judgment_sha,
            evidence_package_sha256="impact-evidence-package-sha",
            derivation_sha256="impact-derivation-sha",
            created_at=now,
        )
    )
    session.add(
        AgentTaskVerification(
            id=uuid4(),
            target_task_id=draft_task_id,
            verification_task_id=verify_task_id,
            verifier_type="technical_report_gate",
            outcome="passed",
            metrics_json={"claims_with_support_judgment_count": 1},
            reasons_json=[],
            details_json={"fixture": "claim_support_policy_change_impact"},
            created_at=now,
            completed_at=now,
        )
    )
    session.flush()
    return {
        "harness_task_id": harness_task_id,
        "draft_task_id": draft_task_id,
        "verify_task_id": verify_task_id,
        "support_run_id": support_run_id,
        "derivation_id": derivation_id,
        "support_judgment_sha256": support_judgment_sha,
    }


def _claim_support_change_impact_payload_without_replay(
    *,
    change_impact_id: UUID,
) -> dict:
    payload = {
        "schema_name": "claim_support_policy_change_impact",
        "schema_version": "1.0",
        "change_impact_id": str(change_impact_id),
        "impact_scope": "claim_support_policy:claim_support_judge_calibration_policy",
        "activation": {
            "reason": "no impacted prior support judgments",
        },
        "semantic_basis": {},
        "impact_summary": {
            "affected_support_judgment_count": 0,
            "affected_generated_document_count": 0,
            "affected_technical_report_verification_count": 0,
            "replay_recommended_count": 0,
        },
        "impact_reasons": [],
        "affected_ids": {
            "claim_derivation_ids": [],
            "draft_task_ids": [],
            "verification_task_ids": [],
        },
        "affected_support_judgments": [],
        "affected_generated_documents": {
            "draft_task_ids": [],
            "artifacts": [],
        },
        "affected_technical_report_verifications": [],
        "replay_recommendations": [],
        "integrity_inputs": {},
    }
    return {
        **payload,
        CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD: (
            claim_support_policy_change_impact_payload_sha256(payload)
        ),
    }
