# Search Harness Facade Boundary Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: resolved locally in the current checkout. The packet reduces
`app/services/search_harnesses.py` to `82` lines by moving harness contracts,
registry, and reranking ownership into
`app/services/search_harness_contracts.py` at `105` lines,
`app/services/search_harness_registry.py` at `291` lines, and
`app/services/search_harness_reranking.py` at `203` lines, preserves the
compatibility seam used by `app/services/search.py`, and advances the
broader-rebaseline residual queue to `app/cli_commands/search_harness.py`.
Owner context: fresh broader rebaseline after the 2026-05-20
search-span closeout surfaced `app/services/search_harnesses.py` as the next
real search-family owner above the default `600`-line budget while the routed
queue remained empty at `top_routed_hotspot_paths=[]`.

## Purpose

Reduce the next real search owner without reopening `app/services/search.py`
or shifting search-harness debt into the CLI and API test roots.

This packet closes the narrowest honest slice by:

- keeping `app/services/search_harnesses.py` as a compact compatibility seam
  over focused owner modules
- moving the search-harness contracts and `build_reranker()` surface into
  `app/services/search_harness_contracts.py`
- moving default harness profiles, override fields, registry state, and
  derived-harness construction into `app/services/search_harness_registry.py`
- moving `LinearFeatureSearchReranker` into
  `app/services/search_harness_reranking.py`
- moving the direct owner coverage into
  `tests/unit/test_search_harness_registry.py` and
  `tests/unit/test_search_harness_reranking.py`, while keeping
  `tests/unit/test_search_harnesses.py` as a compact seam check
- adding `app/services/search_harnesses.py` as an explicit hotspot-prevention
  facade trap and moving the new facade classifier into
  `app/hotspot_prevention_classifier_search_rules.py`

## Non-Goals

- No CLI refactor in `app/cli_commands/search_harness.py`.
- No new API route split in `tests/unit/test_search_api_harnesses.py`.
- No retrieval-primitive or metadata-supplement changes.
- No API contract changes to `/search` or `/search/harnesses`.

## Local Closeout Update

- `app/services/search_harnesses.py` now closes at `82` lines.
- `app/services/search_harness_contracts.py` now owns the contract types and
  `SearchHarness.build_reranker()` seam at `105` lines.
- `app/services/search_harness_registry.py` now owns the default harness
  profiles, registry, and override application path at `291` lines.
- `app/services/search_harness_reranking.py` now owns
  `LinearFeatureSearchReranker` at `203` lines.
- `tests/unit/test_search_harnesses.py` now closes at `18` lines as a facade
  seam check, while direct owner coverage now lives in
  `tests/unit/test_search_harness_registry.py` at `44` lines and
  `tests/unit/test_search_harness_reranking.py` at `69` lines.
- `config/hotspot_prevention.yaml` now records
  `app/services/search_harnesses.py` as a compatibility-facade trap over the
  focused harness owner modules.
- The live architecture-quality summary now reports
  `broader_rebaseline_candidate_count=3` with
  `top_broader_rebaseline_paths=[app/cli_commands/search_harness.py, tests/unit/test_cli_search_harness.py, tests/unit/test_search_api_harnesses.py]`.

Debt-shift audit:

- `app/cli_commands/search_harness.py` (`604` lines),
  `tests/unit/test_cli_search_harness.py` (`714`), and
  `tests/unit/test_search_api_harnesses.py` (`764`) stayed unchanged in this
  packet, so the reduction did not simply push search-harness debt into the
  next queued search owners.
- The new hotspot-prevention facade rule moved into
  `app/hotspot_prevention_classifier_search_rules.py` at `129` lines, so the
  shared `app/hotspot_prevention_classifier_service_rules.py` closes at `291`
  lines instead of inheriting new search-harness classifier debt. The central
  dispatcher remains a `362` line route table with no new private-helper
  growth.

## Verification

```text
uv run ruff check app/services/search_harnesses.py \
  app/services/search_harness_contracts.py \
  app/services/search_harness_registry.py \
  app/services/search_harness_reranking.py \
  app/hotspot_prevention_classifier.py \
  app/hotspot_prevention_classifier_service_rules.py \
  app/hotspot_prevention_classifier_search_rules.py \
  tests/unit/test_search_harnesses.py \
  tests/unit/test_search_harness_registry.py \
  tests/unit/test_search_harness_reranking.py \
  tests/unit/test_hotspot_prevention.py
  pass

uv run pytest -q tests/unit/test_search_harnesses.py \
  tests/unit/test_search_harness_registry.py \
  tests/unit/test_search_harness_reranking.py \
  tests/unit/test_search_harness_overrides.py \
  tests/unit/test_search_service_ranking.py \
  tests/unit/test_hotspot_prevention.py
  30 passed

uv run pytest -q tests/unit/test_search_service.py \
  tests/unit/test_search_execution_orchestration.py \
  tests/unit/test_search_harnesses.py \
  tests/unit/test_search_harness_registry.py \
  tests/unit/test_search_harness_reranking.py \
  tests/unit/test_search_harness_overrides.py \
  tests/unit/test_search_service_ranking.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_cli_search_harness.py
  47 passed

env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs \
  tests/integration/test_multivector_retrieval.py \
  tests/integration/test_search_replays_roundtrip.py \
  tests/integration/test_postgres_roundtrip.py
  6 passed

env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
  2166 passed
  1 Docling deprecation warning

uv run docling-system-hotspot-prevention-check --strict
  blocked=0
  exceptions=0

uv run docling-system-architecture-quality-report --summary
  broader_rebaseline_candidate_count=3
  top_routed_hotspot_paths=[]
  top_broader_rebaseline_paths=[
    "app/cli_commands/search_harness.py",
    "tests/unit/test_cli_search_harness.py",
    "tests/unit/test_search_api_harnesses.py"
  ]

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt: none
```

## Residual Risks And Next Routing

- `app/cli_commands/search_harness.py` remains the next real search-family
  owner at `604` lines and is now the first broader-rebaseline candidate.
- `tests/unit/test_cli_search_harness.py` and
  `tests/unit/test_search_api_harnesses.py` remain inherited residual owners,
  but this packet does not reopen them or move direct search-harness behavior
  into those surfaces.
- The routed queue remains intentionally empty at
  `top_routed_hotspot_paths=[]`; the next code-owning packet still requires the
  broader-rebaseline selection step rather than reviving an old routed search
  facade.
