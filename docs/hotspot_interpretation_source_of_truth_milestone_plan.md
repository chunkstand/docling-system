# Hotspot Interpretation Source Of Truth Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally on 2026-05-18 as the prerequisite docs-and-registry
closeout ahead of the open-owner packet. The routed-hotspot explanation is now
canonical in `docs/architecture_boundaries.md`, queue pointers no longer label
reduced facades as the next active packet, and `IC-9812A0B138D9` now closes as
deployed rather than remaining an ambiguous routed hotspot.
Owner context: residual mechanical debt in the routed-hotspot governance layer
after `docs/hotspot_routing_trap_resolution_milestone_plan.md` resolved the
report overlay. The scoped weakness is no longer how the architecture-quality
report computes routed traps. The weakness is that current human-first queue
surfaces, case lifecycle notes, and queued-plan wording can still drift back
toward the raw facade list, especially around `app/db/models.py`,
`app/cli.py`, `app/services/agent_task_actions.py`, and
`app/services/evidence.py`.

## Purpose

Resolve the remaining hotspot-interpretation debt so future sessions stop
reopening reduced facades even when the raw hotspot list still begins with
them.

The current problem is not a missing routed field. That already exists. The
problem is that the repo still spreads queue truth across several surfaces with
different semantics:

- raw architecture-quality hotspot measurements still lead with reduced
  compatibility facades
- routed hotspot output correctly distinguishes those surfaces as traps
- improvement-case records mix `deployed`, `open`, and retirement-ready states
  that are not always obvious from the first lines a future session reads
- the handoff, architecture index, and queued milestone drafts can drift if
  they restate queue truth instead of clearly pointing at one canonical
  routed-hotspot explanation

This packet exists to make routed hotspot interpretation explicit, durable, and
hard to misread before more owner-family implementation work resumes.

## Current Evidence

- `docs/architecture_boundaries.md` now explains that the raw measurement list
  still begins with `app/db/models.py`, `app/cli.py`,
  `app/services/agent_task_actions.py`, `app/services/evidence.py`, and
  `app/schemas/agent_tasks.py`, while the routed queue now begins elsewhere
  and `stale_facade_hotspot_count=7`.
- `uv run docling-system-architecture-quality-report --summary` currently
  reports `top_hotspot_paths=["app/db/models.py","app/cli.py","app/services/agent_task_actions.py","app/services/evidence.py","app/schemas/agent_tasks.py"]`,
  `routing_trap_paths=["app/db/models.py","app/cli.py","app/services/agent_task_actions.py","app/services/evidence.py","app/schemas/agent_tasks.py","tests/unit/test_cli.py","app/services/agent_tasks.py"]`,
  `top_routed_hotspot_paths=["tests/integration/test_claim_support_judge_evaluation_roundtrip.py","tests/integration/test_technical_report_harness_roundtrip.py","tests/unit/test_hotspot_prevention.py"]`,
  and `stale_facade_hotspot_count=7`.
- `config/hotspot_prevention.yaml` already classifies the known trap surfaces
  with structured routing metadata:
  `app/db/models.py` and `app/services/evidence.py` are
  `compatibility_facade_trap`,
  `app/cli.py`, `app/schemas/agent_tasks.py`, and
  `app/services/agent_tasks.py` are `deferred_reduced_facade`,
  and `app/services/agent_task_actions.py` plus
  `app/services/agent_task_context.py` are explicit compatibility-facade
  traps routed to narrower successors.
- `config/improvement_cases.yaml` now shows the critical trap surfaces in mixed
  lifecycle states:
  `IC-F2A8110185EB` / `app/db/models.py` is `deployed`,
  `IC-050E60059A34` / `app/services/evidence.py` is `deployed`,
  `IC-A1E186A34097` / `app/services/agent_task_actions.py` is `deployed`,
  but `IC-9812A0B138D9` / `app/cli.py` remains `open` even though its notes
  already describe a reduced forwarding facade.
- `docs/open_owner_backlog_resolution_milestone_plan.md` currently targets the
  broader open-owner queue, but its scope explicitly leaves
  `app/db/models.py`, `app/services/evidence.py`, and
  `app/services/agent_task_actions.py` out of scope beyond preserving trap
  status. That makes this interpretation packet a prerequisite if the queue
  itself is still easy to misread.
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` are currently the
  operator-facing queue surfaces most likely to drift if they do not all point
  to the same canonical routed-hotspot explanation.

## Goal

Resolve this debt so that:

- reduced trap surfaces are no longer easy to misread as the next active
  implementation roots
- the repo has one canonical explanation of routed hotspot interpretation and
  all other queue docs point to it instead of restating partial trap lists
- improvement-case lifecycle notes for the trap surfaces match their actual
  routed status
- future sessions can immediately distinguish raw hotspot measurement from the
  real operational queue
- the queued open-owner packet resumes only after the routed-hotspot source of
  truth is stable enough that it will not reopen the wrong facades

The issue is `resolved` when queue consumers, registry consumers, and docs
consumers all see the same routed-trap story without needing prior chat
context.

## Non-Goals

- No reopening of implementation splits already closed for
  `app/db/models.py`, `app/services/evidence.py`,
  `app/services/agent_task_actions.py`, `app/services/agent_task_context.py`,
  `app/schemas/agent_tasks.py`, or `app/services/agent_tasks.py` unless
  Milestone 0 finds real regrowth.
- No rewrite of the raw hotspot risk formula or deletion of
  `top_hotspot_paths`.
- No broad owner-family implementation work for the queued open-owner backlog.
- No weakening of architecture-quality, hotspot-prevention, hygiene, or
  improvement-case gates merely to make the routed output look cleaner.
- No duplicative new architecture queue doc unless Milestone 0 proves the
  existing boundary docs cannot serve as the canonical explanation.

## Scope

In scope:

- `docs/architecture_boundaries.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/hotspot_routing_trap_resolution_milestone_plan.md`
- `docs/open_owner_backlog_resolution_milestone_plan.md`
- `config/hotspot_prevention.yaml`
- `config/improvement_cases.yaml`
- `app/architecture_quality.py`
- `app/architecture_measurements.py`
- `app/architecture_measurement_contracts.py`
- `app/services/improvement_case_intake.py`
- `tests/unit/test_architecture_quality.py`
- `tests/unit/test_improvement_case_intake.py`
- `tests/unit/test_hotspot_prevention.py`
- focused new routing-alignment tests if Milestone 0 proves they are needed

Out of scope:

- new implementation splits inside `app/db/model_domains/`
- evidence owner-family implementation work
- agent-task action or context implementation work
- semantic generation, semantic graph, or runs owner-family implementation
  beyond queue sequencing
- unrelated test-monolith backlog work

## Owner Surfaces

- routed hotspot report and measurement contracts
- hotspot-prevention routing metadata
- improvement-case lifecycle notes for trap surfaces
- operator-facing queue docs and milestone sequencing docs
- the queued open-owner follow-on that depends on this packet’s routing truth

## Placement Rules

- Treat `config/hotspot_prevention.yaml` as the structured registry for known
  trap surfaces and their routed successor paths. Do not duplicate successor
  routing in ad hoc prose without linking back to that registry.
- Treat `config/improvement_cases.yaml` as the lifecycle truth for whether a
  trap surface is `deployed`, `open`, `verified`, or retirement-ready. Do not
  leave a case `open` with notes that already prove it is only a reduced
  compatibility facade unless the remaining issue is explicitly named.
- Keep `docs/architecture_boundaries.md` as the canonical human-readable
  explanation of raw versus routed hotspot semantics unless Milestone 0 proves
  a dedicated queue doc is necessary.
- Keep `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md` as
  queue pointers, not parallel sources of trap-list truth. They should point
  to the canonical explanation and the current next packet rather than repeat
  diverging inventories.
- If code changes are needed, keep them inside the existing
  architecture-quality, measurement-contract, and improvement-intake surfaces.
  Do not create a new generic governance helper sink.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Future sessions still reopen reduced facades because queue docs restate raw hotspots instead of pointing at routed truth. | `docs/architecture_boundaries.md`, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `docs/boring_change_architecture_milestone_plan.md` | Milestone 0 doc review plus final routing-diff audit | two operator-facing docs disagree on the next packet or on whether a trap surface is a real target | leave one doc pointing at `app/cli.py` and another at the routed queue, then confirm the review rejects closeout | future Codex starts from the first stale doc it sees and reopens `app/services/evidence.py` |
| Trap surfaces stay mechanically routed but their improvement cases still read like active monolith debt. | `config/improvement_cases.yaml` | improvement-case summary, validate, and targeted case review | trap cases remain `open` or ambiguous without explicit reduced-facade or successor-language after Milestone 1 | keep `IC-9812A0B138D9` open with monolith wording and confirm the packet stays unresolved | future Codex treats the case title alone as authority and edits the facade |
| Canonical queue truth drifts again because the routed-trap fields exist only in report output and not in durable docs or tests. | `app/architecture_quality.py`, `app/architecture_measurements.py`, `tests/unit/test_architecture_quality.py` | architecture-quality summary plus focused unit tests | routed-trap fields disappear, reorder incorrectly, or stop being documented in the canonical boundary doc | remove `routing_trap_paths` from the summary contract and confirm tests fail | future Codex trusts a stale saved report because no durable docs/test contract remained |
| The queued open-owner follow-on broadens before the interpretation packet closes, leaving two different “next” packets active. | `docs/open_owner_backlog_resolution_milestone_plan.md`, `docs/SESSION_HANDOFF.md` | milestone routing review | the handoff says one next packet while the queued plan still claims it is the active next brief | leave both plans labeled “next” and confirm the routing review fails | future Codex merges queue-selection and owner-family work into one vague cleanup packet |
| New trap surfaces or successor plans are added without structured route metadata. | `config/hotspot_prevention.yaml`, hotspot-prevention tests | hotspot-prevention strict gate plus focused tests | any new trap path lacks route-to case IDs, route-to paths, or route-to plan paths | add a new trap without successor metadata and confirm strict validation fails | future Codex adds another facade exception but forgets where work should actually go |

## Milestone Sequence

### Milestone 0. Live Rebaseline And Canonical Queue Decision
Outcome label: reduced

Refresh the live routed-hotspot state and decide whether
`docs/architecture_boundaries.md` can remain the single canonical explanation
or whether a narrower dedicated queue artifact is required.

This milestone must:

- rerun `uv run docling-system-architecture-quality-report --summary`
- reread the routed-trap section in `docs/architecture_boundaries.md`
- review the lifecycle states for the trap cases in
  `config/improvement_cases.yaml`
- review the current handoff, architecture index, broader coordination brief,
  and queued open-owner plan for conflicting “next packet” wording
- stop if the currently dirty docs-only routing slice cannot be separated
  cleanly from the queued open-owner follow-on

### Milestone 1. Trap Lifecycle And Successor Alignment
Outcome label: reduced

Align the trap-surface lifecycle records so they no longer imply that reduced
facades are active implementation monoliths.

Preferred outcomes include:

- explicit reduced-facade or compatibility-facade wording for
  `IC-F2A8110185EB`, `IC-050E60059A34`, `IC-A1E186A34097`,
  `IC-24F3558D6091`, `IC-4098E8370B88`, and `IC-E52B6C7B22FD`
- either closing or explicitly rerouting `IC-9812A0B138D9` so its remaining
  issue is described as successor-owner or residual-test work rather than
  broad `app/cli.py` ownership
- hotspot-prevention routing metadata that matches the current case lifecycle
  and successor plan paths

### Milestone 2. Canonical Queue Surface And Doc Pointer Alignment
Outcome label: reduced

Reduce queue ambiguity by making one doc the canonical routed-hotspot
explanation and turning the other queue docs into aligned pointers.

Preferred outcomes include:

- `docs/architecture_boundaries.md` becomes the canonical explanation of raw
  versus routed hotspot semantics
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` point to that canonical
  explanation and the active next packet instead of maintaining their own
  divergent trap inventories
- `docs/open_owner_backlog_resolution_milestone_plan.md` is clearly marked as
  queued behind this packet until routed-hotspot interpretation is stable

### Milestone 3. Routing Contract And Regression Gate Hardening
Outcome label: reduced

Add or tighten tests or contract checks so the routed-hotspot interpretation
cannot silently drift again.

Preferred outcomes include:

- focused architecture-quality tests that assert routed-trap fields remain in
  the summary contract
- focused hotspot-prevention or improvement-intake tests that prove trap
  surfaces keep successor metadata and do not reenter import candidates as new
  active cases
- a small doc or routing-alignment check if Milestone 0 proves current tests
  are insufficient to keep queue pointers honest

### Milestone 4. Closeout
Outcome label: resolved

Close the packet only after the routed-hotspot explanation, trap lifecycle
records, and queue pointers all agree on the same operational truth.

## Required Implementation Artifacts

- any focused routing-alignment code or tests required by Milestone 3
- refreshed hotspot-prevention routing metadata
- refreshed improvement-case lifecycle notes for trap surfaces
- updated queue and architecture docs that point to one canonical routed-hotspot explanation

## Required Documentation And Handoff Updates

- `docs/hotspot_interpretation_source_of_truth_milestone_plan.md`
- `docs/architecture_boundaries.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/hotspot_routing_trap_resolution_milestone_plan.md`
- `docs/open_owner_backlog_resolution_milestone_plan.md`
- `config/hotspot_prevention.yaml`
- `config/improvement_cases.yaml`
- `docs/architecture_contract_map.json` if measurement-contract surfaces change

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/architecture_quality.py app/architecture_measurements.py app/architecture_measurement_contracts.py app/services/improvement_case_intake.py tests/unit/test_architecture_quality.py tests/unit/test_improvement_case_intake.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_architecture_quality.py tests/unit/test_improvement_case_intake.py tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- The canonical routed-hotspot explanation is explicit and durable, and every
  queue pointer doc routes through it instead of maintaining conflicting trap
  truth.
- `app/db/models.py`, `app/cli.py`, `app/services/agent_task_actions.py`,
  and `app/services/evidence.py` are no longer easy to misread as the next
  implementation roots when a future session starts from the updated docs or
  case records.
- Trap-surface improvement cases describe their actual reduced or deployed
  state and successor routing honestly.
- The architecture-quality summary still preserves raw `top_hotspot_paths`
  while the routed-trap fields remain present and verifiable.
- The queued open-owner packet is clearly marked as queued behind this packet,
  not as a competing active “next” milestone.
- All required verification gates pass without weaker assertions or reduced
  routing metadata.

## Stop Conditions

- Stop if Milestone 0 shows this debt is already fully resolved in the durable
  docs and registry and only the previously drafted open-owner packet needs
  rewording.
- Stop if the only way to keep queue docs aligned is to duplicate the same
  trap list across multiple files without a stable canonical source.
- Stop if current dirty routing-doc edits from another packet cannot be
  separated cleanly enough for an atomic docs-only closeout.
- Stop if closing a trap case would hide real regrowth in its successor owner
  family.

## Local Commit Closeout Policy

- Close this packet as a docs-and-governance milestone sequence before
  resuming broader owner-family implementation work.
- Each milestone must land as an atomic local commit containing only the
  routing-alignment slice, any matching tests or contract updates, and the
  required doc or handoff updates for that milestone.
- Do not stage unrelated queued owner-family implementation work with this
  packet.

## Residual Risks And Next Milestone Routing

- The queued code-owning follow-on after this packet is
  `docs/open_owner_backlog_resolution_milestone_plan.md`. That packet should
  remain queued until this source-of-truth packet closes, because otherwise the
  same future-session ambiguity will survive.
- If Milestone 1 proves one trap case still carries a real unresolved owner
  split rather than pure interpretation debt, route that case explicitly in the
  handoff instead of letting it fall back into the raw hotspot list.
- After this packet closes, future reselects should start from the routed
  queue and queued owner packets, not from the raw hotspot list or stale
  facade case titles.
