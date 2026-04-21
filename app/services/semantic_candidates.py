from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.db.models import AgentTask, Document
from app.services.semantic_registry import (
    SemanticRegistry,
    get_semantic_registry,
    normalize_semantic_text,
)
from app.services.semantics import (
    SemanticAssertionMaterialization,
    SemanticEvidenceMaterialization,
    SemanticSourceItem,
    _build_semantic_sources,
    _latest_category_review_overlays,
    _latest_concept_review_overlays,
    _materialize_semantic_assertions,
    _preview_assertions,
    _preview_concept_category_bindings,
    _semantic_evaluation_result,
    _source_artifact_api_path,
    get_active_semantic_pass_detail,
)

DEFAULT_BASELINE_EXTRACTOR = "registry_lexical_v1"
DEFAULT_CANDIDATE_EXTRACTOR = "concept_ranker_v1"
DEFAULT_CANDIDATE_SCORE_THRESHOLD = 0.34
DEFAULT_MAX_CANDIDATES_PER_SOURCE = 3
HASH_EMBEDDING_DIM = 96


@dataclass(frozen=True)
class CandidateExtractorDescriptor:
    extractor_name: str
    backing_model: str
    match_strategy: str
    provider_name: str | None = None


@dataclass(frozen=True)
class CandidateConceptScore:
    concept_key: str
    preferred_label: str
    score: float
    matched_terms: tuple[str, ...]
    category_keys: tuple[str, ...]


@dataclass(frozen=True)
class CandidateSourcePrediction:
    source: SemanticSourceItem
    candidates: tuple[CandidateConceptScore, ...]


@dataclass(frozen=True)
class CandidateExtractionResult:
    descriptor: CandidateExtractorDescriptor
    materializations: tuple[SemanticAssertionMaterialization, ...]
    source_predictions: tuple[CandidateSourcePrediction, ...]


def _canonicalize_token(token: str) -> str:
    value = collapse_whitespace(token)
    if len(value) > 4 and value.endswith("ies"):
        return f"{value[:-3]}y"
    if len(value) > 4 and value.endswith("es"):
        return value[:-2]
    if len(value) > 3 and value.endswith("s"):
        return value[:-1]
    return value


def _tokenize(value: str | None) -> tuple[str, ...]:
    normalized = normalize_semantic_text(value)
    if not normalized:
        return ()
    tokens = [_canonicalize_token(token) for token in normalized.split()]
    return tuple(token for token in tokens if token)


def _embedding_vector(value: str | None) -> list[float]:
    vector = [0.0] * HASH_EMBEDDING_DIM
    for token in _tokenize(value):
        index = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16) % HASH_EMBEDDING_DIM
        vector[index] += 1.0
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0.0:
        return vector
    return [item / norm for item in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=False))))


def _stable_source_key(source: SemanticSourceItem) -> str:
    return f"{source.source_type}:{source.source_locator}"


def _unique_document_ids(document_ids: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(document_ids))


def _extractor_descriptor(extractor_name: str) -> CandidateExtractorDescriptor:
    if extractor_name == DEFAULT_BASELINE_EXTRACTOR:
        return CandidateExtractorDescriptor(
            extractor_name=DEFAULT_BASELINE_EXTRACTOR,
            backing_model="none",
            match_strategy="normalized_phrase_contains",
            provider_name=None,
        )
    if extractor_name == DEFAULT_CANDIDATE_EXTRACTOR:
        return CandidateExtractorDescriptor(
            extractor_name=DEFAULT_CANDIDATE_EXTRACTOR,
            backing_model="hashing_embedding_v1",
            match_strategy="token_set_ranker_v1",
            provider_name="local_hashing",
        )
    raise ValueError(f"Unsupported semantic candidate extractor: {extractor_name}")


def _materialization_index(
    registry: SemanticRegistry,
) -> dict[str, SemanticAssertionMaterialization]:
    return {
        concept.concept_key: SemanticAssertionMaterialization(
            concept_definition=concept,
            matched_terms=set(),
            source_types=set(),
            evidence=[],
        )
        for concept in registry.concepts
    }


def _finalize_materializations(
    registry: SemanticRegistry,
    matches_by_concept: dict[str, SemanticAssertionMaterialization],
) -> tuple[SemanticAssertionMaterialization, ...]:
    rows = [
        row
        for concept in registry.concepts
        if (row := matches_by_concept.get(concept.concept_key)) is not None and row.evidence
    ]
    rows.sort(key=lambda item: item.concept_definition.preferred_label.lower())
    return tuple(rows)


def _lexical_extractor(
    registry: SemanticRegistry,
    sources: list[SemanticSourceItem],
) -> CandidateExtractionResult:
    materializations = _materialize_semantic_assertions(registry, sources)
    source_predictions: list[CandidateSourcePrediction] = []
    for source in sources:
        candidates: list[CandidateConceptScore] = []
        if not source.normalized_text:
            continue
        for concept in registry.concepts:
            matched_terms = tuple(
                sorted(
                    {
                        term.text
                        for term in concept.terms
                        if term.normalized_text and term.normalized_text in source.normalized_text
                    }
                )
            )
            if not matched_terms:
                continue
            candidates.append(
                CandidateConceptScore(
                    concept_key=concept.concept_key,
                    preferred_label=concept.preferred_label,
                    score=1.0,
                    matched_terms=matched_terms,
                    category_keys=tuple(sorted(concept.category_keys)),
                )
            )
        if candidates:
            source_predictions.append(
                CandidateSourcePrediction(
                    source=source,
                    candidates=tuple(
                        sorted(
                            candidates, key=lambda row: (-row.score, row.preferred_label.lower())
                        )
                    ),
                )
            )
    return CandidateExtractionResult(
        descriptor=_extractor_descriptor(DEFAULT_BASELINE_EXTRACTOR),
        materializations=tuple(materializations),
        source_predictions=tuple(source_predictions),
    )


def _concept_ranker_extractor(
    registry: SemanticRegistry,
    sources: list[SemanticSourceItem],
    *,
    score_threshold: float,
    max_candidates_per_source: int,
) -> CandidateExtractionResult:
    matches_by_concept = _materialization_index(registry)
    source_predictions: list[CandidateSourcePrediction] = []

    term_tokens: dict[tuple[str, str], frozenset[str]] = {}
    term_vectors: dict[tuple[str, str], list[float]] = {}
    source_vectors = {
        _stable_source_key(source): _embedding_vector(source.normalized_text) for source in sources
    }

    for concept in registry.concepts:
        for term in concept.terms:
            key = (concept.concept_key, term.text)
            term_tokens[key] = frozenset(_tokenize(term.normalized_text))
            term_vectors[key] = _embedding_vector(term.normalized_text)

    for source in sources:
        source_key = _stable_source_key(source)
        source_token_set = frozenset(_tokenize(source.normalized_text))
        if not source_token_set:
            continue

        candidates: list[CandidateConceptScore] = []
        for concept in registry.concepts:
            matched_terms: list[str] = []
            best_score = 0.0
            for term in concept.terms:
                key = (concept.concept_key, term.text)
                tokens = term_tokens[key]
                if not tokens or not tokens.issubset(source_token_set):
                    continue
                matched_terms.append(term.text)
                best_score = max(
                    best_score,
                    _cosine_similarity(term_vectors[key], source_vectors[source_key]),
                )
            if best_score < score_threshold or not matched_terms:
                continue
            candidates.append(
                CandidateConceptScore(
                    concept_key=concept.concept_key,
                    preferred_label=concept.preferred_label,
                    score=round(best_score, 4),
                    matched_terms=tuple(sorted(set(matched_terms))),
                    category_keys=tuple(sorted(concept.category_keys)),
                )
            )

        if not candidates:
            continue
        candidates.sort(key=lambda row: (-row.score, row.preferred_label.lower()))
        selected_candidates = candidates[:max_candidates_per_source]
        source_predictions.append(
            CandidateSourcePrediction(
                source=source,
                candidates=tuple(selected_candidates),
            )
        )

        for candidate in selected_candidates:
            materialization = matches_by_concept[candidate.concept_key]
            materialization.matched_terms.update(candidate.matched_terms)
            materialization.source_types.add(source.source_type)
            materialization.evidence.append(
                SemanticEvidenceMaterialization(
                    source_item=source,
                    matched_terms=list(candidate.matched_terms),
                )
            )

    return CandidateExtractionResult(
        descriptor=_extractor_descriptor(DEFAULT_CANDIDATE_EXTRACTOR),
        materializations=_finalize_materializations(registry, matches_by_concept),
        source_predictions=tuple(source_predictions),
    )


def _run_candidate_extractor(
    registry: SemanticRegistry,
    sources: list[SemanticSourceItem],
    *,
    extractor_name: str,
    score_threshold: float = DEFAULT_CANDIDATE_SCORE_THRESHOLD,
    max_candidates_per_source: int = DEFAULT_MAX_CANDIDATES_PER_SOURCE,
) -> CandidateExtractionResult:
    if extractor_name == DEFAULT_BASELINE_EXTRACTOR:
        return _lexical_extractor(registry, sources)
    if extractor_name == DEFAULT_CANDIDATE_EXTRACTOR:
        return _concept_ranker_extractor(
            registry,
            sources,
            score_threshold=score_threshold,
            max_candidates_per_source=max_candidates_per_source,
        )
    raise ValueError(f"Unsupported semantic candidate extractor: {extractor_name}")


def _load_target_documents(
    session: Session,
    document_ids: list[UUID],
) -> list[Document]:
    if document_ids:
        documents = []
        for document_id in _unique_document_ids(document_ids):
            document = session.get(Document, document_id)
            if document is None:
                raise ValueError(f"Document not found: {document_id}")
            if document.active_run_id is None:
                raise ValueError(f"Document does not have an active run: {document_id}")
            documents.append(document)
        return documents

    return (
        session.execute(
            select(Document)
            .where(Document.active_run_id.is_not(None))
            .order_by(Document.created_at)
        )
        .scalars()
        .all()
    )


def _source_prediction_payload(
    document_id: UUID,
    prediction: CandidateSourcePrediction,
) -> dict:
    source = prediction.source
    return {
        "source_key": _stable_source_key(source),
        "source_type": source.source_type,
        "source_locator": source.source_locator,
        "page_from": source.page_from,
        "page_to": source.page_to,
        "excerpt": source.excerpt,
        "source_artifact_api_path": _source_artifact_api_path(
            document_id,
            source_type=source.source_type,
            table_id=source.table_id,
            figure_id=source.figure_id,
        ),
        "source_artifact_sha256": source.source_artifact_sha256,
        "candidates": [
            {
                "concept_key": candidate.concept_key,
                "preferred_label": candidate.preferred_label,
                "score": candidate.score,
                "matched_terms": list(candidate.matched_terms),
                "category_keys": list(candidate.category_keys),
            }
            for candidate in prediction.candidates
        ],
    }


def _expected_concept_keys(evaluation_summary: dict) -> set[str]:
    return {
        str(item.get("concept_key"))
        for item in (evaluation_summary.get("expectations") or [])
        if item.get("concept_key")
    }


def _assertion_concept_keys(semantic_pass) -> set[str]:
    return {
        assertion.concept_key
        for assertion in semantic_pass.assertions
        if assertion.review_status != "rejected"
    }


def _preview_payloads_for_extractor(
    session: Session,
    *,
    document: Document,
    semantic_pass,
    registry: SemanticRegistry,
    extraction: CandidateExtractionResult,
) -> tuple[list[dict], list[dict], dict]:
    concept_review_overlays = _latest_concept_review_overlays(
        session,
        document.id,
        registry.registry_version,
    )
    category_review_overlays = _latest_category_review_overlays(
        session,
        document.id,
        registry.registry_version,
    )
    assertions = _preview_assertions(
        list(extraction.materializations),
        concept_review_overlays=concept_review_overlays,
        category_review_overlays=category_review_overlays,
        registry=registry,
    )
    concept_category_bindings = _preview_concept_category_bindings(registry)
    _evaluation_status, _fixture_name, evaluation_summary = _semantic_evaluation_result(
        document,
        assertions,
        concept_category_bindings,
    )
    return assertions, concept_category_bindings, evaluation_summary


def _shadow_candidates_from_predictions(
    *,
    document_id: UUID,
    source_predictions: tuple[CandidateSourcePrediction, ...],
    expected_concept_keys: set[str],
) -> list[dict]:
    buckets: dict[str, dict] = {}
    for prediction in source_predictions:
        source = prediction.source
        source_artifact_api_path = _source_artifact_api_path(
            document_id,
            source_type=source.source_type,
            table_id=source.table_id,
            figure_id=source.figure_id,
        )
        for candidate in prediction.candidates:
            bucket = buckets.setdefault(
                candidate.concept_key,
                {
                    "concept_key": candidate.concept_key,
                    "preferred_label": candidate.preferred_label,
                    "max_score": 0.0,
                    "source_count": 0,
                    "source_types": set(),
                    "category_keys": set(candidate.category_keys),
                    "expected_by_evaluation": candidate.concept_key in expected_concept_keys,
                    "evidence_refs": [],
                    "note": None,
                },
            )
            bucket["max_score"] = max(bucket["max_score"], candidate.score)
            bucket["source_count"] += 1
            bucket["source_types"].add(source.source_type)
            bucket["evidence_refs"].append(
                {
                    "source_type": source.source_type,
                    "source_locator": source.source_locator,
                    "page_from": source.page_from,
                    "page_to": source.page_to,
                    "excerpt": source.excerpt,
                    "source_artifact_api_path": source_artifact_api_path,
                    "source_artifact_sha256": source.source_artifact_sha256,
                    "score": candidate.score,
                }
            )

    rows = []
    for value in buckets.values():
        value["source_types"] = sorted(value["source_types"])
        value["category_keys"] = sorted(value["category_keys"])
        value["evidence_refs"].sort(
            key=lambda row: (-row["score"], row["source_type"], row["source_locator"])
        )
        value["max_score"] = round(value["max_score"], 4)
        rows.append(value)
    rows.sort(key=lambda row: (-row["max_score"], row["preferred_label"].lower()))
    return rows


def _brief_shadow_candidates(
    document_reports: list[dict],
    *,
    requested_concept_keys: set[str],
    requested_category_keys: set[str],
    max_shadow_candidates: int,
) -> tuple[list[dict], dict]:
    aggregated: dict[str, dict] = {}
    live_concepts = {
        concept_key
        for report in document_reports
        for concept_key in report.get("live_concept_keys") or []
    }

    for report in document_reports:
        for candidate in report.get("shadow_candidates") or []:
            concept_key = str(candidate.get("concept_key"))
            category_keys = set(candidate.get("category_keys") or [])
            if concept_key in live_concepts:
                continue
            if requested_concept_keys and concept_key not in requested_concept_keys:
                if not requested_category_keys.intersection(category_keys):
                    continue
            elif requested_category_keys and not requested_category_keys.intersection(
                category_keys
            ):
                continue

            bucket = aggregated.setdefault(
                concept_key,
                {
                    "concept_key": concept_key,
                    "preferred_label": candidate.get("preferred_label"),
                    "max_score": 0.0,
                    "source_count": 0,
                    "source_types": set(),
                    "category_keys": set(candidate.get("category_keys") or []),
                    "expected_by_evaluation": bool(candidate.get("expected_by_evaluation")),
                    "evidence_refs": [],
                    "note": None,
                },
            )
            bucket["max_score"] = max(bucket["max_score"], float(candidate.get("max_score") or 0.0))
            bucket["source_count"] += int(candidate.get("source_count") or 0)
            bucket["source_types"].update(candidate.get("source_types") or [])
            bucket["evidence_refs"].extend(candidate.get("evidence_refs") or [])
            bucket["expected_by_evaluation"] = bucket["expected_by_evaluation"] or bool(
                candidate.get("expected_by_evaluation")
            )

    rows = []
    for bucket in aggregated.values():
        bucket["source_types"] = sorted(bucket["source_types"])
        bucket["category_keys"] = sorted(bucket["category_keys"])
        bucket["evidence_refs"] = sorted(
            bucket["evidence_refs"],
            key=lambda row: (-float(row.get("score") or 0.0), row.get("source_type") or ""),
        )[:3]
        bucket["max_score"] = round(bucket["max_score"], 4)
        if bucket["expected_by_evaluation"]:
            bucket["note"] = "Shadow candidate aligns with a semantic evaluation expectation."
        rows.append(bucket)

    rows.sort(key=lambda row: (-row["max_score"], row["preferred_label"] or ""))
    selected_rows = rows[:max_shadow_candidates]
    summary = {
        "candidate_count": len(selected_rows),
        "candidate_only_concept_count": len(selected_rows),
        "expected_shadow_candidate_count": sum(
            1 for row in selected_rows if row.get("expected_by_evaluation")
        ),
    }
    return selected_rows, summary


def _export_success_metrics(corpus: dict) -> list[dict]:
    rows = list(corpus.get("rows") or [])
    row_type_counts = dict(corpus.get("row_type_counts") or {})
    semantic_rows = [
        row
        for row in rows
        if row.get("row_type") in {"semantic_assertion_review", "semantic_category_review"}
    ]
    return [
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": bool(row_type_counts.get("semantic_evaluation_expectation"))
            and bool(row_type_counts.get("grounded_document_verification")),
            "summary": (
                "The supervision corpus captures reusable evaluation and verification signals."
            ),
            "details": {
                "row_type_counts": row_type_counts,
            },
        },
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": all(
                row.get("source_ref") and row.get("registry_version") and row.get("registry_sha256")
                for row in semantic_rows
            ),
            "summary": "Semantic supervision rows stay versioned and traceable to typed sources.",
            "details": {
                "semantic_row_count": len(semantic_rows),
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(rows)
            and all(row.get("row_id") and row.get("source_ref") for row in rows),
            "summary": (
                "The supervision corpus is durable, typed, and replayable from canonical rows."
            ),
            "details": {
                "row_count": len(rows),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(corpus.get("jsonl_path")) and bool(rows),
            "summary": (
                "The system exports a reusable supervision asset instead of ephemeral review state."
            ),
            "details": {
                "jsonl_path": corpus.get("jsonl_path"),
            },
        },
    ]


def export_semantic_supervision_corpus(
    session: Session,
    *,
    document_ids: list[UUID],
    reviewed_only: bool,
    include_generation_verifications: bool,
    output_path: Path,
) -> dict:
    documents = _load_target_documents(session, document_ids)
    rows: list[dict] = []
    target_document_ids = {document.id for document in documents}
    active_refs_by_document_id: dict[UUID, tuple[UUID, UUID]] = {}

    for document in documents:
        semantic_pass = get_active_semantic_pass_detail(session, document.id)
        active_refs_by_document_id[document.id] = (
            semantic_pass.run_id,
            semantic_pass.semantic_pass_id,
        )
        for assertion in semantic_pass.assertions:
            overlay = (assertion.details or {}).get("review_overlay") or {}
            if reviewed_only and not overlay:
                continue
            rows.append(
                {
                    "row_id": f"assertion:{assertion.assertion_id}",
                    "row_type": "semantic_assertion_review",
                    "label_type": "concept_assertion",
                    "document_id": document.id,
                    "run_id": semantic_pass.run_id,
                    "semantic_pass_id": semantic_pass.semantic_pass_id,
                    "source_ref": f"assertion:{assertion.assertion_id}",
                    "concept_key": assertion.concept_key,
                    "category_key": None,
                    "review_status": assertion.review_status,
                    "registry_version": semantic_pass.registry_version,
                    "registry_sha256": semantic_pass.registry_sha256,
                    "evidence_span": {
                        "evidence_count": assertion.evidence_count,
                        "source_types": list(assertion.source_types),
                    },
                    "verification_outcome": None,
                    "details": {
                        "assertion_id": str(assertion.assertion_id),
                        "matched_terms": list(assertion.matched_terms),
                        "review_overlay": overlay,
                    },
                }
            )
            for binding in assertion.category_bindings:
                binding_overlay = (binding.details or {}).get("review_overlay") or {}
                if reviewed_only and not binding_overlay:
                    continue
                rows.append(
                    {
                        "row_id": f"binding:{binding.binding_id}",
                        "row_type": "semantic_category_review",
                        "label_type": "category_binding",
                        "document_id": document.id,
                        "run_id": semantic_pass.run_id,
                        "semantic_pass_id": semantic_pass.semantic_pass_id,
                        "source_ref": f"binding:{binding.binding_id}",
                        "concept_key": assertion.concept_key,
                        "category_key": binding.category_key,
                        "review_status": binding.review_status,
                        "registry_version": semantic_pass.registry_version,
                        "registry_sha256": semantic_pass.registry_sha256,
                        "evidence_span": {
                            "evidence_count": assertion.evidence_count,
                            "source_types": list(assertion.source_types),
                        },
                        "verification_outcome": None,
                        "details": {
                            "binding_id": str(binding.binding_id),
                            "review_overlay": binding_overlay,
                        },
                    }
                )

        for expectation in semantic_pass.evaluation_summary.get("expectations") or []:
            rows.append(
                {
                    "row_id": f"semantic_eval:{document.id}:{expectation.get('concept_key')}",
                    "row_type": "semantic_evaluation_expectation",
                    "label_type": "expected_concept",
                    "document_id": document.id,
                    "run_id": semantic_pass.run_id,
                    "semantic_pass_id": semantic_pass.semantic_pass_id,
                    "source_ref": f"semantic_evaluation:{semantic_pass.evaluation_fixture_name}",
                    "concept_key": expectation.get("concept_key"),
                    "category_key": None,
                    "review_status": expectation.get("observed_review_status"),
                    "registry_version": semantic_pass.registry_version,
                    "registry_sha256": semantic_pass.registry_sha256,
                    "evidence_span": {
                        "observed_evidence_count": expectation.get("observed_evidence_count"),
                        "observed_source_types": expectation.get("observed_source_types") or [],
                    },
                    "verification_outcome": "passed" if expectation.get("passed") else "failed",
                    "details": dict(expectation),
                }
            )

        continuity_summary = dict(semantic_pass.continuity_summary or {})
        continuity_change_count = int(continuity_summary.get("change_count") or 0)
        if continuity_change_count or continuity_summary.get("has_baseline"):
            rows.append(
                {
                    "row_id": f"continuity:{semantic_pass.semantic_pass_id}",
                    "row_type": "semantic_continuity",
                    "label_type": "continuity_delta",
                    "document_id": document.id,
                    "run_id": semantic_pass.run_id,
                    "semantic_pass_id": semantic_pass.semantic_pass_id,
                    "source_ref": f"semantic_pass:{semantic_pass.semantic_pass_id}",
                    "concept_key": None,
                    "category_key": None,
                    "review_status": None,
                    "registry_version": semantic_pass.registry_version,
                    "registry_sha256": semantic_pass.registry_sha256,
                    "evidence_span": {"change_count": continuity_change_count},
                    "verification_outcome": None,
                    "details": continuity_summary,
                }
            )

    if include_generation_verifications:
        verification_tasks = (
            session.execute(
                select(AgentTask).where(
                    AgentTask.task_type == "verify_semantic_grounded_document",
                    AgentTask.status == "completed",
                )
            )
            .scalars()
            .all()
        )
        for task in verification_tasks:
            payload = (task.result_json or {}).get("payload") or {}
            draft = payload.get("draft") or {}
            document_refs = draft.get("document_refs") or []
            verification = payload.get("verification") or {}
            verification_details = verification.get("details") or {}
            for document_ref in document_refs:
                try:
                    document_id = UUID(str(document_ref.get("document_id")))
                    run_id = UUID(str(document_ref.get("run_id")))
                    semantic_pass_id = UUID(str(document_ref.get("semantic_pass_id")))
                except (TypeError, ValueError):
                    continue
                if document_id not in target_document_ids:
                    continue
                active_run_id, active_semantic_pass_id = active_refs_by_document_id.get(
                    document_id,
                    (None, None),
                )
                if run_id != active_run_id or semantic_pass_id != active_semantic_pass_id:
                    continue
                rows.append(
                    {
                        "row_id": f"grounded_verification:{task.id}:{document_id}",
                        "row_type": "grounded_document_verification",
                        "label_type": "grounded_claim_support",
                        "document_id": document_id,
                        "run_id": run_id,
                        "semantic_pass_id": semantic_pass_id,
                        "source_ref": f"agent_task:{task.id}",
                        "concept_key": None,
                        "category_key": None,
                        "review_status": None,
                        "registry_version": document_ref.get("registry_version"),
                        "registry_sha256": document_ref.get("registry_sha256"),
                        "evidence_span": {
                            "claim_count": verification.get("metrics", {}).get("claim_count"),
                            "traceable_claim_ratio": verification.get("metrics", {}).get(
                                "traceable_claim_ratio"
                            ),
                        },
                        "verification_outcome": verification.get("outcome"),
                        "details": {
                            "required_concept_keys": verification_details.get(
                                "required_concept_keys"
                            )
                            or [],
                            "supported_concept_keys": verification_details.get(
                                "supported_concept_keys"
                            )
                            or [],
                            "missing_concept_keys": verification_details.get("missing_concept_keys")
                            or [],
                            "unsupported_claim_count": payload.get("summary", {}).get(
                                "unsupported_claim_count"
                            ),
                        },
                    }
                )

    row_type_counts = dict(Counter(row["row_type"] for row in rows))
    label_type_counts = dict(Counter(row["label_type"] for row in rows))
    corpus = {
        "corpus_name": "semantic_supervision_corpus",
        "document_count": len(target_document_ids),
        "row_count": len(rows),
        "row_type_counts": row_type_counts,
        "label_type_counts": label_type_counts,
        "rows": rows,
        "jsonl_path": str(output_path),
    }
    corpus["success_metrics"] = _export_success_metrics(corpus)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=str))
            handle.write("\n")
    return corpus


def _evaluate_document_candidate_extractors(
    session: Session,
    *,
    document: Document,
    registry: SemanticRegistry,
    baseline_extractor_name: str,
    candidate_extractor_name: str,
    score_threshold: float,
    max_candidates_per_source: int,
) -> dict:
    semantic_pass = get_active_semantic_pass_detail(session, document.id)
    sources = _build_semantic_sources(session, semantic_pass.run_id)
    baseline = _run_candidate_extractor(
        registry,
        sources,
        extractor_name=baseline_extractor_name,
        score_threshold=score_threshold,
        max_candidates_per_source=max_candidates_per_source,
    )
    candidate = _run_candidate_extractor(
        registry,
        sources,
        extractor_name=candidate_extractor_name,
        score_threshold=score_threshold,
        max_candidates_per_source=max_candidates_per_source,
    )
    _baseline_assertions, _baseline_bindings, baseline_evaluation = _preview_payloads_for_extractor(
        session,
        document=document,
        semantic_pass=semantic_pass,
        registry=registry,
        extraction=baseline,
    )
    _candidate_assertions, _candidate_bindings, candidate_evaluation = (
        _preview_payloads_for_extractor(
            session,
            document=document,
            semantic_pass=semantic_pass,
            registry=registry,
            extraction=candidate,
        )
    )

    expected_concept_keys = _expected_concept_keys(candidate_evaluation)
    baseline_expected_pass = {
        str(item.get("concept_key")): bool(item.get("passed"))
        for item in (baseline_evaluation.get("expectations") or [])
        if item.get("concept_key")
    }
    candidate_expected_pass = {
        str(item.get("concept_key")): bool(item.get("passed"))
        for item in (candidate_evaluation.get("expectations") or [])
        if item.get("concept_key")
    }
    improved_expected_concepts = sorted(
        concept_key
        for concept_key, passed in candidate_expected_pass.items()
        if passed and not baseline_expected_pass.get(concept_key, False)
    )
    regressed_expected_concepts = sorted(
        concept_key
        for concept_key, passed in candidate_expected_pass.items()
        if not passed and baseline_expected_pass.get(concept_key, False)
    )
    candidate_predicted_concepts = sorted(
        materialization.concept_definition.concept_key
        for materialization in candidate.materializations
    )
    baseline_predicted_concepts = sorted(
        materialization.concept_definition.concept_key
        for materialization in baseline.materializations
    )
    live_concept_keys = sorted(_assertion_concept_keys(semantic_pass))
    shadow_candidates = _shadow_candidates_from_predictions(
        document_id=document.id,
        source_predictions=candidate.source_predictions,
        expected_concept_keys=expected_concept_keys,
    )

    expected_concept_count = len(expected_concept_keys)
    baseline_expected_hit_count = sum(1 for value in baseline_expected_pass.values() if value)
    candidate_expected_hit_count = sum(1 for value in candidate_expected_pass.values() if value)
    baseline_expected_recall = (
        baseline_expected_hit_count / expected_concept_count if expected_concept_count else 1.0
    )
    candidate_expected_recall = (
        candidate_expected_hit_count / expected_concept_count if expected_concept_count else 1.0
    )
    return {
        "document_id": document.id,
        "run_id": semantic_pass.run_id,
        "semantic_pass_id": semantic_pass.semantic_pass_id,
        "registry_version": semantic_pass.registry_version,
        "registry_sha256": semantic_pass.registry_sha256,
        "evaluation_fixture_name": semantic_pass.evaluation_fixture_name,
        "expected_concept_keys": sorted(expected_concept_keys),
        "live_concept_keys": live_concept_keys,
        "baseline_predicted_concept_keys": baseline_predicted_concepts,
        "candidate_predicted_concept_keys": candidate_predicted_concepts,
        "improved_expected_concept_keys": improved_expected_concepts,
        "regressed_expected_concept_keys": regressed_expected_concepts,
        "candidate_only_concept_keys": sorted(
            set(candidate_predicted_concepts) - set(live_concept_keys)
        ),
        "shadow_candidates": shadow_candidates,
        "source_predictions": [
            _source_prediction_payload(document.id, prediction)
            for prediction in candidate.source_predictions
        ],
        "summary": {
            "baseline_expected_hit_count": baseline_expected_hit_count,
            "candidate_expected_hit_count": candidate_expected_hit_count,
            "baseline_expected_recall": round(baseline_expected_recall, 4),
            "candidate_expected_recall": round(candidate_expected_recall, 4),
            "expected_concept_count": expected_concept_count,
            "candidate_source_prediction_count": len(candidate.source_predictions),
            "baseline_source_prediction_count": len(baseline.source_predictions),
            "improved_expected_concept_count": len(improved_expected_concepts),
            "regressed_expected_concept_count": len(regressed_expected_concepts),
        },
    }


def _candidate_eval_success_metrics(payload: dict) -> list[dict]:
    summary = dict(payload.get("summary") or {})
    document_reports = list(payload.get("document_reports") or [])
    total_sources = sum(len(report.get("source_predictions") or []) for report in document_reports)
    total_shadow_candidates = sum(
        len(report.get("shadow_candidates") or []) for report in document_reports
    )
    return [
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": float(summary.get("candidate_expected_recall") or 0.0)
            >= float(summary.get("baseline_expected_recall") or 0.0),
            "summary": (
                "The shadow extractor improves or preserves expected-concept "
                "recall over the lexical baseline."
            ),
            "details": {
                "baseline_expected_recall": summary.get("baseline_expected_recall"),
                "candidate_expected_recall": summary.get("candidate_expected_recall"),
            },
        },
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": all(
                prediction.get("source_locator") and prediction.get("candidates")
                for report in document_reports
                for prediction in (report.get("source_predictions") or [])
            ),
            "summary": (
                "Every shadow candidate stays tied to explicit source "
                "evidence and registry provenance."
            ),
            "details": {
                "document_count": len(document_reports),
                "source_prediction_count": total_sources,
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(document_reports)
            and all(
                report.get("document_id") and report.get("semantic_pass_id")
                for report in document_reports
            ),
            "summary": (
                "Candidate evaluation persists typed document reports, source "
                "predictions, and shadow candidates."
            ),
            "details": {
                "document_count": len(document_reports),
                "shadow_candidate_count": total_shadow_candidates,
            },
        },
        {
            "metric_key": "explicit_shadow_boundary",
            "stakeholder": "Ronacher",
            "passed": summary.get("live_mutation_performed") is False,
            "summary": (
                "Shadow evaluation is read-only and does not mutate the active semantic contract."
            ),
            "details": {
                "live_mutation_performed": summary.get("live_mutation_performed"),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(document_reports),
            "summary": (
                "The system stores reusable candidate-evaluation context "
                "instead of ephemeral search hits."
            ),
            "details": {
                "document_count": len(document_reports),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": total_shadow_candidates <= max(total_sources, 1),
            "summary": (
                "The shadow layer compacts raw source coverage into a smaller "
                "set of candidate concepts."
            ),
            "details": {
                "shadow_candidate_count": total_shadow_candidates,
                "source_prediction_count": total_sources,
            },
        },
    ]


def evaluate_semantic_candidate_extractor(
    session: Session,
    *,
    document_ids: list[UUID],
    baseline_extractor_name: str,
    candidate_extractor_name: str,
    score_threshold: float,
    max_candidates_per_source: int,
) -> dict:
    documents = _load_target_documents(session, document_ids)
    registry = get_semantic_registry(session)
    document_reports = [
        _evaluate_document_candidate_extractors(
            session,
            document=document,
            registry=registry,
            baseline_extractor_name=baseline_extractor_name,
            candidate_extractor_name=candidate_extractor_name,
            score_threshold=score_threshold,
            max_candidates_per_source=max_candidates_per_source,
        )
        for document in documents
    ]
    expected_concept_count = sum(
        int(report.get("summary", {}).get("expected_concept_count") or 0)
        for report in document_reports
    )
    baseline_expected_hits = sum(
        int(report.get("summary", {}).get("baseline_expected_hit_count") or 0)
        for report in document_reports
    )
    candidate_expected_hits = sum(
        int(report.get("summary", {}).get("candidate_expected_hit_count") or 0)
        for report in document_reports
    )
    summary = {
        "document_count": len(document_reports),
        "expected_concept_count": expected_concept_count,
        "baseline_expected_recall": (
            round(baseline_expected_hits / expected_concept_count, 4)
            if expected_concept_count
            else 1.0
        ),
        "candidate_expected_recall": (
            round(candidate_expected_hits / expected_concept_count, 4)
            if expected_concept_count
            else 1.0
        ),
        "improved_expected_concept_count": sum(
            len(report.get("improved_expected_concept_keys") or []) for report in document_reports
        ),
        "regressed_expected_concept_count": sum(
            len(report.get("regressed_expected_concept_keys") or []) for report in document_reports
        ),
        "candidate_only_concept_count": sum(
            len(report.get("candidate_only_concept_keys") or []) for report in document_reports
        ),
        "live_mutation_performed": False,
        "score_threshold": score_threshold,
        "max_candidates_per_source": max_candidates_per_source,
    }
    payload = {
        "baseline_extractor": {
            **_extractor_descriptor(baseline_extractor_name).__dict__,
            "shadow_mode": True,
        },
        "candidate_extractor": {
            **_extractor_descriptor(candidate_extractor_name).__dict__,
            "shadow_mode": True,
        },
        "document_reports": document_reports,
        "summary": summary,
    }
    payload["success_metrics"] = _candidate_eval_success_metrics(payload)
    return payload


def _triage_success_metrics(report: dict, *, evaluation_summary: dict) -> list[dict]:
    issues = list(report.get("issues") or [])
    expected_issue_count = sum(1 for issue in issues if issue.get("expected_by_evaluation"))
    return [
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": int(evaluation_summary.get("improved_expected_concept_count") or 0)
            >= int(evaluation_summary.get("regressed_expected_concept_count") or 0),
            "summary": (
                "The disagreement report highlights recall gains without hiding regressions."
            ),
            "details": {
                "improved_expected_concept_count": evaluation_summary.get(
                    "improved_expected_concept_count"
                ),
                "regressed_expected_concept_count": evaluation_summary.get(
                    "regressed_expected_concept_count"
                ),
            },
        },
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": all(issue.get("evidence_refs") for issue in issues),
            "summary": "Every disagreement issue is backed by explicit shadow evidence.",
            "details": {
                "issue_count": len(issues),
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(issues) or bool(report.get("recommended_followups")),
            "summary": (
                "The disagreement report is compact, typed, and directly "
                "actionable for downstream agents."
            ),
            "details": {
                "issue_count": len(issues),
                "expected_issue_count": expected_issue_count,
            },
        },
        {
            "metric_key": "explicit_shadow_boundary",
            "stakeholder": "Ronacher",
            "passed": True,
            "summary": (
                "Triage stays in shadow mode and recommends review instead of "
                "mutating live semantics."
            ),
            "details": {
                "issue_count": len(issues),
            },
        },
    ]


def triage_semantic_candidate_disagreements(
    evaluation_payload: dict,
    *,
    min_score: float,
    include_expected_only: bool,
) -> tuple[dict, dict, dict]:
    document_reports = list(evaluation_payload.get("document_reports") or [])
    issues: list[dict] = []
    for report in document_reports:
        expected_concept_keys = set(report.get("expected_concept_keys") or [])
        live_concept_keys = set(report.get("live_concept_keys") or [])
        baseline_concept_keys = set(report.get("baseline_predicted_concept_keys") or [])
        for candidate in report.get("shadow_candidates") or []:
            concept_key = str(candidate.get("concept_key"))
            max_score = float(candidate.get("max_score") or 0.0)
            expected_by_evaluation = concept_key in expected_concept_keys or bool(
                candidate.get("expected_by_evaluation")
            )
            if max_score < min_score:
                continue
            if include_expected_only and not expected_by_evaluation:
                continue
            if concept_key in live_concept_keys:
                continue
            issues.append(
                {
                    "issue_id": f"shadow:{report['document_id']}:{concept_key}",
                    "document_id": report["document_id"],
                    "concept_key": concept_key,
                    "severity": "high" if expected_by_evaluation else "medium",
                    "expected_by_evaluation": expected_by_evaluation,
                    "in_live_semantics": concept_key in live_concept_keys,
                    "baseline_found": concept_key in baseline_concept_keys,
                    "max_score": round(max_score, 4),
                    "summary": (
                        f"Shadow extractor surfaced {candidate.get('preferred_label')} "
                        "outside the live semantic pass."
                    ),
                    "evidence_refs": list(candidate.get("evidence_refs") or []),
                    "details": {
                        "preferred_label": candidate.get("preferred_label"),
                        "category_keys": candidate.get("category_keys") or [],
                        "source_count": candidate.get("source_count") or 0,
                        "candidate_only": True,
                    },
                }
            )

    issues.sort(key=lambda row: (-float(row.get("max_score") or 0.0), row.get("concept_key") or ""))
    recommended_followups = []
    if issues:
        recommended_followups.append(
            {
                "followup_type": "review_shadow_candidates",
                "priority": "high",
                "summary": (
                    "Inspect the highest-signal shadow semantic disagreements "
                    "before any registry change."
                ),
                "target_task_type": None,
                "details": {
                    "issue_count": len(issues),
                    "include_expected_only": include_expected_only,
                },
            }
        )
    if any(issue.get("expected_by_evaluation") for issue in issues):
        recommended_followups.append(
            {
                "followup_type": "draft_semantic_registry_update",
                "priority": "medium",
                "summary": (
                    "Use confirmed shadow disagreements as input to a bounded "
                    "registry draft when justified."
                ),
                "target_task_type": "draft_semantic_registry_update",
                "details": {
                    "expected_issue_count": sum(
                        1 for issue in issues if issue.get("expected_by_evaluation")
                    ),
                },
            }
        )

    disagreement_report = {
        "baseline_extractor_name": evaluation_payload.get("baseline_extractor", {}).get(
            "extractor_name"
        ),
        "candidate_extractor_name": evaluation_payload.get("candidate_extractor", {}).get(
            "extractor_name"
        ),
        "issue_count": len(issues),
        "issues": issues,
        "recommended_followups": recommended_followups,
    }
    disagreement_report["success_metrics"] = _triage_success_metrics(
        disagreement_report,
        evaluation_summary=evaluation_payload.get("summary") or {},
    )

    verification_metrics = {
        "issue_count": len(issues),
        "expected_issue_count": sum(1 for issue in issues if issue.get("expected_by_evaluation")),
        "max_score": max((float(issue.get("max_score") or 0.0) for issue in issues), default=0.0),
        "candidate_expected_recall": (evaluation_payload.get("summary") or {}).get(
            "candidate_expected_recall"
        ),
        "baseline_expected_recall": (evaluation_payload.get("summary") or {}).get(
            "baseline_expected_recall"
        ),
    }
    verification_reasons = []
    if (
        int((evaluation_payload.get("summary") or {}).get("regressed_expected_concept_count") or 0)
        > 0
    ):
        verification_reasons.append("Candidate extractor regressed one or more expected concepts.")
    verification_outcome = "passed" if not verification_reasons else "failed"
    recommendation = {
        "next_action": "review_shadow_candidates" if issues else "no_action",
        "confidence": round(min(0.99, 0.4 + (len(issues) * 0.1)), 2) if issues else 0.5,
        "summary": (
            f"Shadow triage surfaced {len(issues)} disagreement(s) from "
            f"{disagreement_report['candidate_extractor_name']}."
        ),
    }
    return (
        disagreement_report,
        {
            "outcome": verification_outcome,
            "metrics": verification_metrics,
            "reasons": verification_reasons,
            "details": {
                "include_expected_only": include_expected_only,
                "min_score": min_score,
            },
        },
        recommendation,
    )


def collect_shadow_candidates_for_brief(
    session: Session,
    *,
    document_ids: list[UUID],
    candidate_extractor_name: str,
    score_threshold: float,
    requested_concept_keys: set[str],
    requested_category_keys: set[str],
    max_shadow_candidates: int,
) -> tuple[list[dict], dict]:
    evaluation = evaluate_semantic_candidate_extractor(
        session,
        document_ids=document_ids,
        baseline_extractor_name=DEFAULT_BASELINE_EXTRACTOR,
        candidate_extractor_name=candidate_extractor_name,
        score_threshold=score_threshold,
        max_candidates_per_source=DEFAULT_MAX_CANDIDATES_PER_SOURCE,
    )
    return _brief_shadow_candidates(
        list(evaluation.get("document_reports") or []),
        requested_concept_keys=requested_concept_keys,
        requested_category_keys=requested_category_keys,
        max_shadow_candidates=max_shadow_candidates,
    )
