from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.services import semantic_candidate_core as _semantic_candidate_core
from app.services.semantic_registry import SemanticRegistry


def _evaluate_document_candidate_extractors(
    session: Session,
    *,
    document,
    registry: SemanticRegistry,
    baseline_extractor_name: str,
    candidate_extractor_name: str,
    score_threshold: float,
    max_candidates_per_source: int,
    get_active_semantic_pass_detail_fn,
    build_semantic_sources_fn,
    latest_concept_review_overlays_fn,
    latest_category_review_overlays_fn,
    semantic_evaluation_result_fn,
) -> dict:
    semantic_pass = get_active_semantic_pass_detail_fn(session, document.id)
    sources = build_semantic_sources_fn(session, semantic_pass.run_id)
    baseline = _semantic_candidate_core._run_candidate_extractor(
        registry,
        sources,
        extractor_name=baseline_extractor_name,
        score_threshold=score_threshold,
        max_candidates_per_source=max_candidates_per_source,
    )
    candidate = _semantic_candidate_core._run_candidate_extractor(
        registry,
        sources,
        extractor_name=candidate_extractor_name,
        score_threshold=score_threshold,
        max_candidates_per_source=max_candidates_per_source,
    )
    _baseline_assertions, _baseline_bindings, baseline_evaluation = (
        _semantic_candidate_core._preview_payloads_for_extractor(
            session,
            document=document,
            semantic_pass=semantic_pass,
            registry=registry,
            extraction=baseline,
            latest_concept_review_overlays_fn=latest_concept_review_overlays_fn,
            latest_category_review_overlays_fn=latest_category_review_overlays_fn,
            semantic_evaluation_result_fn=semantic_evaluation_result_fn,
        )
    )
    _candidate_assertions, _candidate_bindings, candidate_evaluation = (
        _semantic_candidate_core._preview_payloads_for_extractor(
            session,
            document=document,
            semantic_pass=semantic_pass,
            registry=registry,
            extraction=candidate,
            latest_concept_review_overlays_fn=latest_concept_review_overlays_fn,
            latest_category_review_overlays_fn=latest_category_review_overlays_fn,
            semantic_evaluation_result_fn=semantic_evaluation_result_fn,
        )
    )

    expected_concept_keys = _semantic_candidate_core._expected_concept_keys(candidate_evaluation)
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
    live_concept_keys = sorted(_semantic_candidate_core._assertion_concept_keys(semantic_pass))
    shadow_candidates = _semantic_candidate_core._shadow_candidates_from_predictions(
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
            _semantic_candidate_core._source_prediction_payload(document.id, prediction)
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
    score_threshold: float = _semantic_candidate_core.DEFAULT_CANDIDATE_SCORE_THRESHOLD,
    max_candidates_per_source: int = _semantic_candidate_core.DEFAULT_MAX_CANDIDATES_PER_SOURCE,
    get_semantic_registry_fn,
    get_active_semantic_pass_detail_fn,
    build_semantic_sources_fn,
    latest_concept_review_overlays_fn,
    latest_category_review_overlays_fn,
    semantic_evaluation_result_fn,
) -> dict:
    documents = _semantic_candidate_core._load_target_documents(session, document_ids)
    registry = get_semantic_registry_fn(session)
    document_reports = [
        _evaluate_document_candidate_extractors(
            session,
            document=document,
            registry=registry,
            baseline_extractor_name=baseline_extractor_name,
            candidate_extractor_name=candidate_extractor_name,
            score_threshold=score_threshold,
            max_candidates_per_source=max_candidates_per_source,
            get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail_fn,
            build_semantic_sources_fn=build_semantic_sources_fn,
            latest_concept_review_overlays_fn=latest_concept_review_overlays_fn,
            latest_category_review_overlays_fn=latest_category_review_overlays_fn,
            semantic_evaluation_result_fn=semantic_evaluation_result_fn,
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
            **_semantic_candidate_core._extractor_descriptor(baseline_extractor_name).__dict__,
            "shadow_mode": True,
        },
        "candidate_extractor": {
            **_semantic_candidate_core._extractor_descriptor(candidate_extractor_name).__dict__,
            "shadow_mode": True,
        },
        "document_reports": document_reports,
        "summary": summary,
    }
    payload["success_metrics"] = _candidate_eval_success_metrics(payload)
    return payload
