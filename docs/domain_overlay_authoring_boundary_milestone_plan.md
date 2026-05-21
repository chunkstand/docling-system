# Domain Overlay Authoring Boundary Milestone Plan

Date: 2026-05-21 local / 2026-05-21 UTC
Status: queued locally after
`docs/ontology_evolution_lifecycle_milestone_plan.md` closeout. This packet
is the next bounded ontology follow-on in the current 2026-05-21 checkout. It
does not reopen generic lifecycle operations or ontology-contract
refoundation; it adds the still-missing corpus-scoped domain-overlay authoring
lane on top of those closed foundations.
Owner context: standalone successor after
`docs/ontology_evolution_lifecycle_milestone_plan.md` closes. The lifecycle
packet now proves non-additive split or merge or deprecate or replace or
migrate operations and blocks publication without document preview evidence,
but it intentionally stops short of a first-class authoring lane for
corpus-specific domain overlays.

## Purpose

Close the remaining ontology-governance gap after lifecycle closeout: the repo
now has a canonical layered ontology contract, first-class lifecycle
operations, and document-level lifecycle preview gates, but it still lacks a
bounded workflow for authoring corpus-specific domain overlays that map back to
the shared governed ontology.

Future report-generation and governance work will need explicit overlay
authoring so a corpus can introduce domain-local concepts without silently
forking the ontology or hiding the mapping back to the shared contract in
prose, filenames, or manual seed-file edits.

## Current Evidence

- `docs/ontology_contract_report.md` currently reports the
  `domain_overlay_baseline` layer at version
  `domain-overlay-baseline-v1` with one entity, two relations, and an active
  `domain_overlays` slice. The contract already reserves the layer, but it
  does not yet prove a first-class authoring workflow for later overlay
  additions.
- `config/ontology/docling_ontology_contract.json` explicitly describes the
  domain-overlay layer as a mapped extension of the shared contract rather than
  a second ontology, so later work must preserve that constraint instead of
  bypassing it.
- `docs/ontology_evolution_lifecycle_milestone_plan.md` is now closed by
  routing non-additive ontology mutation support into the existing draft or
  verify or apply task family and by blocking publication without preview
  evidence.
- Current lifecycle owner surfaces do not yet expose overlay-scoped authoring
  fields or routes. A live search across
  `app/services/semantic_ontology.py`,
  `app/services/semantic_registry_operation_contracts.py`,
  `app/services/semantic_registry_operation_mutations.py`,
  `app/services/agent_actions/semantic_governance_ontology_actions.py`,
  `app/services/agent_task_context_semantic_governance_ontology.py`, and
  `app/schemas/agent_task_semantics.py` returns no current `overlay`,
  `domain_overlay`, or `corpus-specific` authoring contract in those lifecycle
  owners.
- `tests/unit/test_ontology_evolution_lifecycle_baseline.py`,
  `tests/unit/test_agent_task_actions_ontology.py`,
  `tests/unit/test_agent_task_context_semantic_governance_ontology.py`, and
  the split portable ontology lifecycle family in
  `tests/integration/test_portable_ontology_roundtrip_lifecycle_draft.py` and
  `tests/integration/test_portable_ontology_roundtrip_lifecycle_apply.py` now
  prove generic lifecycle mutations and preview or apply adoption, but they do
  not yet prove overlay-scoped authoring, overlay lineage, or per-corpus
  mapping safety.

## Goal

Add a bounded domain-overlay authoring lifecycle that:

- lets operators draft, verify, and apply corpus-scoped overlay extensions
  without creating a parallel ontology
- records overlay scope, mapping targets, and successor lineage as
  machine-readable contract data rather than prose-only notes
- verifies overlay drafts against both document preview evidence and
  shared-contract mapping rules before publication
- surfaces applied overlay metadata through runtime snapshots, task payloads,
  and generated ontology report artifacts

## Non-Goals

- No corpus-by-corpus ontology curation campaign in this packet.
- No second ontology, corpus-local fork, or direct legacy-YAML editing path.
- No broad semantic extraction, search, or report-generation rewrite.
- No DB or Alembic change unless Milestone 0 proves current payload JSON
  cannot carry overlay scope or lineage safely.
- No weakening of ontology, semantic, or integration gates to get green.

## Scope

In scope:

- `config/ontology/docling_ontology_contract.json`
- `app/services/ontology_contracts.py`
- `app/services/ontology_contract_runtime.py`
- `app/services/semantic_ontology.py`
- focused overlay sibling owners under `app/services/`
- ontology task payload and context owners only where overlay authoring must be
  surfaced:
  `app/schemas/agent_task_semantics.py`,
  `app/services/agent_actions/semantic_governance_ontology_actions.py`,
  `app/services/agent_task_context_semantic_governance_ontology.py`
- focused ontology contract, lifecycle, and portable roundtrip tests
- generated ontology artifacts under `docs/` when overlay metadata changes
- durable routing docs:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`

Out of scope:

- reopening generic lifecycle mutation support already closed in the predecessor
  packet
- direct corpus ingest, search-ranking, or report-generation work beyond the
  overlay authoring contract needed to govern them safely
- authoring actual production overlays for a real corpus before the authoring
  lane itself is closed and verified

## Owner Surfaces

- overlay contract and validation:
  `config/ontology/docling_ontology_contract.json`,
  `app/services/ontology_contracts.py`
- overlay draft or verify or apply adoption:
  `app/services/semantic_ontology.py`,
  focused sibling overlay owners
- ontology task payloads and context:
  `app/schemas/agent_task_semantics.py`,
  `app/services/agent_actions/semantic_governance_ontology_actions.py`,
  `app/services/agent_task_context_semantic_governance_ontology.py`
- generated ontology closeout artifacts:
  `docs/ontology_contract_report.md`,
  `docs/ontology_evaluation_report.json`
- durable docs:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`

## Placement Rules

- Keep `app/services/semantic_ontology.py` as the public lifecycle surface for
  ontology draft or verify or apply flows. New overlay logic belongs in focused
  sibling owners instead of regrowing the facade.
- Overlay scope, mapping targets, and lineage must live in machine-readable
  fields. Do not encode them only in rationale prose, filenames, or document
  titles.
- Overlay authoring must extend the shared contract. Any overlay concept or
  relation must map back to known governed identifiers or the milestone fails.
- Preserve current task types and stable payload fields additively unless a
  failing compatibility test proves the contract is wrong.
- Any touched owner must close at `<= 600` lines and `<= 6` private helpers.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Overlay authoring becomes a hidden second ontology instead of a mapped extension of the shared contract. | ontology contract overlay section, overlay validators, generated ontology report | `uv run docling-system-ontology-contract-validate --strict`; focused ontology contract tests | an overlay concept or relation can publish without a valid mapping back to governed identifiers | add an overlay fixture with an unknown parent mapping and confirm validation fails | a future session adds a corpus-local ontology file because editing the shared contract feels risky |
| Overlay intent stays prose-only, so operators cannot tell which corpus or slice a change belongs to. | overlay draft schemas, runtime payloads, task-context builders | focused lifecycle and context tests plus portable roundtrips | a draft can publish overlay additions without explicit corpus or overlay scope fields | create a draft that only explains overlay scope in `rationale` and confirm validation fails | a future session stuffs overlay details into a free-text note because the payload is already crowded |
| Overlay publication reuses generic lifecycle previews but never proves the shared mapping is valid on real documents. | overlay verify or apply owners, preview payloads, ontology governance tasks | focused verify or apply tests plus DB-backed roundtrips | an overlay draft publishes without preview evidence or without contract-mapping proof | add a draft with preview evidence but no valid mapping record and confirm verification fails | a future session treats document preview as sufficient proof even when the overlay does not map to the shared contract |
| Overlay support regrows `semantic_ontology.py` or the ontology action or context owners into new hotspots. | lifecycle facade, overlay owners, hygiene or architecture gates | `uv run docling-system-hygiene-check`; `uv run docling-system-hotspot-prevention-check --strict`; `uv run docling-system-architecture-inspect` | any touched owner breaks placement budgets or introduces a new cycle | place overlay parsing and preview logic directly in `semantic_ontology.py` and confirm the milestone rejects it | a future session keeps appending special overlay cases to the public facade because callers already import it |
| Overlay closeout looks green without durable artifact updates, so later sessions cannot see what overlay state is active. | ontology contract report, ontology eval artifact, handoff or index docs | regenerated ontology report and eval artifacts plus doc closeout review | overlay metadata changes but `docs/ontology_contract_report.md`, `docs/ontology_evaluation_report.json`, or routing docs stay stale | change overlay metadata without regenerating the report and confirm artifact or review drift fails the milestone | a future session updates only code and tests, leaving the visible ontology state stale in docs |

## Milestone Sequence

### Milestone 0: Freshness And Baseline Lock

Outcome label: resolved

Implementation slice:

- refresh the current ontology contract report and lifecycle evidence so this
  packet starts from the live contract state rather than a stale assumption
- write the first failing or baseline gate that proves overlay authoring is
  not already first-class in the current checkout

Closure signal:

- the repo records the live overlay baseline and has a repo-owned failing or
  baseline gate for the missing authoring lane

### Milestone 1: Overlay Intent Contract

Outcome label: resolved

Implementation slice:

- add explicit overlay scope and mapping contract fields to the ontology draft
  payloads
- require overlay concepts and relations to declare their governed mapping
  targets and lineage explicitly

Closure signal:

- overlay authoring intent is machine-readable and unmapped overlay drafts fail

### Milestone 2: Verification And Preview Adoption

Outcome label: resolved

Implementation slice:

- extend ontology verify flows so overlay drafts require both document preview
  evidence and shared-contract mapping proof before publication
- keep the existing ontology task family and compatibility fields intact

Closure signal:

- overlay drafts cannot publish without explicit preview evidence and contract
  mapping evidence

### Milestone 3: Apply, Report, And Eval Adoption

Outcome label: resolved

Implementation slice:

- surface applied overlay metadata in active snapshot or apply payloads and the
  ontology contract report or eval artifact
- prove the portable roundtrip and contract artifacts stay honest when overlay
  metadata changes

Closure signal:

- runtime and generated artifacts expose overlay authoring state and the
  contract or eval gates pass

### Milestone 4: Closeout, Docs, And Residual Routing

Outcome label: resolved

Implementation slice:

- refresh this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md`
- route any later corpus-by-corpus content curation into a new packet instead
  of broadening this authoring-infrastructure lane

Closure signal:

- the overlay authoring packet closes as its own bounded owner and any later
  corpus-specific curation work is explicit and discoverable

## Required Implementation Artifacts

- focused overlay contract or validation or preview owners under `app/services/`
- updated ontology draft or verify or apply payload surfaces where overlay data
  must appear
- regenerated `docs/ontology_contract_report.md` and
  `docs/ontology_evaluation_report.json` when the contract surface changes
- focused unit and integration coverage for overlay authoring and mapping rules

## Required Documentation And Handoff Updates

- this plan
- `docs/ontology_contract_report.md`
- `docs/ontology_evaluation_report.json`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check` over touched ontology contract or lifecycle or task files
- `uv run pytest -q` over focused ontology contract, lifecycle, action, and
  context tests
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q` over focused portable
  ontology and semantic orchestration roundtrips
- `uv run docling-system-ontology-contract-validate --strict`
- `uv run docling-system-ontology-contract-report --strict --output docs/ontology_contract_report.md`
- `uv run docling-system-ontology-eval --output docs/ontology_evaluation_report.json`
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-architecture-inspect`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`

## Acceptance Criteria

- The ontology workflow can express corpus-scoped overlay authoring intent as
  structured payload data with explicit mapping targets.
- Overlay drafts cannot publish without both preview evidence and contract
  mapping evidence.
- Generated ontology report or eval artifacts expose the active overlay
  authoring state honestly.
- Existing ontology task identities and required payload fields remain
  compatible unless a failing test proves a contract bug.
- No touched owner exceeds the placement budgets, no new cycle appears, and no
  new hygiene regression lands.
- Full DB-backed verification passes without relying on skipped integration
  coverage.

## Stop Conditions

- Stop and split a migration brief if overlay scope or lineage cannot be
  represented in current payload JSON without DB schema changes.
- Stop if the only workable design is a hidden second ontology or a corpus-only
  direct-edit path.
- Stop before closeout if overlay support can only go green by weakening the
  ontology contract, lifecycle, or integration gates.

## Local Commit Closeout Policy

- Stage only the verified overlay authoring slice.
- Leave unrelated worktree files alone.
- Commit implementation, tests, regenerated artifacts, docs, and handoff
  updates in one atomic local milestone commit after the required verification
  passes.

## Residual Risks And Next Milestone Routing

- Actual overlay content authoring for a specific corpus remains a separate
  later packet after this infrastructure lane closes.
