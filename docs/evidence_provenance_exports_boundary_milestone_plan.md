# Evidence Provenance Exports Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: drafted on 2026-05-13 as a stacked follow-on after
`docs/search_execution_orchestration_boundary_milestone_plan.md`,
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`, and
`docs/evaluations_service_boundary_milestone_plan.md`; do not start
implementation until all three prior packets close locally
Owner context: queued follow-on under `IC-65AF4A6D8B1E` /
`app/services/evidence_provenance_exports.py`. This plan assumes the current
search execution orchestration packet completes first, the queued claim-support
boundary packet completes second, the queued evaluations boundary packet
completes third, and Milestone 0 then refreshes the live system state before
any provenance-export code moves.

## Purpose

Resolve the largest residual evidence owner-module knot that remains after the
`app/services/evidence.py` facade cleanup.

The scoped problem is not only the line budget. The current owner still mixes
multiple distinct concern families in one place:

- provenance graph assembly
- provenance-export receipt and frozen-payload wiring
- supersession and governance change-impact coordination
- export persistence and freeze reuse
- fetch APIs for the persisted export

This plan resolves that scoped knot behind the existing evidence facade by
splitting graph assembly and export lifecycle ownership into focused owner
modules, while explicitly forbidding the work from spilling into adjacent
evidence owner modules such as `app/services/evidence_manifests.py`,
`app/services/evidence_claim_feedback.py`, `app/services/evidence_audit_views.py`,
or back into `app/services/evidence.py`.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 8]
   M app/hotspot_prevention_classifier.py
   M app/services/search.py
   M config/hotspot_prevention.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M tests/unit/test_hotspot_prevention.py
  ?? app/services/search_execution_orchestration.py
  ?? docs/claim_support_policy_impacts_boundary_milestone_plan.md
  ?? docs/evaluations_service_boundary_milestone_plan.md
  ?? docs/evidence_provenance_exports_boundary_milestone_plan.md
  ?? docs/search_execution_orchestration_boundary_milestone_plan.md

wc -l app/services/evidence_provenance_exports.py app/services/evidence_technical_report_exports.py app/services/evidence_provenance.py app/services/evidence.py tests/unit/test_evidence_provenance.py tests/unit/test_evidence_facade_contract.py
  1048 app/services/evidence_provenance_exports.py
   884 app/services/evidence_technical_report_exports.py
   467 app/services/evidence_provenance.py
   141 app/services/evidence.py
   636 tests/unit/test_evidence_provenance.py
    78 tests/unit/test_evidence_facade_contract.py

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

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15
  app/services.evidence has fan_in=28
  app/services/evidence_provenance_exports has fan_out=14
  app/services/evidence_provenance_exports is no longer a top-15 churn hotspot,
  but it remains the largest routed residual evidence owner module
  Python cycle components=3

config/improvement_cases.yaml
  IC-65AF4A6D8B1E remains open for the residual evidence owner-family modules
  observed_failure=app/services/evidence_provenance_exports.py at 1048 lines,
  the largest routed evidence owner surface

config/hygiene_policy.yaml
  app/services/evidence_provenance_exports.py currently allows max_lines=600,
  ratchet_max_lines=1048, and max_private_helpers=20 under IC-65AF4A6D8B1E
```

Repo-current structural evidence:

- `docs/search_execution_orchestration_boundary_milestone_plan.md`,
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`, and this evidence
  follow-on are all still drafted in the worktree. The current checkout also
  already contains in-flight search orchestration implementation surfaces in
  `app/services/search.py`, `app/services/search_execution_orchestration.py`,
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`, and
  `tests/unit/test_hotspot_prevention.py`. The active execution packet
  therefore remains the search orchestration plan, with claim-support and
  evaluations queued behind it, and this evidence follow-on must begin with a
  system-state refresh after all three prior packets complete and are
  committed.
- `app/services/evidence_provenance_exports.py` still groups the main concern
  families together:
  `_build_agent_task_provenance_export(...)`,
  `_existing_prov_export_artifact(...)`,
  `_prov_export_receipt_signature(...)`,
  `_prov_export_receipt(...)`,
  `_frozen_prov_export_payload(...)`,
  `_prov_export_receipt_integrity(...)`,
  `_record_prov_export_supersession_attempt(...)`,
  `_technical_report_change_impact_for_governance(...)`,
  `persist_agent_task_provenance_export(...)`, and
  `get_agent_task_provenance_export(...)`.
- Public and runtime callers currently depend on the `app.services.evidence`
  facade and the provenance-export owner surface through:
  `app/services/agent_task_worker.py`,
  `app/services/capabilities/agent_orchestration.py`,
  `app/api/routers/agent_tasks.py`,
  and `tests/unit/test_evidence_facade_contract.py`.
- The external route family is narrow but real:
  `/agent-tasks/{task_id}/provenance` flows through the agent-orchestration
  capability into `evidence.get_agent_task_provenance_export(...)` and must
  remain behavior-stable, including the structured `404` path.
- `tests/unit/test_evidence_provenance.py` is not yet the owner-module suite
  this file needs. It is only `636` lines and mainly exercises receipt,
  integrity, and cross-owner wrapper behavior rather than persistence,
  supersession reuse, and route-facing provenance-export lifecycle behavior.
- `config/hotspot_prevention.yaml` currently governs only the outer
  `app/services/evidence.py` facade. There is no explicit hotspot-prevention
  rule for `app/services/evidence_provenance_exports.py`, so future growth in
  this owner surface is not blocked today.
- Adjacent evidence owner modules are already oversized and must not absorb
  this debt in the milestone:
  `app/services/evidence_technical_report_exports.py` is `884` lines,
  `app/services/evidence_manifests.py` is governed above the default budget,
  `app/services/evidence_claim_feedback.py` is governed above the default
  budget, and `app/services/evidence_audit_views.py` is governed above the
  default budget under the same follow-on case.

## Goal

Resolve the scoped owner-boundary knot by the end of this stacked plan so
that:

- `app/services/evidence_provenance_exports.py` becomes a narrow compatibility
  surface and public provenance-export seam rather than the owner of graph
  assembly, lifecycle, and governance coordination bodies.
- At most three new owner modules are introduced:
  `app/services/evidence_provenance_export_graph_core.py`,
  `app/services/evidence_provenance_export_graph_report.py`, and
  `app/services/evidence_provenance_export_lifecycle.py`.
- `app/services/evidence.py` remains the stable top-level public facade for the
  evidence family, and `app/services/evidence_provenance.py` remains the owner
  of receipt/signature primitives rather than becoming the next broad export
  hub.
- The scoped issue is `resolved` when provenance graph assembly, receipt/frozen
  export wiring, supersession/governance coordination, persistence, and fetch
  APIs no longer coexist in `app/services/evidence_provenance_exports.py`.
- The broader owner case `IC-65AF4A6D8B1E` is `reduced` unless refreshed live
  hygiene evidence proves the remaining evidence owner-family modules are all
  within budget.

## Non-Goals

- No search, claim-support, evaluations, semantics, or agent-task refactor in
  this packet.
- No API path, request-model, or response-model redesign for agent-task
  provenance routes.
- No DB schema, ORM model, migration, or storage-contract change.
- No rewrite of `app/services/evidence.py`, `app/services/evidence_provenance.py`,
  or `app/services/evidence_technical_report_exports.py`.
- No attempt to close the entire `IC-65AF4A6D8B1E` owner-family follow-on in
  one packet; this plan is for the selected largest residual owner surface.
- No broad split into more than three new provenance-export owner modules.

## Scope

In scope:

- Milestone 0 stacked-state refresh after the search, claim-support, and
  evaluations packets close
- hotspot-prevention bootstrap for
  `app/services/evidence_provenance_exports.py`
- one graph-core owner module:
  `app/services/evidence_provenance_export_graph_core.py`
- one graph-report owner module:
  `app/services/evidence_provenance_export_graph_report.py`
- one export-lifecycle owner module:
  `app/services/evidence_provenance_export_lifecycle.py`
- direct owner-module unit coverage
- compatibility coverage for `app/services/evidence.py` and
  `app/services/evidence_provenance_exports.py`
- route-boundary and DB-backed integration verification for the existing
  provenance export path and governance-chain behavior
- hygiene, improvement-case, index, and handoff updates for the narrowed
  provenance-export facade

Out of scope:

- adding a fourth `evidence_provenance_export_*.py` owner file
- moving graph, governance, or persistence logic into
  `evidence_manifests.py`, `evidence_claim_feedback.py`,
  `evidence_audit_views.py`, or `evidence_technical_report_exports.py`
- changing the outer `app/services/evidence.py` public contract
- solving the other oversized evidence owner-family modules in this milestone

## Owner Surfaces

- compatibility owner:
  `app/services/evidence_provenance_exports.py`
- new graph-core owner:
  `app/services/evidence_provenance_export_graph_core.py`
- new graph-report owner:
  `app/services/evidence_provenance_export_graph_report.py`
- new lifecycle owner:
  `app/services/evidence_provenance_export_lifecycle.py`
- compatibility and importer surfaces:
  `app/services/evidence.py`,
  `app/services/agent_task_worker.py`,
  `app/services/capabilities/agent_orchestration.py`,
  `app/api/routers/agent_tasks.py`
- adjacent owners that may be called but must not absorb this debt:
  `app/services/evidence_provenance.py`,
  `app/services/evidence_manifests.py`,
  `app/services/evidence_claim_feedback.py`,
  `app/services/evidence_audit_views.py`,
  `app/services/evidence_technical_report_exports.py`
- focused tests:
  `tests/unit/test_evidence_provenance.py`,
  `tests/unit/test_evidence_provenance_export_graph_core.py`,
  `tests/unit/test_evidence_provenance_export_graph_report.py`,
  `tests/unit/test_evidence_provenance_export_lifecycle.py`,
  `tests/unit/test_evidence_facade_contract.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_semantic_governance_ledger.py`
- governance and routing surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- New graph scaffolding and shared PROV graph state construction belong in
  `app/services/evidence_provenance_export_graph_core.py`, including:
  entity/activity/agent scaffolding, manifest and trace roots, context-pack
  audit entities, source documents, document runs, source records, evidence
  package export entities, and base relation bookkeeping.
- New report-trace and claim-lineage graph ownership belong in
  `app/services/evidence_provenance_export_graph_report.py`, including:
  evidence cards, claims, claim feedback entities and edges, derivations,
  operator runs, provenance edges, retrieval-evaluation summary, and final
  PROV payload assembly.
- New export lifecycle ownership belongs in
  `app/services/evidence_provenance_export_lifecycle.py`, including:
  frozen export payload/receipt coordination, existing artifact lookup,
  supersession attempts, governance change-impact resolution, persistence
  workflow, freeze reuse, and `get_agent_task_provenance_export(...)`.
- Keep `app/services/evidence_provenance_exports.py` as the stable compatibility
  surface for direct imports and `app.services.evidence` re-exports.
- Keep `app/services/evidence_provenance.py` limited to receipt/signature and
  integrity primitives; do not move graph assembly or persistence workflow into
  that module.
- Do not move new implementation into `app/services/evidence_manifests.py`,
  `app/services/evidence_claim_feedback.py`, `app/services/evidence_audit_views.py`,
  or `app/services/evidence_technical_report_exports.py`; those files already
  carry separate residual debt and must not become the dumping ground for this
  split.
- Put direct owner-module tests in the new focused test files rather than
  broadening `tests/unit/test_evidence_provenance.py` into the next hotspot.
- Preserve the agent-task provenance route, evidence facade aliases, frozen
  artifact immutability semantics, supersession-attempt recording, release
  readiness DB gate relinking, claim-feedback relinking, and semantic
  governance event behavior.

## Weak-Point Prevention Contract

Freshness check: Milestone 0 must rerun live routing and architecture commands
after the search orchestration, claim-support boundary, and evaluations
boundary milestones close. This stacked plan is invalid if any prior packet
remains uncommitted or if the targeted provenance-export concern families no
longer live in `app/services/evidence_provenance_exports.py`.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| No hotspot-prevention rule exists for the residual provenance-export owner, so the split can regress immediately after closeout. | `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py`, `app/services/evidence_provenance_exports.py` | `uv run pytest -q tests/unit/test_hotspot_prevention.py` and `uv run docling-system-hotspot-prevention-check --strict` | New graph or lifecycle logic can be added back into `app/services/evidence_provenance_exports.py` without a failing gate. | Add or update a classifier case proving provenance graph or export-lifecycle growth in `app/services/evidence_provenance_exports.py` is blocked. | A future session drops more audit or receipt logic into `evidence_provenance_exports.py` because it already owns `persist_agent_task_provenance_export(...)`. |
| Debt silently shifts into already oversized adjacent evidence modules or into a broader unit-test file. | `app/services/evidence_manifests.py`, `app/services/evidence_claim_feedback.py`, `app/services/evidence_audit_views.py`, `app/services/evidence_technical_report_exports.py`, `tests/unit/test_evidence_provenance.py` | `wc -l` readback in closeout review plus focused owner-module tests | Adjacent evidence owners gain new concern families, or `tests/unit/test_evidence_provenance.py` grows above `636` lines. | New focused tests must land in `tests/unit/test_evidence_provenance_export_graph_core.py`, `...graph_report.py`, and `...lifecycle.py`. | A future session keeps the main file shorter by dumping lifecycle or graph code into a nearby evidence owner or by adding all new assertions to `test_evidence_provenance.py`. |
| The graph split is only cosmetic and one of the new graph owners becomes another mixed evidence hub. | `app/services/evidence_provenance_export_graph_core.py`, `app/services/evidence_provenance_export_graph_report.py` | `uv run docling-system-hygiene-check` and targeted unit suites | Either graph owner exceeds the stated ceiling or mixes lifecycle/persistence code. | Add a temporary lifecycle helper to a graph owner and prove the classifier or unit suite would reject it during review. | A future session puts supersession or storage-path behavior into the graph owner because it is “part of export generation.” |
| Lifecycle extraction breaks freeze reuse, supersession-attempt recording, or governance relinking while tests stay green only because coverage is thin. | `app/services/evidence_provenance_export_lifecycle.py`, `tests/unit/test_evidence_provenance_export_lifecycle.py`, DB-backed integration tests | `uv run pytest -q tests/unit/test_evidence_provenance_export_lifecycle.py tests/unit/test_evidence_facade_contract.py` and `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_semantic_governance_ledger.py` | Persist/get behavior changes without a failing test, or prior assertions are weakened instead of replaced. | Preserve or replace freeze-reuse, receipt, governance-event, and route assertions with equivalent or stronger owner tests. | A future session rewrites persistence flow and removes the supersession/governance checks because the route still returns a payload. |
| Public evidence facade or agent-task provenance route drifts while internal code moves. | `app/services/evidence.py`, `app/services/capabilities/agent_orchestration.py`, `app/api/routers/agent_tasks.py`, `tests/unit/test_agent_tasks_api.py` | `uv run pytest -q tests/unit/test_evidence_facade_contract.py tests/unit/test_agent_tasks_api.py` and `uv run docling-system-capability-contracts` | The evidence facade alias, capability method, or `/agent-tasks/{task_id}/provenance` 200/404 contract changes unexpectedly. | Keep the current route and facade-identity assertions, including the structured `agent_task_provenance_not_found` failure path. | A future session points the route directly at a new owner module and bypasses the evidence facade or capability seam. |

## Milestone Sequence

### Milestone 0: Post-Search-Claim-Support-Evaluations System-State Refresh
Outcome label: resolved

- Assume `docs/search_execution_orchestration_boundary_milestone_plan.md` has
  closed and committed first, then
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md` has closed and
  committed second, then
  `docs/evaluations_service_boundary_milestone_plan.md` has closed and
  committed third.
- Rerun the live architecture-quality, architecture-probe, improvement-case,
  hotspot-prevention, and hygiene commands after those closeouts.
- Refresh this plan, `docs/agentic_architecture_index.md`, and
  `docs/SESSION_HANDOFF.md` so the provenance-export packet becomes the next
  queued implementation brief only after the prior three packets are no longer
  draft-only worktree artifacts.
- Stop immediately if any of the prior three milestones are not complete, if
  `IC-65AF4A6D8B1E` has already been rerouted elsewhere, or if the targeted
  provenance-export families have already moved.

### Milestone 1: Provenance Export Facade Prevention Bootstrap
Outcome label: resolved

- Add explicit hotspot-prevention coverage for
  `app/services/evidence_provenance_exports.py` before moving code blocks.
- Update `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so provenance graph assembly,
  export-lifecycle logic, supersession handling, and governance relinking are
  blocked from regrowing inside the compatibility owner.
- Add or extend controlled-violation coverage in
  `tests/unit/test_hotspot_prevention.py`.
- Update hygiene ratchets so the final compatibility owner and new owner
  modules have concrete ceilings rather than the current inherited 1048-line
  ratchet.

### Milestone 2: Provenance Graph Owner Extraction
Outcome label: reduced

- Extract graph scaffolding and report-trace/claim-lineage graph ownership into
  `app/services/evidence_provenance_export_graph_core.py` and
  `app/services/evidence_provenance_export_graph_report.py`.
- Keep `app/services/evidence_provenance_exports.py` import-stable for direct
  tests and `app.services.evidence` re-exports.
- Add focused owner tests in
  `tests/unit/test_evidence_provenance_export_graph_core.py` and
  `tests/unit/test_evidence_provenance_export_graph_report.py`.
- Keep `tests/unit/test_evidence_provenance.py` at or below its current line
  count by moving focused cases instead of adding more monolithic coverage.

### Milestone 3: Export Lifecycle Extraction And Compatibility Reduction
Outcome label: resolved for the scoped provenance-export knot and reduced for broader owner case `IC-65AF4A6D8B1E` unless live evidence proves full retirement

- Extract existing-artifact lookup, supersession-attempt recording, governance
  change-impact coordination, freeze reuse, persistence workflow, and
  route-facing export fetch into
  `app/services/evidence_provenance_export_lifecycle.py`.
- Keep `app/services/evidence_provenance_exports.py` as the compatibility
  import surface for direct imports and `app/services/evidence.py` re-exports.
- Preserve `app/services/agent_task_worker.py`,
  `app/services/capabilities/agent_orchestration.py`, and
  `/agent-tasks/{task_id}/provenance` without contract drift.
- Close out the milestone with refreshed hygiene budgets, improvement-case
  measurement updates, architecture routing docs, and one local atomic commit.

## Required Implementation Artifacts

- `app/services/evidence_provenance_exports.py`
- `app/services/evidence_provenance_export_graph_core.py`
- `app/services/evidence_provenance_export_graph_report.py`
- `app/services/evidence_provenance_export_lifecycle.py`
- compatibility adjustments only, if needed:
  `app/services/evidence.py`,
  `app/services/agent_task_worker.py`,
  `app/services/capabilities/agent_orchestration.py`,
  `app/api/routers/agent_tasks.py`
- governance and tests:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `tests/unit/test_evidence_provenance.py`,
  `tests/unit/test_evidence_provenance_export_graph_core.py`,
  `tests/unit/test_evidence_provenance_export_graph_report.py`,
  `tests/unit/test_evidence_provenance_export_lifecycle.py`,
  `tests/unit/test_evidence_facade_contract.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/unit/test_hotspot_prevention.py`

## Required Documentation And Handoff Updates

- update this plan with completion status, outcome labels, verification, and
  any bounded residual routing
- update `docs/agentic_architecture_index.md`
- update `docs/SESSION_HANDOFF.md`
- update `config/improvement_cases.yaml` with deployed ref and measured residual
  state for `IC-65AF4A6D8B1E`
- update `config/hygiene_policy.yaml` with post-split ceilings for the
  compatibility owner and new provenance-export owner modules

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/evidence.py app/services/evidence_provenance.py app/services/evidence_provenance_exports.py app/services/evidence_provenance_export_graph_core.py app/services/evidence_provenance_export_graph_report.py app/services/evidence_provenance_export_lifecycle.py app/services/agent_task_worker.py app/services/capabilities/agent_orchestration.py app/api/routers/agent_tasks.py tests/unit/test_evidence_provenance.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_evidence_provenance_export_graph_report.py tests/unit/test_evidence_provenance_export_lifecycle.py tests/unit/test_evidence_facade_contract.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_evidence_provenance.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_evidence_provenance_export_graph_report.py tests/unit/test_evidence_provenance_export_lifecycle.py tests/unit/test_evidence_facade_contract.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_semantic_governance_ledger.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- Milestone 0 refreshes the stacked system state after the search,
  claim-support, and evaluations packets close and updates routing docs to
  reflect the new queued order.
- `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` explicitly govern
  `app/services/evidence_provenance_exports.py`, and the controlled-violation
  tests prove that graph or lifecycle growth in the compatibility owner is
  blocked.
- No more than three new owner modules are introduced, and they are exactly:
  `app/services/evidence_provenance_export_graph_core.py`,
  `app/services/evidence_provenance_export_graph_report.py`, and
  `app/services/evidence_provenance_export_lifecycle.py`.
- `app/services/evidence_provenance_exports.py` no longer owns provenance graph
  assembly, supersession-attempt logic, governance change-impact resolution, or
  full persistence workflow bodies.
- `app/services/evidence_provenance_exports.py` closes at `<= 300` lines and
  `<= 8` private helpers.
- `app/services/evidence_provenance_export_graph_core.py` closes at
  `<= 550` lines and `<= 18` private helpers.
- `app/services/evidence_provenance_export_graph_report.py` closes at
  `<= 550` lines and `<= 18` private helpers.
- `app/services/evidence_provenance_export_lifecycle.py` closes at
  `<= 350` lines and `<= 10` private helpers.
- `tests/unit/test_evidence_provenance.py` does not grow above its current
  `636` lines; new owner coverage lands in focused test files instead.
- `app/services/evidence.py`, `app/services/evidence_provenance.py`,
  `app/services/evidence_manifests.py`, `app/services/evidence_claim_feedback.py`,
  `app/services/evidence_audit_views.py`, and
  `app/services/evidence_technical_report_exports.py` do not absorb new owner
  families beyond minimal adapter changes.
- `persist_agent_task_provenance_export(...)` still freezes only once,
  reuses the frozen artifact on repeat calls, records supersession attempts when
  a new payload differs, refreshes release-readiness DB gate and claim-feedback
  links, and records the `technical_report_prov_export_frozen` governance event.
- `/agent-tasks/{task_id}/provenance` preserves current HTTP behavior,
  including the structured `agent_task_provenance_not_found` error path.
- The broader owner case `IC-65AF4A6D8B1E` is marked `reduced` unless the live
  hygiene evidence proves the remaining evidence owner-family modules are all
  within their configured budgets.

## Stop Conditions

- The search orchestration, claim-support boundary, or evaluations boundary
  milestone is not complete and committed locally.
- The targeted provenance-export concern families have already moved, making
  this drafted baseline stale.
- The split requires more than three new provenance-export owner modules.
- Any proposed new owner exceeds the ceilings in this plan.
- The split depends on moving core logic into `app/services/evidence.py`,
  `app/services/evidence_provenance.py`, `app/services/evidence_manifests.py`,
  `app/services/evidence_claim_feedback.py`, `app/services/evidence_audit_views.py`,
  or `app/services/evidence_technical_report_exports.py`.
- Route, worker, or governance failures imply an API, schema, or persistence
  contract change outside this packet.
- Hotspot prevention or integration verification can only be made green by
  deleting, weakening, skipping, or narrowing existing provenance/governance
  assertions.

## Local Commit Closeout Policy

This milestone is complete only after:

- implementation, tests, governance updates, and docs/handoff updates are all
  present together
- the full verification gate set passes
- the stacked routing docs reflect the post-closeout next owner case
- one local atomic commit lands for this milestone only

Do not mark the milestone complete if the code is green but the improvement
case, hygiene budgets, architecture index, or session handoff still describe
the old provenance-export ownership.

## Residual Risks And Next Milestone Routing

- `IC-65AF4A6D8B1E` is broader than this single owner surface. Even if this
  packet succeeds, other evidence owner-family modules may still remain above
  budget and require later follow-on milestones.
- `tests/unit/test_agent_tasks_api.py` is already a separate large test
  surface, so route any future route-test decomposition as its own test-focused
  follow-on instead of broadening this provenance-export packet.
- If the selected file is resolved cleanly but the remaining evidence-family
  debt still clusters in `app/services/evidence_technical_report_exports.py` or
  `app/services/evidence_semantic_trace.py`, route the next evidence follow-on
  to the larger of those residual owners based on a fresh hygiene snapshot.
