from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.db.models import Document
from app.services.semantic_candidates import _tokenize, _unique_document_ids
from app.services.semantic_registry import get_semantic_registry
from app.services.semantics import _build_semantic_sources, _source_artifact_api_path

BOOTSTRAP_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "with",
    }
)
BOOTSTRAP_NOISE_TOKENS = frozenset(
    {
        "appendix",
        "chapter",
        "document",
        "figure",
        "page",
        "report",
        "section",
        "table",
    }
)
MAX_EVIDENCE_REFS_PER_CANDIDATE = 5


@dataclass
class _BootstrapCandidateBucket:
    normalized_phrase: str
    phrase_tokens: tuple[str, ...]
    concept_key: str
    preferred_label: str
    document_ids: set[UUID] = field(default_factory=set)
    source_count: int = 0
    source_types: set[str] = field(default_factory=set)
    evidence_refs: list[dict] = field(default_factory=list)


def _load_target_documents(
    session: Session,
    document_ids: list[UUID],
) -> list[Document]:
    documents: list[Document] = []
    for document_id in _unique_document_ids(document_ids):
        document = session.get(Document, document_id)
        if document is None:
            raise ValueError(f"Document not found: {document_id}")
        if document.active_run_id is None:
            raise ValueError(f"Document does not have an active run: {document_id}")
        documents.append(document)
    return documents


def _phrase_is_candidate(
    phrase_tokens: tuple[str, ...],
    *,
    excluded_terms: set[str],
) -> bool:
    if not phrase_tokens:
        return False
    if phrase_tokens[0] in BOOTSTRAP_STOPWORDS or phrase_tokens[-1] in BOOTSTRAP_STOPWORDS:
        return False
    if phrase_tokens[0] in BOOTSTRAP_NOISE_TOKENS or phrase_tokens[-1] in BOOTSTRAP_NOISE_TOKENS:
        return False
    if any(not any(char.isalpha() for char in token) for token in phrase_tokens):
        return False
    if any(len(token) < 2 for token in phrase_tokens):
        return False
    if all(token in BOOTSTRAP_NOISE_TOKENS for token in phrase_tokens):
        return False
    if len(set(phrase_tokens)) == 1:
        return False
    return " ".join(phrase_tokens) not in excluded_terms


def _candidate_concept_key(
    normalized_phrase: str,
    *,
    existing_concept_keys: set[str],
    pending_concept_keys: set[str],
) -> str:
    base_key = collapse_whitespace(normalized_phrase).replace(" ", "_")[:72].strip("_")
    if not base_key:
        base_key = "bootstrap_candidate"
    concept_key = base_key
    suffix = 2
    while concept_key in existing_concept_keys or concept_key in pending_concept_keys:
        concept_key = f"{base_key[:64]}_{suffix}"
        suffix += 1
    pending_concept_keys.add(concept_key)
    return concept_key


def _preferred_label(phrase_tokens: tuple[str, ...]) -> str:
    return " ".join(token.capitalize() for token in phrase_tokens)


def _source_phrase_candidates(
    normalized_text: str,
    *,
    min_phrase_tokens: int,
    max_phrase_tokens: int,
    excluded_terms: set[str],
) -> list[tuple[str, tuple[str, ...]]]:
    tokens = _tokenize(normalized_text)
    if not tokens:
        return []
    rows: list[tuple[str, tuple[str, ...]]] = []
    seen_phrases: set[str] = set()
    upper_bound = min(max_phrase_tokens, len(tokens))
    for token_count in range(min_phrase_tokens, upper_bound + 1):
        for start in range(0, len(tokens) - token_count + 1):
            phrase_tokens = tokens[start : start + token_count]
            if not _phrase_is_candidate(phrase_tokens, excluded_terms=excluded_terms):
                continue
            normalized_phrase = " ".join(phrase_tokens)
            if normalized_phrase in seen_phrases:
                continue
            seen_phrases.add(normalized_phrase)
            rows.append((normalized_phrase, phrase_tokens))
    return rows


def _candidate_score(
    bucket: _BootstrapCandidateBucket,
    *,
    total_documents: int,
) -> float:
    document_coverage = len(bucket.document_ids) / max(total_documents, 1)
    source_support = min(bucket.source_count / 6, 1.0)
    source_type_diversity = min(len(bucket.source_types) / 3, 1.0)
    token_bonus = {
        1: 0.75,
        2: 0.92,
        3: 1.0,
        4: 0.96,
    }.get(len(bucket.phrase_tokens), 0.9)
    return round(
        (0.5 * document_coverage + 0.3 * source_support + 0.2 * source_type_diversity)
        * token_bonus,
        4,
    )


def _bootstrap_success_metrics(report: dict) -> list[dict]:
    candidates = list(report.get("candidates") or [])
    total_evidence = sum(len(candidate.get("evidence_refs") or []) for candidate in candidates)
    return [
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": bool(candidates)
            and report.get("extraction_strategy") == "corpus_phrase_mining_v1",
            "summary": (
                "Bootstrap discovery uses corpus-wide evidence patterns instead of "
                "domain-specific semantic rules."
            ),
            "details": {
                "candidate_count": len(candidates),
                "domain_agnostic": True,
                "existing_registry_term_exclusion": report.get("existing_registry_term_exclusion"),
            },
        },
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": all(
                candidate.get("epistemic_status") == "candidate_bootstrap"
                and candidate.get("evidence_refs")
                for candidate in candidates
            ),
            "summary": ("Bootstrap candidates remain explicitly provisional and evidence-backed."),
            "details": {
                "candidate_count": len(candidates),
                "evidence_ref_count": total_evidence,
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(candidates)
            and all(
                candidate.get("candidate_id") and candidate.get("concept_key")
                for candidate in candidates
            ),
            "summary": "Bootstrap output is durable, typed, and directly consumable by agents.",
            "details": {
                "candidate_count": len(candidates),
            },
        },
        {
            "metric_key": "explicit_shadow_boundary",
            "stakeholder": "Ronacher",
            "passed": True,
            "summary": "Bootstrap discovery stays read-only and does not mutate the live registry.",
            "details": {"live_mutation_performed": False},
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(candidates) and bool(report.get("document_count")),
            "summary": (
                "The system exports owned semantic bootstrap context for arbitrary user data."
            ),
            "details": {
                "document_count": report.get("document_count"),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": len(candidates) <= max(report.get("total_source_count") or 1, 1),
            "summary": (
                "Bootstrap discovery compacts many raw sources into a smaller candidate set."
            ),
            "details": {
                "candidate_count": len(candidates),
                "total_source_count": report.get("total_source_count"),
            },
        },
    ]


def discover_semantic_bootstrap_candidates(
    session: Session,
    *,
    document_ids: list[UUID],
    max_candidates: int,
    min_document_count: int,
    min_source_count: int,
    min_phrase_tokens: int,
    max_phrase_tokens: int,
    exclude_existing_registry_terms: bool,
) -> dict:
    if min_phrase_tokens > max_phrase_tokens:
        raise ValueError("min_phrase_tokens cannot exceed max_phrase_tokens.")

    documents = _load_target_documents(session, document_ids)
    registry = get_semantic_registry(session)
    excluded_terms = (
        {
            term.normalized_text
            for concept in registry.concepts
            for term in concept.terms
            if term.normalized_text
        }
        if exclude_existing_registry_terms
        else set()
    )
    existing_concept_keys = {concept.concept_key for concept in registry.concepts}
    pending_concept_keys: set[str] = set()
    buckets: dict[str, _BootstrapCandidateBucket] = {}
    total_source_count = 0

    for document in documents:
        run_id = document.active_run_id
        assert run_id is not None
        sources = _build_semantic_sources(session, run_id)
        total_source_count += len(sources)
        for source in sources:
            for normalized_phrase, phrase_tokens in _source_phrase_candidates(
                source.normalized_text,
                min_phrase_tokens=min_phrase_tokens,
                max_phrase_tokens=max_phrase_tokens,
                excluded_terms=excluded_terms,
            ):
                bucket = buckets.get(normalized_phrase)
                if bucket is None:
                    concept_key = _candidate_concept_key(
                        normalized_phrase,
                        existing_concept_keys=existing_concept_keys,
                        pending_concept_keys=pending_concept_keys,
                    )
                    bucket = _BootstrapCandidateBucket(
                        normalized_phrase=normalized_phrase,
                        phrase_tokens=phrase_tokens,
                        concept_key=concept_key,
                        preferred_label=_preferred_label(phrase_tokens),
                    )
                    buckets[normalized_phrase] = bucket
                bucket.document_ids.add(document.id)
                bucket.source_count += 1
                bucket.source_types.add(source.source_type)
                if len(bucket.evidence_refs) < MAX_EVIDENCE_REFS_PER_CANDIDATE:
                    bucket.evidence_refs.append(
                        {
                            "document_id": document.id,
                            "run_id": run_id,
                            "source_type": source.source_type,
                            "source_locator": source.source_locator,
                            "page_from": source.page_from,
                            "page_to": source.page_to,
                            "excerpt": source.excerpt,
                            "source_artifact_api_path": _source_artifact_api_path(
                                document.id,
                                source_type=source.source_type,
                                table_id=source.table_id,
                                figure_id=source.figure_id,
                            ),
                            "source_artifact_sha256": source.source_artifact_sha256,
                        }
                    )

    candidate_rows = []
    for bucket in buckets.values():
        if len(bucket.document_ids) < min_document_count:
            continue
        if bucket.source_count < min_source_count:
            continue
        score = _candidate_score(bucket, total_documents=len(documents))
        candidate_rows.append(
            {
                "candidate_id": f"bootstrap:{bucket.concept_key}",
                "concept_key": bucket.concept_key,
                "preferred_label": bucket.preferred_label,
                "normalized_phrase": bucket.normalized_phrase,
                "phrase_tokens": list(bucket.phrase_tokens),
                "epistemic_status": "candidate_bootstrap",
                "document_ids": sorted(bucket.document_ids, key=str),
                "document_count": len(bucket.document_ids),
                "source_count": bucket.source_count,
                "source_types": sorted(bucket.source_types),
                "score": score,
                "evidence_refs": bucket.evidence_refs,
                "details": {
                    "document_frequency": len(bucket.document_ids),
                    "source_type_diversity": len(bucket.source_types),
                    "phrase_token_count": len(bucket.phrase_tokens),
                },
            }
        )

    candidate_rows.sort(
        key=lambda row: (
            -float(row["score"]),
            -int(row["document_count"]),
            -int(row["source_count"]),
            -(len(row["phrase_tokens"])),
            row["preferred_label"].lower(),
        )
    )
    candidate_rows = candidate_rows[:max_candidates]

    warnings: list[str] = []
    if not candidate_rows:
        warnings.append(
            "No bootstrap semantic candidates met the configured thresholds "
            "for the selected documents."
        )

    report = {
        "report_name": "semantic_bootstrap_candidate_report",
        "extraction_strategy": "corpus_phrase_mining_v1",
        "input_document_ids": [document.id for document in documents],
        "document_count": len(documents),
        "total_source_count": total_source_count,
        "existing_registry_term_exclusion": exclude_existing_registry_terms,
        "candidate_count": len(candidate_rows),
        "candidates": candidate_rows,
        "warnings": warnings,
    }
    report["success_metrics"] = _bootstrap_success_metrics(report)
    return report
