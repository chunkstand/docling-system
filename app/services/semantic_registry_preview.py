from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import get_settings
from app.core.text import collapse_whitespace
from app.db.models import (
    Document,
    DocumentRun,
    SemanticAssertionKind,
    SemanticBindingOrigin,
    SemanticCategoryBindingType,
    SemanticContextScope,
    SemanticEpistemicStatus,
    SemanticEvaluationStatus,
    SemanticReviewStatus,
)
from app.services.document_run_views import get_document_or_404
from app.services.semantic_pass_reads import (
    SemanticAssertionMaterialization,
    SemanticReviewOverlay,
    build_semantic_sources,
    details_with_review_overlay,
    get_active_semantic_pass_detail,
    materialize_semantic_assertions,
)
from app.services.semantic_registry import SemanticRegistry, semantic_registry_from_payload

SEMANTIC_EVAL_VERSION = 2
SEMANTIC_MATCH_STRATEGY = "normalized_phrase_contains"


@dataclass(frozen=True)
class SemanticEvaluationExpectation:
    concept_key: str
    minimum_evidence_count: int
    required_source_types: tuple[str, ...]
    expected_category_keys: tuple[str, ...] = ()
    suggested_aliases: tuple[str, ...] = ()
    expected_epistemic_status: str | None = None
    expected_review_status: str | None = None
    expected_category_binding_review_status: str | None = None


@dataclass(frozen=True)
class SemanticConceptCategoryBindingExpectation:
    concept_key: str
    category_key: str
    expected_review_status: str | None = None


@dataclass(frozen=True)
class SemanticEvaluationFixture:
    fixture_name: str
    source_filename: str
    expected_concepts: tuple[SemanticEvaluationExpectation, ...]
    expected_concept_category_bindings: tuple[SemanticConceptCategoryBindingExpectation, ...] = ()


def _preview_concept_category_bindings(registry: SemanticRegistry) -> list[dict[str, Any]]:
    category_index = {category.category_key: category for category in registry.categories}
    bindings: list[dict[str, Any]] = []
    for concept in sorted(registry.concepts, key=lambda row: row.preferred_label.lower()):
        for category_key in concept.category_keys:
            category = category_index[category_key]
            bindings.append(
                {
                    "binding_id": None,
                    "concept_key": concept.concept_key,
                    "category_key": category.category_key,
                    "category_label": category.preferred_label,
                    "binding_type": SemanticCategoryBindingType.CONCEPT_CATEGORY.value,
                    "created_from": SemanticBindingOrigin.REGISTRY.value,
                    "review_status": SemanticReviewStatus.APPROVED.value,
                    "details": {},
                }
            )
    return bindings


def _preview_assertions(
    materializations: list[SemanticAssertionMaterialization],
    *,
    concept_review_overlays: dict[str, SemanticReviewOverlay],
    category_review_overlays: dict[tuple[str, str], SemanticReviewOverlay],
    registry: SemanticRegistry,
) -> list[dict[str, Any]]:
    category_index = {category.category_key: category for category in registry.categories}
    assertions: list[dict[str, Any]] = []
    for materialization in materializations:
        concept_key = materialization.concept_definition.concept_key
        concept_overlay = concept_review_overlays.get(concept_key)
        category_bindings = []
        for category_key in materialization.concept_definition.category_keys:
            category_overlay = category_review_overlays.get((concept_key, category_key))
            category = category_index[category_key]
            category_bindings.append(
                {
                    "binding_id": None,
                    "category_key": category_key,
                    "category_label": category.preferred_label,
                    "binding_type": SemanticCategoryBindingType.ASSERTION_CATEGORY.value,
                    "created_from": SemanticBindingOrigin.DERIVED.value,
                    "review_status": (
                        category_overlay.review_status
                        if category_overlay is not None
                        else SemanticReviewStatus.CANDIDATE.value
                    ),
                    "details": details_with_review_overlay(
                        {"preview_only": True, "match_strategy": SEMANTIC_MATCH_STRATEGY},
                        category_overlay,
                    ),
                }
            )
        assertions.append(
            {
                "assertion_id": None,
                "concept_key": concept_key,
                "preferred_label": materialization.concept_definition.preferred_label,
                "scope_note": materialization.concept_definition.scope_note,
                "assertion_kind": SemanticAssertionKind.CONCEPT_MENTION.value,
                "epistemic_status": SemanticEpistemicStatus.OBSERVED.value,
                "context_scope": SemanticContextScope.DOCUMENT_RUN.value,
                "review_status": (
                    concept_overlay.review_status
                    if concept_overlay is not None
                    else SemanticReviewStatus.CANDIDATE.value
                ),
                "matched_terms": sorted(materialization.matched_terms),
                "source_types": sorted(materialization.source_types),
                "evidence_count": len(materialization.evidence),
                "confidence": min(1.0, 0.65 + (0.1 * len(materialization.source_types))),
                "details": details_with_review_overlay(
                    {
                        "scope_note": materialization.concept_definition.scope_note,
                        "match_strategy": SEMANTIC_MATCH_STRATEGY,
                        "preview_only": True,
                    },
                    concept_overlay,
                ),
                "category_bindings": category_bindings,
                "evidence": [
                    {
                        "evidence_id": None,
                        "source_type": evidence.source_item.source_type,
                        "chunk_id": evidence.source_item.chunk_id,
                        "table_id": evidence.source_item.table_id,
                        "figure_id": evidence.source_item.figure_id,
                        "page_from": evidence.source_item.page_from,
                        "page_to": evidence.source_item.page_to,
                        "matched_terms": list(evidence.matched_terms),
                        "excerpt": evidence.source_item.excerpt,
                        "source_label": evidence.source_item.source_label,
                        "source_artifact_api_path": None,
                        "source_artifact_sha256": evidence.source_item.source_artifact_sha256,
                        "details": evidence.source_item.details,
                    }
                    for evidence in materialization.evidence
                ],
            }
        )
    return assertions


def _load_semantic_evaluation_fixtures(path_value: str) -> tuple[SemanticEvaluationFixture, ...]:
    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        return ()
    payload = yaml.safe_load(path.read_text()) or {}
    if not isinstance(payload, dict):
        raise ValueError("Semantic evaluation corpus must be a mapping.")
    raw_documents = payload.get("documents") or []
    if not isinstance(raw_documents, list):
        raise ValueError("Semantic evaluation corpus documents must be a list.")
    fixtures: list[SemanticEvaluationFixture] = []
    for raw_document in raw_documents:
        if not isinstance(raw_document, dict):
            raise ValueError("Semantic evaluation documents must be mappings.")
        source_filename = Path(str(raw_document.get("source_filename") or "")).name
        if not source_filename:
            raise ValueError("Semantic evaluation fixtures require source_filename.")
        fixture_name = collapse_whitespace(str(raw_document.get("fixture_name") or source_filename))
        raw_expectations = raw_document.get("expected_concepts") or []
        if not isinstance(raw_expectations, list):
            raise ValueError("Semantic evaluation expected_concepts must be a list.")
        expectations: list[SemanticEvaluationExpectation] = []
        for raw_expectation in raw_expectations:
            if not isinstance(raw_expectation, dict):
                raise ValueError("Semantic evaluation expectations must be mappings.")
            concept_key = collapse_whitespace(str(raw_expectation.get("concept_key") or ""))
            if not concept_key:
                raise ValueError("Semantic evaluation expectations require concept_key.")
            required_source_types = raw_expectation.get("required_source_types") or []
            if required_source_types and not isinstance(required_source_types, list):
                raise ValueError(
                    "Semantic evaluation required_source_types must be a list when provided."
                )
            expectations.append(
                SemanticEvaluationExpectation(
                    concept_key=concept_key,
                    minimum_evidence_count=int(raw_expectation.get("minimum_evidence_count") or 1),
                    required_source_types=tuple(
                        sorted(
                            collapse_whitespace(str(item or ""))
                            for item in required_source_types
                            if collapse_whitespace(str(item or ""))
                        )
                    ),
                    expected_category_keys=tuple(
                        sorted(
                            collapse_whitespace(str(item or ""))
                            for item in (raw_expectation.get("expected_category_keys") or [])
                            if collapse_whitespace(str(item or ""))
                        )
                    ),
                    suggested_aliases=tuple(
                        sorted(
                            collapse_whitespace(str(item or ""))
                            for item in (raw_expectation.get("suggested_aliases") or [])
                            if collapse_whitespace(str(item or ""))
                        )
                    ),
                    expected_epistemic_status=collapse_whitespace(
                        str(raw_expectation.get("expected_epistemic_status") or "")
                    )
                    or None,
                    expected_review_status=collapse_whitespace(
                        str(raw_expectation.get("expected_review_status") or "")
                    )
                    or None,
                    expected_category_binding_review_status=collapse_whitespace(
                        str(raw_expectation.get("expected_category_binding_review_status") or "")
                    )
                    or None,
                )
            )
        raw_concept_category_bindings = raw_document.get("expected_concept_category_bindings") or []
        if raw_concept_category_bindings and not isinstance(raw_concept_category_bindings, list):
            raise ValueError(
                "Semantic evaluation expected_concept_category_bindings must be a list."
            )
        concept_category_binding_expectations: list[SemanticConceptCategoryBindingExpectation] = []
        for raw_binding in raw_concept_category_bindings:
            if not isinstance(raw_binding, dict):
                raise ValueError(
                    "Semantic evaluation expected_concept_category_bindings entries "
                    "must be mappings."
                )
            concept_key = collapse_whitespace(str(raw_binding.get("concept_key") or ""))
            category_key = collapse_whitespace(str(raw_binding.get("category_key") or ""))
            if not concept_key or not category_key:
                raise ValueError(
                    "Semantic evaluation concept-category binding expectations "
                    "require concept_key and category_key."
                )
            concept_category_binding_expectations.append(
                SemanticConceptCategoryBindingExpectation(
                    concept_key=concept_key,
                    category_key=category_key,
                    expected_review_status=collapse_whitespace(
                        str(raw_binding.get("expected_review_status") or "")
                    )
                    or None,
                )
            )
        fixtures.append(
            SemanticEvaluationFixture(
                fixture_name=fixture_name,
                source_filename=source_filename,
                expected_concepts=tuple(expectations),
                expected_concept_category_bindings=tuple(concept_category_binding_expectations),
            )
        )
    return tuple(fixtures)


@lru_cache(maxsize=4)
def _load_semantic_evaluation_fixtures_cached(
    path_value: str,
) -> tuple[SemanticEvaluationFixture, ...]:
    return _load_semantic_evaluation_fixtures(path_value)


def _semantic_evaluation_result(
    document: Document,
    assertions: list[dict[str, Any]],
    concept_category_bindings: list[dict[str, Any]],
) -> tuple[str, str | None, dict[str, Any]]:
    settings = get_settings()
    fixtures = _load_semantic_evaluation_fixtures_cached(
        str(settings.semantic_evaluation_corpus_path.expanduser().resolve())
    )
    source_filename = Path(document.source_filename).name
    fixture = next((item for item in fixtures if item.source_filename == source_filename), None)
    if fixture is None:
        return (
            SemanticEvaluationStatus.SKIPPED.value,
            None,
            {
                "all_expectations_passed": True,
                "expected_concept_count": 0,
                "passed_expectations": 0,
                "failed_expectations": 0,
                "expectations": [],
                "reason": "no_semantic_fixture",
            },
        )
    assertions_by_concept = {assertion["concept_key"]: assertion for assertion in assertions}
    concept_category_binding_index = {
        (binding["concept_key"], binding["category_key"]): binding
        for binding in concept_category_bindings
    }
    expectation_results: list[dict[str, Any]] = []
    passed_expectations = 0
    for expectation in fixture.expected_concepts:
        assertion = assertions_by_concept.get(expectation.concept_key)
        observed_source_types = (
            sorted(set(assertion.get("source_types") or [])) if assertion else []
        )
        observed_evidence_count = int(assertion.get("evidence_count") or 0) if assertion else 0
        observed_category_keys = (
            sorted(
                {binding["category_key"] for binding in assertion.get("category_bindings") or []}
            )
            if assertion
            else []
        )
        observed_category_binding_review_statuses = (
            sorted(
                {binding["review_status"] for binding in assertion.get("category_bindings") or []}
            )
            if assertion
            else []
        )
        missing_source_types = [
            source_type
            for source_type in expectation.required_source_types
            if source_type not in observed_source_types
        ]
        missing_category_keys = [
            category_key
            for category_key in expectation.expected_category_keys
            if category_key not in observed_category_keys
        ]
        epistemic_status_matches = expectation.expected_epistemic_status is None or (
            assertion is not None
            and assertion.get("epistemic_status") == expectation.expected_epistemic_status
        )
        review_status_matches = expectation.expected_review_status is None or (
            assertion is not None
            and assertion.get("review_status") == expectation.expected_review_status
        )
        category_binding_review_status_matches = (
            expectation.expected_category_binding_review_status is None
            or (
                assertion is not None
                and expectation.expected_category_binding_review_status
                in observed_category_binding_review_statuses
            )
        )
        passed = (
            assertion is not None
            and observed_evidence_count >= expectation.minimum_evidence_count
            and not missing_source_types
            and not missing_category_keys
            and epistemic_status_matches
            and review_status_matches
            and category_binding_review_status_matches
        )
        if passed:
            passed_expectations += 1
        expectation_results.append(
            {
                "concept_key": expectation.concept_key,
                "minimum_evidence_count": expectation.minimum_evidence_count,
                "required_source_types": list(expectation.required_source_types),
                "observed_evidence_count": observed_evidence_count,
                "observed_source_types": observed_source_types,
                "missing_source_types": missing_source_types,
                "expected_category_keys": list(expectation.expected_category_keys),
                "suggested_aliases": list(expectation.suggested_aliases),
                "observed_category_keys": observed_category_keys,
                "missing_category_keys": missing_category_keys,
                "expected_epistemic_status": expectation.expected_epistemic_status,
                "observed_epistemic_status": assertion.get("epistemic_status")
                if assertion
                else None,
                "expected_review_status": expectation.expected_review_status,
                "observed_review_status": assertion.get("review_status") if assertion else None,
                "expected_category_binding_review_status": (
                    expectation.expected_category_binding_review_status
                ),
                "observed_category_binding_review_statuses": (
                    observed_category_binding_review_statuses
                ),
                "passed": passed,
            }
        )
    concept_category_binding_results: list[dict[str, Any]] = []
    passed_concept_category_binding_expectations = 0
    for expectation in fixture.expected_concept_category_bindings:
        binding = concept_category_binding_index.get(
            (expectation.concept_key, expectation.category_key)
        )
        passed = binding is not None and (
            expectation.expected_review_status is None
            or binding.get("review_status") == expectation.expected_review_status
        )
        if passed:
            passed_concept_category_binding_expectations += 1
        concept_category_binding_results.append(
            {
                "concept_key": expectation.concept_key,
                "category_key": expectation.category_key,
                "expected_review_status": expectation.expected_review_status,
                "observed_review_status": binding.get("review_status") if binding else None,
                "passed": passed,
            }
        )
    failed_expectations = len(expectation_results) - passed_expectations
    failed_concept_category_binding_expectations = (
        len(concept_category_binding_results) - passed_concept_category_binding_expectations
    )
    return (
        SemanticEvaluationStatus.COMPLETED.value,
        fixture.fixture_name,
        {
            "all_expectations_passed": (
                failed_expectations == 0 and failed_concept_category_binding_expectations == 0
            ),
            "expected_concept_count": len(expectation_results),
            "passed_expectations": passed_expectations,
            "failed_expectations": failed_expectations,
            "expected_concept_category_binding_count": len(concept_category_binding_results),
            "passed_concept_category_binding_expectations": (
                passed_concept_category_binding_expectations
            ),
            "failed_concept_category_binding_expectations": (
                failed_concept_category_binding_expectations
            ),
            "expectations": expectation_results,
            "concept_category_binding_expectations": concept_category_binding_results,
        },
    )


def preview_semantic_registry_update_for_document(
    session: Session,
    document_id: UUID,
    registry_payload: dict[str, Any],
    *,
    latest_concept_review_overlays_fn,
    latest_category_review_overlays_fn,
) -> dict[str, Any]:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        raise api_error(
            404, "semantic_pass_not_found", "Semantic pass not found.", document_id=str(document_id)
        )
    run = session.get(DocumentRun, document.active_run_id)
    if run is None:
        raise ValueError("Active document run disappeared before semantic preview.")
    current_pass = get_active_semantic_pass_detail(session, document_id)
    registry = semantic_registry_from_payload(registry_payload)
    concept_review_overlays = latest_concept_review_overlays_fn(
        session,
        document_id,
        registry.registry_version,
    )
    category_review_overlays = latest_category_review_overlays_fn(
        session,
        document_id,
        registry.registry_version,
    )
    sources = build_semantic_sources(session, run.id)
    materializations = materialize_semantic_assertions(registry, sources)
    candidate_concept_category_bindings = _preview_concept_category_bindings(registry)
    candidate_assertions = _preview_assertions(
        materializations,
        concept_review_overlays=concept_review_overlays,
        category_review_overlays=category_review_overlays,
        registry=registry,
    )
    candidate_summary = {
        "assertion_count": len(candidate_assertions),
        "evidence_count": sum(
            len(assertion.get("evidence") or []) for assertion in candidate_assertions
        ),
    }
    (
        candidate_evaluation_status,
        candidate_evaluation_fixture_name,
        candidate_evaluation_summary,
    ) = _semantic_evaluation_result(
        document, candidate_assertions, candidate_concept_category_bindings
    )
    current_concept_keys = {assertion.concept_key for assertion in current_pass.assertions}
    candidate_concept_keys = {assertion["concept_key"] for assertion in candidate_assertions}
    before_expectations = {
        str(item.get("concept_key") or ""): bool(item.get("passed"))
        for item in (current_pass.evaluation_summary.get("expectations") or [])
        if str(item.get("concept_key") or "")
    }
    after_expectations = {
        str(item.get("concept_key") or ""): bool(item.get("passed"))
        for item in (candidate_evaluation_summary.get("expectations") or [])
        if str(item.get("concept_key") or "")
    }
    introduced_expected_concepts = sorted(
        concept_key
        for concept_key, passed in after_expectations.items()
        if passed and not before_expectations.get(concept_key, False)
    )
    regressed_expected_concepts = sorted(
        concept_key
        for concept_key, passed in after_expectations.items()
        if not passed and before_expectations.get(concept_key, False)
    )
    return {
        "document_id": document.id,
        "run_id": run.id,
        "evaluation_fixture_name": candidate_evaluation_fixture_name,
        "before_all_expectations_passed": bool(
            current_pass.evaluation_summary.get("all_expectations_passed")
        ),
        "after_all_expectations_passed": bool(
            candidate_evaluation_summary.get("all_expectations_passed")
        ),
        "before_failed_expectations": int(
            current_pass.evaluation_summary.get("failed_expectations") or 0
        ),
        "after_failed_expectations": int(
            candidate_evaluation_summary.get("failed_expectations") or 0
        ),
        "before_assertion_count": current_pass.assertion_count,
        "after_assertion_count": int(candidate_summary.get("assertion_count") or 0),
        "added_concept_keys": sorted(candidate_concept_keys - current_concept_keys),
        "removed_concept_keys": sorted(current_concept_keys - candidate_concept_keys),
        "introduced_expected_concepts": introduced_expected_concepts,
        "regressed_expected_concepts": regressed_expected_concepts,
        "candidate_evaluation_status": candidate_evaluation_status,
        "candidate_evaluation_summary": candidate_evaluation_summary,
        "candidate_registry_version": registry.registry_version,
        "candidate_registry_sha256": registry.sha256,
    }


preview_assertions = _preview_assertions
preview_concept_category_bindings = _preview_concept_category_bindings
semantic_evaluation_result = _semantic_evaluation_result
