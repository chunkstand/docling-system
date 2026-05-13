from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas.search import SearchRequest
from app.services import search_hydration as _search_hydration
from app.services.search_ranking import RankedEvidenceSpan, RankedResult


def _span(*, source_type: str = "chunk", source_id=None, span_index: int = 0, text: str = "span"):
    return SimpleNamespace(
        id=uuid4(),
        source_type=source_type,
        source_id=source_id or uuid4(),
        span_index=span_index,
        page_from=1,
        page_to=1,
        span_text=text,
        content_sha256=f"sha-{span_index}",
        source_snapshot_sha256=f"snapshot-{span_index}",
        chunk_id=uuid4() if source_type == "chunk" else None,
        table_id=uuid4() if source_type == "table" else None,
        document_id=uuid4(),
        run_id=uuid4(),
    )


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession(Session):
    def __init__(self) -> None:
        self.executed_statements: list[object] = []
        self.scalar_statements: list[object] = []
        self._execute_rows: list[list[object]] = []
        self._scalar_rows: list[list[object]] = []

    def push_execute_rows(self, rows: list[object]) -> None:
        self._execute_rows.append(rows)

    def push_scalar_rows(self, rows: list[object]) -> None:
        self._scalar_rows.append(rows)

    def execute(self, statement):
        self.executed_statements.append(statement)
        rows = self._execute_rows.pop(0)
        return _FakeResult(rows)

    def scalars(self, statement):
        self.scalar_statements.append(statement)
        return list(self._scalar_rows.pop(0))


def _ranked_chunk_result(*, result_id=None, evidence_spans=()) -> RankedResult:
    return RankedResult(
        result_type="chunk",
        result_id=result_id or uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="doc.pdf",
        document_title="Doc",
        page_from=1,
        page_to=1,
        chunk_index=0,
        chunk_text="chunk text",
        heading="Heading",
        evidence_spans=evidence_spans,
    )


def test_hydrate_ranked_span_chunks_attaches_span_payload() -> None:
    source_id = uuid4()
    span = _span(source_type="chunk", source_id=source_id, span_index=2, text="Matched evidence")
    chunk = SimpleNamespace(
        id=source_id,
        document_id=uuid4(),
        run_id=uuid4(),
        page_from=4,
        page_to=4,
        chunk_index=7,
        text="Chunk content",
        heading="Section",
    )
    document = SimpleNamespace(source_filename="doc.pdf", title="Document")

    results = _search_hydration._hydrate_ranked_span_chunks(
        [(span, chunk, document, 0.73)],
        "keyword",
        retrieval_source="keyword_span",
    )

    assert len(results) == 1
    assert results[0].keyword_score == 0.73
    assert results[0].retrieval_sources == ("keyword_span",)
    assert results[0].evidence_spans[0].text_excerpt == "Matched evidence"
    assert results[0].evidence_spans[0].score_kind == "keyword"


def test_load_source_evidence_spans_prefers_keyword_matches_and_merges_existing_spans() -> None:
    source_id = uuid4()
    existing_span = RankedEvidenceSpan(
        retrieval_evidence_span_id=uuid4(),
        source_type="chunk",
        source_id=source_id,
        span_index=9,
        score_kind="existing",
        score=0.2,
        page_from=1,
        page_to=1,
        text_excerpt="existing",
        content_sha256="existing-sha",
        source_snapshot_sha256="existing-snapshot",
        metadata={},
    )
    matched_span = _span(source_type="chunk", source_id=source_id, span_index=1, text="matched")
    session = _FakeSession()
    session.push_execute_rows([(matched_span, 0.91)])
    item = _ranked_chunk_result(result_id=source_id, evidence_spans=(existing_span,))

    spans = _search_hydration._load_source_evidence_spans(
        session,
        SearchRequest(query="matched", mode="keyword", limit=5),
        item,
    )

    assert len(spans) == 2
    assert spans[0].retrieval_evidence_span_id == matched_span.id
    assert spans[0].score_kind == "selected_result_keyword_span"
    assert session.scalar_statements == []


def test_load_source_evidence_spans_falls_back_to_ordered_source_spans() -> None:
    source_id = uuid4()
    fallback_one = _span(source_type="table", source_id=source_id, span_index=1, text="row 1")
    fallback_two = _span(source_type="table", source_id=source_id, span_index=2, text="row 2")
    session = _FakeSession()
    session.push_execute_rows([])
    session.push_scalar_rows([fallback_one, fallback_two])
    item = RankedResult(
        result_type="table",
        result_id=source_id,
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="doc.pdf",
        document_title="Doc",
        page_from=3,
        page_to=3,
        table_index=0,
        table_title="Table 1",
        table_heading="Heading",
        table_preview="preview",
        row_count=2,
        col_count=2,
    )

    spans = _search_hydration._load_source_evidence_spans(
        session,
        SearchRequest(query="absent", mode="keyword", limit=5),
        item,
    )

    assert [span.span_index for span in spans] == [1, 2]
    assert all(span.score_kind == "selected_result_source_span" for span in spans)


def test_hydrate_late_interaction_results_preserves_score_order_and_trace() -> None:
    chunk_span_id = uuid4()
    table_span_id = uuid4()
    chunk_span = _span(source_type="chunk", source_id=uuid4(), text="chunk evidence")
    chunk_span.id = chunk_span_id
    table_span = _span(source_type="table", source_id=uuid4(), text="table evidence")
    table_span.id = table_span_id
    chunk = SimpleNamespace(
        id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        page_from=2,
        page_to=2,
        chunk_index=1,
        text="chunk text",
        heading="Heading",
    )
    table = SimpleNamespace(
        id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        page_from=5,
        page_to=5,
        table_index=0,
        title="Table 1",
        heading="Table heading",
        preview_text="preview",
        row_count=3,
        col_count=2,
    )
    document = SimpleNamespace(source_filename="doc.pdf", title="Document")
    session = _FakeSession()
    session.push_execute_rows([(chunk_span, chunk, document)])
    session.push_execute_rows([(table_span, table, document)])

    results = _search_hydration._hydrate_late_interaction_results(
        session,
        span_scores={
            chunk_span_id: {"score": 0.98, "trace": {"match": "chunk"}},
            table_span_id: {"score": 0.74, "trace": {"match": "table"}},
        },
        limit=5,
        run_id=None,
    )

    assert [result.result_type for result in results] == ["chunk", "table"]
    assert results[0].semantic_score == 0.98
    assert (
        results[0].evidence_spans[0].metadata["late_interaction"]["match"] == "chunk"
    )
    assert results[1].evidence_spans[0].score_kind == "late_interaction_maxsim"
