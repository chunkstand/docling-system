# Search Harness Cycle Boundary Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: resolved locally in the current checkout. The packet removes the
remaining Python import cycle between
`app/services/search_harness_contracts.py` and
`app/services/search_harness_reranking.py` by moving the shared reranker
config into `app/services/search_harness_reranker_config.py`, reducing the
contracts owner to `79` lines, keeping the reranking owner at `203` lines,
and returning
`python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
to `None detected`.
Owner context: the earlier
`docs/search_harness_facade_boundary_milestone_plan.md` split the
search-harness family into focused owners but explicitly left the
contracts/reranking cycle as the remaining architecture defect. This packet
closes that residual without reopening the reduced search-harness, CLI, or API
test roots.

## Purpose

Remove the live search-harness cycle with the smallest ownership change that:

- preserves the public `SearchHarness.build_reranker()` seam
- avoids function-local import masking in a cycle-owning file
- keeps the routed queue empty at `top_routed_hotspot_paths=[]`
- does not shift search-harness debt into the remaining CLI or API test owners

## Non-Goals

- No new search CLI split in `app/cli_commands/search_harness.py`.
- No new API harness split in `tests/unit/test_search_api_harnesses.py`.
- No retrieval-primitive, metadata-supplement, or `/search` contract changes.
- No broader search-family hotspot rebaseline beyond confirming the next
  honest candidate stays `tests/unit/test_search_api_harnesses.py`.

## Local Closeout Update

- `app/services/search_harness_reranker_config.py` now owns the shared
  `LinearRerankerConfig` seam at `29` lines.
- `app/services/search_harness_contracts.py` now closes at `79` lines and
  builds rerankers through a module-scope dependency instead of a nested
  import.
- `app/services/search_harness_reranking.py` remains the focused reranker
  owner at `203` lines and no longer back-imports the contracts owner.
- `tests/unit/test_search_harness_registry.py` now closes at `51` lines with a
  direct registry-to-reranker regression check.
- `tests/unit/test_python_cycle_imports.py` now closes at `111` lines and
  explicitly guards the search-harness cycle boundary against nested imports
  and reranking-to-contract back imports.
- `config/hotspot_prevention.yaml` now routes the reduced
  `app/services/search_harnesses.py` facade to the new shared config owner in
  addition to the existing contracts, registry, and reranking owners.
- `config/hygiene_policy.yaml` now exact-ratchets
  `app/services/search_harness_contracts.py` to `79 / 0` and records
  `app/services/search_harness_reranker_config.py` at `29 / 0` under
  `IC-1D03DBFE8492`.

Debt-shift audit:

- `app/services/search_harnesses.py` stayed at `82` lines, so the cycle fix
  did not regrow the reduced compatibility facade.
- `app/cli_commands/search_harness.py` stayed at `23` lines and
  `tests/unit/test_search_api_harnesses.py` stayed at `764` lines, so the
  cycle removal did not move search-harness behavior into the next broader
  residual owners.
- The live architecture-quality summary still reports
  `top_routed_hotspot_paths=[]` and
  `top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`, so
  the packet closes the cycle without changing the honest next queue choice.

## Verification

```text
git diff --check
  pass

uv run ruff check app/services/search_harness_contracts.py \
  app/services/search_harness_registry.py \
  app/services/search_harness_reranker_config.py \
  app/services/search_harness_reranking.py \
  app/services/search_harnesses.py \
  tests/unit/test_search_harnesses.py \
  tests/unit/test_search_harness_registry.py \
  tests/unit/test_search_harness_reranking.py \
  tests/unit/test_search_harness_overrides.py \
  tests/unit/test_search_service_ranking.py \
  tests/unit/test_search_service.py \
  tests/unit/test_search_execution_orchestration.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_python_cycle_imports.py \
  tests/unit/test_architecture_governance_imports.py
  all checks passed

uv run pytest -q tests/unit/test_search_harnesses.py \
  tests/unit/test_search_harness_registry.py \
  tests/unit/test_search_harness_reranking.py \
  tests/unit/test_search_harness_overrides.py \
  tests/unit/test_search_service_ranking.py \
  tests/unit/test_search_service.py \
  tests/unit/test_search_execution_orchestration.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_python_cycle_imports.py \
  tests/unit/test_architecture_governance_imports.py
  41 passed

env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs \
  tests/integration/test_multivector_retrieval.py \
  tests/integration/test_search_replays_roundtrip.py \
  tests/integration/test_postgres_roundtrip.py
  6 passed

uv run docling-system-hotspot-prevention-check --strict
  blocked=0
  exceptions=0

uv run docling-system-hygiene-check
  inherited budget debt: none
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  status_counts={"deployed":66}

uv run docling-system-architecture-inspect
  valid=true
  violation_count=0

uv run docling-system-architecture-quality-report --summary
  top_routed_hotspot_paths=[]
  top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles
  pass
  Python cycles: none detected
```

## Residual Risks And Next Routing

- `tests/unit/test_search_api_harnesses.py` remains the next honest
  broader-rebaseline candidate at `764` lines.
- The routed queue remains intentionally empty at
  `top_routed_hotspot_paths=[]`; future code-owning work should still begin
  from the broader rebaseline rather than reviving a reduced search facade.
- This packet only closes the cycle boundary. It does not reopen the older
  search-harness facade, CLI, or API split packets.
