from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import (
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
)
from app.schemas.search import SearchRequest
from app.services import search_execution_persistence as _search_execution_persistence
from app.services.search_ranking import RankedEvidenceSpan, RankedResult, RerankedResult


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_count = 0

    def add(self, value) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_count += 1


def _span(
    *,
    source_type: str = "chunk",
    score_kind: str = "keyword",
    span_index: int = 0,
    metadata: dict | None = None,
) -> RankedEvidenceSpan:
    return RankedEvidenceSpan(
        retrieval_evidence_span_id=uuid4(),
        source_type=source_type,
        source_id=uuid4(),
        span_index=span_index,
        score_kind=score_kind,
        score=0.8 - (span_index * 0.01),
        page_from=1,
        page_to=1,
        text_excerpt=f"span-{span_index}",
        content_sha256=f"content-{span_index}",
        source_snapshot_sha256=f"snapshot-{span_index}",
        metadata=metadata or {},
    )


def _ranked_chunk_result(
    *,
    retrieval_sources: tuple[str, ...] = ("keyword_primary",),
    evidence_spans: tuple[RankedEvidenceSpan, ...] = (),
) -> RankedResult:
    return RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="doc.pdf",
        document_title="Doc",
        page_from=3,
        page_to=3,
        chunk_index=1,
        chunk_text="vent stack content",
        heading="Venting",
        keyword_score=0.7,
        retrieval_sources=retrieval_sources,
        evidence_spans=evidence_spans,
    )


def _ranked_table_result(
    *,
    retrieval_sources: tuple[str, ...] = ("semantic_primary",),
    evidence_spans: tuple[RankedEvidenceSpan, ...] = (),
) -> RankedResult:
    return RankedResult(
        result_type="table",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="tables.pdf",
        document_title="Tables",
        page_from=4,
        page_to=4,
        table_index=0,
        table_title="TABLE 1",
        table_heading="Vent stack sizes",
        table_preview="Diameter | Height",
        row_count=2,
        col_count=2,
        keyword_score=0.68,
        semantic_score=0.82,
        hybrid_score=0.9,
        retrieval_sources=retrieval_sources,
        evidence_spans=evidence_spans,
    )


def test_ranked_result_evidence_payload_serializes_span_metadata() -> None:
    result = _ranked_table_result(
        evidence_spans=(
            _span(
                source_type="table",
                score_kind="late_interaction_maxsim",
                metadata={"late_interaction": {"match": "table"}},
            ),
        )
    )

    payload = _search_execution_persistence._ranked_result_evidence_payload(result, 2)

    assert payload["candidate_index"] == 2
    assert payload["label"] == "TABLE 1"
    assert payload["retrieval_sources"] == ["semantic_primary"]
    assert payload["evidence_spans"][0]["metadata"]["late_interaction"]["match"] == "table"


def test_persist_search_result_spans_caps_rows_and_preserves_metadata() -> None:
    session = _FakeSession()
    reranked = RerankedResult(
        item=_ranked_chunk_result(
            retrieval_sources=("keyword_primary", "adjacent_context"),
            evidence_spans=tuple(
                _span(
                    span_index=index,
                    metadata={"late_interaction": {"match": f"span-{index}"}},
                )
                for index in range(6)
            ),
        ),
        rank=1,
        base_rank=1,
        score=0.91,
        features={"final_score": 0.93},
    )

    _search_execution_persistence._persist_search_result_spans(
        session,
        search_request_id=uuid4(),
        reranked_results=[reranked],
        result_rows=[SimpleNamespace(id=uuid4())],
        created_at=datetime.now(UTC),
    )

    span_rows = [row for row in session.added if isinstance(row, SearchRequestResultSpan)]

    assert len(span_rows) == 5
    assert session.flush_count == 1
    assert span_rows[0].span_rank == 1
    assert span_rows[0].metadata_json["retrieval_source_count"] == 2
    assert span_rows[0].metadata_json["retrieval_sources"] == [
        "keyword_primary",
        "adjacent_context",
    ]
    assert span_rows[0].metadata_json["late_interaction"]["match"] == "span-0"


def test_persist_search_execution_persists_request_results_and_operator_chain() -> None:
    session = _FakeSession()
    chunk_result = _ranked_chunk_result(
        evidence_spans=(_span(score_kind="selected_result_keyword_span"),)
    )
    table_result = _ranked_table_result(
        evidence_spans=(
            _span(
                source_type="table",
                score_kind="late_interaction_maxsim",
                metadata={"late_interaction": {"query_vector_count": 2}},
            ),
        )
    )
    reranked_results = [
        RerankedResult(
            item=table_result,
            rank=1,
            base_rank=2,
            score=0.94,
            features={"final_score": 0.97, "document_title_token_coverage": 1.0},
        ),
        RerankedResult(
            item=chunk_result,
            rank=2,
            base_rank=1,
            score=0.83,
            features={"final_score": 0.85},
        ),
    ]

    request_id, operator_run_ids = _search_execution_persistence._persist_search_execution(
        session,
        request=SearchRequest(query="table 1", mode="hybrid", limit=2),
        origin="api",
        run_id=None,
        evaluation_id=None,
        parent_request_id=None,
        tabular_query=True,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config={
            "harness_name": "default_v1",
            "retrieval_profile": {"name": "default_v1"},
            "reranker": {"name": "linear_feature_reranker"},
        },
        embedding_status="completed",
        embedding_error=None,
        candidate_count=2,
        duration_ms=12.5,
        details={
            "served_mode": "hybrid",
            "requested_mode": "hybrid",
            "query_intent": "tabular",
            "candidate_source_breakdown": {"keyword_primary": 1, "semantic_primary": 1},
        },
        candidate_items=[chunk_result, table_result],
        reranked_results=reranked_results,
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]
    result_rows = [row for row in session.added if isinstance(row, SearchRequestResult)]
    span_rows = [row for row in session.added if isinstance(row, SearchRequestResultSpan)]
    operator_rows = [row for row in session.added if isinstance(row, KnowledgeOperatorRun)]
    operator_output_rows = [
        row for row in session.added if isinstance(row, KnowledgeOperatorOutput)
    ]

    assert request_rows
    assert request_id == request_rows[0].id
    assert request_rows[0].origin == "api"
    assert request_rows[0].tabular_query is True
    assert request_rows[0].result_count == 2
    assert request_rows[0].table_hit_count == 1
    assert len(result_rows) == 2
    assert span_rows
    assert len(operator_run_ids) == 3
    assert [row.id for row in operator_rows] == operator_run_ids
    assert [row.operator_kind for row in operator_rows] == ["retrieve", "rerank", "judge"]
    assert operator_rows[1].parent_operator_run_id == operator_rows[0].id
    assert operator_rows[2].parent_operator_run_id == operator_rows[1].id
    selected_outputs = [
        row for row in operator_output_rows if row.output_kind == "selected_evidence"
    ]
    assert selected_outputs
    assert selected_outputs[0].payload_json["preview_text"]
