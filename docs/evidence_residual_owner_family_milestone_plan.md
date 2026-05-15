# Evidence Residual Owner Family Milestone Plan

Date: 2026-05-15 local / 2026-05-15 UTC
Status: active standalone follow-on after
`docs/evidence_provenance_exports_boundary_milestone_plan.md`; Milestone 0 is
resolved locally through closeout commit `44bec70` on 2026-05-15 and
Milestone 1 is now the next implementation slice
Owner context: residual evidence owner-family debt after the closeout that
reduced `app/services/evidence.py` to a 141-line compatibility facade and
`app/services/evidence_provenance_exports.py` to a 14-line compatibility
facade. This packet is intentionally narrower than
`docs/boring_change_architecture_milestone_plan.md` and is centered on the
four selected residual evidence owners:
`app/services/evidence_technical_report_exports.py`,
`app/services/evidence_semantic_trace.py`,
`app/services/evidence_claim_feedback.py`, and
`app/services/evidence_audit_views.py`.

## Local Progress

- Milestone 0 is resolved locally through closeout commit `44bec70`. The
  selected evidence owners still measure `884`, `837`, `834`, and `699` lines
  respectively, so the packet remains narrowed to those four files rather than
  widening into immediate retirement of `IC-65AF4A6D8B1E`.
- `IC-65AF4A6D8B1E` remains broader than the selected packet because
  `app/services/evidence_manifest_traces.py` still measures `980` lines,
  `app/services/evidence_manifests.py` still measures `725`, and
  `app/services/evidence_claim_support_replay_alerts.py` still measures `646`.
  Broader case retirement remains an explicit follow-on, not a Milestone 0
  claim.
- Skeletal owner-test seams now exist in
  `tests/unit/test_evidence_claim_feedback.py`,
  `tests/unit/test_evidence_semantic_trace.py`, and
  `tests/unit/test_evidence_audit_views.py`, so the next production split does
  not start from zero direct owner coverage.
- Milestone 0 closeout verification is recorded and green: `git diff --check`,
  focused `ruff`, focused evidence-owner `pytest` at `13 passed`,
  improvement-case validate or summary, hygiene, architecture inspection,
  architecture quality summary, and the architecture probe all stayed green
  without rerunning the full DB-backed suite because the slice changed only
  docs, registry metadata, and owner-test seams.
- Milestone 1, `Technical Report Derivation And Lock Boundary`, is now the next
  active implementation slice for this packet.

## Local Verification

- `git diff --check` passed
- `uv run ruff check tests/unit/test_evidence_technical_report_exports.py tests/unit/test_evidence_claim_feedback.py tests/unit/test_evidence_semantic_trace.py tests/unit/test_evidence_audit_views.py tests/unit/test_evidence_facade_contract.py` passed
- `uv run pytest -q tests/unit/test_evidence_technical_report_exports.py tests/unit/test_evidence_claim_feedback.py tests/unit/test_evidence_semantic_trace.py tests/unit/test_evidence_audit_views.py tests/unit/test_evidence_facade_contract.py` passed at `13 passed`
- `uv run docling-system-improvement-case-validate` returned `valid=true`
- `uv run docling-system-improvement-case-summary` reported `case_count=46`, `status_counts.open=30`, and `measured_case_count=41`
- `uv run docling-system-hygiene-check` reported `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect` remained `valid=true` with `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary` reported `hotspot_count=10` and `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20` still reported `3` Python cycle components
- Full DB-backed integration was intentionally not rerun for this slice because Milestone 0 changed no production code, API contracts, DB schema, or runtime paths

## Purpose

Resolve the remaining dense implementation debt in the selected evidence owner
modules without reopening the already-closed `app/services/evidence.py`
compatibility-facade work.

The scoped problem is not the public evidence facade anymore. The remaining
debt is that the selected owner modules still combine several distinct concern
families:

- technical-report derivation lock assembly, package shaping, persistence, and
  attachment helpers still coexist in
  `app/services/evidence_technical_report_exports.py`
- technical-report integrity recomputation, semantic trace materialization,
  source-record shaping, and provenance-edge graph assembly still coexist in
  `app/services/evidence_semantic_trace.py`
- retrieval-context shaping, feedback payload construction, integrity
  verification, and append-only ledger persistence still coexist in
  `app/services/evidence_claim_feedback.py`
- provenance receipt shaping, context-pack audit gathering, release-readiness
  DB-gate persistence, and the main audit-bundle aggregation still coexist in
  `app/services/evidence_audit_views.py`

This plan resolves the selected residual by:

- refreshing the live post-provenance-export baseline before code moves
- splitting the selected files along real owner seams rather than cosmetic
  helper moves
- requiring dedicated owner-module tests for the three selected files that do
  not currently have them
- keeping `app/services/evidence.py` and
  `app/services/evidence_provenance_exports.py` as narrow compatibility seams
- making the broader `IC-65AF4A6D8B1E` case status honest if other evidence
  owners still remain above budget after the selected four close

## Current Evidence

Milestone 0 baseline evidence refreshed from the current local checkout on
2026-05-15 local / 2026-05-15 UTC before the no-production-code scope-lock
updates landed:

```text
git status -sb
  ## main...origin/main [ahead 6]
   M config/hygiene_policy.yaml
   M config/improvement_cases.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M docs/boring_change_architecture_milestone_plan.md
  ?? .tmp/
  ?? docs/app_large_owner_modules_resolution_milestone_plan.md
  ?? docs/semantic_residual_owner_family_milestone_plan.md

wc -l app/services/evidence.py app/services/evidence_technical_report_exports.py app/services/evidence_semantic_trace.py app/services/evidence_claim_feedback.py app/services/evidence_audit_views.py
   141 app/services/evidence.py
   884 app/services/evidence_technical_report_exports.py
   837 app/services/evidence_semantic_trace.py
   834 app/services/evidence_claim_feedback.py
   699 app/services/evidence_audit_views.py

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt includes:
    app/services/evidence_audit_views.py = 699 lines under IC-65AF4A6D8B1E
    app/services/evidence_claim_feedback.py = 834 lines under IC-65AF4A6D8B1E
    app/services/evidence_semantic_trace.py = 837 lines under IC-65AF4A6D8B1E
    app/services/evidence_technical_report_exports.py = 884 lines under IC-65AF4A6D8B1E
    app/services/evidence_claim_support_replay_alerts.py = 646 lines under IC-65AF4A6D8B1E
    app/services/evidence_manifests.py = 725 lines under IC-65AF4A6D8B1E
    app/services/evidence_manifest_traces.py = 980 lines under IC-65AF4A6D8B1E

uv run docling-system-improvement-case-summary
  case_count=46
  status_counts.open=30
  measured_case_count=41

uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=501.06
  top_hotspot_paths include app/services/evidence.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  remaining cycle components=3
  selected evidence owners are not currently part of a reported Python cycle component
```

Repo-current structural evidence:

- `config/improvement_cases.yaml` still records `IC-65AF4A6D8B1E` as the live
  open owner-family case, but the selected excerpt is narrower than the live
  hygiene register. The four selected files still exceed the default `600`-line
  budget, and the same case also still governs
  `app/services/evidence_manifest_traces.py`,
  `app/services/evidence_manifests.py`, and
  `app/services/evidence_claim_support_replay_alerts.py`.
- `app/services/evidence_technical_report_exports.py` currently mixes:
  release-binding lookup, audit-bundle and receipt lookup, provenance-lock and
  support-judgment contract mismatch checks, provenance-lock application,
  derivation package shaping, export persistence, attachment helpers, and row
  payload shaping.
- `app/services/evidence_claim_feedback.py` currently mixes:
  verdict-to-feedback classification, retrieval-span and request/result
  materialization, source payload shaping, feedback payload shaping, row
  integrity verification, integrity summary reporting, row lookup, append-only
  live-link enforcement, and ledger persistence.
- `app/services/evidence_semantic_trace.py` currently mixes:
  semantic assertion and fact payload shaping, technical-report derivation
  integrity recomputation, semantic trace DB materialization, source-record
  payload shaping, evidence-card source record shaping, and the large
  technical-report provenance-edge expansion body.
- `app/services/evidence_audit_views.py` currently mixes:
  provenance-export receipt shaping, technical-report context-pack audit
  collection, release-readiness DB-gate persistence plus governance event
  backfill, and the main audit-bundle aggregation read surface.
- Milestone 0 closes the missing owner-test seam with skeletal baseline suites
  at
  `tests/unit/test_evidence_claim_feedback.py`,
  `tests/unit/test_evidence_semantic_trace.py`, and
  `tests/unit/test_evidence_audit_views.py`.

## Goal

Resolve the selected residual evidence-owner issue so that:

- `app/services/evidence_technical_report_exports.py`,
  `app/services/evidence_semantic_trace.py`,
  `app/services/evidence_claim_feedback.py`, and
  `app/services/evidence_audit_views.py`
  all measure `<= 600` lines on a fresh closeout baseline
- each selected file owns only one narrow concern family or becomes a stable
  forwarding seam to focused sibling owners
- `app/services/evidence.py` remains a narrow compatibility facade and
  `app/services/evidence_provenance_exports.py` remains a narrow provenance
  export seam
- dedicated owner tests exist for claim feedback, semantic trace, and audit
  views before the packet closes
- the selected owner work does not increase the architecture-probe cycle count
  above the live baseline of `3`
- the closeout truthfully distinguishes between:
  selected four-file closure, and
  broader `IC-65AF4A6D8B1E` retirement if other live case-owned files still
  remain above budget

## Non-Goals

- No reopening of `app/services/evidence.py` as a broad implementation owner.
- No provenance-export graph rewrite of
  `app/services/evidence_provenance_export_graph_core.py`,
  `app/services/evidence_provenance_export_graph_report.py`, or
  `app/services/evidence_provenance_export_lifecycle.py`.
- No API, CLI, DB schema, migration, or storage-contract redesign.
- No claim-support feature work or semantic-governance behavior redesign beyond
  compatibility-preserving owner splits.
- No silent absorption of debt into
  `app/services/evidence_manifest_traces.py`,
  `app/services/evidence_manifests.py`, or
  `app/services/evidence_claim_support_replay_alerts.py`.
- No weakened unit, integration, or release-readiness coverage.

## Scope

In scope:

- Milestone 0 live refresh and selected-scope lock for the residual evidence
  owner family
- technical-report export family decomposition
- claim-feedback family decomposition
- semantic-trace family decomposition
- audit-view family decomposition
- dedicated focused unit coverage for the selected owners
- routing, hygiene, hotspot-prevention, index, and handoff updates required by
  the selected owners

Out of scope unless Milestone 0 explicitly widens the packet:

- `app/services/evidence_manifest_traces.py`
- `app/services/evidence_manifests.py`
- `app/services/evidence_claim_support_replay_alerts.py`
- new technical-report product capabilities
- search, claim-support, semantics, or agent-task architecture work outside the
  selected evidence seams

## Owner Surfaces

- technical-report export family:
  `app/services/evidence_technical_report_exports.py`,
  new focused owners under `app/services/evidence_technical_report_*.py`,
  `tests/unit/test_evidence_technical_report_exports.py`,
  `tests/unit/test_technical_reports.py`
- claim-feedback family:
  `app/services/evidence_claim_feedback.py`,
  new focused owners under `app/services/evidence_claim_feedback_*.py`,
  `tests/unit/test_evidence_claim_feedback.py`
- semantic-trace family:
  `app/services/evidence_semantic_trace.py`,
  new focused owners under `app/services/evidence_semantic_trace_*.py`,
  `tests/unit/test_evidence_semantic_trace.py`
- audit-view family:
  `app/services/evidence_audit_views.py`,
  new focused owners under `app/services/evidence_audit_*.py`,
  `tests/unit/test_evidence_audit_views.py`
- adjacent compatibility callers that must remain stable:
  `app/services/evidence.py`,
  `app/services/evidence_provenance_exports.py`,
  `app/services/evidence_release_readiness.py`,
  `app/services/evidence_technical_report_context.py`,
  `app/services/evidence_records.py`,
  `app/services/evidence_search_closure.py`,
  `app/services/semantic_governance.py`,
  `tests/unit/test_evidence_facade_contract.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_technical_report_harness_integrity.py`,
  `tests/integration/test_technical_report_harness_source_evidence.py`,
  `tests/integration/test_technical_report_harness_audit_surfaces.py`,
  `tests/integration/test_semantic_governance_ledger.py`,
  `tests/integration/test_retrieval_learning_ledger.py`,
  `tests/integration/test_evidence_operator_runs_roundtrip.py`
- routing and prevention:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `tests/unit/test_hotspot_prevention.py`
- durable docs:
  this plan,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`

## Placement Rules

- Keep `app/services/evidence.py` as the public compatibility facade. Do not
  move implementation back into it.
- Keep `app/services/evidence_provenance_exports.py` as the narrow provenance
  export seam closed by the prior packet. Do not repack provenance-export graph
  work into it.
- New technical-report export ownership belongs under focused
  `app/services/evidence_technical_report_*.py` siblings, not in
  `app/services/technical_reports.py` or `app/services/evidence_provenance.py`.
- New claim-feedback ownership belongs under focused
  `app/services/evidence_claim_feedback_*.py` siblings, not in
  `app/services/evidence_audit_views.py` or
  `app/services/semantic_governance.py`.
- New semantic-trace ownership belongs under focused
  `app/services/evidence_semantic_trace_*.py` siblings. Do not create a new
  trace or graph catch-all that recreates the same broad owner under a
  different filename.
- New audit-view ownership belongs under focused `app/services/evidence_audit_*.py`
  siblings. Do not reduce `evidence_audit_views.py` by dumping release-readiness
  logic into already-large adjacent evidence owners.
- Any new owner module above `600` lines must receive same-milestone owner-case
  routing and a hygiene ratchet. No new or touched file may exceed `800` lines
  at milestone closeout.
- Do not grow `app/hotspot_prevention_classifier.py` by default. Only add
  classifier branches when a real regrowth seam is introduced and the same
  milestone proves the classifier remains under its own active ceiling.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Technical-report export work reduces the file by pushing derivation or persistence bodies into `app/services/evidence.py`, `app/services/technical_reports.py`, or `app/services/evidence_provenance.py`. | `evidence_technical_report_exports.py`, adjacent evidence callers, staged diff | `uv run docling-system-hygiene-check`, focused export tests, staged `wc -l` review | Any touched adjacent caller absorbs moved implementation or the selected file remains above its routed ceiling without explicit follow-on routing | Temporarily move derivation-persistence helpers into `technical_reports.py` and confirm closeout review rejects the slice | A future session sees the technical-report namespace and treats the report service as the easiest overflow location |
| Claim-feedback work stays architecturally broad because payload shaping, integrity, and ledger persistence remain cohabiting behind renamed helpers. | `evidence_claim_feedback.py`, new claim-feedback owners, new unit suite | `uv run pytest -q tests/unit/test_evidence_claim_feedback.py`, file-shape review | The same broad owner still contains classification, retrieval shaping, integrity, and ledger writes at closeout | Keep integrity and persistence in one broad file and confirm acceptance fails because the concern split did not actually happen | A future session performs a cosmetic shuffle and claims the owner is modular because helper names improved |
| Semantic-trace work recreates a second trace or graph monolith or introduces a new evidence import cycle. | `evidence_semantic_trace.py`, new semantic-trace owners, architecture probe | `uv run pytest -q tests/unit/test_evidence_semantic_trace.py`, `python .../architecture_probe.py --format markdown --top 20`, `uv run docling-system-architecture-inspect` | A new or touched selected owner exceeds thresholds or the cycle count increases above `3` | Move provenance-edge expansion into a new oversized sibling or introduce a back-import from a provenance-export graph module and confirm the probe/closeout blocks it | Future Codex breaks one big file into two equally broad trace files and calls it closure |
| Audit-view reduction only peels off helpers while the main audit-bundle aggregation still mixes receipt, readiness, and bundle read assembly. | `evidence_audit_views.py`, new audit owners, audit surface tests | `uv run pytest -q tests/unit/test_evidence_audit_views.py`, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_audit_surfaces.py` | Release-readiness DB-gate persistence and large bundle aggregation still coexist in the same file after closeout | Leave `persist_technical_report_release_readiness_db_gate(...)` and `get_agent_task_audit_bundle(...)` in one owner and confirm acceptance fails | A future session keeps the audit owner large because the external read surface still works |
| The packet claims evidence-family closure on the stale four-file excerpt while other live `IC-65AF4A6D8B1E` files still exceed budget. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, this plan, handoff | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, `uv run docling-system-hygiene-check` | Handoff or case registry claims the broader owner family is retired without live proof that all case-owned files are within budget | Leave `evidence_manifest_traces.py` or `evidence_manifests.py` over budget while marking the whole case closed and confirm closeout review rejects it | A future session trusts the older excerpt and silently loses track of the remaining live blockers |
| Missing owner tests are treated as acceptable because the broader harness and technical-report integration suite is already green. | new unit suites, updated focused tests | `uv run pytest -q tests/unit/test_evidence_technical_report_exports.py tests/unit/test_evidence_claim_feedback.py tests/unit/test_evidence_semantic_trace.py tests/unit/test_evidence_audit_views.py` | Dedicated unit suites for claim feedback, semantic trace, and audit views do not exist by closeout | Add only integration assertions and confirm plan acceptance fails on missing owner tests | A future session relies on broad integration coverage and leaves the new owners without direct regression seams |

Accepted residual after closeout:

- If the selected four close under `600` but
  `evidence_manifest_traces.py`,
  `evidence_manifests.py`, or
  `evidence_claim_support_replay_alerts.py`
  still exceed the default budget on the fresh closeout baseline, the selected
  issue may be `resolved` while the broader `IC-65AF4A6D8B1E` case remains
  explicitly `reduced`.
- If the architecture-probe cycle count remains at the current baseline of `3`,
  that is accepted only when the selected work does not increase it and no new
  evidence cycle component is introduced.

## Milestone Sequence

Milestone 0 is mandatory and must run before any production code changes.

### Milestone 0 - Live Refresh And Scope Lock

Status: resolved locally through closeout commit `44bec70`
Outcome label: `reduced`

- Refreshed `git status -sb`, selected `wc -l`,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-improvement-case-summary`,
  `uv run docling-system-architecture-quality-report --summary`, and the
  architecture probe.
- Replaced the stale draft-time case-summary counts in this plan and kept the
  live selected-file measurements explicit at `884`, `837`, `834`, and `699`
  lines.
- Confirmed that the selected four files remain the right immediate target, but
  the broader `IC-65AF4A6D8B1E` case still also governs
  `app/services/evidence_manifest_traces.py`,
  `app/services/evidence_manifests.py`, and
  `app/services/evidence_claim_support_replay_alerts.py`, so broader
  case-retirement is not in scope for this packet.
- Refreshed `IC-65AF4A6D8B1E` to the 2026-05-15 selected-scope baseline and
  recorded that broader case retirement remains a routed follow-on.
- Added skeletal owner-test files
  `tests/unit/test_evidence_claim_feedback.py`,
  `tests/unit/test_evidence_semantic_trace.py`, and
  `tests/unit/test_evidence_audit_views.py`
  before any production code motion.
- Kept the Milestone 0 slice limited to routing, tests, and docs. No evidence
  production module changed in this milestone.

Acceptance:

- satisfied locally through closeout commit `44bec70`:
  fresh live measurements are recorded in the plan and handoff,
  the selected-scope versus broader-case-retirement distinction is explicit,
  owner-test seams exist before large code moves,
  and no production code changed outside routing, tests, and docs

### Milestone 1 - Technical Report Derivation And Lock Boundary

Status: drafted
Outcome label: `reduced`

- Extract release-binding lookup, audit-bundle or receipt lookup, provenance
  lock application, and contract-mismatch helpers out of
  `app/services/evidence_technical_report_exports.py`
  into focused technical-report export siblings.
- Keep derivation-package shaping and persistence behavior stable through the
  existing public import surface.
- Add focused unit coverage for provenance-lock and derivation-contract paths.

Acceptance:

- the selected file is materially smaller and no longer owns both contract
  mismatch checks and persistence entrypoints
- public callers remain stable through existing imports
- focused export tests cover both contract-mismatch and good-path lock assembly

### Milestone 2 - Technical Report Export Persistence Closeout

Status: drafted
Outcome label: `resolved`

- Extract export persistence, attachment helpers, and row-payload shaping into
  focused technical-report export lifecycle or payload owners.
- Reduce `app/services/evidence_technical_report_exports.py` to `<= 600`
  lines with a narrow stable owner seam or forwarding surface.
- Update focused unit coverage and relevant integration slices for technical
  report harness roundtrip and integrity behavior.

Acceptance:

- `app/services/evidence_technical_report_exports.py` is `<= 600` lines
- persistence, attachment, and payload concerns no longer cohabit with the
  derivation-lock machinery in the same file
- targeted unit and integration gates are green

### Milestone 3 - Claim Feedback Payload And Retrieval Context Boundary

Status: drafted
Outcome label: `reduced`

- Extract verdict classification, span or retrieval-context materialization,
  evidence-ref shaping, and desired-row payload construction into focused
  claim-feedback siblings.
- Add `tests/unit/test_evidence_claim_feedback.py` coverage for positive,
  missing, contradicted, and append-only input preparation paths.

Acceptance:

- `app/services/evidence_claim_feedback.py` no longer owns both retrieval
  context assembly and live ledger mutation setup
- the new owner test file covers payload-shaping and status-edge cases
- no spill occurs into `evidence_audit_views.py` or `semantic_governance.py`

### Milestone 4 - Claim Feedback Integrity And Ledger Closeout

Status: drafted
Outcome label: `resolved`

- Extract row-integrity reporting, integrity-summary aggregation, append-only
  live-link enforcement, and ledger persistence into focused claim-feedback
  integrity and lifecycle owners.
- Reduce `app/services/evidence_claim_feedback.py` to `<= 600` lines.
- Prove that existing ledger rows still reject payload drift and preserve
  append-only link semantics.

Acceptance:

- `app/services/evidence_claim_feedback.py` is `<= 600` lines
- integrity verification and ledger writes no longer coexist in the same broad
  file
- unit and integration coverage proves append-only and integrity-mismatch
  failures still hold

### Milestone 5 - Semantic Trace Integrity And Provenance Edge Boundary

Status: drafted
Outcome label: `resolved`

- Extract technical-report derivation integrity recomputation out of
  `app/services/evidence_semantic_trace.py`
  into a focused integrity owner.
- Extract source-record shaping and provenance-edge expansion into separate
  focused semantic-trace owners.
- Reduce `app/services/evidence_semantic_trace.py` to `<= 600` lines while
  keeping import contracts stable for audit views and other callers.

Acceptance:

- `app/services/evidence_semantic_trace.py` is `<= 600` lines
- no new evidence import cycle is introduced
- `tests/unit/test_evidence_semantic_trace.py` and the technical-report
  integration slices cover integrity and provenance-edge behavior

### Milestone 6 - Audit Views And Release Readiness Boundary

Status: drafted
Outcome label: `resolved`

- Extract release-readiness DB-gate persistence and related governance-event
  backfill out of `app/services/evidence_audit_views.py`
  into focused audit siblings.
- Extract the large audit-bundle aggregation body into a focused audit-bundle
  read owner.
- Reduce `app/services/evidence_audit_views.py` to `<= 600` lines.
- Add `tests/unit/test_evidence_audit_views.py` coverage and revalidate the
  audit-surface integration slice.

Acceptance:

- `app/services/evidence_audit_views.py` is `<= 600` lines
- release-readiness DB-gate persistence no longer cohabits with the main
  audit-bundle aggregation body
- audit surface unit and integration coverage is green

### Milestone 7 - Residual Evidence Owner Family Closeout

Status: drafted
Outcome label: `resolved` for the selected issue and `resolved` or `reduced`
for `IC-65AF4A6D8B1E` based on live proof

- Re-run the full selected verification stack plus the full DB-backed suite.
- Refresh `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md`
  to match the final measured file sizes and owner routing.
- If the broader owner case still includes
  `evidence_manifest_traces.py`,
  `evidence_manifests.py`, or
  `evidence_claim_support_replay_alerts.py`
  above budget, record `IC-65AF4A6D8B1E` as `reduced` and route the next
  packet explicitly. Do not claim full evidence-family retirement on stale
  scope.

Acceptance:

- all four selected files are `<= 600` lines on the closeout baseline
- dedicated unit suites exist and pass for technical-report exports, claim
  feedback, semantic trace, and audit views
- `app/services/evidence.py` and
  `app/services/evidence_provenance_exports.py`
  remain narrow compatibility seams
- broader case status is honest and fully synchronized across registry,
  hygiene, index, and handoff

## Required Implementation Artifacts

- focused technical-report export owner modules under
  `app/services/evidence_technical_report_*.py`
- focused claim-feedback owner modules under
  `app/services/evidence_claim_feedback_*.py`
- focused semantic-trace owner modules under
  `app/services/evidence_semantic_trace_*.py`
- focused audit owner modules under `app/services/evidence_audit_*.py`
- dedicated unit suites:
  `tests/unit/test_evidence_claim_feedback.py`,
  `tests/unit/test_evidence_semantic_trace.py`, and
  `tests/unit/test_evidence_audit_views.py`
- updated routing and hygiene artifacts for every touched or newly created
  owner module

## Required Documentation And Handoff Updates

- update this plan with live milestone status and measured end-state counts
- update `docs/SESSION_HANDOFF.md` with the active or closed packet, exact
  selected-file measurements, case status, and next routing
- update `docs/agentic_architecture_index.md` so future sessions route to this
  packet instead of re-reading the older evidence facade or provenance-export
  closeouts
- update `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` so
  selected-owner routing matches the final measured state
- if hotspot-prevention rules are introduced or tightened, update
  `config/hotspot_prevention.yaml` and the related tests in the same milestone

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/evidence.py app/services/evidence_technical_report_exports.py app/services/evidence_semantic_trace.py app/services/evidence_claim_feedback.py app/services/evidence_audit_views.py app/services/evidence_release_readiness.py app/services/evidence_technical_report_context.py app/services/evidence_provenance.py app/services/evidence_records.py app/services/evidence_search_closure.py app/services/semantic_governance.py app/hotspot_prevention_classifier.py tests/unit/test_evidence_technical_report_exports.py tests/unit/test_evidence_claim_feedback.py tests/unit/test_evidence_semantic_trace.py tests/unit/test_evidence_audit_views.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_evidence_technical_report_exports.py tests/unit/test_evidence_claim_feedback.py tests/unit/test_evidence_semantic_trace.py tests/unit/test_evidence_audit_views.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_technical_report_harness_integrity.py tests/integration/test_technical_report_harness_source_evidence.py tests/integration/test_technical_report_harness_audit_surfaces.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_retrieval_learning_ledger.py tests/integration/test_evidence_operator_runs_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- the four selected files all measure `<= 600` lines on the closeout baseline
- no new or touched evidence owner file exceeds `800` lines
- `app/services/evidence.py` remains a narrow compatibility facade and does not
  regain selected-family implementation bodies
- `app/services/evidence_provenance_exports.py` remains a narrow provenance
  seam and does not regain graph or export-lifecycle ownership
- dedicated unit suites exist for claim feedback, semantic trace, and audit
  views, and the technical-report export suite is expanded as needed
- all required verification gates pass without weakening, deleting, or loosening
  prior coverage
- the architecture-probe cycle count does not increase above `3`
- broader `IC-65AF4A6D8B1E` closure is claimed only if every live case-owned
  file is within budget on the refreshed closeout baseline; otherwise the case
  remains explicitly routed as `reduced`

## Stop Conditions

- Milestone 0 shows the selected excerpt is stale in a way that requires a
  broader packet to retire `IC-65AF4A6D8B1E`, and that broader packet cannot be
  absorbed cleanly into this sequence without losing milestone discipline.
- Any selected split would require an API, DB, or storage-contract change
  rather than an internal owner-boundary change.
- The only apparent way to reduce a selected owner is to push debt into
  `evidence_manifest_traces.py`,
  `evidence_manifests.py`, or
  `evidence_claim_support_replay_alerts.py`.
- Hotspot-prevention hardening would force
  `app/hotspot_prevention_classifier.py`
  beyond its current ratchet without same-milestone classifier reduction.
- Focused unit or integration coverage has to be weakened to get green.

## Local Commit Closeout Policy

- Close each milestone with one local atomic commit after verification passes.
- Stage only the touched milestone slice: implementation, tests, routing or
  hygiene files, generated artifacts, this plan, the architecture index, and
  the session handoff.
- Do not mix unrelated dirty worktree changes into a milestone commit.
- A verified but uncommitted milestone is ready-to-close, not complete.

## Residual Risks And Next Routing

- The live `IC-65AF4A6D8B1E` case is broader than the selected excerpt. Even if
  this packet resolves the selected four files, the broader case may still need
  a follow-on for
  `app/services/evidence_manifest_traces.py`,
  `app/services/evidence_manifests.py`, and
  `app/services/evidence_claim_support_replay_alerts.py`.
- The architecture-quality summary may continue to mention
  `app/services/evidence.py` because of public fan-in even after selected-owner
  closure. That is acceptable only if the file remains a demonstrably narrow
  compatibility seam and the selected owner modules themselves are within
  budget.
- The immediate next implementation slice is Milestone 1,
  `Technical Report Derivation And Lock Boundary`.
- If the broader case remains open after Milestone 7, the next packet should
  start from the largest live blocker at the fresh closeout baseline,
  currently `app/services/evidence_manifest_traces.py`, not from the already
  closed evidence facade or provenance-export seams.
