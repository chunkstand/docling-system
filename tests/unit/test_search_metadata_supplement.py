from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.db.public.ingest import Document
from app.schemas.search import SearchRequest
from app.services.search import RankedResult, execute_search
from app.services.search_metadata_supplement import (
    _document_metadata_candidate_statement,
    _ranked_metadata_overlap_score,
    _run_prose_metadata_chunk_search,
    _should_run_metadata_supplement,
)


def _ranked_chunk() -> RankedResult:
    return RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="report.pdf",
        page_from=1,
        page_to=1,
        chunk_text="chunk text",
        heading="Heading",
    )


def test_metadata_supplement_runs_for_prose_v3_and_identifier_zero_result_queries() -> None:
    assert (
        _should_run_metadata_supplement(
            query="What is the main claim of The Bitter Lesson?",
            query_intent="prose_broad",
            strict_keyword_count=5,
            keyword_chunk_count=1,
            keyword_table_count=1,
            harness_name="prose_v3",
        )
        is True
    )
    assert (
        _should_run_metadata_supplement(
            query="fseprd1091222",
            query_intent="prose_lookup",
            strict_keyword_count=0,
            keyword_chunk_count=0,
            keyword_table_count=0,
            harness_name="default_v1",
        )
        is True
    )
    assert (
        _should_run_metadata_supplement(
            query="what does appendix h alternative costs show",
            query_intent="prose_broad",
            strict_keyword_count=0,
            keyword_chunk_count=0,
            keyword_table_count=0,
            harness_name="default_v1",
        )
        is False
    )
    assert (
        _should_run_metadata_supplement(
            query="mesa restoration outlook distinct prose recall",
            query_intent="prose_lookup",
            strict_keyword_count=1,
            keyword_chunk_count=0,
            keyword_table_count=1,
            harness_name="default_v1",
        )
        is True
    )
    assert (
        _should_run_metadata_supplement(
            query="TABLE 701.2",
            query_intent="tabular",
            strict_keyword_count=1,
            keyword_chunk_count=0,
            keyword_table_count=1,
            harness_name="prose_v3",
        )
        is False
    )


def test_ranked_metadata_overlap_score_uses_chunk_text_signal() -> None:
    score_without_chunk = _ranked_metadata_overlap_score(
        "dear interested party chalk buttes",
        document_title="Chalk Buttes Cover Letter",
        heading=None,
        chunk_text=None,
        source_filename="Chalk Buttes Cover Letter.pdf",
    )
    score_with_chunk = _ranked_metadata_overlap_score(
        "dear interested party chalk buttes",
        document_title="Chalk Buttes Cover Letter",
        heading=None,
        chunk_text="Dear Interested Party,",
        source_filename="Chalk Buttes Cover Letter.pdf",
    )

    assert score_with_chunk > score_without_chunk


def test_ranked_metadata_overlap_score_ignores_filename_when_document_scoped() -> None:
    with_document_context = _ranked_metadata_overlap_score(
        "forest habitat types and abies lasiocarpa streptopus amplexifolius",
        document_title="Forest habitat types for northern Idaho",
        heading=None,
        chunk_text=None,
        source_filename="CooperEtAl_1991_ForestHabitatNIDSecondApproximation.pdf",
    )
    scoped_to_document = _ranked_metadata_overlap_score(
        "forest habitat types and abies lasiocarpa streptopus amplexifolius",
        document_title="Forest habitat types for northern Idaho",
        heading=None,
        chunk_text=None,
        source_filename="CooperEtAl_1991_ForestHabitatNIDSecondApproximation.pdf",
        include_document_context=False,
    )

    assert scoped_to_document < with_document_context
    assert scoped_to_document == 0.0


def test_hybrid_search_resorts_metadata_candidates_before_rrf(monkeypatch) -> None:
    winning_document_id = uuid4()
    losing_document_id = uuid4()

    class FakeEmbeddingProvider:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

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
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260325_ChalkButtes_Hydro.pdf",
                document_title="Chalk Buttes Hydrology",
                page_from=2,
                page_to=2,
                chunk_text="Hydrology design features overview.",
                heading=None,
                keyword_score=0.8,
                retrieval_sources=("keyword",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=winning_document_id,
                run_id=uuid4(),
                source_filename="April 17 2026 Chalk Buttes Billings Gazette Legal Notice.pdf",
                document_title="April 17 2026 Chalk Buttes Billings Gazette Legal Notice",
                page_from=1,
                page_to=1,
                chunk_text="Published in the Billings Gazette on April 17, 2026.",
                heading=None,
                keyword_score=4.6,
                retrieval_sources=("metadata_supplement",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260325_ChalkButtes_Hydro.pdf",
                document_title="Chalk Buttes Hydrology",
                page_from=3,
                page_to=3,
                chunk_text="Hydrology background discussion.",
                heading=None,
                semantic_score=0.92,
                retrieval_sources=("semantic",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.get_embedding_provider", lambda: FakeEmbeddingProvider()
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    execution = execute_search(
        FakeSession(),
        SearchRequest(
            query="published in billings gazette on april 17 2026 chalk buttes",
            mode="hybrid",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="test",
    )

    assert execution.results[0].document_id == winning_document_id
    assert execution.results[0].source_filename.endswith("Billings Gazette Legal Notice.pdf")


def test_run_prose_metadata_chunk_search_uses_textsearch_queries_without_ilike() -> None:
    winning_document = SimpleNamespace(
        id=uuid4(),
        title="Chalk Buttes Cover Letter",
        source_filename="Chalk Buttes Cover Letter.pdf",
    )
    losing_document = SimpleNamespace(
        id=uuid4(),
        title="Chalk Buttes Silviculture",
        source_filename="20260407_ChalkButtes_Silviculture.pdf",
    )
    winning_chunk = SimpleNamespace(
        id=uuid4(),
        document_id=winning_document.id,
        run_id=uuid4(),
        page_from=1,
        page_to=1,
        chunk_index=0,
        text="Dear Interested Party, the Chalk Buttes project is available for review.",
        heading=None,
    )
    losing_chunk = SimpleNamespace(
        id=uuid4(),
        document_id=losing_document.id,
        run_id=uuid4(),
        page_from=2,
        page_to=2,
        chunk_index=1,
        text="Chalk Buttes silviculture overview.",
        heading=None,
    )

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return list(self._rows)

        def scalars(self):
            return self

    class FakeSession:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def execute(self, statement):
            self.statements.append(str(statement))
            if len(self.statements) == 1:
                return FakeResult([])
            if len(self.statements) == 2:
                return FakeResult(
                    [
                        (winning_document, 0.8),
                        (losing_document, 0.2),
                    ]
                )
            return FakeResult(
                [
                    (winning_chunk, winning_document),
                    (losing_chunk, losing_document),
                ]
            )

    session = FakeSession()
    results = _run_prose_metadata_chunk_search(
        session,
        SearchRequest(query="Chalk Buttes Cover Letter", mode="keyword", limit=5),
    )

    assert results[0].source_filename == "Chalk Buttes Cover Letter.pdf"
    assert any("metadata_textsearch" in statement for statement in session.statements)
    assert any("@@" in statement for statement in session.statements)
    assert all("ILIKE" not in statement.upper() for statement in session.statements)


def test_document_metadata_candidate_statement_uses_exists_for_run_scope() -> None:
    request = SearchRequest(query="Blue Mesas readiness narrative", mode="keyword", limit=5)
    run_id = uuid4()
    tsquery = func.to_tsquery("english", "blue | mesas | readiness")
    rank = func.ts_rank_cd(Document.metadata_textsearch, tsquery)
    statement = _document_metadata_candidate_statement(
        request,
        run_id=run_id,
        document_conditions=[Document.metadata_textsearch.op("@@")(tsquery)],
        document_rank=rank,
        candidate_limit=6,
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "SELECT DISTINCT" not in compiled
    assert "EXISTS (" in compiled
    assert "document_chunks.run_id" in compiled


def test_document_metadata_textsearch_ddl_uses_valid_generated_column_syntax() -> None:
    ddl = str(CreateTable(Document.__table__).compile(dialect=postgresql.dialect()))

    assert "metadata_textsearch TSVECTOR GENERATED ALWAYS AS" in ddl
    assert "STORED NOT NULL" not in ddl


def test_prose_v3_metadata_supplement_prefers_exact_phrase_cover_letter_probe(
    monkeypatch,
) -> None:
    winning_document_id = uuid4()
    losing_document_id = uuid4()

    class FakeEmbeddingProvider:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

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
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=winning_document_id,
                run_id=uuid4(),
                source_filename="Chalk Buttes Cover Letter.pdf",
                document_title="Chalk Buttes Cover Letter",
                page_from=1,
                page_to=1,
                chunk_text=(
                    "Dear Interested Party, the Chalk Buttes project is available for review."
                ),
                heading=None,
                keyword_score=6.5,
                retrieval_sources=("metadata_supplement",),
            ),
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260407_ChalkButtes_Silviculture.pdf",
                document_title="Chalk Buttes Silviculture",
                page_from=2,
                page_to=2,
                chunk_text="Chalk Buttes silviculture overview.",
                heading=None,
                keyword_score=1.1,
                retrieval_sources=("metadata_supplement",),
            ),
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260407_ChalkButtes_Silviculture.pdf",
                document_title="Chalk Buttes Silviculture",
                page_from=3,
                page_to=3,
                chunk_text="Generic Chalk Buttes report language.",
                heading=None,
                semantic_score=0.92,
                retrieval_sources=("semantic",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.get_embedding_provider", lambda: FakeEmbeddingProvider()
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    execution = execute_search(
        FakeSession(),
        SearchRequest(
            query="dear interested party chalk buttes",
            mode="keyword",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="test",
    )

    assert execution.results[0].document_id == winning_document_id
    assert execution.results[0].source_filename == "Chalk Buttes Cover Letter.pdf"
