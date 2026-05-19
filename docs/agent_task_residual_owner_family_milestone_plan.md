# Agent-Task Residual Owner Family Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved through the 2026-05-18 durable closeout, with the later
2026-05-19 inherited context-owner closeout now removing the last over-budget
`IC-E52B6C7B22FD` modules. Milestones 0 through 4 are complete, the later
context-owner hardening follow-on is complete, verification is complete, and
the broader queue now returns to
`docs/boring_change_architecture_milestone_plan.md`.
Owner context: selected bounded follow-on for open hotspot
`IC-4098E8370B88` / `app/services/agent_tasks.py`, the inherited
search-harness and semantic-governance owner families still ratcheted under
deployed `IC-A1E186A34097` and `IC-E52B6C7B22FD`, and the currently unowned
agent-task triage integration and unit monoliths. The next routed bounded
packet after this local closeout is now
`docs/db_models_residual_owner_family_milestone_plan.md`.

## Purpose

Resolve the remaining agent-task family debt without pretending the old
orchestration facades are still the problem.

The scoped weakness is now different from the already-resolved
`docs/agent_task_orchestration_boundary_milestone_plan.md` packet. That
earlier plan reduced `app/services/agent_task_actions.py` to `163` lines and
`app/services/agent_task_context.py` to `121` lines, but the live repo still
has three costly follow-on knots in the same family:

- `app/services/agent_tasks.py` is now the top churn hotspot at `776` lines
  and still mixes dependency validation, detail assembly, trace export,
  approval or rejection state transitions, and outcome recording.
- the search-harness and semantic-governance owner families still sit above the
  default hygiene budget in both action and context surfaces, especially
  `app/services/agent_actions/search_harness.py` at `1078` lines and
  `app/services/agent_task_context_semantic_governance.py` at `1126` lines.
- the test side is still monolithic around the same workflows, especially
  `tests/integration/test_agent_task_triage_roundtrip.py` at `1279` lines,
  `tests/unit/test_agent_tasks.py` at `1011`, and
  `tests/unit/test_agent_task_actions_search_harness.py` at `815`.

This plan resolves that residual owner-family debt by decomposing the remaining
agent-task service root, the search-harness family, the semantic-governance
family, and the triage roundtrip tests into focused owners with explicit
routing, ratchets, and closeout gates.

## 2026-05-18 Closeout Update

Milestones 0 through 4 are now resolved locally in the current checkout.

- `app/services/agent_tasks.py` now closes at `324` lines with focused owners
  `app/services/agent_task_dependencies.py` at `176`,
  `app/services/agent_task_reads.py` at `259`, and
  `app/services/agent_task_lifecycle.py` at `197`.
- `app/services/agent_actions/search_harness.py` now closes at `444` lines,
  `app/services/agent_task_context_search_harness.py` at `263`, and the
  focused search-harness owners now live in drafting or triage siblings at
  `453`, `386`, `468`, and `172` lines.
- `app/services/agent_actions/semantic_governance_actions.py` now closes at
  `565` lines, `app/services/agent_task_context_semantic_governance.py` at
  `397`, and the focused ontology or graph owners now live at `281`, `251`,
  `405`, and `367` lines.
- The later inherited context-owner closeout reduces
  `app/services/agent_task_context_semantic_analysis.py` to `436` lines with a
  focused graph-memory sibling at
  `app/services/agent_task_context_semantic_analysis_graph.py` / `373`, and
  reduces `app/services/agent_task_context_technical_reports.py` to `570`
  lines with a focused claim-support sibling at
  `app/services/agent_task_context_technical_reports_claim_support.py` / `112`.
- The residual root tests now close at `12` lines for
  `tests/unit/test_agent_tasks.py`, `10` lines for
  `tests/unit/test_agent_task_actions_search_harness.py`, `97` lines for
  `tests/unit/test_agent_task_context_semantic_governance.py`, and `283` lines
  for `tests/integration/test_agent_task_triage_roundtrip.py`, with focused
  sibling suites and family-local support carrying the moved coverage.
- The later 2026-05-19 registry-alignment sweep now deploys
  `IC-4098E8370B88`, `IC-5D14C2A0B6F7`, `IC-2E0A91B39C5D`, and
  `IC-8F77A1D2C6E4` through durable closeout commit `b9b3e46`, so only the
  adjacent oversized-test residuals `IC-3B4C9F2A76E1` and
  `IC-25C1F7B9E4DA` remain intentionally open because focused successor files
  still exceed the default `600`-line hygiene budget.
- `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, and
  `config/hotspot_prevention.yaml` now route the residual owner families and
  successor test surfaces explicitly. The broader routing now advances to
  `docs/db_models_residual_owner_family_milestone_plan.md` while
  `docs/boring_change_architecture_milestone_plan.md` remains the umbrella
  coordination brief.

Verified local closeout state:

- `git diff --check` passed.
- Focused lint and contract gates passed:
  `uv run ruff check ...`,
  `uv run docling-system-agent-task-action-index`,
  `uv run docling-system-capability-contracts`,
  `uv run docling-system-architecture-inspect`, and
  `uv run docling-system-improvement-case-validate`.
- `uv run docling-system-hotspot-prevention-check --strict` returned
  `blocked=0`.
- `uv run docling-system-hygiene-check` reported
  `new hygiene regressions: none`.
- The later inherited context-owner closeout passes the focused context slice
  at `135 passed`, the DB-backed context integration slice at `8 passed`, and
  `uv run docling-system-hygiene-check` now reports
  `inherited budget debt: none`.
- The final DB-backed suite later passed again at `2115 passed`.
- `uv run docling-system-improvement-case-summary` now reports
  `case_count=52`, `status_counts.open=36`, `status_counts.deployed=15`, and
  `measured_case_count=48`.
- The focused unit slice passed at `105 passed`.
- The focused DB-backed integration slice passed at `13 passed`.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
  reports `0` Python cycles, and the current probe backlog is `20` code files
  above `800` lines.
- The final DB-backed suite passed at `2044 passed`.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-18
local / 2026-05-18 UTC during the Milestone 0 rebaseline before the local
Milestone 1 through 4 implementation:

```text
git status -sb
  ## main...origin/main
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M docs/boring_change_architecture_milestone_plan.md
  ?? docs/python_cycle_backlog_elimination_milestone_plan.md

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

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  largest files include:
    tests/integration/test_agent_task_triage_roundtrip.py = 1279
    app/services/agent_task_context_semantic_governance.py = 1126
    app/services/agent_actions/search_harness.py = 1078
    tests/unit/test_agent_tasks.py = 1011
    app/services/agent_actions/semantic_governance_actions.py = 943
  hotspots include:
    app/services/agent_tasks.py = 30264
    tests/integration/test_agent_task_triage_roundtrip.py = 26859
    tests/unit/test_agent_tasks.py = 13143
  Python cycle components: 3

wc -l app/services/agent_tasks.py
      app/services/agent_actions/search_harness.py
      app/services/agent_task_context_search_harness.py
      app/services/agent_actions/semantic_governance_actions.py
      app/services/agent_task_context_semantic_governance.py
      tests/unit/test_agent_tasks.py
      tests/unit/test_agent_task_actions_search_harness.py
      tests/unit/test_agent_task_context_semantic_governance.py
      tests/integration/test_agent_task_triage_roundtrip.py
   776 app/services/agent_tasks.py
  1078 app/services/agent_actions/search_harness.py
   865 app/services/agent_task_context_search_harness.py
   943 app/services/agent_actions/semantic_governance_actions.py
  1126 app/services/agent_task_context_semantic_governance.py
  1011 tests/unit/test_agent_tasks.py
   815 tests/unit/test_agent_task_actions_search_harness.py
   630 tests/unit/test_agent_task_context_semantic_governance.py
  1279 tests/integration/test_agent_task_triage_roundtrip.py

uv run docling-system-hygiene-check
  inherited budget debt still includes:
    app/services/agent_actions/search_harness.py = 1078 under IC-A1E186A34097
    app/services/agent_actions/semantic_governance_actions.py = 943 under IC-A1E186A34097
    app/services/agent_task_context_search_harness.py = 865 under IC-E52B6C7B22FD
    app/services/agent_task_context_semantic_governance.py = 1126 under IC-E52B6C7B22FD
    app/services/agent_task_context_semantic_analysis.py = 770 under IC-E52B6C7B22FD
    app/services/agent_task_context_technical_reports.py = 643 under IC-E52B6C7B22FD
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  case_count=49
  status_counts.open=33
  status_counts.deployed=15
  measured_case_count=44

config/improvement_cases.yaml
  IC-4098E8370B88 = open owner case for app/services/agent_tasks.py
  IC-A1E186A34097 = deployed root case for app/services/agent_task_actions.py
  IC-E52B6C7B22FD = deployed root case for app/services/agent_task_context.py
  no dedicated target_path entries currently exist for:
    tests/integration/test_agent_task_triage_roundtrip.py
    tests/unit/test_agent_tasks.py
    tests/unit/test_agent_task_actions_search_harness.py
```

Repo-current structural evidence:

- `docs/agent_task_orchestration_boundary_milestone_plan.md` is already
  resolved locally through closeout commit `7cf7465`. This packet must not
  reopen `app/services/agent_task_actions.py` or
  `app/services/agent_task_context.py` as if they were still the primary debt.
- `app/services/agent_tasks.py` still mixes at least four concern families in
  one file: dependency validation and graph checks, detail and trace read
  assembly, lifecycle state transitions, and outcome mutation.
- `app/services/agent_actions/search_harness.py` still mixes repair-case
  shaping, optimization and draft generation, evaluation and verification,
  configuration apply flow, and replay-regression triage.
- `app/services/agent_task_context_semantic_governance.py` still mixes
  ontology-source resolution plus draft, verify, and apply builders for
  semantic registry updates, ontology extensions, and graph promotions.
- `tests/integration/test_agent_task_triage_roundtrip.py` still combines replay
  regression triage, evaluation context, verification context, failure-artifact
  handling, approval lifecycle, learning surfaces, and harness draft-review
  scenarios in one integration surface.
- `tests/unit/test_agent_tasks.py` still mixes creation and dependency
  validation, approval or rejection transitions, outcome dedupe, analytics
  summaries, recommendation summaries, and value-density projections.
- `tests/unit/test_agent_task_actions_search_harness.py` still mixes draft,
  verification, apply, follow-up evidence, and multiple error-path families in
  one unit surface even after the earlier action split.
- The live architecture-quality top-hotspot list still routes small facades such
  as `app/services/agent_task_actions.py`, so this packet must use the
  architecture probe plus hygiene output to target the residual owners
  honestly.

## Goal

Resolve the residual agent-task owner-family debt so that:

- `app/services/agent_tasks.py` becomes a narrow public orchestration and
  compatibility surface at or below `600` lines.
- the selected agent-task service owners in this packet no longer exceed the
  architecture-probe `800`-line threshold, and the selected residual owner
  surfaces close at or below the default `600`-line hygiene budget unless an
  explicit integration-smoke exception is accepted in this plan.
- `tests/integration/test_agent_task_triage_roundtrip.py`,
  `tests/unit/test_agent_tasks.py`, and
  `tests/unit/test_agent_task_actions_search_harness.py` are decomposed into
  focused scenario or owner-family files rather than remaining monoliths.
- search-harness action definitions, semantic-governance context-builder names,
  task action names, `/agent-tasks` API-visible behavior, trace export
  behavior, approval or rejection semantics, and context artifact contracts
  remain stable unless Milestone 0 proves a narrower explicit contract change
  is unavoidable.
- improvement-case, hygiene, and hotspot-prevention routing reflects the true
  residual owners instead of stale root facades or unowned triage tests.
- replacement tests, fixtures, and gates provide equivalent or broader contract
  coverage than the pre-split checks they replace.

## Non-Goals

- No reopening of the resolved `app/services/agent_task_actions.py` or
  `app/services/agent_task_context.py` facade packet.
- No cycle-elimination work beyond preserving the current `3`-component cycle
  baseline already routed through
  `docs/python_cycle_backlog_elimination_milestone_plan.md`.
- No public API, schema, DB, or persisted artifact redesign for agent tasks
  unless Milestone 0 proves the residual owner debt cannot be removed while
  preserving the current contracts.
- No generic helper sink such as a new broad `app/services/agent_task_utils.py`
  or `tests/unit/agent_task_test_support.py` that simply relocates the same
  mixed ownership.
- No test weakening, skip broadening, fixture deletion, assertion loosening, or
  narrower negative-path coverage just to make the file counts or hotspot
  signals look better.
- No unrelated UI, evidence, search, technical-report, evaluation-fixture, or
  data-model backlog cleanup beyond the direct seams required to close the
  selected agent-task family.

## Scope

In scope:

- Milestone 0 live-state refresh and owner-case bootstrap
- `app/services/agent_tasks.py`
- `app/services/agent_actions/search_harness.py`
- `app/services/agent_task_context_search_harness.py`
- `app/services/agent_actions/semantic_governance_actions.py`
- `app/services/agent_task_context_semantic_governance.py`
- focused new `app/services/agent_task_*.py`,
  `app/services/agent_actions/search_harness_*.py`, and
  `app/services/agent_task_context_semantic_governance_*.py` owners created by
  this packet
- `tests/unit/test_agent_tasks.py`
- `tests/unit/test_agent_task_actions_search_harness.py`
- `tests/unit/test_agent_task_context_semantic_governance.py`
- `tests/integration/test_agent_task_triage_roundtrip.py`
- focused new `tests/unit/test_agent_task_*.py`,
  `tests/unit/test_agent_task_actions_search_harness_*.py`, and
  `tests/integration/test_agent_task_triage_roundtrip_*.py` families created by
  this packet
- owner routing and guardrails in `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`, and `config/hotspot_prevention.yaml`
- routing docs:
  `docs/agent_task_residual_owner_family_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md`

Out of scope:

- `tests/unit/test_agent_task_verifications.py` and other nonselected large
  test hotspots unless one must move to preserve equivalent or broader contract
  coverage for a selected root
- `app/services/technical_reports.py`, `app/services/semantic_orchestration.py`,
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/integration/test_postgres_roundtrip.py`, or the UI backlog
- closing the broader app or test backlog across the whole repository in this
  packet

## Owner Surfaces

- `docs/agent_task_residual_owner_family_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `config/hotspot_prevention.yaml`
- service roots and focused owners:
  `app/services/agent_tasks.py`,
  new `app/services/agent_task_dependencies.py`,
  new `app/services/agent_task_lifecycle.py`,
  new `app/services/agent_task_reads.py`, or equivalent focused owners chosen
  during Milestone 1;
  `app/services/agent_actions/search_harness.py` and new focused
  search-harness action owners;
  `app/services/agent_task_context_search_harness.py` and new focused
  search-harness context owners;
  `app/services/agent_actions/semantic_governance_actions.py` and new focused
  semantic-governance action owners if needed;
  `app/services/agent_task_context_semantic_governance.py` and new focused
  semantic-governance context owners
- focused unit and integration suites created by this packet, plus existing
  compatibility and contract tests that protect the public seams:
  `tests/unit/test_agent_action_contracts.py`,
  `tests/unit/test_agent_task_action_lookup.py`,
  `tests/unit/test_agent_task_actions.py`,
  `tests/unit/test_agent_task_context.py`,
  `tests/unit/test_agent_task_context_semantic.py`,
  `tests/unit/test_agent_task_triage.py`,
  `tests/unit/test_agent_task_worker.py`,
  `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`, and
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`

## Placement Rules

- Keep `app/services/agent_tasks.py` as the public entrypoint for task create,
  list, detail, outcome, approval, rejection, and trace export behavior, but
  move mixed implementation families into focused owners.
- Prefer one responsibility per new owner:
  dependency validation and graph checks,
  lifecycle state transitions,
  detail or trace read assembly,
  search-harness workflow stages,
  or semantic-governance builder families.
- Do not move residual implementation back into
  `app/services/agent_task_actions.py` or
  `app/services/agent_task_context.py`; those files are already closed
  compatibility facades.
- In the search-harness family, keep public action registration or manifest
  composition narrow. Split executors by workflow stage or scenario family
  instead of introducing another large “all harness actions” helper.
- In the semantic-governance family, keep
  `build_semantic_governance_context_builders(...)` as a composition seam and
  move draft, verify, and apply families into focused owners.
- Test decomposition must follow the owner or scenario family:
  dependency and lifecycle tests beside the agent-task root split,
  harness-stage tests beside the harness split,
  and semantic-governance builder tests beside the governance split.
- If a family-local test support module is needed, keep it beside that family,
  cap it at `400` lines, and do not use `conftest.py` or a new generic
  agent-task support sink to reaggregate the debt.

## Weak-Point Prevention Contract

Weak point forecast: the most likely failure modes are stale routing that
reopens the already-closed facades, fake service reduction that only pushes
logic into one new helper sink, a search-harness or triage split that weakens
coverage, semantic-governance decomposition that regrows the action or context
roots, and closeout that never gives the new tests and files explicit owner
routing.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A future session reopens `agent_task_actions.py` or `agent_task_context.py` instead of working in the residual owner family. | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `config/hotspot_prevention.yaml` | Milestone 0 routing refresh plus strict hotspot-prevention readback | The plan or routing docs claim the closed facades are still the active hotspot owners. | Add a temporary forbidden helper back to one closed facade and confirm hotspot-prevention rules or review rejects it. | A later session sees the stale architecture-quality list and dumps new implementation back into the wrong root file. |
| `app/services/agent_tasks.py` gets smaller only because mixed logic moved into one new broad helper. | `app/services/agent_tasks.py`, new `app/services/agent_task_*.py` owners, hygiene policy | `wc -l` review, `uv run docling-system-hygiene-check`, focused unit suites | Any new owner created by Milestone 1 exceeds `800` lines or mixes dependency, lifecycle, and read concerns in one file. | Leave a temporary `app/services/agent_task_core.py` importing everything and confirm the review or hygiene ratchet blocks the milestone. | A future session shrinks the root but recreates the same monolith under a different name. |
| Search-harness decomposition leaves the triage integration and unit roots monolithic or narrows assertions so the split looks green. | `app/services/agent_actions/search_harness.py`, `app/services/agent_task_context_search_harness.py`, `tests/unit/test_agent_task_actions_search_harness*.py`, `tests/integration/test_agent_task_triage_roundtrip*.py` | Focused search-harness unit and integration suites plus file-count readback | The root files are smaller, but `tests/unit/test_agent_task_actions_search_harness.py` or the triage integration root still carry mixed workflow families without equivalent or broader contract coverage. | Keep one temporary moved scenario only in the root and confirm the milestone checklist fails until it is rerouted or covered in a focused sibling file. | A future session splits executors but leaves one giant search-harness test file as the real change bottleneck. |
| Semantic-governance context work regrows the matching action owner or leaves the context-governance unit suite above budget. | `app/services/agent_task_context_semantic_governance.py`, `app/services/agent_actions/semantic_governance_actions.py`, `tests/unit/test_agent_task_context_semantic_governance.py` | `uv run docling-system-hygiene-check`, focused semantic-governance unit suites, `wc -l` readback | Any selected semantic-governance root remains above its declared budget after Milestone 3 without an explicit accepted residual and next routing target. | Add a temporary back-imported helper into the context root and confirm the focused semantic-governance suite and review force a narrower owner. | A future session splits one side of the governance workflow and leaves the other side as the next inherited monolith. |
| The triage integration split hides behavior loss in approval, learning, failure-artifact, or draft-review flows because only smoke still passes. | `tests/integration/test_agent_task_triage_roundtrip*.py`, family-local support, focused unit suites | DB-backed triage integration slice plus full DB-backed suite | Approval, outcome, or artifact contracts change without focused failing tests and without equivalent or broader contract coverage. | Temporarily remove a failure-artifact or approval assertion and confirm the focused triage integration family catches it. | A future session keeps one green smoke path while quietly dropping the higher-value negative-path coverage. |
| New service or test families never gain explicit owner-case and ratchet routing, so the next session has to rediscover the same debt. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, `config/hotspot_prevention.yaml` | Improvement-case validation, hygiene check, hotspot-prevention check | Selected new roots or residual files land without owner-case or ratchet updates in the same milestone. | Remove the new owner-case or hygiene entry in a temporary diff and confirm closeout blocks the commit. | A future session sees the split files but no durable routing, so the debt regrows through ambiguity. |

## Milestone Sequence

### Milestone 0 - Live Refresh And Owner-Case Bootstrap

Outcome label: reduced

Purpose: freeze the exact residual agent-task baseline and create the guardrails
before implementation starts.

Required work:

- Re-run the architecture probe, architecture-quality summary, hygiene check,
  improvement-case summary, and `wc -l` readback for the selected roots.
- Confirm that `app/services/agent_task_actions.py` and
  `app/services/agent_task_context.py` remain closed compatibility facades and
  that the active implementation brief is still the cycle packet rather than
  this follow-on.
- Create or refresh explicit improvement-case routing for the currently unowned
  triage and unit roots:
  `tests/integration/test_agent_task_triage_roundtrip.py`,
  `tests/unit/test_agent_tasks.py`, and
  `tests/unit/test_agent_task_actions_search_harness.py`.
- Add or refresh hotspot-prevention and hygiene baselines for the selected
  roots and expected successor families before broad code motion begins.
- Align `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` so this packet is named
  as the next routed follow-on behind the then-active cycle lane.

Acceptance criteria:

- This plan captures the live baseline counts for the selected roots.
- The then-active cycle packet and this follow-on are both routed explicitly in
  the handoff and architecture index.
- The missing owner-case gaps for triage and unit roots are eliminated or
  explicitly documented before implementation starts.
- Guardrail updates exist before the first implementation milestone broadens the
  file set.

### Milestone 1 - Agent Task Service Root Decomposition

Outcome label: resolved

Purpose: reduce `app/services/agent_tasks.py` to a narrow public orchestration
and compatibility surface.

Required work:

- Move dependency ID validation, dependency-kind augmentation, parent-task
  validation, and dependency-cycle logic into focused owner modules.
- Move detail or trace read assembly, outcome projection helpers, and related
  list or count helpers into focused read-model owners.
- Move approval, rejection, and outcome mutation rules into focused lifecycle
  owners.
- Preserve the public entrypoints
  `create_agent_task(...)`,
  `list_agent_tasks(...)`,
  `get_agent_task_detail(...)`,
  `list_agent_task_outcomes(...)`,
  `create_agent_task_outcome(...)`,
  `approve_agent_task(...)`,
  `reject_agent_task(...)`, and
  `export_agent_task_traces(...)`.
- Split `tests/unit/test_agent_tasks.py` into focused lifecycle, dependency,
  read-model, and analytics or recommendation suites while keeping any residual
  compatibility root narrow.

Acceptance criteria:

- `app/services/agent_tasks.py` closes at or below `600` lines.
- `tests/unit/test_agent_tasks.py` closes at or below `600` lines, and any new
  focused sibling files stay at or below `800`.
- The public task-service entrypoints and API-visible error codes remain stable.
- `IC-4098E8370B88` is refreshed with an exact verification contract and a
  measured post-split state, or an explicit named residual remains with a next
  routing target if Milestone 0 proves terminal closure is not yet honest.

### Milestone 2 - Search-Harness Residual Family Split

Outcome label: resolved

Purpose: retire the search-harness owner family as a remaining large-file and
test-monolith knot.

Required work:

- Split `app/services/agent_actions/search_harness.py` into focused executor
  owners for repair-case shaping, optimization or drafting, evaluation or
  verification, and apply or triage flow, or an equivalent narrower family
  layout proven by Milestone 0.
- Split `app/services/agent_task_context_search_harness.py` into matching
  focused context-builder owners without moving search-harness implementation
  back into `app/services/agent_task_context.py`.
- Split `tests/unit/test_agent_task_actions_search_harness.py` into focused
  workflow-stage or scenario suites.
- Move the search-harness-specific scenarios out of
  `tests/integration/test_agent_task_triage_roundtrip.py` into focused
  integration files with a family-local support module only if that support
  module stays at or below `400` lines.

Acceptance criteria:

- `app/services/agent_actions/search_harness.py`,
  `app/services/agent_task_context_search_harness.py`, and
  `tests/unit/test_agent_task_actions_search_harness.py` each close at or below
  `600` lines.
- Any new focused search-harness unit or integration sibling created by this
  milestone stays at or below `800` lines.
- Search-harness action definitions, context-builder names, evaluation output
  expectations, and draft or apply artifact contracts remain stable.
- The architecture probe and `wc -l` readback no longer list the selected
  search-harness roots above the large-file thresholds used by this packet.

### Milestone 3 - Semantic-Governance Residual Family Split

Outcome label: resolved

Purpose: retire the semantic-governance context and matching action-family
monoliths without reopening the closed orchestration facades.

Required work:

- Split `app/services/agent_task_context_semantic_governance.py` into focused
  owners for ontology-source resolution plus registry-update, ontology
  extension, and graph-promotion builder families.
- If the context split would otherwise leave the executor side as the next
  large owner, split `app/services/agent_actions/semantic_governance_actions.py`
  in the same milestone.
- Split `tests/unit/test_agent_task_context_semantic_governance.py` and any
  directly affected action-family test surfaces so the new family boundaries
  keep equivalent or broader contract coverage.

Acceptance criteria:

- `app/services/agent_task_context_semantic_governance.py`,
  `app/services/agent_actions/semantic_governance_actions.py`, and
  `tests/unit/test_agent_task_context_semantic_governance.py` each close at or
  below `600` lines.
- Semantic-governance context-builder names, action names, ontology-source
  resolution behavior, and draft or verify or apply artifact contracts remain
  stable.
- `uv run docling-system-hygiene-check` no longer reports inherited budget debt
  for the selected semantic-governance owner files.

### Milestone 4 - Triage Integration And Durable Closeout

Outcome label: resolved

Purpose: finish the agent-task residual family with explicit routing and no
selected root still above this packet's thresholds.

Required work:

- Decompose the remaining non-search-harness scenarios in
  `tests/integration/test_agent_task_triage_roundtrip.py` into focused files
  for replay-regression failure handling, approval lifecycle, learning
  surfaces, harness draft review, or equivalent scenario families proven by the
  Milestone 0 baseline.
- Keep only a narrow roundtrip smoke surface in the residual root if one still
  adds value.
- Refresh `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, and
  `config/hotspot_prevention.yaml` so the selected roots and any new focused
  successors have honest owner routing and exact post-closeout ratchets.
- Update this plan, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` to record the verified
  post-closeout state and the next backlog item after this packet.

Acceptance criteria:

- `tests/integration/test_agent_task_triage_roundtrip.py` closes at or below
  `800` lines.
- Any family-local support module created for the triage integration family
  closes at or below `400` lines, and no new focused triage integration file
  exceeds `800`.
- The selected roots from this packet no longer exceed their declared packet
  thresholds:
  `app/services/agent_tasks.py`,
  `app/services/agent_actions/search_harness.py`,
  `app/services/agent_task_context_search_harness.py`,
  `app/services/agent_actions/semantic_governance_actions.py`,
  `app/services/agent_task_context_semantic_governance.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_agent_task_actions_search_harness.py`,
  `tests/unit/test_agent_task_context_semantic_governance.py`, and
  `tests/integration/test_agent_task_triage_roundtrip.py`.
- The final routing docs and owner registers agree on the same active packet,
  closeout state, and next residual backlog item.

## Required Implementation Artifacts

- `docs/agent_task_residual_owner_family_milestone_plan.md`
- updated routing docs:
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`
- updated owner registers:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`
- focused agent-task service owners created by Milestones 1 through 3
- focused search-harness and semantic-governance owner files created by
  Milestones 2 and 3
- focused unit and integration suites created by Milestones 1 through 4
- any family-local support module created by Milestone 2 or 4

## Required Documentation And Handoff Updates

- Update this plan with milestone status, outcome labels, verification results,
  and closeout commit hashes as each milestone lands.
- Update `docs/SESSION_HANDOFF.md` after every milestone that changes the
  selected agent-task residual roots, owner routing, or next bounded packet.
- Update `docs/agentic_architecture_index.md` when this plan moves from drafted
  to active, from active to closed, or routes a narrower successor.
- Update `docs/boring_change_architecture_milestone_plan.md` so the umbrella
  brief points to this packet for the residual agent-task lane instead of
  leaving it buried inside generic test or app backlog bullets.
- If any case transitions lifecycle state, update
  `config/improvement_cases.yaml` and the matching hygiene or hotspot-prevention
  entries in the same milestone.

## Required Verification Gates

- Milestone 0 refresh:
  `git status -sb`
  `uv run docling-system-architecture-quality-report --summary`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  `uv run docling-system-hygiene-check`
  `uv run docling-system-improvement-case-summary`
  `wc -l app/services/agent_tasks.py app/services/agent_actions/search_harness.py app/services/agent_task_context_search_harness.py app/services/agent_actions/semantic_governance_actions.py app/services/agent_task_context_semantic_governance.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_actions_search_harness.py tests/unit/test_agent_task_context_semantic_governance.py tests/integration/test_agent_task_triage_roundtrip.py`
- Implementation milestones:
  `git diff --check`
  `uv run ruff check app/services/agent_tasks.py app/services/agent_task_*.py app/services/agent_actions/search_harness*.py app/services/agent_actions/semantic_governance*.py app/services/agent_task_context*.py tests/unit/test_agent_tasks*.py tests/unit/test_agent_task_actions_search_harness*.py tests/unit/test_agent_task_context_semantic_governance*.py tests/integration/test_agent_task_triage_roundtrip*.py config/improvement_cases.yaml config/hygiene_policy.yaml config/hotspot_prevention.yaml`
  `uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_semantic.py tests/unit/test_agent_task_triage.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks*.py tests/unit/test_agent_task_actions_search_harness*.py tests/unit/test_agent_task_context_semantic_governance*.py`
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip*.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
  `uv run docling-system-agent-task-action-index`
  `uv run docling-system-capability-contracts`
  `uv run docling-system-hotspot-prevention-check --strict`
  `uv run docling-system-hygiene-check`
  `uv run docling-system-improvement-case-validate`
  `uv run docling-system-architecture-inspect`
  `uv run docling-system-architecture-quality-report --summary`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  `wc -l app/services/agent_tasks.py app/services/agent_actions/search_harness.py app/services/agent_task_context_search_harness.py app/services/agent_actions/semantic_governance_actions.py app/services/agent_task_context_semantic_governance.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_actions_search_harness.py tests/unit/test_agent_task_context_semantic_governance.py tests/integration/test_agent_task_triage_roundtrip.py`
- Final runtime verification:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- The selected service and test roots in this packet all close at or below
  their declared thresholds by the end of Milestone 4.
- `app/services/agent_tasks.py` has a narrower owner contract than the Milestone
  0 baseline and no longer serves as a mixed dependency or lifecycle or detail
  or trace implementation sink.
- The search-harness and semantic-governance residual families no longer appear
  in hygiene as inherited over-budget owner files for the exact surfaces
  selected by this packet.
- Triage integration coverage, approval or rejection coverage, outcome and
  artifact coverage, harness draft or apply coverage, and semantic-governance
  builder coverage all retain equivalent or broader contract coverage than the
  pre-change suites.
- `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, and
  `config/hotspot_prevention.yaml` reflect the true residual owners rather than
  stale root facades or unowned new files.
- Do not weaken tests, fixtures, or gates to reach a green closeout.
  Replacement coverage must provide equivalent or broader contract coverage
  than the checks this packet replaces.
- The active handoff, architecture index, and umbrella brief all agree on the
  state of this packet and the next residual backlog item.

## Stop Conditions

- Stop if Milestone 0 shows the selected residual agent-task roots are no
  longer the honest next routed residual family after the live rebaseline.
- Stop if the only available way to close one selected root is to regrow
  `app/services/agent_task_actions.py` or `app/services/agent_task_context.py`.
- Stop if a split requires a public API, schema, DB, or persisted artifact
  contract change that cannot remain compatibility-first.
- Stop if decomposition only works by moving the same mixed ownership into one
  new service helper or one new cross-family test support sink.
- Stop before commit if the focused unit or integration suite, the owner-case
  validation, or the full DB-backed verification stack fails.
- Stop before commit if unrelated dirty worktree changes cannot be safely
  separated from the milestone slice.

## Local Commit Closeout Policy

Every milestone is complete only after verification passes, the required docs
and handoff updates land, and a local atomic commit records the milestone
slice. Before that point the milestone is ready-to-close, not complete.

For each milestone:

- stage only the verified agent-task residual owner-family slice
- leave unrelated dirty or untracked files alone
- include code, tests, owner-register updates, and docs or handoff changes that
  describe the milestone in the same commit
- record the closeout commit hash in this plan and in `docs/SESSION_HANDOFF.md`
- do not mark a milestone complete if the green result came from narrower or
  easier coverage rather than equivalent or broader contract coverage

## Residual Risks And Next Milestone Routing

- This packet is now durably recorded as the latest resolved bounded
  implementation brief in the 2026-05-18 closeout.
- After this packet closes, the broader backlog should return to
  `docs/boring_change_architecture_milestone_plan.md`, with
  `docs/db_models_residual_owner_family_milestone_plan.md` as the next active
  bounded packet, rather than keeping this packet open for unrelated large
  files.
- If Milestone 1 through 3 reduce the selected roots but leave one focused
  successor honestly above the default `600`-line budget, mark that exact
  subfamily `reduced`, give it explicit owner routing, and spin a fresh narrow
  follow-on instead of widening this packet.

## Closeout Checklist

- [ ] Milestone 0 freshness readback captured and owner-case gaps closed
- [ ] `app/services/agent_tasks.py` reduced to a narrow public seam
- [ ] search-harness action and context family roots reduced below packet thresholds
- [ ] semantic-governance action and context family roots reduced below packet thresholds
- [ ] triage integration and matching unit monoliths decomposed into focused families
- [ ] improvement-case, hygiene, and hotspot-prevention routing updated
- [ ] focused unit and integration verification passed
- [ ] full DB-backed verification passed
- [ ] plan, handoff, architecture index, and umbrella brief updated
- [ ] atomic closeout commit recorded for each completed milestone
