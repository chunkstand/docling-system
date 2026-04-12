# Ranking Dataset Schema

The ranking dataset export is produced by:

```bash
uv run docling-system-export-ranking-dataset --limit 200
```

It returns a JSON array containing two row types.

## Feedback Rows

`dataset_type = "feedback"`

These rows are mined from persisted direct-search operator labels and are intended to capture human preference signals about individual ranked results or whole-request misses.

Fields:

- `dataset_type`
- `feedback_id`
- `feedback_type`
- `search_request_id`
- `harness_name`
- `reranker_name`
- `reranker_version`
- `retrieval_profile_name`
- `query_text`
- `mode`
- `filters`
- `note`
- `created_at`
- `result_rank`
- `result_type`
- `result_id`
- `rerank_features`

Notes:

- `result_rank`, `result_type`, `result_id`, and `rerank_features` are null or empty for request-level labels such as `no_answer`, `missing_table`, and `missing_chunk`.
- `rerank_features` is the persisted feature snapshot from the original ranked result row.

## Replay Rows

`dataset_type = "replay"`

These rows are mined from persisted replay-suite query executions and are intended to capture how a harness behaved when re-running evaluation queries, live search gaps, and feedback-derived cases.

Fields:

- `dataset_type`
- `replay_query_id`
- `replay_run_id`
- `harness_name`
- `query_text`
- `mode`
- `filters`
- `expected_result_type`
- `expected_top_n`
- `passed`
- `result_count`
- `table_hit_count`
- `overlap_count`
- `added_count`
- `removed_count`
- `top_result_changed`
- `max_rank_shift`
- `details`
- `created_at`

Notes:

- `details` includes source metadata such as `source_reason`, `feedback_type`, `embedding_status`, `harness_name`, `reranker_name`, `reranker_version`, and `retrieval_profile_name` when available.
- Replay rows are useful for offline harness comparison because they preserve both the query and the observed delta signals.

## Intended Use

Use this export to:

- train or score rerankers offline
- analyze which harness versions improve or regress fixed-corpus queries
- cluster repeated live misses before promoting them into durable evaluation fixtures
- inspect which feature snapshots correlate with operator-approved results

This export is a derived operator artifact, not a source of truth. The durable source of truth remains the persisted search request, feedback, replay, and evaluation tables in Postgres.
