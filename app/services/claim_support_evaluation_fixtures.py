from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import ClaimSupportEvaluation, ClaimSupportEvaluationCase, ClaimSupportFixtureSet
from app.services.evidence import payload_sha256

CLAIM_SUPPORT_JUDGE_NAME = "technical_report_claim_support_judge"
CLAIM_SUPPORT_JUDGE_VERSION = "deterministic_claim_support_v1"
CLAIM_SUPPORT_FIXTURE_SET_SCHEMA_NAME = "claim_support_fixture_set"
CLAIM_SUPPORT_FIXTURE_SET_SCHEMA_VERSION = "1.0"
CLAIM_SUPPORT_MINED_FAILURE_MANIFEST_SCHEMA_NAME = "claim_support_mined_failure_manifest"
CLAIM_SUPPORT_MINED_FAILURE_MANIFEST_SCHEMA_VERSION = "1.0"
DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_NAME = "default_claim_support_v1"
DEFAULT_CLAIM_SUPPORT_FIXTURE_SET_VERSION = "v1"
CLAIM_SUPPORT_VERDICTS = ("supported", "unsupported", "insufficient_evidence")
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
    edge_id = "edge:concept:quality_gate:concept:change_window"
    graph_context = [
        {
            "edge_id": edge_id,
            "graph_snapshot_id": _fixture_uuid(case_id, "graph-snapshot"),
            "graph_version": "claim-support-eval-v1",
            "relation_key": "concept_depends_on_concept",
            "relation_label": "Depends On",
            "subject_entity_key": "concept:quality_gate",
            "subject_label": "Quality Gate",
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
            rendered_text="Quality gates depend on change windows.",
            concept_keys=["quality_gate", "change_window"],
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
                rendered_text="Quality gates govern release decisions.",
                concept_keys=["quality_gate", "release_decision"],
                evidence_cards=[
                    _source_card(
                        case_id=supported_case,
                        excerpt=(
                            "Quality gates govern release decisions for "
                            "controlled deployments."
                        ),
                        concept_keys=["quality_gate", "release_decision"],
                        matched_terms=["quality gates", "release decisions"],
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
                rendered_text="Quality gates govern release decisions.",
                concept_keys=["quality_gate", "release_decision"],
                evidence_cards=[
                    _source_card(
                        case_id=weak_case,
                        excerpt=(
                            "Release approvals use quality gate values before "
                            "deployment windows change."
                        ),
                        concept_keys=["quality_gate", "release_decision"],
                        matched_terms=["release approvals", "quality gate"],
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
                rendered_text="Quality gates govern release decisions.",
                concept_keys=["quality_gate", "release_decision"],
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
                rendered_text="Quality gates govern release decisions.",
                concept_keys=["quality_gate", "release_decision"],
                evidence_cards=[
                    _source_card(
                        case_id=contradiction_case,
                        excerpt=(
                            "Quality gates are historical examples and do not "
                            "govern release decisions."
                        ),
                        concept_keys=["quality_gate", "release_decision"],
                        matched_terms=["quality gates", "release decisions"],
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
                rendered_text="Quality gates govern release decisions.",
                concept_keys=["quality_gate", "release_decision"],
                evidence_cards=[],
            ),
        },
        _graph_fixture_case("supported_graph_only"),
    ]


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
    fingerprint_payload = {
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
    }
    payload = {
        **fingerprint_payload,
        "metadata": metadata or {},
    }
    return {**payload, "fixture_set_sha256": str(payload_sha256(fingerprint_payload))}


normalize_string_list = _normalize_string_list
fixture_set_payload = _fixture_set_payload


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


def _fixture_from_fixture_set(
    fixture_set: ClaimSupportFixtureSet | None,
    *,
    case_id: str,
) -> dict[str, Any] | None:
    if fixture_set is None:
        return None
    for fixture in fixture_set.fixtures_json or []:
        if str(fixture.get("case_id") or "") == case_id:
            return deepcopy(fixture)
    return None


def mine_claim_support_failure_fixtures(
    session: Session,
    *,
    limit: int = 20,
    exclude_case_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requested_limit = max(0, min(int(limit), 100))
    seen_case_ids = set(exclude_case_ids or set())
    sources: list[dict[str, Any]] = []
    mined_fixtures: list[dict[str, Any]] = []
    skipped_sources: list[dict[str, Any]] = []
    if requested_limit:
        rows = session.execute(
            select(
                ClaimSupportEvaluationCase,
                ClaimSupportEvaluation,
                ClaimSupportFixtureSet,
            )
            .join(
                ClaimSupportEvaluation,
                ClaimSupportEvaluation.id == ClaimSupportEvaluationCase.evaluation_id,
            )
            .outerjoin(
                ClaimSupportFixtureSet,
                ClaimSupportFixtureSet.id == ClaimSupportEvaluation.fixture_set_id,
            )
            .where(ClaimSupportEvaluationCase.passed.is_(False))
            .order_by(
                ClaimSupportEvaluationCase.created_at.desc(),
                ClaimSupportEvaluationCase.id.desc(),
            )
            .limit(requested_limit * 4)
        ).all()
        for case_row, evaluation_row, fixture_set_row in rows:
            source_case_id = str(case_row.case_id)
            source = {
                "source_evaluation_id": str(evaluation_row.id),
                "source_evaluation_name": evaluation_row.evaluation_name,
                "source_gate_outcome": evaluation_row.gate_outcome,
                "source_agent_task_id": (
                    str(evaluation_row.agent_task_id)
                    if evaluation_row.agent_task_id is not None
                    else None
                ),
                "source_operator_run_id": (
                    str(evaluation_row.operator_run_id)
                    if evaluation_row.operator_run_id is not None
                    else None
                ),
                "source_created_at": evaluation_row.created_at.isoformat(),
                "source_case_row_id": str(case_row.id),
                "source_case_id": source_case_id,
                "case_index": case_row.case_index,
                "source_fixture_set_id": (
                    str(fixture_set_row.id) if fixture_set_row is not None else None
                ),
                "source_fixture_set_name": (
                    fixture_set_row.fixture_set_name if fixture_set_row is not None else None
                ),
                "source_fixture_set_version": (
                    fixture_set_row.fixture_set_version if fixture_set_row is not None else None
                ),
                "source_fixture_set_sha256": (
                    fixture_set_row.fixture_set_sha256 if fixture_set_row is not None else None
                ),
                "source_policy_id": (
                    str(evaluation_row.policy_id) if evaluation_row.policy_id else None
                ),
                "source_policy_name": evaluation_row.policy_name,
                "source_policy_version": evaluation_row.policy_version,
                "source_policy_sha256": evaluation_row.policy_sha256,
                "expected_verdict": case_row.expected_verdict,
                "predicted_verdict": case_row.predicted_verdict,
                "hard_case_kind": case_row.hard_case_kind,
                "support_score": case_row.support_score,
                "failure_reasons": list(case_row.failure_reasons_json or []),
            }
            if source_case_id in seen_case_ids:
                skipped_sources.append({**source, "skip_reason": "duplicate_case_id"})
                continue
            fixture = _fixture_from_fixture_set(fixture_set_row, case_id=source_case_id)
            if fixture is None:
                skipped_sources.append({**source, "skip_reason": "source_fixture_not_found"})
                continue
            if str(fixture.get("expected_verdict") or "") != case_row.expected_verdict:
                skipped_sources.append(
                    {**source, "skip_reason": "source_fixture_verdict_mismatch"}
                )
                continue
            fixture_hard_case_kind = fixture.get("hard_case_kind")
            if (
                fixture_hard_case_kind
                and str(fixture_hard_case_kind) != str(case_row.hard_case_kind or "")
            ):
                skipped_sources.append(
                    {**source, "skip_reason": "source_fixture_hard_case_kind_mismatch"}
                )
                continue
            if not fixture.get("draft_payload"):
                skipped_sources.append({**source, "skip_reason": "missing_draft_payload"})
                continue
            source["source_fixture_sha256"] = str(payload_sha256(fixture))
            fixture["mined_failure_source"] = source
            mined_fixtures.append(fixture)
            sources.append(source)
            seen_case_ids.add(source_case_id)
            if len(mined_fixtures) >= requested_limit:
                break

    manifest_basis = {
        "schema_name": CLAIM_SUPPORT_MINED_FAILURE_MANIFEST_SCHEMA_NAME,
        "schema_version": CLAIM_SUPPORT_MINED_FAILURE_MANIFEST_SCHEMA_VERSION,
        "requested_limit": requested_limit,
        "mined_failure_case_count": len(mined_fixtures),
        "skipped_source_count": len(skipped_sources),
        "sources": sources,
        "skipped_sources": skipped_sources,
    }
    return mined_fixtures, {
        **manifest_basis,
        "manifest_sha256": str(payload_sha256(manifest_basis)),
    }
