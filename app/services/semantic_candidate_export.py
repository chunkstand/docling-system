from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.services import semantic_candidate_core as _semantic_candidate_core


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
    get_active_semantic_pass_detail_fn,
) -> dict:
    documents = _semantic_candidate_core._load_target_documents(session, document_ids)
    rows: list[dict] = []
    target_document_ids = {document.id for document in documents}
    active_refs_by_document_id: dict[UUID, tuple[UUID, UUID]] = {}

    for document in documents:
        semantic_pass = get_active_semantic_pass_detail_fn(session, document.id)
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

