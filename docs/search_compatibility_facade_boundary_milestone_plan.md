# Search Compatibility Facade Boundary Milestone Plan

Date: 2026-05-14 local / 2026-05-14 UTC
Status: resolved locally through implementation closeout commit `fd9dd2a` on
2026-05-14 after the freshness rebaseline, harness/reranker extraction,
retrieval-primitive extraction, metadata-supplement extraction, and
verification closeout for `IC-1D03DBFE8492`
Owner context: the scoped hydration, persistence, execution-orchestration,
harness/reranker, retrieval-primitive, and metadata-supplement families no
longer live in `app/services/search.py`. The broader search owner case
`IC-1D03DBFE8492` is now deployed locally, and the remaining downstream work
has moved to follow-on residuals such as
`app/hotspot_prevention_classifier.py` under `IC-6C1B516A3F92` plus the
broader coordination brief in `docs/boring_change_architecture_milestone_plan.md`.

## Purpose

Resolve the remaining unclear ownership in `app/services/search.py` so the file
becomes a true compatibility facade instead of a semi-facade that still
contains several unrelated implementation families.

The key issue is no longer public execution orchestration. That work already
lives in `app/services/search_execution_orchestration.py`. The remaining debt is
that `app/services/search.py` still mixes three materially different concerns:

- harness, reranker, and override-registry ownership
- low-level chunk, table, span, and late-interaction retrieval primitives
- prose metadata supplement and adjacent-context expansion helpers

This plan resolves that residual ownership gap end to end by refreshing the
live search baseline, extracting those remaining families into bounded owner
modules, hardening the facade-growth gates, and closing the broader owner case
only if `app/services/search.py` stops behaving like a hotspot in the live
probe after closeout.

This is a fresh standalone packet. Do not append these steps to
`docs/boring_change_architecture_milestone_plan.md`; that broader coordination
brief remains downstream of this search-specific owner retirement.

## Closeout

Closeout outcome from the current local checkout:

- `app/services/search.py` now closes at `231` lines / `2` private helpers as
  a narrow compatibility facade with stable public imports plus explicit
  `execute_search(...)` and `search_documents(...)` forwarding wrappers.
- Harness and reranker ownership now lives in
  `app/services/search_harnesses.py` at `627` lines / `0` private helpers.
- Low-level retrieval primitive ownership now lives in
  `app/services/search_retrieval_primitives.py` at `653` lines / `0` private
  helpers.
- Metadata supplement plus adjacent-context ownership now lives in
  `app/services/search_metadata_supplement.py` at `262` lines / `0` private
  helpers.
- The hotspot-prevention classifier now blocks harness-registry,
  retrieval-primitive, and metadata-supplement regrowth directly in
  `app/services/search.py`; this keeps the search facade closed but expands the
  existing classifier hygiene residual `IC-6C1B516A3F92` to `1002` lines.
- The live architecture probe no longer lists `app/services/search.py` in the
  top 20 hotspots and now routes `app/services/agent_tasks.py` as the top
  hotspot instead, so `IC-1D03DBFE8492` is now deployed rather than reduced.

Closeout verification from this local window:

- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_harnesses.py tests/unit/test_search_retrieval_primitives.py tests/unit/test_search_harness_overrides.py tests/unit/test_search_legibility.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/unit/test_hotspot_prevention.py`: `70 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_multivector_retrieval.py tests/integration/test_postgres_roundtrip.py`: `11 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary`: unchanged global summary with `hotspot_count=10`, `max_hotspot_risk_score=501.06`, and `top_hotspot_paths` excluding `app/services/search.py`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`: top hotspot is now `app/services/agent_tasks.py`; `app/services/search.py` no longer appears in the queue

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-14
local / 2026-05-14 UTC:

```text
git status -sb
  ## main...origin/main [ahead 2]

wc -l app/services/search.py app/services/search_hydration.py app/services/search_execution_persistence.py app/services/search_execution_orchestration.py tests/unit/test_search_service.py tests/unit/test_hotspot_prevention.py
    1592 app/services/search.py
     392 app/services/search_hydration.py
     423 app/services/search_execution_persistence.py
     532 app/services/search_execution_orchestration.py
     117 tests/unit/test_search_service.py
    1107 tests/unit/test_hotspot_prevention.py

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=501.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  top hotspot: app/services/search.py
  app/services/search.py = 32 revisions, 1592 lines, score 50944
  Python cycles:
    app.services.chat, app.services.search,
    app.services.search_execution_persistence,
    app.services.search_hydration
    app.services.claim_support_policy_impacts,
    app.services.claim_support_replay_alert_promotions
    app.services.evidence_provenance_export_graph_core,
    app.services.evidence_provenance_export_graph_report
    app.services.evidence_search_packages,
    app.services.evidence_search_trace_store
```

Search-surface evidence from the current file:

- `app/services/search.py` still defines the public search contracts plus the
  concrete harness and reranker registry surface:
  `SearchRetrievalProfile`,
  `LinearRerankerConfig`,
  `SearchHarness`,
  `LinearFeatureSearchReranker`,
  `_build_derived_search_harness(...)`,
  `_build_search_harness_registry(...)`,
  `list_search_harnesses(...)`,
  `get_search_harness(...)`,
  and `get_default_reranker()`.
- The same file also still owns the low-level retrieval primitives:
  `_chunk_query(...)`,
  `_table_query(...)`,
  `_document_query(...)`,
  filter helpers,
  keyword and relaxed-keyword loaders,
  semantic loaders,
  span loaders,
  multivector window helpers,
  and `_run_late_interaction_search(...)`.
- Metadata supplement ownership is still in the facade as well:
  `_ranked_metadata_overlap_score(...)`,
  `_metadata_tsquery(...)`,
  `_run_prose_metadata_chunk_search(...)`,
  `_should_run_metadata_supplement(...)`,
  and `_expand_adjacent_chunk_context(...)`.
- `execute_search(...)` is already only a narrow forwarding wrapper into
  `app/services/search_execution_orchestration.py`, which means the remaining
  bodies in `app/services/search.py` are now owner leftovers rather than a
  single cohesive service boundary.
- Existing callers still import through `app.services.search`, including:
  `app/services/chat.py`,
  `app/services/evaluations.py`,
  `app/services/search_history.py`,
  `app/services/search_replays.py`,
  `app/services/search_replay_runner.py`,
  `app/services/search_legibility.py`,
  `app/services/retrieval_learning.py`,
  and `app/services/agent_actions/search_harness.py`.
- Search test coverage is already decomposed enough to support direct owner
  tests without regrowing the facade test:
  `tests/unit/test_search_service.py` is `117` lines,
  `tests/unit/test_search_service_orchestration.py` is `580` lines,
  `tests/unit/test_search_service_persistence.py` is `208` lines,
  `tests/unit/test_search_metadata_supplement.py` is `411` lines,
  and `tests/unit/test_hotspot_prevention.py` is already a separate `1107`
  line hotspot that should not absorb broad new search coverage.

## Goal

Retire `IC-1D03DBFE8492` by converting `app/services/search.py` into a narrow
compatibility facade with explicit delegated ownership so that:

- `app/services/search.py` closes at `<= 450` lines and `<= 8` private helpers
- harness and reranker ownership lives in one bounded owner module
- low-level retrieval primitive ownership lives in one bounded owner module
- prose metadata supplement and adjacent-context expansion ownership lives in
  one bounded owner module
- stable imports through `app.services.search` continue to work for current
  callers and tests
- the search facade no longer appears as the top hotspot in the live
  architecture probe after closeout
- the broader owner case is marked `resolved`, not merely `reduced`, unless the
  refreshed live measurements prove a narrower residual issue still remains

## Non-Goals

- No retrieval-quality tuning, ranking-weight retuning, or search relevance
  optimization beyond what is required to preserve behavior.
- No API contract change for `/search` or persisted search request records.
- No re-expansion of hydration, persistence, or execution orchestration back
  into `app/services/search.py`.
- No new ad hoc helper file explosion; each extracted family must remain bounded
  and named up front.
- No test weakening, assertion loosening, skip broadening, or xfail broadening
  to get the refactor green.
- No resurrection of the broad umbrella architecture plan as the implementation
  surface for this specific owner case.

## Scope

In scope:

- Milestone 0 freshness and residual-owner rebaseline for
  `IC-1D03DBFE8492`
- one bounded owner module for harness and reranker registry ownership
- one bounded owner module for low-level retrieval primitives
- one bounded owner module for metadata supplement and adjacent-context helpers
- final search-facade contraction and explicit import forwarding
- hotspot-prevention and hygiene ratchet updates that block those families from
  growing back inside the facade
- direct owner tests for the new modules
- architecture index and session handoff updates in the same closeout window

Out of scope:

- new retrieval-learning release gates
- chat-answer behavior changes outside whatever import rewiring is necessary
- claim-support, evidence, or semantics cycle cleanup outside the search-owned
  seam
- large-file cleanup for `tests/unit/test_hotspot_prevention.py` itself

## Owner Surfaces

- `app/services/search.py`
  - role after closeout: compatibility facade, public import surface, small
    public contract holder, and explicit forwarding wrappers only
  - allowed growth after closeout: imports, aliases, tiny wrappers, public
    contract declarations, and deletions
- new harness owner:
  `app/services/search_harnesses.py`
  - intended ownership: harness dataclasses, default profiles, reranker config,
    reranker implementation, override-registry composition, and default
    harness selection helpers
- new retrieval primitive owner:
  `app/services/search_retrieval_primitives.py`
  - intended ownership: base queries, filter helpers, keyword loaders,
    semantic loaders, span loaders, multivector helpers, and late-interaction
    retrieval execution
- new metadata supplement owner:
  `app/services/search_metadata_supplement.py`
  - intended ownership: metadata overlap scoring, metadata tsquery
    construction, metadata chunk search, metadata-supplement eligibility, and
    adjacent-context expansion
- existing search sibling owners that must remain stable:
  `app/services/search_hydration.py`,
  `app/services/search_execution_persistence.py`,
  `app/services/search_execution_orchestration.py`,
  `app/services/search_query_features.py`,
  `app/services/search_ranking.py`,
  `app/services/search_plan.py`,
  `app/services/search_harness_overrides.py`
- tests:
  `tests/unit/test_search_service.py`,
  `tests/unit/test_search_harness_overrides.py`,
  `tests/unit/test_search_legibility.py`,
  `tests/unit/test_search_metadata_supplement.py`,
  `tests/unit/test_search_service_orchestration.py`,
  `tests/unit/test_search_service_persistence.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `tests/integration/test_multivector_retrieval.py`,
  `tests/integration/test_postgres_roundtrip.py`
- routing and governance surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- `app/services/search.py` must end as a compatibility facade, not as the owner
  of concrete retrieval logic.
- Put harness and reranker implementation in `app/services/search_harnesses.py`
  rather than spreading it across the facade, `search_legibility`, or
  `search_harness_overrides`.
- Put low-level query and retrieval primitives in
  `app/services/search_retrieval_primitives.py`, not back into the facade or
  into `search_execution_orchestration.py`.
- Put metadata supplement and adjacent-context ownership in
  `app/services/search_metadata_supplement.py`, not into the retrieval
  primitives file unless Milestone 0 evidence proves the combined module still
  closes within the explicit line and helper ceilings below.
- Keep hydration logic in `app/services/search_hydration.py`, persistence logic
  in `app/services/search_execution_persistence.py`, ranking logic in
  `app/services/search_ranking.py`, and planning logic in
  `app/services/search_plan.py`.
- Preserve import stability through `app.services.search` for:
  `execute_search(...)`,
  `search_documents(...)`,
  `get_search_harness(...)`,
  `list_search_harnesses(...)`,
  `DEFAULT_SEARCH_HARNESS_NAME`,
  override field constants,
  and the current public search contract types used by sibling services and
  tests.
- Prefer direct owner tests in new dedicated files such as
  `tests/unit/test_search_harnesses.py` and
  `tests/unit/test_search_retrieval_primitives.py` instead of regrowing
  `tests/unit/test_search_service.py` or `tests/unit/test_hotspot_prevention.py`
  into larger hotspots.
- Hygiene ceilings after closeout:
  `app/services/search.py` must close at `<= 450` lines and `<= 8` private
  helpers;
  `app/services/search_harnesses.py` must close at `<= 650` lines and
  `<= 15` private helpers;
  `app/services/search_retrieval_primitives.py` must close at `<= 700` lines
  and `<= 18` private helpers;
  `app/services/search_metadata_supplement.py` must close at `<= 350` lines
  and `<= 10` private helpers.
- If Milestone 0 rebaseline shows that one extracted owner cannot stay inside
  those ceilings without creating a fourth file, stop and write a new
  standalone follow-on plan instead of silently broadening this packet.

## Weak-Point Prevention Contract

Freshness rule: do not start implementation from this doc without rerunning the
Milestone 0 baseline commands in the same local closeout window. If the live
line counts, hotspot score, or cycle set differ materially from the evidence
above, update the plan first.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Retrieval logic grows back inside `app/services/search.py` because the file is still the public import surface | `app/services/search.py`, `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py` | `uv run docling-system-hotspot-prevention-check --strict` plus focused hotspot-prevention unit coverage | Any new query builder, loader, metadata supplement helper, or late-interaction body lands in the facade beyond a tiny wrapper or alias-forwarding seam | Add a temporary helper such as `def _run_more_span_search(...):` or `def _maybe_expand_more_metadata(...):` in the facade and confirm the prevention gate fails | A later session appends “one quick retrieval helper” to `app/services/search.py` because imports are already routed through that file |
| The refactor merely moves one hotspot into a differently named large file | `config/hygiene_policy.yaml`, staged file set, the three new owner modules | `uv run docling-system-hygiene-check` plus exact `wc -l` / private-helper recount before commit | Any new owner module exceeds its explicit line or private-helper ceiling, or a fourth ad hoc search owner file is introduced without a new plan | Add a temporary oversized helper cluster to one new file and confirm hygiene fails | A future session keeps splitting by convenience until the search surface becomes a constellation of medium-large files with no durable boundary rules |
| Public search and harness imports drift even though the refactor is “internal” | `app/services/search.py`, search callers, direct owner tests | `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_harness_overrides.py tests/unit/test_search_legibility.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/unit/test_search_metadata_supplement.py` | Existing callers or tests that import through `app.services.search` break, or return payload shape changes without explicit contract intent | Temporarily remove a forwarded constant or helper export from the facade and confirm the targeted tests fail | A future session updates internal imports but forgets that search harness and legibility paths still consume the facade contract |
| Search runtime behavior regresses in late-interaction, span hydration, or persisted search tracing | `app/services/search_retrieval_primitives.py`, `app/services/search_metadata_supplement.py`, integration tests | `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_multivector_retrieval.py tests/integration/test_postgres_roundtrip.py` | Any regression in multivector match traces, span hydration, metadata supplement candidates, or persisted search-request artifacts | Temporarily drop a span-loader call or metadata supplement branch and confirm integration or focused unit coverage fails | A later session “simplifies” retrieval helpers and accidentally removes a path whose only durable proof is in DB-backed tests |
| The search-specific import cycle becomes worse or is hidden behind more wrapper indirection | `app/services/search.py`, new owner modules, architecture probe output | `uv run docling-system-architecture-inspect` and `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20` | Python cycle component count rises above the current baseline of `4`, or the new owner modules require direct back-imports from the facade to access retained implementation bodies | Add a temporary direct back-import from one new owner into `app.services.search` and confirm the architecture review blocks closeout | A future session keeps the facade “small” only by making every owner module import back through it, preserving the cycle and obscuring ownership |

## Milestone Sequence

This is a stacked but standalone plan. Each milestone must commit atomically
after verification and closeout docs are updated. Do not collapse multiple
milestones into one giant search rewrite.

### Milestone 0 - Freshness Rebaseline And Owner Map

Status: resolved locally in the current checkout
Outcome label: `resolved`

Implementation:

- Rerun the baseline commands from the Current Evidence section.
- Recount `app/services/search.py` line count and private-helper count.
- Reconfirm the live import callers that still consume the search facade.
- Reconfirm whether the metadata supplement family still warrants its own owner
  file or can safely close within the retrieval-primitives ceiling.
- Reconfirm whether the search-related import cycle still contains
  `app.services.search`; if the cycle shape changed materially, record the
  current component in this plan before code moves.

Acceptance for this milestone:

- The plan reflects live measurements from the actual starting checkout.
- Any drift in line counts, hotspot score, or cycle set is captured before the
  first implementation commit.
- The remainder of the plan still fits within the named owner modules and line
  ceilings; otherwise implementation stops and a new standalone follow-on is
  written.

### Milestone 1 - Harness And Reranker Owner Extraction

Status: resolved locally in the current checkout
Outcome label: `resolved`

Implementation:

- Add `app/services/search_harnesses.py`.
- Move harness and reranker ownership out of the facade:
  `SearchRetrievalProfile`,
  `LinearRerankerConfig`,
  `SearchHarness`,
  `LinearFeatureSearchReranker`,
  default retrieval profiles,
  `_HARNESS_REGISTRY`,
  `_build_derived_search_harness(...)`,
  `_build_search_harness_registry(...)`,
  `list_search_harnesses(...)`,
  `get_search_harness(...)`,
  and `get_default_reranker()`.
- Keep import stability through `app/services/search.py` by alias-forwarding the
  moved public contract types, helpers, and constants.
- Add direct owner coverage in a new focused test file such as
  `tests/unit/test_search_harnesses.py`, and only keep facade-level assertions
  in the smaller `tests/unit/test_search_service.py` or
  `tests/unit/test_search_harness_overrides.py`.
- Tighten hotspot-prevention rules so new harness-registry or reranker logic is
  blocked from returning to the facade.

Acceptance for this milestone:

- `app/services/search.py` no longer owns the harness and reranker bodies.
- `app/services/search_harnesses.py` closes within `<= 650` lines and
  `<= 15` private helpers.
- Search harness, override, and legibility callers continue to work through the
  facade.
- The facade is materially smaller and remains import-stable.

### Milestone 2 - Retrieval Primitive Owner Extraction

Status: resolved locally in the current checkout
Outcome label: `resolved`

Implementation:

- Add `app/services/search_retrieval_primitives.py`.
- Move the low-level retrieval family out of the facade:
  `_chunk_query(...)`,
  `_table_query(...)`,
  `_document_query(...)`,
  filter helpers,
  keyword and relaxed-keyword loaders,
  semantic loaders,
  span loaders,
  `_query_multivector_windows(...)`,
  `_multivector_span_query(...)`,
  `_late_interaction_match_trace(...)`,
  and `_run_late_interaction_search(...)`.
- Keep the orchestration module calling these helpers through explicit imports
  or stable facade forwarding, not through new direct back-imports into retained
  implementation bodies.
- Add direct owner coverage in a new focused test file such as
  `tests/unit/test_search_retrieval_primitives.py`.
- Harden hotspot prevention so query-builder and retrieval-loader logic is
  blocked from regrowing inside the facade.

Acceptance for this milestone:

- `app/services/search.py` no longer owns the low-level retrieval primitive
  family.
- `app/services/search_retrieval_primitives.py` closes within `<= 700` lines
  and `<= 18` private helpers.
- Integration-sensitive late-interaction and span-search behavior remains
  covered.
- The search-related cycle count does not increase beyond the Milestone 0
  baseline.

### Milestone 3 - Metadata Supplement Extraction And Facade Closeout

Status: resolved locally in the current checkout
Outcome label: `resolved`

Implementation:

- Add `app/services/search_metadata_supplement.py` unless Milestone 0 evidence
  proved the supplement family can safely live inside the retrieval-primitives
  module without violating the agreed ceilings.
- Move the residual metadata supplement family out of the facade:
  `_ranked_metadata_overlap_score(...)`,
  `_metadata_tsquery(...)`,
  `_run_prose_metadata_chunk_search(...)`,
  `_should_run_metadata_supplement(...)`,
  and `_expand_adjacent_chunk_context(...)`.
- Keep `_rerank_results(...)` and `_merge_hybrid_results(...)` only where they
  best preserve a small compatibility surface; they may stay as tiny wrappers
  or move into the harness or retrieval owner only if doing so reduces facade
  ownership without creating a new cycle.
- Reduce `app/services/search.py` to a narrow compatibility facade with public
  contract declarations, imports, aliases, and the explicit
  `execute_search(...)` and `search_documents(...)` wrappers only.
- Update `config/hygiene_policy.yaml` so the facade and new owner modules all
  carry the exact verified ceilings.
- Update `config/improvement_cases.yaml` so `IC-1D03DBFE8492` records the
  closeout measurements and is marked `resolved` only if the live probe and
  narrowed owner contract support retirement.

Acceptance for this milestone:

- `app/services/search.py` closes at `<= 450` lines and `<= 8` private helpers.
- No residual retrieval or metadata supplement bodies remain in the facade
  beyond tiny wrappers or aliases.
- The broader owner case is eligible for `resolved` rather than another reduced
  partial closeout.
- Search callers still import successfully through the facade.

### Milestone 4 - Verification, Docs, And Case Retirement

Status: resolved locally in the current checkout
Outcome label: `resolved`

Implementation:

- Run the full verification stack below in the same closeout window.
- Update this plan, `docs/agentic_architecture_index.md`, and
  `docs/SESSION_HANDOFF.md` with the exact closeout evidence and commit hash.
- Stage only the verified search milestone slice.
- Commit the milestone atomically.

Acceptance for this milestone:

- All verification gates below pass without weakened tests or broadened skips.
- The handoff and architecture index route the search owner case from live
  post-closeout evidence.
- `IC-1D03DBFE8492` is retired only if the architecture probe no longer routes
  `app/services/search.py` as a meaningful hotspot and the file is visibly a
  narrow compatibility facade.

## Required Implementation Artifacts

- `app/services/search_harnesses.py`
- `app/services/search_retrieval_primitives.py`
- `app/services/search_metadata_supplement.py` unless Milestone 0 explicitly
  proves it is unnecessary and the recorded ceilings still hold
- updated `app/services/search.py`
- updated hotspot-prevention policy and classifier
- updated hygiene and improvement-case registry entries
- new direct owner tests for extracted search families

## Required Documentation And Handoff Updates

- this plan:
  `docs/search_compatibility_facade_boundary_milestone_plan.md`
- architecture index:
  `docs/agentic_architecture_index.md`
- canonical handoff:
  `docs/SESSION_HANDOFF.md`
- improvement-case registry:
  `config/improvement_cases.yaml`
- hygiene ratchets:
  `config/hygiene_policy.yaml`
- hotspot-prevention policy:
  `config/hotspot_prevention.yaml`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_harnesses.py app/services/search_retrieval_primitives.py app/services/search_metadata_supplement.py app/services/search_hydration.py app/services/search_execution_persistence.py app/services/search_execution_orchestration.py tests/unit/test_search_service.py tests/unit/test_search_harnesses.py tests/unit/test_search_retrieval_primitives.py tests/unit/test_search_harness_overrides.py tests/unit/test_search_legibility.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_harnesses.py tests/unit/test_search_retrieval_primitives.py tests/unit/test_search_harness_overrides.py tests/unit/test_search_legibility.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_multivector_retrieval.py tests/integration/test_postgres_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`

## Acceptance Criteria

- `app/services/search.py` is a narrow compatibility facade with no broad
  retrieval-family ownership left inside it.
- The remaining search families each have one clear owner module and stay within
  their explicit line and private-helper ceilings.
- The live architecture probe no longer lists `app/services/search.py` as the
  top hotspot, and the broader case can be retired from fresh evidence.
- Search harness, legibility, replay, chat, evaluation, and retrieval callers
  continue to function through the public facade.
- No new search owner module is created outside the modules named in this plan.
- No test coverage was weakened to achieve green verification.

## Stop Conditions

- Stop if Milestone 0 shows the residual search families have already drifted so
  far that they no longer fit inside the named modules and ceilings.
- Stop if the only way to close the plan is to create a fourth new owner file
  that is not named here.
- Stop if import stability through `app.services.search` would need to be broken
  for non-test callers.
- Stop if the refactor increases the Python cycle component count above the
  Milestone 0 baseline of `4`.
- Stop if `tests/unit/test_hotspot_prevention.py` must absorb enough new
  coverage to become the primary hotspot moved by this packet.

## Local Commit Closeout Policy

- Commit one milestone at a time only after its verification passes.
- Update the canonical docs and handoff in the same milestone commit as the code
  that completes that milestone.
- Stage only the verified search-facade slice.
- Do not claim `IC-1D03DBFE8492` retired until the post-closeout probe and
  registry entries agree.

## Residual Risks And Next Routing

- The main residual risk is that the search facade may become small while a new
  extracted owner grows too large. That is why this plan sets explicit ceilings
  for each new file and treats a fourth unnamed owner file as a stop condition.
- A secondary risk is that the search-specific import cycle may survive even if
  the facade shrinks. This plan allows implementation to proceed only if the
  cycle count does not worsen; if a narrower search-cycle seam still remains
  after Milestone 4, route it as a fresh standalone follow-on rather than
  quietly broadening this packet.
- After this plan resolves locally, the broader coordination brief remains
  `docs/boring_change_architecture_milestone_plan.md`, whose Milestone 0 must
  then refresh the live repo state again before taking on the remaining
  cross-owner architecture backlog.
