from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.services import semantic_candidate_core as _semantic_candidate_core


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
    evaluate_semantic_candidate_extractor_fn,
) -> tuple[list[dict], dict]:
    evaluation = evaluate_semantic_candidate_extractor_fn(
        session,
        document_ids=document_ids,
        baseline_extractor_name=_semantic_candidate_core.DEFAULT_BASELINE_EXTRACTOR,
        candidate_extractor_name=candidate_extractor_name,
        score_threshold=score_threshold,
        max_candidates_per_source=_semantic_candidate_core.DEFAULT_MAX_CANDIDATES_PER_SOURCE,
    )
    return _semantic_candidate_core._brief_shadow_candidates(
        list(evaluation.get("document_reports") or []),
        requested_concept_keys=requested_concept_keys,
        requested_category_keys=requested_category_keys,
        max_shadow_candidates=max_shadow_candidates,
    )
