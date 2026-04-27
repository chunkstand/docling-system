from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.agent_tasks import ContextFreshnessStatus, ContextRef
from app.services.technical_reports import (
    build_report_evidence_cards,
    draft_technical_report,
    plan_technical_report,
    prepare_report_agent_harness,
    verify_technical_report,
)


def _semantic_brief_payload() -> dict:
    document_id = uuid4()
    run_id = uuid4()
    semantic_pass_id = uuid4()
    assertion_id = uuid4()
    evidence_id = uuid4()
    fact_id = uuid4()
    graph_snapshot_id = uuid4()
    graph_edge_id = "edge:concept:integration_threshold:concept:change_window"
    return {
        "document_kind": "knowledge_brief",
        "title": "Integration Governance Technical Report",
        "goal": "Explain the integration governance controls.",
        "audience": "Operators",
        "review_policy": "allow_candidate_with_disclosure",
        "target_length": "medium",
        "document_refs": [
            {
                "document_id": document_id,
                "run_id": run_id,
                "semantic_pass_id": semantic_pass_id,
                "source_filename": "integration.pdf",
                "title": "Integration Report",
                "registry_version": "semantics-layer-foundation-alpha.3",
                "registry_sha256": "registry-sha",
                "evaluation_fixture_name": "integration",
                "evaluation_status": "completed",
                "assertion_count": 1,
                "evidence_count": 1,
                "all_expectations_passed": True,
            }
        ],
        "required_concept_keys": ["integration_threshold", "change_window"],
        "selected_concept_keys": ["integration_threshold", "change_window"],
        "selected_category_keys": ["integration_governance"],
        "semantic_dossier": [
            {
                "concept_key": "integration_threshold",
                "preferred_label": "Integration Threshold",
                "category_keys": ["integration_governance"],
                "category_labels": {"integration_governance": "Integration Governance"},
                "document_ids": [document_id],
                "document_count": 1,
                "evidence_count": 1,
                "source_types": ["table"],
                "support_level": "supported",
                "review_policy_status": "candidate_disclosed",
                "disclosure_note": "This claim includes candidate semantic support.",
                "facts": [
                    {
                        "fact_id": fact_id,
                        "document_id": document_id,
                        "run_id": run_id,
                        "semantic_pass_id": semantic_pass_id,
                        "relation_key": "document_mentions_concept",
                        "relation_label": "mentions",
                        "subject_entity_key": f"document:{document_id}",
                        "subject_label": "Integration Report",
                        "object_entity_key": "concept:integration_threshold",
                        "object_label": "Integration Threshold",
                        "object_value_text": None,
                        "review_status": "candidate",
                        "assertion_id": assertion_id,
                        "evidence_ids": [evidence_id],
                    }
                ],
                "assertions": [
                    {
                        "document_id": document_id,
                        "run_id": run_id,
                        "semantic_pass_id": semantic_pass_id,
                        "assertion_id": assertion_id,
                        "concept_key": "integration_threshold",
                        "preferred_label": "Integration Threshold",
                        "review_status": "candidate",
                        "support_level": "supported",
                        "source_types": ["table"],
                        "evidence_count": 1,
                        "category_keys": ["integration_governance"],
                        "category_labels": ["Integration Governance"],
                    }
                ],
                "evidence_refs": [],
            }
        ],
        "graph_index": [
            {
                "edge_id": graph_edge_id,
                "graph_snapshot_id": graph_snapshot_id,
                "graph_version": "graph-v1",
                "relation_key": "concept_depends_on_concept",
                "relation_label": "Depends On",
                "subject_entity_key": "concept:integration_threshold",
                "subject_label": "Integration Threshold",
                "object_entity_key": "concept:change_window",
                "object_label": "Change Window",
                "review_status": "approved",
                "support_level": "supported",
                "extractor_score": 0.87,
                "supporting_document_ids": [document_id],
                "support_ref_ids": [str(evidence_id)],
            }
        ],
        "graph_summary": {"approved_edge_count": 1},
        "sections": [
            {
                "section_id": "section:integration_governance",
                "title": "Integration Governance",
                "summary": "Covers integration controls.",
                "focus_concept_keys": ["integration_threshold"],
                "focus_category_keys": ["integration_governance"],
                "claim_ids": ["claim:integration_threshold"],
            },
            {
                "section_id": "section:cross_document_relationships",
                "title": "Cross-Document Relationships",
                "summary": "Captures approved graph links.",
                "focus_concept_keys": ["integration_threshold", "change_window"],
                "focus_category_keys": [],
                "claim_ids": [f"claim:{graph_edge_id}"],
            },
        ],
        "claim_candidates": [
            {
                "claim_id": "claim:integration_threshold",
                "section_id": "section:integration_governance",
                "summary": "Integration thresholds govern release decisions.",
                "concept_keys": ["integration_threshold"],
                "graph_edge_ids": [],
                "fact_ids": [fact_id],
                "assertion_ids": [assertion_id],
                "evidence_labels": ["E1"],
                "source_document_ids": [document_id],
                "support_level": "supported",
                "review_policy_status": "candidate_disclosed",
                "disclosure_note": "This claim includes candidate semantic support.",
            },
            {
                "claim_id": f"claim:{graph_edge_id}",
                "section_id": "section:cross_document_relationships",
                "summary": "Integration thresholds depend on change windows.",
                "concept_keys": ["integration_threshold", "change_window"],
                "graph_edge_ids": [graph_edge_id],
                "fact_ids": [],
                "assertion_ids": [],
                "evidence_labels": [],
                "source_document_ids": [document_id],
                "support_level": "supported",
                "review_policy_status": "approved_graph",
                "disclosure_note": None,
            },
        ],
        "evidence_pack": [
            {
                "citation_label": "E1",
                "document_id": document_id,
                "run_id": run_id,
                "semantic_pass_id": semantic_pass_id,
                "assertion_id": assertion_id,
                "evidence_id": evidence_id,
                "concept_key": "integration_threshold",
                "preferred_label": "Integration Threshold",
                "review_status": "candidate",
                "source_filename": "integration.pdf",
                "source_type": "table",
                "page_from": 1,
                "page_to": 1,
                "excerpt": "Tier | Integration Threshold",
                "source_artifact_api_path": "/documents/example/tables/1",
                "matched_terms": ["integration threshold"],
            }
        ],
        "shadow_mode": False,
        "shadow_candidate_extractor_name": None,
        "shadow_candidate_summary": {},
        "shadow_candidates": [],
        "warnings": [],
        "success_metrics": [],
    }


def _plan_from_semantic_brief(monkeypatch, semantic_brief: dict) -> dict:
    monkeypatch.setattr(
        "app.services.technical_reports.prepare_semantic_generation_brief",
        lambda *args, **kwargs: semantic_brief,
    )
    return plan_technical_report(
        object(),
        title="Integration Governance Technical Report",
        goal="Explain the integration governance controls.",
        audience="Operators",
        document_ids=[semantic_brief["document_refs"][0]["document_id"]],
        concept_keys=[],
        category_keys=[],
        target_length="medium",
        review_policy="allow_candidate_with_disclosure",
    )


def _fresh_context_ref(task_id=None) -> ContextRef:
    now = datetime.now(UTC)
    return ContextRef(
        ref_key="evidence_cards_task_output",
        ref_kind="task_output",
        summary="test context",
        task_id=task_id or uuid4(),
        schema_name="build_report_evidence_cards_output",
        schema_version="1.0",
        observed_sha256="sha",
        source_updated_at=now,
        checked_at=now,
        freshness_status=ContextFreshnessStatus.FRESH,
    )


def _draft_from_semantic_brief(monkeypatch, semantic_brief: dict) -> dict:
    plan = _plan_from_semantic_brief(monkeypatch, semantic_brief)
    evidence_bundle = build_report_evidence_cards(plan, plan_task_id=uuid4())
    context_ref = _fresh_context_ref()
    harness = prepare_report_agent_harness(
        evidence_bundle,
        harness_task_id=uuid4(),
        evidence_task_id=context_ref.task_id,
        upstream_context_refs=[context_ref],
    )
    return draft_technical_report(harness, harness_task_id=uuid4())


def test_report_harness_service_roundtrip(monkeypatch) -> None:
    semantic_brief = _semantic_brief_payload()
    plan = _plan_from_semantic_brief(monkeypatch, semantic_brief)
    plan_task_id = uuid4()
    evidence_bundle = build_report_evidence_cards(plan, plan_task_id=plan_task_id)
    assert any(card["source_type"] == "table" for card in evidence_bundle["evidence_cards"])

    context_ref = _fresh_context_ref()
    harness = prepare_report_agent_harness(
        evidence_bundle,
        harness_task_id=uuid4(),
        evidence_task_id=context_ref.task_id,
        upstream_context_refs=[context_ref],
    )
    assert harness["allowed_tools"][0]["tool_name"] == "read_task_context"
    assert "technical_report_planning" in {
        skill["skill_name"] for skill in harness["required_skills"]
    }
    assert harness["llm_adapter_contract"]["harness_context_refs"][0]["freshness_status"] == "fresh"

    draft = draft_technical_report(harness, harness_task_id=uuid4())
    assert draft["claims"][0]["evidence_card_ids"]
    assert draft["evidence_package_sha256"]
    assert draft["claims"][0]["evidence_package_sha256"] == draft["evidence_package_sha256"]
    assert draft["claims"][0]["derivation_sha256"]
    assert draft["claim_derivations"][0]["derivation_rule"] == "technical_report_claim_contract_v1"
    assert "Evidence Cards" in draft["markdown"]

    verification = verify_technical_report(draft)
    assert verification.verification_outcome == "passed"
    assert verification.summary["context_ref_count"] == 1
    assert verification.summary["missing_derivation_hash_count"] == 0
    assert any(metric["stakeholder"] == "Joshua Yu" for metric in verification.success_metrics)
    assert any(
        metric["metric_key"] == "frozen_evidence_package"
        for metric in verification.success_metrics
    )


def test_fact_backed_claims_bind_to_source_evidence_without_label(monkeypatch) -> None:
    semantic_brief = _semantic_brief_payload()
    semantic_brief["claim_candidates"][0]["evidence_labels"] = []

    draft = _draft_from_semantic_brief(monkeypatch, semantic_brief)
    fact_backed_claim = next(
        claim for claim in draft["claims"] if claim["claim_id"] == "claim:integration_threshold"
    )

    assert fact_backed_claim["evidence_card_ids"]
    verification = verify_technical_report(draft)
    assert verification.verification_outcome == "passed"


def test_harness_marks_missing_wake_context_blocked(monkeypatch) -> None:
    plan = _plan_from_semantic_brief(monkeypatch, _semantic_brief_payload())
    evidence_bundle = build_report_evidence_cards(plan, plan_task_id=uuid4())

    harness = prepare_report_agent_harness(
        evidence_bundle,
        harness_task_id=uuid4(),
        evidence_task_id=uuid4(),
        upstream_context_refs=[],
    )

    assert harness["workflow_state"]["blocked_steps"]
    wake_metric = next(
        metric
        for metric in harness["success_metrics"]
        if metric["metric_key"] == "wake_up_packet_complete"
    )
    assert wake_metric["passed"] is False


def test_verification_fails_without_wake_context(monkeypatch) -> None:
    draft = _draft_from_semantic_brief(monkeypatch, _semantic_brief_payload())
    draft["llm_adapter_contract"]["harness_context_refs"] = []

    verification = verify_technical_report(draft)

    assert verification.verification_outcome == "failed"
    assert verification.summary["missing_wake_context_count"] == 1
    assert any("wake-up context refs" in reason for reason in verification.verification_reasons)


def test_verification_fails_unresolved_evidence_card_refs(monkeypatch) -> None:
    draft = _draft_from_semantic_brief(monkeypatch, _semantic_brief_payload())
    draft["claims"][0]["evidence_card_ids"] = ["missing-card"]

    verification = verify_technical_report(draft)

    assert verification.verification_outcome == "failed"
    assert verification.summary["unresolved_evidence_card_ref_count"] == 1
    assert any("missing evidence cards" in reason for reason in verification.verification_reasons)
