from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.db.models import (
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.schemas.search import SearchRequest
from app.services.search import (
    RankedResult,
    execute_search,
)


def test_execute_search_persists_request_and_result_snapshots(monkeypatch) -> None:
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
                source_filename="doc.pdf",
                page_from=3,
                page_to=3,
                chunk_text="vent stack content",
                heading="Venting",
                keyword_score=0.6,
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
                source_filename="doc.pdf",
                page_from=2,
                page_to=2,
                table_title="TABLE 1",
                table_heading="Vent stack sizes",
                table_preview="Diameter | Height",
                row_count=2,
                col_count=2,
                keyword_score=0.7,
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
        SearchRequest(query="table 1", mode="keyword", limit=5),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]
    result_rows = [row for row in session.added if isinstance(row, SearchRequestResult)]
    operator_rows = [row for row in session.added if isinstance(row, KnowledgeOperatorRun)]
    operator_output_rows = [
        row for row in session.added if isinstance(row, KnowledgeOperatorOutput)
    ]

    assert execution.request_id is not None
    assert len(execution.evidence_operator_run_ids) == 3
    assert execution.harness_name == "default_v1"
    assert execution.reranker_name == "linear_feature_reranker"
    assert execution.reranker_version == "v1"
    assert execution.retrieval_profile_name == "default_v1"
    assert request_rows[0].origin == "api"
    assert request_rows[0].tabular_query is True
    assert request_rows[0].details_json["served_mode"] == "keyword"
    assert result_rows[0].rerank_features_json["final_score"] >= result_rows[0].score
    assert "source_filename_token_coverage" in result_rows[0].rerank_features_json
    assert "document_title_token_coverage" in result_rows[0].rerank_features_json
    assert "document_cluster_strength" in result_rows[0].rerank_features_json
    assert [row.operator_kind for row in operator_rows] == ["retrieve", "rerank", "judge"]
    assert operator_rows[1].parent_operator_run_id == operator_rows[0].id
    assert operator_rows[2].parent_operator_run_id == operator_rows[1].id
    selected_outputs = [
        row for row in operator_output_rows if row.output_kind == "selected_evidence"
    ]
    assert selected_outputs
    assert selected_outputs[0].payload_json["preview_text"]


def test_execute_search_does_not_rollback_before_persisting_evaluation_request(monkeypatch) -> None:
    class FakeProvider:
        def embed_texts(self, texts):
            assert texts == ["What is the main claim of The Bitter Lesson?"]
            return [[0.1, 0.2, 0.3]]

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.rollback_calls = 0

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

        def rollback(self) -> None:
            self.rollback_calls += 1

    keyword_candidate = RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="The Bitter Lesson.pdf",
        document_title="The Bitter Lesson",
        page_from=1,
        page_to=1,
        chunk_index=0,
        chunk_text="General methods that leverage computation are ultimately the most effective.",
        heading="The Bitter Lesson",
        keyword_score=0.8,
        retrieval_sources=("keyword_primary",),
    )
    semantic_candidate = RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=keyword_candidate.document_id,
        run_id=keyword_candidate.run_id,
        source_filename="The Bitter Lesson.pdf",
        document_title="The Bitter Lesson",
        page_from=1,
        page_to=1,
        chunk_index=0,
        chunk_text=keyword_candidate.chunk_text,
        heading="The Bitter Lesson",
        semantic_score=0.9,
        retrieval_sources=("semantic_primary",),
    )

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [keyword_candidate],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [
            semantic_candidate
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [],
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
            mode="hybrid",
            limit=5,
            harness_name="default_v1",
        ),
        embedding_provider=FakeProvider(),
        origin="api",
        evaluation_id=uuid4(),
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) >= 1
    assert session.rollback_calls == 0
    assert len(request_rows) == 1
    assert request_rows[0].evaluation_id is not None
