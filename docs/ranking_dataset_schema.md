# Ranking Dataset Schema

The ranking dataset export is produced by:

```bash
uv run docling-system-export-ranking-dataset --limit 200
```

It returns a JSON array containing two row types.

The durable retrieval-learning ledger is materialized by:

```bash
uv run docling-system-materialize-retrieval-learning --limit 200
```

That command stores a judgment set, item-level judgments, mined hard negatives, a training run payload hash, and a semantic governance event in Postgres. The JSON export remains a lightweight derived view for offline inspection.

## Feedback Rows

`dataset_type = "feedback"`

These rows are mined from persisted direct-search operator labels and are intended to capture human preference signals about individual ranked results or whole-request misses.

Fields:

- `dataset_type`
- `row_schema_version`
- `metadata_era`
- `feedback_id`
- `feedback_type`
- `search_request_id`
- `harness_name`
- `reranker_name`
- `reranker_version`
- `retrieval_profile_name`
- `harness_config`
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

- `row_schema_version = 2` for the current export contract.
- `metadata_era` distinguishes `harness_v1` rows from `legacy_pre_harness` rows so downstream fitting code can choose whether to include older feedback.
- `result_rank`, `result_type`, `result_id`, and `rerank_features` are null or empty for request-level labels such as `no_answer`, `missing_table`, and `missing_chunk`.
- `rerank_features` is the persisted feature snapshot from the original ranked result row.

## Replay Rows

`dataset_type = "replay"`

These rows are mined from persisted replay-suite query executions and are intended to capture how a harness behaved when re-running evaluation queries, live search gaps, and feedback-derived cases.

Fields:

- `dataset_type`
- `row_schema_version`
- `metadata_era`
- `replay_query_id`
- `replay_run_id`
- `source_type`
- `harness_name`
- `reranker_name`
- `reranker_version`
- `retrieval_profile_name`
- `harness_config`
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

- `row_schema_version = 2` for the current export contract.
- `metadata_era` distinguishes modern harness-era replay rows from older replay rows that predate persisted harness snapshots.
- `details` includes source metadata such as `source_reason`, `feedback_type`, `embedding_status`, `harness_name`, `reranker_name`, `reranker_version`, and `retrieval_profile_name` when available.
- Replay rows are useful for offline harness comparison because they preserve both the query and the observed delta signals.

## Intended Use

Use this export to:

- train or score rerankers offline
- analyze which harness versions improve or regress fixed-corpus queries
- cluster repeated live misses before promoting them into durable evaluation fixtures
- inspect which feature snapshots correlate with operator-approved results

This export is a derived operator artifact, not a source of truth. The durable source of truth remains the persisted search request, feedback, replay, evaluation, and retrieval-learning ledger tables in Postgres:

- `retrieval_judgment_sets` records the source mix, criteria, counts, and canonical payload hash.
- `retrieval_judgments` stores positive, negative, and missing judgments with query, harness, result, rerank feature, evidence-span references, and stable source payload hashes.
- `retrieval_hard_negatives` stores explicit and mined hard negatives for reranker training, including direct source request/replay references, evidence-span refs, stable source payload hashes, and optional positive judgment pair links.
- `retrieval_training_runs` stores the canonical training payload, total training example count, and a link to `semantic_governance_events` for auditability.
- `retrieval_learning_candidate_evaluations` links one training run to a candidate search harness evaluation and release gate, including the training dataset hash, candidate metrics, gate outcome, package hash, and governance event. This is the auditable bridge from learned retrieval data to a candidate retrieval behavior decision.
