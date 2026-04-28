from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    ClaimSupportCalibrationPolicy,
    ClaimSupportEvaluation,
    ClaimSupportEvaluationCase,
    ClaimSupportFixtureSet,
)
from app.services.evidence import payload_sha256
from app.services.technical_reports import judge_technical_report_claim_support

CLAIM_SUPPORT_JUDGE_NAME = "technical_report_claim_support_judge"
CLAIM_SUPPORT_JUDGE_VERSION = "deterministic_claim_support_v1"
CLAIM_SUPPORT_EVALUATION_SCHEMA_NAME = "claim_support_judge_evaluation"
CLAIM_SUPPORT_EVALUATION_SCHEMA_VERSION = "1.0"
CLAIM_SUPPORT_FIXTURE_SET_SCHEMA_NAME = "claim_support_fixture_set"
CLAIM_SUPPORT_FIXTURE_SET_SCHEMA_VERSION = "1.0"
CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_NAME = "claim_support_calibration_policy"
CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_VERSION = "1.0"
DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_NAME = "default_claim_support_v1"
DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_VERSION = "v1"
DEFAULT_CLAIM_SUPPORT_POLICY_NAME = "claim_support_judge_calibration_policy"
DEFAULT_CLAIM_SUPPORT_POLICY_VERSION = "v1"
CLAIM_SUPPORT_VERDICTS = ("supported", "unsupported", "insufficient_evidence")
DEFAULT_REQUIRED_HARD_CASE_KINDS = (
    "exact_source_support",
    "weak_wording_support",
    "wrong_evidence",
    "lexical_overlap_wrong_evidence",
    "missing_traceable_evidence",
    "graph_only_support",
)
DEFAULT_MIN_HARD_CASE_KIND_COUNT = 4
_FIXTURE_NAMESPACE = uuid.UUID("1adfc8cf-07de-41fa-b58f-a7b8df90b452")


def _fixture_uuid(case_id: str, key: str) -> str:
    return str(uuid.uuid5(_FIXTURE_NAMESPACE, f"{case_id}:{key}"))


def _source_card(
    *,
    case_id: str,
    excerpt: str,
    concept_keys: list[str],
    matched_terms: list[str] | None = None,
) -> dict[str, Any]:
    document_id = _fixture_uuid(case_id, "document")
    run_id = _fixture_uuid(case_id, "run")
    semantic_pass_id = _fixture_uuid(case_id, "semantic-pass")
    request_id = _fixture_uuid(case_id, "search-request")
    result_id = _fixture_uuid(case_id, "search-result")
    return {
        "evidence_card_id": f"card:{case_id}:source",
        "evidence_kind": "source_evidence",
        "source_type": "chunk",
        "source_locator": f"chunk:{case_id}:source",
        "chunk_id": _fixture_uuid(case_id, "chunk"),
        "citation_label": "E1",
        "document_id": document_id,
        "run_id": run_id,
        "semantic_pass_id": semantic_pass_id,
        "source_document_ids": [document_id],
        "source_filename": "claim-support-eval.pdf",
        "page_from": 1,
        "page_to": 1,
        "excerpt": excerpt,
        "source_artifact_api_path": (
            f"/documents/{document_id}/chunks/{_fixture_uuid(case_id, 'chunk')}"
        ),
        "evidence_ids": [_fixture_uuid(case_id, "evidence")],
        "fact_ids": [_fixture_uuid(case_id, "fact")],
        "assertion_ids": [_fixture_uuid(case_id, "assertion")],
        "concept_keys": list(concept_keys),
        "support_level": "supported",
        "review_status": "candidate",
        "relation_key": "document_supports_claim",
        "source_search_request_ids": [request_id],
        "source_search_request_result_ids": [result_id],
        "source_evidence_match_keys": [f"source:chunk:{_fixture_uuid(case_id, 'chunk')}"],
        "source_evidence_match_status": "matched_source_record",
        "metadata": {
            "matched_terms": matched_terms or concept_keys,
            "source_record_keys": [f"source:chunk:{_fixture_uuid(case_id, 'chunk')}"],
        },
    }


def _draft_fixture(
    *,
    case_id: str,
    rendered_text: str,
    concept_keys: list[str],
    evidence_cards: list[dict[str, Any]],
    graph_context: list[dict[str, Any]] | None = None,
    graph_edge_ids: list[str] | None = None,
) -> dict[str, Any]:
    document_id = _fixture_uuid(case_id, "document")
    source_result_ids = [
        result_id
        for card in evidence_cards
        for result_id in card.get("source_search_request_result_ids", [])
    ]
    source_request_ids = [
        request_id
        for card in evidence_cards
        for request_id in card.get("source_search_request_ids", [])
    ]
    source_document_ids = [
        source_document_id
        for card in evidence_cards
        for source_document_id in card.get("source_document_ids", [])
    ] or [document_id]
    return {
        "document_kind": "technical_report",
        "title": "Claim Support Evaluation Fixture",
        "goal": "Evaluate the claim support judge.",
        "audience": "Evaluation",
        "target_length": "short",
        "harness_task_id": _fixture_uuid(case_id, "harness-task"),
        "generator_mode": "structured_fallback",
        "generator_model": None,
        "used_fallback": True,
        "llm_adapter_contract": {},
        "document_refs": [],
        "required_concept_keys": list(concept_keys),
        "sections": [
            {
                "section_id": "section:claim_support",
                "title": "Claim Support",
                "body_markdown": rendered_text,
                "claim_ids": [f"claim:{case_id}"],
            }
        ],
        "claims": [
            {
                "claim_id": f"claim:{case_id}",
                "section_id": "section:claim_support",
                "rendered_text": rendered_text,
                "concept_keys": list(concept_keys),
                "evidence_card_ids": [card["evidence_card_id"] for card in evidence_cards],
                "graph_edge_ids": list(graph_edge_ids or []),
                "fact_ids": [
                    fact_id for card in evidence_cards for fact_id in card.get("fact_ids", [])
                ],
                "assertion_ids": [
                    assertion_id
                    for card in evidence_cards
                    for assertion_id in card.get("assertion_ids", [])
                ],
                "source_document_ids": source_document_ids,
                "support_level": "supported",
                "review_policy_status": "candidate_disclosed",
                "source_search_request_ids": source_request_ids,
                "source_search_request_result_ids": source_result_ids,
            }
        ],
        "blocked_claims": [],
        "evidence_cards": evidence_cards,
        "source_evidence_package_exports": [],
        "graph_context": list(graph_context or []),
        "markdown": rendered_text,
        "warnings": [],
        "success_metrics": [],
    }


def _graph_fixture_case(case_id: str) -> dict[str, Any]:
    document_id = _fixture_uuid(case_id, "document")
    edge_id = "edge:concept:integration_threshold:concept:change_window"
    graph_context = [
        {
            "edge_id": edge_id,
            "graph_snapshot_id": _fixture_uuid(case_id, "graph-snapshot"),
            "graph_version": "claim-support-eval-v1",
            "relation_key": "concept_depends_on_concept",
            "relation_label": "Depends On",
            "subject_entity_key": "concept:integration_threshold",
            "subject_label": "Integration Threshold",
            "object_entity_key": "concept:change_window",
            "object_label": "Change Window",
            "review_status": "approved",
            "support_level": "supported",
            "extractor_score": 0.91,
            "supporting_document_ids": [document_id],
            "support_ref_ids": [_fixture_uuid(case_id, "graph-support")],
        }
    ]
    return {
        "case_id": case_id,
        "description": (
            "Approved graph context can support a relationship claim without a source card."
        ),
        "hard_case_kind": "graph_only_support",
        "expected_verdict": "supported",
        "claim_id": f"claim:{case_id}",
        "draft_payload": _draft_fixture(
            case_id=case_id,
            rendered_text="Integration thresholds depend on change windows.",
            concept_keys=["integration_threshold", "change_window"],
            evidence_cards=[],
            graph_context=graph_context,
            graph_edge_ids=[edge_id],
        ),
    }


def default_claim_support_evaluation_fixtures() -> list[dict[str, Any]]:
    supported_case = "supported_exact_source_evidence"
    wrong_case = "unsupported_wrong_evidence"
    contradiction_case = "unsupported_contradiction_cue"
    weak_case = "supported_weak_wording"
    insufficient_case = "insufficient_no_traceable_refs"
    return [
        {
            "case_id": supported_case,
            "description": "Claim and source evidence describe the same release-control fact.",
            "hard_case_kind": "exact_source_support",
            "expected_verdict": "supported",
            "claim_id": f"claim:{supported_case}",
            "draft_payload": _draft_fixture(
                case_id=supported_case,
                rendered_text="Integration thresholds govern release decisions.",
                concept_keys=["integration_threshold", "release_decision"],
                evidence_cards=[
                    _source_card(
                        case_id=supported_case,
                        excerpt=(
                            "Integration thresholds govern release decisions for "
                            "controlled deployments."
                        ),
                        concept_keys=["integration_threshold", "release_decision"],
                        matched_terms=["integration thresholds", "release decisions"],
                    )
                ],
            ),
        },
        {
            "case_id": weak_case,
            "description": "Weaker wording still supports the claim through shared evidence terms.",
            "hard_case_kind": "weak_wording_support",
            "expected_verdict": "supported",
            "claim_id": f"claim:{weak_case}",
            "draft_payload": _draft_fixture(
                case_id=weak_case,
                rendered_text="Integration thresholds govern release decisions.",
                concept_keys=["integration_threshold", "release_decision"],
                evidence_cards=[
                    _source_card(
                        case_id=weak_case,
                        excerpt=(
                            "Release approvals use integration threshold values before "
                            "deployment windows change."
                        ),
                        concept_keys=["integration_threshold", "release_decision"],
                        matched_terms=["release approvals", "integration threshold"],
                    )
                ],
            ),
        },
        {
            "case_id": wrong_case,
            "description": "A traceable source card exists but describes unrelated evidence.",
            "hard_case_kind": "wrong_evidence",
            "expected_verdict": "unsupported",
            "claim_id": f"claim:{wrong_case}",
            "draft_payload": _draft_fixture(
                case_id=wrong_case,
                rendered_text="Integration thresholds govern release decisions.",
                concept_keys=["integration_threshold", "release_decision"],
                evidence_cards=[
                    _source_card(
                        case_id=wrong_case,
                        excerpt="Painting requirements describe wall colors and finish schedules.",
                        concept_keys=["wall_color"],
                        matched_terms=["wall colors", "finish schedules"],
                    )
                ],
            ),
        },
        {
            "case_id": contradiction_case,
            "description": (
                "Lexically similar evidence explicitly says it does not support the claim."
            ),
            "hard_case_kind": "lexical_overlap_wrong_evidence",
            "expected_verdict": "unsupported",
            "claim_id": f"claim:{contradiction_case}",
            "draft_payload": _draft_fixture(
                case_id=contradiction_case,
                rendered_text="Integration thresholds govern release decisions.",
                concept_keys=["integration_threshold", "release_decision"],
                evidence_cards=[
                    _source_card(
                        case_id=contradiction_case,
                        excerpt=(
                            "Integration thresholds are historical examples and do not "
                            "govern release decisions."
                        ),
                        concept_keys=["integration_threshold", "release_decision"],
                        matched_terms=["integration thresholds", "release decisions"],
                    )
                ],
            ),
        },
        {
            "case_id": insufficient_case,
            "description": "A claim without cards or approved graph refs is insufficient.",
            "hard_case_kind": "missing_traceable_evidence",
            "expected_verdict": "insufficient_evidence",
            "claim_id": f"claim:{insufficient_case}",
            "draft_payload": _draft_fixture(
                case_id=insufficient_case,
                rendered_text="Integration thresholds govern release decisions.",
                concept_keys=["integration_threshold", "release_decision"],
                evidence_cards=[],
            ),
        },
        _graph_fixture_case("supported_graph_only"),
    ]


def _thresholds_payload(
    *,
    min_overall_accuracy: float,
    min_verdict_precision: float,
    min_verdict_recall: float,
    min_support_score: float,
) -> dict[str, Any]:
    return {
        "min_overall_accuracy": min_overall_accuracy,
        "min_verdict_precision": min_verdict_precision,
        "min_verdict_recall": min_verdict_recall,
        "min_support_score": min_support_score,
    }


def _normalize_string_list(values: Any) -> list[str]:
    if not values:
        return []
    return sorted({str(value) for value in values if str(value)})


def _fixture_set_payload(
    *,
    fixture_set_name: str,
    fixture_set_version: str,
    fixtures: list[dict[str, Any]],
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hard_case_kinds = _normalize_string_list(
        fixture.get("hard_case_kind") for fixture in fixtures if fixture.get("hard_case_kind")
    )
    verdicts = _normalize_string_list(
        fixture.get("expected_verdict") for fixture in fixtures if fixture.get("expected_verdict")
    )
    payload = {
        "schema_name": CLAIM_SUPPORT_FIXTURE_SET_SCHEMA_NAME,
        "schema_version": CLAIM_SUPPORT_FIXTURE_SET_SCHEMA_VERSION,
        "fixture_set_name": fixture_set_name,
        "fixture_set_version": fixture_set_version,
        "status": status,
        "judge_name": CLAIM_SUPPORT_JUDGE_NAME,
        "judge_version": CLAIM_SUPPORT_JUDGE_VERSION,
        "fixture_count": len(fixtures),
        "hard_case_kinds": hard_case_kinds,
        "verdicts": verdicts,
        "fixtures": fixtures,
        "metadata": metadata or {},
    }
    return {**payload, "fixture_set_sha256": str(payload_sha256(payload))}


def build_claim_support_calibration_policy_payload(
    *,
    policy_name: str = DEFAULT_CLAIM_SUPPORT_POLICY_NAME,
    policy_version: str = DEFAULT_CLAIM_SUPPORT_POLICY_VERSION,
    status: str = "active",
    thresholds: dict[str, Any] | None = None,
    min_hard_case_kind_count: int = DEFAULT_MIN_HARD_CASE_KIND_COUNT,
    required_hard_case_kinds: list[str] | tuple[str, ...] | None = None,
    required_verdicts: list[str] | tuple[str, ...] | None = None,
    owner: str = "docling-system",
    source: str = "built_in_default",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy_thresholds = dict(
        thresholds
        or _thresholds_payload(
            min_overall_accuracy=1.0,
            min_verdict_precision=1.0,
            min_verdict_recall=1.0,
            min_support_score=0.34,
        )
    )
    payload = {
        "schema_name": CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_NAME,
        "schema_version": CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_VERSION,
        "policy_name": policy_name,
        "policy_version": policy_version,
        "status": status,
        "owner": owner,
        "source": source,
        "judge_name": CLAIM_SUPPORT_JUDGE_NAME,
        "judge_version": CLAIM_SUPPORT_JUDGE_VERSION,
        "thresholds": policy_thresholds,
        "min_hard_case_kind_count": int(min_hard_case_kind_count),
        "required_hard_case_kinds": _normalize_string_list(
            required_hard_case_kinds or DEFAULT_REQUIRED_HARD_CASE_KINDS
        ),
        "required_verdicts": _normalize_string_list(required_verdicts or CLAIM_SUPPORT_VERDICTS),
        "metadata": metadata or {},
    }
    return {**payload, "policy_sha256": str(payload_sha256(payload))}


def ensure_claim_support_fixture_set(
    session: Session,
    *,
    fixture_set_name: str,
    fixture_set_version: str = DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_VERSION,
    fixtures: list[dict[str, Any]] | None = None,
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> ClaimSupportFixtureSet:
    fixture_rows = list(fixtures or default_claim_support_evaluation_fixtures())
    payload = _fixture_set_payload(
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        fixtures=fixture_rows,
        status=status,
        metadata=metadata,
    )
    existing = session.scalar(
        select(ClaimSupportFixtureSet).where(
            ClaimSupportFixtureSet.fixture_set_name == fixture_set_name,
            ClaimSupportFixtureSet.fixture_set_version == fixture_set_version,
            ClaimSupportFixtureSet.fixture_set_sha256 == payload["fixture_set_sha256"],
        )
    )
    if existing is not None:
        return existing
    row = ClaimSupportFixtureSet(
        id=uuid.uuid4(),
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        status=status,
        fixture_set_sha256=str(payload["fixture_set_sha256"]),
        fixture_count=int(payload["fixture_count"]),
        hard_case_kinds_json=list(payload["hard_case_kinds"]),
        verdicts_json=list(payload["verdicts"]),
        fixtures_json=fixture_rows,
        metadata_json=dict(payload["metadata"]),
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def ensure_claim_support_calibration_policy(
    session: Session,
    *,
    policy_payload: dict[str, Any] | None = None,
    thresholds: dict[str, Any] | None = None,
) -> ClaimSupportCalibrationPolicy:
    payload = dict(
        policy_payload
        or build_claim_support_calibration_policy_payload(thresholds=thresholds)
    )
    policy_sha256 = str(payload.get("policy_sha256") or payload_sha256(payload))
    existing = session.scalar(
        select(ClaimSupportCalibrationPolicy).where(
            ClaimSupportCalibrationPolicy.policy_name == str(payload["policy_name"]),
            ClaimSupportCalibrationPolicy.policy_version == str(payload["policy_version"]),
            ClaimSupportCalibrationPolicy.policy_sha256 == policy_sha256,
        )
    )
    if existing is not None:
        return existing
    row = ClaimSupportCalibrationPolicy(
        id=uuid.uuid4(),
        policy_name=str(payload["policy_name"]),
        policy_version=str(payload["policy_version"]),
        status=str(payload.get("status") or "active"),
        policy_sha256=policy_sha256,
        owner=payload.get("owner"),
        source=payload.get("source"),
        min_hard_case_kind_count=int(payload.get("min_hard_case_kind_count") or 0),
        required_hard_case_kinds_json=list(payload.get("required_hard_case_kinds") or []),
        required_verdicts_json=list(payload.get("required_verdicts") or []),
        thresholds_json=dict(payload.get("thresholds") or {}),
        policy_payload_json={**payload, "policy_sha256": policy_sha256},
        metadata_json=dict(payload.get("metadata") or {}),
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def resolve_claim_support_calibration_policy(
    session: Session,
    *,
    policy_name: str = DEFAULT_CLAIM_SUPPORT_POLICY_NAME,
    policy_version: str = DEFAULT_CLAIM_SUPPORT_POLICY_VERSION,
    thresholds: dict[str, Any] | None = None,
) -> ClaimSupportCalibrationPolicy:
    if (
        policy_name == DEFAULT_CLAIM_SUPPORT_POLICY_NAME
        and policy_version == DEFAULT_CLAIM_SUPPORT_POLICY_VERSION
    ):
        return ensure_claim_support_calibration_policy(session, thresholds=thresholds)
    row = session.scalar(
        select(ClaimSupportCalibrationPolicy)
        .where(
            ClaimSupportCalibrationPolicy.policy_name == policy_name,
            ClaimSupportCalibrationPolicy.policy_version == policy_version,
            ClaimSupportCalibrationPolicy.status == "active",
        )
        .order_by(ClaimSupportCalibrationPolicy.created_at.desc())
    )
    if row is None:
        raise ValueError(
            f"No active claim support calibration policy found for {policy_name} "
            f"version {policy_version}."
        )
    return row


def _verdict_metrics(case_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for verdict in CLAIM_SUPPORT_VERDICTS:
        true_positive = sum(
            1
            for row in case_results
            if row["expected_verdict"] == verdict and row["predicted_verdict"] == verdict
        )
        false_positive = sum(
            1
            for row in case_results
            if row["expected_verdict"] != verdict and row["predicted_verdict"] == verdict
        )
        false_negative = sum(
            1
            for row in case_results
            if row["expected_verdict"] == verdict and row["predicted_verdict"] != verdict
        )
        expected_count = true_positive + false_negative
        predicted_count = true_positive + false_positive
        precision = true_positive / predicted_count if predicted_count else 1.0
        recall = true_positive / expected_count if expected_count else 1.0
        metrics[verdict] = {
            "expected_count": expected_count,
            "predicted_count": predicted_count,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
        }
    return metrics


def evaluate_claim_support_judge_fixture_set(
    *,
    evaluation_id: UUID | None = None,
    evaluation_name: str = "claim_support_judge_calibration",
    fixture_set_name: str = DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_NAME,
    fixture_set_version: str = DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_VERSION,
    fixtures: list[dict[str, Any]] | None = None,
    calibration_policy: dict[str, Any] | None = None,
    fixture_set_id: UUID | None = None,
    policy_id: UUID | None = None,
    min_support_score: float = 0.34,
    min_overall_accuracy: float = 1.0,
    min_verdict_precision: float = 1.0,
    min_verdict_recall: float = 1.0,
) -> dict[str, Any]:
    evaluation_id = evaluation_id or uuid.uuid4()
    fixture_rows = list(fixtures or default_claim_support_evaluation_fixtures())
    requested_thresholds = _thresholds_payload(
        min_overall_accuracy=min_overall_accuracy,
        min_verdict_precision=min_verdict_precision,
        min_verdict_recall=min_verdict_recall,
        min_support_score=min_support_score,
    )
    policy_payload = dict(
        calibration_policy
        or build_claim_support_calibration_policy_payload(thresholds=requested_thresholds)
    )
    policy_sha256 = str(policy_payload.get("policy_sha256") or payload_sha256(policy_payload))
    policy_payload = {**policy_payload, "policy_sha256": policy_sha256}
    thresholds = dict(policy_payload.get("thresholds") or requested_thresholds)
    min_support_score = float(thresholds["min_support_score"])
    min_overall_accuracy = float(thresholds["min_overall_accuracy"])
    min_verdict_precision = float(thresholds["min_verdict_precision"])
    min_verdict_recall = float(thresholds["min_verdict_recall"])
    fixture_set_payload = _fixture_set_payload(
        fixture_set_name=fixture_set_name,
        fixture_set_version=fixture_set_version,
        fixtures=fixture_rows,
    )
    fixture_set_sha256 = str(fixture_set_payload["fixture_set_sha256"])
    case_results: list[dict[str, Any]] = []
    for index, fixture in enumerate(fixture_rows):
        support_payload = judge_technical_report_claim_support(
            fixture["draft_payload"],
            min_claim_support_score=min_support_score,
        )
        claim_id = fixture.get("claim_id")
        judgment = next(
            (
                row
                for row in support_payload.get("claim_judgments") or []
                if not claim_id or row.get("claim_id") == claim_id
            ),
            {},
        )
        expected_verdict = str(fixture.get("expected_verdict") or "")
        predicted_verdict = str(judgment.get("verdict") or "insufficient_evidence")
        passed = expected_verdict == predicted_verdict
        failure_reasons = [] if passed else [f"expected_{expected_verdict}_got_{predicted_verdict}"]
        claim_payload = next(iter(fixture["draft_payload"].get("claims") or []), {})
        case_results.append(
            {
                "case_index": index,
                "case_id": fixture["case_id"],
                "description": fixture.get("description"),
                "hard_case_kind": fixture.get("hard_case_kind"),
                "expected_verdict": expected_verdict,
                "predicted_verdict": predicted_verdict,
                "support_score": judgment.get("support_score"),
                "passed": passed,
                "failure_reasons": failure_reasons,
                "claim_payload": claim_payload,
                "support_judgment": judgment,
            }
        )

    verdict_metrics = _verdict_metrics(case_results)
    passed_case_count = sum(1 for row in case_results if row["passed"])
    case_count = len(case_results)
    overall_accuracy = passed_case_count / case_count if case_count else 0.0
    hard_case_kinds = sorted(
        {str(row.get("hard_case_kind")) for row in case_results if row.get("hard_case_kind")}
    )
    expected_verdicts = sorted({str(row["expected_verdict"]) for row in case_results})
    required_hard_case_kinds = _normalize_string_list(
        policy_payload.get("required_hard_case_kinds") or []
    )
    required_verdicts = _normalize_string_list(policy_payload.get("required_verdicts") or [])
    min_hard_case_kind_count = int(
        policy_payload.get("min_hard_case_kind_count") or DEFAULT_MIN_HARD_CASE_KIND_COUNT
    )
    missing_hard_case_kinds = sorted(set(required_hard_case_kinds) - set(hard_case_kinds))
    missing_verdicts = sorted(set(required_verdicts) - set(expected_verdicts))
    reasons: list[str] = []
    if overall_accuracy < min_overall_accuracy:
        reasons.append(
            f"Overall accuracy {overall_accuracy:.4f} is below {min_overall_accuracy:.4f}."
        )
    for verdict, metrics in verdict_metrics.items():
        if metrics["precision"] < min_verdict_precision:
            reasons.append(
                f"{verdict} precision {metrics['precision']:.4f} is below "
                f"{min_verdict_precision:.4f}."
            )
        if metrics["recall"] < min_verdict_recall:
            reasons.append(
                f"{verdict} recall {metrics['recall']:.4f} is below {min_verdict_recall:.4f}."
            )

    accuracy_gate_passed = not reasons
    summary = {
        "case_count": case_count,
        "passed_case_count": passed_case_count,
        "failed_case_count": case_count - passed_case_count,
        "overall_accuracy": round(overall_accuracy, 4),
        "gate_outcome": "pending",
        "hard_case_kind_count": len(hard_case_kinds),
        "hard_case_kinds": hard_case_kinds,
        "required_hard_case_kinds": required_hard_case_kinds,
        "missing_hard_case_kinds": missing_hard_case_kinds,
        "expected_verdicts": expected_verdicts,
        "required_verdicts": required_verdicts,
        "missing_verdicts": missing_verdicts,
        "policy_name": str(policy_payload["policy_name"]),
        "policy_version": str(policy_payload["policy_version"]),
        "policy_sha256": policy_sha256,
    }
    hard_case_coverage_passed = (
        summary["hard_case_kind_count"] >= min_hard_case_kind_count
        and not missing_hard_case_kinds
    )
    verdict_coverage_passed = not missing_verdicts
    auditability_passed = bool(fixture_set_sha256 and policy_sha256)
    success_metrics = [
        {
            "metric_key": "claim_support_judge_accuracy_gate",
            "stakeholder": "Omar Khattab",
            "passed": accuracy_gate_passed,
            "summary": "Support-judge verdicts pass fixed replay precision and recall gates.",
            "details": {
                "overall_accuracy": summary["overall_accuracy"],
                "verdict_metrics": verdict_metrics,
            },
        },
        {
            "metric_key": "claim_support_hard_case_coverage",
            "stakeholder": "Rich Sutton / Bitter Lesson",
            "passed": hard_case_coverage_passed,
            "summary": "Support-judge quality satisfies the governed hard-case policy.",
            "details": {
                "hard_case_kinds": hard_case_kinds,
                "hard_case_kind_count": len(hard_case_kinds),
                "min_hard_case_kind_count": min_hard_case_kind_count,
                "required_hard_case_kinds": required_hard_case_kinds,
                "missing_hard_case_kinds": missing_hard_case_kinds,
            },
        },
        {
            "metric_key": "claim_support_verdict_coverage",
            "stakeholder": "Omar Khattab / Jerry Liu",
            "passed": verdict_coverage_passed,
            "summary": "Support-judge fixtures cover every governed verdict class.",
            "details": {
                "expected_verdicts": expected_verdicts,
                "required_verdicts": required_verdicts,
                "missing_verdicts": missing_verdicts,
            },
        },
        {
            "metric_key": "claim_support_eval_auditability",
            "stakeholder": "Luc Moreau / James Cheney",
            "passed": auditability_passed,
            "summary": "The evaluated fixture set and calibration policy are content-addressed.",
            "details": {
                "fixture_set_sha256": fixture_set_sha256,
                "policy_sha256": policy_sha256,
            },
        },
    ]
    if not all(metric["passed"] for metric in success_metrics):
        reasons.extend(metric["summary"] for metric in success_metrics if not metric["passed"])
    summary["gate_outcome"] = "failed" if reasons else "passed"

    return {
        "schema_name": CLAIM_SUPPORT_EVALUATION_SCHEMA_NAME,
        "schema_version": CLAIM_SUPPORT_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": str(evaluation_id),
        "evaluation_name": evaluation_name,
        "fixture_set_id": str(fixture_set_id) if fixture_set_id else None,
        "fixture_set_name": fixture_set_name,
        "fixture_set_version": fixture_set_version,
        "fixture_set_sha256": fixture_set_sha256,
        "policy_id": str(policy_id) if policy_id else None,
        "policy_name": str(policy_payload["policy_name"]),
        "policy_version": str(policy_payload["policy_version"]),
        "policy_sha256": policy_sha256,
        "calibration_policy": policy_payload,
        "judge_name": CLAIM_SUPPORT_JUDGE_NAME,
        "judge_version": CLAIM_SUPPORT_JUDGE_VERSION,
        "thresholds": thresholds,
        "summary": summary,
        "verdict_metrics": verdict_metrics,
        "case_results": case_results,
        "reasons": reasons,
        "success_metrics": success_metrics,
    }


def persist_claim_support_judge_evaluation(
    session: Session,
    evaluation_payload: dict[str, Any],
    *,
    agent_task_id: UUID | None = None,
    operator_run_id: UUID | None = None,
) -> ClaimSupportEvaluation:
    now = utcnow()
    evaluation_id = UUID(str(evaluation_payload["evaluation_id"]))
    payload = {
        **evaluation_payload,
        "operator_run_id": str(operator_run_id) if operator_run_id else None,
    }
    fixture_set_id = (
        UUID(str(payload["fixture_set_id"])) if payload.get("fixture_set_id") else None
    )
    policy_id = UUID(str(payload["policy_id"])) if payload.get("policy_id") else None
    row = ClaimSupportEvaluation(
        id=evaluation_id,
        agent_task_id=agent_task_id,
        operator_run_id=operator_run_id,
        fixture_set_id=fixture_set_id,
        policy_id=policy_id,
        evaluation_name=str(payload["evaluation_name"]),
        fixture_set_name=str(payload["fixture_set_name"]),
        fixture_set_version=payload.get("fixture_set_version"),
        fixture_set_sha256=str(payload["fixture_set_sha256"]),
        policy_name=payload.get("policy_name"),
        policy_version=payload.get("policy_version"),
        policy_sha256=payload.get("policy_sha256"),
        judge_name=str(payload["judge_name"]),
        judge_version=str(payload["judge_version"]),
        min_support_score=float(payload["thresholds"]["min_support_score"]),
        status="completed",
        gate_outcome=str(payload["summary"]["gate_outcome"]),
        thresholds_json=dict(payload["thresholds"]),
        metrics_json=dict(payload["summary"]),
        reasons_json=list(payload.get("reasons") or []),
        evaluation_payload_json=payload,
        evaluation_payload_sha256=str(payload_sha256(payload)),
        created_at=now,
        completed_at=now,
    )
    session.add(row)
    for case_result in payload.get("case_results") or []:
        session.add(
            ClaimSupportEvaluationCase(
                id=uuid.uuid4(),
                evaluation_id=evaluation_id,
                case_index=int(case_result["case_index"]),
                case_id=str(case_result["case_id"]),
                hard_case_kind=case_result.get("hard_case_kind"),
                expected_verdict=str(case_result["expected_verdict"]),
                predicted_verdict=str(case_result["predicted_verdict"]),
                support_score=case_result.get("support_score"),
                passed=bool(case_result["passed"]),
                claim_payload_json=dict(case_result.get("claim_payload") or {}),
                support_judgment_json=dict(case_result.get("support_judgment") or {}),
                failure_reasons_json=list(case_result.get("failure_reasons") or []),
                created_at=now,
            )
        )
    session.flush()
    return row
