# Residual Large-File Backlog Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally in the current checkout through the final
zero-oversized closeout. The live architecture probe now reports zero code
files above `800`, and the former governance under-budget follow-on is now
also resolved locally, so the next code-owning packet must be reselected from
the broader coordination brief instead of from the cleared large-file queue.
Owner context: coordination brief for the remaining code files above the live
architecture-probe `800`-line threshold after the recent facade, cycle, and
selected owner-family closeouts.

## Purpose

Resolve the remaining broad large-file debt without collapsing back into one
vague cleanup milestone or reopening already-closed facade work.

The current weakness is not a single monolith anymore. The live `>800` backlog
is now split across:

- already-resolved predecessor packets whose closeouts changed the queue
- semantic, technical-report, service, and test roots that are still expensive
  to change
- several files that have line-budget ratchets but no honest dedicated residual
  owner packet
- several files that have no durable owner-case routing at all

This plan resolves that debt by turning the remaining `>800` backlog into an
ordered packet queue with explicit owner surfaces, packet creation rules, final
zero-oversized closure, and a durable gate that future sessions cannot ignore.

## 2026-05-18 Milestone 0 Update

Milestone 0 is now resolved locally in the current checkout.

- The live `>800` backlog has been refreshed from the current architecture
  probe baseline at `17` code files, not the earlier `20`-file draft snapshot.
- The predecessor packets are no longer merely queued assumptions:
  `docs/db_models_residual_owner_family_milestone_plan.md` and
  `docs/hotspot_routing_trap_resolution_milestone_plan.md` are both resolved
  locally and the active queue now starts with dedicated child packets rather
  than those prerequisite packets.
- Dedicated child packets now exist for the evaluation, UI,
  semantic-and-technical-report, and cross-cutting residual families:
  `docs/evaluation_residual_owner_family_milestone_plan.md`,
  `docs/ui_module_residual_owner_family_milestone_plan.md`,
  `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`,
  and `docs/cross_cutting_large_file_residual_milestone_plan.md`.
- `config/improvement_cases.yaml` now carries dedicated residual owner routing
  for the evaluation, UI, semantic/report, and cross-cutting families under
  `IC-4B6E9F8D2A10`,
  `IC-81F2C6D4B9A7`,
  `IC-2D5A7E9C4B18`, and
  `IC-6C3E1A7B9D52`, while the governance pair
  `app/services/improvement_cases.py` /
  `tests/unit/test_improvement_case_intake.py` remains explicitly routed under
  `IC-08C078FD4F45`.
- `config/hygiene_policy.yaml` now binds every live `>800` file to an explicit
  owner case and later exact-ratchets the governance self-hosting family at
  `370`, `514`, `552`, `82`, `218`, `122`, `184`, `475`, `279`, `277`,
  `101`, `122`, and `551` under `IC-08C078FD4F45`.

## 2026-05-18 Evaluation Packet Update

The first routed child packet,
`docs/evaluation_residual_owner_family_milestone_plan.md`, is now also
resolved locally in the current checkout.

- The live `>800` backlog is now down to `13` code files after the evaluation
  next pass reduced
  `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_scoring.py`,
  `app/services/eval_workbench.py`, and
  `tests/unit/test_evaluation_fixtures.py` below the probe threshold.
- The later gap-close pass retires the remaining same-family residuals in
  place. The evaluation family now has no governed file above the default
  `600`-line budget, and `IC-4B6E9F8D2A10` remains open only as an uncommitted
  retirement-ready route.
- At that point in the sequence, the queue advanced to
  `docs/ui_module_residual_owner_family_milestone_plan.md`, then the
  semantic/report, cross-cutting, and shared-verification follow-ons.

## 2026-05-18 UI Packet Update

The second routed child packet,
`docs/ui_module_residual_owner_family_milestone_plan.md`, is now also resolved
locally in the current checkout.

- The live `>800` backlog is now down to `11` code files after the UI closeout
  reduced `app/ui/modules/shared.js` to `517` lines and
  `app/ui/modules/agents.js` to `599` while moving family-local ownership into
  `app/ui/modules/shared_runtime.js`,
  `app/ui/modules/shared_search_rendering.js`,
  `app/ui/modules/agents_collections.js`,
  `app/ui/modules/agents_claim_support_replay.js`, and
  `app/ui/modules/agents_report_harness.js`.
- The split did not shift debt into another sink: every newly introduced UI
  module is exact-ratcheted under `IC-81F2C6D4B9A7`, and no governed UI file is
  above the default `600`-line budget.
- The live queue now advances to
  `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`,
  then the cross-cutting and shared-verification follow-ons.

## 2026-05-18 Cross-Cutting Closeout Update

The final large-file child packet,
`docs/cross_cutting_large_file_residual_milestone_plan.md`, is now also
resolved locally in the current checkout.

- The live architecture probe now reports `0` code files above `800` with
  `0` Python cycle components.
- `app/services/documents.py` closes at `49` lines with
  `app/services/document_ingest.py` at `233`,
  `app/services/document_run_queue.py` at `324`, and
  `app/services/document_run_views.py` at `276`, while the selected
  verification roots now measure `324`, `331`, `540`, `269`, and `439` lines
  across
  `tests/unit/test_agent_task_verifications.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/unit/test_docling_parser.py`,
  `tests/integration/test_search_harness_releases.py`, and
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`.
- The governance self-hosting family remains explicitly routed under
  `IC-08C078FD4F45`, with its local cycle removed and its remaining
  under-budget roots reduced in a later bounded packet rather than kept as a
  large-file blocker.
- The next active work is no longer “remove files above 800.” It is queue
  execution of the next under-budget packet selected from the broader
  coordination brief, with the documents-service sink, the cross-cutting
  verification packet, the queue-alignment packet, and the governance
  self-hosting packet all already resolved locally.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-18
local / 2026-05-18 UTC after the cross-cutting large-file, queue-alignment,
and governance self-hosting closeouts:

```text
git status -sb
  ## main...origin/main
   M .github/workflows/architecture-governance.yml
   M config/hotspot_prevention.yaml
   M config/hygiene_policy.yaml
   M config/improvement_cases.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M docs/boring_change_architecture_milestone_plan.md
   ?? docs/db_models_residual_owner_family_milestone_plan.md
   ?? docs/hotspot_routing_trap_resolution_milestone_plan.md
  plus active uncommitted implementation work across service and test owners

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycles: none detected
  0 code files exceed 800 lines
  nearest routed residual:
    tests/integration/test_technical_report_harness_audit_surfaces.py = 799

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=486.06
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

uv run docling-system-improvement-case-summary
  case_count=59
  status_counts.open=41
  status_counts.verified=2
  status_counts.deployed=15
  measured_case_count=55

uv run docling-system-hygiene-check
  new hygiene regressions: none
```

Repo-current structural evidence:

- `docs/SESSION_HANDOFF.md` now records the governance self-hosting packet as
  the latest resolved bounded brief and leaves the next active code-owning
  packet to be reselected from
  `docs/boring_change_architecture_milestone_plan.md`, while the
  closeout-state coordination packet, the documents-service sink, the
  cross-cutting verification packet, and the governance self-hosting packet are
  all now resolved locally.
- `docs/agentic_architecture_index.md` now records this parent packet as
  resolved locally with the live `>800` backlog cleared, the queue-alignment
  packet closed, the documents-service sink retired, the verification packet
  resolved, and the governance self-hosting packet resolved, so the remaining
  under-budget code-owning follow-on now has to be reselected from
  `docs/boring_change_architecture_milestone_plan.md`.
- `docs/boring_change_architecture_milestone_plan.md` remains the umbrella
  coordination brief and now explicitly routes from this parent packet to the
  next reselected under-budget child packet rather than back through
  predecessor packets.
- `config/improvement_cases.yaml` now assigns dedicated residual owner cases to
  the evaluation, UI, semantic/report, and cross-cutting families, while the
  governance self-hosting family remains on `IC-08C078FD4F45`.
- `config/hygiene_policy.yaml` now binds every live `>800` root to an explicit
  owner case and ratchet. The governance self-hosting family is now
  exact-ratcheted at `370`, `514`, `552`, `82`, `218`, `122`, `184`, `475`,
  `279`, `277`, `101`, `122`, and `551` under `IC-08C078FD4F45`.
- The raw architecture-quality hotspot list still contains closed or narrow
  facades, but the routed queue now starts from the child packets created by
  this milestone instead of those measurement-only paths.

### Live Backlog Classification

| Backlog family | Current `>800` members | Current routing state |
| --- | --- | --- |
| Evaluation residual | none above `800`; no governed evaluation root remains above `600` after the 2026-05-18 gap-close pass | Child packet `docs/evaluation_residual_owner_family_milestone_plan.md` is now resolved locally and locally retirement-ready under `IC-4B6E9F8D2A10`. |
| UI module residual | none above `800`; no governed UI root remains above `600` after the 2026-05-18 closeout | Child packet `docs/ui_module_residual_owner_family_milestone_plan.md` is now resolved locally and locally retirement-ready under `IC-81F2C6D4B9A7`. |
| Semantic and report residual | none above `800`; the governed semantic/report family now closes at `543`, `570`, `574`, `485`, `33`, `554`, `159`, and `258` lines across the routed service siblings, and the downstream report-context plus harness-integrity slice stayed green | Child packet `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md` is now resolved locally and locally retirement-ready under `IC-2D5A7E9C4B18`. |
| Cross-cutting service and test residual | none above `800`; the document family now closes at `49`, `233`, `324`, and `276` lines while the selected verification roots close at `324`, `331`, `540`, `269`, and `439`, and the later governance family closes at `370`, `514`, `552`, `82`, and `218` with exact-ratcheted siblings at `122`, `184`, `475`, `279`, `277`, `101`, `122`, and `551` | The large-file parent packet, the queue-alignment packet, the documents-service packet, the cross-cutting verification packet, and the governance self-hosting packet are now all resolved locally. The next code-owning bounded follow-on must be reselected from `docs/boring_change_architecture_milestone_plan.md`. |

## Goal

Resolve the residual large-file backlog so that:

- a fresh architecture probe reports `0` code files above `800` lines
- every touched or newly created owner file between `601` and `800` lines is
  routed in `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
  during the same milestone that creates or leaves it
- already-closed compatibility facades stay narrow and do not re-accumulate
  moved implementation
- the routed packet queue is owner-aware rather than raw-hotspot-driven
- the final large-file closeout includes a checked-in probe gate that future
  sessions can run with `--max-file-lines 800` and `--fail-on-cycles`

The finish line for this plan is not "the backlog feels better routed." The
finish line is a repo where the live architecture probe no longer reports any
code file above `800` lines, the remaining `601-800` residuals are explicitly
routed, and the docs plus gate stack agree on that state.

## Non-Goals

- No threshold increase above the current `800`-line architecture-probe gate.
- No reopening of already-reduced facade packets just because they still appear
  in raw hotspot summaries.
- No using `app/services/semantic_orchestration.py`,
  `app/services/technical_reports.py`, `app/services/documents.py`,
  `app/ui/modules/shared.js`, or broad smoke/integration tests as sink files
  for moved implementation.
- No broad product-feature work, runtime rewrite, UI redesign, or microservice
  extraction outside the owner files selected by the live queue.
- No weakening of tests, fixture coverage, integration coverage, hygiene gates,
  or hotspot-prevention checks to force a green closeout.
- No treating this coordination brief as permission to mix every remaining
  family into one giant implementation commit.

## Scope

In scope:

- live Milestone 0 rebaseline of the current `20`-file `>800` backlog
- durable queue ordering across the active DB-model packet, queued hotspot
  routing packet, and the follow-on large-file owner packets created here
- the current `>800` files listed in the architecture probe excerpt above
- targeted owner-case bootstrap and hygiene-owner binding for large files that
  do not yet have honest residual routing
- new child packets created from this plan for evaluation, UI, semantic/report,
  and cross-cutting service or test owner families
- final zero-oversized closeout with doc alignment and checked-in gate usage
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `config/hotspot_prevention.yaml`
- `.github/workflows/architecture-governance.yml` if the final gate invocation
  or wrapper needs to change

Out of scope:

- pushing every inherited `601-800` file under the default `600` hygiene
  budget during this sequence unless the selected child packet explicitly owns
  that further reduction
- reopening already-closed owner families such as the search facade packet,
  evidence facade packet, CLI dispatch packet, agent-task schema packet, or the
  just-closed agent-task residual packet unless a fresh rebaseline proves real
  regrowth in those exact files
- nonselected JS or CSS work outside the routed `app/ui/modules/*.js` owners
- unrelated cleanup in the currently dirty worktree

## Owner Surfaces

- queue and routing docs:
  `docs/residual_large_file_backlog_milestone_plan.md`,
  `docs/db_models_residual_owner_family_milestone_plan.md`,
  `docs/hotspot_routing_trap_resolution_milestone_plan.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`
- evaluation family:
  `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_scoring.py`,
  `app/services/eval_workbench.py`,
  `tests/unit/test_evaluation_fixtures.py`,
  direct evaluation siblings created by the child packet,
  and the evaluation integration surfaces that prove them
- UI module family:
  `app/ui/modules/agents.js`,
  `app/ui/modules/shared.js`,
  `app/ui/app.js`,
  `tests/unit/test_ui.py`,
  `tests/unit/test_ui_static_assets.py`
- semantic and report family:
  `app/services/semantic_orchestration.py`,
  `app/services/technical_reports.py`,
  `app/services/audit_bundle_training_runs.py`,
  direct semantic, technical-report, and audit-boundary tests or integration
  harnesses required by the child packet
- cross-cutting service and test family:
  `tests/unit/test_agent_task_verifications.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/unit/test_docling_parser.py`,
  `tests/integration/test_search_harness_releases.py`,
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`,
  `app/services/documents.py`,
  `app/services/improvement_cases.py`,
  `tests/unit/test_improvement_case_intake.py`,
  with adjacent inherited routing on
  `app/services/improvement_case_intake.py` at `552` lines under
  `IC-08C078FD4F45`,
  and any direct family-local support modules created to narrow those roots
- routing and gates:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`,
  `.github/workflows/architecture-governance.yml`,
  `tests/unit/test_hotspot_prevention.py`

## Placement Rules

- Keep already-small compatibility facades and entrypoints narrow:
  `app/db/models.py`, `app/services/evaluations.py`, `app/ui/app.js`,
  `app/services/agent_task_actions.py`, `app/services/evidence.py`,
  `app/cli.py`, and `app/schemas/agent_tasks.py` must not be reused as dump
  targets for moved logic.
- Evaluation-family decomposition belongs in focused evaluation siblings, not in
  `documents.py`, `runs.py`, `semantic_backfill.py`, or unrelated capability
  wrappers.
- UI module decomposition belongs in focused `app/ui/modules/*.js` siblings or
  helper modules, not back in `app/ui/app.js`, not in one regrown
  `shared.js` sink, and not in embedded inline page factories.
- Semantic and report decomposition belongs in family-local service siblings.
  Do not move implementation into already-large adjacent files such as
  `documents.py`, `semantic_registry.py`, `eval_workbench.py`, or unrelated
  agent-task context owners just because they share vocabulary.
- Test decomposition must use family-local support modules or focused sibling
  test roots. Do not turn `tests/integration/test_postgres_roundtrip.py` or
  `tests/unit/test_evaluation_fixtures.py` into generic "everything else"
  smoke roots.
- Any new or touched owner file above `600` lines must receive same-milestone
  routing in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`. Any new or touched owner file above `800` lines
  fails the milestone.
- If Milestone 0 discovers that a queued child packet already exists under a
  different honest name, reuse that packet rather than creating a duplicate.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A packet shrinks one large file by bloating another nearby owner. | touched family files, staged diff, `config/hygiene_policy.yaml`, architecture probe | `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 25`, `uv run docling-system-hygiene-check`, staged `wc -l` review | Any touched sibling in the selected family grows past its recorded ceiling or a new `>800` file appears | Temporarily move evaluation work into `documents.py` or agent UI work into `shared.js` and confirm closeout rejects the slice | A future session follows the nearest filename instead of the owner map and recreates the same debt one file over |
| Raw hotspot routing reopens already-closed facades instead of the current large-file owners. | `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `docs/hotspot_routing_trap_resolution_milestone_plan.md`, queue docs | `uv run docling-system-architecture-quality-report --summary`, queue-doc review, Milestone 0 freshness check | The selected next packet after rebaseline targets `app/db/models.py`, `app/services/evidence.py`, `app/services/agent_task_actions.py`, `app/cli.py`, or `app/schemas/agent_tasks.py` without new regrowth evidence | Force a draft to reopen `app/db/models.py` after Milestone 0 and confirm queue review blocks it | A future session trusts the summary top five without noticing those are now compatibility facades |
| UI debt remains invisible because Python-centric routing ignores JavaScript module monoliths. | `app/ui/modules/agents.js`, `app/ui/modules/shared.js`, this plan, `config/improvement_cases.yaml` | fresh architecture probe review, plan queue review, UI child-packet creation | Either JS file remains above `800` without a dedicated child packet and owner-case routing after Milestone 0 | Omit the UI files from the queue table and confirm Milestone 0 closeout fails | A future session sees no Python hygiene entry and assumes the shipped UI is outside architecture-governance scope |
| Test roots are made smaller by deleting assertions, weakening fixtures, or narrowing integration coverage. | touched test files, supporting fixtures, child-packet verification lists | focused unit and integration suites, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`, diff review | Any packet reduces test size by removing scenario coverage without stronger focused replacement coverage | Replace a large scenario block with a shallow smoke assertion and confirm focused verification or review fails the packet | Future Codex optimizes for line count instead of contract coverage |
| Routed residual owners stay above `800` because their child packet is never created or the case registry is left stale. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, queue docs, child-packet files | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, docs review | A live `>800` file closes Milestone 0 or a child milestone without a named packet and explicit owner-case entry | Leave `technical_reports.py` above `800` with only a stale hygiene line and confirm closeout rejects the slice | A future session treats file-budget debt as informational instead of a routed implementation queue |
| Docs drift and later sessions act on stale counts or stale packet order. | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `docs/boring_change_architecture_milestone_plan.md` | Milestone-closeout doc review plus fresh architecture probe rerun | The plan, handoff, and index disagree on the current `>800` count, active packet, or next queued packet | Change the queue in one doc but not the others and confirm closeout review rejects the milestone | A future session starts from a stale brief and duplicates already-queued work |

Accepted residuals during the sequence:

- Files between `601` and `800` lines are accepted only when the same
  milestone records exact owner-case routing, hygiene budgets, and the next
  packet if further reduction is still needed.
- No file above `800` lines is accepted at final closeout.

## Milestone Sequence

### Milestone 0. Live Queue Lock And Owner Bootstrap
Outcome label: reduced

Refresh the live `>800` backlog, classify every current offender into an
existing packet or a new child packet, and bootstrap missing owner-case routing
before broader code motion.

Implementation notes:

- Rerun the architecture probe from a fresh baseline and update this plan if
  the live `>800` list changed.
- Verify that the already-resolved DB-model residual and hotspot-routing
  predecessor packets still match the live queue state recorded in the handoff
  and index.
- Create missing owner-case and hygiene-owner routing for any current `>800`
  file that does not already have honest residual routing.
- Record the exact child packets that will own the remaining families after the
  predecessor closeouts already recorded locally.

Milestone 0 is complete only when:

- every current `>800` file appears in this plan's queue table or a named child
  packet
- missing owner cases and hygiene bindings are added for every live `>800`
  file that lacks them
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and this
  plan agree on the active packet and queued order

### Milestone 1. Active DB-Model Residual Owner Closeout
Outcome label: reduced

This milestone is already satisfied locally by the resolved
`docs/db_models_residual_owner_family_milestone_plan.md` packet, which closed
the three extracted DB-model owner files while keeping `app/db/models.py`
frozen as the public compatibility facade.

Milestone 1 is complete only when:

- `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` no longer appear in the live
  `>800` list
- any new DB-model owner or harness sibling above `600` lines is routed in the
  same milestone
- the DB-model child packet updates the handoff, index, and this plan's queue
  counts

### Milestone 2. Hotspot-Routing Trap Closeout
Outcome label: reduced

This milestone is already satisfied locally by the resolved
`docs/hotspot_routing_trap_resolution_milestone_plan.md` packet, which made
the routed queue owner-aware before the next large-file family was selected.

Milestone 2 is complete only when:

- raw architecture-quality output remains intact
- routed next-work selection no longer treats already-reduced facades as the
  default next packet
- this plan's queue order is refreshed from the post-governance baseline

### Milestone 3. Evaluation Residual Owner Family Packet
Outcome label: reduced

Create or execute a dedicated child packet for:

- `app/services/evaluation_fixtures.py`
- `app/services/evaluation_scoring.py`
- `app/services/eval_workbench.py`
- `tests/unit/test_evaluation_fixtures.py`

The child packet should keep the deployed `app/services/evaluations.py` facade
small while moving fixture, scoring, workbench, and fixture-test ownership into
focused siblings.

Milestone 3 is complete only when:

- all four listed surfaces fall below `800` lines
- the evaluation family keeps or strengthens unit and DB-backed integration
  coverage
- any new `601-800` evaluation owner or test root is routed in the same
  milestone

### Milestone 4. UI Module Residual Packet
Outcome label: reduced

Create or execute a dedicated child packet for:

- `app/ui/modules/agents.js`
- `app/ui/modules/shared.js`

The packet must keep `app/ui/app.js` as the narrow shipped bootstrap and route
page-family or shared-runtime logic through focused module siblings instead of
recreating a new JS sink.

Milestone 4 is complete only when:

- `app/ui/modules/agents.js` and `app/ui/modules/shared.js` both fall below
  `800` lines
- any new JS sibling between `601` and `800` lines is routed explicitly in the
  same milestone
- UI static asset and behavior tests remain green

### Milestone 5. Semantic And Technical-Report Residual Packet
Outcome label: reduced

Create or execute a dedicated child packet for:

- `app/services/semantic_orchestration.py`
- `app/services/technical_reports.py`
- `app/services/audit_bundle_training_runs.py`

The packet must preserve current semantic, report, and audit contracts while
preventing moved implementation from landing in `documents.py`,
`eval_workbench.py`, or agent-task context overflow files.

Milestone 5 is complete only when:

- all three listed service files fall below `800` lines
- the packet preserves or strengthens the direct semantic, technical-report,
  and audit verification slices it touches
- no new cycle appears and no new large adjacent owner file is created

### Milestone 6. Cross-Cutting Service And Test Residual Packet
Outcome label: reduced

Create or execute a dedicated child packet for the remaining live `>800`
cross-cutting roots, including:

- `tests/unit/test_agent_task_verifications.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/unit/test_docling_parser.py`
- `tests/integration/test_search_harness_releases.py`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py`
- `app/services/documents.py`
- `app/services/improvement_cases.py`
- `tests/unit/test_improvement_case_intake.py`

Milestone 6 is complete only when:

- every remaining file listed above falls below `800` lines or is moved into a
  narrower same-milestone child packet created during the refreshed baseline
- governance-family files keep honest owner-case routing under
  `IC-08C078FD4F45`, and the later governance self-hosting closeout keeps
  `app/services/improvement_case_intake.py` exact-ratcheted at `552` with the
  rest of the narrowed family instead of leaving it as an inherited
  `601-800` residual
- parser, search-harness, claim-support, and Postgres integration coverage is
  at least as strong as before the split

### Milestone 7. Final Zero-Oversized Closeout
Outcome label: resolved

Close the broad large-file backlog with a fresh probe, full doc alignment, and
the final no-oversized assertion.

Milestone 7 is complete only when:

- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --max-file-lines 800`
  passes
- `uv run docling-system-hygiene-check` reports no new hygiene regressions
- every remaining `601-800` residual is routed under an explicit owner case and
  recorded in the current handoff and queue docs
- the final active packet, resolved packets, and remaining residuals agree
  across this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`,
  and `docs/boring_change_architecture_milestone_plan.md`

## Required Implementation Artifacts

- `docs/residual_large_file_backlog_milestone_plan.md`
- refreshed `config/improvement_cases.yaml` entries for every live `>800`
  surface lacking honest residual routing
- refreshed `config/hygiene_policy.yaml` bindings for every touched or newly
  created residual owner
- child packets created from Milestones 3 through 6, using honest focused names
  such as:
  - `docs/evaluation_residual_owner_family_milestone_plan.md`
  - `docs/ui_module_residual_owner_family_milestone_plan.md`
  - `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`
  - `docs/cross_cutting_large_file_residual_milestone_plan.md`
  or clearer equivalents chosen from the live baseline
- any gate or workflow updates required to run the final `--max-file-lines 800`
  probe as a checked-in closeout command

## Required Documentation And Handoff Updates

- update this plan at every milestone that changes the live `>800` queue
- update `docs/SESSION_HANDOFF.md` with the current active packet, queued
  packet order, refreshed `>800` count, and completed child-packet checkpoints
- update `docs/agentic_architecture_index.md` so the new child packets are
  discoverable before future sessions search broad history
- update `docs/boring_change_architecture_milestone_plan.md` when the large
  backlog count, active packet, or governing finish line changes
- update any child packet created from this plan in the same milestone that
  creates or closes it

## Required Verification Gates

Base gates for every milestone in this sequence:

- `git diff --check`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 25`

Required family gates when those surfaces are touched:

- Evaluation packet:
  `uv run ruff check app/services/evaluation_fixtures.py app/services/evaluation_scoring.py app/services/eval_workbench.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_evaluation_service.py`
- Evaluation packet:
  `uv run pytest -q tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py`
- Evaluation packet integration:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_eval_workbench_roundtrip.py tests/integration/test_multivector_retrieval.py`
- UI packet:
  `uv run pytest -q tests/unit/test_ui.py tests/unit/test_ui_static_assets.py`
- Semantic and technical-report packet:
  focused `ruff` and `pytest` slices for the touched semantic, technical-report,
  and audit files plus the direct integration harnesses they exercise
- Cross-cutting packet:
  focused `ruff` and `pytest` slices for the touched parser, Postgres, search,
  claim-support, document-service, and governance owners plus their integration
  tests

Final closeout gates:

- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --max-file-lines 800`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- A fresh architecture probe reports `0` code files above `800` lines.
- No already-closed compatibility facade regrows above its recorded narrow
  ratchet while this plan is executed.
- Every touched owner or test root between `601` and `800` lines has same-turn
  routing in `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`.
- The active packet, queued packets, and remaining residual backlog agree
  across this plan, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md`.
- The final probe gate with `--fail-on-cycles --max-file-lines 800` passes.
- The final full DB-backed suite passes without broadening skips or weakening
  assertions.

## Stop Conditions

- Stop and refresh Milestone 0 if a fresh architecture probe changes the live
  `>800` list before implementation of the next child packet begins.
- Stop if a fresh child packet or the paired `IC-08C078FD4F45` governance
  routing changes family ownership enough to alter queue order; update this
  plan before selecting the next child packet.
- Stop if a targeted large file is already being actively modified in the dirty
  worktree for unrelated reasons and the work cannot be cleanly isolated.
- Stop if a proposed split only gets green by weakening coverage, broadening
  skips, or hiding ownership in a nearby large file.
- Stop if a child packet cannot identify a focused owner family and is drifting
  toward another umbrella cleanup plan; rewrite the packet more narrowly first.

## Local Commit Closeout Policy

- Execute this sequence one child packet at a time.
- Each milestone closes only with one local atomic commit that contains the
  selected owner changes, focused tests, routing updates, docs, and handoff
  updates for that milestone only.
- Do not mix unrelated dirty-worktree changes into a large-file closeout
  commit.
- A verified but uncommitted packet is ready-to-close, not complete.

## Residual Risks And Next Milestone Routing

- The immediate next bounded implementation brief must now be reselected from
  `docs/boring_change_architecture_milestone_plan.md`.
- `docs/cross_cutting_verification_roots_milestone_plan.md` and
  `docs/improvement_case_governance_self_hosting_milestone_plan.md` are now
  both resolved locally in the current checkout.
- `docs/shared_verification_roots_milestone_plan.md` is now historical only
  until a later explicit Milestone 0 rebaseline proves it should be reactivated
  with a new live owner set.
- `app/services/improvement_case_intake.py` is no longer a live `>800` root,
  and the broader governance self-hosting family is now exact-ratcheted at
  `370`, `514`, `552`, `82`, `218`, `122`, `184`, `475`, `279`, `277`,
  `101`, `122`, and `551` under `IC-08C078FD4F45`.
- This plan is complete only when the architecture probe no longer reports any
  code file above `800` lines. This condition is now satisfied locally; any
  remaining `401-800` owner must still stay explicitly routed and visible in
  the queue docs.
