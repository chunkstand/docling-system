from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.db.models import SearchRequestRecord
from app.schemas.search import SearchRequest
from app.services.search import RankedResult, execute_search, search_documents


def test_prose_query_exact_source_filename_match_outranks_noisy_relaxed_table(monkeypatch) -> None:
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
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="J2-08_10222025_TK_TSMRSFireGroup.pdf",
                page_from=4,
                page_to=4,
                table_title="A750400020 4.47 4 16 A740100012 28.9 30 16",
                table_heading=None,
                table_preview="noisy numeric table",
                row_count=5,
                col_count=5,
                keyword_score=7.7,
                retrieval_sources=("keyword_relaxed",),
            ),
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="Consolidated BPA MOU 5-1-18.pdf",
                page_from=12,
                page_to=12,
                table_title="FEDERAL HOLDER ACTIVITIES AND PROJECTS",
                table_heading=None,
                table_preview="holder activities by year",
                row_count=8,
                col_count=4,
                keyword_score=4.3,
                retrieval_sources=("keyword_relaxed",),
            ),
        ],
    )

    results = search_documents(
        session=None,
        request=SearchRequest(
            query="Consolidated BPA MOU 5-1-18",
            mode="keyword",
            limit=5,
            harness_name="wide_v2",
        ),
    )

    assert results[0].source_filename == "Consolidated BPA MOU 5-1-18.pdf"


def test_execute_search_uses_camel_case_source_filename_exact_match(monkeypatch) -> None:
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
        lambda session, request, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="J3-12_12032025_TK_OverviewMaps.pdf",
                document_title="Overview Maps",
                page_from=6,
                page_to=6,
                chunk_index=6,
                chunk_text="Map label",
                heading="Babcock",
                keyword_score=0.9,
                retrieval_sources=("keyword_relaxed",),
            )
        ],
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
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="BabcockLEX.pdf",
                document_title=(
                    "Chapter 1: National Forest Land Exchanges and Land Grant Timber Companies"
                ),
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Critical look at land exchanges as viable solutions.",
                heading=None,
                keyword_score=0.2,
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
        SearchRequest(query="Babcock LEX", mode="keyword", limit=5, harness_name="prose_v3"),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert execution.results[0].source_filename == "BabcockLEX.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "relaxed_or_plus_metadata"
