from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.db.models import (
    SearchRequestRecord,
    SearchRequestResult,
)
from app.schemas.search import SearchRequest
from app.services.search import (
    RankedResult,
    execute_search,
    search_documents,
)


def test_semantic_mode_falls_back_to_keyword_when_embeddings_unavailable(monkeypatch) -> None:
    chunk_id = uuid4()
    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=chunk_id,
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=1,
                page_to=1,
                chunk_text="fallback text",
                heading="Heading",
                keyword_score=0.9,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.get_embedding_provider",
        lambda: (_ for _ in ()).throw(RuntimeError("no embeddings")),
    )

    results = search_documents(
        session=None, request=SearchRequest(query="fallback", mode="semantic", limit=5)
    )

    assert len(results) == 1
    assert results[0].result_type == "chunk"
    assert results[0].chunk_id == chunk_id


def test_execute_search_falls_back_to_relaxed_keyword_matching(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="essay.pdf",
                page_from=1,
                page_to=1,
                chunk_text=(
                    "General methods that leverage computation are ultimately the most effective."
                ),
                heading=None,
                keyword_score=0.4,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(
            query="What is the main claim of The Bitter Lesson?",
            mode="keyword",
            limit=5,
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) == 1
    assert execution.results[0].result_type == "chunk"
    assert request_rows[0].details_json["keyword_strategy"] == "relaxed_or"
    assert request_rows[0].details_json["keyword_strict_candidate_count"] == 0
    assert request_rows[0].details_json["keyword_candidate_count"] == 1


def test_execute_search_prose_v3_persists_query_intent_and_candidate_breakdown(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    source_document_id = uuid4()
    source_run_id = uuid4()
    seed_chunk_id = uuid4()
    metadata_chunk_id = uuid4()
    adjacent_chunk_id = uuid4()
    semantic_chunk_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=seed_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=2,
                page_to=2,
                chunk_index=1,
                chunk_text="General methods that leverage computation keep winning.",
                heading="The Bitter Lesson",
                keyword_score=0.7,
                retrieval_sources=("keyword_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="UPC_CH_5.pdf",
                page_from=5,
                page_to=5,
                table_title="TABLE 5",
                table_heading="Unrelated",
                table_preview="preview",
                row_count=1,
                col_count=1,
                keyword_score=0.69,
                retrieval_sources=("keyword_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=metadata_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Metadata match",
                heading="Introduction",
                keyword_score=0.5,
                retrieval_sources=("metadata_supplement",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._expand_adjacent_chunk_context",
        lambda session, request, seed_candidates, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=adjacent_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=3,
                page_to=3,
                chunk_index=2,
                chunk_text="Adjacent context",
                heading="Discussion",
                keyword_score=0.45,
                retrieval_sources=("adjacent_context",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=semantic_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=4,
                page_to=4,
                chunk_index=3,
                chunk_text="Semantic match",
                heading="Conclusion",
                semantic_score=0.8,
                retrieval_sources=("semantic_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.get_embedding_provider",
        lambda: type("FakeProvider", (), {"embed_texts": lambda self, texts: [[0.1, 0.2]]})(),
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(
            query="What is the main claim of The Bitter Lesson?",
            mode="semantic",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]
    result_rows = [row for row in session.added if isinstance(row, SearchRequestResult)]

    assert execution.details["query_intent"] == "prose_lookup"
    assert execution.details["semantic_augmented_with_keyword_context"] is True
    assert execution.details["candidate_source_breakdown"]["keyword_primary"] == 2
    assert execution.details["candidate_source_breakdown"]["metadata_supplement"] == 1
    assert execution.details["candidate_source_breakdown"]["adjacent_context"] == 1
    assert execution.details["candidate_source_breakdown"]["semantic_primary"] == 1
    assert execution.details["metadata_candidate_count"] == 1
    assert execution.details["context_expansion_count"] == 1
    assert request_rows[0].details_json["query_intent"] == "prose_lookup"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1
    assert "heading_token_coverage" in result_rows[0].rerank_features_json
    assert "phrase_overlap" in result_rows[0].rerank_features_json
    assert "rare_token_overlap" in result_rows[0].rerank_features_json
    assert "adjacent_chunk_context_signal" in result_rows[0].rerank_features_json


def test_execute_search_uses_metadata_supplement_as_zero_result_fallback(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    document_id = uuid4()
    chunk_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=chunk_id,
                document_id=document_id,
                run_id=run_id or uuid4(),
                source_filename="fseprd1091222.pdf",
                document_title="Opaque agency document",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Metadata fallback hit",
                heading="Cover",
                keyword_score=0.9,
                retrieval_sources=("metadata_supplement",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(query="fseprd1091222", mode="keyword", limit=5, harness_name="prose_v3"),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) == 1
    assert execution.results[0].source_filename == "fseprd1091222.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "metadata_supplement"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1


def test_execute_search_default_v1_uses_metadata_supplement_for_identifier_lookup(
    monkeypatch,
) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    document_id = uuid4()
    chunk_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=chunk_id,
                document_id=document_id,
                run_id=run_id or uuid4(),
                source_filename="fseprd1091222.pdf",
                document_title="Forest Service",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Metadata fallback hit",
                heading="Cover",
                keyword_score=0.9,
                retrieval_sources=("metadata_supplement",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(query="fseprd1091222", mode="keyword", limit=5, harness_name="default_v1"),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) == 1
    assert execution.results[0].source_filename == "fseprd1091222.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "metadata_supplement"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1


def test_execute_search_adds_metadata_supplement_when_strict_recall_is_sparse(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="Consolidated BPA MOU 5-1-18.pdf",
                document_title="MEMORANDUM OF UNDERSTANDING",
                page_from=3,
                page_to=3,
                chunk_index=3,
                chunk_text="Appendix F IFPL waiver language.",
                heading="APPENDIX F IFPL WAIVER",
                keyword_score=0.3,
                retrieval_sources=("keyword_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="FEIS_Append H_AltCosts.pdf",
                document_title="Appendix H",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Alternative Cost Comparison for the integrated weed management EIS.",
                heading=None,
                keyword_score=0.25,
                retrieval_sources=("metadata_supplement",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(
            query="what does appendix h alternative costs show",
            mode="keyword",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert execution.results[0].source_filename == "FEIS_Append H_AltCosts.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "strict_plus_metadata"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1


def test_execute_search_default_v1_does_not_run_metadata_supplement(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("default_v1 should not invoke metadata supplement")
        ),
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(
            query="what does appendix h alternative costs show",
            mode="keyword",
            limit=5,
            harness_name="default_v1",
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert execution.details["metadata_candidate_count"] == 0
    assert (
        request_rows[0].details_json["candidate_source_breakdown"].get("metadata_supplement", 0)
        == 0
    )
