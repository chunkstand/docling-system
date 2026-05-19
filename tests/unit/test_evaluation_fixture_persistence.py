from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import yaml

from app.schemas.search import SearchResult, SearchScores
from app.services.evaluation_fixtures import ensure_auto_evaluation_fixture, fixture_for_document


def test_ensure_auto_evaluation_fixture_writes_auto_corpus_entry(monkeypatch, tmp_path) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    tables = [
        SimpleNamespace(
            title="Table 3 Transportation Mitigations",
            heading="Transportation mitigations",
            preview_text="Transportation mitigations by route segment.",
            search_text="Transportation mitigations by route segment.",
        )
    ]
    figures = [
        SimpleNamespace(
            caption="Figure 1. Proposed access route.",
            json_path="/tmp/figure.json",
            yaml_path="/tmp/figure.yaml",
            metadata_json={"provenance": [{"page_no": 2}]},
        )
    ]
    chunks = [
        SimpleNamespace(
            heading="Executive Summary",
            text="Transportation mitigation measures are required for the proposed route.",
        )
    ]

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeSession:
        def __init__(self):
            self._results = [tables, figures, chunks]
            self.calls = 0

        def execute(self, _query):
            rows = self._results[self.calls]
            self.calls += 1
            return FakeResult(rows)

    monkeypatch.setattr(
        "app.services.evaluation_fixtures.search_documents",
        lambda *args, **kwargs: [],
    )

    fixture = ensure_auto_evaluation_fixture(
        FakeSession(),
        SimpleNamespace(
            id=uuid4(),
            source_filename="autogen_doc.pdf",
            sha256="abc123",
            title="Autogen Document",
        ),
        SimpleNamespace(id=uuid4()),
    )

    auto_corpus_path = storage_root / "evaluation_corpus.auto.yaml"
    assert auto_corpus_path.exists() is True
    assert fixture["source_filename"] == "autogen_doc.pdf"
    assert fixture["sha256"] == "abc123"
    assert fixture["thresholds"]["expected_logical_table_count"] == 1
    loaded = fixture_for_document(
        SimpleNamespace(source_filename="autogen_doc.pdf", sha256="abc123")
    )
    assert loaded is not None
    assert loaded.name == fixture["name"]


def test_ensure_auto_evaluation_fixture_keeps_only_retrieval_backed_queries(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    tables = [
        SimpleNamespace(
            title="Table 3 Transportation Mitigations",
            heading="Transportation mitigations",
            preview_text="Transportation mitigations by route segment.",
            search_text="Transportation mitigations by route segment.",
        )
    ]
    figures: list[object] = []
    chunks = [
        SimpleNamespace(
            heading="Executive Summary",
            text="Transportation mitigation measures are required for the proposed route.",
        )
    ]

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeSession:
        def __init__(self):
            self._results = [tables, figures, chunks]
            self.calls = 0

        def execute(self, _query):
            rows = self._results[self.calls]
            self.calls += 1
            return FakeResult(rows)

    def fake_search_documents(_session, request, *_args, **_kwargs):
        if request.query in {
            "Table 3 Transportation Mitigations",
            "Transportation Mitigations",
        }:
            return [
                SearchResult(
                    result_type="table",
                    document_id=uuid4(),
                    run_id=uuid4(),
                    score=0.9,
                    table_id=uuid4(),
                    table_title="Table 3 Transportation Mitigations",
                    table_heading="Transportation mitigations",
                    table_preview="Transportation mitigations by route segment.",
                    row_count=3,
                    col_count=2,
                    page_from=1,
                    page_to=1,
                    source_filename="autogen_doc.pdf",
                    scores=SearchScores(keyword_score=0.9, hybrid_score=0.9),
                )
            ]
        return [
            SearchResult(
                result_type="table",
                document_id=uuid4(),
                run_id=uuid4(),
                score=0.5,
                table_id=uuid4(),
                table_title="Table 3 Transportation Mitigations",
                table_heading="Transportation mitigations",
                table_preview="Transportation mitigations by route segment.",
                row_count=3,
                col_count=2,
                page_from=1,
                page_to=1,
                source_filename="autogen_doc.pdf",
                scores=SearchScores(keyword_score=0.5, hybrid_score=0.5),
            )
        ]

    monkeypatch.setattr("app.services.evaluation_fixtures.search_documents", fake_search_documents)

    fixture = ensure_auto_evaluation_fixture(
        FakeSession(),
        SimpleNamespace(
            id=uuid4(),
            source_filename="autogen_doc.pdf",
            sha256="abc123",
            title="Autogen Document",
        ),
        SimpleNamespace(id=uuid4()),
    )

    thresholds = fixture["thresholds"]
    assert len(thresholds["expected_top_n_table_hit_queries"]) == 1
    assert thresholds["expected_top_n_table_hit_queries"][0]["query"] in {
        "Table 3 Transportation Mitigations",
        "Transportation Mitigations",
    }
    assert thresholds["expected_top_n_chunk_hit_queries"] == []


def test_fixture_for_document_prefers_auto_fixture_over_manual_filename_match(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )
    storage_root.mkdir(parents=True, exist_ok=True)
    (storage_root / "evaluation_corpus.auto.yaml").write_text(
        """
documents:
  - name: auto_test_pdf
    kind: auto_generated_document
    source_filename: TEST_PDF.pdf
    thresholds:
      expected_top_n_chunk_hit_queries:
        - query: Automatic query
"""
    )

    fixture = fixture_for_document(SimpleNamespace(source_filename="TEST_PDF.pdf"))

    assert fixture is not None
    assert fixture.name == "auto_test_pdf"


def test_ensure_auto_evaluation_fixture_keeps_other_same_filename_sha256_entries(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )
    storage_root.mkdir(parents=True, exist_ok=True)
    auto_corpus_path = storage_root / "evaluation_corpus.auto.yaml"
    auto_corpus_path.write_text(
        """
documents:
  - name: auto_duplicate_old
    kind: auto_generated_document
    source_filename: duplicate.pdf
    sha256: oldsha
    thresholds:
      expected_top_n_chunk_hit_queries:
        - query: Old query
"""
    )

    tables: list[object] = []
    figures: list[object] = []
    chunks = [SimpleNamespace(heading=None, text="Fresh duplicate document content.")]

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeSession:
        def __init__(self):
            self._results = [tables, figures, chunks]
            self.calls = 0

        def execute(self, _query):
            rows = self._results[self.calls]
            self.calls += 1
            return FakeResult(rows)

    monkeypatch.setattr(
        "app.services.evaluation_fixtures.search_documents",
        lambda *args, **kwargs: [],
    )

    fixture = ensure_auto_evaluation_fixture(
        FakeSession(),
        SimpleNamespace(
            id=uuid4(),
            source_filename="duplicate.pdf",
            sha256="newsha",
            title="New Duplicate",
        ),
        SimpleNamespace(id=uuid4()),
    )

    payload = yaml.safe_load(auto_corpus_path.read_text())
    documents = payload["documents"]

    assert fixture["sha256"] == "newsha"
    assert len(documents) == 2
    assert {document["sha256"] for document in documents} == {"oldsha", "newsha"}
