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
- `tunable_knobs`: allowed override fields grouped by `retrieval_profile_overrides` and `reranker_overrides`.
- `constraints`: invariants a draft must respect before apply.
- `known_tradeoffs`: expected risks when tuning the harness.
- `harness_config`: the full current config snapshot used by runtime execution.

## Repair Use

`verify_draft_harness_config` builds a descriptor for the transient draft harness and includes it in the comprehension gate. A draft should not pass comprehension unless its changed scopes are within the descriptor-backed, bounded repair surface.

## Source Of Truth

The descriptor must stay derived from code and config. Do not maintain a separate YAML or markdown list of knob values as a source of truth.
