# Agent Task Schema Aggregation Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-14 UTC
Status: Milestone 0 refreshed the live post-CLI state after
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
`docs/evaluations_service_boundary_milestone_plan.md`,
`docs/evidence_provenance_exports_boundary_milestone_plan.md`,
`docs/semantics_service_boundary_milestone_plan.md`, and
`docs/cli_command_dispatch_boundary_milestone_plan.md` all closed locally
through commits `3d7d090`, `1159297`, `1aa8378`, `a2eb27e`, and `4a79a82`;
Milestone 1 is now the next active governance-ratchet slice
Owner context: active follow-on under `IC-24F3558D6091` /
`app/schemas/agent_tasks.py`. The prior claim-support packet completed first,
the evaluations packet completed second, the evidence provenance-export packet
completed third, the semantics packet completed fourth, the CLI packet
completed fifth, Milestone 0 refreshed the live system state, and Milestone 1
now governs the first schema-facade code change.

## Purpose

Resolve the open architecture hotspot in `app/schemas/agent_tasks.py`.

The scoped problem is not missing owner modules. The agent-task schema family is
already split across seven focused schema files, but most of the repo still
imports through one oversized aggregation facade. That leaves three forms of
debt in place at once:

- a broad re-export surface at `app/schemas/agent_tasks.py`
- high production import fan-in through that aggregation facade
- weak governance because hygiene still allows `2061` lines and there is no
  dedicated hotspot-prevention rule for the facade

This plan resolves that scoped knot by turning `app/schemas/agent_tasks.py`
into a narrow compatibility facade backed by the existing schema-owner module
contracts, moving internal production importers onto those owners directly, and
explicitly forbidding the work from being "solved" by creating a second export
catalog file or another new `app/schemas/agent_task_*.py` sink.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-14 UTC:

```text
git status -sb
  ## main...origin/main [ahead 36]

wc -l app/schemas/agent_tasks.py app/schemas/agent_task_core.py app/schemas/agent_task_claim_support.py app/schemas/agent_task_reports.py app/schemas/agent_task_search_workflows.py app/schemas/agent_task_semantic_generation.py app/schemas/agent_task_semantic_graph.py app/schemas/agent_task_semantics.py
   461 app/schemas/agent_tasks.py
   458 app/schemas/agent_task_core.py
   577 app/schemas/agent_task_claim_support.py
   429 app/schemas/agent_task_reports.py
   370 app/schemas/agent_task_search_workflows.py
   312 app/schemas/agent_task_semantic_generation.py
   565 app/schemas/agent_task_semantic_graph.py
   348 app/schemas/agent_task_semantics.py

python - <<'PY'
from app.schemas import agent_tasks
print(len(agent_tasks.__all__))
PY
  221

uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=501.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

uv run docling-system-improvement-case-summary
  case_count=29
  status_counts.open=21
  status_counts.deployed=7
  status_counts.measured=1
  actionable_buckets.oldest_open_case_id=IC-9812A0B138D9

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  top hotspot remains tests/unit/test_agent_tasks_api.py
  app.schemas.agent_tasks imported by 92 local modules
  Python cycle components=5

config/improvement_cases.yaml
  IC-24F3558D6091 remains open for app/schemas/agent_tasks.py with
  observed_failure=risk_score=409.07, line_count=461, changes_90d=58

config/hygiene_policy.yaml
  app/schemas/agent_tasks.py currently allows max_lines=2061 and
  max_private_helpers=0, with no owner_case_id

rg -n '^__all__' app/schemas/agent_task_*.py
  app/schemas/agent_task_core.py:421
  app/schemas/agent_task_claim_support.py:545
  app/schemas/agent_task_reports.py:404
  app/schemas/agent_task_search_workflows.py:336
  app/schemas/agent_task_semantic_generation.py:291
  app/schemas/agent_task_semantic_graph.py:521
  app/schemas/agent_task_semantics.py:314
```

Repo-current structural evidence:

- `app/schemas/agent_tasks.py` is currently a pure aggregation facade. The file
  has no local schema class bodies or service logic; it is almost entirely
  direct re-export imports plus a 221-name `__all__`.
- The specialized owner modules already exist and already publish explicit
  `__all__` contracts. The remaining issue is therefore aggregation and import
  fan-in, not missing schema boundaries.
- Production importers still come through the broad facade across API, service,
  capability, and CLI surfaces, including
  `app/api/routers/agent_tasks.py`,
  `app/api/routers/agent_task_analytics.py`,
  `app/api/routers/claim_support_policy_impacts.py`,
  `app/agent_task_cli.py`,
  `app/cli.py`,
  `app/services/agent_tasks.py`,
  `app/services/agent_task_context.py`,
  `app/services/agent_task_context_*.py`,
  `app/services/agent_actions/*.py`,
  `app/services/capabilities/agent_orchestration*.py`,
  `app/services/technical_report*.py`,
  `app/services/semantic_generation.py`,
  `app/services/eval_workbench.py`, and
  `app/services/search_harness_optimization.py`.
- The five upstream packets are no longer drafted or in flight. They are now
  committed local closeouts at `3d7d090`, `1159297`, `1aa8378`, `a2eb27e`, and
  `4a79a82`, so this schema-facade packet is now the active bounded follow-on.
- The live post-stack refresh confirms the scoped schema-aggregation issue
  still exists unchanged: the facade is still 461 lines, still exports 221
  names, still appears in the architecture-quality top-hotspot set, and still
  routes 92 production or test imports through one aggregation surface.
- The current live config still leaves the schema-facade governance gap open:
  `config/hygiene_policy.yaml` still allows `app/schemas/agent_tasks.py` at
  `2061` lines with no `owner_case_id`, and `config/improvement_cases.yaml`
  still records the older 409.07-risk snapshot without any post-refresh
  measurement or deployment note.

## Goal

Resolve the scoped schema-aggregation debt so that:

- `app/schemas/agent_tasks.py` becomes a compact compatibility facade rather
  than the primary internal dependency surface for most agent-task schemas.
- No new schema-definition owner modules are created; the existing seven owner
  modules remain authoritative.
- Production `app/` code imports focused owner modules directly instead of
  defaulting to `app.schemas.agent_tasks`.
- Hotspot prevention, hygiene, and schema-facade contract tests make the new
  boundary executable.
- The scoped aggregation issue is `resolved` when the compatibility facade no
  longer owns long direct re-export batches or broad production import fan-in.
- The broader owner case `IC-24F3558D6091` is `reduced` unless refreshed live
  architecture evidence proves the hotspot is fully retired.

## Non-Goals

- No schema shape, field, enum value, or API contract change.
- No service, capability, route, or CLI behavior redesign.
- No new `app/schemas/agent_task_*.py` owner modules.
- No second public facade such as `app/schemas/agent_task_public.py`.
- No broad generated export-catalog file or private aggregation sink such as
  `app/schemas/_agent_task_schema_exports.py`.
- No attempt to resolve `app/services/agent_tasks.py`,
  `tests/unit/test_agent_tasks_api.py`, or
  `tests/unit/test_agent_task_context.py` as separate hotspot owners beyond the
  minimal import updates required by this plan.

## Scope

In scope:

- Milestone 0 stacked-state refresh after the five prior queued packets close
- compatibility-facade compaction for `app/schemas/agent_tasks.py`
- direct-import migration for production `app/` importers
- a dedicated schema-facade contract and import-fan-in test surface
- hotspot-prevention, hygiene, and owner-case ratchets for the facade
- closeout updates for docs, handoff, and architecture routing

Out of scope:

- any new schema-definition owner file
- any new broad schema-export helper or registry file
- broad test-hotspot decomposition
- any business-logic move in services or routers beyond import rewiring

## Owner Surfaces

- compatibility facade:
  `app/schemas/agent_tasks.py`
- authoritative schema owners:
  `app/schemas/agent_task_core.py`,
  `app/schemas/agent_task_claim_support.py`,
  `app/schemas/agent_task_reports.py`,
  `app/schemas/agent_task_search_workflows.py`,
  `app/schemas/agent_task_semantic_generation.py`,
  `app/schemas/agent_task_semantic_graph.py`,
  `app/schemas/agent_task_semantics.py`
- high-fan-in production importers:
  `app/api/routers/agent_tasks.py`,
  `app/api/routers/agent_task_analytics.py`,
  `app/api/routers/claim_support_policy_impacts.py`,
  `app/agent_task_cli.py`,
  `app/cli.py`,
  `app/services/agent_tasks.py`,
  `app/services/agent_task_context.py`,
  `app/services/agent_task_context_*.py`,
  `app/services/agent_actions/*.py`,
  `app/services/capabilities/agent_orchestration*.py`,
  `app/services/technical_report*.py`,
  `app/services/semantic_generation.py`,
  `app/services/search_harness_optimization.py`,
  `app/services/claim_support_policy_impacts.py`,
  `app/services/eval_workbench.py`
- focused tests:
  `tests/unit/test_agent_task_schema_facade_contract.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/unit/test_agent_task_actions.py`,
  `tests/unit/test_agent_task_context.py`,
  `tests/unit/test_cli_agent_tasks.py`,
  `tests/unit/test_hotspot_prevention.py`
- adjacent surfaces that may be touched for imports but must not absorb this
  debt:
  `app/schemas/search.py`,
  `app/services/agent_tasks.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/unit/test_agent_task_context.py`
- governance and routing surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- `app/schemas/agent_tasks.py` remains the stable public compatibility facade.
  After closeout it may contain only:
  owner-module imports,
  composed export-registry declarations,
  explicit alias forwarders,
  `__all__`,
  `__getattr__`,
  `__dir__`,
  and deletion-only cleanup.
- No `BaseModel`, `Field`, `StrEnum`, `UUID`, `datetime`, or schema-class
  definitions may remain in `app/schemas/agent_tasks.py` after closeout.
- Long direct `from app.schemas.agent_task_* import (...)` batches do not
  belong in the facade after closeout. Use a compact module-registry pattern
  backed by the existing owner-module `__all__` contracts instead.
- Do not create a new `app/schemas/_agent_task_schema_exports.py`,
  `app/schemas/agent_task_export_catalog.py`, or another equivalent sink just
  to move the same aggregation debt elsewhere. If the facade cannot be
  compacted without that move, stop and rewrite the plan.
- Production `app/` code must import from the focused owner module it actually
  uses. `app.schemas.agent_tasks` remains for legacy compatibility imports and
  explicit contract tests, not for internal convenience.
- New schema-contract coverage belongs in
  `tests/unit/test_agent_task_schema_facade_contract.py`, not in
  `tests/unit/test_agent_tasks_api.py` or
  `tests/unit/test_agent_task_context.py`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A future session adds one more schema class or enum directly to the aggregation facade because "it is already imported there." | `app/schemas/agent_tasks.py`, `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py`, `tests/unit/test_hotspot_prevention.py` | `uv run docling-system-hotspot-prevention-check --strict` plus controlled-violation tests | Any new schema definition or schema-building import lands directly in `app/schemas/agent_tasks.py` | Add a temporary `class NewTaskInput(BaseModel): ...` or `from pydantic import BaseModel, Field` to the facade and confirm the gate fails | A future session treats the facade as the easiest place to add a new request or response model |
| The work only moves the same 221-name aggregation list into a second private file and calls that "modular." | `app/schemas/agent_tasks.py`, staged diff, `tests/unit/test_agent_task_schema_facade_contract.py` | Structure contract plus closeout review | A new broad export-catalog file or second public surface is introduced to hold the same aggregation debt | Add a temporary `app/schemas/_agent_task_schema_exports.py` sink and confirm the contract or closeout review rejects it | A future session rewrites the imports mechanically and hides the hotspot one file away |
| Production app code keeps importing the broad facade out of habit, so fan-in remains effectively unchanged. | `app/**/*.py`, `tests/unit/test_agent_task_schema_facade_contract.py` | Focused importer-scan test plus targeted unit suites | Any non-allowlisted production importer still uses `app.schemas.agent_tasks` after the migration | Leave one direct app importer on `app.schemas.agent_tasks` and confirm the focused contract test fails | A future session takes the shortcut because direct owner imports look slightly longer |
| Compacting the facade breaks legacy `from app.schemas.agent_tasks import ...` imports or runtime schema use. | `app/schemas/agent_tasks.py`, focused facade contract tests, targeted unit suites, final DB-backed suite | `uv run pytest -q` on the named schema or agent-task suites and `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` | Any legacy import or runtime schema path fails after the facade is compacted | Temporarily drop one export from the registry and confirm contract tests or agent-task suites fail | A future session optimizes for line count and silently drops compatibility |

Accepted residual risk after closeout: `app/schemas/agent_tasks.py` may still
remain a routed hotspot if tests and external compatibility callers continue to
import it heavily even after production fan-in is removed. If that happens,
keep the owner case open as `reduced` and route any remaining work from fresh
post-closeout evidence rather than stretching this milestone into a schema
redesign.

## Milestone Sequence

This plan is intentionally stacked behind the current claim-support,
evaluations, evidence provenance-export, semantics, and CLI packets.
Milestone 0 is mandatory and must run before any schema code changes start.

### Milestone 0 - Post-CLI System-State Refresh

Status: resolved locally in this refresh closeout
Outcome label: `resolved`

Purpose:

- convert the current repo state from "five earlier packets drafted or in
  flight" into the fresh baseline used by this plan
- promote this schema-facade plan to the active bounded follow-on only after
  the prior five packets are actually complete

Implementation:

- confirm
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`,
  `docs/semantics_service_boundary_milestone_plan.md`, and
  `docs/cli_command_dispatch_boundary_milestone_plan.md`
  each have real closeout commits recorded and are no longer merely drafted
- rerun live routing and schema-facade evidence after those closeouts:
  `git status -sb`,
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`,
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`,
  and `wc -l` for the facade and owner schema files
- refresh this plan's evidence section if the earlier closeouts changed the
  queue, counts, or hotspot ordering materially
- update `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md` so
  this plan becomes the active bounded implementation brief

Acceptance:

- all five prior packets are complete, verified, and committed locally before
  schema-facade implementation begins
- `app/schemas/agent_tasks.py` still presents the same scoped aggregation issue
  or the plan is rewritten before code motion starts
- this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` reflect the refreshed post-stack state

### Milestone 1 - Facade Governance Ratchet

Status: next active implementation slice
Outcome label: `resolved`

Implementation:

- add a dedicated hotspot-prevention policy entry for
  `app/schemas/agent_tasks.py`
- set the target role to agent-task schema compatibility facade and point the
  preferred owner modules at the existing seven schema-owner files
- block direct schema definitions, broad direct re-export batches, and new
  export-sink surfaces in the facade while still allowing compact
  compatibility-registry declarations and explicit alias forwarders
- update `app/hotspot_prevention_classifier.py` and
  `tests/unit/test_hotspot_prevention.py` with controlled violations that prove
  the new rule blocks facade growth but still allows the narrow compatibility
  pattern
- add `owner_case_id: IC-24F3558D6091` to the hygiene entry immediately, then
  tighten the final line budget in the closeout milestone after the compact
  facade exists

Acceptance:

- `uv run docling-system-hotspot-prevention-check --strict` passes on the real
  milestone diff
- a temporary direct schema definition or broad re-export batch in
  `app/schemas/agent_tasks.py` fails the tightened gate
- the rule still allows a compact compatibility registry and explicit legacy
  forwarders
- the facade can no longer grow new schema implementation without a gate
  failure

### Milestone 2 - Production Import Fan-In Reduction

Status: drafted
Outcome label: `reduced`

Implementation:

- migrate production `app/` importers from `app.schemas.agent_tasks` to the
  focused owner module they actually need
- perform the migration by schema family so ownership stays obvious:
  core,
  claim-support,
  reports,
  search workflows,
  semantic generation,
  semantic graph,
  semantics
- touch the broad production importer families in this packet, including API
  routers, capabilities, CLIs, `app/services/agent_tasks.py`,
  `app/services/agent_task_context*.py`,
  `app/services/agent_actions/*.py`,
  `app/services/technical_report*.py`,
  `app/services/semantic_generation.py`,
  `app/services/search_harness_optimization.py`,
  `app/services/claim_support_policy_impacts.py`, and
  `app/services/eval_workbench.py`
- add a focused contract test that scans production `app/` code and fails if
  `app.schemas.agent_tasks` remains in use outside an explicit and documented
  allowlist

Acceptance:

- production `app/` import fan-in through `app.schemas.agent_tasks` drops
  materially from the current 90-importer baseline
- no non-allowlisted production importer still depends on the broad facade
- targeted unit suites prove the import rewiring did not change behavior

### Milestone 3 - Compatibility Facade Compaction

Status: drafted
Outcome label: `resolved` for the scoped aggregation issue and `reduced` for
the broader owner case unless the live hotspot fully retires

Implementation:

- rewrite `app/schemas/agent_tasks.py` as a compact compatibility facade backed
  by the existing owner-module `__all__` contracts
- compose the public export surface from the seven owner modules rather than
  keeping a long direct re-export file
- preserve runtime compatibility for legacy
  `from app.schemas.agent_tasks import ...` imports
- do not add a new schema owner or an export-catalog support file
- add `tests/unit/test_agent_task_schema_facade_contract.py` with at least
  these checks:
  public surface equals the union of the owner-module exports,
  every facade export resolves to the underlying owner object,
  the facade contains only allowed top-level structure,
  production app importers do not route through the broad facade,
  and controlled negative fixtures fail when an unexpected schema definition or
  export is introduced

Acceptance:

- `app/schemas/agent_tasks.py` closes within `<= 160` lines and
  `<= 2` private helpers
- the public export surface remains complete and behavior-stable
- no new owner module or export-sink file is introduced
- the scoped aggregation issue is resolved because the facade is now compact
  and production code no longer treats it as the default import source

### Milestone 4 - Closeout, Ratchets, And Residual Routing

Status: drafted
Outcome label: `reduced`

Implementation:

- update `config/hygiene_policy.yaml` with exact verified ceilings for the
  compacted facade and its helper count
- update `config/improvement_cases.yaml` so `IC-24F3558D6091` records the
  refreshed measurements, owner-case notes, and `resolved` or `reduced`
  language grounded in live evidence
- refresh `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  this plan with the closeout hash, verification commands, and post-closeout
  routing
- stage only the verified schema-facade milestone slice and close with one
  local atomic commit

Acceptance:

- all required verification gates below pass in the same closeout window
- the scoped schema aggregation issue is recorded as resolved in this plan
- the broader owner case is marked `reduced` unless live architecture evidence
  proves full retirement
- the same closeout commit contains code, tests, governance config, and docs

## Required Implementation Artifacts

- updated `app/schemas/agent_tasks.py`
- updated production importers across the named `app/` surfaces
- updated `app/schemas/agent_task_*.py` files only if their `__all__` surfaces
  need same-commit cleanup or normalization
- updated hotspot-prevention policy and classifier
- new `tests/unit/test_agent_task_schema_facade_contract.py`
- updated focused unit suites and routing docs

## Required Documentation And Handoff Updates

- update this plan with actual closeout status, evidence, and residual routing
- update `docs/SESSION_HANDOFF.md` so the active plan and next routed follow-on
  are accurate after closeout
- update `docs/agentic_architecture_index.md` so the compact architecture queue
  reflects the verified post-closeout state
- update `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` in
  the same commit as the implementation and tests

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/schemas/agent_tasks.py app/schemas/agent_task_*.py app/api/routers/agent_tasks.py app/api/routers/agent_task_analytics.py app/api/routers/claim_support_policy_impacts.py app/agent_task_cli.py app/cli.py app/services/agent_tasks.py app/services/agent_task_*.py app/services/agent_actions/*.py app/services/capabilities/agent_orchestration*.py app/services/technical_report*.py app/services/semantic_generation.py app/services/search_harness_optimization.py app/services/claim_support_policy_impacts.py app/services/eval_workbench.py tests/unit/test_agent_task_schema_facade_contract.py tests/unit/test_agent_tasks.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_cli_agent_tasks.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_agent_task_schema_facade_contract.py tests/unit/test_agent_tasks.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_cli_agent_tasks.py tests/unit/test_hotspot_prevention.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Equivalent or broader contract coverage is required. Do not weaken tests, add
skips, narrow gates, or move assertions out of the failing path just to make
verification pass.

## Acceptance Criteria

- `app/schemas/agent_tasks.py` is a genuine compatibility facade with no local
  schema implementation and no broad direct re-export batch.
- Production `app/` code no longer relies on the aggregation facade except for
  an explicit, documented allowlist if a true edge case remains.
- No new schema owner module or export-catalog sink file was introduced.
- The schema facade has an executable hotspot-prevention rule and a focused
  contract test surface.
- The public `app.schemas.agent_tasks` import contract remains behavior-stable.
- `IC-24F3558D6091` is updated from fresh live evidence, and this plan records
  the outcome as `resolved` for the scoped issue and `reduced` or `resolved`
  for the broader owner case based on the refreshed architecture evidence.

## Stop Conditions

- If Milestone 0 shows any of the five earlier queued packets are incomplete,
  unverified, or rerouted, stop and refresh this plan before implementation.
- If the only way to shrink the facade is to create a second giant export list
  or generated support file, stop and rewrite the approach instead of shifting
  the debt.
- If direct owner imports introduce an unresolvable import cycle or require a
  schema redesign rather than import rewiring, stop and document the blocker
  rather than diluting the boundary.
- If the focused contract test cannot define a clear production-import allowlist
  from live code, stop and capture the ambiguity before implementation
  continues.
- If the final verification stack passes only after weakened tests, narrower
  gates, or skipped suites, do not close the milestone.

## Local Commit Closeout Policy

- Close this milestone with one local atomic commit after all required gates
  pass.
- Include code, tests, governance config, this plan, and the updated handoff
  and architecture index in that same commit.
- Stage only the verified schema-facade slice. Do not include unrelated dirty
  worktree changes from other hotspot packets.
- Mark the implementation complete only after the commit exists locally and the
  closeout docs record the actual verification commands and results.

## Residual Risks And Next Milestone Routing

If the compact compatibility facade still appears in the architecture-quality
top set after closeout, treat `IC-24F3558D6091` as reduced and route the next
paydown from fresh post-closeout evidence rather than reopening this plan with
schema redesign scope. The most likely follow-ons after a real facade reduction
are:

- residual agent-task service ownership in `app/services/agent_tasks.py`
- oversized agent-task test hotspots such as
  `tests/unit/test_agent_tasks_api.py` or
  `tests/unit/test_agent_task_context.py`

Choose the next packet only after the refreshed post-closeout architecture
summary, improvement-case summary, and import-fan-in evidence are recorded in
the handoff.
