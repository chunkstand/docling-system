# Ontology Evolution Lifecycle Milestone Plan

Date: 2026-05-21 local / 2026-05-21 UTC
Status: in_progress in the current 2026-05-21 checkout. Milestones 0, 1, and
2 are now resolved locally. The repo no longer treats
split/merge/deprecate/replace/migrate as blocked prose-only intent: the
versioned lifecycle contract now lives in
`app/services/semantic_registry_operation_contracts.py`, the concrete draft
mutation owner now lives in
`app/services/semantic_registry_operation_mutations.py`, and
`DraftOntologyExtensionTaskInput` in `app/schemas/agent_task_semantics.py`
now accepts explicit machine-readable lifecycle operations without requiring a
source task. Milestone 2 now adds typed lifecycle verification previews in
`app/services/semantic_ontology_lifecycle_previews.py`, records that preview
evidence in `VerifyDraftOntologyExtensionTaskOutput` and
`ApplyOntologyExtensionTaskOutput`, and blocks lifecycle publication when the
verification output cannot prove document-level preview signals for every
non-additive operation. Milestone 3, the final docs-and-routing closeout,
remains open.
Owner context: standalone follow-on after
`docs/ontology_contract_refoundation_milestone_plan.md` closes. This packet
does not reopen the canonical contract scaffold or the runtime-readiness
closeout; it adds the missing non-additive ontology evolution lifecycle on top
of the now-refounded contract.

## Purpose

Close the remaining ontology governance gap after refoundation: the repo now
has a canonical layered ontology contract, first-class ontology slices,
dedicated ontology-eval gates, and contract-aware runtime readiness, but
ontology change workflows are still additive-only.

Report-generation and governance agents eventually need explicit, reviewable
operations for split, merge, deprecate, replace, and migrate so the ontology
can evolve without hidden manual rewrites or silent semantic drift.

## Current Evidence

- `app/services/semantic_registry_operation_contracts.py` now exposes the
  versioned lifecycle contract through
  `SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION`,
  `SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES`, and
  `validate_semantic_registry_operations(...)`, so split/merge/deprecate/
  replace/migrate operations are first-class supported types rather than
  blocked placeholders.
- `app/services/semantic_registry_operation_mutations.py` now owns the
  effective-ontology mutation rules for additive and lifecycle operations,
  including predecessor/successor lineage fields and successor concept
  materialization, while `app/services/semantic_orchestration.py` stays below
  the hygiene ratchet as a thinner draft/verification owner.
- `app/schemas/agent_task_semantics.py` now records the lifecycle surface
  directly in `SemanticRegistryUpdateOperation`, adds structured
  `successor_concepts`, versions ontology draft payloads through
  `operation_contract_version`, and allows `DraftOntologyExtensionTaskInput`
  to draft explicit lifecycle operations without a source task when the draft
  is operator-authored rather than triage- or bootstrap-derived.
- `app/services/semantic_ontology.py` and the ontology task-context owners now
  expose contract metadata, ontology slices, and competency families, and the
  ontology draft action owner now accepts explicit lifecycle operations through
  the same `draft_ontology_extension` task family instead of introducing a
  parallel task or side channel.
- `app/services/semantic_ontology_lifecycle_previews.py` now owns the
  lifecycle-specific document preview contract for verification and apply:
  every split/merge/deprecate/replace/migrate operation now produces a typed
  per-operation preview over the selected documents, verification fails when
  any non-additive operation has no document-level signal, and apply refuses
  lifecycle drafts unless that explicit preview evidence is present and
  complete.
- `app/schemas/agent_task_semantics.py`,
  `app/services/agent_actions/semantic_governance_ontology_actions.py`, and
  `app/services/agent_task_context_semantic_governance_ontology.py` now carry
  that lifecycle preview evidence through the existing verify/apply task
  family without breaking task identities or removing prior payload fields.
- `tests/unit/test_ontology_evolution_lifecycle_baseline.py` now pins the
  lifecycle contract surface, the direct mutation lineage semantics, and the
  current draft/verify/apply ontology payload fields, while
  `tests/unit/test_agent_task_actions_ontology.py`,
  `tests/unit/test_agent_task_context_semantic_governance_ontology.py`, and
  `tests/integration/test_portable_ontology_roundtrip.py` now prove the new
  manual lifecycle draft path plus the document-preview verification and apply
  adoption path through the real task worker stack.
- `docs/ontology_contract_refoundation_milestone_plan.md` is resolved locally
  in the current checkout after the final readiness and portable-roundtrip
  slice, and `docs/SESSION_HANDOFF.md` routes this packet as the remaining
  ontology-specific follow-on.
- The canonical contract and compatibility views are still versioned and
  hashable, so lifecycle changes can be verified against concrete pre/post
  ontology snapshots rather than inferred from prose.

## Goal

Add a bounded ontology evolution lifecycle that:

- supports non-additive draft operations for split, merge, deprecate, replace,
  and migrate
- verifies lifecycle drafts against document-level regression previews before
  publication
- preserves the existing ontology task identities and machine-readable payload
  contracts unless an exact failing test proves the current contract is wrong
- records lifecycle intent and migration effects in durable runtime payloads,
  docs, and tests instead of relying on chat-only operator judgment

## Non-Goals

- No second ontology or corpus-specific parallel contract.
- No broad rewrite of semantic extraction, semantic graph promotion, or search.
- No DB or Alembic change unless Milestone 0 proves the current snapshot and
  payload storage cannot represent the required lifecycle refs.
- No weakening of ontology, semantic, or integration tests to produce a green
  result.

## Scope

In scope:

- `app/services/semantic_orchestration.py`
- `app/services/semantic_ontology.py`
- focused lifecycle sibling owners under `app/services/`
- ontology task-context and schema owners only where lifecycle payloads must be
  surfaced:
  `app/services/agent_task_context_semantic_governance_ontology.py`,
  `app/schemas/agent_task_semantics.py`
- focused ontology lifecycle tests and integration roundtrips
- durable docs and routing surfaces:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`

Out of scope:

- reopening the refoundation contract compiler or export stack
- broad `semantic_graph_core.py` or `semantic_generation.py` rework unless a
  narrowly bounded compatibility seam is required
- corpus-specific overlay authoring beyond the lifecycle operations needed to
  manage them safely

## Owner Surfaces

- lifecycle draft and verification orchestration:
  `app/services/semantic_orchestration.py`,
  focused sibling lifecycle owners
- runtime payload adoption:
  `app/services/semantic_ontology.py`,
  `app/schemas/agent_task_semantics.py`
- ontology governance task context:
  `app/services/agent_task_context_semantic_governance_ontology.py`
- focused verification:
  ontology lifecycle unit tests,
  ontology governance task tests,
  semantic orchestration integration roundtrips
- durable docs:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`

## Placement Rules

- Keep `app/services/semantic_ontology.py` as the public lifecycle surface for
  initialize, snapshot, draft, verify, and apply flows; new lifecycle logic
  belongs in focused sibling owners instead of regrowing the facade.
- Lifecycle operations must be machine-readable structures with explicit source
  identifiers, replacement targets, and migration intent; do not hide lifecycle
  meaning inside prose-only rationale fields.
- Preserve current task types and stable payload fields additively unless a
  failing compatibility test proves the contract is wrong.
- Any touched owner must close at `<= 600` lines and `<= 6` private helpers.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Lifecycle support lands as ad hoc prose or operator folklore instead of explicit machine-readable operations. | lifecycle draft schemas, semantic orchestration, ontology task payloads | focused lifecycle unit tests plus semantic orchestration integration roundtrips | split, merge, deprecate, replace, or migrate cannot be represented as structured operations | add a prose-only lifecycle draft fixture and confirm validation fails | a future session stuffs destructive ontology intent into `rationale` because it is easier than extending the contract |
| Non-additive edits silently regress documents because verification only checks syntax or counts. | draft verification, preview surfaces, ontology governance tasks | focused verification tests plus DB-backed semantic orchestration roundtrips | a lifecycle draft publishes without explicit document-level regression preview evidence | create a merge or deprecate draft that drops supported concepts and confirm verification fails | a future session merges concepts directly because the ontology still loads locally |
| Lifecycle support regrows `semantic_ontology.py` or `semantic_orchestration.py` into another hotspot. | lifecycle service owners, hygiene policy, architecture gates | `uv run docling-system-hygiene-check`; `uv run docling-system-architecture-inspect` | touched owners exceed placement budgets or introduce a new cycle | implement all lifecycle logic in one existing facade and confirm the milestone rejects it | a future session keeps bolting lifecycle cases onto the current orchestration file |
| Compatibility breaks for existing ontology task consumers. | ontology task payloads, task-context builders, integration roundtrips | focused ontology action/context tests plus DB-backed semantic orchestration roundtrips | existing task types or required payload fields regress without explicit scoped approval | remove one legacy payload field in a fixture and confirm compatibility tests fail | a future session rewrites the ontology task payload shape because lifecycle fields need room |
| Lifecycle operations mutate the ontology without clear replacement lineage. | lifecycle payload schema, runtime snapshot metadata, docs | focused lifecycle lineage tests plus doc closeout review | a deprecate or replace operation lacks explicit predecessor/successor lineage | add a deprecate fixture without a replacement or migration note and confirm validation fails | a future session deprecates a concept by deleting it from a seed file and loses the audit trail |

## Milestone Sequence

### Milestone 0: Freshness And Baseline Lock

Outcome label: resolved

Implementation slice:

- baseline the current additive-only lifecycle behavior and write the first
  failing lifecycle-operation gate
- record the exact compatibility fields that current ontology tasks and
  contexts expose today

Closure signal:

- a repo-owned lifecycle gate fails against the current additive-only behavior
  and records the required compatibility baseline

### Milestone 1: Lifecycle Operation Contract

Outcome label: resolved

Implementation slice:

- add structured draft operations for split, merge, deprecate, replace, and
  migrate
- keep operation semantics machine-readable and versioned

Closure signal:

- lifecycle drafts can represent the required non-additive operations without
  hiding intent in prose

### Milestone 2: Verification And Apply Adoption

Outcome label: resolved

Implementation slice:

- extend verification previews and apply flows so lifecycle drafts prove
  document-level impact before publication
- preserve current ontology task identities and stable payload fields

Closure signal:

- lifecycle drafts cannot publish without explicit regression-preview evidence,
  and existing ontology task contracts remain compatible

### Milestone 3: Closeout, Docs, And Residual Routing

Outcome label: resolved

Implementation slice:

- refresh this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` with the final lifecycle surface
- route any still-missing corpus-specific overlay authoring work into a new
  bounded follow-on instead of broadening this packet

Closure signal:

- the ontology evolution lifecycle closes as its own bounded packet and any
  later overlay-specific work is explicit and discoverable

## Required Implementation Artifacts

- focused lifecycle owners under `app/services/`
- updated ontology runtime payloads and task-context fixtures where lifecycle
  data must surface
- focused lifecycle unit and integration tests

## Required Documentation And Handoff Updates

- this plan
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

## Required Verification Gates

- `git diff --check`
- `uv run pytest -q` over focused ontology lifecycle unit tests and ontology
  governance task-context coverage
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q` over focused
  semantic orchestration / ontology lifecycle roundtrips
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-architecture-inspect`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`

## Acceptance Criteria

- The ontology workflow can express split, merge, deprecate, replace, and
  migrate as structured draft operations.
- Lifecycle drafts cannot publish without document-level verification evidence.
- Existing ontology task identities and required payload fields remain
  compatible unless a failing test proves a contract bug.
- No touched owner exceeds the placement-rule budgets, no new cycle appears,
  and no new hygiene regression lands.
- Full DB-backed verification passes without relying on skipped integration
  coverage.

## Stop Conditions

- Stop and split a migration brief if lifecycle lineage cannot be represented
  in current payload JSON without DB schema changes.
- Stop if compatibility preservation would require a hidden second ontology or
  a dual source-of-truth workflow.
- Stop before closeout if lifecycle support can only go green by weakening the
  existing ontology or integration gates.

## Local Commit Closeout Policy

- Stage only the verified ontology evolution lifecycle slice.
- Leave unrelated worktree files alone.
- Commit implementation, tests, docs, and handoff updates in one atomic local
  milestone commit after the required verification passes.

## Residual Risks And Next Milestone Routing

- Corpus-specific overlay authoring may still require later bounded packets
  even after lifecycle support exists; route that work separately instead of
  broadening this plan.
