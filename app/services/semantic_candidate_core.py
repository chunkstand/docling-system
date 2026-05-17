from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.db.models import Document
from app.services.semantic_registry import SemanticRegistry, normalize_semantic_text
from app.services.semantics import (
    SemanticAssertionMaterialization,
    SemanticEvidenceMaterialization,
    SemanticSourceItem,
    materialize_semantic_assertions,
    preview_assertions,
    preview_concept_category_bindings,
)
from app.services.semantics import source_artifact_api_path as semantic_source_artifact_api_path

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


tokenize = _tokenize
embedding_vector = _embedding_vector
cosine_similarity = _cosine_similarity
unique_document_ids = _unique_document_ids


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
    materializations = materialize_semantic_assertions(registry, sources)
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
        "source_artifact_api_path": semantic_source_artifact_api_path(
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
    latest_concept_review_overlays_fn,
    latest_category_review_overlays_fn,
    semantic_evaluation_result_fn,
) -> tuple[list[dict], list[dict], dict]:
    concept_review_overlays = latest_concept_review_overlays_fn(
        session,
        document.id,
        registry.registry_version,
    )
    category_review_overlays = latest_category_review_overlays_fn(
        session,
        document.id,
        registry.registry_version,
    )
    assertions = preview_assertions(
        list(extraction.materializations),
        concept_review_overlays=concept_review_overlays,
        category_review_overlays=category_review_overlays,
        registry=registry,
    )
    concept_category_bindings = preview_concept_category_bindings(registry)
    _evaluation_status, _fixture_name, evaluation_summary = semantic_evaluation_result_fn(
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
        source_artifact_api_path = semantic_source_artifact_api_path(
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

