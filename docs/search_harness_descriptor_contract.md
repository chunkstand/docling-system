# Search Harness Descriptor Contract

Status: Active v1 additive contract
Schema: `search_harness_descriptor`
Version: `1.0`

## Purpose

`GET /search/harnesses/{harness_name}/descriptor` exposes a self-description of a search harness before an agent or operator changes it.

The descriptor is derived from the live harness registry plus optional transient overrides. It is not hand-maintained shadow documentation.

## Contract

The response uses `SearchHarnessDescriptorResponse` in `app/schemas/search.py`.

Important fields:

- `config_fingerprint`: SHA-256 over the normalized harness config snapshot.
- `retrieval_stages`: readable execution stages enabled by the harness family.
- Span-level keyword and semantic stages mean candidate generation can use persisted retrieval evidence spans in addition to whole chunks and tables.
- `multivector_late_interaction_candidates_when_span_vectors_exist` means the harness can run a ColBERT-style max-sim retrieval pass over persisted span sub-vectors when embeddings are available.
- `tunable_knobs`: allowed override fields grouped by `retrieval_profile_overrides` and `reranker_overrides`.
- `constraints`: invariants a draft must respect before apply.
- `known_tradeoffs`: expected risks when tuning the harness.
- `harness_config`: the full current config snapshot used by runtime execution.

## Multivector Harness

`multivector_v1` is an opt-in harness family. It preserves the existing keyword, semantic, span-level, table-first, and reranking stages, then adds a late-interaction candidate stage when retrieval evidence span multivectors exist.

The stage stores one or more vectors per retrieval evidence span in Postgres, computes query-window vectors at request time, and scores candidates by average query-window max similarity. Search telemetry records:

- `details.late_interaction.status`
- `details.late_interaction.query_vector_count`
- `details.late_interaction.match_count`
- `details.late_interaction.candidate_count`
- per-span `metadata.late_interaction.maxsim_matches`

Those traces make a late-interaction hit explainable without treating the vector index as a black box.

## Repair Use

`verify_draft_harness_config` builds a descriptor for the transient draft harness and includes it in the comprehension gate. A draft should not pass comprehension unless its changed scopes are within the descriptor-backed, bounded repair surface.

## Source Of Truth

The descriptor must stay derived from code and config. Do not maintain a separate YAML or markdown list of knob values as a source of truth.
