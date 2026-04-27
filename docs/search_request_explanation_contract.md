# Search Request Explanation Contract

Status: Active v1 additive contract
Schema: `search_request_explanation`
Version: `1.0`

## Purpose

`GET /search/requests/{search_request_id}/explain` turns persisted search telemetry into one canonical explanation that humans and agents can inspect without reading raw database rows.

The explanation is deterministic. It is built from the persisted `search_requests`, `search_request_results`, and captured harness snapshot. It does not use prompt-only memory or a model call.

## Contract

The response uses `SearchRequestExplanationResponse` in `app/schemas/search.py`.

Required interpretation rules:

- `schema_name` must be `search_request_explanation`.
- `schema_version` must be `1.0`.
- `requested_mode` and `served_mode` explain whether the system honored the requested keyword, semantic, or hybrid mode.
- `harness_config` is the captured config snapshot from request execution, not a live lookup.
- `span_candidate_count` reports how many final candidates carried persisted retrieval evidence span citations.
- `selected_result_span_count` appears in `details` and reports how many selected results have span citations after final citation attachment.
- `late_interaction_candidate_count` reports how many final candidates came from the opt-in multivector late-interaction path when that harness stage ran.
- `top_result_snapshot` is a compact result summary for review, not a replacement for `/search/requests/{id}`.
- `diagnosis.category` is a bounded system classification, not a human judgment.
- `recommended_next_action` is advisory and must not mutate runtime state.

## Diagnosis Taxonomy

- `healthy`: persisted telemetry does not expose an obvious recall or fallback failure.
- `fallback_only`: semantic-capable execution fell back to keyword behavior.
- `filter_overconstraint`: filters removed all observable candidates/results.
- `table_recall_gap`: a tabular query returned no table hits.
- `low_recall`: candidate or result counts are too low to support ranking-only repair.
- `metadata_bias`: metadata supplement candidates dominate the candidate mix.
- `bad_ranking`: relevant result-type evidence exists but appears suppressed by ranking.

## Evidence Rules

Explanations must be reconstructable from persisted state. If a future explanation field depends on transient runtime state, that field must either be persisted first or marked advisory outside this contract.

Span candidate counts are derived from persisted search telemetry and result-span citation rows. The full span text/hash evidence belongs in `/search/requests/{id}` and `/search/requests/{id}/evidence-package`, not in the compact explanation snapshot.

If an active legacy run is missing retrieval evidence spans, search may rebuild the span index before candidate generation and record `details.retrieval_span_backfill`. That backfill is additive and derived from canonical chunk/table rows.

For `multivector_v1`, persisted request details and result-span metadata include the late-interaction max-sim trace. The compact explanation should summarize candidate counts and fallback status, while the detailed request surfaces retain query-vector hashes, span-vector ids, vector text, token ranges, and similarity scores. `/search/requests/{id}/evidence-package` also materializes the referenced span-vector rows with content, embedding, and snapshot hashes.

YAML renderings may be added as derived artifacts, but JSON remains the machine-facing contract.
