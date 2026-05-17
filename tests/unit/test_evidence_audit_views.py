from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.evidence_audit_views as evidence_audit_views
import app.services.evidence_audit_views_bundle as bundle_owner
import app.services.evidence_audit_views_context as context_owner
import app.services.evidence_audit_views_payloads as payload_owner
import app.services.evidence_audit_views_release_readiness as readiness_owner
from app.services.evidence_common import payload_sha256
from app.services.evidence_constants import RELEASE_READINESS_DB_GATE_CHECK_KEY


def test_provenance_export_receipt_payload_preserves_frozen_export_hashes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        payload_owner,
        "_frozen_export_receipt",
        lambda payload: {"receipt_id": "receipt-1", "payload_keys": sorted(payload)},
    )
    monkeypatch.setattr(
        payload_owner,
        "_prov_export_receipt_integrity",
        lambda payload: {"ok": True, "frozen_export": "frozen_export" in payload},
    )
    row = SimpleNamespace(
        id=uuid4(),
        task_id=uuid4(),
        artifact_kind="technical_report_prov_export",
        storage_path="storage/evidence/prov-export.json",
        payload_json={
            "frozen_export": {
                "export_payload_sha256": "export-sha",
                "prov_hash_basis_sha256": "basis-sha",
            }
        },
    )

    payload = evidence_audit_views._provenance_export_receipt_payload(row)

    assert payload["artifact_id"] == row.id
    assert payload["task_id"] == row.task_id
    assert payload["export_payload_sha256"] == "export-sha"
    assert payload["prov_hash_basis_sha256"] == "basis-sha"
    assert payload["export_receipt"]["receipt_id"] == "receipt-1"
    assert payload["receipt_integrity"] == {"ok": True, "frozen_export": True}


def test_context_pack_audit_raises_for_missing_verification_task() -> None:
    class _MissingSession:
        def get(self, *_args, **_kwargs):
            return None

    with pytest.raises(ValueError, match="was not found"):
        evidence_audit_views._technical_report_context_pack_audit_for_verification_task(
            _MissingSession(),
            uuid4(),
        )


def test_audit_views_facade_exports_split_owners() -> None:
    assert (
        evidence_audit_views.provenance_export_receipt_payload
        is payload_owner.provenance_export_receipt_payload
    )
    assert (
        evidence_audit_views._technical_report_context_pack_audit_for_verification_task
        is context_owner.technical_report_context_pack_audit_for_verification_task
    )
    assert (
        evidence_audit_views.persist_technical_report_release_readiness_db_gate
        is readiness_owner.persist_technical_report_release_readiness_db_gate
    )
    assert (
        evidence_audit_views.get_agent_task_audit_bundle is bundle_owner.get_agent_task_audit_bundle
    )


def test_release_readiness_governance_event_backfill_relinks_mismatched_event(
    monkeypatch,
) -> None:
    existing_event_id = uuid4()
    new_event_id = uuid4()
    row = SimpleNamespace(
        evidence_manifest_id=uuid4(),
        prov_export_artifact_id=uuid4(),
        semantic_governance_event_id=existing_event_id,
        updated_at=None,
    )

    class _FakeSession:
        def __init__(self) -> None:
            self.flush_calls = 0

        def get(self, *_args, **_kwargs):
            return SimpleNamespace(
                id=existing_event_id,
                event_kind="wrong_kind",
                evidence_manifest_id=row.evidence_manifest_id,
                agent_task_artifact_id=row.prov_export_artifact_id,
            )

        def flush(self) -> None:
            self.flush_calls += 1

    session = _FakeSession()
    monkeypatch.setattr(
        readiness_owner,
        "record_technical_report_release_readiness_db_gate_event",
        lambda _session, gate: SimpleNamespace(id=new_event_id, gate_id=getattr(gate, "id", None)),
    )

    persisted = readiness_owner.ensure_technical_report_release_readiness_db_gate_governance_event(
        session,
        row,
    )

    assert persisted is row
    assert row.semantic_governance_event_id == new_event_id
    assert row.updated_at is not None
    assert session.flush_calls == 1


def test_persist_release_readiness_db_gate_builds_row_from_context_pack_audit(
    monkeypatch,
) -> None:
    verification_task_id = uuid4()
    source_verification_id = uuid4()
    source_verification_task_id = uuid4()
    harness_task_id = uuid4()
    evidence_manifest = SimpleNamespace(id=uuid4())
    prov_export_artifact = SimpleNamespace(id=uuid4())
    gate_payload = {
        "verification_id": str(source_verification_id),
        "verification_task_id": str(source_verification_task_id),
        "passed": True,
        "required": True,
        "coverage_complete": True,
        "complete": True,
        "source_search_request_count": 2,
        "verified_request_count": 2,
        "failure_count": 0,
        "source_search_request_ids": ["search-1", "search-2"],
        "verified_request_ids": ["search-1", "search-2"],
        "missing_expected_request_ids": [],
        "unexpected_verified_request_ids": [],
        "summary": {"failed_ref_count": 0},
    }

    class _FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.flush_calls = 0

        def add(self, row) -> None:
            self.added.append(row)

        def flush(self) -> None:
            self.flush_calls += 1

    session = _FakeSession()
    monkeypatch.setattr(
        readiness_owner,
        "_technical_report_readiness_db_gate_for_verification_task",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        readiness_owner,
        "technical_report_context_pack_audit_for_verification_task",
        lambda *_args, **_kwargs: {
            "harness_task_id": str(harness_task_id),
            "release_readiness_db_gate": gate_payload,
        },
    )
    monkeypatch.setattr(
        readiness_owner,
        "ensure_technical_report_release_readiness_db_gate_governance_event",
        lambda _session, row: row,
    )

    row = readiness_owner.persist_technical_report_release_readiness_db_gate(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=evidence_manifest,
        prov_export_artifact=prov_export_artifact,
    )

    assert row is session.added[0]
    assert session.flush_calls == 1
    assert row.technical_report_verification_task_id == verification_task_id
    assert row.source_verification_id == source_verification_id
    assert row.source_verification_task_id == source_verification_task_id
    assert row.harness_task_id == harness_task_id
    assert row.evidence_manifest_id == evidence_manifest.id
    assert row.prov_export_artifact_id == prov_export_artifact.id
    assert row.check_key == RELEASE_READINESS_DB_GATE_CHECK_KEY
    assert row.passed is True
    assert row.coverage_complete is True
    assert row.complete is True
    assert row.source_search_request_ids_json == ["search-1", "search-2"]
    assert row.verified_request_ids_json == ["search-1", "search-2"]
    assert row.summary_json == {"failed_ref_count": 0}
    assert row.gate_payload_json == gate_payload
    assert row.gate_payload_sha256 == str(payload_sha256(gate_payload))


def test_get_agent_task_audit_bundle_marks_complete_when_owner_integrity_is_green(
    monkeypatch,
) -> None:
    verify_task_id = uuid4()
    draft_task_id = uuid4()
    manifest_id = uuid4()
    prov_artifact_id = uuid4()
    report_export_id = uuid4()
    draft_payload = {
        "harness_task_id": str(uuid4()),
        "claims": [
            {
                "claim_id": "claim-1",
                "provenance_lock": {"lock": "value"},
                "provenance_lock_sha256": "lock-sha",
                "support_verdict": "supported",
                "support_score": 0.9,
                "support_judge_run_id": "judge-1",
                "support_judgment": {"status": "supported"},
                "support_judgment_sha256": "support-sha",
                "source_search_request_result_ids": ["result-1"],
            }
        ],
    }
    task = SimpleNamespace(
        id=verify_task_id,
        task_type="verify_technical_report",
        result_json={"payload": {"verification": {"outcome": "passed"}}},
    )
    draft_task = SimpleNamespace(
        id=draft_task_id,
        task_type="draft_technical_report",
        result_json={"payload": {"draft": draft_payload}},
    )
    verification_row = SimpleNamespace(outcome="passed")
    prov_artifact = SimpleNamespace(
        id=prov_artifact_id,
        task_id=verify_task_id,
        artifact_kind="technical_report_prov_export",
        created_at=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
        storage_path="storage/prov.json",
        payload_json={},
    )
    context_artifact = SimpleNamespace(
        id=uuid4(),
        task_id=draft_task_id,
        artifact_kind="document_generation_context_pack",
        created_at=datetime(2026, 5, 15, 11, 0, tzinfo=UTC),
        storage_path=None,
        payload_json={},
    )
    feedback_row = SimpleNamespace(id=uuid4(), claim_id="claim-1")
    report_export = SimpleNamespace(id=report_export_id, package_kind="technical_report_claims")
    search_export = SimpleNamespace(id=uuid4(), package_kind="search_request")
    derivation = SimpleNamespace(id=uuid4(), claim_id="claim-1")
    release_gate_row = SimpleNamespace(id=uuid4())

    class _FakeSession:
        def __init__(self) -> None:
            self.scalar_batches = [
                [],
                [SimpleNamespace(id=manifest_id)],
                [report_export, search_export],
                [derivation],
            ]

        def get(self, _model, row_id):
            return task if row_id == verify_task_id else None

        def scalars(self, *_args, **_kwargs):
            return self.scalar_batches.pop(0)

    session = _FakeSession()
    monkeypatch.setattr(
        bundle_owner,
        "technical_report_audit_inputs_for_task",
        lambda *_args, **_kwargs: {
            "draft_task": draft_task,
            "verification_task": task,
            "verification_row": verification_row,
            "draft_payload": draft_payload,
            "related_task_ids": [draft_task_id, verify_task_id],
            "artifacts": [context_artifact, prov_artifact],
            "operator_runs": [
                SimpleNamespace(
                    operator_kind="judge", operator_name="technical_report_claim_support_judge"
                ),
                SimpleNamespace(
                    operator_kind="generate", operator_name="technical_report_generation"
                ),
                SimpleNamespace(
                    operator_kind="verify", operator_name="technical_report_verification"
                ),
            ],
            "harness_task_id": uuid4(),
            "context_pack_eval_task_ids": [uuid4()],
            "context_pack_verifications": [SimpleNamespace(id=uuid4())],
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "_provenance_export_receipt_payload",
        lambda _row: {
            "export_receipt": {
                "receipt_sha256": "receipt-1",
                "signature_status": "signed",
            },
            "receipt_integrity": {
                "complete": True,
                "signature_verification_status": "verified",
            },
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "semantic_governance_chain_for_audit",
        lambda *_args, **_kwargs: {
            "integrity": {
                "has_events": True,
                "complete": True,
                "links_requested_prov_receipt": True,
                "change_impact_evaluated": True,
            },
            "events": [],
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "_claim_retrieval_feedback_rows_for_verification_task",
        lambda *_args, **_kwargs: [feedback_row],
    )
    monkeypatch.setattr(
        bundle_owner,
        "_technical_report_context_pack_audit_payload",
        lambda **kwargs: {
            "harness_task_id": str(kwargs["harness_task_id"]),
            "evaluation_task_ids": [str(row_id) for row_id in kwargs["eval_task_ids"]],
            "context_pack_artifacts": [{"artifact_id": "context-artifact"}],
            "evaluation_artifacts": [{"artifact_id": "eval-artifact"}],
            "operator_runs": [{"operator_name": "document_generation_context_pack_evaluation"}],
            "release_readiness_assessments": [{"assessment_id": "assessment-1"}],
            "release_readiness_db_gate": {"verification_id": "verification-1", "complete": True},
            "integrity": {
                "has_context_pack_artifact": True,
                "has_context_pack_evaluation_artifact": True,
                "has_context_pack_verifier_record": True,
                "has_context_pack_evaluation_operator_run": True,
                "latest_context_pack_evaluation_passed": True,
                "context_pack_hash_verified": True,
                "has_release_readiness_assessments": True,
                "release_readiness_assessments_cover_source_requests": True,
                "release_readiness_assessments_ready": True,
                "release_readiness_assessment_integrity_verified": True,
                "release_readiness_db_gate_verified": True,
                "release_readiness_db_gate_complete": True,
                "release_readiness_db_covers_source_requests": True,
                "has_persisted_release_readiness_db_gate": True,
                "persisted_release_readiness_db_gate_integrity_verified": True,
                "complete": True,
            },
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "_technical_report_readiness_db_gate_for_verification_task",
        lambda *_args, **_kwargs: release_gate_row,
    )
    monkeypatch.setattr(
        bundle_owner,
        "_with_release_readiness_db_gate_record",
        lambda context_pack_audit, _row, **_kwargs: {
            **context_pack_audit,
            "release_readiness_db_gate_record": {"gate_id": "gate-1"},
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "_change_impact_payload",
        lambda *_args, **_kwargs: {
            "impacted": False,
            "claim_support_policy_change_impacts": {
                "waiver_lifecycle": {
                    "unresolved_waiver_count": 0,
                    "invalid_waiver_closure_count": 0,
                    "waiver_closure_integrity_verified": True,
                },
                "replay_alert_fixture_corpus": {
                    "invalid_snapshot_governance_count": 0,
                    "trace_incomplete_snapshot_count": 0,
                    "governance_integrity_verified": True,
                    "trace_complete": True,
                    "active_replay_alert_fixture_corpus_snapshot_id": "snapshot-1",
                    "active_replay_alert_fixture_corpus_sha256": "snapshot-sha",
                },
            },
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "_technical_report_integrity_payload",
        lambda *_args, **_kwargs: {
            "draft_package_hash_matches": True,
            "export_package_hash_matches": True,
            "claim_derivation_count_matches": True,
            "claim_derivation_hash_mismatch_count": 0,
            "claim_package_hash_mismatch_count": 0,
            "claim_provenance_lock_mismatch_count": 0,
            "claim_provenance_lock_contract_mismatch_count": 0,
            "missing_claim_provenance_lock_count": 0,
            "claim_support_judgment_mismatch_count": 0,
            "claim_support_judgment_contract_mismatch_count": 0,
            "missing_claim_support_judgment_count": 0,
            "failed_claim_support_judgment_count": 0,
            "missing_claim_derivation_count": 0,
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "_technical_report_claim_feedback_integrity_payload",
        lambda *_args, **_kwargs: {
            "coverage_complete": True,
            "integrity_verified": True,
        },
    )
    monkeypatch.setattr(
        bundle_owner,
        "technical_report_search_evidence_closure_payload",
        lambda *_args, **_kwargs: {
            "complete": True,
            "trace_summaries": [{"trace_id": "trace-1"}],
        },
    )
    monkeypatch.setattr(bundle_owner, "_task_payload", lambda row: {"task_id": str(row.id)})
    monkeypatch.setattr(
        bundle_owner,
        "_verification_payload",
        lambda row: {"outcome": row.outcome} if row is not None else None,
    )
    monkeypatch.setattr(
        bundle_owner,
        "_artifact_payload",
        lambda row: {"artifact_id": str(row.id), "artifact_kind": row.artifact_kind},
    )
    monkeypatch.setattr(
        bundle_owner,
        "_immutability_event_payload",
        lambda row: {"event_id": str(row.id)},
    )
    monkeypatch.setattr(
        bundle_owner,
        "_operator_run_summary",
        lambda row: {"operator_kind": row.operator_kind, "operator_name": row.operator_name},
    )
    monkeypatch.setattr(
        bundle_owner,
        "_evidence_export_payload",
        lambda row: {"package_kind": row.package_kind},
    )
    monkeypatch.setattr(
        bundle_owner,
        "_claim_derivation_payload",
        lambda row: {"claim_id": row.claim_id},
    )
    monkeypatch.setattr(
        bundle_owner,
        "_claim_retrieval_feedback_payload",
        lambda row, **_kwargs: {"feedback_id": str(row.id)},
    )
    monkeypatch.setattr(bundle_owner, "payload_sha256", lambda _payload: "bundle-sha")

    audit_bundle = evidence_audit_views.get_agent_task_audit_bundle(session, verify_task_id)

    assert audit_bundle["schema_name"] == "technical_report_audit_bundle"
    assert audit_bundle["audit_checklist"]["complete"] is True
    assert audit_bundle["audit_bundle_sha256"] == "bundle-sha"
    assert audit_bundle["provenance_export_receipts"][0]["export_receipt"]["receipt_sha256"] == (
        "receipt-1"
    )
    assert audit_bundle["context_pack_audit"]["release_readiness_db_gate_record"]["gate_id"] == (
        "gate-1"
    )


def test_audit_views_facade_stays_narrow() -> None:
    with open(evidence_audit_views.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 600
