# Remaining Packet Queue Resolution Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: active queue-coordination brief after
`docs/documents_api_route_surface_boundary_milestone_plan.md` left the live
`top_routed_hotspot_paths` queue empty. Packet A is now resolved through
`docs/stale_open_registry_closeout_milestone_plan.md`, Packet B is now
resolved through `docs/verified_to_deployed_registry_closeout_milestone_plan.md`,
Packet C is now resolved through
`docs/agent_task_context_residual_successor_split_milestone_plan.md`, Packet D
is now resolved through
`docs/search_service_residual_ranking_split_milestone_plan.md`, and Packet E is
the next queued packet.
Owner context: broader coordination follow-on for the remaining improvement
cases after the fresh broader reselect reduced `IC-23F2C79C8AA7`. The later
stale-open, verified-to-deployed, Packet C residual-successor, and Packet D
residual-ranking closeouts now leave the repo with `open=0`, `verified=0`, and
`deployed=60`.

## Purpose

Turn the remaining architecture-governance backlog into an explicit execution
queue so future sessions stop treating the raw case registry as the operative
packet order.

The current weakness is not the lack of known debt. The repo already knows the
remaining queue truth. The problem is making sure the now-empty code-owning
backlog gets closed honestly instead of leaving stale Packet D wording behind
or reopening already-reduced roots because `top_routed_hotspot_paths` is still
empty.

## Current Evidence

Live baseline from the current checkout on 2026-05-19:

```text
git status -sb
  ## main...origin/main [ahead 9]

uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":40,"open":11,"verified":9}

uv run docling-system-improvement-case-list --status open
  open cases:
    IC-65AF4A6D8B1E  evidence owner-family modules
    IC-FD18EE2D3309  tests/unit/test_cli.py
    IC-3B4C9F2A76E1  tests/unit/test_agent_task_context.py
    IC-25C1F7B9E4DA  tests/unit/test_search_service.py
    IC-81C531769EB3  app/services/semantic_governance.py
    IC-9A0332D41F79  app/services/docling_parser.py
    IC-33B4990DC366  app/services/quality.py
    IC-649D7B4E3AB5  app/services/semantic_candidates.py
    IC-4B6E9F8D2A10  evaluation residual owner-family modules
    IC-81F2C6D4B9A7  UI module residual owner family
    IC-2D5A7E9C4B18  semantic and technical-report residual owner family

uv run docling-system-improvement-case-list --status verified
  verified cases:
    IC-8304248AB64C  app/services/semantic_pass_lifecycle.py
    IC-ADCFFF108626  app/services/semantic_pass_reads.py
    IC-D49E037D5657  tests/integration/test_technical_report_harness_roundtrip.py
    IC-23F2C79C8AA7  tests/unit/test_documents_api.py
    IC-8AFAD4A415CA  app/services/runs.py
    IC-865AB8419D55  app/services/semantic_graph.py
    IC-A92BA42C6D18  app/services/semantic_generation.py
    IC-6F4E2B5A91C3  semantic generation owner-family modules
    IC-C8D41A2F77BE  semantic graph owner-family modules

uv run docling-system-architecture-quality-report --summary
  broad_facade_count=2
  legibility_gap_count=0
  top_routed_hotspot_paths=[]

wc -l app/services/evidence_claim_support_replay_alerts.py \
  tests/unit/test_cli.py \
  tests/unit/test_agent_task_context.py \
  tests/unit/test_search_service.py \
  app/services/semantic_governance.py \
  app/services/docling_parser.py \
  app/services/quality.py \
  app/services/semantic_candidates.py \
  app/services/evaluation_fixtures.py \
  app/ui/modules/agents.js \
  app/services/technical_reports.py \
  app/services/semantic_pass_lifecycle.py \
  app/services/semantic_pass_reads.py \
  tests/integration/test_technical_report_harness_roundtrip.py \
  app/services/runs.py \
  app/services/semantic_graph.py \
  app/services/semantic_generation.py \
  app/services/semantic_generation_brief.py \
  app/services/semantic_graph_promotions.py
    407 app/services/evidence_claim_support_replay_alerts.py
      0 tests/unit/test_cli.py
    328 tests/unit/test_agent_task_context.py
    117 tests/unit/test_search_service.py
     39 app/services/semantic_governance.py
    199 app/services/docling_parser.py
     15 app/services/quality.py
    120 app/services/semantic_candidates.py
    376 app/services/evaluation_fixtures.py
    599 app/ui/modules/agents.js
    574 app/services/technical_reports.py
    529 app/services/semantic_pass_lifecycle.py
    372 app/services/semantic_pass_reads.py
     93 tests/integration/test_technical_report_harness_roundtrip.py
    404 app/services/runs.py
    185 app/services/semantic_graph.py
     91 app/services/semantic_generation.py
    505 app/services/semantic_generation_brief.py
    589 app/services/semantic_graph_promotions.py
```

Durable repo evidence already narrowed the remaining live code work further at
the queue-freeze baseline:

- `docs/agent_task_residual_owner_family_milestone_plan.md` says only
  `IC-3B4C9F2A76E1` and `IC-25C1F7B9E4DA` remain intentionally open because
  focused successor files still exceed the default `600`-line budget.
- `config/improvement_cases.yaml` says `IC-65AF4A6D8B1E` is retirement-ready
  because no governed evidence owner remains above the default `600`-line
  budget.
- `docs/evaluation_residual_owner_family_milestone_plan.md`,
  `docs/ui_module_residual_owner_family_milestone_plan.md`, and
  `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`
  all already describe resolved local closeouts with family roots at or below
  the default `600`-line budget.
- `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md` and
  `docs/open_owner_backlog_resolution_milestone_plan.md` already describe the
  semantic pass, run-processing, semantic generation, and semantic graph roots
  as reduced or verified and needing honest deployment rather than fresh code
  work.

Packet A closeout result from the same 2026-05-19 checkout:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":49,"open":2,"verified":9}
```

At the Packet A checkpoint, the remaining `open` cases were only:

- `IC-3B4C9F2A76E1`
- `IC-25C1F7B9E4DA`

Packet B closeout result from the same 2026-05-19 checkout:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":58,"open":2,"verified":0}
```

Packet C closeout result from the same 2026-05-19 checkout:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":59,"open":1,"verified":0}
```

Packet D closeout result from the same 2026-05-19 checkout:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":60,"open":0,"verified":0}
```

## Goal

Queue the remaining packets into an explicit, durable execution order so that:

- retirement-ready `open` cases are closed through a docs-only registry sweep
  instead of being reimplemented
- already-verified cases are deployed through a second honest closeout sweep
  instead of staying indefinitely in `verified`
- the two genuinely active residual code packets are listed explicitly and
  executed after the registry truth sweeps
- the final queue-exhaustion sweep can close the coordination brief honestly
  once the code-owning backlog reaches zero
- the repo can drive from a durable ordered list instead of another broad
  free-form reselect

## Non-Goals

- No production code changes in this queue-plan packet.
- No registry mutations in this packet beyond updating the handoff and queue
  docs to point at the ordered follow-ons.
- No reopening of already-resolved architecture packets just because their old
  selected roots still appear in historical docs.
- No broad reprioritization outside the current `open` plus `verified`
  improvement-case backlog.

## Scope

In scope:

- `docs/remaining_packet_queue_resolution_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

Out of scope:

- `config/improvement_cases.yaml`
- production or test source files
- any child packet implementation work

## Owner Surfaces

- queue truth in `docs/SESSION_HANDOFF.md`
- architecture map routing in `docs/agentic_architecture_index.md`
- broader coordination wording in `docs/boring_change_architecture_milestone_plan.md`
- this queue brief as the durable ordered list
- the future child packet docs created when each queued packet begins

## Placement Rules

- Treat `top_routed_hotspot_paths` as measurement-only for this queue packet
  because it is currently empty; this plan is the operative order until a
  later code packet recreates a live routed queue.
- Create one child packet or one docs-only closeout sweep per milestone. Do
  not bundle the two real code packets into the same implementation milestone.
- When a case is already under budget and its durable docs say the local code
  work is complete, route it into a docs-only registry sweep rather than back
  into source edits.
- When an `open` root is already small but its focused successor files remain
  above `600`, target the oversized focused successors, not the reduced root.
- Before starting any child packet, rerun the Milestone 0 baseline commands in
  this plan. If a supposedly retirement-ready case regrows above budget, eject
  it from the docs-only sweep and create a fresh code-owning child packet.
- For docs-only closeout packets, stage only docs and registry artifacts. Do
  not include unrelated source or test edits in those commits.

## Packet Queue

1. `Packet A`: stale-open registry closeout sweep.
   Cases: `IC-65AF4A6D8B1E`, `IC-FD18EE2D3309`, `IC-81C531769EB3`,
   `IC-9A0332D41F79`, `IC-33B4990DC366`, `IC-649D7B4E3AB5`,
   `IC-4B6E9F8D2A10`, `IC-81F2C6D4B9A7`, `IC-2D5A7E9C4B18`.
2. `Packet B`: verified-to-deployed registry closeout sweep.
   Cases: `IC-8304248AB64C`, `IC-ADCFFF108626`, `IC-D49E037D5657`,
   `IC-23F2C79C8AA7`, `IC-8AFAD4A415CA`, `IC-865AB8419D55`,
   `IC-A92BA42C6D18`, `IC-6F4E2B5A91C3`, `IC-C8D41A2F77BE`.
3. `Packet C`: agent-task context residual successor split.
   Case: `IC-3B4C9F2A76E1`, targeting the still-over-budget focused successors
   `tests/unit/test_agent_task_context_semantic_graph_promotions.py` and
   `tests/unit/test_agent_task_context_reports_claim_support.py`.
4. `Packet D`: search service residual ranking split.
   Case: `IC-25C1F7B9E4DA`, targeting the still-over-budget focused successor
   `tests/unit/test_search_service_ranking.py`.
5. `Packet E`: final queue exhaustion and rebaseline sweep.
   Purpose: confirm `open=0`, `verified=0`, and either leave the routed queue
   empty or create one new explicit packet if fresh regrowth appears.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Future sessions reopen small roots because the queue plan mirrors raw `open` status instead of live evidence. | This plan, handoff, architecture index | Milestone 0 baseline commands plus targeted `wc -l` and doc review | A case already under budget is still queued as code work without proof of regrowth. | Keep `tests/unit/test_cli.py` in a code-owning packet despite `0` lines and confirm Milestone 0 rejects it. | Future Codex rewrites a resolved facade or empty smoke root instead of closing stale registry debt. |
| Docs-only sweeps accidentally hide a real regrowth in a supposedly retirement-ready case. | Packet A and Packet B child plans | Fresh `wc -l`, `uv run docling-system-hygiene-check`, `uv run docling-system-improvement-case-summary` | Any case in a docs-only sweep has a live governed owner above `600` or contradictory current docs. | Leave a regrown `>600` owner inside Packet A and confirm the sweep must eject it into a new code packet. | Future Codex marks a case deployed because an older note said it was small. |
| The two real residual test packets get lost behind registry-only work and the queue never reaches actual code debt. | This plan, child packet list | Ordered queue review in handoff and index | Packet C or Packet D is absent, vague, or not tied to the known over-budget successors. | Omit `tests/unit/test_search_service_ranking.py` from the queue and confirm the remaining open count cannot reach zero honestly. | Future Codex closes only docs and claims the backlog is resolved while over-budget focused tests remain. |
| A child packet bundles unrelated cases just to drive down counts quickly. | Future child plan docs, handoff | One-packet-at-a-time closeout policy plus staged-file review | Any child milestone combines docs-only sweeps with source splits or combines Packet C and Packet D into one implementation commit. | Stage both residual test lanes in one milestone and confirm the plan rejects the overlap. | Future Codex mixes multiple families into one noisy closeout commit and loses precise routing history. |
| Queue truth drifts again after one or two child packets land. | `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, this plan | Every child packet must refresh counts and remaining queue order before commit | Counts or remaining queue order differ across durable docs after a child packet closes. | Update only the child packet doc and leave the handoff queue stale; confirm the closeout gate fails. | Future Codex resumes from the wrong remaining packet because the queue docs disagree. |

## Milestone Sequence

### Milestone 0. Live Rebaseline And Queue Freeze
Outcome label: reduced

Reconfirm that the remaining backlog still matches the queue above before any
child packet starts.

This milestone must:

- rerun `uv run docling-system-improvement-case-summary`
- rerun `uv run docling-system-improvement-case-list --status open`
- rerun `uv run docling-system-improvement-case-list --status verified`
- rerun `uv run docling-system-architecture-quality-report --summary`
- rerun the targeted `wc -l` baseline from this plan for every queued family
- confirm that only `IC-3B4C9F2A76E1` and `IC-25C1F7B9E4DA` still require code
  work
- rewrite this plan if any queued case regrew or any additional live code
  packet appears

### Milestone 1. Packet A: Stale-Open Registry Closeout Sweep
Outcome label: resolved

Close the nine `open` cases that are already under budget and already
described as resolved or retirement-ready in durable docs.

Resolved on 2026-05-19 through
`docs/stale_open_registry_closeout_milestone_plan.md`. The post-closeout live
target landed at `open=2`, `verified=9`, and `deployed=49`.

Packet A must:

- create a fresh child plan dedicated to the stale-open sweep
- refresh and deploy `IC-65AF4A6D8B1E`, `IC-FD18EE2D3309`,
  `IC-81C531769EB3`, `IC-9A0332D41F79`, `IC-33B4990DC366`,
  `IC-649D7B4E3AB5`, `IC-4B6E9F8D2A10`, `IC-81F2C6D4B9A7`, and
  `IC-2D5A7E9C4B18` only if live measurements still prove they are under
  budget
- leave `IC-3B4C9F2A76E1` and `IC-25C1F7B9E4DA` open and explicitly named as
  the remaining code-owning packets
- target a post-closeout summary of `open=2`, `verified=9`, `deployed=49`
  unless Milestone 0 discovers additional regrowth

### Milestone 2. Packet B: Verified-To-Deployed Closeout Sweep
Outcome label: resolved

Deploy the nine cases that are already verified and no longer need code work.

Resolved on 2026-05-19 through
`docs/verified_to_deployed_registry_closeout_milestone_plan.md`. The
post-closeout live target landed at `open=2`, `verified=0`, and
`deployed=58`.

Packet B must:

- create a fresh child plan dedicated to the verified sweep
- refresh and deploy `IC-8304248AB64C`, `IC-ADCFFF108626`,
  `IC-D49E037D5657`, `IC-23F2C79C8AA7`, `IC-8AFAD4A415CA`,
  `IC-865AB8419D55`, `IC-A92BA42C6D18`, `IC-6F4E2B5A91C3`, and
  `IC-C8D41A2F77BE`
- confirm that the child packet does not reopen already-reduced roots in code
- target a post-closeout summary of `open=2`, `verified=0`, `deployed=58`
  unless Milestone 0 or Packet A discovered new live code work

### Milestone 3. Packet C: Agent-Task Context Residual Successor Split
Outcome label: resolved

Finish `IC-3B4C9F2A76E1` by splitting or reducing the still-over-budget
focused successor tests rather than regrowing the reduced root.

Resolved on 2026-05-19 through
`docs/agent_task_context_residual_successor_split_milestone_plan.md`. The
post-closeout live target landed at `open=1`, `verified=0`, and
`deployed=59`.

Packet C must:

- create a fresh child plan for the agent-task context residual test lane
- target `tests/unit/test_agent_task_context_semantic_graph_promotions.py` and
  `tests/unit/test_agent_task_context_reports_claim_support.py`
- keep `tests/unit/test_agent_task_context.py` at or below its current narrow
  residual size
- add or refresh hotspot-prevention and hygiene governance if the focused
  successors are further split
- target a post-closeout summary of `open=1`, `verified=0`, `deployed=59`
  unless a new queued packet appears during the milestone

### Milestone 4. Packet D: Search-Service Residual Ranking Split
Outcome label: resolved

Finish `IC-25C1F7B9E4DA` by reducing the still-over-budget ranking successor
without reopening the reduced root or shifting debt into a new ungoverned test
file.

Resolved on 2026-05-19 through
`docs/search_service_residual_ranking_split_milestone_plan.md`. The
post-closeout live target landed at `open=0`, `verified=0`, and
`deployed=60`.

Packet D must:

- create a fresh child plan for the search-service residual test lane
- target `tests/unit/test_search_service_ranking.py`
- keep `tests/unit/test_search_service.py` at or below its current narrow
  residual size
- refresh hotspot-prevention or hygiene governance if the ranking owner is
  further decomposed
- target a post-closeout summary of `open=0`, `verified=0`, `deployed=60`
  unless a new queued packet appears during the milestone

### Milestone 5. Packet E: Final Queue Exhaustion And Honesty Sweep
Outcome label: resolved

Prove that the queued backlog is exhausted and either leave the routed queue
empty honestly or create exactly one new explicit packet if fresh debt
appeared during execution.

Packet E must:

- rerun the full Milestone 0 baseline
- confirm `status_counts.open=0` and `status_counts.verified=0`, or
  explicitly name the new remaining packet if the counts do not land
- refresh this plan, the handoff, the architecture index, and the broader
  coordination brief to show the remaining queue truth
- retire this queue plan as resolved if no additional packet is needed

## Required Implementation Artifacts

- This queue plan as the durable queue source of truth
- one fresh child packet doc for each queued execution packet
- refreshed `config/improvement_cases.yaml` entries during Packet A, B, C, and
  D execution
- refreshed `config/hotspot_prevention.yaml` and `config/hygiene_policy.yaml`
  during Packet C or D if new successor routing is introduced

## Required Documentation And Handoff Updates

Every child packet created from this queue must update:

- its own child packet doc
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

Packet A and Packet B must also update any older child packet docs whose
status wording still says `resolved locally`, `retirement-ready`, or
`verified` once the registry is actually deployed.

## Required Verification Gates

For this queue-plan packet itself:

- `git diff --check`
- targeted `rg` review proving the same counts and packet order appear in this
  plan, the handoff, the architecture index, and the broader coordination
  brief

For Packet A and Packet B:

- `git diff --check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- targeted `wc -l` or equivalent line-count proof for every case being closed

For Packet C and Packet D:

- `git diff --check`
- packet-local Ruff and pytest slices
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-architecture-inspect`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q`

## Acceptance Criteria

- The queue order is explicit and durable in repo docs rather than living only
  in chat.
- The first two queued packets are docs-only registry sweeps, not accidental
  code packets.
- Packet D `IC-25C1F7B9E4DA` is the only remaining queued code-owning packet
  unless Milestone 0 discovers fresh regrowth.
- The plan names the exact case IDs and the exact remaining over-budget
  successor file for Packet D after Packet C closes.
- The handoff, architecture index, broader coordination brief, and this plan
  all describe the same queue order.
- The queue targets honest counts: `open=2`, `verified=9`, `deployed=49`
  after Packet A; `open=2`, `verified=0`, `deployed=58` after Packet B;
  `open=1`, `verified=0`, `deployed=59` after Packet C; and `open=0`,
  `verified=0`, `deployed=60` after Packet D unless Milestone 0 finds new
  live debt.

## Stop Conditions

- Stop and rewrite the queue if Milestone 0 shows any Packet A or Packet B
  case has regrown above budget.
- Stop and create a new child packet if any unlisted remaining case becomes
  the real next code-owning packet during execution.
- Stop a docs-only sweep if closing a case would require source edits rather
  than honest registry or handoff alignment.

## Local Commit Closeout Policy

- This queue-plan packet closes as a docs-only atomic commit containing this
  plan plus the queue-doc updates that point to it.
- Each queued child packet must close in its own local atomic commit after its
  required verification passes.
- Stage only the packet-local docs or code slice for each milestone.
- Treat any child packet as incomplete until its docs, handoff, verification,
  and local commit all exist together.

## Residual Risks And Next Milestone Routing

- This plan does not itself close any remaining case; it only freezes the
  execution order.
- The case counts and retirement readiness are live-state dependent, so
  Milestone 0 must run before Packet A or Packet B.
- If Milestone 0 still confirms the current baseline, Packet A is the next
  logical milestone because it removes the largest block of stale `open` debt
  without reopening resolved code surfaces.
