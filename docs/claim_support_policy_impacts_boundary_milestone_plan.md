# Claim Support Policy Impacts Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: resolved locally on 2026-05-13 after Milestones 1-4 completed in the
same local closeout window. The scoped subsystem-knot is resolved, while the
broader owner case `IC-E2270F89B397` remains reduced and open because
`app/services/claim_support_replay_alert_promotions.py`,
`app/services/claim_support_policy_impact_views.py`, and
`app/services/claim_support_policy_impact_replay.py` still exceed the default
600-line hygiene budget. The exact closeout commit hash is carried by the same
atomic commit that updates this plan and cannot be self-recorded here without
an amend.
Owner context: queued follow-on under `IC-E2270F89B397` /
`app/services/claim_support_policy_impacts.py`. This plan assumes the current
search execution orchestration packet is already closed locally as
`dae5e4f` and uses Milestone 1 to activate the first claim-support code
moves.

## Purpose

Resolve the subsystem-knot debt that remains in
`app/services/claim_support_policy_impacts.py` after the earlier replay-alert
promotion split.

The scoped problem is not only file size. The remaining service still owns
multiple distinct concern families in one place:

- list and summary reads
- worklist assembly
- alert and escalation read-models
- replay task queueing
- replay status refresh and closure lifecycle

This plan resolves that scoped knot behind the existing compatibility facade by
splitting the read-model family and replay-lifecycle family into two focused
owner modules, while explicitly forbidding the work from spilling into several
new `claim_support_*` files or bloating adjacent residual-debt modules such as
`app/services/claim_support_policy_governance.py` and
`app/services/claim_support_evaluations.py`.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 10]
  ?? docs/cli_command_dispatch_boundary_milestone_plan.md

wc -l app/services/claim_support_policy_impacts.py app/services/claim_support_replay_alert_promotions.py app/services/claim_support_policy_governance.py app/services/claim_support_evaluations.py tests/unit/test_claim_support_policy_impacts.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py
  2011 app/services/claim_support_policy_impacts.py
  1536 app/services/claim_support_replay_alert_promotions.py
  1259 app/services/claim_support_policy_governance.py
  1142 app/services/claim_support_evaluations.py
   116 tests/unit/test_claim_support_policy_impacts.py
   632 tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py
   341 tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py

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
  app/services/claim_support_policy_impacts.py: 18 revisions, 2011 lines, score 36198
  app/services/search.py: 32 revisions, 1592 lines, score 50944
  Python cycle components=3

config/improvement_cases.yaml
  IC-E2270F89B397 remains open for app/services/claim_support_policy_impacts.py
  observed_failure=line_count=2011 and private_helper_count=42 after the
  replay-alert promotion split
  deployed_ref=afc324a
```

Repo-current structural evidence:

- `docs/search_execution_orchestration_boundary_milestone_plan.md` is resolved
  locally through Milestone 1 closeout commit `dae5e4f`, and this
  claim-support follow-on is now the active bounded implementation brief.
  Milestone 0 refreshed the post-search system state so Milestone 1 can begin
  from the committed search baseline instead of the old drafted-worktree state.
- stacked follow-on milestone plans for evaluations, evidence
  provenance-export, semantics, runtime health orchestration, CI release gate
  parity, and boring-change architecture were committed locally as `f5d7823`;
  `docs/cli_command_dispatch_boundary_milestone_plan.md` remains the only
  adjacent late-stack follow-on still drafted locally.
- The prior claim-support split only moved replay-alert fixture coverage,
  candidate derivation, promotion receipts, and waiver-closure governance into
  `app/services/claim_support_replay_alert_promotions.py`; the compatibility
  facade stayed at `2011` lines after commit `afc324a`.
- `app/services/claim_support_policy_impacts.py` still groups the main concern
  families together:
  `list_claim_support_policy_change_impacts(...)`,
  `summarize_claim_support_policy_change_impacts(...)`,
  `claim_support_policy_change_impact_worklist(...)`,
  `claim_support_policy_change_impact_alerts(...)`,
  `record_claim_support_policy_change_impact_alert_escalations(...)`,
  `queue_claim_support_policy_change_impact_replay_tasks(...)`,
  `refresh_claim_support_policy_change_impact_replay_status(...)`, and
  `refresh_claim_support_policy_change_impacts_for_replay_task(...)`.
- `app/api/routers/claim_support_policy_impacts.py` exposes a full externally
  reachable route family for list, summary, worklist, alerts, escalations,
  fixture candidates, fixture promotions, detail, replay task creation, and
  replay-status refresh. The split is internal, but runtime HTTP behavior must
  remain stable.
- Current direct service-unit coverage is thin:
  `tests/unit/test_claim_support_policy_impacts.py` only guards the replay
  fixture candidate identity seam imported from
  `app/services/claim_support_replay_alert_promotions.py`.
- The claim-support route and runtime family already have meaningful boundary
  coverage in:
  `tests/unit/test_agent_tasks_api.py`,
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`,
  `tests/integration/test_claim_support_policy_activation_change_impacts_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py`,
  `tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`,
  and `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`.
- `config/hotspot_prevention.yaml` does not currently govern
  `app/services/claim_support_policy_impacts.py`, so future growth is not
  blocked by the same facade-prevention workflow used for search, evidence, and
  agent-task hotspots.
- Adjacent claim-support owner files are already oversized and must not absorb
  more debt in this milestone:
  `app/services/claim_support_policy_governance.py` is `1259` lines and
  `app/services/claim_support_evaluations.py` is `1142` lines with
  milestone-owned inherited ratchets rather than explicit owner-case closure.

## Goal

Resolve the scoped service-boundary knot by the end of this stacked plan so
that:

- `app/services/claim_support_policy_impacts.py` becomes a narrow compatibility
  facade and route-facing service seam rather than the owner of all read-model
  and replay-lifecycle bodies.
- At most two new owner modules are introduced:
  `app/services/claim_support_policy_impact_views.py` and
  `app/services/claim_support_policy_impact_replay.py`.
- Existing fixture-candidate and promotion logic remains in
  `app/services/claim_support_replay_alert_promotions.py`; this milestone must
  not duplicate or move that concern back.
- Adjacent residual modules
  `app/services/claim_support_policy_governance.py` and
  `app/services/claim_support_evaluations.py` do not gain new implementation
  debt.
- The scoped issue is `resolved` when the selected concern families no longer
  live together in `app/services/claim_support_policy_impacts.py`.
- The broader owner case `IC-E2270F89B397` is `reduced` unless refreshed live
  architecture evidence proves the hotspot is fully retired.

## Non-Goals

- No search, retrieval-learning, evidence, or agent-task refactor in this
  packet.
- No API path, request-model, or response-model contract redesign.
- No change to replay workflow version names, governance event kinds, artifact
  kinds, schema names, or receipt hash semantics unless a compatibility-preserving
  move requires the constants to relocate with the replay owner.
- No migration, DB schema, or persistence model change.
- No effort to resolve the unrelated size debt in
  `claim_support_policy_governance.py` or `claim_support_evaluations.py`.
- No broad split into more than two new owner modules.

## Scope

In scope:

- Milestone 0 stacked-state refresh after the search orchestration milestone
  closes
- hotspot-prevention bootstrap for
  `app/services/claim_support_policy_impacts.py`
- one read-model owner module:
  `app/services/claim_support_policy_impact_views.py`
- one replay-lifecycle owner module:
  `app/services/claim_support_policy_impact_replay.py`
- direct unit coverage for both new owners
- route-boundary and integration verification for the existing claim-support
  route family
- hygiene and improvement-case updates for the narrowed facade and the new
  owners
- architecture index and handoff updates in the same closeout commit

Out of scope:

- adding a third new `claim_support_policy_impact_*.py` owner file
- moving replay-alert fixture candidate or promotion logic out of
  `app/services/claim_support_replay_alert_promotions.py`
- solving the oversized-owner debt already present in
  `claim_support_policy_governance.py`,
  `claim_support_evaluations.py`, or
  `claim_support_replay_alert_promotions.py`
- changing route registration structure or moving the route family out of
  `app/api/routers/claim_support_policy_impacts.py`

## Owner Surfaces

- compatibility facade:
  `app/services/claim_support_policy_impacts.py`
- new read-model owner:
  `app/services/claim_support_policy_impact_views.py`
- new replay-lifecycle owner:
  `app/services/claim_support_policy_impact_replay.py`
- existing adjacent owners that may be called but must not absorb new debt:
  `app/services/claim_support_replay_alert_promotions.py`,
  `app/services/claim_support_policy_governance.py`,
  `app/services/claim_support_evaluations.py`
- route surfaces:
  `app/api/routers/claim_support_policy_impacts.py`,
  `app/api/routers/agent_tasks.py`
- tests:
  `tests/unit/test_claim_support_policy_impacts.py`,
  `tests/unit/test_claim_support_policy_impact_views.py`,
  `tests/unit/test_claim_support_policy_impact_replay.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/unit/test_hotspot_prevention.py`,
  and the claim-support integration roundtrip family
- governance and routing surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- New read-model logic belongs in
  `app/services/claim_support_policy_impact_views.py`, including:
  list, summary, worklist, alert projections, alert-escalation responses, and
  detail reads for policy change impacts.
- New replay-lifecycle logic belongs in
  `app/services/claim_support_policy_impact_replay.py`, including:
  replay queueing, plan integrity, replay closure construction, replay status
  refresh, and refresh-by-task coordination.
- Keep `app/services/claim_support_policy_impacts.py` as the stable import
  surface for existing callers and route modules.
- Do not move new implementation into
  `app/services/claim_support_policy_governance.py` or
  `app/services/claim_support_evaluations.py`; those files already carry
  separate residual debt and must not become the dumping ground for this split.
- Keep fixture candidate/promotion logic in
  `app/services/claim_support_replay_alert_promotions.py` and call it from the
  views owner where needed instead of duplicating candidate identity logic.
- Do not create additional files such as
  `claim_support_policy_impact_alerts.py` or
  `claim_support_policy_impact_worklist.py` in this milestone.
- Put direct owner-module unit tests in the matching new test files rather than
  growing `tests/unit/test_claim_support_policy_impacts.py` into another broad
  hotspot.

## Weak-Point Prevention Contract

Freshness check: Milestone 0 must rerun live routing and architecture commands
after the search orchestration milestone closes. This stacked plan is invalid if
the prior search milestone remains uncommitted or if the targeted claim-support
concern families no longer live in `app/services/claim_support_policy_impacts.py`.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Claim-support logic keeps growing in the facade because no hotspot-prevention rule exists today | `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py`, `app/services/claim_support_policy_impacts.py` | `uv run docling-system-hotspot-prevention-check --strict` plus `tests/unit/test_hotspot_prevention.py` | New read-model, alert, or replay-lifecycle bodies can be added to the facade without the gate failing | Add a temporary helper such as `def _build_replay_alert_worklist(...):` to the facade and confirm the gate blocks it | A future session adds “just one more worklist helper” because the facade has no explicit prevention rule |
| The split silently shifts debt into already-oversized adjacent claim-support files | `app/services/claim_support_policy_governance.py`, `app/services/claim_support_evaluations.py`, staged diff | `git diff --stat` review plus `uv run docling-system-hygiene-check` | New implementation lands in the adjacent oversized files instead of the planned new owners | Temporarily move a replay helper into `claim_support_policy_governance.py` and confirm staged-slice review or hygiene closeout rejects it | A future session sees “policy” or “evaluation” in a helper name and appends it to the wrong residual file |
| The read-model and replay-lifecycle concerns are separated only on paper while still sharing one broad owner body | `app/services/claim_support_policy_impact_views.py`, `app/services/claim_support_policy_impact_replay.py`, `app/services/claim_support_policy_impacts.py` | `uv run docling-system-hygiene-check` plus file-shape review | More than two new owner modules are introduced, or the facade still contains one of the selected major concern families by milestone closeout | Leave `claim_support_policy_change_impact_alerts(...)` or `refresh_claim_support_policy_change_impact_replay_status(...)` in the facade and confirm acceptance review fails | A future session creates one new module but leaves the other concern family in the facade and still claims the knot is fixed |
| Route behavior drifts while internal code is moved | `app/api/routers/claim_support_policy_impacts.py`, `app/api/routers/agent_tasks.py`, claim-support integration tests | `uv run pytest -q tests/unit/test_agent_tasks_api.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_hotspot_prevention.py` and `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` on the named claim-support integration family | Any worklist, alerts, replay-task creation, replay-status refresh, or detail route contract regresses | Temporarily drop alert operator links or a replay-status branch and confirm the unit/integration family fails | A future session assumes the split is “internal only” and skips HTTP-boundary proof |

Accepted residual risk after closeout: the broader owner case may remain open
even if the scoped subsystem knot is resolved. If either new owner module still
needs its own future size paydown, route that as new residual debt from fresh
post-closeout evidence rather than stretching this plan beyond its bounded
scope.

## Milestone Sequence

This plan is intentionally stacked behind the current search orchestration
packet. Milestone 0 is now resolved locally, so Milestone 1 is the first
remaining claim-support implementation gate.

### Milestone 0 - Post-Search System-State Refresh

Status: resolved locally on 2026-05-13 during the post-search closeout
alignment pass
Outcome label: `resolved`

Purpose:

- convert the current repo state from “search orchestration plan drafted but not
  closed” into the fresh baseline used by this plan
- promote this claim-support plan to the active bounded follow-on only after
  the prior search milestone is actually complete

Implementation:

- confirmed `docs/search_execution_orchestration_boundary_milestone_plan.md`
  records closeout commit `dae5e4f` and is no longer merely a
  pre-closeout verification snapshot
- reran live routing and hotspot evidence after that search closeout:
  `git status -sb`,
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`,
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`,
  and `wc -l` for the active claim-support owner files
- updated `docs/SESSION_HANDOFF.md` and
  `docs/agentic_architecture_index.md` so this claim-support plan is the active
  bounded implementation brief and Milestone 1 is the next gate
- refreshed this plan’s evidence section for the committed post-search
  baseline, including the reduced `app/services/search.py` architecture-probe
  footprint

Acceptance:

- the search orchestration milestone is complete, verified, and committed
  locally before claim-support implementation begins
- `IC-E2270F89B397` still exists and the targeted concern families still live in
  `app/services/claim_support_policy_impacts.py`
- this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` reflect the refreshed post-search state
- if the targeted concern families have already moved or the prior milestone is
  incomplete, stop and rewrite this plan instead of continuing

### Milestone 1 - Claim-Support Facade Prevention Bootstrap

Status: resolved locally on 2026-05-13
Outcome label: `resolved`

Implementation:

- add a hotspot-prevention rule for
  `app/services/claim_support_policy_impacts.py` with target role
  `claim-support policy impact compatibility facade`
- block new categories for:
  read-model worklist logic,
  alert projection or escalation logic,
  replay-lifecycle logic,
  and replay-closure receipt logic
- allow only import forwarders, alias forwarders, explicit forwarding wrappers,
  and deletions on the facade
- extend `app/hotspot_prevention_classifier.py` and
  `tests/unit/test_hotspot_prevention.py` with a controlled violation for the
  new rule

Acceptance:

- `uv run docling-system-hotspot-prevention-check --strict` passes on the real
  milestone diff
- the new controlled violation fails when introduced
- the rule allows a narrow forwarding facade but blocks new implementation in
  the compatibility surface

### Milestone 2 - Read-Model And Alert Owner Extraction

Status: resolved locally on 2026-05-13
Outcome label: `reduced`

Implementation:

- add `app/services/claim_support_policy_impact_views.py`
- move the read-model family into that owner module:
  `list_claim_support_policy_change_impacts(...)`,
  `summarize_claim_support_policy_change_impacts(...)`,
  `claim_support_policy_change_impact_worklist(...)`,
  `claim_support_policy_change_impact_alerts(...)`,
  `record_claim_support_policy_change_impact_alert_escalations(...)`,
  `get_claim_support_policy_change_impact(...)`,
  and their supporting worklist or alert projection helpers
- preserve stable imports through `app/services/claim_support_policy_impacts.py`
- add direct owner coverage in
  `tests/unit/test_claim_support_policy_impact_views.py`
- keep fixture-candidate and promotion logic delegated to
  `app/services/claim_support_replay_alert_promotions.py`

Acceptance:

- the selected read-model and alert families no longer have implementation
  bodies in `app/services/claim_support_policy_impacts.py` except for narrow
  forwarding seams
- `app/services/claim_support_policy_impact_views.py` closes within
  `<= 900` lines and `<= 20` private helpers
- `claim_support_policy_governance.py` and `claim_support_evaluations.py` do
  not gain new implementation debt
- router and integration behavior remain stable through the existing route
  family

### Milestone 3 - Replay Queueing And Closure Lifecycle Extraction

Status: resolved locally on 2026-05-13
Outcome label: `resolved` for the scoped subsystem-knot issue and `reduced` for
the broader owner case unless the live hotspot fully retires

Implementation:

- add `app/services/claim_support_policy_impact_replay.py`
- move the replay-lifecycle family into that owner module:
  `queue_claim_support_policy_change_impact_replay_tasks(...)`,
  `refresh_claim_support_policy_change_impact_replay_status(...)`,
  `refresh_claim_support_policy_change_impacts_for_replay_task(...)`,
  replay-plan integrity helpers,
  replay-closure payload and artifact helpers,
  task-queue helpers,
  and replay-status evaluation helpers
- preserve stable imports through `app/services/claim_support_policy_impacts.py`
- add direct owner coverage in
  `tests/unit/test_claim_support_policy_impact_replay.py`
- keep the replay workflow version, closure schema names, artifact kinds,
  semantic-governance event kinds, and receipt hash behavior contract-stable

Acceptance:

- the selected replay queueing and refresh families no longer have
  implementation bodies in `app/services/claim_support_policy_impacts.py`
  except for narrow forwarding seams
- `app/services/claim_support_policy_impact_replay.py` closes within
  `<= 900` lines and `<= 20` private helpers
- `app/services/claim_support_policy_impacts.py` closes within
  `<= 450` lines and `<= 8` private helpers
- no third new claim-support owner file is introduced
- the scoped subsystem-knot issue is resolved because the selected read-model,
  alert, and replay-lifecycle concerns no longer cohabit the same file

### Milestone 4 - Closeout, Ratchets, And Residual Routing

Status: resolved locally on 2026-05-13
Outcome label: `reduced`

Implementation:

- update `config/hygiene_policy.yaml` with exact verified ceilings for the
  narrowed facade and both new owner modules
- update `config/improvement_cases.yaml` so `IC-E2270F89B397` records the new
  measurements and broader owner-case state after the split
- refresh `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  this plan with the verified closeout status, verification commands, and
  post-closeout routing; note that the same atomic commit cannot self-record
  its own closeout hash without an amend
- stage only the verified claim-support milestone slice and close with one
  local atomic commit

Acceptance:

- all required verification gates below pass in the same closeout window
- the scoped subsystem-knot issue is recorded as resolved in this plan
- the broader owner case is marked `reduced` unless live architecture evidence
  proves full retirement
- the same closeout commit contains code, tests, governance config, and docs

Closeout results:

- `app/services/claim_support_policy_impacts.py` now closes at `184` lines and
  `0` private helpers as a compatibility facade
- `app/services/claim_support_policy_impact_views.py` now closes at `899` lines
  and `16` private helpers
- `app/services/claim_support_policy_impact_replay.py` now closes at `898`
  lines and `11` private helpers
- direct owner-module coverage now lives in
  `tests/unit/test_claim_support_policy_impact_views.py` and
  `tests/unit/test_claim_support_policy_impact_replay.py`
- final verification window closed with `64` focused unit passes, `19`
  claim-support integration passes, `1896` full DB-backed suite passes,
  `known_hotspots=8`, `changed_hotspots=1`, `blocked=0`, `allowed=1`,
  `exceptions=0`, and architecture quality
  `max_hotspot_risk_score=516.06`
- the next routed follow-on after this local closeout is
  `docs/evaluations_service_boundary_milestone_plan.md`

## Required Implementation Artifacts

- `app/services/claim_support_policy_impact_views.py`
- `app/services/claim_support_policy_impact_replay.py`
- updated `app/services/claim_support_policy_impacts.py`
- updated hotspot-prevention policy and classifier
- updated direct owner-module unit tests
- updated route-boundary and integration coverage where needed
- updated improvement-case and hygiene routing
- updated architecture index and handoff

## Required Documentation And Handoff Updates

- this plan:
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`
- architecture index:
  `docs/agentic_architecture_index.md`
- canonical handoff:
  `docs/SESSION_HANDOFF.md`
- improvement-case registry:
  `config/improvement_cases.yaml`
- hygiene ratchets:
  `config/hygiene_policy.yaml`

Milestone 0 must also update the active-follow-up references in the handoff and
index after the search orchestration milestone completes.

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/claim_support_policy_impacts.py app/services/claim_support_policy_impact_views.py app/services/claim_support_policy_impact_replay.py app/services/claim_support_replay_alert_promotions.py app/api/routers/claim_support_policy_impacts.py app/api/routers/agent_tasks.py app/hotspot_prevention_classifier.py tests/unit/test_claim_support_policy_impacts.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_claim_support_policy_impacts.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_activation_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py tests/integration/test_claim_support_policy_mined_failures_roundtrip.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- Milestone 0 refreshes the repo’s live system state after the search
  orchestration milestone closes and promotes this plan to the active bounded
  follow-on.
- `app/services/claim_support_policy_impacts.py` gains explicit
  hotspot-prevention governance before broad refactoring begins.
- No more than two new owner modules are introduced.
- The selected read-model, alert, queueing, replay-closure, and refresh
  concerns no longer live together in the compatibility facade by closeout.
- `app/services/claim_support_policy_impact_views.py` and
  `app/services/claim_support_policy_impact_replay.py` remain under the stated
  line and helper ceilings.
- `app/services/claim_support_policy_impacts.py` closes at `<= 450` lines and
  `<= 8` private helpers with only allowed forwarding or compatibility seams.
- `claim_support_policy_governance.py` and `claim_support_evaluations.py` do
  not absorb new implementation debt.
- Existing route paths and response contracts remain stable for list, summary,
  worklist, alerts, detail, replay-task creation, and replay-status refresh.
- Test coverage is equivalent or stronger than before the split; no test,
  fixture, or gate is weakened to get green.
- The scoped subsystem-knot issue is `resolved` in this plan, while the broader
  owner case is only `reduced` unless refreshed live evidence proves the hotspot
  is retired.

## Stop Conditions

- Stop if Milestone 0 shows the prior search orchestration milestone is not yet
  complete and committed.
- Stop if the selected claim-support concern families have already moved or the
  file no longer matches this plan’s baseline shape after the search closeout.
- Stop if preserving route and runtime behavior requires more than two new owner
  modules.
- Stop if either new owner module cannot be kept within the stated line and
  helper ceilings.
- Stop if the split requires moving new logic into
  `claim_support_policy_governance.py` or `claim_support_evaluations.py`.
- Stop if targeted route or integration verification fails in a way that
  implies an API, schema, or persistence contract change outside this packet.

## Local Commit Closeout Policy

- Stage only the verified claim-support milestone slice.
- Leave unrelated dirty and untracked files alone.
- Include implementation, tests, config, docs, and handoff updates in the same
  local atomic commit.
- Record the closeout commit hash in this plan and in
  `docs/SESSION_HANDOFF.md` during the next alignment pass; the same atomic
  closeout commit cannot self-record that hash without an amend.
- Treat the milestone as incomplete until that commit exists.
- Do not commit if any required verification gate fails.

## Residual Risks And Next Milestone Routing

- Most likely residual risk: the new read-model or replay-lifecycle owners may
  still be oversized relative to the default file budget even if the subsystem
  knot is resolved. If so, route them as explicit new residual debt rather than
  stretching this plan.
- Another residual risk is that the broader architecture ranking may still
  prioritize other hotspots even after this service-boundary split. That does
  not invalidate the scoped resolution here; it only affects what comes next.
- After closeout, choose the next follow-on from fresh post-closeout evidence in
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`, and the architecture probe.
- Do not predeclare the post-claim-support target before that evidence exists.
