# Agent-Task Orchestration Boundary Milestone Plan

Date: 2026-05-12 local / 2026-05-13 UTC
Status: Milestone 2 implemented locally on 2026-05-12; Milestone 3 Semantic
Governance Family Composition is next
Owner context: dedicated follow-on plan for `IC-A1E186A34097` /
`app/services/agent_task_actions.py` and `IC-E52B6C7B22FD` /
`app/services/agent_task_context.py` after the Residual Weakness Plan cycle
break and the first report-action family split.

## Local Progress

Milestone 2 is now implemented locally in the working tree. The Milestone 1
registry-composition baseline remains relevant as the before-state, but the
current local checkpoint has already completed the search-harness execution and
specialized context extraction slice.

Local Milestone 2 snapshot:

- `app/services/agent_task_actions.py` no longer owns the remaining
  search-harness executors; that owner family now lives in
  `app/services/agent_actions/search_harness.py`
- `app/services/agent_task_context.py` no longer owns the remaining
  search-harness context builders or `evaluate_claim_support_judge`; those
  builders now live in
  `app/services/agent_task_context_search_harness.py` and
  `app/services/agent_task_context_technical_reports.py`
- `app/services/agent_task_actions.py` is reduced to 1,504 lines / 25 private
  helpers and `app/services/agent_task_context.py` is reduced to 2,950 lines /
  31 private helpers
- `config/hygiene_policy.yaml` now also ratchets
  `app/services/agent_actions/search_harness.py` at 1,078 lines and
  `app/services/agent_task_context_search_harness.py` at 867 lines under the
  same owner cases while keeping the central facade ratchets in place
- `config/hotspot_prevention.yaml` now carries the narrow
  `agent-task-context-milestone-2-reflow` exception so strict mode stays green
  while the context facade shrinks through owner-module extraction
- `config/improvement_cases.yaml`, `docs/agentic_architecture_index.md`, and
  `docs/SESSION_HANDOFF.md` now record the reduced central-facade measurements
  and the next semantic-governance slice
- `uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_actions_search_harness.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_triage.py tests/unit/test_hotspot_prevention.py`:
  `160 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_claim_support_judge_evaluation_roundtrip.py`:
  `4 passed`
- `uv run docling-system-agent-task-action-index` still emits
  `schema_name=agent_action_index`, `schema_version=1.0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `known_hotspots=7`, `changed_hotspots=3`, `blocked=0`, `exceptions=9`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`:
  `valid=true`, `violation_count=0`
- architecture probe now routes the active execution hotspot to
  `app/services/agent_task_actions.py` at 1,504 lines / score `90240`; the
  paired context facade is next at 2,950 lines / score `70800`
- next milestone boundary: Milestone 3 Semantic Governance Family Composition

## Purpose

Resolve the remaining technical debt in the agent-task orchestration boundary
end to end.

The scoped problem is no longer the old large import cycle. That was already
reduced by introducing `app/services/agent_task_action_lookup.py`. The
remaining debt is that `app/services/agent_task_actions.py` still owns too much
action definition, executor wiring, and contract assembly, while
`app/services/agent_task_context.py` still owns too much context-builder
implementation, context registry composition, and persistence-adjacent context
assembly.

This plan resolves that debt by finishing the boundary shape the repo is
already moving toward:

- `app/services/agent_task_actions.py` becomes a narrow compatibility and
  composition facade for action definitions, validation, and worker execution.
- `app/services/agent_task_context.py` becomes a narrow compatibility and
  composition facade for context-builder lookup, context assembly entrypoints,
  and context artifact writing.
- Family-owned implementation moves into `app/services/agent_actions/*.py` and
  `app/services/agent_task_context_*.py`.
- Verification is preserved or strengthened. No milestone may reduce coverage,
  delete assertions, or narrow runtime checks merely to get green results.

## Current Evidence

Live repo evidence refreshed on 2026-05-12 local / 2026-05-13 UTC:

```text
uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=541.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py,
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app/services/agent_task_actions.py: 1504 lines, score 90240, fan-out 29
  app/services/agent_task_context.py: 2950 lines, score 70800, fan-out 14
  Python cycle components: 3

wc -l app/services/agent_task_actions.py app/services/agent_actions/search_harness.py app/services/agent_task_context.py app/services/agent_task_context_search_harness.py
  1504 app/services/agent_task_actions.py
  1078 app/services/agent_actions/search_harness.py
  2950 app/services/agent_task_context.py
   867 app/services/agent_task_context_search_harness.py

uv run docling-system-improvement-case-summary
  case_count=28
  status_counts.open=23
  status_counts.deployed=4
  status_counts.measured=1
  measured_case_count=17

config/improvement_cases.yaml
  IC-A1E186A34097 = open hotspot case for app/services/agent_task_actions.py
  IC-E52B6C7B22FD = open hotspot case for app/services/agent_task_context.py
  IC-6C1B516A3F92 = open hygiene follow-on for
  app/hotspot_prevention_classifier.py

config/hotspot_prevention.yaml
  app/services/agent_task_actions.py blocks new executor_implementation,
  action_family_helper, and schema_builder additions and routes them to
  app/services/agent_actions/
  app/services/agent_task_context.py blocks new
  context_builder_implementation and context_family_helper additions and
  routes them to app/services/agent_task_context_*.py

config/hygiene_policy.yaml
  app/services/agent_task_actions.py is ratcheted at 2081 lines and 35 private helpers
  app/services/agent_actions/search_harness.py is ratcheted at 1078 lines
  app/services/agent_task_context.py is ratcheted at 3833 lines and 38
  private helpers under owner case IC-E52B6C7B22FD
  app/services/agent_task_context_search_harness.py is ratcheted at 867 lines
```

Current structural evidence:

- `app/services/agent_task_actions.py` now composes the public action catalog
  from owner-family registries and no longer owns the remaining search-harness
  executor implementations. The remaining debt is concentrated in the
  semantic-governance and semantic-analysis families plus the worker execution
  facade.
- `app/services/agent_task_context.py` now composes `_CONTEXT_BUILDERS` from
  owner-family registry modules and no longer owns the remaining
  search-harness or `evaluate_claim_support_judge` builders. The remaining debt
  is concentrated in the semantic builder families and the central artifact
  entrypoints.
- `app/services/agent_task_action_lookup.py` is the current directional seam.
  `app/services/agent_task_context.py`, `app/services/agent_task_context_store.py`,
  and `app/services/agent_tasks.py` must keep using that seam instead of
  statically importing the executor facade.
- `tests/unit/test_agent_task_action_lookup.py` already proves public action
  identity and blocks the old static back edge into
  `app.services.agent_task_actions`.
- Existing owner families now own the registry-composition seams under
  `app/services/agent_actions/*.py` and
  `app/services/agent_task_context_*.py`. The remaining debt is semantic-family
  implementation extraction, not missing composition contracts or search-
  harness ownership.

## Goal

Resolve the agent-task orchestration boundary debt so that:

- `app/services/agent_task_actions.py` and `app/services/agent_task_context.py`
  are both narrow compatibility and composition facades rather than primary
  implementation surfaces.
- Both files end under explicit facade budgets of `max_lines <= 600` and
  `max_private_helpers <= 20`.
- New action-family implementation lands in `app/services/agent_actions/*.py`.
- New context-builder implementation lands in `app/services/agent_task_context_*.py`.
- The lookup seam remains the only allowed static bridge from context/task
  services into action metadata and validation.
- Action type names, context-builder names, input/output models, action-index
  output, `/agent-tasks/actions` behavior, worker execution semantics, and
  persisted context artifact contracts remain stable unless a later explicit
  contract-change milestone says otherwise.
- Verification remains at least as strong as it is now.

## Non-Goals

- No microservice extraction.
- No rewrite of the agent-task worker, task persistence model, or task API.
- No task type rename, context-builder rename, schema-name change, or payload
  contract change.
- No broad semantic or claim-support business-logic rewrite outside the bounded
  owner-family moves needed to complete the orchestration split.
- No deletion, loosening, or narrowing of tests, contract checks, or DB-backed
  integration gates just to satisfy the split.
- No umbrella commit that mixes this boundary work with unrelated dirty local
  evidence-split changes.

## Scope

In scope:

- `app/services/agent_task_actions.py`
- `app/services/agent_task_context.py`
- `app/services/agent_task_context_store.py`
- `app/services/agent_task_context_resolvers.py`
- `app/services/agent_task_action_lookup.py`
- `app/services/agent_actions/*.py`
- new `app/services/agent_task_context_*.py` family modules
- family-specific unit and integration tests that protect action definitions,
  context-builder composition, lookup identity, and DB-backed task execution
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- this plan

Out of scope:

- unrelated search, evidence, UI, parser, or ORM hotspot work
- new agent-task capabilities not already represented in the current public
  action catalog
- schema or migration changes not strictly required to preserve current runtime
  behavior
- weakening architecture or hygiene thresholds to match the current monoliths

## Owner Surfaces

- action facade and public contracts:
  `app/services/agent_task_actions.py`,
  `app/services/agent_task_action_lookup.py`,
  `app/services/agent_actions/__init__.py`,
  `app/services/agent_actions/types.py`,
  `app/services/agent_actions/manifest.py`
- context facade and context composition:
  `app/services/agent_task_context.py`,
  `app/services/agent_task_context_store.py`,
  `app/services/agent_task_context_resolvers.py`,
  new `app/services/agent_task_context_*.py`
- current action owner modules:
  `app/services/agent_actions/evaluation_actions.py`,
  `app/services/agent_actions/evaluation.py`,
  `app/services/agent_actions/semantic_*_actions.py`,
  `app/services/agent_actions/report_actions.py`,
  `app/services/agent_actions/claim_support_actions.py`,
  `app/services/agent_actions/claim_support_*.py`,
  `app/services/agent_actions/search_harness.py`,
  `app/services/agent_actions/document_lifecycle_actions.py`
- current context owner modules:
  `app/services/agent_task_context_core.py`,
  `app/services/agent_task_context_semantic.py`,
  `app/services/agent_task_context_technical_reports.py`,
  `app/services/agent_task_context_search_harness.py`
- tests and gates:
  `tests/unit/test_agent_action_contracts.py`,
  `tests/unit/test_agent_task_action_lookup.py`,
  `tests/unit/test_agent_task_actions.py`,
  `tests/unit/test_agent_task_context.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_agent_task_worker.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`,
  `tests/integration/test_agent_task_triage_roundtrip.py`,
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- governance and routing:
  `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`

## Placement Rules

- Keep `app/services/agent_task_actions.py` as the public executor registry,
  action-definition lookup facade, and worker execution entrypoint until the
  final closeout milestone proves the narrow facade shape.
- Keep `app/services/agent_task_context.py` as the public context-builder
  lookup facade and context artifact entrypoint until the final closeout
  milestone proves the narrow facade shape.
- New action definitions and executors must live in
  `app/services/agent_actions/*.py`. Reuse existing family files when the
  concern already belongs there.
- New context-builder families must live in
  `app/services/agent_task_context_*.py`. Do not add new long-lived builder
  functions directly to `app/services/agent_task_context.py`.
- `app/services/agent_task_action_lookup.py` remains the only allowed static
  lookup seam from context/task services into action metadata and validation.
  Context, task, worker, and API services must not statically import
  `app.services.agent_task_actions`.
- The public task catalog must continue to be generated from family-owned action
  definitions rather than ad hoc tuple or dict copies.
- Context-builder names must remain stable and must continue to round-trip
  through `tests/unit/test_agent_action_contracts.py`,
  `tests/unit/test_agent_task_action_lookup.py`, the action index, and the
  `/agent-tasks/actions` API surface.
- If a family split requires a new helper module, put the helper beside the
  family owner module instead of back in a central facade.

## Weak-Point Prevention Contract

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation |
| --- | --- | --- | --- | --- |
| New executor logic lands back in the action facade | `app/services/agent_task_actions.py`, `config/hotspot_prevention.yaml` | `uv run docling-system-hotspot-prevention-check --strict` plus focused prevention tests | Any new `executor_implementation`, `action_family_helper`, or `schema_builder` lands in `app/services/agent_task_actions.py` without an approved exception | A fixture diff that adds an inline executor or action helper to `app/services/agent_task_actions.py` must fail strict mode |
| New context-builder implementation lands back in the context facade | `app/services/agent_task_context.py`, `config/hotspot_prevention.yaml`, `config/hygiene_policy.yaml` | strict hotspot prevention plus hygiene ratchet tests | Any new builder-family implementation or large helper lands in `app/services/agent_task_context.py` instead of `app/services/agent_task_context_*.py` | A fixture diff that adds a new `_build_*_context` function to `app/services/agent_task_context.py` must fail strict mode |
| Context and task services reintroduce a static back edge to the action facade | `app/services/agent_task_action_lookup.py`, `tests/unit/test_agent_task_action_lookup.py` | lookup seam test plus architecture probe | `app/services/agent_task_context.py`, `app/services/agent_task_context_store.py`, or `app/services/agent_tasks.py` statically imports `app.services.agent_task_actions` | A negative test import fixture or temporary back-edge change must fail the lookup seam test |
| Action definitions and context builders drift out of sync | `app/services/agent_actions/*.py`, `app/services/agent_task_context*.py`, contract tests | `uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py` plus `uv run docling-system-agent-task-action-index` | A registered action references a missing context builder, duplicate task type, stale output schema, or drifted catalog row | Existing negative tests for stale context builders must remain, and new family-composition tests must prove duplicates fail |
| A split gets green by weakening verification | touched tests, gates, and this plan | side-by-side gate review plus full final DB-backed suite | Assertions are removed, integration scope is narrowed, or gate thresholds are loosened without stronger replacement evidence | Milestone verification must include the replaced test files and a focused explanation of stronger or equivalent coverage in docs/handoff |
| Runtime behavior changes behind stable task names | action definitions, API route, worker path, context artifact path | focused unit tests, `/agent-tasks/actions` route tests, DB-backed roundtrips | Task type names, side-effect levels, approval behavior, context output shape, or action index output changes unexpectedly | Add or preserve API-boundary and DB-backed roundtrip tests that fail on contract drift |

Future-Codex misuse scenario: the likely wrong move is adding “just one more”
action definition or `_build_*_context` helper to the central facade because it
already has the imports. Every milestone below must leave behind a more obvious
family owner module and a stricter prevention gate so that the wrong location
fails before commit.

## Milestone Sequence

### Milestone 0: Boundary Baseline And Governance Expansion

Outcome label: resolved

Purpose: resolve the current governance gap before more split work begins by
making the whole orchestration boundary, not only `agent_task_actions.py`,
subject to explicit owner routing and diff-time prevention.

Scope:

- Refresh the current live line counts, hotspot scores, fan-out, and cycle
  evidence for `app/services/agent_task_actions.py` and
  `app/services/agent_task_context.py`.
- Extend `config/hotspot_prevention.yaml` so `app/services/agent_task_context.py`
  blocks new context-builder implementation and routes it to
  `app/services/agent_task_context_*.py`.
- Convert the current broad `app/services/agent_task_context.py` budget into an
  explicit ratcheted owner case tied to `IC-E52B6C7B22FD` in
  `config/hygiene_policy.yaml`.
- Add or extend prevention tests so both central files have controlled
  violations that fail before commit.

Acceptance:

- `app/services/agent_task_context.py` has explicit prevention policy and owner
  routing equivalent in strength to the current `agent_task_actions.py` policy.
- Strict hotspot prevention fails on controlled additions to either central
  facade.
- Hygiene policy no longer treats `app/services/agent_task_context.py` as an
  unowned broad allowance.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_hotspot_prevention.py tests/unit/test_agent_task_action_lookup.py
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-architecture-inspect
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

### Milestone 1: Registry Composition Contract

Outcome label: resolved

Purpose: resolve the enabling-architecture gap by establishing one composition
pattern for action families and one composition pattern for context-builder
families before moving more logic.

Scope:

- Introduce family registry builders so action definitions are composed from
  owner modules instead of assembled primarily inline in
  `app/services/agent_task_actions.py`.
- Introduce family builder registries so context-builder ownership can be
  composed from `app/services/agent_task_context_*.py` instead of remaining
  inline in `app/services/agent_task_context.py`.
- Preserve the public `list_agent_task_actions()`, action-index, action-manifest,
  validation, `get_agent_task_context_builder()`, `build_agent_task_context()`,
  and `write_agent_task_context()` entrypoints.
- Add negative tests for duplicate task types, duplicate context-builder names,
  and stale composition entries.

Acceptance:

- Both central files compose owner-family registries rather than defining the
  entire catalog inline.
- Contract tests prove that duplicate or stale family composition fails fast.
- `uv run docling-system-agent-task-action-index` still emits the same public
  schema and task catalog shape.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_action_lookup.py
uv run docling-system-agent-task-action-index
uv run docling-system-capability-contracts
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-architecture-inspect
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

### Milestone 2: Search-Harness Execution And Specialized Context Extraction

Outcome label: reduced

Purpose: reduce the next largest non-semantic orchestration slice by moving
remaining search-harness execution wiring and specialized context-builder
implementation behind the Milestone 1 registry seams.

Local status: implemented locally on 2026-05-12. The next bounded execution
slice is Milestone 3 Semantic Governance Family Composition.

Scope:

- Move the remaining search-harness executor implementations and helper logic
  out of `app/services/agent_task_actions.py` into
  `app/services/agent_actions/search_harness.py` or focused sibling owner
  modules if that yields a cleaner end state.
- Move the remaining non-generic search-harness context builders out of
  `app/services/agent_task_context.py` into
  `app/services/agent_task_context_search_harness.py`.
- Move the `evaluate_claim_support_judge` context builder out of
  `app/services/agent_task_context.py` into
  `app/services/agent_task_context_technical_reports.py`.
- Keep evaluation actions on the shared `generic` context builder unless a
  live contract need emerges; do not create a synthetic owner module only to
  mirror the pre-Milestone-1 wording.
- Preserve task names, context-builder names, approval semantics, and output
  schemas for every moved slice.

Acceptance:

- Search-harness executors no longer live primarily in
  `app/services/agent_task_actions.py`.
- Search-harness and `evaluate_claim_support_judge` context builders no longer
  live primarily in `app/services/agent_task_context.py`.
- Public lookup identity, validation defaults, and action-index output remain
  unchanged.
- `app/services/agent_task_actions.py` and `app/services/agent_task_context.py`
  both shrink materially from the Milestone 1 baseline.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks_api.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_claim_support_judge_evaluation_roundtrip.py
uv run docling-system-agent-task-action-index
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-capability-contracts
uv run docling-system-architecture-inspect
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

### Milestone 3: Semantic Governance Family Composition

Outcome label: reduced

Purpose: reduce the remaining orchestration debt by extracting the bounded
semantic-governance family that is centered on registry updates, ontology
changes, and promotion workflows.

Scope:

- Move draft, verify, and apply action definitions plus executor wiring for
  semantic registry updates, ontology extension, and graph promotions into
  family-owned `app/services/agent_actions/*.py` modules.
- Move the matching context builders into dedicated
  `app/services/agent_task_context_*.py` owner modules.
- Keep `app/services/agent_task_actions.py` and
  `app/services/agent_task_context.py` as composition facades only.
- Preserve static dependency direction through `agent_task_action_lookup`.

Acceptance:

- Semantic-governance action and context families are no longer primarily owned
  by the central files.
- No new Python cycle component appears, and the old lookup seam remains intact.
- Hotspot and fan-out measurements continue to move down from the Milestone 2
  baseline.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py
uv run docling-system-agent-task-action-index
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-capability-contracts
uv run docling-system-architecture-inspect
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

### Milestone 4: Semantic Analysis, Generation, And Triage Family Composition

Outcome label: reduced

Purpose: reduce the final large action and context families that still keep the
central orchestration surfaces broad after the governance-oriented moves.

Scope:

- Move the remaining semantic analysis, generation, graph-construction, and
  triage action families into owner modules under `app/services/agent_actions/`.
- Move the matching context-builder families into owner modules under
  `app/services/agent_task_context_*.py`.
- Preserve existing public task types including semantic-pass, disagreement,
  generation-brief, grounded-document, and graph-construction workflows.
- Add focused family tests instead of growing the broad compatibility files.

Acceptance:

- The remaining semantic action and context families no longer live primarily
  in the two central orchestration files.
- The central files are reduced to composition, lookup, validation, and
  artifact-entrypoint responsibilities.
- Focused family tests exist for the moved surfaces, and no equivalent or
  stronger existing coverage is removed without replacement proof.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py
uv run docling-system-agent-task-action-index
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-capability-contracts
uv run docling-system-architecture-inspect
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

### Milestone 5: Facade Closeout And Case Lifecycle Alignment

Outcome label: resolved

Purpose: prove that the orchestration boundary debt is actually closed rather
than merely redistributed.

Scope:

- Reduce `app/services/agent_task_actions.py` to a stable composition facade
  with verified budgets of `max_lines <= 600` and `max_private_helpers <= 20`.
- Reduce `app/services/agent_task_context.py` to a stable composition facade
  with verified budgets of `max_lines <= 600` and `max_private_helpers <= 20`.
- Ratchet both files and all new family-owner modules in
  `config/hygiene_policy.yaml` to the verified post-closeout counts.
- Update `config/improvement_cases.yaml` so `IC-A1E186A34097` and
  `IC-E52B6C7B22FD` record deployed refs, current measurements, and the final
  narrow-owner outcome.
- Update the plan, architecture index, and session handoff with exact final
  verification evidence and the next routed hotspot.
- Prove that the final shape did not get green by weakening verification.

Acceptance:

- `app/services/agent_task_actions.py` is at or below 600 lines and 20 private
  helpers.
- `app/services/agent_task_context.py` is at or below 600 lines and 20 private
  helpers.
- Both files are governed as narrow facades in hotspot prevention and hygiene
  policy.
- Family-owned action definitions and context builders live outside the central
  files.
- Lookup seam tests, contract tests, action-index generation, API behavior, and
  DB-backed roundtrips remain green.
- `IC-A1E186A34097` and `IC-E52B6C7B22FD` can transition to deployed because
  their acceptance condition is met by a narrower verified owner contract and
  improved measurements.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks_api.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py
uv run docling-system-agent-task-action-index
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-capability-contracts
uv run docling-system-architecture-inspect
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

## Required Implementation Artifacts

- extended hotspot prevention rules for `app/services/agent_task_context.py`
- explicit hygiene-owner routing for `IC-E52B6C7B22FD`
- family composition helpers or registries for action definitions
- family composition helpers or registries for context builders
- new `app/services/agent_task_context_*.py` owner modules
- updated `app/services/agent_actions/*.py` owner modules
- focused tests for composition, duplicate prevention, and family routing
- refreshed improvement-case measurements and deployed refs

## Required Documentation And Handoff Updates

Every milestone must update the affected durable docs before commit. At minimum:

- this plan
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- any architecture boundary doc that changes the described owner surfaces,
  including `docs/architecture_boundaries.md` when the final composition pattern
  changes how future sessions should place work

The handoff must record:

- completed milestone number and outcome label
- exact verification commands
- exact pass counts or key report outputs
- commit hash
- residual risks
- the next routed hotspot or owner case

## Required Verification Gates

These gates are mandatory throughout the plan:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py
uv run docling-system-agent-task-action-index
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

Additional milestone-specific gates are mandatory when their surfaces are
touched:

- route or catalog behavior:
  `uv run pytest -q tests/unit/test_agent_tasks_api.py`
- semantic orchestration moves:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py`
- claim-support action or context moves:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- final milestone closeout:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

No milestone may replace one of these with a weaker command unless the
replacement is strictly stronger and that proof is written into the plan update
and handoff.

## Acceptance Criteria

- Each milestone closes with exact command evidence, not prose-only claims.
- No milestone is complete until implementation, tests, docs, and handoff
  updates are committed together in one local atomic commit.
- `app/services/agent_task_actions.py` never gains new broad implementation
  categories after Milestone 0.
- `app/services/agent_task_context.py` never gains new broad implementation
  categories after Milestone 0.
- The public action catalog, action index, lookup identity, validation defaults,
  context-builder names, and DB-backed task execution continue to behave the
  same from the caller perspective.
- Any test that is split or replaced must demonstrate equal or stronger
  contract coverage. Removing assertions, shrinking integration scope, or
  weakening thresholds is a milestone failure.
- The final milestone is not `resolved` unless both central files are under
  their facade budgets and both owner cases can transition with current
  measurements and deployed refs.

## Stop Conditions

- Stop if a proposed move requires renaming task types, renaming
  context-builder names, or changing output schema names to make the split
  work.
- Stop if a family cannot be made directional without reintroducing a static
  import cycle through `app.services.agent_task_actions`.
- Stop if preserving runtime behavior would require touching unrelated hotspot
  families in the same milestone commit.
- Stop if focused family tests or DB-backed roundtrips fail and the failure
  cannot be fixed inside the scoped milestone.
- Stop if unrelated dirty worktree changes cannot be separated safely from the
  milestone slice.
- Stop if a milestone would need to loosen hotspot prevention, hygiene budgets,
  contract tests, or integration coverage in order to pass.

## Local Commit Closeout Policy

- Stage only the verified milestone slice.
- Leave unrelated dirty or untracked files alone.
- Commit implementation, tests, configs, docs, generated evidence, and handoff
  updates for that milestone together.
- Record the commit hash in `docs/SESSION_HANDOFF.md` and the active plan.
- Do not mark a milestone complete until the commit exists.
- Do not push unless the user explicitly requests it.

## Residual Risks And Next Milestone Routing

- The most likely execution risk is that the semantic family is still too broad
  for one milestone. If that happens, split the semantic work into smaller
  owner-family commits, but do not collapse multiple broad families into one
  “cleanup” milestone.
- If Milestone 5 completes and either central file is still above its facade
  budget, the plan is not finished. Add another bounded milestone under this
  same plan rather than claiming `resolved`.
- If the final architecture-quality report still routes either file because of
  short-term churn but the file is now a verified narrow facade, document that
  distinction explicitly in the improvement-case measurement notes and handoff.
- After this plan resolves, the next routed hotspot should come from the then
  current architecture-quality summary, expected to be outside the
  agent-task orchestration boundary unless live measurements prove otherwise.
