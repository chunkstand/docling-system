from __future__ import annotations

import re

from app.hotspot_prevention_classifier_support import ClassifiedLine, blocked
from app.hotspot_prevention_diff import ChangedLine

_SEARCH_HARNESS_OWNER_MESSAGE = (
    "search harness contracts, registry, and reranking logic belongs in "
    "search_harness_contracts.py, search_harness_registry.py, "
    "or search_harness_reranking.py"
)


def classify_search_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    lowered = stripped.lower()
    if re.match(
        r"(async def |def )(_?)(build_derived_search_harness|build_search_harness_registry|"
        r"list_search_harnesses|get_search_harness|get_default_reranker)\b",
        stripped,
    ) or any(
        token in stripped
        for token in (
            "SearchHarness(",
            "LinearFeatureSearchReranker(",
            "LinearRerankerConfig(",
            "SearchRetrievalProfile(",
        )
    ):
        return blocked(line, "harness_registry_logic", _SEARCH_HARNESS_OWNER_MESSAGE)
    if re.match(
        r"(async def |def )(_?)(chunk_query|table_query|document_query|apply_.*filters|"
        r"keyword_terms|build_relaxed_tsquery|run_keyword_[A-Za-z0-9_]+|"
        r"run_semantic_[A-Za-z0-9_]+|query_multivector_windows|"
        r"multivector_span_query|late_interaction_match_trace|"
        r"run_late_interaction_search)\b",
        stripped,
    ):
        return blocked(
            line,
            "retrieval_primitive_logic",
            "search primitives live in search_retrieval_primitives.py or search_span_retrieval.py",
        )
    if re.match(
        r"(async def |def )(_?)(ranked_metadata_overlap_score|metadata_tsquery|"
        r"run_prose_metadata_chunk_search|should_run_metadata_supplement|"
        r"expand_adjacent_chunk_context)\b",
        stripped,
    ):
        return blocked(
            line,
            "metadata_supplement_logic",
            "search metadata supplement logic belongs in search_metadata_supplement.py",
        )
    if re.match(r"(async def |def )_load_.*candidate", stripped):
        return blocked(line, "candidate_loading", "candidate loading belongs in search_* modules")
    if re.match(r"(async def |def )_build_search_execution_details", stripped):
        return blocked(line, "search_detail_payload_builder", "detail assembly belongs in search_*")
    is_execution_def = re.match(
        r"(async def |def )_(resolve_candidate_items|run_execution_|execute_search)",
        stripped,
    )
    if is_execution_def or any(
        token in stripped for token in ("build_search_execution_plan(", "SearchStage.")
    ):
        return blocked(line, "execution_orchestration", "execution flow belongs in search_*")
    if re.match(r"(async def |def )_persist_", stripped) or any(
        token in stripped
        for token in (
            "SearchRequestRecord(",
            "SearchRequestResult(",
            "SearchRequestResultSpan(",
        )
    ):
        return blocked(line, "persistence_logic", "search persistence belongs in search_* modules")
    if re.match(
        r"(async def |def )_((ranked|reranked)_result_evidence_payload|build_operator_trace_)",
        stripped,
    ) or any(
        token in lowered
        for token in (
            "record_knowledge_operator_run(",
            "output_payload",
            "selected_evidence",
            "knowledge_operator_runs",
        )
    ):
        return blocked(
            line,
            "operator_trace_payload_builder",
            "operator-trace payloads belong in search_* modules",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(line, "query_feature_helper", "search helpers belong in search_* modules")
    if stripped.startswith(("def ", "async def ")):
        return blocked(line, "ranking_logic", "new search behavior belongs in search_* modules")
    if any(token in lowered for token in ("rank", "score", "hydrate", "telemetry")):
        return blocked(line, "ranking_logic", "new search logic belongs in search_* modules")
    return None


def classify_search_harness_facade_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    if stripped.startswith("class "):
        return blocked(line, "harness_owner_logic", _SEARCH_HARNESS_OWNER_MESSAGE)
    if re.match(r"(async def |def )", stripped):
        return blocked(
            line,
            "harness_owner_logic",
            (
                "search harness behavior belongs in search_harness_contracts.py, "
                "search_harness_registry.py, or search_harness_reranking.py"
            ),
        )
    if any(
        token in stripped
        for token in (
            "SearchHarness(",
            "SearchRetrievalProfile(",
            "LinearRerankerConfig(",
            "LinearFeatureSearchReranker(",
            "_HARNESS_REGISTRY",
        )
    ):
        return blocked(line, "harness_owner_logic", _SEARCH_HARNESS_OWNER_MESSAGE)
    return None
