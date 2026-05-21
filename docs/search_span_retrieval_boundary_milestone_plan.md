# Search Span Retrieval Boundary Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: resolved locally in committed but unpushed state through closeout
commit `0c007206`. The packet reduces
`app/services/search_retrieval_primitives.py` to `312` lines by moving the
span-search and late-interaction retrieval path into
`app/services/search_span_retrieval.py` at `378` lines, preserves the
compatibility seam used by `app/services/search.py`, and advances the
broader-rebaseline residual queue to `app/services/search_harnesses.py`.
Owner context: fresh broader rebaseline after the 2026-05-20
architecture-quality refresh (`8b0ea812`) surfaced
`app/services/search_retrieval_primitives.py` as the top real search-family
owner above the default `600`-line budget while the routed queue remained
empty at `top_routed_hotspot_paths=[]`.

## Purpose

Reduce the next real search owner without pretending the remaining search
residual debt is only in CLI or test roots.

This packet closes the narrowest honest slice by:

- keeping `app/services/search_retrieval_primitives.py` focused on
  document/chunk/table retrieval primitives and the compatibility re-exports
- moving span keyword retrieval, span semantic retrieval, and multivector
  late-interaction logic into `app/services/search_span_retrieval.py`
- moving the direct owner tests for the moved functions into
  `tests/unit/test_search_span_retrieval.py`
- keeping `tests/unit/test_search_retrieval_primitives.py` as a compact
  compatibility-seam check instead of another mixed owner root
- recording the new search owner in `config/hotspot_prevention.yaml` so the
  compatibility facade and the broader rebaseline route stay honest

## Non-Goals

- No search-harness registry or reranker refactor in this packet.
- No CLI changes in `app/cli_commands/search_harness.py`.
- No new coverage moved into `tests/unit/test_cli_search_harness.py` or
  `tests/unit/test_search_api_harnesses.py`.
- No API contract changes to `/search`.

## Local Closeout Update

- `app/services/search_retrieval_primitives.py` now closes at `312` lines.
- `app/services/search_span_retrieval.py` now owns the moved span and
  late-interaction retrieval path at `378` lines.
- `tests/unit/test_search_retrieval_primitives.py` now closes at `23` lines as
  a compatibility-seam check, and the direct owner coverage now lives in
  `tests/unit/test_search_span_retrieval.py` at `52` lines.
- `config/hotspot_prevention.yaml` now records
  `app/services/search_span_retrieval.py` as an explicit search-family owner
  path under the reduced `app/services/search.py` compatibility facade.
- The bounded search-span split is committed locally as `0c007206`
  (`Split search span retrieval owner`).
- The live architecture-quality summary now reports
  `broader_rebaseline_candidate_count=4` with
  `top_broader_rebaseline_paths=[app/services/search_harnesses.py, app/cli_commands/search_harness.py, tests/unit/test_cli_search_harness.py, tests/unit/test_search_api_harnesses.py]`.

Debt-shift audit:

- `app/services/search_harnesses.py` (`627` lines),
  `app/cli_commands/search_harness.py` (`604`),
  `tests/unit/test_cli_search_harness.py` (`714`), and
  `tests/unit/test_search_api_harnesses.py` (`764`) stayed unchanged in this
  packet, so the reduction did not simply push retrieval debt into the next
  queued search owners.

## Verification

```text
uv run ruff check app/services/search_retrieval_primitives.py \
  app/services/search_span_retrieval.py \
  app/hotspot_prevention_classifier_service_rules.py \
  tests/unit/test_search_retrieval_primitives.py \
  tests/unit/test_search_span_retrieval.py \
  tests/unit/test_search_execution_orchestration.py \
  tests/unit/test_hotspot_prevention.py
  pass

uv run pytest -q tests/unit/test_search_retrieval_primitives.py \
  tests/unit/test_search_span_retrieval.py \
  tests/unit/test_search_execution_orchestration.py \
  tests/unit/test_hotspot_prevention.py
  18 passed

uv run pytest -q tests/unit/test_search_service.py \
  tests/unit/test_search_execution_orchestration.py \
  tests/unit/test_search_retrieval_primitives.py \
  tests/unit/test_search_span_retrieval.py \
  tests/unit/test_search_harnesses.py \
  tests/unit/test_search_service_orchestration.py \
  tests/unit/test_search_service_persistence.py \
  tests/unit/test_hotspot_prevention.py
  32 passed

env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs \
  tests/integration/test_multivector_retrieval.py \
  tests/integration/test_search_replays_roundtrip.py \
  tests/integration/test_postgres_roundtrip.py
  6 passed

uv run docling-system-hotspot-prevention-check --strict
  blocked=0
  exceptions=0

uv run docling-system-architecture-quality-report --summary
  broader_rebaseline_candidate_count=4
  top_routed_hotspot_paths=[]
  top_broader_rebaseline_paths=[
    "app/services/search_harnesses.py",
    "app/cli_commands/search_harness.py",
    "tests/unit/test_cli_search_harness.py",
    "tests/unit/test_search_api_harnesses.py"
  ]
```

## Residual Risks And Next Routing

- `app/services/search_harnesses.py` remains the next real search-family owner
  at `627` lines and is now the first broader-rebaseline candidate.
- `app/cli_commands/search_harness.py`,
  `tests/unit/test_cli_search_harness.py`, and
  `tests/unit/test_search_api_harnesses.py` remain inherited residual owners,
  but this packet does not reopen them or move direct search span logic into
  those surfaces.
- The routed queue remains intentionally empty at
  `top_routed_hotspot_paths=[]`; the next code-owning packet still requires the
  broader-rebaseline selection step rather than reviving an old routed facade.
