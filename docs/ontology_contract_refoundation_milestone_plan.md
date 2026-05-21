# Ontology Contract Refoundation Milestone Plan

Date: 2026-05-21 local / 2026-05-21 UTC
Status: in_progress
Owner context: standalone semantic contract follow-on after
`docs/semantic_registry_owner_rebaseline_milestone_plan.md` and
`docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md` closed. The
live routed hotspot queue is empty in the current checkout, so this packet is
selected from ontology-contract and agent-legibility evidence rather than from
an active hotspot trap queue.
Milestone 0, the opening Milestone 1 scaffold, the first Milestone 3 runtime
task-context slice, and the first Milestone 4 ontology-eval slice are now
landed locally through the canonical JSON contract, legacy-view parity
validation, the ontology contract report artifact, additive ontology-slice
metadata on active snapshot and ontology task payloads, enriched non-legacy
application or overlay or report-semantics layers, explicit ontology-eval
coverage in `docs/semantic_evaluation_corpus.yaml`, and the dedicated
`docs/ontology_evaluation_report.json` gate. The later alignment pass also
adds same-slice owner budgets for the new ontology contract owners in
`config/hygiene_policy.yaml` so the landed modules satisfy the packet placement
rules instead of relying only on green tests. The deeper readiness-gate
expansion and portable roundtrip enrichment remain open in later milestones.

## Purpose

Resolve the gap between the repo's strong semantic runtime and governance and
its still-thin ontology contract.

Today the system already supports ontology snapshots, draft, verify, and
apply task flows, semantic graph payloads, and semantic evaluation coverage,
but the
contract underneath those surfaces is still essentially a portable seed plus
additive registry patches. That is not yet enough for report-generation agents
that need explicit classes, relations, provenance semantics, validation
shapes, and stable cross-document meaning.

This milestone refounds the ontology contract without reopening the already
closed registry-owner and semantic-pass owner packets.

It also makes two currently under-specified requirements explicit:

- ontology slices must become first-class typed agent context rather than thin
  snapshot counters or prose-only summaries
- ontology-specific evals must become first-class closeout gates rather than
  remaining implied by the broader semantic evaluation lane

## Current Evidence

Live state from the current 2026-05-21 checkout after the landed ontology
runtime and eval slices:

```text
latest local ontology slice commit
  7a2c2012 Implement ontology contract runtime and eval slices

uv run docling-system-ontology-contract-validate --strict
  valid=true; layer_count=5; slice_count=5; competency_family_count=4

uv run docling-system-ontology-eval --output docs/ontology_evaluation_report.json
  overall_passed=true; global_entity_type_count=19; global_relation_count=20

wc -l app/services/ontology_contracts.py \
  app/services/ontology_contract_evaluations.py \
  app/services/ontology_contract_reporting.py \
  app/services/ontology_contract_runtime.py \
  app/services/semantic_ontology.py
     381 app/services/ontology_contracts.py
     425 app/services/ontology_contract_evaluations.py
     174 app/services/ontology_contract_reporting.py
     107 app/services/ontology_contract_runtime.py
     291 app/services/semantic_ontology.py
```

Current structural evidence:

- `config/upper_ontology.yaml` and `config/semantic_registry.yaml` remain
  duplicate legacy portable-seed compatibility views, but they are now
  compiled from the canonical JSON contract instead of being the only
  machine-readable ontology authority.
- `config/ontology/docling_ontology_contract.json` now carries five named
  layers, five named ontology slices, and four competency families. The
  non-legacy application, domain-overlay, report-semantics, and
  evaluation-coverage layers are active and contribute nineteen aggregate
  entity types and twenty aggregate relations to the compiled full-contract
  registry used by the ontology-eval gate.
- `app/services/ontology_contracts.py`,
  `app/services/ontology_contract_reporting.py`,
  `app/services/ontology_contract_runtime.py`, and
  `app/services/ontology_contract_evaluations.py` now form the focused
  ontology-contract owner family. The later alignment pass explicitly routes
  `ontology_contracts.py` and `ontology_contract_evaluations.py` in
  `config/hygiene_policy.yaml` because both new owners exceed the packet's
  stricter new-owner thresholds.
- `app/services/semantic_ontology.py` now exposes contract-prefixed runtime
  metadata plus first-class `ontology_slices` and `competency_families` on the
  active snapshot, ontology extension draft, and ontology apply payloads, so
  agent-context consumers can reuse slice-first ontology context instead of
  reconstructing it from counts or prose.
- `app/services/semantic_orchestration.py` currently supports only additive
  registry operations (`add_concept`, `add_alias`, `add_category_binding`).
  That is enough for vocabulary growth, but not enough to prove a refounded
  ontology contract on its own.
- `app/services/semantic_backfill.py` still reduces ontology readiness to
  concept presence and `document_mentions_concept`. Report-generation agents
  need broader class and relation guarantees than that.
- `app/services/semantic_graph_build.py` carries ontology version and hash
  into graph payloads, but not layer, export, or shape-contract metadata.
- `app/services/agent_task_context_semantic_analysis.py` and
  `app/services/agent_task_context_semantic_governance_ontology.py` now inherit
  first-class ontology slices and competency-family payloads through the
  enriched snapshot and ontology-governance schemas, but the repo still lacks a
  broader slice-aware readiness expansion across the rest of semantic runtime.
- `docs/semantic_evaluation_corpus.yaml` is no longer empty. It now carries
  five slice expectations, four competency-family expectations, and eight
  competency questions, and `docs/ontology_evaluation_report.json` records the
  resulting dedicated ontology gate as a repo-owned artifact.
- `tests/integration/test_portable_ontology_roundtrip.py` still proves the
  runtime can bootstrap a domain-agnostic ontology, but the fixture contract
  remains a minimal portable seed and does not yet exercise the richer
  report-semantics families now present in the canonical contract.

## Goal

Refound the ontology contract so that:

- the canonical machine-readable source of truth is a versioned checked-in
  JSON contract with explicit layer boundaries
- compatibility views for `config/upper_ontology.yaml` and
  `config/semantic_registry.yaml` are derived from that canonical contract
  instead of remaining coequal hand-edited authorities
- the contract compiler emits deterministic runtime payloads plus derived
  JSON-LD, OWL/Turtle, and SHACL artifacts using only repo-local contexts
  and vocab references
- runtime snapshots and graph payloads expose agent-legible contract metadata
  such as layer versions, export digests, and competency-question coverage
- runtime snapshot and task-context surfaces expose stable named ontology
  slices for core, application, domain-overlay, report-semantics, and
  evaluation-coverage concerns so agents can reuse those slices directly
  instead of re-deriving ontology meaning from counts or prose
- ontology readiness and semantic graph readiness require more than the single
  `document_mentions_concept` relation
- the semantic evaluation corpus contains explicit ontology competency
  questions relevant to report generation
- ontology-specific evals produce their own durable report artifact and
  verification gate so ontology coverage does not stay hidden inside broader
  semantic regressions
- existing public task types, route names, and stable payload fields remain
  compatible unless an exact failing test proves a contract bug

## Non-Goals

- No full domain-complete ontology authoring for every present or future
  corpus.
- No `app/db/models.py` or Alembic migration work unless Milestone 0 proves
  payload JSON cannot carry the required metadata without schema changes.
- No broad rewrite of semantic extraction, ranking, graph promotion, or report
  generation logic beyond the contract surfaces required to consume the
  refounded ontology.
- No replacement of JSON canonical artifacts with OWL or Turtle as the source
  of truth. OWL, SHACL, and JSON-LD are derived outputs in this packet.
- No hidden second ontology or parallel corpus-specific ontology introduced as
  a shortcut around the current runtime contract.
- No weakening of semantic unit, HTTP-boundary, or integration coverage to get
  a green result.

## Scope

In scope:

- `config/upper_ontology.yaml`
- `config/semantic_registry.yaml`
- new canonical ontology-contract artifacts under `config/ontology/`
- `app/services/semantic_registry_contracts.py`
- `app/services/semantic_ontology.py`
- `app/services/semantic_orchestration.py`
- `app/services/semantic_backfill.py`
- `app/services/semantic_graph_build.py`
- `app/services/semantic_registry_state.py` only where contract metadata must
  be persisted or surfaced through existing snapshot payloads
- `app/services/agent_task_context_semantic_analysis.py`
- `app/services/agent_task_context_semantic_governance.py`
- `app/services/agent_task_context_semantic_governance_ontology.py`
- direct semantic consumers only where compatibility seams must be updated:
  `app/services/semantic_registry_preview.py`,
  `app/services/semantic_graph.py`,
  `app/services/semantic_facts.py`,
  `app/services/agent_task_verifications.py`,
  `app/api/routers/semantics.py`,
  `app/services/capabilities/semantics.py`
- focused unit, integration, and HTTP-boundary tests for ontology contract,
  exports, task flows, semantic backfill, graph build, semantics routes, and
  first-class ontology context or ontology-eval gates
- `docs/semantic_evaluation_corpus.yaml`
- durable ontology-eval artifacts under `docs/`
- durable docs and routing surfaces:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`

Out of scope:

- reopening `app/services/semantic_registry.py` as a large-owner split packet;
  that owner is already closed
- reopening `app/services/semantics.py` as the central semantic owner
- new storage-backed artifact route families outside the current semantics
  surfaces
- broad residual work in `semantic_generation.py`, `semantic_graph_core.py`,
  or `semantic_graph_promotions.py` unless Milestone 0 proves the ontology
  contract cannot land without a narrowly bounded compatibility seam

## Owner Surfaces

- canonical ontology contract source:
  `config/ontology/*`
- compatibility views:
  `config/upper_ontology.yaml`,
  `config/semantic_registry.yaml`
- contract compile, export, or validation owners:
  `app/services/semantic_registry_contracts.py`,
  new focused sibling modules under `app/services/`
- runtime contract adoption:
  `app/services/semantic_ontology.py`,
  `app/services/semantic_orchestration.py`,
  `app/services/semantic_backfill.py`,
  `app/services/semantic_graph_build.py`,
  `app/services/semantic_registry_state.py`
- first-class agent context adoption:
  `app/services/agent_task_context_semantic_analysis.py`,
  `app/services/agent_task_context_semantic_governance.py`,
  `app/services/agent_task_context_semantic_governance_ontology.py`
- compatibility callers that must remain stable:
  `app/services/semantic_registry_preview.py`,
  `app/services/semantic_graph.py`,
  `app/services/semantic_facts.py`,
  `app/services/agent_task_verifications.py`,
  `app/services/capabilities/semantics.py`,
  `app/api/routers/semantics.py`
- focused verification:
  new ontology-contract unit tests,
  `tests/unit/test_semantic_orchestration.py`,
  `tests/unit/test_semantic_backfill_api.py`,
  `tests/unit/test_semantic_graph.py`,
  `tests/unit/test_documents_api_semantics.py`,
  `tests/unit/test_agent_task_actions_ontology.py`,
  `tests/unit/test_agent_task_context_semantic_analysis.py`,
  `tests/unit/test_agent_task_context_semantic.py`,
  `tests/unit/test_agent_task_context_semantic_governance.py`,
  `tests/unit/test_agent_task_context_semantic_governance_ontology.py`,
  `tests/integration/test_portable_ontology_roundtrip.py`,
  `tests/integration/test_semantic_bootstrap_roundtrip.py`,
  `tests/integration/test_semantic_backfill_roundtrip.py`,
  `tests/integration/test_semantic_graph_roundtrip.py`,
  `tests/integration/test_semantic_governance_ledger.py`,
  `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- routing and prevention:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`
- durable docs:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/semantic_evaluation_corpus.yaml`,
  generated ontology contract report artifacts

## Placement Rules

- The canonical machine-readable ontology source of truth must live under
  `config/ontology/` as checked-in JSON. Suggested entrypoint:
  `config/ontology/docling_ontology_contract.json`.
- `config/upper_ontology.yaml` and `config/semantic_registry.yaml` must stop
  being hand-edited authorities. Preserve current env-var and file-path
  compatibility by generating or compiling their legacy view from the
  canonical JSON contract.
- The canonical contract must define stable ontology slice families for core,
  application, domain overlays, report semantics, and evaluation coverage.
  Exact field names may vary, but each slice must be independently
  addressable, hashable, and reusable in runtime payloads, task context, and
  durable report artifacts.
- JSON-LD contexts must be local repo files. Do not rely on remote context
  resolution in tests, runtime, or closeout verification.
- Derived export artifacts such as JSON-LD, OWL/Turtle, and SHACL must live
  under an explicit docs-local or fixture-local path such as
  `docs/ontology_contract_exports/`, not as hidden runtime-only files.
- Keep `app/services/semantic_ontology.py` as the public orchestration surface
  for initialize, snapshot, draft, verify, and apply flows. New compile,
  export, or shape logic belongs in focused sibling owners instead of being
  added wholesale to `semantic_ontology.py` or `semantic_orchestration.py`.
- First-class ontology slices must appear as structured payload sections,
  context refs, or summary metrics, not only as prose text embedded in
  `TaskContextSummary.headline`, `decision`, or `next_action`.
- Ontology-specific eval outputs must be durable repo-owned artifacts with a
  stable path and machine-readable summary, not an ad hoc assertion folded
  into broader semantic-eval logs.
- Do not regrow `app/services/semantic_registry.py`,
  `app/services/semantics.py`,
  `app/services/semantic_registry_preview.py`,
  `app/services/semantic_graph.py`, or
  `app/services/semantic_generation.py` as sinks for contract debt.
- Any touched owner must close at `<= 600` lines and `<= 6` private helpers.
  Any new owner above `400` lines or `4` private helpers requires same-milestone
  hygiene routing and an explicit owner budget in `config/hygiene_policy.yaml`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The new canonical JSON contract lands, but future edits still change `config/upper_ontology.yaml` or `config/semantic_registry.yaml` directly and drift the contract. | `config/ontology/*`, compatibility exporters, legacy YAML views | `uv run docling-system-ontology-contract-validate --strict`; focused unit tests for compatibility export drift | Legacy YAML compatibility views differ from the compiled legacy projection of the canonical JSON contract | Manually edit one legacy YAML file only and confirm validation fails | A future session patches the old YAML because it is the easiest visible file and silently forks the ontology |
| The packet merely upgrades a glossary instead of introducing a real ontology contract. | canonical contract schema, report artifact, competency-question fixtures | `uv run docling-system-ontology-contract-report --output docs/ontology_contract_report.md`; focused contract tests | The compiled contract still exposes only generic `document`/`concept`/`literal` semantics with no explicit application layer or required report-semantics families | Compile the current minimal portable seed through the new validator and confirm the milestone gate rejects it | A future session adds more aliases or categories and claims ontology progress without richer class or relation semantics |
| Formal exports exist, but runtime validation still accepts invalid domain or range or overlay mappings. | SHACL exports, validator, graph build, backfill readiness | Focused ontology export tests plus semantic graph and backfill tests | Invalid relation domain or range, missing inverse mapping, or unmapped overlay class passes validation or graph build | Add a fixture relation with an invalid domain or an overlay reference to an unknown core type and confirm validation fails | A future session adds a relation key to the registry but forgets to add shapes or mapping rules |
| Runtime ontology context remains thin or opaque, so agents still only see counts and relation keys instead of reusable ontology slices. | `agent_task_context_semantic_analysis.py`, `agent_task_context_semantic_governance_ontology.py`, snapshot payload schemas, context fixtures | Focused agent-context tests plus the ontology contract report and ontology eval report | `get_active_ontology_snapshot`, `initialize_workspace_ontology`, or ontology governance contexts still lack independently addressable slice payloads for core, application, domain-overlay, report-semantics, or evaluation-coverage concerns | Keep the old minimal `active_ontology_snapshot_payload()` fixture and confirm the revised context gate fails until slice-first payload coverage is added | A future session adds more summary prose to ontology tasks and claims agent legibility without making the slices reusable by downstream tasks |
| Ontology-specific evals stay buried inside generic semantic-eval coverage and never become a first-class ontology gate. | `docs/semantic_evaluation_corpus.yaml`, ontology eval command or report, focused ontology-eval fixtures | `uv run docling-system-ontology-eval --output docs/ontology_evaluation_report.json`; focused ontology-eval tests | No dedicated ontology-eval artifact exists, or the artifact lacks explicit competency-family pass/fail results for ontology slices and report semantics | Remove one required competency family or its slice mapping from the ontology fixture and confirm the ontology-eval gate fails even if broader semantic tests stay green | A future session points at a general semantic pass or search replay and claims ontology readiness without proving the ontology contract itself is covered |
| Runtime adoption breaks existing ontology task flows or semantics route contracts. | `semantic_ontology.py`, `semantic_orchestration.py`, semantics routes, agent-task context builders | Focused unit, HTTP-boundary, and integration tests; full `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` gate | Existing task types, route names, or stable payload fields regress without explicit scoped approval | Temporarily remove a legacy snapshot field or rename a task-type dependency and confirm the gate fails | A future session rewires contract loading and breaks current agents that depend on the existing task or route shapes |
| Compile or export logic turns `semantic_ontology.py` or `semantic_orchestration.py` into the next monolith. | `semantic_ontology.py`, `semantic_orchestration.py`, new contract sibling modules, hygiene policy | `uv run docling-system-hygiene-check`; `uv run docling-system-architecture-inspect`; staged `wc -l` review | Any touched owner exceeds `600` lines or `6` private helpers, or a new owner exceeds `400` lines or `4` private helpers without same-milestone routing | Move export generation directly into `semantic_orchestration.py` and confirm hygiene or closeout review rejects it | A future session keeps bolting every ontology concern onto the existing orchestration file because it already imports the right helpers |
| A domain overlay becomes a second ontology rather than a mapped extension of the core contract. | canonical contract overlay section, overlay validators, competency fixtures | Focused overlay mapping tests plus ontology contract report | Overlay classes or relations bypass the core identifiers or map to unknown parents | Add a fixture overlay with an unmapped class or relation and confirm validation fails | A future session introduces a corpus-specific ontology file that no longer compiles through the shared core contract |

## Milestone Sequence

### Milestone 0: Freshness And Baseline Lock

Outcome label: resolved

Implementation slice:

- rerun the live baseline commands for current contract shape, current file
  budgets, and current routing state before code changes
- add the first failing or baseline ontology-contract validation or reporting
  gate before broad implementation starts
- baseline the current ontology-context surfaces explicitly:
  active snapshot payload fields,
  initialize or snapshot context outputs,
  ontology draft or verify or apply context refs,
  and the current absence of named ontology slices in those payloads
- baseline the current ontology-eval state explicitly:
  what `docs/semantic_evaluation_corpus.yaml` covers today,
  which competency families are missing,
  and whether any dedicated ontology-eval artifact exists
- record exact compatibility obligations for:
  current env-var file paths,
  current ontology task types,
  current snapshot payload fields,
  current semantics route payload fields,
  and current graph/backfill readiness signals

Closure signal:

- a repo-owned ontology-contract validation or report gate exists and fails or
  records baseline truth against the current minimal seed in a way that future
  milestones can tighten

### Milestone 1: Canonical Layered Contract And Compatibility Compiler

Outcome label: resolved

Implementation slice:

- introduce the canonical JSON contract under `config/ontology/`
- make the contract explicitly layered with:
  upper ontology,
  Docling application ontology,
  domain overlay mapping surfaces,
  report-semantic relation families,
  competency-question declarations,
  and explicit ontology slice boundaries that can be surfaced unchanged into
  agent context and evaluation artifacts
- convert the current portable seed into the new canonical contract while
  preserving the legacy compiled view consumed by the existing runtime
- generate compatibility views for
  `config/upper_ontology.yaml` and `config/semantic_registry.yaml`
  from the canonical contract
- define the stable slice contract that downstream agents can rely on for:
  core ontology meaning,
  Docling application semantics,
  domain-overlay mappings,
  report-semantics families,
  and ontology-evaluation coverage

Closure signal:

- the canonical JSON contract is the only authoritative machine-readable
  source, and the legacy YAML files are demonstrably compiled compatibility
  views rather than hand-maintained peers

### Milestone 2: Validation, Export, Shape, And Slice Boundary

Outcome label: resolved

Implementation slice:

- add deterministic export generation for JSON-LD, OWL/Turtle, and SHACL
- emit a durable ontology contract report artifact that summarizes:
  layer IDs and versions,
  named ontology slices and slice digests,
  required entity families,
  required relation families,
  competency-question coverage,
  export digests,
  and compatibility-view status
- add negative fixtures for:
  duplicate IDs,
  invalid domain or range,
  missing inverse relation symmetry,
  literal misuse,
  overlay mismatch,
  and direct legacy-YAML edits
- prove the compiler rejects or reports slice drift when a required ontology
  slice is missing, renamed incompatibly, or left without evaluation mapping

Closure signal:

- the validator rejects invalid ontology or overlay fixtures, and the export
  report is deterministic from the canonical contract with stable slice
  coverage recorded

### Milestone 3: Runtime Adoption Behind Stable Public Surfaces

Outcome label: resolved

Implementation slice:

- update runtime loaders and snapshot builders to consume the compiled
  canonical contract
- update the ontology-facing task-context builders so
  `initialize_workspace_ontology`,
  `get_active_ontology_snapshot`,
  `draft_ontology_extension`,
  `verify_draft_ontology_extension`,
  and `apply_ontology_extension`
  all expose first-class ontology context that downstream agents can reuse
- enrich ontology and graph payloads with agent-legible metadata such as:
  `contract_version`,
  `layer_versions`,
  `entity_type_count`,
  `relation_family_count`,
  `competency_question_count`,
  and export artifact digests
- expose stable ontology slices or slice refs for:
  core ontology,
  application ontology,
  domain overlays,
  report semantics,
  and evaluation coverage
- expand readiness logic so the ontology contract is not considered ready only
  because `document_mentions_concept` exists
- preserve stable task types and route names:
  `initialize_workspace_ontology`,
  `get_active_ontology_snapshot`,
  `draft_ontology_extension`,
  `verify_draft_ontology_extension`,
  `apply_ontology_extension`,
  and the current semantics route family

Closure signal:

- the runtime uses the refounded contract and exposes richer contract metadata
  plus first-class ontology slices without breaking the current public
  semantics surfaces

### Milestone 4: Ontology-Specific Eval And Report-Semantics Coverage

Outcome label: resolved

Implementation slice:

- extend `docs/semantic_evaluation_corpus.yaml` and focused fixtures so the
  ontology contract is exercised against report-generation semantics
- add a dedicated ontology-eval runner and durable ontology-eval artifact such
  as `docs/ontology_evaluation_report.json` that reports per-competency-family
  pass or fail results, slice coverage, and missing-mapping failures
- required minimum competency families:
  claim-support,
  measurement-or-unit,
  actor-or-obligation,
  document-or-source linkage
- required minimum ontology-slice coverage families:
  core terminology coverage,
  application-semantic coverage,
  domain-overlay mapping coverage,
  report-semantics relation coverage,
  and evaluation-coverage slice completeness
- expand the portable ontology integration lane so the roundtrip proves richer
  report semantics than the current two-relation seed
- require the active ontology context surfaces to expose enough slice detail
  that the ontology-eval artifact can name which slice or competency family
  failed without ad hoc manual interpretation
- add at least one HTTP-boundary regression for any enriched semantics route
  payload or handled ontology-validation error path

Closure signal:

- the ontology-eval artifact and focused tests prove the ontology contract
  supports non-trivial report semantics and first-class slice coverage rather
  than only generic concept mentions

### Milestone 5: Closeout, Docs, And Residual Routing

Outcome label: reduced

Implementation slice:

- refresh this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` with the implemented final state and
  verification commands
- commit generated ontology report or export artifacts that are part of the
  closeout contract
- record the final first-class ontology slice families and ontology-eval gate
  names in the durable docs so later sessions do not have to rediscover them
- if non-additive ontology evolution operations such as split, merge,
  deprecate, or migrate are still absent after refoundation, route that work
  into a fresh named follow-on instead of broadening this packet further

Closure signal:

- the contract refoundation closes as its own atomic milestone, and any
  remaining ontology evolution-lifecycle debt is explicit, bounded, and routed

## Required Implementation Artifacts

- canonical ontology contract JSON under `config/ontology/`
- compiled compatibility views for
  `config/upper_ontology.yaml` and `config/semantic_registry.yaml`
- deterministic export artifacts for JSON-LD, OWL/Turtle, and SHACL
- a durable ontology contract report artifact
- stable ontology slice payload sections or compiled slice artifacts that are
  reusable from runtime snapshots and agent task context
- a durable ontology-eval artifact with competency-family and slice-coverage
  results
- focused unit and integration fixtures for invalid contracts, overlay
  mismatches, and richer report-semantics competency questions
- updated context-support fixtures that prove ontology slices are first-class
  runtime and agent-context inputs rather than prose-only metadata
- touched runtime surfaces updated to expose richer contract metadata without
  changing stable public identities

## Required Documentation And Handoff Updates

- `docs/ontology_contract_refoundation_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/semantic_evaluation_corpus.yaml`
- `docs/ontology_contract_report.md`
- `docs/ontology_evaluation_report.json`
- any operator-facing README or runbook section that documents new ontology
  validation or report commands if those commands become required closeout
  gates

## Required Verification Gates

- `git diff --check`
- `uv run pytest -q tests/unit/test_semantic_registry_contracts.py tests/unit/test_semantic_ontology_contract_exports.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_semantic_graph.py tests/unit/test_documents_api_semantics.py tests/unit/test_agent_task_actions_ontology.py tests/unit/test_agent_task_context_semantic_analysis.py tests/unit/test_agent_task_context_semantic.py tests/unit/test_agent_task_context_semantic_governance.py tests/unit/test_agent_task_context_semantic_governance_ontology.py`
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_portable_ontology_roundtrip.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-ontology-contract-validate --strict`
- `uv run docling-system-ontology-contract-report --output docs/ontology_contract_report.md`
- `uv run docling-system-ontology-eval --output docs/ontology_evaluation_report.json`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`

## Acceptance Criteria

- A checked-in canonical JSON ontology contract exists under `config/ontology/`
  and is the only machine-readable source of truth for the ontology contract.
- `config/upper_ontology.yaml` and `config/semantic_registry.yaml` are proven
  compatibility views compiled from that canonical contract rather than
  independent authorities.
- The ontology-contract validator rejects the current minimal-seed shape when
  the required layered contract families are absent, and passes after the
  refoundation is implemented.
- Deterministic JSON-LD, OWL/Turtle, and SHACL exports are generated from
  the canonical contract and tracked by a durable report artifact.
- Runtime ontology snapshots and graph payloads expose richer contract metadata
  without breaking stable task types, route names, or required legacy payload
  fields.
- `initialize_workspace_ontology`, `get_active_ontology_snapshot`, and the
  ontology draft or verify or apply task contexts expose first-class ontology
  slices for core, application, domain-overlay, report-semantics, and
  evaluation-coverage concerns. Those slices are independently reusable by
  downstream agents and are not represented only as prose summaries.
- Ontology and semantic graph readiness requires more than
  `document_mentions_concept`; the gate must prove the required report-semantics
  relation family set is present.
- `docs/semantic_evaluation_corpus.yaml` and focused fixtures contain
  competency-question coverage for claim-support, measurement-or-unit,
  actor-or-obligation, and document-or-source linkage.
- A dedicated ontology-eval artifact exists, reports explicit pass or fail
  results for the required competency families and ontology slices, and fails
  when slice coverage or ontology-specific mappings regress even if broader
  semantic evals remain green.
- Any changed or new owner closes at or below the placement-rule budgets, no
  new Python cycles are introduced, and no new hygiene regressions appear.
- Full DB-backed verification passes with
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`; skipped integration
  coverage is not accepted for milestone closeout.

## Stop Conditions

- Stop and split a separate migration brief if Milestone 0 proves richer
  contract metadata cannot live in the existing snapshot payloads without DB
  schema changes.
- Stop if preserving current task or route compatibility would require a
  hidden second ontology or dual source-of-truth system.
- Stop if export generation depends on remote contexts, network fetches, or
  non-deterministic external tooling that cannot be made repo-local.
- Stop if a required runtime owner would exceed the placement-rule budgets and
  cannot be reduced within the same milestone.
- Stop before closeout if the ontology validator or the full integration gate
  cannot be made green without weakening tests or narrowing required behavior.

## Local Commit Closeout Policy

- Stage only the verified ontology-contract refoundation slice.
- Leave unrelated worktree files alone.
- Commit implementation, tests, generated ontology artifacts, docs, and
  handoff updates in the same atomic local milestone commit after all required
  verification passes.
- Record the commit hash and final verification commands in
  `docs/SESSION_HANDOFF.md`.
- Treat the milestone as ready-to-close, not complete, until that local commit
  exists.

## Residual Risks And Next Milestone Routing

- Non-additive ontology evolution operations such as split, merge, deprecate,
  and migrate may still remain after this contract refoundation. If so, route
  them into a fresh follow-on such as
  `docs/ontology_evolution_lifecycle_milestone_plan.md` instead of broadening
  this packet.
- Corpus-specific domain overlays may require later bounded follow-ons once the
  core contract exists; those overlays should extend the refounded contract,
  not replace it.
- If richer report-generation semantics reveal gaps in graph promotion or
  semantic generation beyond the contract boundary, route that work into a
  separate runtime packet after this milestone closes.
