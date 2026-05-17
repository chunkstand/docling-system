# Semantic Residual Owner Family Milestone Plan

Date: 2026-05-15 local / 2026-05-15 UTC
Status: superseded historical draft from 2026-05-15. Do not execute this file
as the active packet. The live lifecycle/read follow-on now routes through
`docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`, and the later
app large owner modules closeout already reduced
`app/services/semantic_governance.py` to `39` lines while routing the remaining
graph or generation semantic residuals under `IC-6F4E2B5A91C3` and
`IC-C8D41A2F77BE`
Owner context: residual semantic owner-family debt after the closeout that
reduced `app/services/semantics.py` to a 54-line compatibility facade.
This packet is intentionally narrower than
`docs/app_large_owner_modules_resolution_milestone_plan.md`. This historical
draft targeted only:
`app/services/semantic_pass_lifecycle.py`,
`app/services/semantic_pass_reads.py`, and
`app/services/semantic_governance.py`.
Do not execute this draft unchanged. If any part of this historical packet is
revived, refresh the baseline first and re-scope it around the live lifecycle
and read residuals rather than the now-closed semantic-governance root.

## Purpose

Resolve the remaining dense app-code debt inside the extracted semantic owner
modules.

The scoped problem is not facade ambiguity anymore. `app/services/semantics.py`
is already narrow. The remaining debt is that the three extracted semantic
owners still combine several distinct concern families, two of them are
oversized without dedicated improvement-case ownership, and all three still sit
inside the residual semantic service cycle reported by the architecture probe.

This plan resolves that scoped residual by:

- refreshing the live post-closeout baseline before code moves
- creating explicit owner-case routing for the two oversized extracted owners
  that still lack it
- reducing the three selected files below the `600`-line hygiene target where
  feasible and below the `800`-line large-file threshold without exception
- preserving the current semantics route, worker, backfill, and capability
  contracts
- preventing future sessions from dumping new semantic lifecycle, read, or
  governance logic back into the same residual owners

## Historical Evidence

Historical pre-app-large-owner evidence captured from the local checkout on
2026-05-15 local / 2026-05-15 UTC before this draft became stale:

```text
git status -sb
  ## main...origin/main [ahead 6]
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
  ?? .tmp/
  ?? docs/app_large_owner_modules_resolution_milestone_plan.md

wc -l app/services/semantic_pass_lifecycle.py app/services/semantic_pass_reads.py app/services/semantic_governance.py
   961 app/services/semantic_pass_lifecycle.py
   762 app/services/semantic_pass_reads.py
  1157 app/services/semantic_governance.py

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt includes:
    app/services/semantic_governance.py = 1157 lines under IC-81C531769EB3

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown
  remaining cycle components=3
  cycle component includes:
    app.services.semantic_pass_lifecycle
    app.services.semantic_pass_reads
    app.services.semantic_registry_preview
    app.services.semantics
```

Repo-current structural evidence:

- `docs/semantics_service_boundary_milestone_plan.md` is already resolved
  locally and explicitly left this residual open because
  `semantic_pass_lifecycle.py` and `semantic_pass_reads.py` still exceed the
  default `600`-line budget.
- `app/services/semantic_pass_lifecycle.py` currently mixes:
  review-overlay loading, registry-definition syncing, assertion replacement,
  semantic artifact persistence, pass-row preparation, semantic pass
  execution, projection refresh, and review mutation handlers.
- `app/services/semantic_pass_reads.py` currently mixes:
  source materialization, assertion and binding record shaping, summary and
  continuity projection, and the public active-pass row/detail/continuity
  entrypoints.
- `app/services/semantic_governance.py` currently mixes:
  governance-event recording across several domains, active semantic basis
  context assembly, release-governance context shaping, event payload and
  integrity helpers, and audit-chain expansion/reporting.
- `config/improvement_cases.yaml` currently binds only
  `app/services/semantic_governance.py` through `IC-81C531769EB3`.
  `semantic_pass_lifecycle.py` and `semantic_pass_reads.py` do not yet have
  dedicated case entries.
- `config/hygiene_policy.yaml` already tracks all three files as inherited
  budget debt, so routing and line-budget enforcement are partly present but
  still incomplete for the extracted lifecycle and read owners.
- The selected files sit on contract-sensitive semantics behavior already
  covered by focused unit and integration slices in the prior semantics
  closeout: pass lifecycle, active-pass reads, documents API semantics,
  semantic orchestration and backfill, semantic generation, semantic graph, and
  semantic governance ledger flows.

## Goal

Resolve the residual semantic owner-family debt so that:

- `app/services/semantic_pass_lifecycle.py`,
  `app/services/semantic_pass_reads.py`, and
  `app/services/semantic_governance.py`
  all measure `<= 600` lines on a fresh closeout baseline
- if any selected owner cannot responsibly close under `600` in its milestone,
  it must still close at `<= 800` with explicit same-milestone routed residual
  ownership and a `reduced` outcome label
- `semantic_pass_lifecycle.py` and `semantic_pass_reads.py` gain durable
  improvement-case entries before code motion begins
- current semantics route, backfill, worker, and capability imports remain
  behavior-compatible
- the selected owner work does not increase the current architecture-probe
  cycle count above the live baseline of `3`

## Non-Goals

- No rewrite of `app/services/semantics.py`; it remains the compatibility
  facade.
- No broad semantic cleanup of `semantic_graph.py`,
  `semantic_candidates.py`,
  `semantic_generation.py`,
  `semantic_orchestration.py`, or
  `semantic_registry.py`.
- No repo-wide cycle-elimination packet.
- No test-monolith cleanup.
- No weakening of unit, integration, route, or review-mutation coverage.

## Scope

In scope:

- Milestone 0 live refresh and owner-case bootstrap for the three selected
  residual owners
- lifecycle-family decomposition inside `semantic_pass_lifecycle.py`
- read-family decomposition inside `semantic_pass_reads.py`
- governance-family decomposition inside `semantic_governance.py`
- focused routing, hygiene, and targeted hotspot-prevention updates required by
  the selected owners
- docs and handoff alignment for this new residual-owner packet

Out of scope:

- changes to semantic graph, generation, candidate extraction, or registry
  preview owners except where those modules must remain stable callers
- general search, documents, evaluations, or run-processing cycle cleanup
- threshold increases above `600` or `800`

## Owner Surfaces

- lifecycle family:
  `app/services/semantic_pass_lifecycle.py`,
  new focused lifecycle owners under `app/services/semantic_pass_*.py`,
  `app/services/semantics.py`,
  `tests/unit/test_semantic_pass_lifecycle.py`
- read family:
  `app/services/semantic_pass_reads.py`,
  new focused read owners under `app/services/semantic_pass_*.py`,
  `app/services/semantics.py`,
  `app/api/routers/semantics.py`,
  `tests/unit/test_semantic_pass_reads.py`,
  `tests/unit/test_documents_api_semantics.py`
- governance family:
  `app/services/semantic_governance.py`,
  new focused governance owners under `app/services/semantic_governance_*.py`,
  `tests/unit/test_semantic_governance.py`,
  `tests/integration/test_semantic_governance_ledger.py`
- adjacent compatibility callers that must remain stable:
  `app/services/semantic_backfill.py`,
  `app/services/agent_task_verifications.py`,
  `app/services/capabilities/semantics.py`,
  `app/services/runs.py`,
  `app/api/routers/semantics.py`,
  `tests/unit/test_semantic_orchestration.py`,
  `tests/unit/test_semantic_backfill_api.py`,
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
  `docs/agentic_architecture_index.md`

## Placement Rules

- Keep `app/services/semantics.py` as the public semantics compatibility seam.
  Do not move implementation back into it.
- New lifecycle, read, or governance code belongs in focused sibling modules
  under `app/services/`, not in already-large adjacent owners such as
  `semantic_graph.py`,
  `semantic_candidates.py`,
  `semantic_generation.py`,
  `semantic_orchestration.py`, or
  `semantic_registry.py`.
- Preserve public entrypoints already imported by routes, workers, backfill,
  and capabilities. Narrowing a selected file into a forwarding facade is
  allowed only when existing callers remain stable.
- Any new owner module above `600` lines must receive same-milestone owner-case
  routing and a hygiene ratchet. No new or touched file may exceed `800` lines
  at milestone closeout.
- Do not grow `app/hotspot_prevention_classifier.py` by default. Add or adjust
  classifier rules only when a real blocked-regrowth seam is introduced and the
  same milestone proves the classifier itself does not become the new sink.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Lifecycle code is reduced by pushing logic into `runs.py`, `semantic_backfill.py`, or `semantics.py` instead of splitting the owner cleanly. | `semantic_pass_lifecycle.py`, adjacent semantic callers, staged diff | `uv run docling-system-hygiene-check`, staged `wc -l`, focused lifecycle tests | Any touched adjacent caller grows with moved lifecycle implementation or the lifecycle owner remains above its routed ceiling without explicit residual routing | Temporarily move projection-refresh helpers into `runs.py` or the facade and confirm closeout review rejects the slice | A future session sees runtime-adjacent helpers and treats `runs.py` as the easiest landing zone |
| Read-side work only renames helpers without separating source materialization from active-pass projections. | `semantic_pass_reads.py`, new read owners, read tests | `uv run pytest -q tests/unit/test_semantic_pass_reads.py tests/unit/test_documents_api_semantics.py`, file-shape review | Public entrypoints stay in the same broad owner while the internal concern families remain cohabiting | Leave continuity and detail materialization together in the same file and confirm milestone acceptance fails | Future Codex performs a cosmetic shuffle and claims the file is modular because the names changed |
| Governance work breaks ledger integrity or hides residual complexity in a second oversized governance sibling. | `semantic_governance.py`, new governance owners, governance tests, hygiene policy | `uv run pytest -q tests/unit/test_semantic_governance.py`, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_semantic_governance_ledger.py`, `uv run docling-system-hygiene-check` | Governance event recording or audit-chain behavior changes unexpectedly, or a new governance file exceeds thresholds without routing | Temporarily move chain-integrity expansion into a new `semantic_governance_audit.py` above `800` lines and confirm hygiene/closeout rejects it | Future Codex splits event writers but recreates the same oversized owner in a new filename |
| The residual-owner plan lands code changes without explicit improvement-case routing for lifecycle and reads. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, this plan, handoff | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary` | `semantic_pass_lifecycle.py` or `semantic_pass_reads.py` is touched without a durable case entry | Create a temporary routed slice with changed lifecycle code but no case entry and confirm validation or closeout review blocks it | Future Codex treats extracted owner files as “already owned” because they came from a closed facade plan |
| Residual-owner regrowth is blocked by adding more classifier branches than the classifier can safely hold. | `app/hotspot_prevention_classifier.py`, hotspot policy, hotspot tests | `uv run docling-system-hygiene-check`, `uv run pytest -q tests/unit/test_hotspot_prevention.py`, staged `wc -l` | The classifier grows beyond its current `999`-line ceiling without same-milestone extraction or reduction elsewhere | Add a second large semantic branch directly into the classifier and confirm closeout rejects it | Future Codex keeps turning every residual owner into more classifier prose instead of smaller owner modules |

Accepted residual after closeout:

- If one selected owner closes between `601` and `800` lines, that is accepted
  only with explicit same-milestone routed residual ownership, hygiene ratchet
  coverage, and an outcome label of `reduced`.
- If the repo-wide cycle count remains at the current baseline of `3`, that is
  accepted only when the selected owners close without increasing the cycle
  count and the remaining cycle cleanup is explicitly routed as separate work.

## Milestone Sequence

Milestone 0 is mandatory and must run before any production code changes.

### Milestone 0 - Live Refresh And Owner-Case Bootstrap

Status: drafted
Outcome label: `reduced`

- Refresh `git status -sb`, selected `wc -l`, `uv run docling-system-hygiene-check`,
  `uv run docling-system-improvement-case-summary`,
  `uv run docling-system-architecture-quality-report --summary`, and the
  architecture probe.
- Replace every draft-time count in this plan if live measurements changed.
- Create dedicated improvement cases for
  `app/services/semantic_pass_lifecycle.py` and
  `app/services/semantic_pass_reads.py`.
- Refresh `IC-81C531769EB3` for `app/services/semantic_governance.py` with the
  current baseline and residual-family intent.
- Refresh or add hygiene-owner entries for any selected or newly created owner
  module that will participate in later milestones.

Acceptance:

- all three selected owners have explicit durable routing before code moves
- this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` reflect the live baseline
- no production code changed outside routing and docs

### Milestone 1 - Semantic Pass Lifecycle Execution And Projection Boundary

Status: drafted
Outcome label: `reduced`

- Split lifecycle execution and persistence from review-mutation and projection
  refresh ownership inside `semantic_pass_lifecycle.py`.
- Preserve public lifecycle entrypoints used by `app/services/semantics.py` and
  current callers.

Acceptance:

- `app/services/semantic_pass_lifecycle.py` is materially reduced from the
  Milestone 0 baseline
- no touched adjacent semantic owner absorbs lifecycle implementation
- `tests/unit/test_semantic_pass_lifecycle.py` passes
- if the owner remains above `600`, the residual is explicitly routed to
  Milestone 2

### Milestone 2 - Semantic Pass Lifecycle Review And Artifact Closeout

Status: drafted
Outcome label: `resolved`

- Extract any remaining artifact payload, review-mutation, and projection-owner
  logic needed to bring `semantic_pass_lifecycle.py` within the final budget.
- Preserve current review endpoints and artifact expectations.

Acceptance:

- `app/services/semantic_pass_lifecycle.py` measures `<= 600` lines
- no new lifecycle-family owner exceeds `800` lines
- focused lifecycle and route semantics coverage stays green

### Milestone 3 - Semantic Pass Reads Materialization Boundary

Status: drafted
Outcome label: `reduced`

- Split source-materialization and record-shaping ownership from row/detail and
  continuity response assembly inside `semantic_pass_reads.py`.
- Preserve the existing public active-pass row/detail/continuity entrypoints.

Acceptance:

- `app/services/semantic_pass_reads.py` is materially reduced from the
  Milestone 0 baseline
- `tests/unit/test_semantic_pass_reads.py` and
  `tests/unit/test_documents_api_semantics.py` pass
- if the owner remains above `600`, the residual is explicitly routed to
  Milestone 4

### Milestone 4 - Semantic Pass Reads Closeout

Status: drafted
Outcome label: `resolved`

- Extract any remaining continuity, summary, or detail-assembly families
  needed to close `semantic_pass_reads.py` within budget.
- Preserve route and backfill compatibility through the semantics facade.

Acceptance:

- `app/services/semantic_pass_reads.py` measures `<= 600` lines
- no new read-family owner exceeds `800` lines
- focused reads, route, and backfill coverage remains green

### Milestone 5 - Semantic Governance Event Recording Boundary

Status: drafted
Outcome label: `reduced`

- Split governance-event recording families from active-basis context assembly
  and audit-chain projection logic.
- Preserve the current public governance entrypoints used by semantic and
  release-governance callers.

Acceptance:

- `app/services/semantic_governance.py` is materially reduced from the
  Milestone 0 baseline
- `tests/unit/test_semantic_governance.py` passes
- if the owner remains above `600`, the residual is explicitly routed to
  Milestone 6

### Milestone 6 - Semantic Governance Audit And Integrity Closeout

Status: drafted
Outcome label: `resolved`

- Extract remaining active-basis, integrity, and audit-chain families needed to
  close `semantic_governance.py` within budget.
- Refresh `IC-81C531769EB3` to the final post-closeout state.

Acceptance:

- `app/services/semantic_governance.py` measures `<= 600` lines
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_semantic_governance_ledger.py` passes
- no new governance-family owner exceeds `800` lines

### Milestone 7 - Residual Semantic Owner Family Closeout

Status: drafted
Outcome label: `resolved`

- Re-run the full selected verification stack and refresh line-count, routing,
  hygiene, and architecture evidence.
- Update this plan with actual closeout status, outcome labels, and any
  accepted routed residuals.
- Update the handoff and architecture index with the active next routing and
  commit hashes.

Acceptance:

- the three selected owners all measure `<= 600` lines on a fresh baseline
- all three have durable improvement-case routing and hygiene-owner coverage
- the architecture probe does not report more than the Milestone 0 cycle
  baseline of `3`
- the final full DB-backed integration suite passes

## Required Implementation Artifacts

- focused new lifecycle, read, and governance owner modules under
  `app/services/`
- improvement-case entries for `semantic_pass_lifecycle.py` and
  `semantic_pass_reads.py`
- refreshed `IC-81C531769EB3` measurement and closeout notes
- updated hygiene ratchets for the selected owners and any accepted new
  `601-800` owner modules
- targeted hotspot-prevention updates only where a true blocked-regrowth seam
  is introduced

## Required Documentation And Handoff Updates

- update this plan with actual milestone status, evidence, and residual routing
- update `docs/SESSION_HANDOFF.md` with the active residual semantic-owner
  milestone, verification commands, commit hash, and next routing
- update `docs/agentic_architecture_index.md` so the current drafted brief
  points to this new residual-owner packet

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/semantics.py app/services/semantic_pass_lifecycle.py app/services/semantic_pass_reads.py app/services/semantic_registry_preview.py app/services/semantic_governance.py app/services/semantic_backfill.py app/services/semantic_ontology.py app/services/agent_task_verifications.py app/services/capabilities/semantics.py app/api/routers/semantics.py app/hotspot_prevention_classifier.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_governance.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_governance.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-architecture-inspect`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown`

## Acceptance Criteria

- `app/services/semantic_pass_lifecycle.py`,
  `app/services/semantic_pass_reads.py`, and
  `app/services/semantic_governance.py`
  each measure `<= 600` lines on a fresh closeout baseline
- `semantic_pass_lifecycle.py` and `semantic_pass_reads.py` are explicitly
  routed in `config/improvement_cases.yaml`
- `IC-81C531769EB3` is refreshed to the final `semantic_governance.py`
  measurement and residual state
- no selected-family implementation debt is hidden in
  `semantics.py`,
  `runs.py`,
  `semantic_backfill.py`,
  `semantic_orchestration.py`,
  `semantic_registry.py`,
  `semantic_graph.py`,
  `semantic_candidates.py`, or
  `semantic_generation.py`
- no new owner module in the selected families exceeds `800` lines
- any newly created owner module between `601` and `800` lines is explicitly
  routed and ratcheted in the same milestone
- the focused unit and integration slices pass without weakened coverage
- the final full DB-backed integration suite passes

## Stop Conditions

- Milestone 0 shows the selected residual-owner set is no longer the live next
  semantic debt surface
- reducing a selected owner would require pushing implementation into another
  already-large semantic sibling
- the only available prevention move is to keep growing
  `app/hotspot_prevention_classifier.py` beyond its current ceiling without a
  same-milestone extraction
- route, backfill, or governance verification fails because of unrelated system
  breakage that prevents trustworthy milestone proof
- user-owned edits appear in the same selected files and cannot be cleanly
  separated from the milestone slice

## Local Commit Closeout Policy

- Close each milestone with a local atomic commit after verification passes.
- Stage only the verified milestone slice.
- Leave unrelated dirty or untracked files, including `.tmp/` and the unrelated
  drafted docs already present in the worktree, alone unless the user
  explicitly asks to clean or commit them.
- Include code, tests, config updates, docs, and handoff changes for that
  milestone in the same commit.
- Record the commit hash in `docs/SESSION_HANDOFF.md` and this plan.
- Treat a verified but uncommitted milestone as ready-to-close, not complete.

## Residual Risks And Next Routing

- This plan resolves the extracted residual semantic-owner family only. Broader
  semantic large-file debt such as `semantic_graph.py`,
  `semantic_candidates.py`, and `semantic_generation.py` remains outside this
  packet unless the user later selects it explicitly.
- If the selected owners close without reducing the repo-wide cycle count below
  `3`, route cycle-only cleanup through a fresh standalone packet instead of
  broadening this one after the fact.
- After this packet closes, the next semantic or app-side hotspot should be
  chosen from fresh live evidence rather than by reusing the older broader
  owner lists unchanged.
