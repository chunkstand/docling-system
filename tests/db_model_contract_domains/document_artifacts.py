"""DB model contract fragment for document artifacts."""

from __future__ import annotations

MODEL_SYMBOLS = (
    "DocumentRunEvaluation",
    "DocumentRunEvaluationQuery",
    "DocumentChunk",
    "DocumentTable",
    "DocumentTableSegment",
    "DocumentFigure",
)

DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS = {
    "document_run_evaluations": frozenset(
        {
            "completed_at",
            "corpus_name",
            "created_at",
            "error_message",
            "eval_version",
            "fixture_name",
            "id",
            "run_id",
            "status",
            "summary",
        }
    ),
    "document_run_evaluation_queries": frozenset(
        {
            "baseline_label",
            "baseline_rank",
            "baseline_result_type",
            "baseline_score",
            "candidate_label",
            "candidate_rank",
            "candidate_result_type",
            "candidate_score",
            "created_at",
            "details",
            "evaluation_id",
            "expected_result_type",
            "expected_top_n",
            "filters",
            "id",
            "mode",
            "passed",
            "query_text",
            "rank_delta",
        }
    ),
    "document_chunks": frozenset(
        {
            "chunk_index",
            "created_at",
            "document_id",
            "embedding",
            "heading",
            "id",
            "metadata",
            "page_from",
            "page_to",
            "run_id",
            "text",
            "textsearch",
        }
    ),
    "document_tables": frozenset(
        {
            "col_count",
            "created_at",
            "document_id",
            "embedding",
            "heading",
            "id",
            "json_path",
            "lineage_group",
            "logical_table_key",
            "metadata",
            "page_from",
            "page_to",
            "preview_text",
            "row_count",
            "run_id",
            "search_text",
            "status",
            "supersedes_table_id",
            "table_index",
            "table_version",
            "textsearch",
            "title",
            "yaml_path",
        }
    ),
    "document_table_segments": frozenset(
        {
            "created_at",
            "id",
            "metadata",
            "page_from",
            "page_to",
            "run_id",
            "segment_index",
            "segment_order",
            "source_table_ref",
            "table_id",
        }
    ),
    "document_figures": frozenset(
        {
            "caption",
            "confidence",
            "created_at",
            "document_id",
            "figure_index",
            "heading",
            "id",
            "json_path",
            "metadata",
            "page_from",
            "page_to",
            "run_id",
            "source_figure_ref",
            "status",
            "yaml_path",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "document_chunks": frozenset(
        {
            "ix_document_chunks_document_id",
            "ix_document_chunks_embedding_hnsw",
            "ix_document_chunks_page_from",
            "ix_document_chunks_page_to",
            "ix_document_chunks_textsearch",
        }
    ),
    "document_figures": frozenset(
        {
            "ix_document_figures_document_id",
            "ix_document_figures_page_from",
            "ix_document_figures_page_to",
            "ix_document_figures_run_id",
        }
    ),
    "document_run_evaluation_queries": frozenset(
        {
            "ix_document_run_evaluation_queries_evaluation_id",
            "ix_document_run_evaluation_queries_query_text",
        }
    ),
    "document_run_evaluations": frozenset(
        {"ix_document_run_evaluations_run_id", "ix_document_run_evaluations_status"}
    ),
    "document_table_segments": frozenset(
        {
            "ix_document_table_segments_page_from",
            "ix_document_table_segments_page_to",
            "ix_document_table_segments_run_id",
        }
    ),
    "document_tables": frozenset(
        {
            "ix_document_tables_document_id",
            "ix_document_tables_embedding_hnsw",
            "ix_document_tables_page_from",
            "ix_document_tables_page_to",
            "ix_document_tables_textsearch",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "document_chunks": {
        "ix_document_chunks_document_id": ("document_id",),
        "ix_document_chunks_embedding_hnsw": ("embedding",),
        "ix_document_chunks_page_from": ("page_from",),
        "ix_document_chunks_page_to": ("page_to",),
        "ix_document_chunks_textsearch": ("textsearch",),
    },
    "document_figures": {
        "ix_document_figures_document_id": ("document_id",),
        "ix_document_figures_page_from": ("page_from",),
        "ix_document_figures_page_to": ("page_to",),
        "ix_document_figures_run_id": ("run_id",),
    },
    "document_run_evaluation_queries": {
        "ix_document_run_evaluation_queries_evaluation_id": ("evaluation_id",),
        "ix_document_run_evaluation_queries_query_text": ("query_text",),
    },
    "document_run_evaluations": {
        "ix_document_run_evaluations_run_id": ("run_id",),
        "ix_document_run_evaluations_status": ("status",),
    },
    "document_table_segments": {
        "ix_document_table_segments_page_from": ("page_from",),
        "ix_document_table_segments_page_to": ("page_to",),
        "ix_document_table_segments_run_id": ("run_id",),
    },
    "document_tables": {
        "ix_document_tables_document_id": ("document_id",),
        "ix_document_tables_embedding_hnsw": ("embedding",),
        "ix_document_tables_page_from": ("page_from",),
        "ix_document_tables_page_to": ("page_to",),
        "ix_document_tables_textsearch": ("textsearch",),
    },
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "document_chunks": frozenset({"uq_document_chunks_run_chunk_index"}),
    "document_figures": frozenset({"uq_document_figures_run_figure_index"}),
    "document_run_evaluations": frozenset({"uq_document_run_evaluations_run_corpus_version"}),
    "document_table_segments": frozenset({"uq_document_table_segments_table_segment_index"}),
    "document_tables": frozenset({"uq_document_tables_run_table_index"}),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "document_chunks": {"uq_document_chunks_run_chunk_index": ("run_id", "chunk_index")},
    "document_figures": {"uq_document_figures_run_figure_index": ("run_id", "figure_index")},
    "document_run_evaluations": {
        "uq_document_run_evaluations_run_corpus_version": ("run_id", "corpus_name", "eval_version")
    },
    "document_table_segments": {
        "uq_document_table_segments_table_segment_index": ("table_id", "segment_index")
    },
    "document_tables": {"uq_document_tables_run_table_index": ("run_id", "table_index")},
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
