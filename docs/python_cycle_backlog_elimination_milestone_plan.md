# Python Cycle Backlog Elimination Milestone Plan

Date: 2026-05-17 local / 2026-05-17 UTC
Status: resolved through the 2026-05-18 durable closeout. Milestones 0 through
4 are complete for the zero-cycle lane; the separate `27`-file `>800` backlog
remains owned by
`docs/boring_change_architecture_milestone_plan.md`.
Owner context: selected bounded follow-on for the three remaining Python import
cycle components reported by the live architecture probe. This packet
operationalizes the cycle-elimination lane named by
`docs/boring_change_architecture_milestone_plan.md` Milestone 3 without
reopening the earlier closed architecture-governance cycle packet.

## 2026-05-18 Closeout Update

Milestone 0 rebaseline showed that the drafted 2026-05-17 cycle map was stale.
The live implementation work started from three real remaining cycle families:

- the search-family cycle caused by ambiguous `from app.services import ...`
  package imports across `search.py` and its extracted owner modules
- the explicit evidence provenance graph cycle between
  `evidence_provenance_export_graph_core.py` and
  `evidence_provenance_export_graph_report.py`
- the explicit evidence search package cycle between
  `evidence_search_packages.py` and `evidence_search_trace_store.py`

As the cycle count dropped, repeated live probe runs also exposed the same
package-import ambiguity in adjacent parser, evaluation, run, and
semantic-governance owner families. The final closeout therefore resolved the
entire live zero-cycle lane by:

- converting the remaining `from app.services import ...` and
  `from app.core import ...` package imports in the cycle-owning families to
  explicit submodule imports so the static graph is stable and deterministic
- extracting shared provenance graph contracts into
  `app/services/evidence_provenance_export_graph_contracts.py`
- extracting search evidence package assembly into
  `app/services/evidence_search_package_build.py`
- removing the duplicate supplement helper from
  `app/services/docling_parser_tables.py` so the parser family is strictly
  one-way again
- adding `tests/unit/test_python_cycle_imports.py` and wiring the checked-in
  import-boundary regression command
  `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`
  into `.github/workflows/architecture-governance.yml`

Milestone status:

- Milestone 0: resolved. The packet was rebaselined to the live search,
  evidence, parser, evaluation, run, and semantic-governance import surfaces.
- Milestone 1: resolved. The live service-family SCCs introduced by ambiguous
  package imports were removed through explicit submodule ownership.
- Milestone 2: resolved. The provenance graph cycle is gone after moving shared
  graph contracts into a narrow owner.
- Milestone 3: resolved. The evidence package or trace-store cycle is gone
  after moving package assembly into a dedicated build owner.
- Milestone 4: resolved for the zero-cycle lane. The repo-owned workflow now
  runs `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`,
  and the live probe reaches zero cycles without local-import masking.

Closeout verification:

- `git diff --check`: pass
- `uv run ruff check ...`: pass
- `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`: `6 passed`
- `uv run pytest -q tests/unit/test_evidence_provenance.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_evidence_provenance_export_graph_report.py tests/unit/test_evidence_provenance_export_lifecycle.py`: `18 passed`
- focused cycle and owner suites: `111 passed`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`: pass, `0` cycle components
- `uv run docling-system-architecture-inspect`: `valid=true`
- `uv run docling-system-architecture-decisions`: `valid=true`
- `uv run docling-system-capability-contracts`: `valid=true`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`
- `uv run docling-system-improvement-case-validate`: `valid=true`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `2042 passed`

Important residual:

- `python .../architecture_probe.py --max-file-lines 800` still reports `27`
  code files above the threshold. This packet resolves the cycle backlog only;
  the large-file gate remains routed through the broader boring-change brief and
  the queued `docs/agent_task_residual_owner_family_milestone_plan.md` follow-on.

## Purpose

Resolve the remaining live Python import-cycle debt with one standalone packet
that another session can execute without widening back into the umbrella
architecture brief.

The scoped weakness is not just "the probe still shows red." The current repo
still contains:

- one large service-level cycle that ties together `chat`, `documents`,
  `evaluations`, `runs`, `search`, and semantic-pass owners
- one evidence provenance graph cycle between
  `evidence_provenance_export_graph_core` and
  `evidence_provenance_export_graph_report`
- one evidence search package cycle between `evidence_search_packages` and
  `evidence_search_trace_store`

Those cycles keep change expensive in exactly the files the broader architecture
program has already been trying to make boring to change. The plan therefore
must remove the cycles by explicit seam ownership, not by local-import masking,
while preserving the facade reductions and public contracts that earlier
packets already closed.

## Current Evidence

Live repo evidence refreshed from the clean `main` checkout on 2026-05-17
local / 2026-05-17 UTC:

```text
git status -sb
  ## main...origin/main

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=496.06

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt still includes:
    app/services/agent_actions/search_harness.py = 1078
    app/services/agent_task_context_semantic_governance.py = 1126
    app/services/semantic_generation_brief.py = 644
    app/services/semantic_graph_core.py = 697
    app/services/semantic_graph_promotions.py = 718

uv run docling-system-improvement-case-summary
  case_count=49
  status_counts.open=33
  status_counts.deployed=15
  status_counts.measured=1

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown
  27 code files exceed 800 lines
  Python cycles:
    app.services.chat, app.services.docling_parser, app.services.documents,
    app.services.evaluations, app.services.run_failure_artifacts,
    app.services.run_leases, app.services.run_post_promotion,
    app.services.runs, app.services.search,
    app.services.search_execution_persistence,
    app.services.search_harnesses, app.services.search_hydration,
    app.services.search_metadata_supplement,
    app.services.search_retrieval_primitives,
    app.services.semantic_governance, app.services.semantic_pass_artifacts,
    app.services.semantic_pass_lifecycle, app.services.semantic_pass_reads,
    app.services.semantic_pass_reviews,
    app.services.semantic_pass_source_records,
    app.services.semantic_registry,
    app.services.semantic_registry_preview,
    app.services.semantics, app.services.validation
    app.services.evidence_provenance_export_graph_core,
    app.services.evidence_provenance_export_graph_report
    app.services.evidence_search_packages,
    app.services.evidence_search_trace_store
```

AST import-subgraph readback for the three live components:

```text
large service cycle
  chat -> search
  evaluations -> chat, search
  documents -> evaluations
  semantic_pass_reads -> documents
  semantic_registry_preview -> documents, semantic_pass_reads, semantic_registry
  semantic_pass_lifecycle -> semantic_pass_reads, semantic_pass_reviews,
    semantic_pass_artifacts, semantic_registry, semantic_registry_preview
  semantics -> semantic_pass_lifecycle, semantic_pass_reads,
    semantic_registry_preview
  runs -> evaluations, semantics, validation, run_leases,
    run_post_promotion, docling_parser
  validation -> docling_parser
  run_failure_artifacts -> validation
  run_leases -> run_failure_artifacts
  run_post_promotion -> run_leases, run_failure_artifacts, validation
  search -> search_execution_persistence, search_harnesses,
    search_hydration, search_metadata_supplement,
    search_retrieval_primitives

evidence provenance cycle
  evidence_provenance_export_graph_core
    -> evidence_provenance_export_graph_report
  evidence_provenance_export_graph_report
    -> evidence_provenance_export_graph_core

evidence search cycle
  evidence_search_packages -> evidence_search_trace_store
  evidence_search_trace_store -> evidence_search_packages
```

Repo-current structural evidence:

- `docs/architecture_governance_cycle_boundary_milestone_plan.md` is already
  closed and removed the earlier governance-only cycle. This packet must not
  reclaim that closed scope.
- `docs/boring_change_architecture_milestone_plan.md` already names cycle
  elimination as Milestone 3 and explicitly allows a standalone cycle-specific
  follow-on packet.
- `docs/search_compatibility_facade_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/semantics_service_boundary_milestone_plan.md`,
  `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`, and
  `docs/app_large_owner_modules_resolution_milestone_plan.md` already reduced
  the main service facades. Cycle work must preserve those reductions rather
  than treat them as unfinished hotspots.
- `app/services/capabilities/retrieval.py`,
  `app/services/capabilities/evaluation.py`,
  `app/services/capabilities/semantics.py`, and
  `app/services/capabilities/run_lifecycle.py` already provide repo-native seam
  patterns. Prefer those or similarly narrow contract-only seams before adding
  a new abstraction family.

## Goal

Resolve the three remaining Python cycle components so that:

- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
  reports `0` cycle components
- the large service cycle spanning search, chat, evaluations, documents, runs,
  and semantic-pass owners is gone without regrowing the compact compatibility
  facades
- the two evidence two-file cycles are gone through explicit shared contracts
  or helper ownership, not by hiding imports in function bodies
- `.github/workflows/architecture-governance.yml` or an equivalent repo-owned
  gate runs the same strict cycle check used for closeout
- no new file above the `800`-line architecture-probe threshold is created
- no test, fixture, or contract coverage is weakened just to make the probe
  green

## Non-Goals

- No microservice extraction, package split, or platform rewrite.
- No reopening of the closed architecture-governance cycle packet.
- No broad large-file cleanup beyond what is strictly required to break the
  three live cycle components.
- No threshold increase above the current `800`-line architecture-probe gate.
- No local-import masking, import-time side effects, dynamic-import workarounds,
  or similar tricks that only hide the same dependency loop from the static
  graph.
- No public API, CLI, DB, or persisted artifact contract redesign unless
  Milestone 0 proves a narrower compatibility-preserving seam cannot work.
- No test weakening, fixture deletion, assertion loosening, or skip broadening
  to offset refactor risk. Replacement coverage must provide equivalent or
  broader contract coverage.

## Scope

In scope:

- Milestone 0 live-state cycle refresh and routed owner confirmation
- the large service cycle centered on `chat`, `search`, `evaluations`,
  `documents`, `runs`, and the semantic-pass owner family
- the `evidence_provenance_export_graph_core` /
  `evidence_provenance_export_graph_report` cycle
- the `evidence_search_packages` / `evidence_search_trace_store` cycle
- focused AST import-boundary tests or equivalent cycle-specific contract tests
- final strict cycle gating in the repo-owned architecture workflow
- docs, handoff, routing, and owner-register updates required to prove closure

Out of scope:

- the residual `>800`-line test backlog unless a touched test must be split to
  preserve equivalent or broader contract coverage
- unrelated UI or app hotspot cleanup
- changing the current hotspot-prevention thresholds
- claim-support, runtime-health, CI parity, or data-model work not directly
  required to remove one of the three live cycle components

## Owner Surfaces

- `docs/python_cycle_backlog_elimination_milestone_plan.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `.github/workflows/architecture-governance.yml`
- search/service cycle owners:
  `app/services/chat.py`,
  `app/services/search.py`,
  `app/services/search_execution_persistence.py`,
  `app/services/search_harnesses.py`,
  `app/services/search_hydration.py`,
  `app/services/search_metadata_supplement.py`,
  `app/services/search_retrieval_primitives.py`,
  `app/services/documents.py`,
  `app/services/evaluations.py`,
  `app/services/runs.py`,
  `app/services/validation.py`,
  `app/services/semantics.py`,
  `app/services/semantic_pass_lifecycle.py`,
  `app/services/semantic_pass_reads.py`,
  `app/services/semantic_pass_reviews.py`,
  `app/services/semantic_pass_artifacts.py`,
  `app/services/semantic_pass_source_records.py`,
  `app/services/semantic_registry.py`,
  `app/services/semantic_registry_preview.py`
- evidence cycle owners:
  `app/services/evidence_provenance_export_graph_core.py`,
  `app/services/evidence_provenance_export_graph_report.py`,
  `app/services/evidence_search_packages.py`,
  `app/services/evidence_search_trace_store.py`
- cycle and contract tests:
  `tests/unit/test_architecture_governance_imports.py`,
  new focused cycle test files under `tests/unit/`,
  existing focused search/semantic/run/evidence suites
- owner routing and hygiene registers when lifecycle state changes:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`

## Placement Rules

- Prefer contract-only or capability-owned seams over new broad utility modules.
- Reuse existing capability families first:
  `app/services/capabilities/retrieval*.py`,
  `app/services/capabilities/evaluation.py`,
  `app/services/capabilities/semantics.py`,
  and `app/services/capabilities/run_lifecycle.py`.
- If a new shared seam is unavoidable, place it beside the owner family it
  serves and keep it contract-only. Do not create a new catch-all
  `app/services/common_cycle_utils.py`.
- Keep `app/services/search.py`, `app/services/evaluations.py`,
  `app/services/semantics.py`, `app/services/runs.py`, and
  `app/services/evidence_provenance_exports.py` as compatibility or orchestration
  entrypoints rather than moving bulk implementation back into them.
- Place new import-boundary tests in focused files such as
  `tests/unit/test_service_cycle_imports.py` and
  `tests/unit/test_evidence_cycle_imports.py` instead of expanding
  `tests/unit/test_architecture_governance_imports.py` into another mixed test
  hotspot.
- If a cycle member is still governed by an open improvement case, update that
  case rather than creating a duplicate owner family unless Milestone 0 proves
  the existing case cannot honestly own the remaining cycle work.

## Weak-Point Prevention Contract

Weak point forecast: the most likely failure modes are stale routing, fake
cycle removal through local imports, regrowth of already-shrunk facades,
replacement of one cycle with another broad bridge module, silent breakage in
evidence integrity while import tests still pass, and a closeout that never
reaches the repo-owned workflow.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet starts from stale cycle membership or stale routing and edits the wrong files. | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `docs/boring_change_architecture_milestone_plan.md` | Milestone 0 freshness check plus architecture-probe readback | The live cycle set or selected packet differs from the plan and the docs are not updated first. | Re-run the probe after adding a temporary import and confirm Milestone 0 forces a doc refresh before code edits continue. | A future session implements against an old umbrella paragraph and reopens already-closed search or evidence packets. |
| The probe goes green only because imports moved inside functions or runtime side effects. | cycle-owning service files plus focused cycle-import tests | `python .../architecture_probe.py --fail-on-cycles`, focused AST import-boundary tests, code review against new local imports | Any cycle disappears without an explicit seam, or a new function-local import is introduced inside the affected owners. | Add a temporary function-local back import in a fixture or temporary diff and confirm the focused cycle test rejects it. | A future session hides `search` or evidence imports inside a helper and calls the cycle resolved. |
| Cycle work regrows already-shrunk facades or pushes debt into another large owner. | `app/services/search.py`, `app/services/evaluations.py`, `app/services/semantics.py`, `app/services/runs.py`, evidence facades, hygiene policy | `uv run docling-system-hygiene-check`, `uv run docling-system-hotspot-prevention-check --strict`, `wc -l` readback in closeout review | A touched compact facade regains implementation bodies or any new file crosses the current `800`-line threshold. | Add a temporary helper back into `app/services/search.py` or `app/services/evidence_provenance_exports.py` and confirm hotspot prevention or review blocks it. | A future session keeps the cycle out of the graph by dumping the logic back into a compatibility file. |
| The large service cycle is broken by inventing another broad cross-domain owner instead of a narrow seam. | capability modules, any new contract-only owner, search/run/semantic/documents/evaluations families | focused unit suites plus architecture-quality summary and file-shape review | A new seam imports multiple runtime-heavy service owners and becomes another mixed hub. | Leave a temporary `app/services/search_semantic_bridge.py` importing search, documents, evaluations, and runs together and confirm review rejects it. | A future session introduces a single “bridge” module that only relocates the cycle. |
| The evidence subcycle fixes break trace integrity or provenance/report behavior while only import tests pass. | evidence graph/store owners, technical-report and search evidence tests | focused evidence unit suites plus DB-backed integration slices | The cycle is gone but graph assembly, recomputation, or trace integrity contracts change without equivalent or broader contract coverage. | Preserve or replace graph, integrity, and recomputation assertions with explicit owner tests and confirm a temporary wrong hash or missing node fails. | A future session removes the mutual import but also weakens the provenance or search-trace contract. |
| The final gate stays local-only and the cycle backlog can regress on the next PR. | `.github/workflows/architecture-governance.yml`, architecture-governance CLI path, docs | workflow update plus local replay of the same command | Closeout passes locally, but the repo-owned workflow still never runs `--fail-on-cycles`. | Remove the workflow step in a temporary diff and confirm the closeout checklist blocks the milestone. | A future session fixes cycles once, but the next PR can reintroduce them without CI feedback. |

## Milestone Sequence

### Milestone 0 - Live Cycle Refresh And Gate-First Routing

Outcome label: reduced

Purpose: freeze the exact live cycle backlog and set the guardrails before code
motion begins.

Required work:

- Re-run the architecture probe, quality summary, hygiene check, and
  improvement-case summary from the current checkout.
- Record the exact cycle memberships and the current AST edge readback in this
  plan.
- Confirm the currently relevant routed owners:
  the closed search-owner packet under `IC-1D03DBFE8492`,
  the evidence owner-family under `IC-65AF4A6D8B1E`,
  the semantics owner family under `IC-9E6B8F5D62A1`,
  and any still-relevant `runs` or `documents` owner routing from the app-large
  packet. If the live registry no longer matches those surfaces, update routing
  first.
- Add or update focused AST import-boundary tests for the cycle packet in new
  cycle-specific test files under `tests/unit/`.
- Add negative-path fixtures or equivalent checks that prove local-import
  masking and mutual back-imports are rejected.

Acceptance criteria:

- This plan captures the live cycle set from the current probe output.
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` all point at this packet
  as the selected cycle lane rather than a vague umbrella milestone.
- The cycle-import test helpers exist before broad implementation starts and
  include at least one controlled-violation case.

### Milestone 1 - Large Service Cycle Elimination

Outcome label: resolved

Purpose: remove the large service cycle spanning search, chat, evaluations,
documents, runs, and semantic-pass owners.

Required work:

- Remove the `documents -> evaluations -> chat -> search` closure by routing
  evaluation-time search and chat behavior through a narrower capability or
  contract seam instead of direct service back-imports.
- Remove the `semantic_pass_reads -> documents` and
  `semantic_registry_preview -> documents` back edges by routing active-document
  access through a narrow read contract or existing lifecycle capability rather
  than the runtime-heavy `documents` owner.
- Remove the `runs -> evaluations / semantics / validation -> docling_parser`
  closure through the smallest compatibility-preserving seam that keeps run
  orchestration stable.
- Preserve the narrowed public facades in `search.py`, `evaluations.py`,
  `semantics.py`, and `runs.py`; do not move implementation back into those
  files just to change import direction.

Acceptance criteria:

- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown`
  no longer lists the large 24-module service cycle component.
- The total Python cycle count drops from `3` to `2`.
- No touched facade regrows beyond its current verified ceiling.
- Focused search, chat, document, run, and semantic tests pass, and the full
  DB-backed suite still passes.

### Milestone 2 - Evidence Provenance Graph Cycle Elimination

Outcome label: resolved

Purpose: break the two-file provenance export graph cycle without weakening
technical-report provenance behavior.

Required work:

- Remove the mutual dependency between
  `evidence_provenance_export_graph_core.py` and
  `evidence_provenance_export_graph_report.py`.
- If shared types such as `ProvenanceGraphContext` or `ProvenanceGraphState`
  must be consumed by both files, move them into a narrow contract-only owner
  rather than leaving one file to import the other for types or callbacks.
- Keep `build_agent_task_provenance_export(...)` stable as the public assembly
  entrypoint.

Acceptance criteria:

- The architecture probe no longer lists the provenance graph cycle.
- The total Python cycle count drops from `2` to `1`.
- Focused provenance graph, lifecycle, and integrity tests retain equivalent or
  broader contract coverage than the pre-split suite.

### Milestone 3 - Evidence Search Package Cycle Elimination

Outcome label: resolved

Purpose: break the `evidence_search_packages` /
`evidence_search_trace_store` mutual import while keeping search evidence trace
recomputation and persistence stable.

Required work:

- Remove the `trace_store -> get_search_evidence_package(...)` back import by
  routing recomputation through a narrower rebuild helper, callback-owned seam,
  or contract-only module that does not also own persistence.
- Keep package assembly in `evidence_search_packages.py` and trace persistence
  or integrity in `evidence_search_trace_store.py`.
- Preserve the public search evidence package and trace response contracts.

Acceptance criteria:

- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
  reports `0` Python cycle components.
- Focused evidence-search and search-persistence tests pass.
- No new search or evidence hotspot-prevention regression is introduced while
  cutting the last cycle.

### Milestone 4 - Strict Repo Gate And Durable Closeout

Outcome label: resolved

Purpose: make the zero-cycle state mechanically enforced and durably routed.

Required work:

- Update `.github/workflows/architecture-governance.yml` so the checked-in
  repo-owned import-boundary regression command used locally,
  `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`,
  also runs in the repo workflow.
- Keep the external architecture probe command
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
  as the separate local zero-cycle proof gate for milestone closeout unless a
  repo-owned equivalent is intentionally versioned later.
- Refresh routing docs and any affected owner-case or hygiene records.
- Record the zero-cycle state, verification commands, and closeout commit in
  the handoff and architecture index.

Acceptance criteria:

- `.github/workflows/architecture-governance.yml` runs
  `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`
  as the checked-in import-boundary regression gate.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
  passes with `0` Python cycle components.
- `uv run docling-system-architecture-inspect`,
  `uv run docling-system-architecture-decisions`,
  `uv run docling-system-capability-contracts`,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-hotspot-prevention-check --strict`, and
  `uv run docling-system-improvement-case-validate` all pass.
- The full DB-backed suite passes without broader skips or weakened tests.
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` no longer describe the
  cycle debt as an unresolved active backlog item.

## Required Implementation Artifacts

- `docs/python_cycle_backlog_elimination_milestone_plan.md`
- updated routing docs:
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`
- focused cycle-import tests under `tests/unit/`
- any narrow contract or capability seam files needed to remove the cycles
- touched search, run, semantic, document, evaluation, and evidence owners
- `.github/workflows/architecture-governance.yml`
- same-milestone updates to `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`, and `config/hotspot_prevention.yaml` whenever
  owner routing or ratchets change

## Required Documentation And Handoff Updates

- Update this plan with milestone status, outcome label verification, and
  closeout commit hashes as each milestone lands.
- Update `docs/SESSION_HANDOFF.md` after every milestone that changes the next
  routed packet or the live cycle count.
- Update `docs/agentic_architecture_index.md` whenever this packet advances
  from drafted to active, from active to closed, or reroutes another packet.
- Update `docs/boring_change_architecture_milestone_plan.md` so the umbrella
  brief points to this packet for cycle work and does not claim direct
  ownership once closeout is complete.
- If any improvement case changes lifecycle state, update
  `config/improvement_cases.yaml` and the corresponding hygiene entry in the
  same milestone.

## Required Verification Gates

- Milestone 0 refresh:
  `git status -sb`
  `uv run docling-system-architecture-quality-report --summary`
  `uv run docling-system-hygiene-check`
  `uv run docling-system-improvement-case-summary`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown`
- Cycle implementation milestones:
  `git diff --check`
  `uv run ruff check <touched files>`
  `uv run pytest -q tests/unit/test_architecture_governance_imports.py <new cycle test files> <focused owner tests>`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
  `uv run docling-system-architecture-inspect`
  `uv run docling-system-architecture-decisions`
  `uv run docling-system-capability-contracts`
  `uv run docling-system-hygiene-check`
  `uv run docling-system-hotspot-prevention-check --strict`
  `uv run docling-system-improvement-case-validate`
- Focused service-cycle verification:
  `uv run pytest -q tests/unit/test_chat_service.py tests/unit/test_document_service.py tests/unit/test_evaluation_service.py tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py tests/unit/test_search_harnesses.py tests/unit/test_search_hydration.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_retrieval_primitives.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_run_logic.py`
- Focused provenance-cycle verification:
  `uv run pytest -q tests/unit/test_evidence_provenance.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_evidence_provenance_export_graph_report.py tests/unit/test_evidence_provenance_export_lifecycle.py`
- Focused evidence-search-cycle verification:
  `uv run pytest -q tests/unit/test_evidence_search_packages.py tests/unit/test_search_service_persistence.py tests/unit/test_search_execution_persistence.py`
- Checked-in import-boundary regression gate:
  `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`
- Final runtime verification:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- The live architecture probe reports `0` Python cycle components at closeout.
- The zero-cycle result is produced by explicit seam ownership, not local-import
  masking or equivalent opacity.
- No new `>800`-line file is introduced while removing the cycles.
- No touched compact facade regains moved implementation ownership.
- Replacement tests, fixtures, and gates retain equivalent or broader contract
  coverage than the pre-change checks they replace.
- The repo-owned architecture workflow runs the checked-in import-boundary
  regression command used for local closeout, while the external architecture
  probe remains the separate zero-cycle proof gate.
- The docs and owner registers agree on the same cycle count, active packet,
  and residual backlog after the final commit.

## Stop Conditions

- Stop if Milestone 0 shows the cycle membership or routed owner landscape has
  materially changed and this plan is no longer the honest next packet.
- Stop if the only available fix is local-import masking, import-time
  side-effect indirection, or another opaque workaround.
- Stop if breaking the large service cycle requires a public API, CLI, DB, or
  persisted artifact contract redesign that cannot remain compatibility-first.
- Stop if a milestone would create a new file above the `800`-line threshold or
  regrow a previously reduced facade just to remove one import edge.
- Stop before commit if the focused or full DB-backed verification stack fails
  or if unrelated dirty worktree changes cannot be separated safely.

## Local Commit Closeout Policy

Every milestone is complete only after verification passes, the required docs
and handoff updates land, and a local atomic commit records the milestone
slice. Before that point the milestone is ready-to-close, not complete.

For each milestone:

- stage only the verified cycle-resolution slice
- leave unrelated dirty or untracked files alone
- include code, tests, docs, workflow updates, generated routing artifacts, and
  owner-register edits that describe the milestone in the same commit
- record the closeout commit hash in this plan and in `docs/SESSION_HANDOFF.md`
- do not mark a milestone complete if its verification passed only because
  coverage became narrower or easier

## Residual Risks And Next Milestone Routing

- The large-file backlog remains after this packet even if the cycle backlog
  closes cleanly. That residual work should return to
  `docs/boring_change_architecture_milestone_plan.md` as the next queued
  large-file packet rather than keeping this cycle plan open.
- Existing open owner-family cases such as `IC-65AF4A6D8B1E`,
  `IC-6F4E2B5A91C3`, and `IC-C8D41A2F77BE` may still remain open for
  large-file ratchet reasons after the cycle debt is gone. That is acceptable
  if their cycle scope is actually resolved and the residual issue is routed
  honestly.
- If Milestone 1 proves the large service cycle cannot be closed inside one
  compatibility-preserving slice, stop and spin a fresh narrower follow-on plan
  for the specific surviving seam instead of widening this packet.

## Closeout Checklist

- [ ] Milestone 0 freshness readback captured and routing docs aligned
- [ ] Large service cycle removed with focused import-boundary tests
- [ ] Evidence provenance graph cycle removed
- [ ] Evidence search package / trace-store cycle removed
- [ ] Strict repo-owned cycle gate wired into workflow
- [ ] Full DB-backed verification passed
- [ ] Plan, handoff, architecture index, and umbrella brief updated
- [x] Atomic closeout commit recorded for each completed milestone
