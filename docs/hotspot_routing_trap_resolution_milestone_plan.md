# Hotspot Routing Trap Resolution Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved through the 2026-05-18 durable closeout through the routed
architecture-quality overlay, structured hotspot-routing metadata, measurement
and import alignment, and durable-doc closeout. The live routed backlog has
since advanced through
`docs/residual_large_file_backlog_milestone_plan.md` to the current
cross-cutting child queue, so treat this packet as resolved-local routing
infrastructure rather than as the next active bounded implementation brief.
Owner context: stale-prioritization mechanical debt in the governance and
routing layer after the hotspot-prevention, cycle, agent-task residual,
evidence, CLI, schema, and DB-model facade closeouts. The scoped weakness is
not that the closed facades grew broad again. The weakness is that the raw
architecture-quality routing path still promotes several already-reduced
compatibility facades as if they were the next implementation targets.

## Purpose

Resolve the stale hotspot-routing trap so future sessions stop reopening the
wrong files.

The draft baseline for this packet showed a system with strong owner splits and
prevention gates, but a governance layer that still routed from the wrong
evidence source:

- `app/architecture_quality.py` turned raw churn-and-size hotspots directly
  into improvement candidates and summary paths.
- `app/services/improvement_case_intake.py` imported those raw candidate paths
  verbatim.
- `docs/boring_change_architecture_milestone_plan.md` already says several of
  those paths are routing traps rather than the true next work.
- `config/improvement_cases.yaml` already records that multiple selected
  facades are deployed or reduced, yet the raw summary still surfaces them.

This packet resolves that mechanical debt by making hotspot routing
owner-aware while preserving the raw measurement surfaces needed for historical
trend tracking.

## 2026-05-18 Local Closeout Update

All four milestones are now resolved locally in the current checkout:

- `config/hotspot_prevention.yaml` and `app/hotspot_prevention_policy.py` now
  carry structured routing metadata and validation for the known stale-facade
  trap set, including `app/db/models.py`, `app/services/evidence.py`,
  `app/services/agent_task_actions.py`, `app/cli.py`,
  `app/schemas/agent_tasks.py`, `app/services/agent_tasks.py`,
  `app/services/agent_task_context.py`, `app/services/search.py`, and
  `app/services/claim_support_policy_impacts.py`.
- `app/architecture_quality.py` now preserves raw hotspot measurement output
  while exposing routed hotspot annotations, `top_routed_hotspot_paths`,
  `routing_trap_paths`, `stale_facade_hotspot_count`,
  `raw_improvement_case_candidates`, and a routed
  `improvement_case_candidates` queue.
- `app/architecture_measurement_contracts.py`,
  `app/architecture_measurements.py`, and `app/architecture_inspection.py` now
  publish the routed summary fields through the architecture-governance
  contracts instead of leaving them as implicit local-only report details.
- `app/services/improvement_case_intake.py` now imports only the routed
  architecture-quality candidate queue while preserving the routing metadata in
  source notes for auditability.

Live verification from the local closeout slice:

- `uv run docling-system-architecture-quality-report --summary` now reports
  `top_routed_hotspot_paths` as
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`, and
  `app/api/main.py`, while the raw measurement list still begins with
  `app/db/models.py`, `app/cli.py`, `app/services/agent_task_actions.py`,
  `app/services/evidence.py`, and `app/schemas/agent_tasks.py`.
- The compact routed summary now records `routing_trap_paths` for
  `app/db/models.py`, `app/cli.py`, `app/services/agent_task_actions.py`,
  `app/services/evidence.py`, `app/schemas/agent_tasks.py`,
  `tests/unit/test_cli.py`, and `app/services/agent_tasks.py`, with
  `stale_facade_hotspot_count=7`. The regenerated default 20-hotspot report
  artifact extends that routed-trap list with
  `app/services/agent_task_context.py`, `app/services/search.py`, and
  `app/services/claim_support_policy_impacts.py`, bringing the full-report
  `stale_facade_hotspot_count` to `10` while preserving the same routed next
  queue.
- `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
  now reports `candidate_count=12`, `imported_count=1`, and `skipped_count=11`,
  proving that the routed import path no longer tries to recreate the stale
  facade queue and now skips an already-governed architecture artifact instead
  of reopening it under a new report-specific source ref.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  still reports `0` Python cycle components and `17` code files above `800`,
  which means the next packet should return to the residual large-file backlog
  rather than reopen the now-routed facade traps.
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` passed at
  `2083 passed`.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-18
local / 2026-05-18 UTC:

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
  ?? docs/python_cycle_backlog_elimination_milestone_plan.md
  ...plus active service-family implementation files

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=496.06
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

docs/boring_change_architecture_milestone_plan.md
  The current hotspot summary still routes
  app/db/models.py, app/services/agent_task_actions.py, app/cli.py,
  app/schemas/agent_tasks.py, and app/services/evidence.py, but those are now
  small compatibility facades or already-routed owner families rather than the
  primary >800-line blockers. That makes them routing traps, not the first
  files to reopen.
```

Repo-current structural evidence after the local closeout:

- `app/architecture_quality.py` now keeps raw hotspot scoring intact while
  exposing a routed overlay, `top_routed_hotspot_paths`,
  `routing_trap_paths`, `stale_facade_hotspot_count`, and
  `raw_improvement_case_candidates`.
- `app/services/improvement_case_intake.py` now imports only the routed
  `improvement_case_candidates` queue and preserves route metadata in source
  notes.
- `config/hotspot_prevention.yaml` plus
  `app/hotspot_prevention_policy.py` now carry structured reroute metadata for
  the known facade traps, including successor case IDs, routed owner paths, and
  routed plan paths.
- `config/improvement_cases.yaml` still carries the pre-existing routed owner
  cases for the reduced facades, and the architecture-quality dry-run import no
  longer proposes a duplicate open case for an artifact that is already governed
  by another active architecture-governance case.
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` now agree that the next
  routed bounded packet is `docs/residual_large_file_backlog_milestone_plan.md`.
- The architecture probe still reports `0` Python cycle components and `17`
  code files above `800`, while the post-close-gap rerun kept
  `uv run docling-system-hygiene-check` at `new hygiene regressions: none`,
  `uv run docling-system-hotspot-prevention-check --strict` at `blocked=0`,
  `uv run docling-system-architecture-inspect` at `valid=true`,
  `uv run docling-system-capability-contracts` at `valid=true`, and the focused
  governance alignment slice at `96 passed`, so this packet did not shift the
  debt into a new oversized helper, new cycle, or relaxed governance boundary.

## Goal

Resolve the routing-trap debt so that:

- raw architecture-quality scoring remains available for longitudinal
  measurement and auditability
- routed governance output becomes explicit and owner-aware
- already-reduced or deployed compatibility facades are not selected as the
  next implementation packet unless the live repo state proves they are still
  the honest next owner surface
- the architecture-quality report, improvement-case import path, and durable
  coordination docs agree on the same routed next-work queue
- future sessions can tell the difference between a high-fan-in compatibility
  facade and the actual large or mixed owner family that should be edited next

## Non-Goals

- No reopening of the active DB-model residual owner-family packet.
- No reopening of the evidence, agent-task, schema, or CLI compatibility facade
  implementation work unless the new routed output proves one of those facades
  truly regressed.
- No rewrite of the raw hotspot risk formula solely to hide churn.
- No deletion of raw hotspot measurements, raw hotspot rows, or raw
  `top_hotspot_paths` without an explicit schema-versioned replacement.
- No broad service, API, CLI, or DB refactor outside the governance surfaces
  needed to correct routing.
- No weakening of architecture-quality, hotspot-prevention, hygiene, or
  improvement-case gates just to make the routed output look cleaner.

## Scope

In scope:

- `app/architecture_quality.py`
- `app/architecture_measurements.py`
- `app/architecture_measurement_contracts.py`
- `app/services/improvement_case_intake.py`
- `app/hotspot_prevention_policy.py`
- `config/hotspot_prevention.yaml`
- `config/improvement_cases.yaml` only for structured follow-on metadata or
  aligned case lifecycle updates required by this packet
- focused governance tests such as
  `tests/unit/test_architecture_quality.py`,
  `tests/unit/test_improvement_case_intake.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `tests/unit/test_hotspot_prevention_family_rules.py`,
  `tests/unit/test_hotspot_prevention_wrapper_rules.py`,
  and any new focused routing test siblings introduced by this packet
- routing and coordination docs:
  `docs/hotspot_routing_trap_resolution_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/architecture_boundaries.md`,
  `docs/architecture_contract_map.json`

Out of scope:

- changing implementation ownership inside `app/db/model_domains/*.py`,
  `app/services/evidence_*.py`, `app/services/agent_actions/*.py`,
  `app/cli_commands/*.py`, or `app/schemas/agent_task_*.py`
- re-ranking the repo’s broader `>800` backlog by hand in docs without
  updating the actual routing surfaces
- replacing the current improvement-case registry with a new system

## Owner Surfaces

- raw hotspot report generation:
  `app/architecture_quality.py`
- measurement history and summary propagation:
  `app/architecture_measurements.py`,
  `app/architecture_measurement_contracts.py`
- architecture-quality import surface:
  `app/services/improvement_case_intake.py`
- known-facade routing registry:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_policy.py`
- owner-case lifecycle evidence:
  `config/improvement_cases.yaml`
- durable routing docs:
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/architecture_boundaries.md`,
  `docs/architecture_contract_map.json`

## Placement Rules

- Keep raw hotspot scoring and raw hotspot rows in `app/architecture_quality.py`
  as the measurement baseline. Do not silently repurpose the raw fields into
  routed output.
- Add owner-aware routing as an explicit overlay, not as an undocumented tweak
  to the risk score formula.
- Prefer extending `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_policy.py` with structured routing metadata because
  that policy already owns the known compatibility-facade map and preferred
  owner-module families.
- Keep `config/improvement_cases.yaml` as lifecycle and follow-on evidence, not
  as the only source of routing truth embedded in prose notes.
- Keep `improvement_case_candidates` as the operational candidate list consumed
  by import tooling; if raw candidates must remain visible, expose them under a
  separate clearly named report field.
- If new tests are required, add focused routing tests such as
  `tests/unit/test_architecture_quality_routing.py` rather than broadening the
  existing generic quality or intake tests into another mixed governance root.
- Do not make docs the only place where reroute knowledge lives. The report and
  policy surfaces must carry enough structured data that another session can
  regenerate the same routing result mechanically.

## Proposed Routed Output Contract

Milestone 0 should start from this default contract unless live implementation
constraints prove a narrower variant is needed:

- raw measurement surface remains:
  `hotspots`, `top_hotspot_paths`, `max_hotspot_risk_score`
- each hotspot row gains routing annotations such as:
  `routing_status`, `route_reason`, `route_to_case_ids`, `route_to_paths`,
  `route_to_plan_paths`, and `selected_for_routed_queue`
- summary gains routed governance fields such as:
  `top_routed_hotspot_paths`, `routing_trap_paths`,
  `stale_facade_hotspot_count`
- `improvement_case_candidates` becomes the routed candidate set used by
  `app/services/improvement_case_intake.py`
- if raw candidate preservation is required for auditability, expose it under a
  separate explicit field such as `raw_improvement_case_candidates`

Default routing statuses for Milestone 0 design:

- `active_owner`: the raw hotspot is still the honest next work surface
- `compatibility_facade_trap`: the raw hotspot is a reduced or deployed facade
  and should route to narrower owner surfaces or follow-on cases
- `deferred_reduced_facade`: the raw hotspot remains open but is not the next
  selected packet because larger or more mixed owners take precedence
- `accepted_residual`: the path still has residual debt but is intentionally
  governed by another active packet or documented follow-on

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet hides raw hotspot evidence by mutating the risk formula instead of adding an explicit routed overlay. | `app/architecture_quality.py`, `app/architecture_measurement_contracts.py`, routing tests | focused architecture-quality unit tests plus schema readback | `top_hotspot_paths` changes semantics without an explicit routed companion field or schema contract update | Temporarily rewrite the summary to expose only routed paths and confirm the contract test fails | A future session “fixes” stale routing by erasing the raw evidence source |
| Routing knowledge lives only in prose notes and cannot be regenerated mechanically. | `config/hotspot_prevention.yaml`, `app/hotspot_prevention_policy.py`, routing docs | policy validation, focused routing tests, docs review | A known reduced facade is marked as a routing trap without structured successor metadata | Add a trap status for `app/services/evidence.py` without `route_to_case_ids` or `route_to_paths` and confirm the policy or routing test fails | A future session must read hand-written notes to guess what the real next owner is |
| Improvement-case import still opens or refreshes the raw facade path after the report marks it as a trap. | `app/services/improvement_case_intake.py`, architecture-quality report contract, intake tests | focused intake tests and dry-run import of the generated report | `artifact_target_path` for a routed candidate still points to the stale facade path when successor routing exists | Feed a report where `app/db/models.py` is marked `compatibility_facade_trap` with routed DB-model owner paths and confirm the intake rejects or reroutes the raw facade candidate | A future session runs the import command and recreates the wrong owner case |
| The routed overlay suppresses a facade that truly regressed and should still block changes. | `config/hotspot_prevention.yaml`, `app/architecture_quality.py`, hotspot-prevention tests | hotspot-prevention strict mode plus routed hotspot tests | A facade with new blocked implementation growth cannot appear as routed work or governance warning | Add new command implementation to `app/cli.py` or ORM ownership to `app/db/models.py` and confirm the strict gate still fails even if the path is usually a routing trap | A future session exploits the routing overlay to sneak broad logic back into a protected facade |
| Docs drift from the routed report and keep telling future sessions to read the raw top-hotspot list as the next work queue. | `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `docs/boring_change_architecture_milestone_plan.md`, `docs/architecture_boundaries.md` | doc consistency review, `git diff --check`, focused grep/readback | The report exposes routed fields but the durable docs still instruct future sessions to select the next packet from raw `top_hotspot_paths` | Leave the docs pointing at raw summary-only routing and confirm Milestone 3 cannot close | A future session sees the new report fields but keeps following the stale older docs |
| The current dirty worktree causes this packet to overwrite or misroute active unrelated implementation. | this plan, `docs/SESSION_HANDOFF.md`, current worktree state | Milestone 0 freshness readback and staged-slice review | The packet starts code work before isolating the active docs/governance slice or before refreshing the live report | Begin implementation without regenerating the report or isolating the dirty slice and confirm Milestone 0 blocks continuation | A future session lands governance changes on top of unrelated active service splits and corrupts routing evidence |

## Milestone Sequence

### Milestone 0 - Freshness And Trap Inventory

Outcome label: resolved

Purpose: freeze the live routing-trap baseline and keep this packet queued
behind the live routed backlog until the governance slice is isolated.

Required work:

- Re-run the architecture-quality summary and full report generation, the
  architecture probe, hotspot-prevention strict mode, improvement-case summary,
  and improvement-case validation.
- Capture the live raw top-hotspot list and the live larger `>800` owner
  backlog in this plan.
- Confirm the active bounded packet matches the live
  `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md` queue
  before governance implementation starts, rather than silently making this
  routing packet active too early from stale prose.
- Inventory every known compatibility-facade trap that the live raw summary
  still surfaces, including at minimum:
  `app/db/models.py`, `app/services/evidence.py`, `app/services/agent_task_actions.py`,
  `app/cli.py`, and `app/schemas/agent_tasks.py`.
- Decide and record the exact routed-output contract and structured metadata
  shape this packet will use.

Acceptance criteria:

- This plan records the live raw `top_hotspot_paths`, the stale-facade trap
  set, and the true active packet queue.
- The selected routing metadata shape is explicit before implementation starts.
- The packet stays queued until the active dirty worktree can isolate the
  governance slice cleanly.

Closeout note:

- The implemented slice captured the live routing-trap baseline, isolated the
  governance packet from unrelated in-flight owner work, and then advanced the
  routed queue to `docs/residual_large_file_backlog_milestone_plan.md`.

### Milestone 1 - Structured Route-Trap Registry And Parser Gate

Outcome label: resolved

Purpose: give known hotspot facades explicit structured reroute metadata before
the report or import surfaces change behavior.

Required work:

- Extend `config/hotspot_prevention.yaml` with structured routing metadata for
  known facades that can become stale-routing traps.
- Update `app/hotspot_prevention_policy.py` validation and loading so the new
  routing metadata is schema-checked and testable.
- Record successor owner evidence for at minimum:
  `app/db/models.py`,
  `app/services/evidence.py`,
  `app/services/agent_task_actions.py`,
  `app/cli.py`, and
  `app/schemas/agent_tasks.py`.
- Add focused tests that fail if a trap-classified facade lacks structured
  reroute metadata.

Acceptance criteria:

- The hotspot-prevention policy can represent known routing traps and their
  successor owner surfaces without relying on prose-only notes.
- Policy validation fails if a trap-classified facade is missing required
  reroute metadata.
- No existing hotspot-prevention rule or exception behavior regresses.

Closeout note:

- The structured policy now routes the known facade traps mechanically, and the
  focused policy tests plus `docling-system-hotspot-prevention-check --strict`
  remain green without adding new exceptions.

### Milestone 2 - Routed Architecture-Quality Report And Summary

Outcome label: resolved

Purpose: resolve stale-prioritization at the report layer by separating raw
measurement from routed governance output.

Required work:

- Update `app/architecture_quality.py` so raw hotspot scoring stays intact while
  routed hotspot selection becomes an explicit overlay.
- Annotate hotspot rows with structured routing status and successor metadata.
- Add routed summary fields that future sessions can safely use for next-packet
  selection.
- Make `improvement_case_candidates` owner-aware so routed candidates no longer
  point to stale facades when a narrower routed owner exists.
- Add focused unit coverage for:
  raw versus routed summary behavior,
  trap classification,
  deferred reduced facades,
  and legitimate active-owner regression cases.

Acceptance criteria:

- Raw `top_hotspot_paths` remains available as measurement output.
- The report also exposes routed governance fields sufficient to select the next
  implementation packet without reading prose docs.
- Facades such as `app/db/models.py`, `app/services/evidence.py`,
  `app/services/agent_task_actions.py`, and `app/schemas/agent_tasks.py` do not
  appear in `top_routed_hotspot_paths` when their routed owner surfaces are
  still the honest next work.
- `app/cli.py` appears in `top_routed_hotspot_paths` only if the live repo
  state proves it is still the true next owner surface rather than a reduced
  forwarding facade with larger blockers elsewhere.

Closeout note:

- The compact routed summary now keeps the raw top-hotspot list unchanged while
  routing next-work selection through
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`, and
  `app/api/main.py`; the reduced facades are now recorded explicitly in
  `routing_trap_paths`.

### Milestone 3 - Improvement-Case Import, Measurement History, And Durable Adoption

Outcome label: resolved

Purpose: finish the routing-trap packet by aligning import, measurement, and
coordination docs around the routed queue.

Required work:

- Update `app/services/improvement_case_intake.py` so architecture-quality
  import consumes routed candidates correctly and preserves raw audit details in
  source notes where needed.
- Update `app/architecture_measurements.py` and
  `app/architecture_measurement_contracts.py` so routed summary fields are
  captured without breaking raw historical measurement continuity.
- Refresh `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/architecture_boundaries.md`, and
  `docs/architecture_contract_map.json` so future sessions use the routed queue
  rather than the raw top-hotspot list for next-packet selection.
- Regenerate the architecture-quality report artifact and dry-run the
  architecture-quality improvement-case import against it.

Acceptance criteria:

- Architecture-quality import no longer proposes a stale facade path when the
  report marks that facade as a routing trap with successor metadata.
- Measurement history and summary contracts preserve raw fields and include the
  routed governance fields added by this packet.
- Durable docs point future sessions at routed hotspot output for packet
  selection.
- The final routed output and durable docs agree on the next queue named by the
  live handoff or index state instead of the raw hotspot list.

Closeout note:

- The final dry-run import now reports `candidate_count=12`, `imported_count=1`,
  and `skipped_count=11` because the routed import path now treats an existing
  active architecture-governance artifact case as already governed instead of
  proposing a duplicate case under a new report-specific source ref.

## Required Implementation Artifacts

- `docs/hotspot_routing_trap_resolution_milestone_plan.md`
- updated report and measurement surfaces:
  `app/architecture_quality.py`,
  `app/architecture_measurements.py`,
  `app/architecture_measurement_contracts.py`
- updated import surface:
  `app/services/improvement_case_intake.py`
- updated hotspot policy parser and config:
  `app/hotspot_prevention_policy.py`,
  `config/hotspot_prevention.yaml`
- aligned lifecycle registry data when needed:
  `config/improvement_cases.yaml`
- focused routing tests, including a new routing-specific unit suite if needed
- refreshed report artifact:
  `build/architecture-governance/architecture_quality_report.json`

## Required Documentation And Handoff Updates

- Update this plan with milestone status, verification, and closeout commit
  hashes as each milestone lands.
- Update `docs/SESSION_HANDOFF.md` when this packet moves from queued to active,
  closes, or when the routed next-work queue changes.
- Update `docs/agentic_architecture_index.md` when this packet becomes the
  selected bounded follow-on or closes.
- Update `docs/boring_change_architecture_milestone_plan.md` so the umbrella
  coordination brief points to routed hotspot output instead of treating the raw
  top-hotspot list as the operational queue.
- Update `docs/architecture_boundaries.md` and
  `docs/architecture_contract_map.json` if the architecture-quality report
  contract or summary fields change.

## Required Verification Gates

- Milestone 0 refresh:
  `git status -sb`
  `uv run docling-system-architecture-quality-report --summary`
  `uv run docling-system-architecture-quality-report --output-path build/architecture-governance/architecture_quality_report.json`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  `uv run docling-system-hotspot-prevention-check --strict`
  `uv run docling-system-improvement-case-summary`
  `uv run docling-system-improvement-case-validate`
  `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
- Implementation milestones:
  `git diff --check`
  `uv run ruff check app/architecture_quality.py app/architecture_measurements.py app/architecture_measurement_contracts.py app/hotspot_prevention_policy.py app/services/improvement_case_intake.py tests/unit/test_architecture_quality*.py tests/unit/test_improvement_case_intake.py tests/unit/test_hotspot_prevention*.py config/hotspot_prevention.yaml config/improvement_cases.yaml`
  `uv run pytest -q tests/unit/test_architecture_quality.py tests/unit/test_architecture_quality_routing.py tests/unit/test_improvement_case_intake.py tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py`
  `uv run docling-system-architecture-quality-report --output-path build/architecture-governance/architecture_quality_report.json`
  `uv run docling-system-architecture-quality-report --summary`
  `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
  `uv run docling-system-improvement-case-summary`
  `uv run docling-system-improvement-case-validate`
  `uv run docling-system-hotspot-prevention-check --strict`
  `uv run docling-system-hygiene-check`
  `uv run docling-system-architecture-inspect`
  `uv run docling-system-capability-contracts`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- Final confidence gate:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- Raw architecture-quality measurement remains intact and auditable.
- Routed governance output exists and is explicit enough to select the next
  packet mechanically.
- The routed queue no longer promotes already-reduced or deployed compatibility
  facades as the default next implementation target when narrower routed owners
  remain active.
- `improvement_case_candidates` and the improvement-case import path align with
  routed owner surfaces rather than stale facade paths.
- The hotspot-prevention policy schema can represent routing traps and successor
  owner surfaces mechanically.
- The handoff, architecture index, umbrella coordination brief, and report
  contract all agree on how to select the next routed packet.

## Stop Conditions

- Stop if raw hotspot fields are consumed by external repo automation that
  cannot be updated in the same milestone and no backward-compatible routed
  overlay can be added.
- Stop if the only available source of reroute truth is freeform prose in
  `deployment.notes` rather than structured config or report fields.
- Stop if implementation would require reopening active owner-family code rather
  than correcting the governance surfaces themselves.
- Stop if the current dirty worktree cannot isolate the governance slice from
  unrelated active implementation.
- Stop before commit if routed output only looks cleaner because tests, import
  rules, or gates became weaker.

## Local Commit Closeout Policy

Every milestone is complete only after verification passes, the required docs
and handoff updates land, and a local atomic commit records the milestone
slice. Before that point the milestone is ready-to-close, not complete.

For each milestone:

- stage only the verified hotspot-routing-governance slice
- leave unrelated dirty or untracked service-family implementation alone
- include code, config, tests, regenerated report artifacts, and doc or handoff
  updates that describe the milestone in the same commit
- record closeout commit hashes in this plan and in `docs/SESSION_HANDOFF.md`
- do not claim the routing debt is resolved if the raw report still drives the
  operational queue through stale facade paths

## Residual Risks And Next Milestone Routing

- This packet is now durably recorded in the 2026-05-18 closeout.
- If Milestone 0 shows a narrower pre-existing governance surface already owns
  routed hotspot selection, retire this packet and route that exact owner
  surface instead of widening scope.
- The current routed bounded implementation brief is now
  `docs/documents_service_boundary_milestone_plan.md` in the historical
  sequence captured by this packet, followed by
  `docs/cross_cutting_verification_roots_milestone_plan.md` and
  `docs/improvement_case_governance_self_hosting_milestone_plan.md`; all three
  are now also resolved locally in the current checkout.
- After this packet closes, use `top_routed_hotspot_paths` and
  `routing_trap_paths` for packet selection. Keep `top_hotspot_paths` as a raw
  measurement surface, not the operational queue.

## Closeout Checklist

- [x] Milestone 0 freshness readback captured and the live trap inventory is explicit
- [x] Structured route-trap metadata exists for the known stale facades
- [x] Routed architecture-quality summary and candidate generation are implemented
- [x] Improvement-case import consumes routed candidates correctly
- [x] Measurement contracts preserve raw fields and add routed governance fields
- [x] Handoff, architecture index, coordination brief, and architecture contract docs are aligned
- [x] Regenerated architecture-quality report and dry-run import reflect the routed queue
- [x] Atomic closeout commit recorded for each completed milestone
