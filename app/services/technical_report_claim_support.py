from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from app.core.coercion import unique_strings as _unique_strings
from app.core.hashes import payload_sha256 as _payload_sha256
from app.schemas.agent_task_reports import TechnicalReportDraftPayload

CLAIM_SUPPORT_VERDICTS = {"supported", "unsupported", "insufficient_evidence"}
_CLAIM_SUPPORT_JUDGE_SCHEMA_NAME = "technical_report_claim_support_judgment"
_CLAIM_SUPPORT_JUDGE_SCHEMA_VERSION = "1.0"
_CLAIM_SUPPORT_JUDGE_KIND = "deterministic_claim_support_v1"
_CLAIM_SUPPORT_TOKEN_RE = re.compile(r"[a-z0-9]+")
_CLAIM_SUPPORT_CONTRADICTION_PHRASES = (
    "does not",
    "do not",
    "is not",
    "are not",
    "not supported",
    "not evidence",
    "unrelated",
    "contradicts",
)
_CLAIM_SUPPORT_STOPWORDS = {
    "about",
    "above",
    "after",
    "against",
    "also",
    "and",
    "are",
    "because",
    "between",
    "but",
    "can",
    "claim",
    "could",
    "does",
    "from",
    "has",
    "have",
    "into",
    "its",
    "may",
    "must",
    "not",
    "only",
    "or",
    "over",
    "per",
    "report",
    "shall",
    "should",
    "than",
    "that",
    "the",
    "their",
    "there",
    "this",
    "through",
    "under",
    "use",
    "uses",
    "using",
    "with",
    "within",
}


def _support_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, default=str)


def _support_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = _support_text(value).replace("_", " ").replace("-", " ").lower()
        for token in _CLAIM_SUPPORT_TOKEN_RE.findall(text):
            if len(token) < 3 or token in _CLAIM_SUPPORT_STOPWORDS:
                continue
            tokens.add(token)
            if token.endswith("s") and len(token) > 4:
                tokens.add(token[:-1])
    return tokens


def _evidence_card_support_parts(card: dict[str, Any]) -> list[Any]:
    metadata = dict(card.get("metadata") or {})
    return [
        card.get("evidence_card_id"),
        card.get("evidence_kind"),
        card.get("source_type"),
        card.get("source_locator"),
        card.get("citation_label"),
        card.get("source_filename"),
        card.get("excerpt"),
        card.get("concept_keys"),
        card.get("support_level"),
        card.get("review_status"),
        card.get("relation_key"),
        card.get("source_evidence_match_keys"),
        card.get("source_evidence_match_status"),
        metadata.get("matched_terms"),
        metadata.get("source_record_keys"),
        metadata.get("relation_label"),
        metadata.get("object_label"),
        metadata.get("subject_label"),
    ]


def _graph_edge_support_parts(edge: Any) -> list[Any]:
    return [
        edge.edge_id,
        edge.relation_key,
        edge.relation_label,
        edge.subject_entity_key,
        edge.subject_label,
        edge.object_entity_key,
        edge.object_label,
        edge.review_status,
        edge.support_level,
        edge.support_ref_ids,
    ]


def _has_support_contradiction_cue(*values: Any) -> bool:
    text = " ".join(_support_text(value).lower() for value in values if value is not None)
    return any(phrase in text for phrase in _CLAIM_SUPPORT_CONTRADICTION_PHRASES)


def claim_support_judgment_contract_mismatches(
    claim,
    *,
    min_claim_support_score: float,
) -> list[str]:
    judgment = dict(claim.support_judgment or {})
    if not judgment:
        return ["support_judgment"]
    mismatches: list[str] = []
    if judgment.get("schema_name") != _CLAIM_SUPPORT_JUDGE_SCHEMA_NAME:
        mismatches.append("schema_name")
    if judgment.get("schema_version") != _CLAIM_SUPPORT_JUDGE_SCHEMA_VERSION:
        mismatches.append("schema_version")
    if judgment.get("judge_kind") != _CLAIM_SUPPORT_JUDGE_KIND:
        mismatches.append("judge_kind")
    if str(judgment.get("claim_id") or "") != claim.claim_id:
        mismatches.append("claim_id")
    if judgment.get("verdict") != claim.support_verdict:
        mismatches.append("verdict")
    try:
        judgment_score = float(judgment.get("support_score"))
    except (TypeError, ValueError):
        mismatches.append("support_score")
    else:
        if claim.support_score is None or abs(judgment_score - claim.support_score) > 0.0001:
            mismatches.append("support_score")
    if (
        "min_support_score" in judgment
        and float(judgment.get("min_support_score") or 0.0) != min_claim_support_score
    ):
        mismatches.append("min_support_score")
    if _unique_strings(
        [str(value) for value in (judgment.get("source_search_request_result_ids") or [])]
    ) != [str(value) for value in claim.source_search_request_result_ids]:
        mismatches.append("source_search_request_result_ids")
    if sorted(
        _unique_strings([str(value) for value in (judgment.get("evidence_card_ids") or [])])
    ) != sorted([str(value) for value in claim.evidence_card_ids]):
        mismatches.append("evidence_card_ids")
    if sorted(
        _unique_strings([str(value) for value in (judgment.get("graph_edge_ids") or [])])
    ) != sorted([str(value) for value in claim.graph_edge_ids]):
        mismatches.append("graph_edge_ids")
    return mismatches


def judge_technical_report_claim_support(
    draft_payload: dict[str, Any],
    *,
    min_claim_support_score: float = 0.34,
) -> dict[str, Any]:
    """Deterministically score each rendered claim against its frozen support refs."""

    draft = TechnicalReportDraftPayload.model_validate(draft_payload)
    cards_by_id = {
        card.evidence_card_id: card.model_dump(mode="json") for card in draft.evidence_cards
    }
    graph_edges_by_id = {edge.edge_id: edge for edge in draft.graph_context}
    claim_judgments: list[dict[str, Any]] = []

    for claim in draft.claims:
        resolved_cards = [
            cards_by_id[card_id] for card_id in claim.evidence_card_ids if card_id in cards_by_id
        ]
        graph_refs = [
            graph_edges_by_id[edge_id]
            for edge_id in claim.graph_edge_ids
            if edge_id in graph_edges_by_id
        ]
        graph_approved = bool(graph_refs) and all(
            edge.review_status == "approved" for edge in graph_refs
        )
        source_search_result_ids = _unique_strings(
            [
                *[str(value) for value in claim.source_search_request_result_ids],
                *[
                    str(value)
                    for card in resolved_cards
                    for value in (card.get("source_search_request_result_ids") or [])
                ],
            ]
        )
        claim_tokens = _support_tokens(claim.rendered_text, claim.concept_keys)
        evidence_tokens = _support_tokens(
            *[part for card in resolved_cards for part in _evidence_card_support_parts(card)],
            *[part for edge in graph_refs for part in _graph_edge_support_parts(edge)],
        )
        matched_tokens = sorted(claim_tokens.intersection(evidence_tokens))
        lexical_overlap_ratio = len(matched_tokens) / len(claim_tokens) if claim_tokens else 0.0
        score = 0.0
        reasons: list[str] = []
        unsupported_reasons: list[str] = []
        evidence_parts = [
            part for card in resolved_cards for part in _evidence_card_support_parts(card)
        ]
        graph_parts = [part for edge in graph_refs for part in _graph_edge_support_parts(edge)]
        has_contradiction_cue = _has_support_contradiction_cue(*evidence_parts, *graph_parts)
        if resolved_cards:
            score = max(score, 0.15)
            reasons.append("resolved_evidence_cards")
        if source_search_result_ids:
            score = min(1.0, score + 0.1)
            reasons.append("source_search_results_present")
        elif resolved_cards:
            unsupported_reasons.append("missing_source_search_results")
        if graph_approved:
            score = max(score, 0.72)
            reasons.append("approved_graph_edges")
        elif graph_refs:
            unsupported_reasons.append("graph_edges_not_approved")
        if claim.fact_ids or claim.assertion_ids:
            score = min(1.0, score + 0.1)
            reasons.append("semantic_fact_or_assertion_refs")
        if matched_tokens:
            score = min(1.0, score + min(0.65, lexical_overlap_ratio * 0.65))
            reasons.append("claim_terms_overlap_evidence")
        if has_contradiction_cue:
            score = min(score, 0.2)
            unsupported_reasons.append("evidence_contains_contradiction_cue")

        if not resolved_cards and not graph_refs:
            verdict = "insufficient_evidence"
            unsupported_reasons.append("no_traceable_evidence_refs")
        elif resolved_cards and not source_search_result_ids:
            verdict = "insufficient_evidence"
        elif has_contradiction_cue:
            verdict = "unsupported"
        elif resolved_cards and not matched_tokens and not graph_approved:
            verdict = "unsupported"
            unsupported_reasons.append("no_claim_terms_overlap_evidence")
        elif score < min_claim_support_score:
            verdict = "unsupported"
            unsupported_reasons.append("support_score_below_threshold")
        else:
            verdict = "supported"

        judgment = {
            "schema_name": _CLAIM_SUPPORT_JUDGE_SCHEMA_NAME,
            "schema_version": _CLAIM_SUPPORT_JUDGE_SCHEMA_VERSION,
            "judge_kind": _CLAIM_SUPPORT_JUDGE_KIND,
            "claim_id": claim.claim_id,
            "verdict": verdict,
            "support_score": round(score, 4),
            "min_support_score": min_claim_support_score,
            "evidence_card_ids": list(claim.evidence_card_ids),
            "resolved_evidence_card_ids": [
                str(card.get("evidence_card_id")) for card in resolved_cards
            ],
            "graph_edge_ids": list(claim.graph_edge_ids),
            "resolved_graph_edge_ids": [edge.edge_id for edge in graph_refs],
            "source_search_request_result_ids": source_search_result_ids,
            "matched_claim_tokens": matched_tokens[:50],
            "matched_claim_token_count": len(matched_tokens),
            "claim_token_count": len(claim_tokens),
            "lexical_overlap_ratio": round(lexical_overlap_ratio, 4),
            "support_reasons": _unique_strings(reasons),
            "unsupported_reasons": _unique_strings(unsupported_reasons),
            "provisional_rule": (
                "Deterministic v1 support scoring; replaceable by learned or "
                "model-based judges while preserving this persisted contract."
            ),
        }
        claim_judgments.append(judgment)

    supported_count = sum(1 for row in claim_judgments if row["verdict"] == "supported")
    return {
        "schema_name": "technical_report_claim_support_judgments",
        "schema_version": "1.0",
        "judge_kind": _CLAIM_SUPPORT_JUDGE_KIND,
        "min_support_score": min_claim_support_score,
        "claim_count": len(claim_judgments),
        "supported_claim_count": supported_count,
        "unsupported_claim_count": sum(
            1 for row in claim_judgments if row["verdict"] == "unsupported"
        ),
        "insufficient_evidence_claim_count": sum(
            1 for row in claim_judgments if row["verdict"] == "insufficient_evidence"
        ),
        "claim_judgments": claim_judgments,
    }


def apply_technical_report_claim_support_judgments(
    draft_payload: dict[str, Any],
    support_judgments_payload: dict[str, Any],
    *,
    support_judge_run_id: UUID | str | None,
) -> dict[str, Any]:
    judgments_by_claim_id = {
        str(row.get("claim_id")): row
        for row in support_judgments_payload.get("claim_judgments") or []
        if row.get("claim_id")
    }
    support_judge_run_id_text = str(support_judge_run_id) if support_judge_run_id else None
    support_judgment_sha256s: list[str] = []
    supported_count = 0
    unsupported_count = 0
    insufficient_count = 0

    for claim in draft_payload.get("claims") or []:
        judgment = judgments_by_claim_id.get(str(claim.get("claim_id")))
        if not judgment:
            continue
        judgment_hash = _payload_sha256(judgment)
        claim["support_verdict"] = judgment.get("verdict")
        claim["support_score"] = judgment.get("support_score")
        claim["support_judge_run_id"] = support_judge_run_id_text
        claim["support_judgment"] = dict(judgment)
        claim["support_judgment_sha256"] = judgment_hash
        support_judgment_sha256s.append(judgment_hash)
        if judgment.get("verdict") == "supported":
            supported_count += 1
        elif judgment.get("verdict") == "unsupported":
            unsupported_count += 1
        elif judgment.get("verdict") == "insufficient_evidence":
            insufficient_count += 1

    claim_count = len(draft_payload.get("claims") or [])
    draft_payload["support_judge_run_id"] = support_judge_run_id_text
    draft_payload["support_judgment_sha256s"] = _unique_strings(support_judgment_sha256s)
    draft_payload["claim_support_summary"] = {
        "schema_name": "technical_report_claim_support_summary",
        "schema_version": "1.0",
        "judge_kind": support_judgments_payload.get("judge_kind"),
        "support_judge_run_id": support_judge_run_id_text,
        "min_support_score": support_judgments_payload.get("min_support_score"),
        "claim_count": claim_count,
        "claims_with_support_judgment_count": len(support_judgment_sha256s),
        "supported_claim_count": supported_count,
        "unsupported_claim_count": unsupported_count,
        "insufficient_evidence_claim_count": insufficient_count,
    }
    return draft_payload
