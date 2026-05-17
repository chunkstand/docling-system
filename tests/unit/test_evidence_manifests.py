from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.evidence_manifest_payloads as payload_owner
import app.services.evidence_manifests as evidence_manifests


class _FakeSession:
    def __init__(self, task):
        self._task = task

    def get(self, _model, task_id):
        if self._task is None:
            return None
        return self._task if task_id == self._task.id else None


def _audit_checklist() -> dict[str, object]:
    true_keys = [
        "all_claims_have_provenance_locks",
        "all_claims_have_support_judgments",
        "claim_support_judgment_integrity_verified",
        "all_claims_have_source_search_results",
        "has_claim_retrieval_feedback_ledger",
        "claim_retrieval_feedback_coverage_complete",
        "claim_retrieval_feedback_integrity_verified",
        "has_generation_operator_run",
        "has_support_judge_operator_run",
        "has_verification_operator_run",
        "has_context_pack_artifact",
        "has_context_pack_evaluation_artifact",
        "has_context_pack_verifier_record",
        "has_context_pack_evaluation_operator_run",
        "context_pack_evaluation_passed",
        "context_pack_hash_verified",
        "has_release_readiness_assessments",
        "release_readiness_assessments_cover_source_requests",
        "release_readiness_assessments_ready",
        "release_readiness_assessment_integrity_verified",
        "release_readiness_db_gate_verified",
        "release_readiness_db_gate_complete",
        "release_readiness_db_covers_source_requests",
        "has_persisted_release_readiness_db_gate",
        "persisted_release_readiness_db_gate_integrity_verified",
        "verification_passed",
        "hash_integrity_verified",
        "has_frozen_source_evidence_packages",
        "source_evidence_trace_integrity_verified",
        "generation_evidence_closed",
        "change_impact_clear",
        "replay_alert_waiver_closure_integrity_verified",
        "replay_alert_waiver_lifecycle_clear",
    ]
    checklist: dict[str, object] = {key: True for key in true_keys}
    checklist["active_replay_alert_fixture_corpus_snapshot_id"] = "snapshot-1"
    checklist["active_replay_alert_fixture_corpus_sha256"] = "snapshot-sha"
    checklist["replay_alert_fixture_corpus_snapshot_governed"] = True
    checklist["replay_alert_fixture_corpus_trace_complete"] = True
    checklist["invalid_replay_alert_fixture_corpus_snapshot_governance_count"] = 0
    checklist["incomplete_replay_alert_fixture_corpus_trace_count"] = 0
    return checklist


def _base_audit_bundle():
    task_id = uuid4()
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()
    assertion_id = uuid4()
    fact_id = uuid4()
    evidence_id = uuid4()

    audit_bundle = {
        "task": {"task_id": str(task_id)},
        "draft_task": {"task_id": str(draft_task_id)},
        "verification_task": {"task_id": str(verification_task_id)},
        "draft": {
            "document_refs": [{"document_id": str(document_id), "run_id": str(run_id)}],
            "evidence_cards": [
                {
                    "document_id": str(document_id),
                    "run_id": str(run_id),
                    "assertion_ids": [str(assertion_id)],
                    "fact_ids": [str(fact_id)],
                    "evidence_ids": [str(evidence_id)],
                }
            ],
            "claims": [
                {
                    "claim_id": "claim-1",
                    "source_document_ids": [str(document_id)],
                    "assertion_ids": [str(assertion_id)],
                    "fact_ids": [str(fact_id)],
                    "provenance_lock_sha256": "provenance-lock-sha",
                    "support_verdict": "supported",
                    "support_score": 0.93,
                    "support_judge_run_id": "judge-run-1",
                    "support_judgment_sha256": "support-sha",
                    "source_search_request_result_ids": ["search-result-1"],
                    "source_snapshot_sha256s": ["snapshot-claim"],
                }
            ],
            "graph_context": {"summary": "semantic"},
            "source_snapshot_sha256s": ["snapshot-draft"],
        },
        "evidence_package_exports": [
            {
                "package_kind": "search_request",
                "document_ids": [str(document_id)],
                "run_ids": [str(run_id)],
                "operator_run_ids": ["operator-run-2"],
                "search_request_id": "search-request-1",
                "source_snapshot_sha256s": ["snapshot-export"],
            }
        ],
        "search_evidence_package_traces": [{"trace_id": "trace-1"}],
        "source_evidence_closure": {"complete": True},
        "claim_derivations": [{"claim_id": "claim-1"}],
        "claim_retrieval_feedback": [{"claim_id": "claim-1"}],
        "claim_retrieval_feedback_integrity": {"complete": True},
        "operator_runs": [
            {
                "operator_kind": "retrieve",
                "operator_run_id": "operator-run-1",
                "search_request_id": "search-request-1",
            }
        ],
        "context_pack_audit": {"integrity": {"complete": True}},
        "audit_checklist": _audit_checklist(),
        "integrity": {"complete": True},
        "verification_record": {"outcome": "passed"},
        "change_impact": {"rows": []},
    }
    return {
        "task_id": task_id,
        "verification_task_id": verification_task_id,
        "document_id": document_id,
        "run_id": run_id,
        "audit_bundle": audit_bundle,
    }


def test_manifest_payload_owner_builds_complete_payload(monkeypatch) -> None:
    fixture = _base_audit_bundle()
    session = _FakeSession(SimpleNamespace(id=fixture["task_id"]))

    monkeypatch.setattr(
        payload_owner,
        "_verification_task_id_for_manifest",
        lambda _session, _task: fixture["verification_task_id"],
    )
    monkeypatch.setattr(
        payload_owner,
        "get_agent_task_audit_bundle",
        lambda *_args, **_kwargs: fixture["audit_bundle"],
    )
    monkeypatch.setattr(
        payload_owner,
        "_select_by_ids",
        lambda _session, _model, ids: {value: SimpleNamespace(id=value) for value in ids},
    )
    monkeypatch.setattr(
        payload_owner,
        "_document_payload",
        lambda row: {"document_id": str(row.id), "sha256": "document-sha"},
    )
    monkeypatch.setattr(
        payload_owner,
        "_manifest_run_payload",
        lambda row: {"run_id": str(row.id), "validation_status": "passed"},
    )
    monkeypatch.setattr(
        payload_owner,
        "_semantic_trace_payload",
        lambda *_args, **_kwargs: {
            "assertions": [{"assertion_id": "assertion-1"}],
            "facts": [{"fact_id": "fact-1"}],
            "assertion_evidence": [{"assertion_id": "assertion-1"}],
        },
    )
    monkeypatch.setattr(
        payload_owner,
        "_report_evidence_card_source_records",
        lambda _cards: [{"source": "card"}],
    )
    monkeypatch.setattr(
        payload_owner,
        "_source_record_payloads_from_semantic_trace",
        lambda _session, _assertion_evidence: [{"source": "semantic"}],
    )
    monkeypatch.setattr(
        payload_owner,
        "_technical_report_provenance_edges",
        lambda **_kwargs: [{"edge_type": "derived_from"}],
    )

    payload = payload_owner.build_technical_report_evidence_manifest_payload(
        session,
        fixture["task_id"],
    )

    assert payload["schema_name"] == "technical_report_evidence_manifest"
    assert payload["manifest_kind"] == "technical_report_court_evidence"
    assert payload["document_ids"] == [str(fixture["document_id"])]
    assert payload["run_ids"] == [str(fixture["run_id"])]
    assert payload["claim_ids"] == ["claim-1"]
    assert payload["search_request_ids"] == ["search-request-1"]
    assert set(payload["operator_run_ids"]) == {"operator-run-1", "operator-run-2"}
    assert payload["source_records"] == [{"source": "card"}, {"source": "semantic"}]
    assert payload["retrieval_trace"]["search_evidence_package_trace_summaries"] == [
        {"trace_id": "trace-1"}
    ]
    assert payload["retrieval_trace"]["source_evidence_closure"] == {"complete": True}
    assert payload["report_trace"]["claim_retrieval_feedback_integrity"]["complete"] is True
    assert payload["provenance_edges"] == [{"edge_type": "derived_from"}]
    assert payload["audit_checklist"]["complete"] is True


def test_manifest_payload_owner_missing_task_raises() -> None:
    session = _FakeSession(None)
    task_id = uuid4()

    with pytest.raises(ValueError, match=f"Agent task '{task_id}' was not found."):
        payload_owner.build_technical_report_evidence_manifest_payload(session, task_id)


def test_evidence_manifests_facade_stays_within_budget() -> None:
    with open(evidence_manifests.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 600


def test_manifest_payload_owner_marks_checklist_incomplete_when_gate_missing(monkeypatch) -> None:
    fixture = _base_audit_bundle()
    fixture["audit_bundle"] = deepcopy(fixture["audit_bundle"])
    fixture["audit_bundle"]["audit_checklist"]["verification_passed"] = False
    session = _FakeSession(SimpleNamespace(id=fixture["task_id"]))

    monkeypatch.setattr(
        payload_owner,
        "_verification_task_id_for_manifest",
        lambda _session, _task: fixture["verification_task_id"],
    )
    monkeypatch.setattr(
        payload_owner,
        "get_agent_task_audit_bundle",
        lambda *_args, **_kwargs: fixture["audit_bundle"],
    )
    monkeypatch.setattr(
        payload_owner,
        "_select_by_ids",
        lambda _session, _model, ids: {value: SimpleNamespace(id=value) for value in ids},
    )
    monkeypatch.setattr(
        payload_owner,
        "_document_payload",
        lambda row: {"document_id": str(row.id), "sha256": "document-sha"},
    )
    monkeypatch.setattr(
        payload_owner,
        "_manifest_run_payload",
        lambda row: {"run_id": str(row.id), "validation_status": "passed"},
    )
    monkeypatch.setattr(
        payload_owner,
        "_semantic_trace_payload",
        lambda *_args, **_kwargs: {
            "assertions": [{"assertion_id": "assertion-1"}],
            "facts": [{"fact_id": "fact-1"}],
            "assertion_evidence": [{"assertion_id": "assertion-1"}],
        },
    )
    monkeypatch.setattr(
        payload_owner,
        "_report_evidence_card_source_records",
        lambda _cards: [{"source": "card"}],
    )
    monkeypatch.setattr(
        payload_owner,
        "_source_record_payloads_from_semantic_trace",
        lambda _session, _assertion_evidence: [{"source": "semantic"}],
    )
    monkeypatch.setattr(
        payload_owner,
        "_technical_report_provenance_edges",
        lambda **_kwargs: [{"edge_type": "derived_from"}],
    )

    payload = payload_owner.build_technical_report_evidence_manifest_payload(
        session,
        fixture["task_id"],
    )

    assert payload["audit_checklist"]["verification_passed"] is False
    assert payload["audit_checklist"]["complete"] is False
