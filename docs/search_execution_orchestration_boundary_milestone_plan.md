# Search Execution Orchestration Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: resolved locally through Milestone 1 closeout commit `dae5e4f` on
2026-05-13 for `IC-1D03DBFE8492` / `app/services/search.py`; the scoped
execution-orchestration issue is closed, while the broader owner case remains
reduced because `app/services/search.py` still appears in the architecture
probe
Owner context: follow-on brief created after
`docs/search_execution_persistence_boundary_milestone_plan.md` resolved locally
through Milestone 1 closeout commit `f55b474`; the same owner case remains open
and this milestone closes the next bounded search reduction behind the existing
compatibility facade.

## Local Progress

Milestone 1 is closed locally as commit `dae5e4f`. The remaining
execution-orchestration cluster no longer lives in `app/services/search.py`.

Local Milestone 1 snapshot:

- added `app/services/search_execution_orchestration.py` as the focused owner
  for `_load_keyword_candidates`, `_load_semantic_candidates`,
  `_apply_metadata_supplement_stage`, `_resolve_candidate_items`,
  `_build_search_execution_details`, and `execute_search(...)`
- reduced `app/services/search.py` to a `1592` line / `32` private-helper
  compatibility facade with a narrow explicit forwarding wrapper for
  `execute_search(...)`; `search_documents(...)` remains import-stable through
  the facade
- governed `app/services/search_execution_orchestration.py` at `532` lines /
  `6` private helpers under the same owner case `IC-1D03DBFE8492`
- hardened `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so execution-orchestration,
  candidate-loading, and search-detail assembly growth are blocked directly in
  the facade while the forwarding wrapper seam stays allowed
- added focused direct owner-module coverage in
  `tests/unit/test_search_execution_orchestration.py`
- refreshed `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md` so the
  reduced search boundary and the next routed follow-on are durable repo state
- architecture quality still reports `hotspot_count=10` and
  `max_hotspot_risk_score=531.06`; the architecture-quality top-five still
  excludes `app/services/search.py`, but the architecture probe continues to
  route it at `32 revisions`, `1592 lines`, and `score 50944`
- next routed stacked follow-on after this closed search packet:
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`
- local closeout commit: `dae5e4f`

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_execution_orchestration.py app/services/search_execution_persistence.py app/services/search_hydration.py app/hotspot_prevention_classifier.py tests/unit/test_search_service.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`:
  pass
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`:
  `62 passed`
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
- `uv run docling-system-improvement-case-summary`: `case_count=28`,
  `status_counts.open=21`, `status_counts.deployed=6`,
  `status_counts.measured=1`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`:
  top hotspot remains `app/cli.py`; `app/services/search.py` remains in the
  top twelve churn hotspots at `32 revisions`, `1592 lines`, `score 50944`,
  and the Python cycle component count remains `3`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1890 passed`

## Purpose

Resolve the remaining execution-orchestration cluster inside
`app/services/search.py` while preserving the existing public search facade and
limiting the refactor to one new owner module at most.

The scoped debt in this packet is the orchestration and adjacent
candidate-loading/detail-assembly family that still lives in the search facade:

- `_load_keyword_candidates`
- `_load_semantic_candidates`
- `_apply_metadata_supplement_stage`
- `_resolve_candidate_items`
- `_build_search_execution_details`
- `execute_search(...)`
- `search_documents(...)` only as a stable public wrapper or alias-forwarding
  surface

This milestone is intentionally single-packet and end to end. The scoped issue
must be resolved in one local atomic commit or not claimed complete at all. The
broader owner case may remain open after closeout, but this plan does not allow
another partial spill into several new search files.

## Baseline Evidence

Repo evidence captured before implementation from the local checkout on
2026-05-13 local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 8]

wc -l app/services/search.py app/services/search_execution_persistence.py app/services/search_hydration.py tests/unit/test_search_service.py tests/unit/test_hotspot_prevention.py
  2089 app/services/search.py
   423 app/services/search_execution_persistence.py
   392 app/services/search_hydration.py
  1845 tests/unit/test_search_service.py
   477 tests/unit/test_hotspot_prevention.py

uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=531.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app/services/search.py: 31 revisions, 2089 lines, score 64759
  Python cycle components=3

config/improvement_cases.yaml
  IC-1D03DBFE8492 remains open for app/services/search.py
  observed_failure=line_count=2089 and private_helper_count=37 after the
  search execution persistence split
  deployed_ref=f55b474

docs/SESSION_HANDOFF.md
  active follow-up owner case=IC-1D03DBFE8492 / app/services/search.py
  next routed follow-on=remaining execution-orchestration cluster in
  execute_search(...) and adjacent candidate-loading/detail assembly paths
```

Current structural evidence:

- `app/services/search.py` still owns the public `execute_search(...)` and
  `search_documents(...)` search entrypoints.
- The remaining execution-orchestration cluster currently spans
  `app/services/search.py:1548-2069`, with `execute_search(...)` at
  `app/services/search.py:1810-2066`.
- Focused owner modules already exist for adjacent families:
  `app/services/search_hydration.py` owns hydration and evidence-span loading,
  and `app/services/search_execution_persistence.py` owns persistence and
  operator-run payload recording.
- `config/hotspot_prevention.yaml` already blocks new `ranking_logic`,
  `query_feature_helper`, `hydration_logic`, `persistence_logic`,
  `operator_trace_payload_builder`, and `telemetry_payload_builder` growth in
  `app/services/search.py`, but it does not yet explicitly block
  execution-orchestration or candidate-loading/detail-assembly growth in the
  facade.
- Stable search callers currently import through `app.services.search`,
  including `app/services/chat.py`, `app/services/evaluations.py`,
  `app/services/search_history.py`, `app/services/search_replays.py`, and
  `app/services/agent_actions/report_evidence.py`; public import stability
  matters even though this milestone is internal.
- Integration coverage already proves the sensitive runtime path this split
  must preserve:
  `tests/integration/test_postgres_roundtrip.py` verifies stored search result
  spans and persisted search-request rows, and
  `tests/integration/test_multivector_retrieval.py` verifies late-interaction
  traces, stored result spans, and operator-run evidence.

## Goal

Resolve the scoped execution-orchestration debt by moving it behind one focused
owner module so that:

- `app/services/search.py` stops owning the stage loop and adjacent
  candidate-loading/detail-assembly bodies.
- At most one new owner module is introduced for this milestone:
  `app/services/search_execution_orchestration.py`.
- The existing public import surface remains stable through
  `app.services.search`.
- Search request persistence, result-span persistence, metadata supplement,
  late-interaction fallback behavior, reranking, and emitted execution details
  remain equivalent or better covered.
- The scoped milestone issue is `resolved` only when the orchestration cluster
  no longer lives in the facade except for an allowed wrapper/dependency-bundle
  seam.
- The broader owner case `IC-1D03DBFE8492` is `reduced` unless the refreshed
  live architecture evidence proves the overall hotspot is retired.

## Non-Goals

- No search-history, replay, or chat-answer refactor.
- No reranker scoring rewrite, metadata-query redesign, or quality-tuning pass.
- No DB model, Alembic, API schema, or HTTP contract change.
- No new owner family beyond one orchestration module in this milestone.
- No split of persistence or hydration ownership back out of their current
  modules.
- No weakening of tests, narrower gates, added skips, or looser assertions to
  get green.

## Scope

In scope:

- one new owner module for search execution orchestration:
  `app/services/search_execution_orchestration.py`
- moving the stage loop and adjacent candidate-loading/detail-assembly helpers
  into that owner module
- a small typed dependency bundle or explicit wrapper seam in
  `app/services/search.py` if needed to avoid a new import cycle while keeping
  the facade import-stable
- hotspot-prevention hardening so new execution-orchestration logic cannot land
  back in `app/services/search.py`
- focused direct owner-module unit coverage
- hygiene and improvement-case updates for the narrowed facade and the new
  orchestration owner
- architecture index and session handoff updates in the same closeout commit

Out of scope:

- moving low-level keyword, semantic, or span SQL primitives into additional
  new sibling files
- moving `search_execution_persistence.py` or `search_hydration.py` concerns
  again
- introducing a second orchestration helper module such as
  `search_candidate_loading.py` or `search_execution_details.py`
- touching unrelated evaluation, replay, or agent-action paths unless a tiny
  import or signature adjustment is required for compilation

## Owner Surfaces

- `app/services/search.py`
  - role after this milestone: compatibility facade, primitive search helper
    surface, and explicit wrapper/dependency-bundle seam only
  - allowed growth: import forwarders, alias forwarders, explicit forwarding
    wrappers, typed dependency-bundle assembly, and deletions
- `app/services/search_execution_orchestration.py`
  - new owner module for the stage loop, candidate loading/merging orchestration,
    served-mode resolution, detail-payload assembly, and public execution flow
- stable dependency surfaces that may be touched only minimally if required:
  `app/services/search_plan.py`,
  `app/services/search_hydration.py`,
  `app/services/search_execution_persistence.py`,
  `app/services/search_ranking.py`
- tests:
  `tests/unit/test_search_execution_orchestration.py`,
  `tests/unit/test_search_service.py`,
  `tests/unit/test_search_execution_persistence.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/integration/test_multivector_retrieval.py`
- governance and routing surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- New execution-orchestration implementation belongs in
  `app/services/search_execution_orchestration.py` and nowhere else.
- Do not create additional sibling owner files for candidate loading, detail
  payloads, or served-mode selection in this milestone.
- Keep `app/services/search.py` as the public import surface for
  `execute_search(...)` and `search_documents(...)`; existing callers should not
  need import rewrites.
- Prefer a small typed dependency bundle or explicit wrapper seam from
  `app/services/search.py` into the new owner module over importing the new
  owner module back into retained low-level helper files in a way that raises
  the Python cycle count.
- Keep hydration logic in `app/services/search_hydration.py`, persistence logic
  in `app/services/search_execution_persistence.py`, and planning logic in
  `app/services/search_plan.py`; this milestone may call those modules but may
  not absorb their ownership.
- If one or two low-level helpers must move to keep the new module acyclic,
  they must move into `app/services/search_execution_orchestration.py` in the
  same milestone, not into a second new file.
- Put direct owner tests in `tests/unit/test_search_execution_orchestration.py`
  instead of growing `tests/unit/test_search_service.py` further unless the
  behavior is only meaningful through the public facade.
- Tighten hygiene ceilings in the same milestone:
  `app/services/search_execution_orchestration.py` must close at `<= 600` lines
  and `<= 15` private helpers; `app/services/search.py` must close at
  `<= 1700` lines and `<= 32` private helpers, then record the exact verified
  numbers in `config/hygiene_policy.yaml`.

## Weak-Point Prevention Contract

Freshness check: rerun the live architecture, hygiene, improvement-case, and
integration commands in the same closeout window before committing. If the plan
or handoff cites stale values, the milestone is not complete.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Execution-orchestration logic grows back inside `app/services/search.py` | `app/services/search.py`, `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py` | `uv run docling-system-hotspot-prevention-check --strict` plus `tests/unit/test_hotspot_prevention.py` | Any new stage-loop, candidate-loading, or detail-payload helper body lands in the facade beyond an allowed wrapper/dependency-bundle seam | Add a temporary helper such as `def _run_execution_stage(...):` in `app/services/search.py` and confirm the hotspot-prevention gate fails | A later session appends “just one more stage” to `execute_search(...)` because the facade already owns the public entrypoint |
| The split sprays into multiple new search owner files or just recreates another large hotspot elsewhere | `app/services/search_execution_orchestration.py`, `config/hygiene_policy.yaml`, staged file list | `uv run docling-system-hygiene-check` plus staged-slice review before commit | More than one new search execution owner file is added, or the new owner module exceeds `600` lines / `15` private helpers | Add a temporary oversized helper cluster to the new owner module and confirm hygiene fails on the line/helper ceilings | A future session creates `search_candidate_loading.py` and `search_execution_details.py` because the first orchestration split did not forbid further sharding |
| Runtime behavior drifts even though the change is “internal” | `app/services/search_execution_orchestration.py`, integration tests, public facade tests | `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py` and `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py` | Any regression in persisted search-request rows, result spans, metadata supplement behavior, late-interaction traces, or public search result payloads | Temporarily remove metadata-candidate merge or late-interaction detail propagation and confirm the targeted tests fail | A later session “cleans up” orchestration by dropping a path that only integration coverage currently proves |
| The refactor introduces a new dependency cycle or inverts the intended facade direction | `app/services/search.py`, `app/services/search_execution_orchestration.py`, architecture probe output | `uv run docling-system-architecture-inspect` and `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12` | Python cycle component count rises above the current baseline of `3`, or the new owner module imports `app.services.search` directly | Add a temporary direct `from app.services.search import ...` import inside the new owner module and confirm the cycle review blocks closeout | A future session uses direct back-imports from the facade because wrappers are convenient |

Accepted residual risk after closeout: the broader owner case may remain open
even if the scoped orchestration issue is resolved. If the refreshed quality and
probe evidence still route `IC-1D03DBFE8492`, record that state explicitly as
`reduced` and choose the next owner family only from fresh post-closeout
evidence.

## Milestone Sequence

This plan is intentionally one implementation milestone with gate-first steps.
Do not split it into separate “preparation” and “later implementation”
milestones. The milestone is complete only after verification, doc updates, and
one local atomic commit.

### Milestone 1 - Search Execution Orchestration Owner Extraction

Status: drafted
Outcome label: `resolved` for the scoped execution-orchestration issue and
`reduced` for the broader owner case unless the live hotspot fully retires

#### Step 1 - Gate the facade before moving code

Outcome label: `resolved`

Implementation:

- Extend `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so `app/services/search.py` also
  blocks new execution-orchestration, candidate-loading, and search-detail
  payload builder logic.
- Add or update `tests/unit/test_hotspot_prevention.py` with a controlled
  violation proving the new search-facade rule fires on orchestration growth.

Acceptance for this step:

- `uv run docling-system-hotspot-prevention-check --strict` passes on the real
  change set.
- The controlled violation would fail the gate if reintroduced.
- The gate still allows the intended wrapper/dependency-bundle seam in
  `app/services/search.py`.

#### Step 2 - Move the orchestration cluster into one owner module

Outcome label: `resolved`

Implementation:

- Add `app/services/search_execution_orchestration.py`.
- Move the scoped orchestration family into that owner module:
  `_load_keyword_candidates`, `_load_semantic_candidates`,
  `_apply_metadata_supplement_stage`, `_resolve_candidate_items`,
  `_build_search_execution_details`, and `execute_search(...)`.
- Keep `search_documents(...)` public through `app/services/search.py` as a
  stable wrapper or alias-forwarding seam. If `search_documents(...)` itself is
  moved, the facade must still expose the same import surface.
- Use one typed dependency bundle or explicit forwarding seam from
  `app/services/search.py` if needed so the new owner module does not import the
  facade directly.
- Do not create a second new search execution owner file.
- Add direct owner coverage in
  `tests/unit/test_search_execution_orchestration.py`.

Acceptance for this step:

- `app/services/search.py` no longer contains the scoped orchestration family
  except for the allowed public wrapper/dependency seam.
- `app/services/search_execution_orchestration.py` stays within `<= 600` lines
  and `<= 15` private helpers.
- `app/services/search.py` closes within `<= 1700` lines and `<= 32` private
  helpers.
- The new owner module does not import `app.services.search` directly.
- Public `execute_search(...)` and `search_documents(...)` imports remain stable
  through `app.services.search`.

#### Step 3 - End-to-end closeout and routing update

Outcome label: `reduced`

Implementation:

- Refresh `config/hygiene_policy.yaml` with the exact verified post-split
  ceilings for `app/services/search.py` and
  `app/services/search_execution_orchestration.py`.
- Update `config/improvement_cases.yaml` so `IC-1D03DBFE8492` records the
  post-closeout measurement and labels the broader case `reduced` unless the
  live quality evidence proves retirement.
- Update `docs/agentic_architecture_index.md`, `docs/SESSION_HANDOFF.md`, and
  this plan with the completed milestone, verification commands, commit hash,
  and next routed follow-on if any remains.
- Stage only the verified search milestone slice and close with one local atomic
  commit.

Acceptance for this step:

- All required verification gates below pass in the same closeout window.
- Durable docs and handoff are updated in the same commit as code and tests.
- The milestone commit records the exact closeout hash in the handoff and plan.
- If `app/services/search.py` still remains a routed hotspot after refresh, the
  remaining issue is named explicitly and routed from fresh post-closeout
  evidence rather than precommitted guesswork.

## Required Implementation Artifacts

- `app/services/search_execution_orchestration.py`
- `tests/unit/test_search_execution_orchestration.py`
- updated `app/services/search.py`
- updated hotspot-prevention policy and classifier
- updated hygiene and improvement-case registry entries
- updated architecture index and session handoff

## Required Documentation And Handoff Updates

- this plan:
  `docs/search_execution_orchestration_boundary_milestone_plan.md`
- architecture index:
  `docs/agentic_architecture_index.md`
- canonical handoff:
  `docs/SESSION_HANDOFF.md`
- improvement-case routing and measurement:
  `config/improvement_cases.yaml`
- hygiene ratchets:
  `config/hygiene_policy.yaml`

If the implementation introduces a new explicit wrapper/dependency seam that a
future search milestone must honor, document that rule in
`docs/architecture_boundaries.md` during closeout.

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_execution_orchestration.py app/services/search_execution_persistence.py app/services/search_hydration.py app/hotspot_prevention_classifier.py tests/unit/test_search_service.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

If any verification command fails, the milestone does not close and must not be
committed as complete.

## Acceptance Criteria

- The scoped execution-orchestration issue is `resolved` only if the stage loop
  and adjacent candidate-loading/detail-assembly family no longer live in
  `app/services/search.py` except for an allowed wrapper/dependency seam.
- The milestone introduces no more than one new `app/services/search_*.py`
  owner module.
- `app/services/search_execution_orchestration.py` closes at `<= 600` lines and
  `<= 15` private helpers.
- `app/services/search.py` closes at `<= 1700` lines and `<= 32` private
  helpers, then records the exact verified ceiling in `config/hygiene_policy.yaml`.
- `app.services.search` continues to expose stable `execute_search(...)` and
  `search_documents(...)` imports for existing callers.
- `uv run docling-system-hotspot-prevention-check --strict` passes and the new
  controlled-violation test proves the gate blocks orchestration logic from
  re-entering the facade.
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`
  passes with no new skips or narrowed scope.
- `uv run docling-system-architecture-inspect` remains valid and the
  architecture probe does not raise Python cycle components above the current
  baseline of `3`.
- `config/improvement_cases.yaml` records the refreshed measurement for
  `IC-1D03DBFE8492` and labels the broader case `reduced` unless the live
  hotspot evidence proves it is fully retired.
- No tests, gates, or fixtures are weakened to obtain a passing result. Any
  test changes must be equivalent or stronger contract coverage.

## Stop Conditions

- Stop if avoiding a new import cycle requires more than one new orchestration
  owner file.
- Stop if the single owner-module shape would exceed the `600` line or
  `15` private-helper ceilings.
- Stop if the search facade cannot be reduced below `1700` lines /
  `32` private helpers without expanding the milestone into low-level query
  primitive families.
- Stop if the hotspot-prevention classifier cannot distinguish allowed
  wrappers/dependency seams from forbidden orchestration growth in the facade.
- Stop if integration verification fails in a way that requires API, schema, or
  DB contract changes outside this milestone.
- Stop if unrelated dirty changes cannot be separated safely from the verified
  milestone slice.

## Local Commit Closeout Policy

- Stage only the verified search orchestration milestone slice.
- Leave unrelated dirty and untracked files alone.
- Include code, tests, config, docs, and handoff updates that describe the
  completed milestone in the same local atomic commit.
- Record the closeout commit hash in this plan and in `docs/SESSION_HANDOFF.md`.
- Treat the milestone as incomplete until that commit exists.
- Do not commit if any required verification gate fails.

## Residual Risks And Next Milestone Routing

- Most likely residual risk: `app/services/search.py` may still remain a routed
  hotspot after the orchestration cluster is removed because low-level query
  primitives, metadata supplement helpers, or late-interaction internals remain
  in the facade.
- If that happens, the broader owner case `IC-1D03DBFE8492` remains `reduced`,
  not `resolved`.
- The next routed follow-on must be chosen from fresh post-closeout evidence in
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`, and the architecture probe.
- Do not predeclare the next owner family before that closeout evidence exists.
