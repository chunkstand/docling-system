# Boring Change Architecture Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: drafted on 2026-05-13 as a stacked follow-on after
`docs/search_execution_orchestration_boundary_milestone_plan.md`,
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
`docs/evaluations_service_boundary_milestone_plan.md`,
`docs/evidence_provenance_exports_boundary_milestone_plan.md`,
`docs/semantics_service_boundary_milestone_plan.md`,
`docs/runtime_health_orchestration_milestone_plan.md`, and
`docs/ci_release_gate_parity_milestone_plan.md`; do not start implementation
until those prior packets close locally
Owner context: queued follow-on coordination packet for the remaining
expensive-change architecture gap across `SYSTEM_PLAN.md`,
`config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
`config/hotspot_prevention.yaml`, the remaining post-stack large-file owners in
`app/` and `tests/`, the current Python cycle components, and the checked-in
architecture/release workflows. This packet does not replace the already-open
owner cases for search, claim-support, evaluations, evidence, retrieval
learning, or data-model work. Milestone 0 must refresh live system state and
either bind this plan to the still-open owner cases plus any missing cycle/test
cases, or create the missing owner cases before code moves.

## Purpose

Resolve the current "not yet boring to change" gap identified in the system
review.

The scoped problem is not only that the repo still has some architecture debt.
The deeper issue is that the remaining change-cost burden is now split across
three different kinds of drift:

- source-of-truth docs still name several old hotspots that are already reduced
  to small compatibility facades
- the live architecture probe still reports 3 Python cycle components
- the live architecture probe still reports 52 code files above 800 lines,
  including both production code and test monoliths

This plan resolves that scoped gap end to end by refreshing stale routing,
re-baselining the post-stack offender list from live measurements, finishing
the remaining app and test large-file backlog one owner at a time, removing the
remaining Python cycles, and landing a durable boring-change gate so future
work cannot silently drift back into broad files and cycle-heavy seams.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 8]
   M app/hotspot_prevention_classifier.py
   M app/services/search.py
   M config/hotspot_prevention.yaml
   M config/hygiene_policy.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M tests/unit/test_hotspot_prevention.py
  ?? app/services/search_execution_orchestration.py
  ?? docs/ci_release_gate_parity_milestone_plan.md
  ?? docs/claim_support_policy_impacts_boundary_milestone_plan.md
  ?? docs/evaluations_service_boundary_milestone_plan.md
  ?? docs/evidence_provenance_exports_boundary_milestone_plan.md
  ?? docs/runtime_health_orchestration_milestone_plan.md
  ?? docs/search_execution_orchestration_boundary_milestone_plan.md
  ?? docs/semantics_service_boundary_milestone_plan.md
  ?? tests/unit/test_search_execution_orchestration.py

wc -l app/db/models.py app/services/evidence.py app/services/claim_support_policy_impacts.py app/services/retrieval_learning.py app/services/search.py app/services/semantics.py app/services/evaluations.py tests/db_model_contract.py tests/unit/test_agent_task_context.py tests/integration/test_retrieval_learning_ledger.py tests/unit/test_evaluation_service.py tests/integration/test_technical_report_harness_roundtrip.py tests/unit/test_search_service.py
     159 app/db/models.py
     141 app/services/evidence.py
    2011 app/services/claim_support_policy_impacts.py
     143 app/services/retrieval_learning.py
    1592 app/services/search.py
    2309 app/services/semantics.py
    2159 app/services/evaluations.py
    3700 tests/db_model_contract.py
    2972 tests/unit/test_agent_task_context.py
    2339 tests/integration/test_retrieval_learning_ledger.py
    2237 tests/unit/test_evaluation_service.py
    2030 tests/integration/test_technical_report_harness_roundtrip.py
    1845 tests/unit/test_search_service.py

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=531.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Code files: 576
  Python cycles: 3
  Suggested gate: --fail-on-cycles
  Suggested gate: --max-file-lines 800
  Large-file count above 800 lines: 52
  Largest files include:
    tests/db_model_contract.py = 3700
    tests/unit/test_agent_task_context.py = 2972
    app/services/semantics.py = 2309
    tests/unit/test_evaluation_service.py = 2237
    app/services/evaluations.py = 2159
    app/services/claim_support_policy_impacts.py = 2011
    tests/integration/test_technical_report_harness_roundtrip.py = 2030
    tests/unit/test_search_service.py = 1845
    app/services/search.py = 1592
  Python cycle components:
    app.architecture_decisions, app.architecture_inspection,
    app.architecture_inspection_rules, app.hygiene,
    app.services.improvement_case_intake
    app.services.chat, app.services.search,
    app.services.search_execution_persistence,
    app.services.search_hydration
    app.services.evidence_search_packages,
    app.services.evidence_search_trace_store

python large-file distribution (repo code only, >800 lines)
  app = 37
  tests = 15
```

Repo-current structural evidence:

- `SYSTEM_PLAN.md` still names `app/db/models.py`, `app/services/evidence.py`,
  and `app/services/retrieval_learning.py` as inherited hotspot debt, but the
  live line counts are now `159`, `141`, and `143`. Those files are no longer
  the main large-file blockers, although some remain fan-in-heavy compatibility
  surfaces and governed owner cases.
- The live large-file burden has shifted toward the still-open search,
  claim-support, evaluations, evidence-provenance, and semantics lanes, plus
  broader semantic/support services and several large test files.
- The current worktree already contains drafted stacked plans for:
  search orchestration, claim-support policy impacts, evaluations service
  boundary, evidence provenance exports, semantics service boundary, runtime
  health orchestration, and CI release-gate parity. This boring-change packet
  must therefore begin with a post-stack refresh rather than assuming those
  lanes stay static.
- `config/improvement_cases.yaml` already routes the main historical hotspot
  owners for:
  `app/db/models.py`,
  `app/services/search.py`,
  `app/services/claim_support_policy_impacts.py`,
  `app/services/evidence.py`,
  and `app/services/retrieval_learning.py`.
  The remaining live cycle components and many of the large test files do not
  yet have a single clearly discoverable coordination packet that closes them as
  one boring-change program.
- The current checked-in architecture workflow does not yet enforce the probe's
  suggested `--fail-on-cycles` and `--max-file-lines 800` gates, so the repo can
  still drift back toward broad files and cycles even when architecture
  inspection remains green.

## Goal

Resolve the scoped boring-change gap so that:

- source-of-truth docs and routing artifacts reflect the live residual debt
  rather than historical hotspot names
- every post-stack code file in `app/` and `tests/` is at or below 800 lines
- the architecture probe reports 0 Python cycle components
- already-reduced compatibility facades such as `app/db/models.py`,
  `app/services/evidence.py`, and `app/services/retrieval_learning.py` stay
  small and do not re-accumulate implementation ownership
- the zero-cycle / max-800-lines boring-change gate is executable in checked-in
  CI and in local closeout

The finish line for this plan is not "fewer big files than before." The finish
line is that the repo becomes mechanically boring on these axes:
no code file over 800 lines, no Python import cycle components, and no stale
source-of-truth routing that points future work at already-closed debt.

## Non-Goals

- No microservice extraction or platform rewrite.
- No attempt to solve all architecture hotspots by score alone; fan-in-heavy
  small compatibility facades may remain hot by measurement while still being
  acceptable if they stay small and behavior-stable.
- No threshold increase above 800 lines.
- No test weakening, skip broadening, xfail broadening, or fixture deletion as
  a shortcut to reduce file size.
- No hiding cycle debt behind ad hoc local imports, dynamic imports, or runtime
  side effects.
- No broad product-feature work outside the owner surfaces chosen from the live
  post-stack offender list.
- No parallel rewrite of the already-drafted stacked plans this packet depends
  on.

## Scope

In scope:

- Milestone 0 post-stack refresh and stale-source correction
- live re-baselining of every `app/` and `tests/` file above 800 lines after the
  currently stacked packets close
- explicit routing for every remaining large-file and cycle owner case
- one-owner-at-a-time reduction of the remaining app backlog above 800 lines
- one-owner-at-a-time reduction of the remaining test backlog above 800 lines
- removal of all remaining Python cycle components
- addition of a checked-in boring-change gate based on the architecture probe's
  `--fail-on-cycles` and `--max-file-lines 800` checks
- `SYSTEM_PLAN.md`, architecture index, handoff, workflow, and plan closeout
  updates in the same final milestone sequence

Out of scope:

- remote deployment work beyond consuming the runtime-health and CI parity
  contracts from the stacked plans
- changes to canonical JSON/YAML source-of-truth rules
- redesign of public API path contracts unless a live owner split requires
  focused compatibility coverage
- generic "clean up everything" sweeps with no owner-case routing

## Owner Surfaces

- stale source-of-truth and routing:
  `SYSTEM_PLAN.md`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan
- architecture governance and durable ratchets:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`,
  `config/architecture_inspection.yaml`,
  `.github/workflows/architecture-governance.yml`,
  `.github/workflows/release-gate-parity.yml`
- already-reduced facades that must stay small:
  `app/db/models.py`,
  `app/services/evidence.py`,
  `app/services/retrieval_learning.py`
- current queued owner lanes that this plan depends on:
  `app/services/search.py`,
  `app/services/claim_support_policy_impacts.py`,
  `app/services/evaluations.py`,
  `app/services/evidence_provenance_exports.py`,
  `app/services/semantics.py`
- remaining cycle-owner families selected from live Milestone 0 evidence:
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`,
  `app.services.improvement_case_intake`,
  `app.services.chat`,
  `app.services.search_execution_persistence`,
  `app.services.search_hydration`,
  `app.services.evidence_search_packages`,
  `app.services.evidence_search_trace_store`
- remaining large app owners selected from live Milestone 0 evidence, starting
  from the current top surfaces:
  `app/cli.py`,
  `app/services/semantics.py`,
  `app/services/semantic_graph.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_orchestration.py`,
  `app/services/claim_support_replay_alert_promotions.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/technical_reports.py`,
  `app/services/quality.py`,
  `app/services/documents.py`,
  `app/services/docling_parser.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`,
  and any other post-stack live offenders still above 800
- remaining large test owners selected from live Milestone 0 evidence, starting
  from the current top surfaces:
  `tests/db_model_contract.py`,
  `tests/unit/test_agent_task_context.py`,
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_search_service.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/integration/test_retrieval_learning_ledger.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/unit/test_docling_parser.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_agent_task_verifications.py`,
  and any other post-stack live offenders still above 800

## Placement Rules

- Keep public compatibility facades stable while shrinking implementation owners
  behind them.
- Do not solve one large-file problem by moving code into another file that is
  already over 800 lines.
- New test coverage belongs in focused owner files, not back inside the current
  broad test monoliths.
- Do not "break" cycles through local-import tricks that make the dependency
  graph harder to reason about. Break cycles by moving shared types, read
  helpers, or orchestration seams into clearer owner modules.
- When live Milestone 0 evidence changes the offender list, route the live
  offender list rather than forcing today's names into the implementation.
- If a file is already reduced below 800, keep it there by ratchet; do not
  reopen it as a general-purpose landing zone just because callers already
  import it.
- `SYSTEM_PLAN.md` and the architecture index must name only live residuals, not
  historical hotspot names that were already retired.

## Weak-Point Prevention Contract

Freshness check: Milestone 0 must rerun live routing, architecture, and
large-file commands after the currently stacked packets close. This plan is
invalid if the prior packets remain uncommitted or if they materially change
the post-stack offender list.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Stale source-of-truth docs keep pointing future work at already-closed hotspots | `SYSTEM_PLAN.md`, `docs/agentic_architecture_index.md`, `docs/SESSION_HANDOFF.md`, this plan | Milestone 0 refresh plus closeout doc readback | Docs still name `app/db/models.py`, `app/services/evidence.py`, or `app/services/retrieval_learning.py` as the primary large-file blockers after live evidence shows they are small facades | Leave the old hotspot sentence unchanged after refreshing live `wc -l` output and confirm the alignment review rejects the closeout | A later session plans new work around dead hotspot names and misses the real remaining files |
| Large-file count falls only by shifting code into another broad file | live post-stack `app/` and `tests/` owners, hygiene policy, hotspot prevention | architecture probe `--max-file-lines 800`, hygiene, and focused owner tests | One file drops below 800 while another already-large file grows or a new >800 offender appears without routing | Move logic from one broad module into another already-large sibling and confirm the max-file-lines gate still fails | A future split "solves" one monolith by hiding the same responsibility in another monolith |
| Cycles disappear only because imports were hidden, not because ownership improved | cycle-owner modules and focused import tests | architecture probe `--fail-on-cycles` plus architecture inspection | Static cycle count hits zero only through opaque local-import patterns or undocumented runtime dependency tricks | Replace a top-level import with a local function import and confirm review rejects the fake cycle fix | A later session optimizes for the green gate instead of clearer ownership |
| Broad test files shrink by deleting assertions or narrowing coverage | focused test owners, integration suites, release gate parity runner | targeted unit/integration suites plus full `DOCLING_SYSTEM_RUN_INTEGRATION=1` closeout | A split reduces file size but coverage meaningfully narrows, or a deleted assertion is not replaced by equivalent or broader focused tests | Remove a broad test block without moving its assertions into focused files and confirm targeted/full suites fail or closeout review blocks the change | A future session treats file-size reduction as more important than preserving behavior coverage |
| Already-reduced compatibility facades regrow because they are convenient import hubs | `app/db/models.py`, `app/services/evidence.py`, `app/services/retrieval_learning.py`, hotspot prevention | `uv run docling-system-hotspot-prevention-check --strict` plus focused facade tests | New implementation ownership lands back in a small compatibility facade | Add a new helper or implementation branch back into one reduced facade and confirm hotspot prevention flags it | A future session uses the stable facade as the default place for "one more helper" |
| The boring-change gate is never made durable in checked-in CI | `.github/workflows/architecture-governance.yml`, `.github/workflows/release-gate-parity.yml`, architecture probe command docs | workflow readback plus local runner invocation | Local closeout can prove zero cycles / zero >800, but checked-in CI still never runs those gates | Leave the probe gate local-only and confirm the workflow diff is incomplete | A future session reintroduces a cycle or monolith because only humans remember to run the final gate |

## Milestone Sequence

### Milestone 0 - Refresh the stacked packet and correct the stale baseline

Outcome label: `reduced`

Purpose: refresh this plan to current system state after the currently stacked
search, claim-support, evaluations, evidence-provenance, semantics,
runtime-health, and CI-parity packets close locally, and correct the stale
source-of-truth hotspot baseline before code changes begin.

Implementation:

- Re-run:
  `git status -sb`,
  `sed -n '96,132p' SYSTEM_PLAN.md`,
  `sed -n '1,220p' docs/SESSION_HANDOFF.md`,
  `sed -n '1,220p' docs/agentic_architecture_index.md`,
  `uv run docling-system-architecture-quality-report --summary`,
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 30`,
  targeted `wc -l` commands for the live residual surfaces, and a repo-local
  count of all `app/` and `tests/` files above 800 lines.
- Confirm the prior stacked packets are committed and update this plan's
  dependency list if the queue changed.
- Replace this plan's draft-time offender list with the live post-stack list.
- Explicitly record which surfaces from the stale `SYSTEM_PLAN.md` paragraph are
  no longer large-file blockers.
- Bind every remaining >800 file and every remaining cycle component to an
  existing owner case or create the missing owner cases for the live residuals.

Acceptance:

- This plan reflects live post-stack repo state rather than the review's older
  hotspot paragraph.
- Every remaining >800 file and every remaining cycle component has explicit
  owner routing.
- The plan says which earlier hotspot names were stale and what replaced them as
  the real remaining offenders.

Stop conditions:

- Any prior stacked packet remains uncommitted.
- The post-stack offender list differs so much that this draft's routing no
  longer matches live repo state.
- Missing owner cases cannot be created or reconciled cleanly from the
  refreshed evidence.

### Milestone 1 - Encode the boring-change finish line in docs and routing

Outcome label: `reduced`

Purpose: turn "boring to change" from review prose into a repo-owned contract
before the remaining refactors start.

Implementation:

- Update `SYSTEM_PLAN.md` so the architecture-residual paragraph reflects the
  live state from Milestone 0 instead of the older hotspot list.
- Update `docs/agentic_architecture_index.md` and `docs/SESSION_HANDOFF.md` so
  the next work is routed against the refreshed offender list.
- Add or refresh improvement-case and hygiene routing for every newly selected
  app, test, and cycle owner.
- Record the final boring-change closeout command explicitly in this plan:
  architecture probe with `--fail-on-cycles --max-file-lines 800`, plus the
  repo's release/verification gate.

Acceptance:

- The source-of-truth docs no longer point at already-reduced large-file
  surfaces as if they were still the main blockers.
- Every live offender is discoverable through the routing docs and the owner
  registry.
- The final boring-change gate is explicit, not implied.

Stop conditions:

- The docs cannot be aligned because the post-stack queue is still changing.
- Any new routing would weaken existing owner-case or hygiene guarantees.

### Milestone 2 - Finish the post-stack app-code backlog one owner at a time

Outcome label: `reduced`

Purpose: reduce every remaining `app/` code file above 800 lines to a focused
owner surface at or below the boring-change threshold.

Implementation:

- Starting from the Milestone 0 rebaseline, select the current largest `app/`
  offender still above 800 lines and split it behind stable compatibility seams.
- Land one owner split per atomic commit. After each owner closes, update this
  plan, the owner case, the hygiene ratchet, and the handoff before starting the
  next offender.
- Begin with the live top post-stack app offenders unless the refresh changes
  the order:
  `app/cli.py`,
  `app/services/semantics.py`,
  `app/services/semantic_graph.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_orchestration.py`,
  `app/services/claim_support_replay_alert_promotions.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/technical_reports.py`,
  `app/services/quality.py`,
  `app/services/documents.py`,
  `app/services/docling_parser.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`,
  and any other live post-stack offenders.
- Keep `app/db/models.py`, `app/services/evidence.py`, and
  `app/services/retrieval_learning.py` small by ratchet instead of reopening
  them as implementation owners.

Acceptance:

- No `app/` code file remains above 800 lines.
- Each moved concern has focused owner tests and preserved facade compatibility.
- No already-reduced compatibility facade regrows during the backlog sweep.

Stop conditions:

- A split would force substantial new responsibility into another already-large
  app file.
- An owner cannot be reduced without first changing public contracts beyond the
  scoped compatibility envelope.

### Milestone 3 - Finish the post-stack test backlog one owner at a time

Outcome label: `reduced`

Purpose: reduce every remaining `tests/` code file above 800 lines without
throwing away behavior coverage.

Implementation:

- Starting from the Milestone 0 rebaseline, select the current largest test
  offender still above 800 lines and split it by owner concern, behavior slice,
  or route family.
- Land one test-owner split per atomic commit. Replace or broaden every moved
  assertion in focused files before deleting it from the broad file.
- Begin with the live top post-stack test offenders unless the refresh changes
  the order:
  `tests/db_model_contract.py`,
  `tests/unit/test_agent_task_context.py`,
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_search_service.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/integration/test_retrieval_learning_ledger.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/unit/test_docling_parser.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_agent_task_verifications.py`,
  and any other live post-stack offenders.
- Do not move the burden into giant `conftest.py` helpers or new omnibus
  fixture modules.

Acceptance:

- No `tests/` code file remains above 800 lines.
- Coverage is preserved or broadened through focused owner tests.
- The broad-file count goes down without creating new broad fixture or helper
  monoliths.

Stop conditions:

- The only way to reduce a test file would weaken real assertion coverage.
- Shared helpers start becoming the next ungoverned broad-file problem.

### Milestone 4 - Break every remaining Python cycle component

Outcome label: `reduced`

Purpose: remove the last static import-cycle components so module ownership is
locally understandable and safer to refactor.

Implementation:

- Break the architecture-control cycle involving:
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`,
  `app.services.improvement_case_intake`.
- Break the search-family cycle involving:
  `app.services.chat`,
  `app.services.search`,
  `app.services.search_execution_persistence`,
  `app.services.search_hydration`.
- Break the evidence-search cycle involving:
  `app.services.evidence_search_packages` and
  `app.services.evidence_search_trace_store`.
- Use extracted shared value modules, narrower read/write helpers, or
  orchestration seams. Do not use local-import masking as the primary solution.
- Add focused import and behavior coverage for every cycle break.

Acceptance:

- The architecture probe reports 0 Python cycle components.
- Cycle breaks improve ownership clarity instead of just hiding imports.
- No new cycle component appears while closing the listed ones.

Stop conditions:

- A proposed break only hides imports and does not clarify ownership.
- A cycle can be broken only by broad public-contract redesign outside the
  scoped owner surfaces.

### Milestone 5 - Make the boring-change gate durable in checked-in CI

Outcome label: `reduced`

Purpose: ensure the repo cannot silently drift back above the large-file or
cycle thresholds after the backlog is closed.

Implementation:

- After the stacked CI parity packet lands, add the boring-change probe gate to
  the checked-in workflow set using the same local command recorded in this
  plan.
- Require the architecture probe to run with:
  `--fail-on-cycles --max-file-lines 800`.
- Keep the existing architecture inspection, capability, hygiene, hotspot
  prevention, and release-parity signals in place; this gate is additive.
- Update workflow docs and closeout notes so future sessions know where the
  boring-change gate runs and what it proves.

Acceptance:

- Reintroducing a >800 file or a Python cycle fails checked-in CI.
- The local boring-change gate and the checked-in CI gate use the same command
  contract.
- The gate does not depend on human memory or review prose alone.

Stop conditions:

- The CI parity dependency is not yet landed and no equivalent checked-in
  runner exists.
- The gate can only be made green by excluding files or raising thresholds.

### Milestone 6 - Prove the repo is boring on the selected axes and close out

Outcome label: `resolved` for the scoped boring-change architecture issue

Purpose: prove the repo has reached the selected boringness finish line and
close the program with the required docs, handoff, and local atomic commit
discipline.

Implementation:

- Run the full required verification stack, including the final boring-change
  probe gate and the repo's release gate.
- Update `SYSTEM_PLAN.md`, `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`, and this plan with the final counts, closeout
  commit hashes, residual risks, and any remaining follow-up that is outside
  this scoped gap.
- Close or reduce the owner cases with refreshed live evidence only. If a case
  remains hot by fan-in while the facade is already small and stable, record
  that explicitly instead of pretending the system is still broad on file-size
  grounds.

Acceptance:

- The architecture probe reports 0 Python cycle components.
- The architecture probe reports 0 code files above 800 lines.
- Source-of-truth docs no longer list already-reduced facades as the main live
  blockers.
- The boring-change gate is checked in and part of durable closeout.
- Full verification passes without weakening tests or narrowing coverage.
- The milestone closes through atomic commits that update code, tests, docs,
  routing, and handoff together.

Stop conditions:

- The final probe still reports any code file above 800 lines or any Python
  cycle component.
- Docs, routing, and live measurements disagree on what remains open.

## Required Implementation Artifacts

- updated `SYSTEM_PLAN.md`
- updated `config/improvement_cases.yaml`
- updated `config/hygiene_policy.yaml`
- updated `config/hotspot_prevention.yaml` if new ratchets or follow-up rules
  are required
- updated `config/architecture_inspection.yaml` if the final gate needs a
  durable repo-owned home there
- reduced live post-stack owner modules in `app/`
- reduced live post-stack test files in `tests/`
- any new focused owner modules and focused owner tests created by the splits
- updated `.github/workflows/architecture-governance.yml`
- updated `.github/workflows/release-gate-parity.yml`
- updated `docs/agentic_architecture_index.md`
- updated `docs/SESSION_HANDOFF.md`
- this plan

## Required Documentation And Handoff Updates

- `SYSTEM_PLAN.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- this plan
- `config/improvement_cases.yaml` when owner routing or status changes

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app tests`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --max-file-lines 800 --top 20`
- `uv run docling-system-release-gate-parity`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run --extra dev python -m pytest -q -rs`

If the CI parity runner is not yet available when Milestone 0 refresh occurs,
record the exact fallback release-gate command stack in
`docs/SESSION_HANDOFF.md` and update this plan before any implementation starts.

## Acceptance Criteria

- The plan begins with Milestone 0 freshness because the selected review text is
  already partially stale against the live checkout.
- The stale `SYSTEM_PLAN.md` hotspot paragraph is corrected to live state.
- Every post-stack code file above 800 lines is reduced below the threshold.
- Every remaining Python cycle component is removed.
- Small compatibility facades stay small and do not reacquire implementation
  ownership.
- The boring-change gate is checked in and runs both locally and in CI.
- No tests, skips, xfails, or verification gates are weakened to achieve the
  outcome; replacement coverage must be equivalent or broader.
- The milestone closes only after docs, handoff, and the final atomic closeout
  commits all exist.

## Stop Conditions

- The prior stacked plans are not yet closed and committed.
- Live Milestone 0 evidence shows materially different remaining offenders and
  this draft is not refreshed before implementation.
- Any implementation slice would require broad contract redesign outside the
  selected owner surfaces.
- The final boring-change gate cannot be made durable in checked-in CI.
- Unrelated worktree changes cannot be separated from the boring-change slices.

## Local Commit Closeout Policy

- Stage only the verified boring-change slice for the current owner or cycle
  milestone.
- For Milestones 2 and 3, land one owner split per atomic commit and update
  this plan, routing docs, and handoff before starting the next offender.
- Do not close the overall plan until the final probe reports zero Python
  cycles and zero code files above 800 lines.
