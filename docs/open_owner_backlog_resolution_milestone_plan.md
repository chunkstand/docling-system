# Open Owner Backlog Resolution Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally on 2026-05-18 after the routed-hotspot
interpretation prerequisite and the open-owner closeout executed together.
The packet reclassified the reduced CLI, API, semantic-pass, and run roots so
they no longer remain vague open owner debt, reduced
`app/services/semantic_generation_brief.py` to `505` lines with
`semantic_generation_brief_metrics.py` at `145`, and reduced
`app/services/semantic_graph_core.py` / `app/services/semantic_graph_promotions.py`
to `492` / `589` lines with new support and snapshot-lifecycle siblings at
`214` / `138`. Historical drafted sections below remain useful as the
Milestone 0 baseline, but the live queue has moved past this packet.
Owner context: this packet began from the remaining open owner backlog around
the reduced CLI or API compatibility roots, the semantic-pass family that was
already reduced in code but not durably retired in the registry, the
run-processing root, and the residual semantic graph or generation owner
families under `IC-9812A0B138D9`, `IC-5B6430FCB929`, `IC-9E6B8F5D62A1`,
`IC-8304248AB64C`, `IC-ADCFFF108626`, `IC-8AFAD4A415CA`,
`IC-865AB8419D55`, `IC-A92BA42C6D18`, `IC-6F4E2B5A91C3`, and
`IC-C8D41A2F77BE`. After closeout those selected cases now read as deployed,
and the later 2026-05-19 routing-source-of-truth refresh now records
`IC-5B6430FCB929` / `app/api/main.py` as deployed through `d8841fd` while the
later verified-to-deployed registry closeout records
`IC-8304248AB64C`, `IC-ADCFFF108626`, `IC-8AFAD4A415CA`,
`IC-865AB8419D55`, `IC-A92BA42C6D18`, `IC-6F4E2B5A91C3`, and
`IC-C8D41A2F77BE` as deployed through the same closeout lane and routes the
bootstrap root off the active queue as an accepted residual boundary.
Next-packet selection therefore returns to the routed hotspot/test queue
without reopening the small API bootstrap surface.

## Purpose

Resolve the remaining ownership debt without reopening already-closed packets
just because stale open cases or raw hotspot measurements still mention the
old roots.

The current weakness is not a single oversized file. It is the combination of
three different failure modes:

- some open cases now point at compatibility facades that are already small,
  but the registry has not been durably retired or rerouted
- some reduced roots still own too much orchestration and need one more
  explicit boundary pass even though they are already below the `800`-line
  emergency threshold
- some extracted semantic owner modules remain above the default `600`-line
  hygiene budget after the root facade split, so the backlog is now living in
  the child owners rather than in the old monoliths

This packet exists to separate those situations cleanly, close the
retirement-ready cases, finish the real residual owner-family splits, and
leave the selected scope no longer represented as vague open ownership debt.

## Current Evidence

- `uv run docling-system-improvement-case-summary` now reports
  `case_count=59`, `status_counts={"measured":1,"deployed":15,"open":41,"verified":2}`,
  and `cause_class_counts={"missing_constraint":2,"unclear_ownership":57}`.
- `uv run docling-system-architecture-quality-report --summary` now reports
  `hotspot_count=10`, `max_hotspot_risk_score=486.06`,
  `stale_facade_hotspot_count=7`, `routing_trap_paths=["app/db/models.py","app/cli.py","app/services/agent_task_actions.py","app/services/evidence.py","app/schemas/agent_tasks.py","tests/unit/test_cli.py","app/services/agent_tasks.py"]`,
  and `top_routed_hotspot_paths=["tests/integration/test_claim_support_judge_evaluation_roundtrip.py","tests/integration/test_technical_report_harness_roundtrip.py","tests/unit/test_hotspot_prevention.py"]`.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  reports `0` Python cycle components, no code files above `800`, and the
  relevant remaining large owners are
  `app/services/semantic_graph_promotions.py` at `718`,
  `app/services/semantic_graph_core.py` at `697`, and
  `app/services/semantic_generation_brief.py` at `644`. It also still shows
  high churn on `app/cli.py` at hotspot score `21375` and
  `app/services/runs.py` at `10100`.
- Live `wc -l` now measures the selected roots at:
  `app/cli.py=375`, `app/api/main.py=98`,
  `app/services/semantics.py=54`,
  `app/services/semantic_pass_lifecycle.py=529`,
  `app/services/semantic_pass_reads.py=372`,
  `app/services/runs.py=404`,
  `app/services/semantic_generation.py=91`,
  `app/services/semantic_generation_brief.py=644`,
  `app/services/semantic_graph.py=185`,
  `app/services/semantic_graph_core.py=697`, and
  `app/services/semantic_graph_promotions.py=718`.
- `config/improvement_cases.yaml` shows `IC-9812A0B138D9` still open even
  though `app/cli.py` is now a 375-line forwarding surface over
  `app/cli_commands/improvement_cases.py`, `app/cli_commands/ingest.py`,
  `app/cli_commands/runtime.py`, and `app/cli_commands/search_harness.py`.
- `config/improvement_cases.yaml` shows `IC-5B6430FCB929` open for
  `app/api/main.py` with `risk_score=331.4`, `line_count=98`, and
  `changes_90d=47`, but no deployment notes or refreshed measurement
  narrative now explain whether the file is still a real owner boundary or a
  stale compatibility hotspot.
- `config/improvement_cases.yaml` now describes `IC-9E6B8F5D62A1`,
  `IC-8304248AB64C`, and `IC-ADCFFF108626` as already reduced or
  retirement-ready after the semantic pass lifecycle or reads boundary work:
  `app/services/semantics.py` is a 54-line facade,
  `app/services/semantic_pass_lifecycle.py` is `529`,
  `app/services/semantic_pass_artifacts.py` is `150`,
  `app/services/semantic_pass_reviews.py` is `369`,
  `app/services/semantic_pass_reads.py` is `372`, and
  `app/services/semantic_pass_source_records.py` is `415`.
- `config/improvement_cases.yaml` shows `IC-8AFAD4A415CA` still open even
  though `app/services/runs.py` is now a 404-line orchestration root over
  `app/services/run_leases.py`, `app/services/run_persistence.py`, and
  `app/services/run_post_promotion.py`, while the architecture probe still
  lists `app.services.runs` among the highest fan-out modules at `16` local
  imports.
- `config/improvement_cases.yaml` shows `IC-A92BA42C6D18` and
  `IC-865AB8419D55` still open on the already-reduced semantic generation and
  graph facades, while the actual live residual debt is now explicitly routed
  to `IC-6F4E2B5A91C3` for `app/services/semantic_generation_brief.py` and
  `IC-C8D41A2F77BE` for `app/services/semantic_graph_core.py` plus
  `app/services/semantic_graph_promotions.py`.
- `app/api/main.py` currently contains only runtime bind validation, the
  remote-read auth middleware, router registration, static UI mounting, and
  the uvicorn entrypoint. `app/cli.py` currently contains forwarding wrappers
  and `run_*` entrypoints. `app/services/runs.py` still carries the
  `RunProcessor` state machine and worker loop. The semantic generation and
  graph roots are already explicit facades over family-local siblings.

## Goal

Resolve this selected ownership backlog so that:

- the selected open cases no longer remain vague `open` debt with stale owner
  descriptions
- `app/cli.py`, `app/api/main.py`, `app/services/semantics.py`,
  `app/services/runs.py`, `app/services/semantic_generation.py`, and
  `app/services/semantic_graph.py` end as explicit compatibility or
  orchestration roots with durable owner-case narratives
- the retirement-ready semantic pass cases are durably closed instead of being
  left open after their code split already landed
- `app/services/semantic_generation_brief.py`,
  `app/services/semantic_graph_core.py`, and
  `app/services/semantic_graph_promotions.py` are reduced under the configured
  budget or replaced by narrower same-milestone owner routing
- no new Python cycle appears, no code file regrows above `800`, and no new
  `601-800` line owner is left ungoverned
- the handoff, index, broader coordination brief, improvement-case registry,
  and hygiene policy all describe the same live queue

The issue is `resolved` when the selected case family is no longer pretending
that reduced facades and real residual owner modules are the same kind of
problem.

## Non-Goals

- No reopening of the already-resolved search, evidence, documents-service,
  evaluation, UI, semantic-report, agent-task residual, DB-model residual, or
  governance self-hosting packets unless Milestone 0 proves real regrowth in
  those exact surfaces.
- No threshold increase above the current architecture-probe `800`-line gate
  or above the default `600`-line hygiene budget.
- No generic `app/services/utils.py`, broad `semantic_helpers.py`, or shared
  test-support sink used to hide moved ownership.
- No test weakening, assertion loosening, skip broadening, xfail broadening,
  or route-coverage deletion just to make the selected case count drop.
- No pretending that a raw architecture-quality hotspot automatically needs
  code motion when Milestone 0 shows it is only a stale compatibility case.

## Scope

In scope:

- `app/cli.py`
- `app/cli_commands/common.py`
- `app/cli_commands/improvement_cases.py`
- `app/cli_commands/ingest.py`
- `app/cli_commands/runtime.py`
- `app/cli_commands/search_harness.py`
- `app/api/main.py`
- focused new `app/api/*` siblings if Milestone 0 proves a clean bootstrap or
  auth-boundary split is still needed
- `app/services/semantics.py`
- `app/services/semantic_pass_lifecycle.py`
- `app/services/semantic_pass_artifacts.py`
- `app/services/semantic_pass_reviews.py`
- `app/services/semantic_pass_reads.py`
- `app/services/semantic_pass_source_records.py`
- `app/services/semantic_registry_preview.py`
- `app/services/runs.py`
- `app/services/run_*.py`
- `app/services/semantic_generation.py`
- `app/services/semantic_generation_*.py`
- `app/services/semantic_graph.py`
- `app/services/semantic_graph_*.py`
- `app/api/routers/semantics.py` and other direct callers only as needed to
  preserve caller contracts
- `tests/unit/test_cli*.py`
- `tests/unit/test_run_logic.py`
- `tests/unit/test_documents_api_semantics.py`
- `tests/unit/test_semantic*.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/integration/test_semantic_*roundtrip.py`
- `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`
- `docs/app_large_owner_modules_resolution_milestone_plan.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`

Out of scope:

- routed hotspot tests outside this selected owner backlog
- `app/db/models.py`, `app/services/evidence.py`,
  `app/services/agent_task_actions.py`, and `app/services/agent_tasks.py`
  beyond preserving their routing-trap status
- UI module work outside direct semantic or API callers
- broader product features unrelated to the selected owner-family cleanup

## Owner Surfaces

- CLI compatibility and command-dispatch ownership under
  `IC-9812A0B138D9`
- API bootstrap and read-auth ownership under `IC-5B6430FCB929`
- semantics facade plus lifecycle or reads retirement state under
  `IC-9E6B8F5D62A1`, `IC-8304248AB64C`, and `IC-ADCFFF108626`
- run-processing orchestration under `IC-8AFAD4A415CA`
- semantic generation facade plus residual brief owner under
  `IC-A92BA42C6D18` and `IC-6F4E2B5A91C3`
- semantic graph facade plus residual core or promotions owners under
  `IC-865AB8419D55` and `IC-C8D41A2F77BE`
- the registry, hygiene policy, and routing docs that make those owner
  boundaries durable

## Placement Rules

- Keep `app/cli.py` as the console-script compatibility layer and forwarding
  entrypoint only. Direct command bodies must live in `app/cli_commands/*.py`
  or narrower family-local siblings, not back in the root wrapper file.
- Keep `app/api/main.py` as bootstrap, middleware wiring, UI mount, and
  router-registration only. If any split is still justified, move runtime bind
  validation or remote-read auth wiring into focused `app/api/*` siblings
  rather than into routers or service modules.
- Keep `app/services/semantics.py`, `app/services/semantic_generation.py`, and
  `app/services/semantic_graph.py` as narrow compatibility facades. Do not
  move implementation back into those roots just because their old cases are
  still open.
- Keep semantic pass lifecycle, artifact, review, reads, and source-record
  ownership inside `app/services/semantic_pass*.py` siblings. Do not fold the
  retirement-ready lifecycle or reads work into `app/services/semantic_graph.py`
  or `app/services/runs.py`.
- Preserve `app/services/runs.py` as the public orchestration root while
  keeping stage-specific persistence, promotion, lease, or future worker-loop
  helpers in `app/services/run_*.py` siblings rather than in a new nested
  helper sink inside `RunProcessor`.
- Keep semantic generation residual work inside
  `app/services/semantic_generation_*.py` siblings and semantic graph residual
  work inside `app/services/semantic_graph_*.py` siblings. Do not spill graph
  logic into `app/services/semantics.py` or generation logic into
  `app/services/semantic_candidates.py`.
- Any new focused owner between `401` and `600` lines must receive an exact
  same-milestone hygiene ratchet. Any new support file must remain at or below
  `400` lines.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet treats stale open cases and real residual owners as the same problem, so it does unnecessary code churn and still leaves the backlog open. | `config/improvement_cases.yaml`, packet docs, selected roots | Milestone 0 rebaseline, case-by-case classification review | any selected case still has no explicit classification as retirement, reroute, or active implementation after Milestone 0 | leave `app/api/main.py` and `app/cli.py` as ambiguous open hotspots and confirm the queue remains unclear | future Codex refactors already-small roots because the registry prose stayed stale |
| A reduced compatibility facade regrows because raw `top_hotspot_paths` is used as the execution queue. | `app/cli.py`, `app/services/semantics.py`, `app/services/semantic_generation.py`, `app/services/semantic_graph.py` | architecture-quality summary plus routing review | implementation bodies move back into a known facade or the docs stop distinguishing raw and routed hotspots | move semantic-generation logic back into `app/services/semantic_generation.py` and confirm closeout rejects it | future Codex reopens the wrong roots because churn stayed high |
| The packet “closes” semantic pass debt by editing already-bounded files instead of durably retiring the ready-to-close cases. | `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`, `IC-9E6B8F5D62A1`, `IC-8304248AB64C`, `IC-ADCFFF108626` | Milestone 0 doc review, `wc -l`, hygiene check, improvement-case review | lifecycle or reads roots are changed without a demonstrated regrowth need, or the cases remain open without honest retirement notes | leave the cases open and add more edits to `semantic_pass_lifecycle.py` anyway | future Codex keeps paying to modify code that is already under budget because registry closeout never lands |
| `app/services/runs.py` shrinks by dropping validation, failure, promotion, or semantics behavior instead of clarifying stage ownership. | `app/services/runs.py`, `app/services/run_*.py`, run tests | unit, integration, and full DB-backed pytest slices | any stage behavior, retry path, or post-promotion semantics path loses coverage or changes contract | remove one post-promotion branch and confirm the selected run or Postgres slices fail | future Codex optimizes for line count and silently weakens processing guarantees |
| Residual semantic graph or generation splits move debt into new untracked owners or create a new cycle. | `app/services/semantic_generation_*.py`, `app/services/semantic_graph_*.py` | hygiene check, architecture probe, same-milestone ratchets | any new owner exceeds `600` without routing, any support file exceeds `400`, or any Python cycle appears | dump the brief or promotions helpers into a new 750-line support file and confirm the gate fails | future Codex converts one residual into two new unguided residuals |

## Milestone Sequence

### Milestone 0. Live Rebaseline And Case Classification Lock
Outcome label: reduced

Refresh the selected backlog from the live checkout and classify each case as
one of three things before more code moves:

- docs-only retirement or closeout
- compatibility-boundary refinement
- real residual owner-family split

This milestone must:

- rerun `uv run docling-system-improvement-case-summary`
- rerun `uv run docling-system-architecture-quality-report --summary`
- rerun `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --format markdown --top 20`
- rerun `wc -l` for the selected roots
- confirm whether `app/api/main.py` and `app/cli.py` still need code motion or
  only honest routing or retirement notes
- confirm whether the semantic pass cases should close via docs or registry
  alignment rather than another service split
- stop if overlapping user-owned edits cannot be separated from this packet

### Milestone 1. CLI And API Compatibility Boundary Closeout
Outcome label: reduced

Resolve `IC-9812A0B138D9` and `IC-5B6430FCB929` without regrowing the roots.

Preferred outcomes include:

- `app/cli.py` stays a forwarding-only root while any remaining mixed entry
  ownership moves into focused `app/cli_commands/*.py` siblings
- `app/api/main.py` stays a bootstrap-only root while any remaining runtime
  bind or remote-read auth glue moves into focused `app/api/*` siblings if
  Milestone 0 proves that split is still worth doing
- the registry no longer treats either file as a vague unresolved hotspot with
  null deployment notes
- the CLI and API cases are either durably closed or rerouted as explicit
  compatibility-facade exceptions instead of being left as stale `open`
  backlog

### Milestone 2. Semantic Pass And Runs Durable Alignment
Outcome label: reduced

Resolve the mixed semantic-pass or run-processing backlog without reopening the
already-resolved semantic service-boundary packet.

Preferred outcomes include:

- `IC-9E6B8F5D62A1`, `IC-8304248AB64C`, and `IC-ADCFFF108626` close through
  durable registry, hygiene, and handoff alignment if Milestone 0 confirms the
  code is already at the correct boundary
- `app/services/runs.py` either closes as an honest 404-line orchestration
  root or moves any remaining mixed worker-loop or stage helper ownership into
  focused `app/services/run_*.py` siblings
- the selected run case no longer says the root is still a 1026-line monolith
  after the split already landed

### Milestone 3. Semantic Generation Residual Owner-Family Split
Outcome label: reduced

Resolve the generation-family residual without reopening the already-small
facade.

Preferred outcomes include:

- `app/services/semantic_generation.py` stays a narrow public facade
- `app/services/semantic_generation_brief.py` is reduced under budget through
  focused brief-assembly siblings if needed
- `IC-A92BA42C6D18` stops carrying stale root-monolith prose once the real
  residual work is routed through `IC-6F4E2B5A91C3`

### Milestone 4. Semantic Graph Residual Owner-Family Split
Outcome label: reduced

Resolve the graph-family residual without moving graph logic back into the root
facade or into the broader semantics service.

Preferred outcomes include:

- `app/services/semantic_graph.py` stays a narrow public facade
- `app/services/semantic_graph_core.py` and
  `app/services/semantic_graph_promotions.py` are reduced under budget through
  focused graph-family siblings if needed
- `IC-865AB8419D55` stops carrying stale root-monolith prose once the real
  residual work is routed through `IC-C8D41A2F77BE`

### Milestone 5. Registry, Hygiene, And Routing Closeout
Outcome label: resolved

Close the packet only after:

- the selected cases are durably closed, verified, or replaced by narrower
  same-milestone successors
- the registry and hygiene policy reflect the live post-split counts
- the handoff, architecture index, and broader coordination brief all point to
  the same next queue
- the selected verification slices and full DB-backed suite are green

## Required Implementation Artifacts

- any new focused CLI or API boundary siblings required by Milestone 1
- any focused `app/services/run_*.py`,
  `app/services/semantic_generation_*.py`, or
  `app/services/semantic_graph_*.py` siblings required by Milestones 2 through 4
- focused unit or integration tests for any newly created owner boundary
- refreshed `config/improvement_cases.yaml` entries for the selected cases
- refreshed `config/hygiene_policy.yaml` ratchets for any new same-milestone
  owner siblings

## Required Documentation And Handoff Updates

- `docs/open_owner_backlog_resolution_milestone_plan.md`
- `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`
- `docs/app_large_owner_modules_resolution_milestone_plan.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/cli.py app/cli_commands/*.py app/api/main.py app/api/routers/*.py app/services/runs.py app/services/run_*.py app/services/semantics.py app/services/semantic_pass*.py app/services/semantic_generation*.py app/services/semantic_graph*.py tests/unit/test_cli*.py tests/unit/test_run_logic.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic*.py tests/integration/test_postgres_roundtrip.py tests/integration/test_semantic_*roundtrip.py`
- `uv run pytest -q tests/unit/test_cli.py tests/unit/test_cli_entrypoints.py tests/unit/test_cli_runtime.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py tests/unit/test_run_logic.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py tests/unit/test_semantic_orchestration.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --format markdown --top 20`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- `IC-9812A0B138D9`, `IC-5B6430FCB929`, `IC-9E6B8F5D62A1`,
  `IC-8304248AB64C`, `IC-ADCFFF108626`, `IC-8AFAD4A415CA`,
  `IC-865AB8419D55`, `IC-A92BA42C6D18`, `IC-6F4E2B5A91C3`, and
  `IC-C8D41A2F77BE` no longer remain vague open owner debt. Each is either
  durably closed, marked verified or deployed with honest notes, or replaced
  by a narrower same-milestone successor.
- `app/cli.py`, `app/api/main.py`, `app/services/semantics.py`,
  `app/services/runs.py`, `app/services/semantic_generation.py`, and
  `app/services/semantic_graph.py` remain at or below their Milestone 0
  baselines unless a stricter exact ratchet is recorded in the same milestone.
- `app/services/semantic_generation_brief.py`,
  `app/services/semantic_graph_core.py`, and
  `app/services/semantic_graph_promotions.py` end under the configured budget
  or under explicit narrower routing with exact ratchets recorded in the same
  milestone.
- No new Python cycle appears, and the architecture probe still reports no
  code files above `800`.
- The selected CLI, run, semantic, and full DB-backed verification stacks pass
  without weaker assertions or broader skips.
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` all point at this packet
  during execution and no longer instruct future sessions to reselect from a
  stale queue once the packet closes.

## Stop Conditions

- Stop if Milestone 0 proves one or more selected cases are docs-only
  retirement work and mixing that work with the real residual code splits would
  prevent atomic milestone commits.
- Stop if user-owned local edits overlap the selected roots and cannot be
  separated safely.
- Stop if `app/api/main.py` or `app/cli.py` still appear only because of churn
  metrics and there is no defensible owner-boundary change to make.
- Stop if the only path to closing `runs.py`, generation, or graph residuals
  is to spill logic into unrelated owners or to create a new ungoverned
  `601-800` line module.
- Stop if the only path to green is to weaken route, semantic, or DB-backed
  integration coverage.

## Local Commit Closeout Policy

- Close this plan milestone by milestone, not as one giant cleanup commit.
- Each implementation milestone must land as one atomic local commit that
  contains the verified code, tests, registry updates, and doc or handoff
  updates for that milestone.
- Stage only the selected milestone slice and leave unrelated worktree changes
  alone.
- Treat the overall packet as unresolved until the final closeout milestone
  records the selected case status transitions and the aligned routing docs in
  the same verified commit set.

## Residual Risks And Next Milestone Routing

- If Milestone 0 shows the CLI or API roots are purely routing-trap debt, the
  active code-owning scope should narrow immediately to `runs.py` plus the
  semantic generation or graph residual families and the handoff must say so
  explicitly.
- If the semantic pass cases close as docs-only retirement, do not reopen
  `app/services/semantic_pass_lifecycle.py` or
  `app/services/semantic_pass_reads.py` in a later milestone without fresh
  regrowth evidence.
- After this packet closes, the next bounded follow-on should be reselected
  from the routed hotspot or test queue reported by
  `top_routed_hotspot_paths`, not from the stale raw facade list.
