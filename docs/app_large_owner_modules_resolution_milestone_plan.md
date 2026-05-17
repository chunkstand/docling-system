# App Large Owner Modules Resolution Milestone Plan

Date: 2026-05-15 local / 2026-05-15 UTC
Status: resolved locally in the working tree on 2026-05-15. Milestones 0
through 9 are complete locally; accepted routed residuals remain under
`IC-6F4E2B5A91C3` for `app/services/semantic_generation_brief.py` at `644`
lines and `IC-C8D41A2F77BE` for `app/services/semantic_graph_core.py` at
`697` lines plus `app/services/semantic_graph_promotions.py` at `718` lines.
Owner context: selected app-side large owner-module debt from the live
architecture probe:
`app/services/semantic_graph.py`,
`app/services/docling_parser.py`,
`app/services/quality.py`,
`app/services/semantic_candidates.py`,
`app/services/semantic_generation.py`,
`app/services/semantic_governance.py`, and
`app/services/runs.py`.
This packet intentionally excludes the test-monolith backlog and repo-wide
cycle-elimination work except where those surfaces are required to preserve the
selected owners' contracts.

## Purpose

Resolve the current concentration of implementation debt in the selected
app-side owner modules.

The scoped problem is not only line count. The selected files mix multiple
concern families, several sit on active runtime or parser seams, and only one
of the seven files is currently bound to an explicit open owner case. That
combination makes future change expensive even when the broader system is green.

This plan resolves that scoped gap by:

- refreshing the live baseline before code moves
- creating missing durable owner-case routing for the selected files
- reducing the selected files below the current `800`-line large-file threshold
- preserving public entrypoints and externally visible behavior
- blocking future sessions from hiding the same debt in adjacent already-large
  siblings

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-15
local / 2026-05-15 UTC:

```text
git status -sb
  ## main...origin/main [ahead 6]
  ?? .tmp/

wc -l app/services/semantic_graph.py app/services/docling_parser.py app/services/quality.py app/services/semantic_candidates.py app/services/semantic_generation.py app/services/semantic_governance.py app/services/runs.py
   1847 app/services/semantic_graph.py
   1555 app/services/docling_parser.py
   1444 app/services/quality.py
   1357 app/services/semantic_candidates.py
   1259 app/services/semantic_generation.py
   1157 app/services/semantic_governance.py
   1026 app/services/runs.py

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=501.06

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown
  41 code files exceed 800 lines
  hotspots include:
    app/services/runs.py score=23598
    app/services/docling_parser.py score=23325
    app/services/quality.py score=15884
    app/services/semantic_graph.py score=12929
  remaining cycle components=3

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt includes:
    app/services/semantic_governance.py = 1157 lines under IC-81C531769EB3
```

Repo-current structural evidence:

- The selected set accounts for `9645` lines of app-side implementation debt.
- `app/services/runs.py`, `app/services/docling_parser.py`,
  `app/services/quality.py`, and `app/services/semantic_graph.py` are both
  large files and live churn hotspots according to the current architecture
  probe.
- Only `app/services/semantic_governance.py` is currently routed through an
  open improvement case, `IC-81C531769EB3`. The selected files
  `app/services/docling_parser.py`, `app/services/quality.py`,
  `app/services/runs.py`, `app/services/semantic_graph.py`,
  `app/services/semantic_candidates.py`, and
  `app/services/semantic_generation.py` do not yet have dedicated owner-case
  entries in `config/improvement_cases.yaml`.
- The prior semantics boundary closeout explicitly forbade spilling work into
  `semantic_graph.py`, `semantic_candidates.py`, `semantic_generation.py`,
  `semantic_governance.py`, and `runs.py`, which means this residual debt now
  has to be owned directly rather than hidden behind `app/services/semantics.py`.
- The selected modules sit on stability-sensitive behavior:
  parser conversion and supplement overlays in `docling_parser.py`,
  validation-gated promotion and worker lease handling in `runs.py`,
  quality status/candidate/trend reads in `quality.py`, and semantic
  generation/graph/governance APIs and roundtrips across the remaining semantic
  owners.

## Goal

Resolve the selected large-owner-module debt so that:

- each of the seven selected files measures `<= 800` lines on a fresh baseline
- each selected owner has durable improvement-case routing and hygiene-owner
  coverage
- public entrypoints for parser, run processing, quality, and semantic service
  callers remain behavior-compatible
- no new file in the selected owner families exceeds `800` lines
- any newly created owner module between `601` and `800` lines is explicitly
  routed in `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
  in the same milestone
- the architecture probe does not report more than the current baseline of
  `3` cycle components after closeout

## Non-Goals

- No test-monolith cleanup packet.
- No repo-wide cycle-elimination packet.
- No threshold reduction from `800` to the default `600` hygiene budget for the
  whole repo in this sequence.
- No microservice extraction or runtime-platform rewrite.
- No widening of skips, xfails, or fixture deletion to make the result green.
- No search, claim-support, evidence, CLI, or architecture-governance cleanup
  outside the touched owner surfaces.

## Scope

In scope:

- live Milestone 0 freshness and owner-case bootstrap for the selected files
- one-owner-at-a-time reduction of the selected files below `800` lines
- compatibility-preserving extraction of focused owner modules in
  `app/services/`
- focused test and integration updates needed to preserve the selected
  contracts
- selected-family hygiene ratchets, improvement-case routing, and targeted
  hotspot-prevention coverage where a new facade or blocked-regrowth rule is
  warranted
- docs and handoff alignment for the new plan and the resulting milestones

Out of scope:

- reducing unrelated large files such as `app/services/semantic_orchestration.py`,
  `app/services/technical_reports.py`, or repo-wide test hotspots
- forcing all extracted owner modules under the default `600` budget if the
  selected file can be resolved first with explicit routed residuals
- closing existing cycle components that do not move when the selected owners
  are split

## Owner Surfaces

- parser family:
  `app/services/docling_parser.py`,
  new `app/services/docling_parser_*.py` owners,
  `config/table_supplements.yaml`,
  `tests/unit/test_docling_parser.py`
- run-processing family:
  `app/services/runs.py`,
  new `app/services/run_*.py` owners,
  `app/services/runtime.py`,
  `app/services/validation.py`,
  `app/services/run_failure_artifacts.py`,
  `tests/unit/test_run_logic.py`
- quality family:
  `app/services/quality.py`,
  new `app/services/quality_*.py` owners,
  `app/schemas/quality.py`,
  `tests/unit/test_quality_service.py`,
  `tests/unit/test_quality_api.py`,
  `tests/integration/test_quality_roundtrip.py`
- semantic residual family:
  `app/services/semantic_graph.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_governance.py`,
  new focused `app/services/semantic_*` owners,
  `app/services/semantics.py`,
  `app/api/routers/semantics.py`,
  `tests/unit/test_semantic_graph.py`,
  `tests/unit/test_semantic_candidates.py`,
  `tests/unit/test_semantic_generation.py`,
  `tests/unit/test_semantic_governance.py`,
  `tests/unit/test_documents_api_semantics.py`,
  `tests/unit/test_semantic_orchestration.py`,
  `tests/unit/test_semantic_backfill_api.py`,
  `tests/integration/test_semantic_generation_roundtrip.py`,
  `tests/integration/test_semantic_graph_roundtrip.py`,
  `tests/integration/test_semantic_governance_ledger.py`,
  `tests/integration/test_semantic_backfill_roundtrip.py`,
  `tests/integration/test_postgres_roundtrip.py`
- routing and prevention:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `tests/unit/test_hotspot_prevention.py`
- durable docs:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `SYSTEM_PLAN.md` when it still names stale large-owner debt after closeout

## Placement Rules

- Keep existing public entrypoints stable. New family code belongs in focused
  sibling owners such as `docling_parser_*.py`, `run_*.py`, `quality_*.py`,
  and semantic family-specific modules, not in already-large adjacent files.
- Do not use `app/services/semantics.py`, `app/services/semantic_orchestration.py`,
  `app/services/semantic_registry.py`, `app/services/semantic_backfill.py`,
  `app/services/evaluations.py`, `app/services/documents.py`, or
  `app/services/technical_reports.py` as sink files for moved implementation.
- Parser work must preserve `DoclingParser`, `ParsedDocument`, `ParsedTable`,
  `ParsedFigure`, table supplement overlay behavior, artifact schema versions,
  and source-segment provenance expectations.
- Run-processing work must preserve claim/requeue semantics, lease heartbeat
  behavior, validation-gated promotion, runtime heartbeats, and worker-loop
  behavior.
- Quality work must preserve response schema shapes and keep in-memory and DB
  session behavior aligned.
- Semantic residual work must preserve the currently imported public functions
  from `semantic_generation.py`, `semantic_candidates.py`,
  `semantic_graph.py`, and `semantic_governance.py`; the split may narrow those
  files into forwarding entrypoints or compact facades, but callers must not be
  forced to retarget imports mid-sequence.
- Any new owner module above `600` lines must receive same-milestone
  owner-case routing and a hygiene ratchet. No new or touched file may exceed
  `800` lines at milestone closeout.
- Only add hotspot-prevention rules when a real compatibility facade or
  blocked-regrowth seam is introduced. Do not grow the primary classifier by
  default when hygiene ratchets and owner-case routing are sufficient.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A milestone reduces one selected file by moving code into another already-large sibling. | selected owner files, staged diff, `config/hygiene_policy.yaml`, architecture probe | `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown`, `uv run docling-system-hygiene-check`, staged `wc -l` review | Any touched sibling in the selected family grows above its recorded ceiling or a new `>800` file appears | Temporarily move semantic generation helpers into `semantic_orchestration.py` or parser helpers into `runs.py` and confirm closeout rejects the slice | A future session sees a nearby semantic filename and uses it as the easiest dump target |
| The split creates new owner modules but leaves them unrouted. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, this plan, handoff | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, docs review | A selected file or new `601-800` owner closes a milestone without a case entry and hygiene owner | Create a temporary `quality_trends.py` above `600` lines without registry updates and confirm validation or closeout review blocks it | Future Codex treats the split as purely mechanical and forgets the durable routing work |
| Parser refactoring breaks supplement overlays, artifact payloads, or figure/table provenance. | `app/services/docling_parser.py`, new parser owners, `config/table_supplements.yaml`, parser tests | `uv run pytest -q tests/unit/test_docling_parser.py`, full DB-backed integration closeout | Table supplements, figure metadata, or artifact payload expectations change without stronger coverage | Temporarily remove supplement overlay path resolution or table-family validation and confirm parser tests fail | Future Codex isolates helper code but drops the provenance-preserving behavior that made supplements safe |
| Run-processing refactoring weakens promotion, validation, retry, or heartbeat behavior. | `app/services/runs.py`, new run owners, runtime/validation dependencies, run tests | `uv run pytest -q tests/unit/test_run_logic.py`, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py`, final full integration | Active-run promotion, failure artifact handling, or runtime heartbeat behavior changes unexpectedly | Temporarily stop calling `runtime_process_heartbeat(...)` or skip `execute_semantic_pass(...)` after promotion and confirm tests or integration fail | Future Codex narrows the file but silently weakens the worker and promotion contract |
| Semantic family work regresses the public route and roundtrip behavior while shrinking files. | semantic owner files, `app/api/routers/semantics.py`, semantic unit and integration tests | focused semantic unit slice plus semantic roundtrip integrations | Any selected semantic split requires callers to change imports or causes route/integration regressions | Move verification or promotion logic into a hidden helper without preserving the public entrypoint and confirm the semantic unit or integration slice fails | Future Codex treats the large semantic files as internal-only and forgets that routes and workers import them directly |
| Prevention work recreates debt inside `app/hotspot_prevention_classifier.py`. | `app/hotspot_prevention_classifier.py`, `config/hotspot_prevention.yaml`, `tests/unit/test_hotspot_prevention.py` | `uv run docling-system-hygiene-check`, `uv run pytest -q tests/unit/test_hotspot_prevention.py`, staged `wc -l` review | The classifier grows past its current `999`-line ceiling without a paired extraction or stronger justification in the same milestone | Add a second large branch directly to the classifier rather than a support owner and confirm hygiene or closeout review blocks it | Future Codex keeps encoding every residual boundary as another classifier branch instead of extracting support logic |

Accepted residual after plan closeout:

- If a newly created owner module lands between `601` and `800` lines, that is
  accepted only when the same milestone records explicit owner-case routing and
  a hygiene ratchet for that owner. Unrouted residuals are not accepted.
- If the selected owner work does not reduce the repo-wide cycle count below
  the current baseline of `3`, that residual is accepted only when the cycle
  count does not increase and the selected files themselves are resolved.

## Milestone Sequence

Milestone 0 is mandatory and must run before any production code changes.

### Milestone 0 - Live Baseline Lock And Owner-Case Bootstrap

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `reduced`

- Refresh `git status -sb`, the selected `wc -l` baseline,
  `uv run docling-system-improvement-case-summary`,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-architecture-quality-report --summary`, and the
  architecture probe.
- Replace every draft-time count in this plan if live measurements changed.
- Create durable improvement cases for the six currently unrouted selected
  files:
  `docling_parser.py`, `quality.py`, `runs.py`, `semantic_graph.py`,
  `semantic_candidates.py`, and `semantic_generation.py`.
- Refresh `IC-81C531769EB3` for `semantic_governance.py` with the new baseline.
- Add or refresh hygiene-owner entries for every selected file and any
  pre-existing extracted owner in this family that already exceeds `600` lines.
- Decide which later milestones need hotspot-prevention entries; do not add
  classifier growth without recording the intended owner seam here first.

Acceptance:

- every selected file has durable owner routing before code moves
- this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` reflect the live baseline
- no production code changed outside routing or docs

Milestone 0 progress update:

- `uv run docling-system-improvement-case-validate` now returns `valid=true`
  after creating `IC-9A0332D41F79`, `IC-33B4990DC366`,
  `IC-8AFAD4A415CA`, `IC-865AB8419D55`, `IC-649D7B4E3AB5`, and
  `IC-A92BA42C6D18`, and refreshing `IC-81C531769EB3`.
- `uv run docling-system-improvement-case-summary` now reports `case_count=46`,
  `status_counts.open=30`, and `measured_case_count=41`.
- `uv run docling-system-hygiene-check` still reports `new hygiene
  regressions: none` while the seven selected owners now appear as explicit
  inherited debt under their routed case IDs instead of unrouted large-file
  entries.
- New routed residual owner-family cases now record the extracted oversize
  semantic follow-ons: `IC-6F4E2B5A91C3` for
  `app/services/semantic_generation_brief.py` and `IC-C8D41A2F77BE` for
  `app/services/semantic_graph_core.py` plus
  `app/services/semantic_graph_promotions.py`.

### Milestone 1 - Run Processing Boundary

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Split run lease/claim/requeue and heartbeat ownership from artifact
  persistence, promotion, and worker-loop orchestration.
- Keep `app/services/runs.py` as the public entrypoint for the existing run
  processing API.
- Preserve `process_run(...)`, `claim_next_run(...)`, retry behavior, failure
  artifact handling, validation-gated promotion, and runtime-heartbeat wiring.

Acceptance:

- `app/services/runs.py` measures `<= 800` lines
- no new run-family owner module exceeds `800` lines
- `tests/unit/test_run_logic.py` passes
- `tests/integration/test_postgres_roundtrip.py` and the final full
  DB-backed suite preserve the run-processing behavior

### Milestone 2 - Docling Parser Conversion And Overlay Boundary

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `reduced`

- Extract converter selection, fallback/rescue policy, supplement-registry
  loading, and overlay-path resolution into focused parser owners.
- Preserve `DoclingParser`, parsed dataclasses, and supplement configuration
  loading through the public parser surface.

Acceptance:

- `app/services/docling_parser.py` is materially reduced from the Milestone 0
  baseline and no new parser-family file exceeds `800` lines
- parser unit coverage for converter and supplement behavior is green
- the remaining parser debt is narrowed to normalization and table/figure
  ownership routed to Milestone 3

### Milestone 3 - Docling Parser Table, Figure, And Normalization Closeout

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Extract chunk normalization, table-family grouping/merge logic, figure
  caption/title recovery, and artifact payload helpers into focused parser
  owners.
- Preserve table supplement provenance and the current table and figure artifact
  payload contract.

Acceptance:

- `app/services/docling_parser.py` measures `<= 800` lines
- parser-family owner modules stay within the milestone thresholds
- `tests/unit/test_docling_parser.py` passes
- final full DB-backed integration remains green after parser closeout

### Milestone 4 - Quality Evaluation Boundary

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Split quality status/summary reads, candidate scanning and resolution, and
  quality trend reporting into focused quality owners.
- Preserve the public `quality.py` service entrypoints and response-shape
  compatibility.

Acceptance:

- `app/services/quality.py` measures `<= 800` lines
- `tests/unit/test_quality_service.py` and `tests/unit/test_quality_api.py`
  pass
- `tests/integration/test_quality_roundtrip.py` passes
- no quality logic spills back into `app/services/evaluations.py`

### Milestone 5 - Semantic Generation Boundary

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Split brief preparation, drafting, and verification ownership into focused
  semantic generation owners.
- Preserve the current public entrypoints for semantic generation callers and
  tests.

Acceptance:

- `app/services/semantic_generation.py` measures `<= 800` lines
- `tests/unit/test_semantic_generation.py` passes
- `tests/integration/test_semantic_generation_roundtrip.py` passes
- no generation debt is moved into `semantic_graph.py`,
  `semantic_candidates.py`, or `semantic_governance.py`

### Milestone 6 - Semantic Candidate Extraction Boundary

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Split extractor execution/materialization, corpus export/evaluation, and
  disagreement triage/shadow-candidate ownership into focused candidate owners.
- Preserve the current public entrypoints used by evaluation and operator
  callers.

Acceptance:

- `app/services/semantic_candidates.py` measures `<= 800` lines
- `tests/unit/test_semantic_candidates.py` passes
- candidate-family owners stay within the milestone thresholds
- no candidate debt is pushed into `semantic_generation.py` or
  `semantic_graph.py`

### Milestone 7 - Semantic Graph Boundary

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Split graph payload construction, evaluation/triage, and promotion lifecycle
  ownership into focused graph owners.
- Preserve the public graph snapshot, draft, verify, apply, and memory
  entrypoints used by routes, agents, and integrations.

Acceptance:

- `app/services/semantic_graph.py` measures `<= 800` lines
- `tests/unit/test_semantic_graph.py` passes
- `tests/integration/test_semantic_graph_roundtrip.py` passes
- the architecture probe does not report more than the Milestone 0 cycle
  baseline after the graph split

### Milestone 8 - Semantic Governance Boundary

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Split event-recording families, active-basis context construction, and
  chain-audit/integrity projection ownership into focused governance owners.
- Update `IC-81C531769EB3` with final measurements and residual routing, if any.

Acceptance:

- `app/services/semantic_governance.py` measures `<= 800` lines
- `tests/unit/test_semantic_governance.py` passes
- `tests/integration/test_semantic_governance_ledger.py` passes
- no new governance-family owner exceeds `800` lines

### Milestone 9 - Selected Large-Owner Closeout

Status: resolved locally in the working tree on 2026-05-15
Outcome label: `resolved`

- Re-run the full selected verification stack and refresh all line-count,
  routing, hygiene, and architecture evidence.
- Update this plan with actual closeout status and residual routing.
- Update the handoff and architecture index with the commit hashes,
  verification commands, and any accepted routed residuals.
- If `SYSTEM_PLAN.md` still names one of the selected files as active large
  owner debt after closeout, refresh it to the new live state.

Acceptance:

- each selected file measures `<= 800` lines on fresh `wc -l`
- no new or touched file in the selected families exceeds `800` lines
- every selected file has durable improvement-case routing and hygiene-owner
  coverage
- the architecture probe no longer lists any selected file above `800` lines
- cycle components do not exceed the Milestone 0 baseline of `3`
- final `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` passes

Milestone 9 closeout update:

- Selected root owners now measure `199`, `15`, `404`, `120`, `91`, `39`, and
  `185` lines respectively for
  `app/services/docling_parser.py`,
  `app/services/quality.py`,
  `app/services/runs.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_governance.py`, and
  `app/services/semantic_graph.py`.
- Accepted routed residuals remain under `IC-6F4E2B5A91C3` for
  `app/services/semantic_generation_brief.py` at `644` lines and
  `IC-C8D41A2F77BE` for `app/services/semantic_graph_core.py` at `697` lines
  plus `app/services/semantic_graph_promotions.py` at `718` lines.
- Verification is green on the final closeout snapshot:
  `git diff --check`,
  `uv run ruff check app/services app/api tests/unit tests/integration config`,
  the governed unit slice at `123 passed`,
  the named DB-backed integration slice at `16 passed`,
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` at `1995 passed`,
  `uv run docling-system-hygiene-check` with `new hygiene regressions: none`,
  `uv run docling-system-improvement-case-validate` with `valid=true`,
  `uv run docling-system-improvement-case-summary` with `case_count=46`,
  `status_counts.open=30`, and `measured_case_count=41`,
  `uv run docling-system-architecture-quality-report --summary` with
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, and `max_hotspot_risk_score=501.06`,
  `uv run docling-system-architecture-inspect` with `valid=true` and
  `violation_count=0`, and the architecture probe with `3` Python cycle
  components and no selected root owner remaining above `800` lines.

## Required Implementation Artifacts

- focused new owner modules under `app/services/` for parser, runs, quality,
  and the semantic residual families
- updated owner-case entries in `config/improvement_cases.yaml` for every
  selected file
- updated ratchets in `config/hygiene_policy.yaml` for every selected file and
  any accepted new `601-800` owners
- targeted hotspot-prevention updates only where a true compatibility facade or
  blocked-regrowth seam is introduced
- compatibility-preserving tests for any newly created forwarding facade or
  public entrypoint

## Required Documentation And Handoff Updates

- update this plan with actual milestone status, outcome labels, evidence, and
  residual routing
- update `docs/SESSION_HANDOFF.md` with the active milestone, verification
  commands, commit hash, accepted residuals, and next routing
- update `docs/agentic_architecture_index.md` so the current drafted plan list
  routes future work to this narrower packet instead of the broader stale
  summary
- update `SYSTEM_PLAN.md` if it still points future work at a selected file
  that is no longer the live debt surface after closeout

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services app/api tests/unit tests/integration config`
- `uv run pytest -q tests/unit/test_docling_parser.py tests/unit/test_run_logic.py tests/unit/test_quality_service.py tests/unit/test_quality_api.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py tests/unit/test_semantic_governance.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_quality_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_governance_ledger.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-architecture-inspect`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown`

## Acceptance Criteria

- the selected files
  `semantic_graph.py`,
  `docling_parser.py`,
  `quality.py`,
  `semantic_candidates.py`,
  `semantic_generation.py`,
  `semantic_governance.py`, and
  `runs.py`
  each measure `<= 800` lines on a fresh baseline
- the six currently unrouted selected files are no longer unrouted in
  `config/improvement_cases.yaml`
- `IC-81C531769EB3` is refreshed to the final `semantic_governance.py`
  measurement and residual state
- no selected-family implementation debt is hidden in
  `semantic_orchestration.py`,
  `semantic_registry.py`,
  `semantic_backfill.py`,
  `semantics.py`,
  `evaluations.py`,
  `documents.py`, or
  `technical_reports.py`
- no new owner module in the selected families exceeds `800` lines
- any newly created owner module between `601` and `800` lines is explicitly
  routed and ratcheted in the same milestone
- the focused parser, run, quality, and semantic unit and integration slices
  pass without weakened coverage
- the final full DB-backed integration suite passes
- docs and handoff updates land in the same milestone commit as the verified
  code slice they describe

## Stop Conditions

- Milestone 0 shows that the selected file set is no longer the right slice and
  a different live offender set should be routed instead
- a reduction would require public API, DB schema, or runtime-contract changes
  outside the listed owner surfaces
- the only way to reduce a selected file is to move implementation into another
  already-large adjacent owner
- the split would require growing `app/hotspot_prevention_classifier.py` beyond
  its current ceiling without a same-milestone extraction
- the focused or full integration gates fail because of unrelated system
  breakage that prevents trustworthy milestone verification
- user-owned edits appear in the same selected files and cannot be safely
  separated from the milestone slice

## Local Commit Closeout Policy

- Close each milestone with a local atomic commit after verification passes.
- Stage only the verified milestone slice.
- Leave unrelated dirty or untracked files, including `.tmp/`, alone unless the
  user explicitly asks to clean them.
- Include code, tests, config updates, docs, and handoff changes for that
  milestone in the same commit.
- Record the commit hash in `docs/SESSION_HANDOFF.md` and this plan.
- Treat a verified but uncommitted milestone as ready-to-close, not complete.

## Residual Risks And Next Routing

- This plan resolves the selected app-side large-owner-module debt only. Other
  large files such as `app/services/semantic_orchestration.py`,
  `app/services/technical_reports.py`, `app/services/evaluation_fixtures.py`,
  and large test files remain outside this packet.
- If the selected files close below `800` but some extracted owner modules land
  between `601` and `800` lines, that is accepted only with explicit routed
  follow-on ownership in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`.
- If the repo-wide cycle count remains at the Milestone 0 baseline after the
  selected files close, route cycle-only cleanup through a fresh standalone
  packet rather than broadening this one at the end.
- After this packet closes, the next follow-on should be chosen from live
  post-closeout evidence rather than reviving the draft-time `boring_change`
  owner list unchanged.
