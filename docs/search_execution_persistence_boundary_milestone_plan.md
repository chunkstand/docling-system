# Search Execution Persistence Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: resolved locally through Milestone 1 for `IC-1D03DBFE8492` /
`app/services/search.py`; the owner case remains open and the next routed
follow-on stays inside the search compatibility facade
Owner context: follow-on brief created after
`docs/search_hydration_boundary_milestone_plan.md` resolved locally through
Milestone 1 closeout commit `14390ad`; the same search owner case remains open
and the next bounded reduction stays behind the existing search compatibility
facade.

## Local Progress

Milestone 1 is now closed locally. The search execution persistence family is
no longer implemented inside `app/services/search.py`.

Local Milestone 1 snapshot:

- added `app/services/search_execution_persistence.py` as the focused owner
  for ranked-result evidence payload assembly, search request/result
  persistence, result-span persistence, and knowledge-operator trace
  persistence
- moved `_ranked_result_evidence_payload`,
  `_reranked_result_evidence_payload`,
  `_persist_search_operator_runs`,
  `_persist_search_result_spans`, and `_persist_search_execution` behind that
  owner module while keeping `app/services/search.py` import-stable through
  allowed alias forwarding
- hardened `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so persistence/operator-trace growth
  in the facade is blocked directly
- reduced `app/services/search.py` to `2089` lines / `37` private helpers and
  governed `app/services/search_execution_persistence.py` at `423` lines /
  `6` private helpers under the same owner case `IC-1D03DBFE8492`
- added focused direct owner-module coverage in
  `tests/unit/test_search_execution_persistence.py`
- refreshed `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md` so the
  reduced search boundary and next routed follow-on are durable repo state
- architecture probe still routes `app/services/search.py` as the top churn
  hotspot at `30 revisions`, `2089 lines`, and `score 62670`, but the
  architecture-quality summary top-five still excludes `app/services/search.py`
- next routed follow-on inside `IC-1D03DBFE8492`:
  the remaining execution-orchestration cluster in `execute_search(...)` and
  adjacent candidate-loading/detail assembly paths

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_execution_persistence.py tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`:
  pass
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`:
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
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`:
  top hotspot remains `app/cli.py`; `app/services/search.py` stays in the top
  four churn hotspots at `30 revisions`, `2089 lines`, `score 62670`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1883 passed`

## Purpose

Reduce the next coherent owner family inside `app/services/search.py` without
changing the public search contract.

The scoped debt in this packet is the remaining search execution persistence
and operator-trace payload assembly cluster that still lives in the facade:

- `_ranked_result_evidence_payload`
- `_reranked_result_evidence_payload`
- `_persist_search_operator_runs`
- `_persist_search_result_spans`
- `_persist_search_execution`

This plan reduces that debt by moving the persistence cluster behind a focused
owner module while preserving the public facade and equivalent or broader
verification. No milestone in this plan may weaken tests, narrow runtime
coverage, add skips, loosen gates, or relax assertions merely to get green.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 6]

wc -l app/services/search.py app/services/search_hydration.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py
  2496 app/services/search.py
   392 app/services/search_hydration.py
  1845 tests/unit/test_search_service.py
   224 tests/unit/test_search_hydration.py
  1132 tests/integration/test_postgres_roundtrip.py
   346 tests/integration/test_multivector_retrieval.py

config/improvement_cases.yaml
  IC-1D03DBFE8492 remains open for app/services/search.py
  observed_failure=line_count=2496 and private_helper_count=42 after the
  search-hydration owner split
  deployed_ref=14390ad

docs/search_hydration_boundary_milestone_plan.md
  next routed follow-on=search execution persistence and operator-trace payload
  assembly
```

Current structural evidence:

- `app/services/search.py` remains the active top churn hotspot in the live
  architecture probe at `30 revisions`, `2496` lines, and `score 74880`.
- The remaining bounded persistence cluster lives in
  `app/services/search.py:1544-1945`.
- `config/hotspot_prevention.yaml` already blocks new
  `ranking_logic`, `query_feature_helper`, `hydration_logic`, and
  `telemetry_payload_builder` growth in `app/services/search.py`, but it does
  not yet explicitly route persistence/operator-trace payload growth out of the
  facade.
- `tests/integration/test_postgres_roundtrip.py` already proves persisted
  `SearchRequestResultSpan` rows exist for stored search requests, and
  `tests/integration/test_multivector_retrieval.py` already proves
  late-interaction traces, stored search result spans, and operator-run hashes
  survive the runtime path.
- `tests/unit/test_search_service.py` exercises search execution through the
  public facade, but there is no direct owner-module contract yet for the
  persistence cluster itself.

## Goal

Reduce `IC-1D03DBFE8492` by extracting one coherent persistence owner module
so that:

- `app/services/search.py` is materially smaller and delegates persistence
  helpers through import or alias forwarding only.
- `app/services/search_execution_persistence.py` becomes the focused owner for
  search request/result persistence, result-span row creation, and
  operator-trace payload assembly.
- Persisted search request rows, result rows, result-span rows, and
  knowledge-operator traces remain API-visible and audit-visible with
  equivalent or broader coverage.
- The improvement case remains open unless the hotspot is fully retired, but
  this milestone must leave the owner contract narrower and the durable
  governance tighter than before.

## Non-Goals

- No candidate-loading or keyword/semantic retrieval refactor.
- No reranker feature rewrite or scoring change.
- No search-history split or search replay work.
- No API or schema contract changes for `/search`,
  `GET /search/requests/{search_request_id}`, or evidence-package responses.
- No DB model or Alembic migration changes.
- No hydration-family rework; that already lives in
  `app/services/search_hydration.py`.
- No broad README current-state rewrite in this packet. If README is updated
  during closeout, it must be refreshed from live evidence in the same window,
  not partially patched.

## Scope

- Add `app/services/search_execution_persistence.py` as the owner module for
  the persistence cluster.
- Move the five persistence/operator-trace helpers and any tiny local-only
  support code they require into that owner module.
- Keep `execute_search(...)` and public search entrypoints in
  `app/services/search.py`.
- Harden hotspot prevention so new persistence/operator-trace payload logic is
  blocked from landing in `app/services/search.py`.
- Add focused direct unit tests for the new owner module.
- Tighten hygiene budgets and improvement-case measurements to the verified
  post-split counts.
- Update the active plan, architecture index, and session handoff in the same
  milestone closeout commit.

## Out Of Scope

- Moving `observe_search_results(...)` or broader telemetry observation unless
  a tiny forwarding change is required to preserve compilation.
- Moving retrieval span backfill or candidate-resolution helpers.
- Rewriting `SearchExecution`, `SearchHarness`, or the search execution-plan
  orchestration.
- Any change that would require a public HTTP contract migration.

## Owner Surfaces

- `app/services/search.py`
  - role after this plan: compatibility facade and search execution entrypoint
  - allowed growth: import forwarding, alias forwarding, deletion-only
    reductions
- `app/services/search_execution_persistence.py`
  - new owner module for search request/result persistence, result-span row
    creation, and operator-run payload assembly
- `tests/unit/test_search_execution_persistence.py`
  - focused owner-module contract tests for direct persistence behavior
- existing regression surfaces that must stay green:
  `tests/unit/test_search_service.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/integration/test_multivector_retrieval.py`
- governance and routing surfaces:
  `app/hotspot_prevention_classifier.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- New persistence/operator-trace implementation belongs in
  `app/services/search_execution_persistence.py`, not back in
  `app/services/search.py`.
- Keep `app/services/search.py` import-stable by re-exporting or aliasing the
  moved helpers where that avoids churn in nearby code or tests.
- Keep ranking-owned helpers in `app/services/search_ranking.py` and
  hydration-owned helpers in `app/services/search_hydration.py`; do not use
  this milestone to reshuffle unrelated search families.
- Put direct persistence-owner tests in
  `tests/unit/test_search_execution_persistence.py` instead of further growing
  `tests/unit/test_search_service.py` unless a behavior is only meaningful
  through the public facade.
- If a helper belongs equally to persistence and hydration, keep it with the
  owner that writes or materializes `SearchRequestRecord`,
  `SearchRequestResult`, `SearchRequestResultSpan`, or
  `KnowledgeOperatorRun` rows unless a cycle would result.
- Tighten hygiene budgets to the verified post-split line and helper counts for
  both the narrowed facade and the new owner module under
  `IC-1D03DBFE8492`.

## Weak-Point Prevention Contract

Weak point forecast: this work could claim hotspot reduction while leaving the
persistence cluster half in the facade, fail to harden hotspot-prevention rules
for the next slice, drift persisted search trace payloads because only unit
tests were rerun, or create a new owner module without tightening hygiene and
routing around it. Another likely failure is touching only code and leaving the
active handoff/index still pointing at the old resolved hydration brief.

Future-Codex misuse scenario: a later session adds a small `_persist_*`
helper, result-span payload builder, or operator-trace payload formatter
directly in `app/services/search.py` because the facade already owns
`execute_search(...)`. This plan prevents that wrong pattern by hardening the
search hotspot-prevention rule first, adding a controlled-violation test for
the facade, and making `app/services/search_execution_persistence.py` the only
allowed owner surface for new persistence logic.

Freshness check: rerun the live line-count, architecture probe, hotspot,
hygiene, and improvement-case verification commands in the same closeout window
before committing. If the closeout docs cite stale values or the worktree is
dirty from unrelated files that cannot be safely separated, the milestone is
not complete.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation |
| --- | --- | --- | --- | --- |
| Persistence logic grows back inside `app/services/search.py` | `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py`, `tests/unit/test_hotspot_prevention.py` | `uv run pytest -q tests/unit/test_hotspot_prevention.py` and `uv run docling-system-hotspot-prevention-check --strict` | The search hotspot policy still lacks an explicit persistence/operator-trace rule, or a throwaway persistence helper in the facade is not blocked | Add a temporary helper such as `def _persist_more_search_rows(...):` or `def _build_operator_trace_payload(...):` in `app/services/search.py` and confirm the prevention gate fails |
| Search result-span rows or operator traces silently drift | `app/services/search_execution_persistence.py`, integration tests | `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py` and final full-suite rerun | Any regression in persisted `SearchRequestResultSpan` rows, late-interaction trace metadata, `KnowledgeOperatorRun` chaining, or evidence-package audit fields | Temporarily drop persisted span metadata or selected-evidence payload content and confirm the targeted integration tests fail |
| Facade compatibility is preserved only by accident | `app/services/search.py`, `tests/unit/test_search_service.py`, `tests/unit/test_search_execution_persistence.py` | `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py` and focused diff review | Moved helpers still contain implementation bodies in the facade, or public search execution behavior changes without owner-module coverage | Temporarily remove an alias-forwarded helper import or break the returned operator-run IDs and confirm unit coverage fails |
| Closeout claims reduced ownership without tightening durable routing | `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`, this plan, `docs/agentic_architecture_index.md`, `docs/SESSION_HANDOFF.md` | `uv run docling-system-hygiene-check`, `uv run docling-system-improvement-case-validate`, plan lint, and doc alignment review | Post-split line/helper counts are not updated, the new owner module lacks a budget entry, or the active plan/handoff/index disagree on the next routed follow-on | Omit the new module budget or leave the old routing text in the handoff/index and confirm the alignment review catches the mismatch |

## Milestone Sequence

## Milestone 0 - Search Persistence Gate Hardening

Status: resolved locally
Outcome label: reduced

Why this milestone exists:

- The current search hotspot rule blocks ranking, query-feature, hydration, and
  telemetry growth, but not this next persistence/operator-trace slice
  explicitly.
- The repo requires a gate-first step for architecture/hotspot work so that a
  future Codex session cannot re-open the same facade seam immediately after
  the extraction.

Implementation scope:

- Update `config/hotspot_prevention.yaml` so `app/services/search.py` explicitly
  blocks new persistence/operator-trace payload logic in the facade.
- Update `app/hotspot_prevention_classifier.py` so search persistence additions
  classify to the right blocked category instead of falling through to vague
  helper detection.
- Add or update controlled-violation coverage in
  `tests/unit/test_hotspot_prevention.py`.
- Record the current `app/services/search.py` line/helper counts as the
  pre-extraction baseline inside this plan and the owner-case closeout notes.

Verification:

- `git diff --check`
- `uv run pytest -q tests/unit/test_hotspot_prevention.py`
- `uv run docling-system-hotspot-prevention-check --strict`

Milestone outcome requirements:

- The prevention gate fails on a deliberate persistence/operator-trace helper
  added to `app/services/search.py`.
- The milestone is only `reduced`, not `resolved`, because the implementation
  body still lives in the facade until Milestone 1 lands.

## Milestone 1 - Search Execution Persistence Owner Extraction

Status: resolved locally
Outcome label: reduced

Why this milestone exists:

- It is the next routed search owner family named by the resolved hydration
  plan and active handoff.
- It is large enough to materially shrink `app/services/search.py` but narrow
  enough to verify end to end in one atomic commit.
- It preserves the public facade while giving future search work a clear owner
  for persisted request/result rows and operator-trace payloads.

Implementation scope:

- Create `app/services/search_execution_persistence.py`.
- Move `_ranked_result_evidence_payload`,
  `_reranked_result_evidence_payload`,
  `_persist_search_operator_runs`,
  `_persist_search_result_spans`,
  and `_persist_search_execution` into that owner module, plus only the small
  local support code strictly required to keep the module coherent.
- Update `app/services/search.py` to import or alias the moved helpers and keep
  `execute_search(...)` behavior stable.
- Add focused direct tests in
  `tests/unit/test_search_execution_persistence.py`.
- Update `config/hygiene_policy.yaml` to ratchet the narrowed facade down to
  the verified post-split counts and govern the new owner module under
  `IC-1D03DBFE8492`.
- Refresh `config/improvement_cases.yaml`, this plan,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md` to record
  the reduced boundary, the actual closeout commit, and the next routed
  follow-on.

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_execution_persistence.py tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `python /Users/chunkstand/.codex/skills/milestone-plan-writer/scripts/lint_milestone_plan.py --strict docs/search_execution_persistence_boundary_milestone_plan.md`

Milestone outcome requirements:

- `app/services/search.py` is smaller than the current `2496` lines /
  `42` private helpers and only forwards the moved persistence helpers.
- The new owner module has explicit direct contract coverage and an explicit
  hygiene budget.
- The broader owner case remains open unless the architecture-quality routing
  proves terminal closure, so the milestone outcome is `reduced`, not
  `resolved`.

## Required Implementation Artifacts

- `app/services/search_execution_persistence.py`
- import or alias forwarding updates in `app/services/search.py`
- hotspot-prevention governance updates in
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  and `tests/unit/test_hotspot_prevention.py`
- direct owner-module tests in
  `tests/unit/test_search_execution_persistence.py`
- refreshed owner-case and hygiene records in
  `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`

## Required Documentation And Handoff Updates

- update this plan with the final milestone status, verified metrics, and
  actual closeout commit hash
- update `docs/SESSION_HANDOFF.md` with the completed milestone, commands run,
  commit hash, residual risk, and next routed follow-on
- update `docs/agentic_architecture_index.md` so the active search brief and
  routed hotspot both match the finished milestone state
- if README is intentionally touched during closeout, refresh its routed
  current-state snapshot from live evidence in the same closeout window; do not
  leave a partial README update behind

## Required Verification Gates

- Search hotspot prevention gate must fail on a controlled persistence
  violation before the broader extraction lands.
- Targeted unit and targeted integration coverage must pass with no weakened
  assertions.
- The full `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` suite must
  pass before closeout because this change touches a core runtime search path.
- Do not weaken, delete, loosen, narrow, skip, or xfail existing search unit,
  integration, hotspot-prevention, or full-suite coverage to obtain a passing
  result. Any replaced coverage must be equivalent or stronger and must prove
  the contract did not get easier.
- Architecture, capability-contract, hygiene, improvement-case, and probe
  checks must be rerun in the same closeout window so doc updates use live
  evidence rather than stale numbers.
- The milestone plan linter must pass in `--strict` mode after the plan is
  updated to its final closeout state.

## Acceptance Criteria

- `app/services/search_execution_persistence.py` exists and owns the bounded
  search execution persistence cluster named in this plan.
- `app/services/search.py` remains the public execution entrypoint but no
  longer contains the moved persistence implementations; compatibility is
  preserved through import or alias forwarding only.
- `config/hotspot_prevention.yaml` plus
  `app/hotspot_prevention_classifier.py` explicitly prevent new
  persistence/operator-trace payload implementation from landing in the facade,
  and `tests/unit/test_hotspot_prevention.py` proves the gate catches a
  controlled violation.
- Postgres-backed search persistence behavior remains intact:
  `SearchRequestRecord`, `SearchRequestResult`, `SearchRequestResultSpan`, and
  `KnowledgeOperatorRun` rows still materialize with equivalent or broader
  audited behavior, including late-interaction trace persistence.
- `config/hygiene_policy.yaml` and `config/improvement_cases.yaml` are updated
  to the exact post-split line/helper counts and routed follow-on state.
- This milestone is complete only after a local atomic commit contains the
  verified implementation, tests, governance updates, and docs/handoff updates
  for this milestone only. A verified but uncommitted worktree is ready to
  close, not complete.

## Stop Conditions

- Stop and ask only if the extraction would require a public API/schema change,
  a DB model or migration change, a search-history import-cycle change, or test
  weakening to obtain a passing result.
- Stop before commit if targeted integrations, the full DB-backed suite, the
  hotspot-prevention gate, or doc-alignment checks fail.
- Otherwise continue through implementation, verification, docs, and a local
  atomic milestone commit in the same session.

## Local Commit Closeout Policy

- Stage only the verified milestone slice.
- Leave unrelated dirty or untracked files alone.
- Include implementation, tests, governance configs, this plan, and handoff or
  architecture-index updates in the same local commit.
- Record the commit hash in this plan and `docs/SESSION_HANDOFF.md`.
- Treat the milestone as incomplete until that commit exists.

## Residual Risks And Next Milestone Routing

If this milestone lands cleanly, `IC-1D03DBFE8492` should remain open but
reduced. The next routed search follow-on should move to the remaining
execution-orchestration cluster in `execute_search(...)` and adjacent
candidate-loading/detail-assembly paths, not back to hydration or persistence
unless a regression is discovered.

If the hotspot-prevention classifier cannot express a narrow persistence rule
without broader breakage, route that residual governance issue explicitly
through `IC-6C1B516A3F92` instead of silently weakening the search gate.

## Closeout Checklist

- [x] Milestone 0 gate-hardening changes landed and controlled-violation
      coverage proved the search facade blocks persistence/operator-trace
      growth.
- [x] `app/services/search_execution_persistence.py` owns the bounded
      persistence cluster.
- [x] `app/services/search.py` line and helper counts are lower than the
      `2496` / `42` baseline and ratcheted to the verified closeout values.
- [x] Focused unit tests, targeted Postgres integrations, hotspot-prevention,
      hygiene, architecture, capability-contract, improvement-case, and full
      DB-backed suite verification all passed.
- [x] This plan, `docs/SESSION_HANDOFF.md`, and
      `docs/agentic_architecture_index.md` were updated in the same closeout
      slice with live evidence.
- [ ] The milestone was closed with a local atomic commit; otherwise it is not
      complete.
