# Search Hydration Boundary Milestone Plan

Date: 2026-05-12 local / 2026-05-13 UTC
Status: resolved locally through Milestone 1 closeout commit `14390ad` for
`IC-1D03DBFE8492` / `app/services/search.py`; the owner case remains open and
the next routed follow-on stays inside the search compatibility facade
Owner context: fresh bounded implementation brief created after
`docs/agent_task_orchestration_boundary_milestone_plan.md` resolved locally and
routed the next hotspot to the search service compatibility facade.

## Local Progress

Milestone 1 is now closed locally. The search hydration family is no longer
implemented inside `app/services/search.py`.

Local Milestone 1 snapshot:

- added `app/services/search_hydration.py` as the focused owner for
  span-backed query builders, ranked-result hydration, selected-result
  evidence-span loading, and late-interaction hydration
- moved `_span_chunk_query`, `_span_table_query`,
  `_hydrate_ranked_chunks`, `_hydrate_ranked_span_chunks`,
  `_hydrate_ranked_tables`, `_hydrate_ranked_span_tables`,
  `_span_evidence_payload`, `_supports_retrieval_span_search`,
  `_load_source_evidence_spans`, `_ensure_reranked_result_evidence_spans`, and
  `_hydrate_late_interaction_results` behind that owner module while keeping
  `app/services/search.py` import-stable through allowed alias forwarding
- reduced `app/services/search.py` to `2496` lines / `42` private helpers and
  governed `app/services/search_hydration.py` at `392` lines / `11` private
  helpers under the same owner case `IC-1D03DBFE8492`
- added focused direct owner-module coverage in
  `tests/unit/test_search_hydration.py`
- refreshed `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md` so the
  reduced search boundary and next routed follow-on are durable repo state
- local closeout commit: `14390ad`
- architecture probe still routes `app/services/search.py` as the top churn
  hotspot at `30 revisions`, `2496 lines`, and `score 74880`, but the
  architecture-quality summary top-five no longer includes `app/services/search.py`
- next routed follow-on inside `IC-1D03DBFE8492`:
  search execution persistence and operator-trace payload assembly in
  `_ranked_result_evidence_payload`, `_reranked_result_evidence_payload`,
  `_persist_search_operator_runs`, `_persist_search_result_spans`, and
  `_persist_search_execution`

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_hydration.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py`:
  pass
- `uv run pytest -q tests/unit/test_search_hydration.py tests/unit/test_search_service.py tests/unit/test_hotspot_prevention.py`:
  `55 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`:
  `11 passed`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `known_hotspots=7`, `changed_hotspots=1`, `blocked=0`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=531.06`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1879 passed`

## Purpose

Reduce the next coherent owner family inside `app/services/search.py` without
changing the public search contract.

The scoped problem is not general search quality, a reranker rewrite, or a
search-history redesign. The specific debt in this packet is the remaining
result-hydration and retrieval-evidence-span loading logic that still lives in
the central compatibility facade even after the earlier query-feature and
ranking splits.

This plan resolves that debt by moving the hydration family behind a focused
owner module while preserving import stability and search behavior:

- `app/services/search.py` remains the public compatibility facade and search
  execution entrypoint.
- Result hydration, span-backed result assembly, late-interaction hydration,
  and selected-result evidence-span loading move into
  `app/services/search_hydration.py`.
- Verification remains equivalent or broader. No milestone may delete
  assertions, narrow runtime checks, weaken integration coverage, add skips, or
  relax gates merely to get green results.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-12
local / 2026-05-13 UTC and refreshed again for alignment on 2026-05-13 local:

```text
git status -sb
  ## main...origin/main [ahead 5]

wc -l app/services/search.py app/services/search_hydration.py app/services/search_ranking.py app/services/search_query_features.py app/services/search_history.py
  2496 app/services/search.py
   392 app/services/search_hydration.py
   467 app/services/search_ranking.py
   199 app/services/search_query_features.py
   311 app/services/search_history.py

config/improvement_cases.yaml
  IC-1D03DBFE8492 remains open for app/services/search.py
  observed_failure=line_count=2496 and private_helper_count=42 after the
  search-hydration owner split
  deployed_ref=14390ad

config/hotspot_prevention.yaml
  app/services/search.py target_role=search service compatibility facade
  block_new includes ranking_logic, query_feature_helper, hydration_logic, and
  telemetry_payload_builder

docs/SESSION_HANDOFF.md
  active bounded implementation brief=docs/search_hydration_boundary_milestone_plan.md
  next routed follow-on=search execution persistence and operator-trace payload
  assembly
```

Current structural evidence:

- `app/services/search.py` still owns the public `execute_search(...)` and
  `search_documents(...)` entrypoints and now delegates ranking/query-feature
  families into focused owner modules.
- The hydration cluster now lives in `app/services/search_hydration.py`:
  `_span_chunk_query`, `_span_table_query`, `_hydrate_ranked_chunks`,
  `_hydrate_ranked_span_chunks`, `_hydrate_ranked_tables`,
  `_hydrate_ranked_span_tables`, `_span_evidence_payload`,
  `_supports_retrieval_span_search`, `_load_source_evidence_spans`,
  `_ensure_reranked_result_evidence_spans`, and
  `_hydrate_late_interaction_results`.
- The remaining largest central search family after this split is persistence
  and operator-trace payload assembly:
  `_ranked_result_evidence_payload`, `_reranked_result_evidence_payload`,
  `_persist_search_operator_runs`, `_persist_search_result_spans`, and
  `_persist_search_execution`.
- The current search governance still expects implementation to continue moving
  out of the facade:
  `config/hotspot_prevention.yaml` blocks new `hydration_logic` additions in
  `app/services/search.py` and routes them to `app/services/search_*.py`;
  `config/hygiene_policy.yaml` now locks the narrowed facade at `2496` lines /
  `42` private helpers and governs `app/services/search_hydration.py` at
  `392` lines / `11` private helpers under `IC-1D03DBFE8492`.
- Integration coverage already proves the sensitive behaviors this split must
  preserve:
  `tests/integration/test_postgres_roundtrip.py` verifies persisted search
  evidence spans and `tests/integration/test_multivector_retrieval.py` verifies
  late-interaction trace persistence.

## Goal

Reduce `IC-1D03DBFE8492` by extracting one coherent hydration-family owner
module so that:

- `app/services/search.py` is materially smaller and delegates hydration logic
  through allowed alias-forwarding seams.
- `app/services/search_hydration.py` becomes the focused owner for ranked
  result hydration and retrieval-evidence-span loading.
- Ranked chunk/table hydration, selected-result source evidence loading, and
  late-interaction trace hydration continue to produce the same API-visible
  fields and persisted evidence-span rows.
- The improvement case remains open unless the hotspot is fully resolved, but
  this milestone must leave the owner contract narrower and the ratchets
  tighter than before.

## Non-Goals

- No search-history refactor.
- No telemetry payload split in this packet.
- No persistence-layer move for `SearchRequestRecord`, `SearchRequestResult`,
  or `SearchRequestResultSpan`.
- No reranker feature or candidate-retrieval scoring changes.
- No API/schema contract changes for `/search`,
  `GET /search/requests/{search_request_id}`, or evidence packages.
- No weakening of full integration verification because the change is
  "internal only".

## Owner Surfaces

- `app/services/search.py`
  - role after this plan: compatibility facade and search execution entrypoint
  - allowed growth: import forwarding, alias forwarding, deletion-only
    reductions
- `app/services/search_hydration.py`
  - new owner module for result hydration, span-backed result assembly,
    late-interaction hydration, and selected-result evidence-span loading
- `tests/unit/test_search_hydration.py`
  - focused owner-module contract tests for direct hydration behavior
- existing regression surfaces that must stay green:
  `tests/unit/test_search_service.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/integration/test_multivector_retrieval.py`
- governance and routing surfaces:
  `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`, `docs/SESSION_HANDOFF.md`, and this
  plan

## Placement Rules

- New hydration implementation belongs in `app/services/search_hydration.py`,
  not back in `app/services/search.py`.
- Keep `app/services/search.py` import-stable by re-exporting or aliasing the
  moved helpers where that avoids churn in nearby code or tests.
- Put new direct hydration tests in `tests/unit/test_search_hydration.py`
  instead of growing `tests/unit/test_search_service.py` unless a behavior is
  only meaningful through the public facade.
- If a helper belongs equally to ranking and hydration, keep it with the owner
  that produces or loads `RankedResult`/`RankedEvidenceSpan` values unless a
  cycle would result.
- Tighten hygiene budgets to the verified post-split line and helper counts for
  the narrowed facade and the new owner module.

## Weak-Point Prevention Contract

Weak point forecast: this work could claim a search hotspot reduction while
leaving the hydration family half in the facade, drift late-interaction traces
or evidence-span persistence because only unit tests were rerun, or add a new
owner module without tightening hygiene/governance around it. Another likely
failure is moving code without creating a real bounded brief, leaving the next
session to reconstruct intent from chat history.

Owner surface: `app/services/search.py` owns the public compatibility surface;
`app/services/search_hydration.py` owns hydration-family implementation;
`config/hygiene_policy.yaml` and `config/improvement_cases.yaml` own the
durable ratchet and routing state; this plan, `docs/agentic_architecture_index.md`,
and `docs/SESSION_HANDOFF.md` own the bounded execution record.

Freshness check: rerun the live line-count, hygiene, architecture, and
improvement-case verification commands in the same closeout window before
committing. If the closeout docs cite stale values or the worktree is dirty
from unrelated files, the milestone is not complete.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation |
| --- | --- | --- | --- | --- |
| Hydration logic grows back inside `app/services/search.py` | `app/services/search.py`, `config/hotspot_prevention.yaml` | `uv run docling-system-hotspot-prevention-check --strict` and focused diff review | New hydration helper bodies remain or are added in the facade beyond import/alias forwarding | Add a throwaway helper such as `def _hydrate_more_results(...):` in the facade and confirm the hotspot prevention gate blocks it |
| Evidence spans or late-interaction traces silently drift | `app/services/search_hydration.py`, integration tests | `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py` | Any evidence-span persistence, trace metadata, or search detail contract regression | Temporarily drop evidence-span loading in the owner module and confirm the integration suite fails |
| Closeout claims reduced ownership without tightening durable routing | `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`, docs | `uv run docling-system-hygiene-check`, `uv run docling-system-improvement-case-validate`, and doc alignment review | Search case/hygiene still point at the pre-split line counts or the new owner module is unrouted | Remove the new module budget entry or leave the old search.py ratchet untouched and confirm alignment review catches the mismatch |

## Milestone 1 - Search Hydration Family Extraction

Status: reduced locally after commit

Why this milestone exists:

- It matches the existing search hotspot-prevention rule exactly.
- It is large enough to materially shrink `app/services/search.py` but narrow
  enough to verify end to end in one atomic commit.
- It preserves the public facade while giving future search work a clear owner
  for result materialization and evidence-span assembly.

Implementation scope:

- Create `app/services/search_hydration.py`.
- Move the hydration-family helpers into that module, including span-backed
  query builders that are only meaningful for hydration-backed result
  assembly.
- Update `app/services/search.py` to import/alias the moved helpers and keep
  `execute_search(...)` and retrieval orchestration behavior stable.
- Add focused direct tests in `tests/unit/test_search_hydration.py`.
- Update `config/hygiene_policy.yaml` to lock the narrowed facade and govern
  the new owner module under `IC-1D03DBFE8492`.
- Refresh `config/improvement_cases.yaml`, this plan,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md` to record
  the reduced boundary and the next routed follow-on concern.

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_hydration.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_hydration.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Closeout requirements:

- Update this plan to the final resolved-local status with the actual commit
  hash, verified line counts, and the next routed search follow-on.
- Update `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md` in
  the same commit so the next session does not depend on chat memory.
- Keep the worktree clean after the milestone commit.

Stop conditions:

- Stop and ask only if the extraction would require a public API/schema change,
  a search-history import-cycle change, or weakening the full integration gate.
- Otherwise continue through implementation, verification, docs, and commit in
  this same session.
