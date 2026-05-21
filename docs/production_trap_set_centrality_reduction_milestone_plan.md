# Production Trap-Set Centrality Reduction Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: proposed in the current checkout as a standalone technical-paydown
packet after the routed queue, broader-rebaseline queue, and Python-cycle
backlog all closed locally.
Owner context: the live architecture-quality summary now reports
`top_routed_hotspot_paths=[]`, `broader_rebaseline_candidate_count=0`,
`top_broader_rebaseline_paths=[]`, `broad_facade_count=2`, and
`stale_facade_hotspot_count=20`. The queue is empty, but the repo still carries
an intentionally governed production trap set centered on
`app/db/models.py`, `app/services/agent_task_actions.py`,
`app/services/evidence.py`, `app/cli.py`, `app/services/agent_tasks.py`,
`app/services/search.py`, `app/services/audit_bundles.py`, and the adjacent
schema facade `app/schemas/agent_tasks.py`. Most of those roots are already
small compatibility or dispatch facades; the remaining debt is structural
centrality, not unsplit line count.

## Purpose

Reduce the remaining production trap-set centrality without reopening the
already-resolved hotspot-routing interpretation work or the already-split owner
families behind these facades.

This packet exists because the repo has moved past queue-selected hotspot
splits. What remains is a cross-cutting centrality problem:

- very high import fan-in still concentrates callers on a few legacy public
  surfaces
- orchestration and dispatch roots still import too many sibling owners
- the current governance state preserves these roots as compatibility traps, but
  it does not yet ratchet their importer or fan-out gravity down

## Current Evidence

- `uv run docling-system-architecture-quality-report --summary` currently
  reports `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=20`, `stale_facade_hotspot_count=20`,
  `max_hotspot_risk_score=466.06`, `top_routed_hotspot_paths=[]`,
  `broader_rebaseline_candidate_count=0`, and
  `top_broader_rebaseline_paths=[]`.
- The same live summary keeps the production trap set visible through
  `routing_trap_paths`, including
  `app/db/models.py`, `app/services/agent_task_actions.py`,
  `app/services/evidence.py`, `app/cli.py`, `app/schemas/agent_tasks.py`,
  `app/services/agent_tasks.py`, `app/services/search.py`, and
  `app/services/audit_bundles.py`.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 25`
  currently reports the strongest remaining production fan-in on
  `app.db.models` (`337` importers), `app.services.evidence` (`42`),
  `app.schemas.agent_tasks` (`37`), and `app.services.agent_tasks` (`26`).
- The same live probe reports the strongest remaining production fan-out on
  `app.services.agent_task_actions` (`18` imports),
  `app.services.evidence` (`17`), `app.services.audit_bundles` (`14`),
  `app.services.agent_tasks` (`13`), and `app.services.search` (`12`).
- Current line counts confirm that this is no longer a pure file-size problem:
  `app/db/models.py=159`, `app/services/agent_task_actions.py=163`,
  `app/services/evidence.py=141`, `app/cli.py=213`,
  `app/services/agent_tasks.py=324`, `app/services/search.py=231`,
  `app/services/audit_bundles.py=595`, and
  `app/schemas/agent_tasks.py=38`.
- `docs/architecture_boundaries.md` already records the routing-source-of-truth
  rule: fresh packet selection must come from `top_routed_hotspot_paths`, while
  `routing_trap_paths`, `stale_facade_hotspot_count`, and
  `broad_facade_count` remain measurement signals. That mechanical interpretation
  debt is already closed; this packet is about the remaining centrality behind
  the trap set itself.
- `docs/db_models_caller_migration_boundary_milestone_plan.md` already exists
  as a narrower optional follow-on for `app.db.models` importer gravity. That
  brief remains useful, but it is too narrow for the current selected debt and
  should be treated as the DB caller-migration lane inside this broader packet.

## Goal

- Reduce importer gravity on the selected production trap roots through bounded
  caller migration instead of more facade splitting.
- Reduce orchestration gravity on the selected dispatch roots by pushing
  implementation back into already-existing owner families.
- Add machine-checked importer and fan-out ratchets so future sessions cannot
  quietly rebuild the same centrality debt.
- Close this packet only when the selected roots either leave the live
  trap-set metrics or remain as explicitly accepted legacy shims with durable
  ceilings, allowlists, and no hidden backlog.

## Non-Goals

- Do not reopen the hotspot-routing interpretation packet or change how
  `top_routed_hotspot_paths` versus `routing_trap_paths` are defined unless a
  later closeout needs one small governance extension to record accepted legacy
  shims.
- Do not move additional ORM definitions out of `app/db/model_domains/`.
- Do not reopen the already-closed search, evidence, agent-task, or audit owner
  splits merely to restate prior work.
- Do not create new broad convenience facades that replace one central choke
  point with another.
- Do not weaken tests, architecture gates, hotspot-prevention rules, or
  integration verification to make centrality metrics look better.
- Do not mix unrelated UI, runtime-health, downloader, or parser work into this
  packet.

## Scope

In scope:

- `app/db/models.py`
- `app/services/agent_task_actions.py`
- `app/services/evidence.py`
- `app/cli.py`
- `app/services/agent_tasks.py`
- `app/services/search.py`
- `app/services/audit_bundles.py`
- `app/schemas/agent_tasks.py`
- new bounded public caller surfaces when needed, such as `app/db/public/*`,
  `app/services/*_views.py`, `app/services/*_contracts.py`,
  `app/services/*_lifecycle.py`, or `app/cli_commands/*`
- importer-policy and centrality-ratchet tests
- architecture-governance config or report code only where needed to encode the
  new ratchets or accepted-legacy closeout state
- durable current-state docs:
  `docs/production_trap_set_centrality_reduction_milestone_plan.md`,
  `docs/db_models_caller_migration_boundary_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/architecture_boundaries.md`,
  `docs/architecture_decisions.yaml`, and
  `docs/architecture_decision_map.json`

Out of scope:

- unrelated test-only trap roots such as
  `tests/unit/test_hotspot_prevention.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/unit/test_search_api.py` unless a touched production lane requires a
  stronger companion test
- claim-support, retrieval-learning, or hotspot-classifier residual owner
  families that are not part of the selected production roots
- new API features, schema changes, migrations, or behavior changes unrelated
  to centrality reduction

## Owner Surfaces

- Legacy public DB facade: `app/db/models.py`
- Adjacent schema facade: `app/schemas/agent_tasks.py`
- Production dispatch facades:
  `app/services/agent_task_actions.py`,
  `app/services/evidence.py`,
  `app/cli.py`,
  `app/services/agent_tasks.py`,
  `app/services/search.py`,
  `app/services/audit_bundles.py`
- Existing owner families that should absorb migrated behavior instead of
  regrowing the roots:
  `app/db/model_domains/*`,
  `app/services/agent_actions/*`,
  `app/services/agent_task_*`,
  `app/services/evidence_*`,
  `app/services/search_*`,
  `app/services/audit_*`,
  `app/services/technical_reports.py`,
  `app/cli_commands/*`,
  `app/schemas/agent_task_*`
- Governance surfaces:
  `config/hotspot_prevention.yaml`,
  `config/architecture_inspection.yaml`,
  `app/architecture_inspection.py`,
  `app/architecture_quality.py`,
  `tests/unit/test_architecture_inspection.py`,
  `tests/unit/test_hotspot_prevention.py`
- New centrality-ratchet tests such as
  `tests/unit/test_trap_set_caller_routes.py` and
  `tests/unit/test_trap_set_centrality_budget.py`

## Placement Rules

- Keep the selected trap roots as compatibility or dispatch facades only. New
  implementation belongs in the existing owner families behind them.
- Any new DB caller-facing surface must live under `app/db/public/`; do not let
  application callers import `app.db.model_domains.*` directly.
- Any new service helper or lifecycle extraction must be bounded to one owner
  family. Do not create a new shared “support” sink that spans search, audit,
  evidence, and agent-task concerns.
- `app/cli.py` may own command registration and top-level dispatch only. New
  command implementation belongs in `app/cli_commands/*`.
- `app/schemas/agent_tasks.py` may remain a public schema aggregator only if
  sibling callers migrate to narrower schema modules and the root stops growing.
- When a caller spans multiple bounded families, prefer multiple narrow imports
  over a new umbrella facade.
- Any accepted legacy shim must have a named allowlist, a ratcheted ceiling,
  and an explicit closeout note in the packet docs. Hidden “we know this is
  still broad” residuals are not allowed.

## Weak-Point Prevention Contract

- Weak point forecast: the packet creates new narrow public surfaces, but one
  of them becomes a second monolith and simply recreates the current trap set
  under a new name
  Owner surface: `app/db/public/*`, new service or schema public facades,
  centrality-ratchet tests
  Prevention gate: export-manifest tests, per-module line-count review, and
  final architecture diff review for every new public surface
  Fail threshold: any new public surface spans multiple unrelated owner
  families or becomes the new highest-fan-in entrypoint for the same caller set
  Controlled violation: add a cross-family export to a new public facade and
  prove the route-budget test fails
  Future-Codex misuse scenario: a future session adds “just one more” search,
  evidence, or agent-task symbol to the newest facade because it already exists

- Weak point forecast: caller migration reduces imports from one trap root by
  pushing callers onto internal modules, spreading dependency debt instead of
  shrinking it
  Owner surface: importer-policy tests and architecture-inspection rules
  Prevention gate: repo-wide checks that reject direct imports of internal owner
  modules outside their allowed boundary and ratchet direct root-import counts
  down
  Fail threshold: a migrated caller imports `app.db.model_domains.*`,
  `app.services.search_*`, `app.services.evidence_*`,
  `app.services.agent_task_*`, or `app.cli_commands.*` from an unapproved
  boundary
  Controlled violation: add a fixture file that imports one internal owner
  directly and prove the policy gate fails
  Future-Codex misuse scenario: a future session bypasses a narrow public route
  because importing an internal owner is faster

- Weak point forecast: the packet adds gates but leaves the selected metrics
  flat, so centrality debt is now merely documented rather than reduced
  Owner surface: centrality-budget tests, plan closeout metrics, handoff docs
  Prevention gate: Milestone 0 baseline inventory plus ratcheted maxima for
  direct importer counts and fan-out counts on every selected root
  Fail threshold: a later milestone closes without lowering at least one
  selected centrality metric and without keeping all other selected metrics at
  or below baseline
  Controlled violation: add a new direct import of `app.db.models` or a new
  sibling import in `app/services/search.py` and prove the budget test fails
  Future-Codex misuse scenario: a future milestone claims “no new hotspot” even
  though all of the old fan-in and fan-out counts stayed unchanged

- Weak point forecast: the packet shifts complexity into adjacent owner modules
  or tests, recreating broad sinks behind the reduced facades
  Owner surface: selected owner families, hotspot-prevention policy, focused
  unit and integration tests
  Prevention gate: debt-shift review against touched sibling owners,
  hotspot-prevention strict check, and exact-ratchet or budget assertions on
  newly created owners
  Fail threshold: any touched sibling owner becomes the new uncontrolled broad
  sink, or focused replacement coverage is weaker than the root coverage it
  replaced
  Controlled violation: move multiple unrelated concerns into one new support
  file and prove the hotspot-prevention or ratchet tests fail
  Future-Codex misuse scenario: a future session “keeps the root small” by
  dumping unrelated logic into one large sibling helper

- Weak point forecast: `app/cli.py` and the service facades remain accepted as
  “legacy,” but no machine-readable closeout state explains why they still
  appear in the trap set
  Owner surface: architecture-quality summary, architecture-boundary docs, and
  packet closeout docs
  Prevention gate: closeout doc requirement plus a machine-readable accepted
  legacy inventory if any selected root remains in `routing_trap_paths`
  Fail threshold: the packet claims completion while selected roots still appear
  in the trap set without an allowlist, ceiling, and accepted-legacy note
  Controlled violation: leave one selected root in the trap set with no closeout
  record and prove the doc-alignment review fails
  Future-Codex misuse scenario: a future session sees an unchanged trap root,
  assumes it is still active debt, and pulls the wrong packet

## Milestone Sequence

### Milestone 0: Freshness Lock And Selected-Root Census

Outcome label: resolved

Purpose:
Lock the packet to fresh live measurements and convert the vague “controlled
trap set” into a bounded selected-root inventory with exact baseline counts.

Scope:

- rerun the live architecture-quality summary and architecture probe
- record baseline importer and fan-out counts for every selected root
- classify each selected root as caller-gravity, orchestration-gravity, or
  accepted-legacy candidate
- update the architecture decision docs so this packet explicitly supersedes the
  narrower standalone `app.db.models` caller brief when the broader trap-set
  lane is chosen

Acceptance:

- the packet records a reproducible baseline for all selected roots
- the selected-root list is closed and discoverable in the current-state docs
- the older `app.db.models` caller brief is marked as a detailed sublane or
  absorbed reference, not a parallel top-level packet

### Milestone 1: Gate-First Centrality Ratchets

Outcome label: resolved

Purpose:
Create the failing-or-baseline gates that prove later work actually reduces
centrality rather than only moving code around.

Scope:

- add selected-root importer-budget and fan-out-budget tests
- add any needed architecture-inspection or hotspot-prevention support so the
  selected roots, allowlists, and ceilings are machine-readable
- add at least one controlled-violation fixture per gate family

Acceptance:

- every selected root has an explicit baseline ceiling
- the gates fail when a new direct caller import or sibling-import fan-out is
  added outside policy
- the gates allow legacy shims only through explicit allowlists and named
  owner-family routes

### Milestone 2: Caller-Gravity Reduction Lane

Outcome label: reduced

Purpose:
Shrink direct importer gravity on the highest-fan-in selected roots without
reopening internal owner splits.

Scope:

- absorb `docs/db_models_caller_migration_boundary_milestone_plan.md` as the
  `app.db.models` lane
- add bounded caller surfaces where needed, such as `app/db/public/*`
- migrate selected callers off `app.db.models`, `app/services/evidence.py`,
  `app/services/agent_tasks.py`, and `app/schemas/agent_tasks.py`
- update compatibility and schema contract tests so the narrower routes become
  the preferred import paths

Acceptance:

- `app.db.models` importer count is lower than the Milestone 0 baseline
- `app.services.evidence`, `app.services.agent_tasks`, and
  `app.schemas.agent_tasks` importer counts are each lower than the Milestone 0
  baseline
- no migrated caller reaches into internal owner modules directly
- all compatibility, metadata, schema, and DB-backed tests remain green

Remaining issue after closeout:

- orchestration gravity may still remain on the selected dispatch roots even
  after caller fan-in is reduced

### Milestone 3: Orchestration-Gravity Reduction Lane

Outcome label: reduced

Purpose:
Shrink sibling-owner fan-out and dispatch gravity on the selected orchestration
roots.

Scope:

- reduce sibling-owner imports and implementation ownership in
  `app/services/agent_task_actions.py`, `app/services/search.py`,
  `app/services/audit_bundles.py`, and `app/cli.py`
- push command behavior into `app/cli_commands/*` and service behavior into the
  already split owner families behind the facades
- add focused route and dispatch tests so the reduced roots stay small and
  implementation-free

Acceptance:

- `app.services.agent_task_actions`, `app.services.search`, and
  `app.services.audit_bundles` fan-out counts are each lower than the Milestone
  0 baseline
- `app/cli.py` owns registration and dispatch only; new command implementation
  lives in `app/cli_commands/*`
- focused replacement tests are stronger than the root coverage they replace

Remaining issue after closeout:

- a small set of selected roots may still persist as accepted legacy shims if
  their remaining centrality is deliberate and bounded

### Milestone 4: Accepted-Legacy Closeout Or Final Exit

Outcome label: resolved

Purpose:
Close the packet by making the post-migration state explicit and machine-checked
instead of leaving ambiguous trap-set residue.

Scope:

- rerun the live architecture-quality summary, architecture probe, hotspot
  prevention, hygiene, and full DB-backed suite
- lower `stale_facade_hotspot_count` from the Milestone 0 baseline where the
  report supports it
- if a selected root still appears in the trap set, record it as an accepted
  legacy shim with a named allowlist, ceiling, and closeout note
- route any truly remaining per-root work into fresh standalone follow-ons
  rather than leaving this umbrella packet half-open

Acceptance:

- this packet no longer depends on undocumented residual trap-set debt
- every selected root either exits the live trap set or is recorded as an
  accepted legacy shim with machine-checked ceilings
- no selected root ends above its Milestone 0 importer or fan-out baseline
- future sessions can tell from the current-state docs whether the selected
  debt is closed, accepted, or rerouted

## Required Implementation Artifacts

- centrality-ratchet tests for importer and fan-out budgets
- any controlled-violation fixtures used to prove the new gates fail
- bounded caller surfaces such as `app/db/public/*` only where needed
- focused route, dispatch, and compatibility tests for reduced roots
- any small architecture-governance config or summary extensions needed to
  record accepted legacy shims honestly

## Required Documentation And Handoff Updates

- `docs/production_trap_set_centrality_reduction_milestone_plan.md`
- `docs/db_models_caller_migration_boundary_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/architecture_boundaries.md`
- `docs/architecture_decisions.yaml`
- `docs/architecture_decision_map.json`
- any touched improvement-case or hotspot-policy docs needed to keep the
  selected roots discoverable

Closeout requirement:

- every milestone must update the active plan, the handoff, and the compact
  architecture index in the same atomic commit as the implementation and tests

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app tests`
- focused unit tests for any touched caller routes, dispatch roots, schema
  routes, and hotspot-governance gates
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 25`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`

Additional touched-surface gates:

- if `app/db/models.py` or any DB caller surface changes:
  `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/unit/test_db_models_facade_contract.py tests/unit/test_db_model_import_compatibility.py tests/integration/test_db_model_metadata.py -q`
- if `app/cli.py` or `app/cli_commands/*` changes:
  focused CLI entrypoint and command-family tests
- if `app/services/search.py`, `app/services/evidence.py`, or
  `app/services/agent_tasks.py` changes:
  focused HTTP, service, and integration coverage for the touched owner family

## Acceptance Criteria

- The live summary used at closeout still reports
  `top_routed_hotspot_paths=[]`; this packet must not manufacture a fake queued
  hotspot to justify itself.
- The selected-root baseline from Milestone 0 is recorded in durable docs or a
  repo-owned gate artifact and is reproducible from commands in the repo.
- No selected root ends the packet with higher importer or fan-out counts than
  its Milestone 0 baseline.
- `app.db.models`, `app.services.evidence`, `app.services.agent_tasks`, and
  `app.schemas.agent_tasks` each end with a lower direct importer count than
  baseline or an explicit accepted-legacy ceiling that is lower than the
  starting count.
- `app.services.agent_task_actions`, `app.services.search`, and
  `app.services.audit_bundles` each end with a lower fan-out count than
  baseline or an explicit accepted-legacy ceiling that is lower than the
  starting count.
- `app/cli.py` ends as a registration and dispatch root only, with command
  implementation owned by `app/cli_commands/*`.
- Replacement tests are equal or stronger than the route, compatibility, and
  dispatch coverage they supersede; no weakening through skip, xfail, narrowed
  assertions, or deleted negative-path checks is allowed.
- The final current-state docs make it obvious whether each selected root is
  closed, accepted, or rerouted.

## Stop Conditions

- Stop if the fresh Milestone 0 rebaseline shows a materially different
  selected-root set than the one scoped here; write a new packet instead of
  forcing stale scope.
- Stop if reducing one selected root would require reopening a previously
  resolved owner-family split rather than migrating callers or dispatch.
- Stop if the work starts to depend on broad schema, migration, or feature
  changes unrelated to centrality reduction.
- Stop if the packet needs to mix multiple unrelated root families without one
  shared gate or closeout signal.
- Stop if the worktree contains unrelated dirty implementation files that would
  have to be bundled into the same commit.

## Local Commit Closeout Policy

- Close each milestone in one atomic local commit after verification passes.
- Stage only the files that belong to the milestone slice; do not bundle
  unrelated dirty worktree changes.
- Documentation-only routing or packet-writing updates still require the active
  plan, handoff, and architecture index to land together in the same commit.
- A verified but uncommitted milestone is not complete.

## Residual Risks And Next Milestone Routing

- The packet may prove too broad for one uninterrupted execution run even after
  the Milestone 0 census. If that happens, split by centrality class, not by
  file size: caller-gravity lanes first, orchestration-gravity lanes second.
- `docs/db_models_caller_migration_boundary_milestone_plan.md` remains a valid
  detailed reference for the `app.db.models` lane, but it should not remain a
  parallel top-level optional packet once this broader plan is active.
- If `app/schemas/agent_tasks.py` or `app/cli.py` remain deliberate public
  aggregators after the migration, their accepted-legacy ceilings must be
  explicitly documented rather than implied.
