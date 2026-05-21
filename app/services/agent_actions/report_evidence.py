from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.coercion import unique_strings as _unique_strings
from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_reports import (
    BuildReportEvidenceCardsTaskInput,
    BuildReportEvidenceCardsTaskOutput,
    PlanTechnicalReportTaskOutput,
    PrepareReportAgentHarnessTaskInput,
)
from app.schemas.search import (
    SearchFilters,
    SearchRequest,
)
from app.services.agent_actions.report_evidence_sources import (
    source_export_summary,
    task_page_spans_overlap,
    task_source_page_span,
    task_source_record_key,
)
from app.services.agent_actions.report_readiness import (
    release_readiness_assessment_refs_for_exports,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
)
from app.services.evidence_search_packages import persist_search_evidence_package_export
from app.services.report_shared import (
    source_evidence_match_status as _aggregate_source_match_status,
)
from app.services.search import execute_search
from app.services.storage import StorageService
from app.services.technical_reports import (
    build_report_evidence_cards,
    prepare_report_agent_harness,
    task_output_context_ref,
)


def _card_document_run_keys(card: dict) -> list[str]:
    document_ids = _unique_strings(
        [card.get("document_id"), *(card.get("source_document_ids") or [])]
    )
    run_ids = _unique_strings([card.get("run_id")])
    if not run_ids:
        return []
    return [f"{document_id}:{run_id}" for document_id in document_ids for run_id in run_ids]


def _task_card_source_record_keys(card: dict) -> list[str]:
    metadata = card.get("metadata") or {}
    source_type = str(card.get("source_type") or "").strip().lower()
    source_record_keys: list[str] = [
        task_source_record_key("chunk", card.get("chunk_id") or metadata.get("chunk_id")),
        task_source_record_key("table", card.get("table_id") or metadata.get("table_id")),
    ]
    if source_type in {"chunk", "table"}:
        source_record_keys.append(
            task_source_record_key(
                source_type,
                card.get("source_locator") or metadata.get("source_locator"),
            )
        )
    return _unique_strings(source_record_keys)


def _task_card_requires_source_match(card: dict) -> bool:
    source_type = str(card.get("source_type") or "").strip().lower()
    evidence_kind = str(card.get("evidence_kind") or "").strip().lower()
    return (
        source_type in {"chunk", "table", "figure"}
        or evidence_kind in {"source_evidence", "semantic_fact"}
        or bool(card.get("evidence_ids"))
    )


def _task_card_page_span(card: dict) -> dict | None:
    return task_source_page_span(
        document_id=card.get("document_id"),
        run_id=card.get("run_id"),
        page_from=card.get("page_from"),
        page_to=card.get("page_to"),
    )


def _match_card_source_exports(
    card: dict,
    search_export_summaries: list[dict],
) -> tuple[str, list[dict], list[str]]:
    source_record_keys = set(_task_card_source_record_keys(card))
    if source_record_keys:
        matched_summaries: list[dict] = []
        matched_keys: list[str] = []
        for summary in search_export_summaries:
            summary_keys = set(summary.get("source_record_keys") or [])
            overlap = sorted(source_record_keys & summary_keys)
            if overlap:
                matched_summaries.append(summary)
                matched_keys.extend(overlap)
        if matched_summaries:
            return "matched_source_record", matched_summaries, _unique_strings(matched_keys)

    card_page_span = _task_card_page_span(card)
    if card_page_span:
        matched_summaries = []
        matched_keys = []
        for summary in search_export_summaries:
            overlapping_source_spans = [
                span
                for span in summary.get("source_page_spans") or []
                if task_page_spans_overlap(card_page_span, span)
            ]
            if overlapping_source_spans:
                matched_summaries.append(summary)
                matched_keys.extend(span["key"] for span in overlapping_source_spans)
        if matched_summaries:
            return "matched_page_span", matched_summaries, _unique_strings(matched_keys)

    if not source_record_keys and not card_page_span:
        matched_summaries = []
        for key in _card_document_run_keys(card):
            matched_summaries.extend(
                summary
                for summary in search_export_summaries
                if key in (summary.get("source_document_run_keys") or [])
            )
        if matched_summaries:
            return "matched_document_run_fallback", matched_summaries, _card_document_run_keys(card)

    return "missing", [], []


def _card_targeted_query(card: dict) -> str | None:
    excerpt = str(card.get("excerpt") or "").strip()
    if excerpt:
        return " ".join(excerpt.split())[:1000]
    matched_terms = (card.get("metadata") or {}).get("matched_terms") or []
    query = " ".join(_unique_strings(matched_terms)).strip()
    return query[:1000] or None


def _attach_source_exports_to_evidence_bundle(
    evidence_bundle: dict,
    search_export_summaries: list[dict],
) -> None:
    def matched_result_ids(card: dict, summaries: list[dict]) -> list[str]:
        card_source_record_keys = set(_task_card_source_record_keys(card))
        card_page_span = _task_card_page_span(card)
        result_ids: list[str] = []
        for summary in summaries:
            for result in summary.get("source_results") or []:
                result_id = result.get("search_request_result_id")
                if not result_id:
                    continue
                result_record_keys = set(result.get("source_record_keys") or [])
                result_page_spans = list(result.get("source_page_spans") or [])
                if card_source_record_keys and card_source_record_keys & result_record_keys:
                    result_ids.append(result_id)
                    continue
                if card_page_span and any(
                    task_page_spans_overlap(card_page_span, span) for span in result_page_spans
                ):
                    result_ids.append(result_id)
                    continue
                if not card_source_record_keys and not card_page_span:
                    result_ids.append(result_id)
        return _unique_strings(result_ids)

    cards_by_id: dict[str, dict] = {}
    for card in evidence_bundle.get("evidence_cards") or []:
        source_match_status, matched_summaries, source_match_keys = _match_card_source_exports(
            card,
            search_export_summaries,
        )
        matched_summaries = list(
            {
                summary["evidence_package_export_id"]: summary for summary in matched_summaries
            }.values()
        )
        card["source_search_request_ids"] = _unique_strings(
            summary.get("search_request_id") for summary in matched_summaries
        )
        card["source_search_request_result_ids"] = matched_result_ids(
            card,
            matched_summaries,
        )
        card["source_evidence_package_export_ids"] = _unique_strings(
            summary.get("evidence_package_export_id") for summary in matched_summaries
        )
        card["source_evidence_package_sha256s"] = _unique_strings(
            summary.get("package_sha256") for summary in matched_summaries
        )
        card["source_evidence_trace_sha256s"] = _unique_strings(
            summary.get("trace_sha256") for summary in matched_summaries
        )
        card["source_evidence_match_keys"] = source_match_keys
        card["source_evidence_match_status"] = source_match_status
        card_metadata = dict(card.get("metadata") or {})
        card_metadata["source_record_keys"] = _task_card_source_record_keys(card)
        card_metadata["source_page_span"] = _task_card_page_span(card)
        card["metadata"] = card_metadata
        cards_by_id[str(card.get("evidence_card_id"))] = card

    for claim in evidence_bundle.get("claim_evidence_map") or []:
        claim_cards = [
            cards_by_id[card_id]
            for card_id in _unique_strings(claim.get("evidence_card_ids") or [])
            if card_id in cards_by_id
        ]
        claim["source_search_request_ids"] = _unique_strings(
            value for card in claim_cards for value in (card.get("source_search_request_ids") or [])
        )
        claim["source_search_request_result_ids"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_search_request_result_ids") or [])
        )
        claim["source_evidence_package_export_ids"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_package_export_ids") or [])
        )
        claim["source_evidence_package_sha256s"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_package_sha256s") or [])
        )
        claim["source_evidence_trace_sha256s"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_trace_sha256s") or [])
        )
        claim["source_evidence_match_keys"] = _unique_strings(
            value
            for card in claim_cards
            for value in (card.get("source_evidence_match_keys") or [])
        )
        claim["source_evidence_match_status"] = _aggregate_source_match_status(
            [
                card.get("source_evidence_match_status")
                for card in claim_cards
                if _task_card_requires_source_match(card)
                if card.get("source_evidence_match_status")
            ]
        )

    evidence_bundle["search_evidence_package_exports"] = search_export_summaries


def _freeze_report_retrieval_evidence(
    session: Session,
    *,
    task_id: UUID,
    evidence_bundle: dict,
) -> list[dict]:
    summaries: list[dict] = []
    seen_search_keys: set[tuple[str, str | None, str | None]] = set()
    for retrieval_row in evidence_bundle.get("retrieval_index") or []:
        document_ids = _unique_strings(retrieval_row.get("document_ids") or [])
        for query in _unique_strings(retrieval_row.get("queries") or []):
            for document_id in document_ids:
                search_key = (query, document_id, None)
                if search_key in seen_search_keys:
                    continue
                seen_search_keys.add(search_key)
                execution = execute_search(
                    session,
                    SearchRequest(
                        query=query,
                        mode="keyword",
                        filters=SearchFilters(document_id=UUID(document_id)),
                        limit=5,
                    ),
                    origin="agent_task_report_retrieval",
                )
                if execution.request_id is None:
                    continue
                export = persist_search_evidence_package_export(
                    session,
                    search_request_id=execution.request_id,
                    agent_task_id=task_id,
                )
                summaries.append(source_export_summary(export))
    for card in evidence_bundle.get("evidence_cards") or []:
        source_type = str(card.get("source_type") or "").strip().lower()
        if source_type not in {"chunk", "table"}:
            continue
        document_id = str(card.get("document_id") or "")
        if not document_id:
            continue
        query = _card_targeted_query(card)
        if not query:
            continue
        search_key = (query, document_id, source_type)
        if search_key in seen_search_keys:
            continue
        seen_search_keys.add(search_key)
        execution = execute_search(
            session,
            SearchRequest(
                query=query,
                mode="keyword",
                filters=SearchFilters(
                    document_id=UUID(document_id),
                    result_type=source_type,
                ),
                limit=10,
            ),
            origin="agent_task_report_source_card_retrieval",
        )
        if execution.request_id is None:
            continue
        export = persist_search_evidence_package_export(
            session,
            search_request_id=execution.request_id,
            agent_task_id=task_id,
        )
        summaries.append(source_export_summary(export))
    _attach_source_exports_to_evidence_bundle(evidence_bundle, summaries)
    return summaries


def build_report_evidence_cards_executor(
    session: Session,
    task: AgentTask,
    payload: BuildReportEvidenceCardsTaskInput,
) -> dict:
    plan_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="plan_technical_report",
        expected_schema_name="plan_technical_report_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Evidence-card construction must declare the report plan as a target_task dependency."
        ),
        rerun_message=(
            "Technical report plan must be rerun after the context migration "
            "before evidence cards can be built."
        ),
    )
    plan_output = PlanTechnicalReportTaskOutput.model_validate(plan_context.output)
    evidence_bundle = build_report_evidence_cards(
        plan_output.plan.model_dump(mode="json"),
        plan_task_id=payload.target_task_id,
    )
    search_evidence_exports = _freeze_report_retrieval_evidence(
        session,
        task_id=task.id,
        evidence_bundle=evidence_bundle,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="technical_report_evidence_cards",
        payload=evidence_bundle,
        storage_service=StorageService(),
        filename="technical_report_evidence_cards.json",
    )
    return {
        "evidence_bundle": evidence_bundle,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "search_evidence_package_export_count": len(search_evidence_exports),
    }


def prepare_report_agent_harness_executor(
    session: Session,
    task: AgentTask,
    payload: PrepareReportAgentHarnessTaskInput,
) -> dict:
    evidence_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
        dependency_kind="target_task",
        expected_task_type="build_report_evidence_cards",
        expected_schema_name="build_report_evidence_cards_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Report harness packaging must declare the evidence-card task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Report evidence cards must be rerun after the context migration "
            "before harness packaging."
        ),
    )
    evidence_output = BuildReportEvidenceCardsTaskOutput.model_validate(evidence_context.output)
    release_readiness_assessments = release_readiness_assessment_refs_for_exports(
        session,
        list(evidence_output.evidence_bundle.search_evidence_package_exports),
    )
    upstream_context_refs = [
        task_output_context_ref(
            ref_key="evidence_cards_task_output",
            summary="Typed evidence-card bundle consumed by this report harness.",
            task_id=evidence_context.task_id,
            schema_name=evidence_context.output_schema_name,
            schema_version=evidence_context.output_schema_version,
            output=evidence_context.output,
            source_updated_at=evidence_context.task_updated_at,
            freshness_status=evidence_context.freshness_status,
        ),
        *evidence_context.refs,
    ]
    harness_payload = prepare_report_agent_harness(
        evidence_output.evidence_bundle.model_dump(mode="json"),
        harness_task_id=task.id,
        evidence_task_id=payload.target_task_id,
        upstream_context_refs=upstream_context_refs,
        release_readiness_assessments=release_readiness_assessments,
    )
    context_pack_payload = harness_payload["document_generation_context_pack"]
    storage_service = StorageService()
    context_pack_artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="document_generation_context_pack",
        payload=context_pack_payload,
        storage_service=storage_service,
        filename="document_generation_context_pack.json",
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="report_agent_harness",
        payload=harness_payload,
        storage_service=storage_service,
        filename="report_agent_harness.json",
    )
    return {
        "harness": harness_payload,
        "context_pack": context_pack_payload,
        "context_pack_artifact_id": str(context_pack_artifact.id),
        "context_pack_artifact_kind": context_pack_artifact.artifact_kind,
        "context_pack_artifact_path": context_pack_artifact.storage_path,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
