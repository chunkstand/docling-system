from __future__ import annotations

from uuid import uuid4

from app.services.evidence import apply_technical_report_derivation_links, payload_sha256
from app.services.technical_reports import verify_technical_report
from tests.unit.test_technical_reports import _draft_from_semantic_brief, _semantic_brief_payload


def test_verification_fails_when_claim_derivation_hash_is_stale(monkeypatch) -> None:
    draft = _draft_from_semantic_brief(monkeypatch, _semantic_brief_payload())
    draft["claims"][0]["rendered_text"] = (
        f"{draft['claims'][0]['rendered_text']} Tampered after the hash was frozen."
    )

    verification = verify_technical_report(draft)

    assert verification.verification_outcome == "failed"
    assert verification.summary["evidence_package_integrity_mismatch_count"] > 0
    assert verification.summary["derivation_integrity_mismatch_count"] > 0
    assert any(
        "derivation hash does not match recomputed" in reason
        for reason in verification.verification_reasons
    )
    frozen_metric = next(
        metric
        for metric in verification.success_metrics
        if metric["metric_key"] == "frozen_evidence_package"
    )
    assert frozen_metric["passed"] is False


def test_verification_fails_when_draft_package_hash_is_tampered(monkeypatch) -> None:
    draft = _draft_from_semantic_brief(monkeypatch, _semantic_brief_payload())
    draft["evidence_package_sha256"] = "0" * 64

    verification = verify_technical_report(draft)

    assert verification.verification_outcome == "failed"
    assert verification.summary["evidence_package_integrity_mismatch_count"] == 1
    assert verification.summary["derivation_integrity_mismatch_count"] == 0
    assert any(
        "Draft evidence package hash does not match recomputed" in reason
        for reason in verification.verification_reasons
    )


def test_verification_fails_when_provenance_lock_does_not_match_claim(monkeypatch) -> None:
    draft = _draft_from_semantic_brief(monkeypatch, _semantic_brief_payload())
    claim = draft["claims"][0]
    claim["provenance_lock"]["source_search_request_result_ids"] = [str(uuid4())]
    claim["provenance_lock_sha256"] = payload_sha256(claim["provenance_lock"])
    apply_technical_report_derivation_links(draft)

    verification = verify_technical_report(draft)

    assert verification.verification_outcome == "failed"
    assert verification.summary["provenance_lock_integrity_mismatch_count"] == 0
    assert verification.summary["provenance_lock_contract_mismatch_count"] == 1
    assert any(
        "provenance lock does not match claim fields" in reason
        for reason in verification.verification_reasons
    )


def test_verification_fails_when_claim_support_judgment_is_unsupported(monkeypatch) -> None:
    draft = _draft_from_semantic_brief(monkeypatch, _semantic_brief_payload())
    claim = draft["claims"][0]
    judgment = {
        **claim["support_judgment"],
        "verdict": "unsupported",
        "support_score": 0.01,
        "unsupported_reasons": ["unit_test_forced_unsupported"],
    }
    claim["support_verdict"] = "unsupported"
    claim["support_score"] = 0.01
    claim["support_judgment"] = judgment
    claim["support_judgment_sha256"] = payload_sha256(judgment)
    apply_technical_report_derivation_links(draft)

    verification = verify_technical_report(draft)

    assert verification.verification_outcome == "failed"
    assert verification.summary["unsupported_support_judgment_count"] == 1
    assert verification.summary["claim_support_score_below_threshold_count"] == 1
    assert any(
        "support judge verdict is unsupported" in reason
        for reason in verification.verification_reasons
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
