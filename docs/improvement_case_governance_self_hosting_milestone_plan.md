# Improvement Case Governance Self-Hosting Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved through durable closeout commit `b9b3e46`. The governed
roots now close at `370`, `514`, `552`, `82`, and `218` lines, the local
`app.services.improvement_case_observations` /
`app.services.improvement_cases` cycle remains removed, and the family-local
siblings are now exact-ratcheted under `IC-08C078FD4F45`.
Owner context: residual architecture-governance self-hosting family under
`IC-08C078FD4F45`. The selected excerpt understates the live family: the
current governed owner set is `app/architecture_inspection.py`,
`app/architecture_inspection_rules.py`,
`app/services/improvement_case_intake.py`,
`app/services/improvement_cases.py`, and
`tests/unit/test_improvement_case_intake.py`, with family-local siblings now
closed out in the same packet.

## Purpose

Resolve the remaining self-hosting debt in the improvement-case and
architecture-governance stack without reopening the already-closed cycle or
hotspot-routing packets as vague repo-wide cleanup.

The current weakness is not only size. The family still carries mixed
ownership, stale registry measurements, and partially extracted local siblings
whose routing and bounded ownership are not yet closed out. The packet exists
to finish that split cleanly, keep the removed cycle from regrowing, and leave
the governance system capable of governing itself with smaller, family-local
owners and stronger bounded tests.

## 2026-05-18 Closeout Update

- The governed roots now measure `370`, `514`, `552`, `82`, and `218` lines
  across `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`, and
  `tests/unit/test_improvement_case_intake.py`.
- Family-local siblings now close at `122`, `184`, `475`, `279`, `277`,
  `101`, `122`, and `551` lines across
  `app/services/improvement_case_architecture_quality.py`,
  `app/services/improvement_case_models.py`,
  `app/services/improvement_case_registry.py`,
  `app/services/improvement_case_observations.py`,
  `app/services/improvement_case_report_imports.py`,
  `app/architecture_inspection_rule_contracts.py`,
  `tests/unit/test_improvement_case_intake_contracts.py`, and
  `tests/unit/test_improvement_case_intake_reports.py`.
- `config/improvement_cases.yaml` now records `IC-08C078FD4F45` as
  `deployed` through durable closeout commit `b9b3e46` with a refreshed family
  max of `552`, while
  `config/hygiene_policy.yaml` exact-ratchets the governed roots and the new
  siblings so the split cannot silently regrow.
- The live architecture probe still reports `0` Python cycle components and
  `0` code files above `800`, the focused governance unit packet passed at
  `80 passed`, and the packet-local Ruff gate stayed green.

## Current Evidence

- `uv run docling-system-improvement-case-summary` still reports
  `case_count=59` and `cause_class_counts.unclear_ownership=57`, while the
  routed governance owner case now advances from `open` to `deployed`
  in `config/improvement_cases.yaml` through closeout commit `b9b3e46`.
- Live `wc -l` in the current dirty checkout measures
  `app/architecture_inspection.py` at `370`,
  `app/architecture_inspection_rules.py` at `514`,
  `app/services/improvement_case_intake.py` at `552`,
  `app/services/improvement_cases.py` at `82`, and
  `tests/unit/test_improvement_case_intake.py` at `218`.
- `config/improvement_cases.yaml` now records the refreshed family max at
  `552` and the same-packet sibling counts, so the routed case reflects the
  live post-split family instead of a stale pre-closeout snapshot.
- `config/hygiene_policy.yaml` now exact-ratchets the governed roots plus the
  family-local siblings created or retained by this packet under
  `IC-08C078FD4F45`.
- The live checkout now contains exact-ratcheted family-local siblings:
  `app/services/improvement_case_architecture_quality.py` at `122` lines,
  `app/services/improvement_case_models.py` at `184`,
  `app/services/improvement_case_registry.py` at `475`,
  `app/services/improvement_case_observations.py` at `279`,
  `app/services/improvement_case_report_imports.py` at `277`,
  `app/architecture_inspection_rule_contracts.py` at `101`,
  `tests/unit/test_improvement_case_intake_contracts.py` at `122`, and
  `tests/unit/test_improvement_case_intake_reports.py` at `551`.
- The live architecture probe still reports `0` Python cycle components after
  the local `app.services.improvement_case_observations` /
  `app.services.improvement_cases` cycle removal, so the split did not shift
  the debt back into a hidden local-import loop.
- `app/services/improvement_case_contracts.py` already exists as a narrow
  `99`-line source-contract seam. This packet should build around that stable
  contract surface instead of routing more responsibilities back through the
  cycle.
- Focused verification now passes across the family:
  `uv run ruff check ...` is green for the packet surfaces and
  `uv run pytest -q ...` passed at `80 passed` across the governance-family
  intake, registry, CLI, architecture-inspection, and import-boundary roots.

## Goal

Resolve the governance self-hosting debt so that:

- `app/architecture_inspection.py` closes at or below `400` lines
- `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`, and
  `tests/unit/test_improvement_case_intake.py` all close at or below `600`
  lines
- `app/services/improvement_cases.py` and
  `app/services/improvement_case_intake.py` end as narrow family-local registry
  or orchestration owners rather than mixed sinks
- no Python import cycle remains anywhere in the improvement-case family
- any new sibling between `401` and `600` lines receives same-milestone routing
  and an exact hygiene ratchet
- any new support file stays at or below `400` lines and remains family-local
- CLI, report-import, registry-validation, and architecture-rule contracts stay
  equivalent or stronger than today
- `IC-08C078FD4F45`, `config/hygiene_policy.yaml`, the handoff, and the
  routing docs all reflect the live post-split family instead of stale
  pre-closeout measurements

The scoped issue is `resolved` when the governed family is under budget, the
cycle is gone, the self-hosting seams are explicit, and the durable routing
artifacts describe the live family honestly.

## Non-Goals

- No reopening of the already-routed `documents.py` packet or the selected
  cross-cutting verification packet.
- No broad rewrite of the architecture-quality report pipeline, hotspot
  prevention workflow, or raw improvement-case registry schema.
- No duplication of `IC-08C078FD4F45` unless Milestone 0 proves the current
  owner case cannot honestly represent the narrowed family.
- No generic `app/services/utils.py`, `tests/support.py`, or broad conftest
  sink for moved governance helpers.
- No weakening of CLI boundary behavior, report-import validation, source-path
  contracts, registry validation, or cycle-detection tests just to get a green
  closeout.

## Scope

In scope:

- `app/architecture_inspection.py`
- `app/architecture_inspection_rules.py`
- `app/services/improvement_case_contracts.py`
- `app/services/improvement_case_intake.py`
- `app/services/improvement_cases.py`
- `app/services/improvement_case_architecture_quality.py`
- `app/services/improvement_case_observations.py`
- focused new siblings such as
  `app/services/improvement_case_registry.py`,
  `app/services/improvement_case_summary.py`,
  `app/services/improvement_case_import_paths.py`,
  `app/services/improvement_case_import_sources.py`, or
  `app/architecture_inspection_rule_*.py` if Milestone 0 confirms they are the
  clean split points
- `app/improvement_case_intake_cli.py` and
  `app/cli_commands/improvement_cases.py` only as needed to preserve caller
  contracts
- `tests/unit/test_improvement_cases.py`
- `tests/unit/test_improvement_case_intake.py`
- `tests/unit/test_improvement_case_intake_contracts.py`
- focused new siblings such as
  `tests/unit/test_improvement_case_intake_sources.py`,
  `tests/unit/test_improvement_case_intake_reports.py`, or
  `tests/unit/test_improvement_case_intake_runner.py`
- `tests/unit/test_cli_improvement_cases.py`
- `tests/unit/test_architecture_inspection.py`
- `tests/unit/test_architecture_quality.py`
- `tests/unit/test_architecture_quality_routing.py`
- `tests/unit/test_architecture_governance_imports.py`
- `tests/unit/test_python_cycle_imports.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- the parent routing and handoff docs that must queue this packet correctly

Out of scope:

- `app/services/documents.py`
- `tests/unit/test_agent_task_verifications.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/integration/test_search_harness_releases.py`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py`
- stale shared-verification routing unrelated to the improvement-case family
- broader repo-wide cycle cleanup outside the governed self-hosting family

## Owner Surfaces

- the governed `IC-08C078FD4F45` family surfaces listed above
- any focused family-local siblings created by the packet
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
- CLI entrypoints or callers that expose the improvement-case registry or
  import workflow
- routing docs and the canonical handoff

## Placement Rules

- Preserve `app/services/improvement_case_contracts.py` as the typed
  source-contract seam for import-source capabilities. Do not move source-path
  or DB-session policy back into the CLI entrypoints.
- Keep observation collectors in
  `app/services/improvement_case_observations.py` or narrower
  family-local siblings, not in `app/services/improvement_cases.py`.
- If shared Pydantic models or helper primitives are needed to break the new
  cycle, move them into a narrow family-local module such as
  `app/services/improvement_case_models.py` or
  `app/services/improvement_case_registry_models.py` rather than hiding the
  cycle behind local imports.
- Keep architecture-quality report parsing in
  `app/services/improvement_case_architecture_quality.py` or a narrower
  family-local sibling, not in `app/services/improvement_case_intake.py`.
- Keep `app/services/improvement_case_intake.py` as the orchestration facade or
  runner surface. Move source selection, path validation, or file-report
  collectors into named family-local siblings when they no longer fit.
- Preserve the public architecture-rule APIs
  `list_architecture_rules`, `build_architecture_rule_manifest`, and
  `collect_architecture_rule_violations` even if
  `app/architecture_inspection_rules.py` becomes a narrow registry facade over
  rule-family siblings.
- Keep intake tests family-local. Do not move improvement-case import coverage
  into unrelated architecture, CLI, or generic support files.
- Any new focused sibling between `401` and `600` lines must receive
  same-milestone routing and an exact hygiene ratchet. No new support file may
  exceed `400` lines.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet trusts stale case measurements and preserves the wrong family boundary. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, packet docs | Milestone 0 `wc -l`, improvement-case summary, doc review | the plan or registry still describe stale pre-closeout family measurements after rebaseline | leave the old counts in the registry notes and confirm review rejects the packet | future Codex resumes from stale prose instead of the live checkout |
| The new split “fixes” size by creating or hiding a Python cycle. | `app/services/improvement_cases.py`, `app/services/improvement_case_observations.py`, shared model or helper siblings | `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`, import-boundary tests | any cycle remains in the improvement-case family after closeout | keep the bottom-level reciprocal imports and confirm the cycle gate fails | future Codex moves helpers across files without breaking shared-type ownership cleanly |
| `app/services/improvement_case_intake.py` shrinks by dropping source-path, file-report, or DB-session contract coverage. | intake owners, intake tests, CLI import entrypoints | focused unit tests plus CLI import tests | source-path validation, report-path validation, or DB-session selection becomes weaker | remove one invalid source-path rejection and confirm focused tests fail | future Codex optimizes for size and deletes negative-path import coverage |
| `app/architecture_inspection_rules.py` splits into a registry that no longer exposes the same public rule APIs or manifest behavior. | rule modules and `tests/unit/test_architecture_inspection.py` | architecture inspection unit tests plus architecture-governance import tests | `list_architecture_rules`, `build_architecture_rule_manifest`, or rule collection drift or disappear | stub one rule-family module without wiring it into the manifest and confirm tests fail | future Codex narrows the file but forgets the caller-visible inspection contract |
| The packet creates a new generic utility or support sink instead of explicit family-local owners. | new `app/services/improvement_case_*.py` siblings and new `tests/unit/test_improvement_case_*` siblings | `wc -l` readback, hygiene check, routing review | any new catch-all utility or support file exceeds `400` or carries multiple unrelated families | dump shared helpers into `tests/support.py` or a 650-line utility module and confirm closeout rejects it | future Codex uses “support” as a loophole to hide the same self-hosting debt |

## Milestone Sequence

### Milestone 0. Live Rebaseline And Case Scope Lock
Outcome label: reduced

Refresh the live governed family, confirm which in-progress sibling files are
real split points, and lock the exact self-hosting boundary before further code
motion.

This milestone must:

- rerun `uv run docling-system-improvement-case-summary`
- rerun `wc -l` for the governed family
- rerun `architecture_probe.py --fail-on-cycles`
- inventory the current candidate siblings already present in the dirty
  checkout
- refresh the `IC-08C078FD4F45` notes if the live family no longer matches the
  older registry measurement
- stop if overlapping local edits cannot be separated safely from this packet

### Milestone 1. Registry And Observation Boundary Plus Cycle Guard
Outcome label: reduced

Finish the `app/services/improvement_cases.py` split while preserving the
removed cycle break between `app/services/improvement_cases.py` and
`app/services/improvement_case_observations.py`.

Preferred outcomes include:

- `app/services/improvement_case_observations.py` remains the owner for
  observation collectors
- shared models or helper primitives move to a cycle-free family-local module
  if both sides need them
- `app/services/improvement_cases.py` becomes a narrow registry or validation
  owner instead of a mixed collector, summary, and recording sink
- `tests/unit/test_improvement_cases.py` stays under budget and proves the new
  registry boundary

### Milestone 2. Intake Import Boundary And Verification Root Split
Outcome label: reduced

Reduce `app/services/improvement_case_intake.py` and
`tests/unit/test_improvement_case_intake.py` into explicit family-local owners
without weakening source-path, file-report, DB-session, or CLI contracts.

Preferred outcomes include:

- preserving or extending `app/services/improvement_case_architecture_quality.py`
- extracting source-path validation or source-selection helpers into
  family-local intake siblings
- preserving `tests/unit/test_improvement_case_intake_contracts.py` as the
  contract-focused root
- moving report-, source-, and runner-specific cases into focused
  `tests/unit/test_improvement_case_intake_*.py` siblings
- keeping `tests/unit/test_cli_improvement_cases.py` green without routing the
  CLI around the service boundary

### Milestone 3. Architecture Rule Family Boundary
Outcome label: reduced

Reduce `app/architecture_inspection_rules.py` while keeping the public rule
registry and manifest contracts stable and keeping `app/architecture_inspection.py`
at or below its tighter `400`-line budget.

Preferred outcomes include:

- rule-family siblings such as `app/architecture_inspection_rule_*.py`
- a narrow rule-registry facade in `app/architecture_inspection_rules.py`
- no caller-visible drift in manifest generation or rule execution order

### Milestone 4. Routing And Self-Hosting Closeout
Outcome label: resolved

Close the packet only after:

- the governed family is within budget
- the cycle is gone
- the registry, hygiene policy, and routing docs describe the live family
  honestly
- focused unit and import-boundary verification are green

## Required Implementation Artifacts

- narrowed governance-family service and rule owners
- any new family-local siblings required to remove the cycle or split the
  intake and rule owners
- focused governance-family test roots
- refreshed `IC-08C078FD4F45` registry measurement or same-milestone successor
  routing if Milestone 0 proves one is required

## Required Documentation And Handoff Updates

- `docs/improvement_case_governance_self_hosting_milestone_plan.md`
- `docs/cross_cutting_large_file_residual_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/boring_change_architecture_milestone_plan.md` if the queue wording
  changes
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/architecture_inspection.py app/architecture_inspection_rules.py app/services/improvement_case*.py app/improvement_case_intake_cli.py app/cli_commands/improvement_cases.py tests/unit/test_improvement_case*.py tests/unit/test_cli_improvement_cases.py tests/unit/test_architecture_inspection.py tests/unit/test_architecture_quality.py tests/unit/test_architecture_quality_routing.py tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`
- `uv run pytest -q tests/unit/test_improvement_cases.py tests/unit/test_improvement_case_intake.py tests/unit/test_improvement_case_intake_reports.py tests/unit/test_improvement_case_intake_contracts.py tests/unit/test_cli_improvement_cases.py tests/unit/test_architecture_inspection.py tests/unit/test_architecture_quality.py tests/unit/test_architecture_quality_routing.py tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --format markdown --top 20`

## Acceptance Criteria

- `app/architecture_inspection.py` closes at or below `400` lines.
- `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`, and
  `tests/unit/test_improvement_case_intake.py` all close at or below `600`
  lines.
- No Python cycle remains in the improvement-case self-hosting family.
- No new sibling created by this packet exceeds `600` lines, and no new support
  file exceeds `400` lines.
- `app/services/improvement_case_contracts.py` remains the stable typed
  source-contract seam for import sources.
- The focused intake, registry, CLI import, and architecture-rule test slices
  pass without weaker assertions, broader skips, or narrower negative-path
  coverage.
- `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, and the routed
  docs no longer describe stale pre-closeout family measurements as the live
  measurement.

## Stop Conditions

- Stop if Milestone 0 shows the dirty checkout already contains conflicting
  user-owned governance-family edits that cannot be separated safely.
- Stop if keeping the cycle broken requires reopening a broader repo-wide cycle
  packet instead of a family-local boundary fix.
- Stop if the packet starts routing documents-service or cross-cutting
  verification work into the governance family.
- Stop if the only path to green is to weaken source-path, CLI, registry, or
  rule-manifest coverage.

## Local Commit Closeout Policy

- Close this packet with one atomic local commit containing only the governed
  self-hosting family changes, any new family-local siblings, focused tests,
  routing updates, and the aligned docs or handoff updates for this packet.
- Stage only the verified milestone slice and leave unrelated dirty or
  untracked files alone.
- Treat the packet as ready-to-close, not complete, until that atomic local
  commit exists and its hash is recorded in `docs/SESSION_HANDOFF.md`.

## Residual Risks And Next Milestone Routing

- This packet is now the next active code-owning follow-on after
  `docs/cross_cutting_verification_roots_milestone_plan.md` resolved locally.
  If the local governance family materially changes before implementation
  begins, rerun Milestone 0 instead of trusting this draft.
- If any governed owner honestly remains between `401` and `600` lines after
  the split, keep it explicitly routed under `IC-08C078FD4F45` or a narrower
  same-milestone successor case and record the exact next slice in the handoff.
- After this packet closes, reselect the next under-budget follow-on from
  `docs/boring_change_architecture_milestone_plan.md` and refresh
  `docs/SESSION_HANDOFF.md` instead of reopening the already resolved
  `docs/cross_cutting_large_file_residual_milestone_plan.md` parent packet.
