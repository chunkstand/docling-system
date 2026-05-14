"""DB model retrieval contract fragment for retrieval interactions."""

from __future__ import annotations

TABLE_COLUMNS = {
    "search_requests": frozenset(
        {
            "candidate_count",
            "created_at",
            "details",
            "duration_ms",
            "embedding_error",
            "embedding_status",
            "evaluation_id",
            "filters",
            "harness_config",
            "harness_name",
            "id",
            "limit",
            "mode",
            "origin",
            "parent_request_id",
            "query_text",
            "reranker_name",
            "reranker_version",
            "result_count",
            "retrieval_profile_name",
            "run_id",
            "table_hit_count",
            "tabular_query",
        }
    ),
    "search_request_results": frozenset(
        {
            "base_rank",
            "chunk_id",
            "created_at",
            "document_id",
            "hybrid_score",
            "id",
            "keyword_score",
            "label",
            "page_from",
            "page_to",
            "preview_text",
            "rank",
            "rerank_features",
            "result_type",
            "run_id",
            "score",
            "search_request_id",
            "semantic_score",
            "source_filename",
            "table_id",
        }
    ),
    "retrieval_evidence_spans": frozenset(
        {
            "chunk_id",
            "content_sha256",
            "created_at",
            "document_id",
            "embedding",
            "heading",
            "id",
            "metadata",
            "page_from",
            "page_to",
            "run_id",
            "source_id",
            "source_snapshot_sha256",
            "source_type",
            "span_index",
            "span_text",
            "table_id",
            "textsearch",
        }
    ),
    "retrieval_evidence_span_multivectors": frozenset(
        {
            "content_sha256",
            "created_at",
            "document_id",
            "embedding",
            "embedding_dim",
            "embedding_model",
            "embedding_sha256",
            "id",
            "metadata",
            "retrieval_evidence_span_id",
            "run_id",
            "source_id",
            "source_type",
            "token_end",
            "token_start",
            "vector_index",
            "vector_text",
        }
    ),
    "search_request_result_spans": frozenset(
        {
            "content_sha256",
            "created_at",
            "id",
            "metadata",
            "page_from",
            "page_to",
            "retrieval_evidence_span_id",
            "score",
            "score_kind",
            "search_request_id",
            "search_request_result_id",
            "source_id",
            "source_snapshot_sha256",
            "source_type",
            "span_index",
            "span_rank",
            "text_excerpt",
        }
    ),
    "search_feedback": frozenset(
        {
            "created_at",
            "feedback_type",
            "id",
            "note",
            "result_rank",
            "search_request_id",
            "search_request_result_id",
        }
    ),
    "chat_answer_records": frozenset(
        {
            "answer_text",
            "citations",
            "created_at",
            "document_id",
            "harness_name",
            "id",
            "mode",
            "model",
            "question_text",
            "reranker_name",
            "reranker_version",
            "retrieval_profile_name",
            "search_request_id",
            "used_fallback",
            "warning",
        }
    ),
    "chat_answer_feedback": frozenset(
        {"chat_answer_id", "created_at", "feedback_type", "id", "note"}
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "search_requests": frozenset(
        {
            "ix_search_requests_created_at",
            "ix_search_requests_evaluation_id",
            "ix_search_requests_origin_created_at",
            "ix_search_requests_parent_request_id",
        }
    ),
    "search_request_results": frozenset(
        {"ix_search_request_results_result_type", "ix_search_request_results_search_request_id"}
    ),
    "retrieval_evidence_spans": frozenset(
        {
            "ix_retrieval_evidence_spans_chunk_id",
            "ix_retrieval_evidence_spans_content_sha256",
            "ix_retrieval_evidence_spans_document_id",
            "ix_retrieval_evidence_spans_embedding_hnsw",
            "ix_retrieval_evidence_spans_page_from",
            "ix_retrieval_evidence_spans_page_to",
            "ix_retrieval_evidence_spans_run_id",
            "ix_retrieval_evidence_spans_source",
            "ix_retrieval_evidence_spans_table_id",
            "ix_retrieval_evidence_spans_textsearch",
        }
    ),
    "retrieval_evidence_span_multivectors": frozenset(
        {
            "ix_retrieval_span_multivectors_content_sha256",
            "ix_retrieval_span_multivectors_document_id",
            "ix_retrieval_span_multivectors_embedding_hnsw",
            "ix_retrieval_span_multivectors_embedding_sha256",
            "ix_retrieval_span_multivectors_model",
            "ix_retrieval_span_multivectors_run_id",
            "ix_retrieval_span_multivectors_source",
            "ix_retrieval_span_multivectors_span_id",
        }
    ),
    "search_request_result_spans": frozenset(
        {
            "ix_search_request_result_spans_content_sha256",
            "ix_search_request_result_spans_request_id",
            "ix_search_request_result_spans_result_id",
            "ix_search_request_result_spans_source",
            "ix_search_request_result_spans_span_id",
        }
    ),
    "search_feedback": frozenset(
        {
            "ix_search_feedback_created_at",
            "ix_search_feedback_feedback_type",
            "ix_search_feedback_search_request_id",
            "ix_search_feedback_search_request_result_id",
        }
    ),
    "chat_answer_records": frozenset(
        {"ix_chat_answer_records_created_at", "ix_chat_answer_records_search_request_id"}
    ),
    "chat_answer_feedback": frozenset(
        {
            "ix_chat_answer_feedback_answer_id",
            "ix_chat_answer_feedback_created_at",
            "ix_chat_answer_feedback_feedback_type",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "search_requests": {
        "ix_search_requests_created_at": ("created_at",),
        "ix_search_requests_origin_created_at": ("origin", "created_at"),
        "ix_search_requests_evaluation_id": ("evaluation_id",),
        "ix_search_requests_parent_request_id": ("parent_request_id",),
    },
    "search_request_results": {
        "ix_search_request_results_search_request_id": ("search_request_id",),
        "ix_search_request_results_result_type": ("result_type",),
    },
    "retrieval_evidence_spans": {
        "ix_retrieval_evidence_spans_document_id": ("document_id",),
        "ix_retrieval_evidence_spans_run_id": ("run_id",),
        "ix_retrieval_evidence_spans_source": ("source_type", "source_id"),
        "ix_retrieval_evidence_spans_chunk_id": ("chunk_id",),
        "ix_retrieval_evidence_spans_table_id": ("table_id",),
        "ix_retrieval_evidence_spans_page_from": ("page_from",),
        "ix_retrieval_evidence_spans_page_to": ("page_to",),
        "ix_retrieval_evidence_spans_content_sha256": ("content_sha256",),
        "ix_retrieval_evidence_spans_textsearch": ("textsearch",),
        "ix_retrieval_evidence_spans_embedding_hnsw": ("embedding",),
    },
    "retrieval_evidence_span_multivectors": {
        "ix_retrieval_span_multivectors_span_id": ("retrieval_evidence_span_id",),
        "ix_retrieval_span_multivectors_document_id": ("document_id",),
        "ix_retrieval_span_multivectors_run_id": ("run_id",),
        "ix_retrieval_span_multivectors_source": ("source_type", "source_id"),
        "ix_retrieval_span_multivectors_model": ("embedding_model",),
        "ix_retrieval_span_multivectors_content_sha256": ("content_sha256",),
        "ix_retrieval_span_multivectors_embedding_sha256": ("embedding_sha256",),
        "ix_retrieval_span_multivectors_embedding_hnsw": ("embedding",),
    },
    "search_request_result_spans": {
        "ix_search_request_result_spans_request_id": ("search_request_id",),
        "ix_search_request_result_spans_result_id": ("search_request_result_id",),
        "ix_search_request_result_spans_span_id": ("retrieval_evidence_span_id",),
        "ix_search_request_result_spans_source": ("source_type", "source_id"),
        "ix_search_request_result_spans_content_sha256": ("content_sha256",),
    },
    "search_feedback": {
        "ix_search_feedback_search_request_id": ("search_request_id",),
        "ix_search_feedback_search_request_result_id": ("search_request_result_id",),
        "ix_search_feedback_feedback_type": ("feedback_type",),
        "ix_search_feedback_created_at": ("created_at",),
    },
    "chat_answer_records": {
        "ix_chat_answer_records_search_request_id": ("search_request_id",),
        "ix_chat_answer_records_created_at": ("created_at",),
    },
    "chat_answer_feedback": {
        "ix_chat_answer_feedback_answer_id": ("chat_answer_id",),
        "ix_chat_answer_feedback_feedback_type": ("feedback_type",),
        "ix_chat_answer_feedback_created_at": ("created_at",),
    },
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "search_request_results": frozenset({"uq_search_request_results_request_rank"}),
    "retrieval_evidence_spans": frozenset({"uq_retrieval_evidence_spans_run_source_span"}),
    "retrieval_evidence_span_multivectors": frozenset(
        {"uq_retrieval_span_multivectors_span_vector"}
    ),
    "search_request_result_spans": frozenset({"uq_search_request_result_spans_result_rank"}),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "search_request_results": {
        "uq_search_request_results_request_rank": ("search_request_id", "rank")
    },
    "retrieval_evidence_spans": {
        "uq_retrieval_evidence_spans_run_source_span": (
            "run_id",
            "source_type",
            "source_id",
            "span_index",
        )
    },
    "retrieval_evidence_span_multivectors": {
        "uq_retrieval_span_multivectors_span_vector": ("retrieval_evidence_span_id", "vector_index")
    },
    "search_request_result_spans": {
        "uq_search_request_result_spans_result_rank": ("search_request_result_id", "span_rank")
    },
}

REQUIRED_VECTOR_DIMENSIONS = {
    "retrieval_evidence_spans": {"embedding": 1536},
    "retrieval_evidence_span_multivectors": {"embedding": 1536},
}

REQUIRED_COMPUTED_SQL = {
    "retrieval_evidence_spans": {
        "textsearch": "setweight(to_tsvector('english', "
        "coalesce(heading, '')), 'A') || "
        "to_tsvector('english', "
        "coalesce(span_text, ''))"
    }
}
