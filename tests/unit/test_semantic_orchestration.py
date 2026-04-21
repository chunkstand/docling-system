from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.semantics import DocumentSemanticPassResponse
from app.services.semantic_orchestration import (
    build_semantic_success_metrics,
    draft_semantic_registry_update_from_bootstrap_report,
    semantic_registry_verification_summary,
    triage_semantic_pass,
)
from app.services.semantic_registry import semantic_registry_from_payload


def _semantic_pass_response(
    *, assertions=None, evaluation_summary=None
) -> DocumentSemanticPassResponse:
    now = datetime.now(UTC)
    return DocumentSemanticPassResponse(
        semantic_pass_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        status="completed",
        registry_version="semantics-layer-foundation-alpha.2",
        registry_sha256="registry-sha",
        extractor_version="semantics_sidecar_v2_1",
        artifact_schema_version="2.1",
        baseline_run_id=None,
        baseline_semantic_pass_id=None,
        has_json_artifact=True,
        has_yaml_artifact=True,
        artifact_json_sha256="artifact-json-sha",
        artifact_yaml_sha256="artifact-yaml-sha",
        assertion_count=len(assertions or []),
        evidence_count=sum(assertion.evidence_count for assertion in (assertions or [])),
        summary={"concept_keys": [assertion.concept_key for assertion in (assertions or [])]},
        evaluation_status="completed",
        evaluation_fixture_name="semantic_fixture",
        evaluation_version=2,
        evaluation_summary=evaluation_summary
        or {"all_expectations_passed": True, "expectations": []},
        continuity_summary={"reason": "no_prior_active_run", "change_count": 0},
        error_message=None,
        created_at=now,
        completed_at=now,
        concept_category_bindings=[],
        assertions=assertions or [],
    )


def test_build_semantic_success_metrics_marks_core_checks_passed() -> None:
    semantic_pass = _semantic_pass_response()

    metrics = build_semantic_success_metrics(semantic_pass)
    metrics_by_key = {metric["metric_key"]: metric for metric in metrics}

    assert metrics_by_key["semantic_integrity"]["passed"] is True
    assert metrics_by_key["agent_legibility"]["passed"] is True
    assert metrics_by_key["explicit_control_surface"]["passed"] is True
    assert metrics_by_key["owned_context"]["passed"] is True
    assert metrics_by_key["memory_compaction"]["passed"] is True


def test_triage_semantic_pass_emits_missing_concept_issue_and_registry_hint() -> None:
    semantic_pass = _semantic_pass_response(
        evaluation_summary={
            "all_expectations_passed": False,
            "expectations": [
                {
                    "concept_key": "integration_threshold",
                    "minimum_evidence_count": 2,
                    "required_source_types": ["chunk", "table"],
                    "observed_evidence_count": 0,
                    "observed_source_types": [],
                    "missing_source_types": ["chunk", "table"],
                    "expected_category_keys": ["integration_governance"],
                    "observed_category_keys": [],
                    "missing_category_keys": ["integration_governance"],
                    "suggested_aliases": ["integration guardrail"],
                    "passed": False,
                }
            ],
        }
    )

    result = triage_semantic_pass(semantic_pass, low_evidence_threshold=2)

    assert result.recommendation["next_action"] == "draft_registry_update"
    assert result.verification_outcome == "failed"
    assert result.gap_report["issue_count"] == 1
    assert result.gap_report["recommended_followups"][0]["target_task_type"] == (
        "draft_semantic_registry_update"
    )

    issue = result.gap_report["issues"][0]
    assert issue["issue_type"] == "missing_expected_concept"
    assert issue["concept_key"] == "integration_threshold"
    assert issue["registry_update_hints"] == [
        {
            "update_type": "add_alias",
            "concept_key": "integration_threshold",
            "alias_text": "integration guardrail",
            "category_key": None,
            "reason": "Evaluation fixture marked this alias as a missing semantic synonym.",
        }
    ]


def test_draft_semantic_registry_update_from_bootstrap_report_adds_concept(monkeypatch) -> None:
    base_registry_payload = {
        "registry_name": "semantic_registry",
        "registry_version": "semantics-layer-foundation-alpha.2",
        "categories": [],
        "concepts": [
            {
                "concept_key": "integration_threshold",
                "preferred_label": "Integration Threshold",
                "aliases": ["integration threshold"],
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.semantic_orchestration.get_semantic_registry",
        lambda session: semantic_registry_from_payload(base_registry_payload),
    )
    monkeypatch.setattr(
        "app.services.semantic_orchestration.get_active_semantic_ontology_snapshot",
        lambda session: type("Snapshot", (), {"payload_json": base_registry_payload})(),
    )

    draft = draft_semantic_registry_update_from_bootstrap_report(
        object(),
        {
            "input_document_ids": [str(uuid4())],
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": "bootstrap:incident_response_latency",
                    "concept_key": "incident_response_latency",
                    "preferred_label": "Incident Response Latency",
                }
            ],
        },
        source_task_id=uuid4(),
        source_task_type="discover_semantic_bootstrap_candidates",
        proposed_registry_version=None,
        rationale="bootstrap the registry from corpus evidence",
    )

    assert draft["operations"][0]["operation_type"] == "add_concept"
    assert any(
        concept["concept_key"] == "incident_response_latency"
        for concept in draft["effective_registry"]["concepts"]
    )


def test_draft_semantic_registry_update_from_bootstrap_report_preserves_discovered_label(
    monkeypatch,
) -> None:
    base_registry_payload = {
        "registry_name": "semantic_registry",
        "registry_version": "semantics-layer-foundation-alpha.2",
        "categories": [],
        "concepts": [
            {
                "concept_key": "incident_response_latency",
                "preferred_label": "Incident Response Latency",
                "aliases": ["incident response latency"],
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.semantic_orchestration.get_semantic_registry",
        lambda session: semantic_registry_from_payload(base_registry_payload),
    )
    monkeypatch.setattr(
        "app.services.semantic_orchestration.get_active_semantic_ontology_snapshot",
        lambda session: type("Snapshot", (), {"payload_json": base_registry_payload})(),
    )

    draft = draft_semantic_registry_update_from_bootstrap_report(
        object(),
        {
            "input_document_ids": [str(uuid4())],
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": "bootstrap:incident_response_latency_2",
                    "concept_key": "incident_response_latency_2",
                    "preferred_label": "Incident Response Latency",
                }
            ],
        },
        source_task_id=uuid4(),
        source_task_type="discover_semantic_bootstrap_candidates",
        proposed_registry_version=None,
        rationale="bootstrap the registry from corpus evidence",
    )

    assert draft["operations"][0]["preferred_label"] == "Incident Response Latency"
    drafted_concept = next(
        concept
        for concept in draft["effective_registry"]["concepts"]
        if concept["concept_key"] == "incident_response_latency_2"
    )
    assert drafted_concept["preferred_label"] == "Incident Response Latency"


def test_semantic_registry_verification_summary_counts_added_concepts_as_improvement() -> None:
    summary = semantic_registry_verification_summary(
        [
            {
                "document_id": str(uuid4()),
                "run_id": str(uuid4()),
                "evaluation_fixture_name": None,
                "before_all_expectations_passed": False,
                "after_all_expectations_passed": False,
                "before_failed_expectations": 0,
                "after_failed_expectations": 0,
                "before_assertion_count": 0,
                "after_assertion_count": 1,
                "added_concept_keys": ["incident_response_latency"],
                "removed_concept_keys": [],
                "introduced_expected_concepts": [],
                "regressed_expected_concepts": [],
            }
        ]
    )

    assert summary["improved_document_count"] == 1
    assert summary["added_concept_count"] == 1
