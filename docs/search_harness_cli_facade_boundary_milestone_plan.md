# Search Harness CLI Facade Boundary Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: resolved locally in the current checkout. The packet reduces
`app/cli_commands/search_harness.py` to `23` lines by moving shared parser
support plus retrieval-learning, evaluation/gate, and audit ownership into
`app/cli_commands/search_harness_support.py` at `84` lines,
`app/cli_commands/search_harness_learning.py` at `268` lines,
`app/cli_commands/search_harness_evaluations.py` at `176` lines, and
`app/cli_commands/search_harness_audit.py` at `111` lines, preserves the
stable `app.cli` forwarding seam, and advances the broader-rebaseline residual
queue to `tests/unit/test_search_api_harnesses.py`.
Owner context: fresh broader rebaseline after the 2026-05-20 search-harness
facade closeout surfaced `app/cli_commands/search_harness.py` together with
`tests/unit/test_cli_search_harness.py` as the next real search-family owners
above the default `600`-line budget while the routed queue remained empty at
`top_routed_hotspot_paths=[]`.

## Purpose

Reduce the next real search-family CLI owner without shifting the residual debt
into the remaining API harness test root.

This packet closes the narrowest honest slice by:

- keeping `app/cli_commands/search_harness.py` as a compact compatibility
  facade over focused command-owner modules
- moving shared replay-source and release-gate parser helpers into
  `app/cli_commands/search_harness_support.py`
- moving retrieval-learning and optimization command ownership into
  `app/cli_commands/search_harness_learning.py`
- moving evaluation, durable list/show, and release-gate command ownership
  into `app/cli_commands/search_harness_evaluations.py`
- moving audit-bundle command ownership into
  `app/cli_commands/search_harness_audit.py`
- moving the direct owner coverage into
  `tests/unit/test_cli_search_harness_learning.py`,
  `tests/unit/test_cli_search_harness_evaluations.py`, and
  `tests/unit/test_cli_search_harness_audit.py`, while keeping
  `tests/unit/test_cli_search_harness.py` as a compact seam check
- routing the reduced CLI root and reduced root test through
  `config/hotspot_prevention.yaml` and moving the focused guard coverage into
  `tests/unit/test_hotspot_prevention_search_cli.py`

## Non-Goals

- No search API route or response change in `/search/harnesses` or
  `/search/learning`.
- No split of `tests/unit/test_search_api_harnesses.py` in this packet.
- No new search service, retrieval, or reranking behavior.
- No `app/cli.py` entrypoint contract change.

## Local Closeout Update

- `app/cli_commands/search_harness.py` now closes at `23` lines.
- `app/cli_commands/search_harness_support.py` now owns the shared replay and
  gate parser helpers at `84` lines.
- `app/cli_commands/search_harness_learning.py` now owns the
  retrieval-learning materialization, candidate evaluation, reranker artifact,
  and optimization command path at `268` lines.
- `app/cli_commands/search_harness_evaluations.py` now owns the evaluation,
  durable read, and release-gate command path at `176` lines.
- `app/cli_commands/search_harness_audit.py` now owns the search-harness and
  retrieval-training audit-bundle commands at `111` lines.
- `tests/unit/test_cli_search_harness.py` now closes at `18` lines as a facade
  seam check, while direct owner coverage now lives in
  `tests/unit/test_cli_search_harness_learning.py` at `303` lines,
  `tests/unit/test_cli_search_harness_evaluations.py` at `275` lines, and
  `tests/unit/test_cli_search_harness_audit.py` at `152` lines.
- `config/hotspot_prevention.yaml` now records
  `app/cli_commands/search_harness.py` as a compatibility-facade trap and
  `tests/unit/test_cli_search_harness.py` as a deferred reduced facade, while
  the reduced `app/cli.py` and `tests/unit/test_cli.py` routes now point to
  the focused search-harness command/test owners instead of the old broad
  roots.
- The live architecture-quality summary now reports
  `broader_rebaseline_candidate_count=1` with
  `top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`.

Debt-shift audit:

- `tests/unit/test_search_api_harnesses.py` stayed unchanged at `764` lines in
  this packet, so the reduction did not simply push search-harness CLI debt
  into the next queued residual owner.
- The new focused hotspot-prevention coverage now lives in
  `tests/unit/test_hotspot_prevention_search_cli.py` at `36` lines, so the
  governed `tests/unit/test_hotspot_prevention.py` root did not inherit new
  broad case-table debt.
- `app/hotspot_prevention_classifier.py` still closes at `362` lines, so the
  new CLI facade rule did not shift governance debt into the central
  classifier dispatcher.

## Verification

```text
uv run ruff check app/cli_commands/search_harness.py \
  app/cli_commands/search_harness_support.py \
  app/cli_commands/search_harness_learning.py \
  app/cli_commands/search_harness_evaluations.py \
  app/cli_commands/search_harness_audit.py \
  app/hotspot_prevention_classifier.py \
  app/hotspot_prevention_classifier_search_rules.py \
  tests/unit/test_cli_search_harness.py \
  tests/unit/test_cli_search_harness_learning.py \
  tests/unit/test_cli_search_harness_evaluations.py \
  tests/unit/test_cli_search_harness_audit.py \
  tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_search_cli.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  pass

uv run pytest -q tests/unit/test_cli_search_harness.py \
  tests/unit/test_cli_search_harness_learning.py \
  tests/unit/test_cli_search_harness_evaluations.py \
  tests/unit/test_cli_search_harness_audit.py \
  tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_search_cli.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  36 passed

uv run pytest -q tests/unit/test_cli_entrypoints.py \
  tests/unit/test_cli_search_harness.py \
  tests/unit/test_cli_search_harness_learning.py \
  tests/unit/test_cli_search_harness_evaluations.py \
  tests/unit/test_cli_search_harness_audit.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_search_api_learning_audit.py \
  tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  49 passed

env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs \
  tests/integration/test_retrieval_learning_ledger_candidates.py \
  tests/integration/test_search_harness_releases.py
  4 passed

env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
  2169 passed
  1 Docling deprecation warning

uv run docling-system-hotspot-prevention-check --strict
  blocked=0
  exceptions=0

uv run docling-system-architecture-quality-report --summary
  broader_rebaseline_candidate_count=1
  top_routed_hotspot_paths=[]
  top_broader_rebaseline_paths=[
    "tests/unit/test_search_api_harnesses.py"
  ]

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt: none
```

## Residual Risks And Next Routing

- `tests/unit/test_search_api_harnesses.py` remains the next real
  search-family owner at `764` lines and is now the only broader-rebaseline
  candidate.
- The routed queue remains intentionally empty at
  `top_routed_hotspot_paths=[]`; the next code-owning packet still requires the
  broader-rebaseline selection step rather than reviving an old reduced root.
