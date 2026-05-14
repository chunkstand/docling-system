# Architecture Governance Cycle Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: resolved locally through closeout commit `7a4c5b0` after
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
`docs/evaluations_service_boundary_milestone_plan.md`,
`docs/evidence_provenance_exports_boundary_milestone_plan.md`,
`docs/semantics_service_boundary_milestone_plan.md`,
`docs/cli_command_dispatch_boundary_milestone_plan.md`,
`docs/agent_task_schema_aggregation_boundary_milestone_plan.md`,
`docs/oversized_test_hotspots_boundary_milestone_plan.md`, and
`docs/hygiene_owner_case_routing_boundary_milestone_plan.md`; those prior
packets are now closed locally, the hygiene owner-case routing packet is
closed locally through closeout commit `9876f67`, it has bound explicit owner
cases for the residual governance files, Milestone 0 live refresh is resolved
locally through baseline commit `46b90a7`, Milestone 1 gate-first
architecture import contract is resolved locally through checkpoint `4338d4e`,
the minimal contract-only seam already removed the targeted
architecture-governance cycle component, and Milestone 4 closeout has now
realigned the next active slice to
`docs/runtime_health_orchestration_milestone_plan.md`
Owner context: resolved closeout packet for the architecture-governance owner
family. `IC-08C078FD4F45` remains the residual owner anchor for
`app/architecture_inspection.py`, `app/architecture_inspection_rules.py`,
`app/services/improvement_case_intake.py`, and
`app/services/improvement_cases.py` because those governed files still exceed
the configured hygiene budget even though the cycle-removal slice is closed.

## Local Progress

Milestone 0 is resolved locally through baseline commit `46b90a7`.
`IC-08C078FD4F45` is now confirmed as the live architecture-governance owner
case across both `config/improvement_cases.yaml` and
`config/hygiene_policy.yaml`, the exact post-stack architecture-control cycle
baseline is frozen from the current probe output, and Milestone 1 gate-first
architecture import contract is resolved locally through checkpoint `4338d4e`.
The gate landed through a shared architecture contract catalog in `app/`, one
improvement-case contract metadata module under the existing improvement-case
owner family, one agent-action contract metadata module under the existing
agent-action owner family, a focused AST import-boundary test, and refreshed
contract-map artifacts. The post-change architecture probe now reports only
four Python cycle components instead of the Milestone 0 baseline of five, and
the removed component is the targeted architecture-governance cycle containing
`app.architecture_decisions`, `app.architecture_inspection`,
`app.architecture_inspection_rules`, `app.hygiene`, and
`app.services.improvement_case_intake`. This packet is now resolved locally
through closeout commit `7a4c5b0`. Milestone 4 closeout revalidated architecture
inspection, capability contracts, improvement-case routing, hygiene, hotspot
prevention, and the architecture probe; the remaining global cycle backlog is
now the four non-governance components for the
search/documents/evaluations/runs/semantics family, claim-support policy
impacts/promotions, evidence-provenance export graph, and evidence-search
packages/trace-store. The next active stacked follow-on is
`docs/runtime_health_orchestration_milestone_plan.md` Milestone 0 refresh /
owner-case bootstrap.

## Purpose

Resolve the remaining coupling debt inside the architecture-governance tooling:

- `app/architecture_inspection.py` still reaches into runtime-oriented service
  modules to build contract metadata
- `app/architecture_decisions.py` still lazily imports
  `app.architecture_inspection` to discover expected contracts
- the architecture probe still reports a Python cycle component containing
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake`

The scoped problem is not simply "there are still three cycle components." The
specific weakness is that the governance tooling meant to inspect architecture
boundaries still depends on runtime-heavy service modules and on recursive
inspection/decision discovery. That makes the governance layer harder to trust,
harder to refactor, and easier for future sessions to "fix" with local-import
masking instead of clearer ownership.

This packet resolves that scoped knot by introducing only the minimal
contract-only seams required to remove the architecture-governance cycle
component, keep public inspection and decision entrypoints stable, and stop
`architecture_inspection` from importing full runtime service owners directly.

## Current Evidence

Live repo evidence refreshed at the Milestone 0 baseline on 2026-05-14 local /
2026-05-14 UTC:

```text
git status -sb
  ## main...origin/main [ahead 52]

uv run docling-system-improvement-case-summary
  case_count=36
  status_counts.open=25
  status_counts.deployed=10
  status_counts.measured=1
  measured_case_count=31
  oldest_open_case_id=IC-9812A0B138D9

uv run docling-system-improvement-case-validate
  valid=true
  issue_count=0

uv run docling-system-architecture-inspect
  valid=true
  violation_count=0

uv run docling-system-capability-contracts
  valid=true
  facade_count=6
  function_count=110

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycles:
    app.architecture_decisions, app.architecture_inspection,
    app.architecture_inspection_rules, app.hygiene,
    app.services.improvement_case_intake
    app.services.chat, app.services.search,
    app.services.search_execution_persistence,
    app.services.search_hydration
    app.services.claim_support_policy_impacts,
    app.services.claim_support_replay_alert_promotions
    app.services.evidence_provenance_export_graph_core,
    app.services.evidence_provenance_export_graph_report
    app.services.evidence_search_packages,
    app.services.evidence_search_trace_store
  Python import fan out:
    app.architecture_inspection = 12 local modules
  Largest governance files:
    app/architecture_inspection.py = 412 lines
    app/architecture_inspection_rules.py = 604 lines
    app/services/improvement_case_intake.py = 820 lines
  Top hotspot:
    app/services/search.py = score 50944

rg -n "IC-08C078FD4F45|app/architecture_inspection.py|app/architecture_inspection_rules.py|app/services/improvement_case_intake.py|app/services/improvement_cases.py" config/improvement_cases.yaml config/hygiene_policy.yaml
  config/hygiene_policy.yaml:
    app/architecture_inspection.py -> owner_case_id=IC-08C078FD4F45
    app/architecture_inspection_rules.py -> owner_case_id=IC-08C078FD4F45
    app/services/improvement_case_intake.py -> owner_case_id=IC-08C078FD4F45
    app/services/improvement_cases.py -> owner_case_id=IC-08C078FD4F45
  config/improvement_cases.yaml:
    IC-08C078FD4F45 remains the live architecture-governance owner case

rg -n "build_agent_task_action_manifest|list_improvement_case_import_source_specs|list_improvement_case_import_sources|validate_architecture_decisions|validate_agent_task_action_contracts|inspect_architecture_contracts|build_architecture_contract_map" app/architecture_inspection.py app/architecture_inspection_rules.py app/architecture_decisions.py app/hygiene.py app/services/improvement_case_intake.py
  app/architecture_decisions.py:
    _default_expected_contracts() lazily imports
    app.architecture_inspection.build_architecture_contract_map
  app/architecture_inspection.py imports:
    app.services.agent_task_actions.build_agent_task_action_manifest
    app.services.improvement_case_intake.list_improvement_case_import_sources
    app.services.improvement_case_intake.list_improvement_case_import_source_specs
  app/architecture_inspection_rules.py imports:
    app.architecture_decisions.validate_architecture_decisions
    app.services.agent_task_actions.validate_agent_task_action_contracts
  app/hygiene.py:
    run_architecture_contract_checks() imports
    app.architecture_inspection.inspect_architecture_contracts
```

Repo-current structural evidence:

- `IC-08C078FD4F45` already exists as the live architecture-governance owner
  case in both the registry and hygiene policy, so this packet must reuse it
  rather than create a duplicate case family.
- the exact architecture-control cycle component is still
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake`; Milestone 0 must freeze that
  baseline before code motion begins
- `app/architecture_inspection.py` is the public inspection and contract-map
  entrypoint, but today it imports full runtime surfaces just to assemble
  manifest data for `agent_action_catalog` and `improvement_case_intake`.
- `app/architecture_decisions.py` currently discovers default expected
  contracts by importing `build_architecture_contract_map()` from the
  inspection module, which creates the recursive dependency that the probe
  still reports.
- `app/architecture_inspection_rules.py` validates architecture decisions and
  agent action contracts directly against those runtime owners instead of
  against a narrower contract-only metadata seam.
- `docs/boring_change_architecture_milestone_plan.md` already names this
  architecture-control cycle in its broader cycle milestone. This packet is the
  dedicated owner-level follow-on so the broader plan can later consume a
  reduced cycle backlog instead of still owning this slice directly.
- `docs/hygiene_owner_case_routing_boundary_milestone_plan.md` already routes
  the architecture-governance family through explicit owner cases as a prior
  dependency. This packet must reuse that live owner routing instead of opening
  a second case family for the same files.

## Goal

Resolve the scoped architecture-governance coupling debt so that:

- `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake` no longer appear in the same Python
  cycle component
- `app/architecture_decisions.py` no longer imports
  `app.architecture_inspection`, even lazily, to discover expected contracts
- `app/architecture_inspection.py` no longer imports
  `app.services.improvement_case_intake` or `app.services.agent_task_actions`
  directly for contract metadata
- architecture inspection, decision validation, and measurement/report
  generation still produce the same public machine-readable artifacts
- the scoped governance-cycle issue is `resolved` even if the global probe still
  reports the other non-governance cycle components

## Non-Goals

- No attempt to remove all three current Python cycle components in this
  packet.
- No search-family or evidence-search cycle work here.
- No new runtime service split for `app/services/improvement_case_intake.py`,
  `app/services/agent_task_actions.py`, or `app/services/architecture_governance.py`.
- No API, CLI, DB, worker, or route contract redesign.
- No local-import masking as the primary cycle fix.
- No new generic `app/architecture_utils.py`, `app/services/contracts.py`, or
  other broad sink that just relocates the same coupling.
- No reopening of the prior hygiene owner-case routing packet except to reuse
  its live owner case IDs during Milestone 0.

## Scope

In scope:

- Milestone 0 post-stack refresh after the earlier queued packets close
- reuse of the live architecture-governance owner case created or bound by the
  hygiene owner-case routing packet
- contract-first extraction of the minimum shared metadata needed to break the
  governance cycle
- decoupling `app/architecture_decisions.py` from
  `app/architecture_inspection.py`
- decoupling `app/architecture_inspection.py` from runtime-heavy service
  modules used only for contract discovery
- focused architecture-governance import and contract tests
- refreshed `docs/architecture_contract_map.json` and
  `docs/architecture_decision_map.json` if the metadata source moves
- handoff and architecture-index updates for the new stacked order

Out of scope:

- the remaining global cycle components outside the architecture-governance
  family
- broad large-file cleanup across `app/` or `tests/`
- CI gate parity or broader boring-change workflow work
- claim-support, evaluations, evidence, semantics, CLI, schema, or test-hotspot
  refactors already owned by earlier queued packets

## Owner Surfaces

- `app/architecture_inspection.py`
- `app/architecture_inspection_rules.py`
- `app/architecture_decisions.py`
- `app/architecture_measurements.py`
- `app/hygiene.py`
- `app/services/improvement_case_intake.py`
- `app/services/agent_task_actions.py`
- `app/services/architecture_governance.py`
- `app/services/capabilities/system_governance.py`
- `tests/unit/test_architecture_inspection.py`
- `tests/unit/test_architecture_decisions.py`
- `tests/unit/test_improvement_case_intake.py`
- `tests/unit/test_architecture_quality.py`
- `tests/unit/test_agent_action_contracts.py`
- `tests/unit/test_api_architecture.py`
- `docs/architecture_contract_map.json`
- `docs/architecture_decision_map.json`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml` only if the live owner case notes or ratchets
  need to be refreshed after the code motion
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

## Placement Rules

- Keep `app/architecture_inspection.py` and `app/architecture_decisions.py` as
  the public entrypoints and CLI-owning surfaces. Do not replace them with a
  new orchestration facade.
- If new modules are required, allow at most three lightweight contract-only
  owner modules total:
  - one shared architecture contract catalog under `app/`
  - one improvement-case import contract metadata module under the existing
    improvement-case owner family
  - one agent-action contract metadata module under the existing agent-action
    owner family
- Any new module created by this packet must remain contract-only:
  metadata, schema references, expected contract names, or import-source
  descriptors. No DB sessions, FastAPI app creation, task execution, or runtime
  orchestration bodies may move into those new files.
- Do not shift runtime work into `app/services/architecture_governance.py` or
  `app/services/capabilities/system_governance.py` just to hide the imports.
  Those route-facing service seams must stay narrow.
- Reuse the owner case introduced by
  `docs/hygiene_owner_case_routing_boundary_milestone_plan.md`. If Milestone 0
  finds that no such case exists yet, stop and finish that packet first rather
  than creating a duplicate architecture-governance case here.
- Do not grow `tests/unit/test_architecture_inspection.py` or
  `tests/unit/test_architecture_decisions.py` into the next monolith. If the
  import-boundary assertions become too broad, add one focused
  `tests/unit/test_architecture_governance_imports.py` and stop there.

## Weak-Point Prevention Contract

Freshness check: before implementation begins, rerun
`uv run docling-system-improvement-case-summary`,
`uv run docling-system-improvement-case-validate`,
`uv run docling-system-architecture-inspect`,
`uv run docling-system-capability-contracts`, and
`python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`.
If the architecture-governance owner case or cycle set already changed after
the prior stacked packets close, refresh this plan before editing code.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet starts from stale post-stack routing and binds to the wrong owner case | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `config/improvement_cases.yaml` | Milestone 0 refresh plus manual owner-case readback | the architecture-governance family from the hygiene packet does not exist yet, or a conflicting live case already owns the same files and this plan does not reconcile it first | refresh after prior packets close and verify the owner case before code edits | a future session implements the cycle fix against this draft while the hygiene packet is still open or has already changed the owner routing |
| The cycle disappears only because imports were hidden, not because ownership improved | `app/architecture_decisions.py`, `app/architecture_inspection.py`, `app/architecture_inspection_rules.py`, focused import tests, architecture probe output | targeted AST import tests plus architecture probe readback | the cycle count drops only because of local-import masking or undocumented runtime indirection | add a temporary local import inside a helper and confirm the focused import test or review rejects the fake fix | a future session optimizes for a green probe by moving imports inside functions and leaves the same ownership knot intact |
| Contract metadata is pushed into a new broad sink or into route-facing services | any new contract-only module, `app/services/architecture_governance.py`, `app/services/capabilities/system_governance.py` | `wc -l` readback in closeout review plus focused unit tests | more than three new modules appear, or route-facing governance services grow new metadata-orchestration bodies | prototype a new `app/services/contracts.py` or expanded `system_governance.py` diff and reject it during review | a future session keeps `architecture_inspection.py` shorter by moving everything into a generic governance helper file |
| Breaking the recursive contract discovery drifts the persisted architecture maps | `docs/architecture_contract_map.json`, `docs/architecture_decision_map.json`, architecture inspection and decisions tests | `uv run pytest -q tests/unit/test_architecture_inspection.py tests/unit/test_architecture_decisions.py` plus map regeneration/readback | contract names, decision links, or persisted maps drift from the new shared catalog | add a temporary contract entry without refreshing the maps and confirm the tests fail | a future session changes the contract catalog and forgets to regenerate the committed map artifacts |
| Runtime-service coupling remains through direct manifest discovery imports | `app/architecture_inspection.py`, `app/architecture_inspection_rules.py`, focused import tests | AST-based import checks plus `uv run docling-system-architecture-inspect` | `architecture_inspection.py` still imports `app.services.improvement_case_intake` or `app.services.agent_task_actions` directly at closeout | add one direct import back temporarily and confirm the focused import test fails | a future session adds "just one more manifest helper" from the runtime owner because the architecture module already imported it once |

## Milestone Sequence

### Milestone 0 - Refresh the post-stack state and bind the live owner case

Status: resolved locally through baseline commit `46b90a7`

Outcome label: reduced

Purpose: do not implement this packet against stale queue state. Confirm that
the hygiene owner-case routing packet has already created or bound the
architecture-governance owner case, then freeze the current cycle baseline and
live dependency map before code motion begins.

Implementation:

- Rerun:
  - `git status -sb`
  - `uv run docling-system-improvement-case-summary`
  - `uv run docling-system-improvement-case-validate`
  - `uv run docling-system-architecture-inspect`
  - `uv run docling-system-capability-contracts`
  - `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  - `rg -n "architecture_inspection|architecture_inspection_rules|improvement_case_intake" config/improvement_cases.yaml`
- Confirm that the earlier hygiene routing packet has already bound an explicit
  owner case for the architecture-governance family and record that case ID in
  this plan, the handoff, and the architecture index.
- Freeze the current global cycle baseline and the exact architecture-control
  cycle component from the probe output.
- Run the architecture-quality, hotspot-prevention, and hygiene gates so the
  refreshed baseline proves the packet is not forming a new hotspot or shifting
  debt into adjacent owner surfaces before Milestone 1 begins.
- If Milestone 0 finds that the owner case does not yet exist, stop and close
  the hygiene owner-case routing packet first instead of creating a duplicate
  case here.

Acceptance signal:

- The plan names the live owner case that this packet is working under.
- The architecture-control cycle component is captured from the post-stack
  baseline before implementation begins.
- Architecture-quality, hotspot-prevention, and hygiene remain green, so the
  refreshed baseline does not create new hotspots or shift debt into other
  governed surfaces.

Local result:

- confirmed the hygiene owner-case routing packet is already closed locally
  through `9876f67`, so this packet now reuses the live owner case
  `IC-08C078FD4F45` instead of creating a duplicate architecture-governance
  case family
- confirmed `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
  both route `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`, and
  `app/services/improvement_cases.py` through `IC-08C078FD4F45`
- refreshed the current 2026-05-14 post-stack baseline and froze the exact
  architecture-control cycle component as
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake`
- updated this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` so Milestone 1 gate-first architecture
  import contract is now the next active code-changing slice

Local verification:

- `git status -sb`: clean worktree at baseline start commit `6867004`; local
  `main` ahead of `origin/main` by `52`
- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`,
  `oldest_open_case_id=IC-9812A0B138D9`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `known_hotspots=21`, `changed_hotspots=0`, `blocked=0`, `allowed=0`,
  `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`;
  inherited budget debt stays routed through explicit owner cases rather than
  new milestone labels
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; Python cycle components=`5`; the
  architecture-control cycle component still contains
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake`
- `rg -n "IC-08C078FD4F45|app/architecture_inspection.py|app/architecture_inspection_rules.py|app/services/improvement_case_intake.py|app/services/improvement_cases.py" config/improvement_cases.yaml config/hygiene_policy.yaml`:
  registry and hygiene-policy hits both confirm `IC-08C078FD4F45` owns the
  four governed architecture-governance files

### Milestone 1 - Add the gate-first architecture import contract

Outcome label: reduced

Purpose: make the misuse pattern executable before large code motion. The repo
must fail if governance tooling keeps importing runtime owners directly or if
`architecture_decisions` falls back to importing inspection again.

Implementation:

- Add focused AST-based contract coverage that proves:
  - `app/architecture_decisions.py` does not import
    `app.architecture_inspection`
  - `app/architecture_inspection.py` does not import
    `app.services.improvement_case_intake` or
    `app.services.agent_task_actions` directly
  - the allowed architecture-governance metadata imports stay limited to the
    new contract-only seams introduced by this packet
- Place this gate in the existing architecture test family if it stays narrow.
  If not, allow one focused `tests/unit/test_architecture_governance_imports.py`.
- Update `app/architecture_inspection_rules.py` only if the most durable gate
  belongs in the machine-checked architecture rule manifest rather than in a
  pure unit test.

Acceptance signal:

- There is a failing contract test path for direct governance-to-runtime
  imports before the full refactor finishes.
- The gate is precise enough to block the old coupling pattern without
  broadening unrelated architecture rules.

Local result:

- added `tests/unit/test_architecture_governance_imports.py` so AST-based
  contract coverage now fails if `app/architecture_decisions.py` imports
  `app.architecture_inspection` or if `app/architecture_inspection.py`
  imports `app.services.improvement_case_intake` or
  `app.services.agent_task_actions` directly, including local-import masking
- added `app/architecture_contract_catalog.py` so default expected contract
  discovery is shared and `app/architecture_decisions.py` no longer imports
  `app.architecture_inspection`
- added `app/services/improvement_case_contracts.py` so improvement-case
  import-source schema names, source descriptors, and source-path capabilities
  are available to architecture tooling without importing the runtime intake
  service owner directly
- added `app/services/agent_actions/contracts.py` so the architecture contract
  map can build `agent_action_catalog` metadata without importing
  `app.services.agent_task_actions` directly
- updated `app/architecture_inspection.py` to consume the new contract-only
  seams and refreshed `docs/architecture_contract_map.json` so the emitted
  machine-readable map now records
  `app.services.improvement_case_contracts` and
  `app.services.agent_actions.contracts` as the metadata sources
- added a parity assertion in `tests/unit/test_agent_action_contracts.py` so
  the contract-only manifest stays aligned with the runtime
  `build_agent_task_action_manifest()` output
- removed the targeted architecture-governance cycle component earlier than
  the original staging assumed: the post-change architecture probe now reports
  four Python cycle components and no longer lists the
  `app.architecture_decisions` / `app.architecture_inspection` /
  `app.architecture_inspection_rules` / `app.hygiene` /
  `app.services.improvement_case_intake` component

Local verification:

- `git diff --check`: pass
- `uv run ruff check app/architecture_contract_catalog.py app/architecture_inspection.py app/architecture_inspection_rules.py app/architecture_decisions.py app/architecture_measurements.py app/hygiene.py app/services/improvement_case_contracts.py app/services/improvement_case_intake.py app/services/agent_actions/contracts.py app/services/agent_task_actions.py app/services/architecture_governance.py app/services/capabilities/system_governance.py tests/unit/test_architecture_governance_imports.py tests/unit/test_architecture_inspection.py tests/unit/test_architecture_decisions.py tests/unit/test_improvement_case_intake.py tests/unit/test_architecture_quality.py tests/unit/test_agent_action_contracts.py tests/unit/test_api_architecture.py`: pass
- `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_architecture_inspection.py tests/unit/test_architecture_decisions.py tests/unit/test_improvement_case_intake.py tests/unit/test_architecture_quality.py tests/unit/test_agent_action_contracts.py tests/unit/test_api_architecture.py`: `80 passed`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`, `facade_count=6`, `function_count=110`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=36`, `status_counts.open=25`, `status_counts.deployed=10`, `status_counts.measured=1`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`; `app/architecture_inspection.py` now sits exactly at its `412`-line ratchet ceiling and `app/services/improvement_case_intake.py` at `818` lines under its `820`-line ratchet ceiling
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=21`, `changed_hotspots=0`, `blocked=0`, `allowed=0`, `exceptions=0`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`: Python cycle components=`4` and the targeted architecture-governance cycle component is gone
- `uv run docling-system-architecture-inspect --write-map`: refreshed `docs/architecture_contract_map.json`
- `uv run docling-system-architecture-decisions --write-map`: refreshed `docs/architecture_decision_map.json`

### Milestone 2 - Extract shared contract metadata and remove recursive discovery

Outcome label: reduced

Current local state: subsumed by local checkpoint `4338d4e`. The shared architecture contract catalog, improvement-case
contract metadata module, and agent-action contract metadata module already
removed recursive contract discovery for this scoped packet, so no separate
Milestone 2 code slice remains before closeout.

Purpose: break the inspection-to-decisions recursion through a shared contract
catalog rather than through local-import tricks.

Implementation:

- Introduce only the minimum contract-only metadata seams allowed by
  `Placement Rules`.
- Move expected contract-name discovery out of
  `app/architecture_inspection.py` so `app/architecture_decisions.py` can get
  default expected contracts without importing inspection.
- Move improvement-case import-source contract metadata and agent-action
  contract metadata behind lightweight contract-only owners so the architecture
  tooling can discover schemas, source descriptors, and manifest vocabulary
  without importing full runtime orchestration services.
- Update `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/architecture_decisions.py`, and any touched tests to use the new shared
  contract metadata source.
- Regenerate `docs/architecture_contract_map.json` and
  `docs/architecture_decision_map.json` if the shared catalog changes those
  emitted artifacts.

Acceptance signal:

- `app/architecture_decisions.py` no longer imports
  `app.architecture_inspection`.
- Shared contract discovery comes from explicit contract-only owners rather than
  from runtime service modules.

### Milestone 3 - Break the architecture-governance cycle and remove runtime reachthrough

Outcome label: resolved

Current local state: subsumed by local checkpoint `4338d4e`. The post-change architecture probe no longer lists the
targeted architecture-governance cycle component, and
`app/architecture_inspection.py` no longer imports
`app.services.improvement_case_intake` or
`app.services.agent_task_actions` directly.

Purpose: close the scoped debt by making the architecture-control cycle
disappear from the probe and by leaving the inspection tooling independent from
runtime service modules used only for manifest discovery.

Implementation:

- Update `app/architecture_inspection.py` so it no longer imports
  `app.services.improvement_case_intake` or
  `app.services.agent_task_actions` directly.
- Keep `app/services/architecture_governance.py` and
  `app/services/capabilities/system_governance.py` behavior-stable while the
  internals move onto contract-only seams.
- Preserve public machine-readable outputs for:
  - `build_architecture_contract_map(...)`
  - `build_architecture_inspection_report(...)`
  - `validate_architecture_decisions(...)`
  - architecture measurement summaries and report generation
- Re-run the architecture probe and confirm the cycle component containing
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake` is gone.
- Treat the other two global cycle components as residual follow-on work owned
  by the broader boring-change lane.

Acceptance signal:

- The architecture probe no longer lists the architecture-governance cycle
  component.
- The total Python cycle component count drops by at least one from the
  Milestone 0 baseline.
- `app/architecture_inspection.py` no longer imports the two runtime-heavy
  service owners directly.

### Milestone 4 - Close out the packet and realign the stacked route

Outcome label: resolved

Current local state: resolved locally through closeout commit `7a4c5b0`. `uv run
docling-system-architecture-inspect` and `uv run
docling-system-capability-contracts` remain valid, `uv run
docling-system-hotspot-prevention-check --strict` stays at
`changed_hotspots=0`, `blocked=0`, and the remaining Python cycle backlog is
reduced to four non-governance components: the
search/documents/evaluations/runs/semantics family,
`app.services.claim_support_policy_impacts` /
`app.services.claim_support_replay_alert_promotions`,
`app.services.evidence_provenance_export_graph_core` /
`app.services.evidence_provenance_export_graph_report`, and
`app.services.evidence_search_packages` /
`app.services.evidence_search_trace_store`. The next stacked follow-on is
`docs/runtime_health_orchestration_milestone_plan.md` Milestone 0 because no
dedicated runtime-health owner case exists yet.

Purpose: finish with aligned docs, refreshed evidence, and a clear reduced
global cycle backlog.

Implementation:

- Refresh:
  - `uv run docling-system-architecture-inspect`
  - `uv run docling-system-capability-contracts`
  - `uv run docling-system-improvement-case-validate`
  - `uv run docling-system-improvement-case-summary`
  - `uv run docling-system-hygiene-check`
  - `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- Update this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` with the final cycle count, owner case,
  and next queued packet.
- If the broader `docs/boring_change_architecture_milestone_plan.md` still
  claims ownership of this architecture-control cycle slice after closeout,
  update that plan in the same commit so it reflects the reduced residual
  cycle backlog instead of duplicating ownership.

Acceptance signal:

- The closeout docs no longer route this cycle family through the broader
  boring-change plan as if it were still unclaimed.
- The remaining global cycle backlog is clearly reduced to the non-governance
  components.

## Required Implementation Artifacts

- Updated architecture-governance code in:
  `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/architecture_decisions.py`, and any required supporting contract-only
  modules
- Updated or new focused architecture import tests
- Refreshed `docs/architecture_contract_map.json` if contract-map metadata moved
- Refreshed `docs/architecture_decision_map.json` if expected contract discovery
  moved
- `config/improvement_cases.yaml` only if the live architecture-governance
  owner case notes, measurement, or lifecycle state need a closeout update
- `config/hygiene_policy.yaml` only if the touched governance files need
  refreshed ratchets after the code motion

## Required Documentation And Handoff Updates

- Update this plan with final status, live cycle readings, and closeout commit
- Update `docs/SESSION_HANDOFF.md`
- Update `docs/agentic_architecture_index.md`
- Update `docs/boring_change_architecture_milestone_plan.md` only if it still
  duplicates the closed architecture-control cycle slice after closeout
- Update the owner case in `config/improvement_cases.yaml` if the live
  architecture-governance owner status or notes change

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/architecture_inspection.py app/architecture_inspection_rules.py app/architecture_decisions.py app/architecture_measurements.py app/hygiene.py app/services/improvement_case_intake.py app/services/agent_task_actions.py app/services/architecture_governance.py app/services/capabilities/system_governance.py tests/unit/test_architecture_inspection.py tests/unit/test_architecture_decisions.py tests/unit/test_improvement_case_intake.py tests/unit/test_architecture_quality.py tests/unit/test_agent_action_contracts.py tests/unit/test_api_architecture.py`
- `uv run pytest -q tests/unit/test_architecture_inspection.py tests/unit/test_architecture_decisions.py tests/unit/test_improvement_case_intake.py tests/unit/test_architecture_quality.py tests/unit/test_agent_action_contracts.py tests/unit/test_api_architecture.py`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `uv run docling-system-architecture-inspect --write-map` or the repo-equivalent map refresh command if the contract map changed
- `uv run docling-system-architecture-decisions --write-map` if the decision map changed

## Acceptance Criteria

- The architecture probe no longer lists a cycle component containing
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake`.
- The total Python cycle component count is at least one lower than the
  Milestone 0 baseline.
- `app/architecture_decisions.py` no longer imports
  `app.architecture_inspection`.
- `app/architecture_inspection.py` no longer imports
  `app.services.improvement_case_intake` or
  `app.services.agent_task_actions` directly.
- No more than three new contract-only modules are introduced, and no new broad
  metadata sink is created.
- Public architecture inspection, decision validation, and measurement/report
  outputs remain behavior-compatible and machine-readable.
- Docs, maps, owner-case notes, and handoff updates land in the same atomic
  closeout commit as the code and tests.

## Stop Conditions

- Milestone 0 shows the hygiene owner-case routing packet is still incomplete
  for the architecture-governance family.
- The only available cycle fix is local-import masking or another opacity
  pattern that does not improve ownership clarity.
- Breaking the cycle would require broad redesign of public governance routes,
  runtime APIs, or agent-task execution beyond the scoped owner surfaces.
- The implementation starts expanding into the remaining search-family or
  evidence-search cycle components. If that happens, stop and route those
  families through the broader boring-change plan or a dedicated follow-on
  packet instead of widening this one.

## Local Commit Closeout Policy

- Close this packet in one atomic local commit after all verification gates
  pass.
- Include the code, tests, refreshed maps, owner-case updates, this plan, and
  the handoff/index updates in the same commit.
- Do not stage unrelated dirty worktree changes from the active claim-support
  implementation or any other in-flight packet.
- A verified-but-uncommitted cycle reduction is not complete.

## Residual Risks And Next Milestone Routing

- The global probe may still report the remaining search-family and
  evidence-search cycle components after this packet closes. That is acceptable
  for this scoped milestone as long as the architecture-governance cycle is
  gone.
- If the architecture-governance owner files remain large after the cycle break,
  that residual size debt stays with the explicit owner case created by the
  hygiene packet and later broader boring-change coordination.
- After this packet closes, the next queued broader coordination packet remains
  `docs/runtime_health_orchestration_milestone_plan.md`, followed by
  `docs/ci_release_gate_parity_milestone_plan.md`, and then the reduced-scope
  `docs/boring_change_architecture_milestone_plan.md`.
