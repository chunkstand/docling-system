# Evidence Manifest Trace Graph Boundary Milestone Plan

Date: 2026-05-15 local / 2026-05-15 UTC
Status: resolved locally in the current checkout as an uncommitted standalone
follow-on after `docs/evidence_residual_owner_family_milestone_plan.md`;
Milestones 0 through 2 are resolved locally, the scoped manifest-trace owner
now closes at `203` lines with focused siblings at `204`, `461`, and `244`,
and the later manifest-owner follow-on now reduces
`app/services/evidence_manifests.py` to `370` lines with payload assembly in
`app/services/evidence_manifest_payloads.py` at `384` lines. The later
replay-alert follow-on now reduces
`app/services/evidence_claim_support_replay_alerts.py` to `407` lines with a
new `app/services/evidence_claim_support_replay_alert_corpus.py` owner at
`128`, leaving the broader owner-family case locally retirement-ready pending
commit
Owner context: targeted follow-on for the largest remaining live blocker under
`IC-65AF4A6D8B1E` after the selected evidence residual owner packet closed
locally in the current checkout. The selected four seams are now closed at
`45`, `48`, `36`, and `19` lines for
`app/services/evidence_technical_report_exports.py`,
`app/services/evidence_claim_feedback.py`,
`app/services/evidence_semantic_trace.py`, and
`app/services/evidence_audit_views.py`; Milestone 1 of this follow-on now
reduces `app/services/evidence_manifest_traces.py` to a `203`-line facade and
adds focused siblings at `204`, `461`, and `244` lines for
`app/services/evidence_manifest_trace_graph.py`,
`app/services/evidence_manifest_trace_assembly.py`, and
`app/services/evidence_manifest_trace_replay.py`. The broader evidence
owner-family case was later reduced only by
`app/services/evidence_claim_support_replay_alerts.py` after the manifest-owner
follow-on reduced `app/services/evidence_manifests.py` to `370` lines with
payload assembly in `app/services/evidence_manifest_payloads.py` at `384`. The
later replay-alert follow-on now resolves that final evidence-owner blocker
locally.

## Purpose

Reduce the largest remaining live evidence owner without reopening the already
closed selected evidence seams or silently shifting debt into adjacent
evidence owners.

The immediate scoped problem was `app/services/evidence_manifest_traces.py`,
which mixed graph-node and edge canonicalization, manifest or report or
context-pack trace assembly, claim-support replay lineage expansion, DB
persistence, and integrity recomputation in one `980`-line owner. Milestone 1
now isolates graph canonicalization, mixed trace assembly, and replay lineage
behind focused manifest-trace siblings while preserving the public manifest
surface in `app/services/evidence_manifests.py`.

## Current Evidence

Milestone 0 baseline refreshed from the local checkout on 2026-05-15 local /
2026-05-15 UTC after the selected evidence residual packet closed locally:

```text
wc -l app/services/evidence_manifest_traces.py app/services/evidence_manifests.py app/services/evidence_claim_support_replay_alerts.py
   980 app/services/evidence_manifest_traces.py
   725 app/services/evidence_manifests.py
   646 app/services/evidence_claim_support_replay_alerts.py

python - <<'PY'
from pathlib import Path
path = Path("app/services/evidence_manifest_traces.py")
for start, end in [(250, 420), (420, 823), (823, 919)]:
    print(f"{start}-{end}: {end-start} lines")
PY
  250-420: 170 lines
  420-823: 403 lines
  823-919: 96 lines

python - <<'PY'
from pathlib import Path
path = Path("app/services/evidence_manifest_traces.py")
for i, line in enumerate(path.read_text().splitlines(), 1):
    if line.startswith("def ") or line.startswith("async def "):
        print(f"{i}: {line}")
PY
  250: def build_evidence_trace_graph_specs(
  823: def persist_evidence_trace_graph(
  885: def evidence_trace_rows(
  906: def evidence_trace_integrity_payload(

rg -n "from app.services.evidence_manifest_traces" app/services/evidence_manifests.py
  app/services/evidence_manifests.py imports
  build_evidence_trace_graph_specs,
  persist_evidence_trace_graph,
  evidence_trace_rows, and
  evidence_trace_integrity_payload

rg -n "persist_evidence_trace_graph|build_evidence_trace_graph_specs|evidence_trace_integrity_payload|trace_sha256" tests
  trace-graph behavior is covered today primarily through
  tests/integration/test_technical_report_harness_integrity.py,
  tests/integration/test_technical_report_harness_audit_surfaces.py,
  tests/integration/test_multivector_retrieval.py,
  tests/unit/test_evidence_facade_contract.py, and
  tests/unit/test_evidence_provenance_export_graph_core.py;
  the current checkout now also includes
  tests/unit/test_evidence_manifest_traces.py as the dedicated owner seam
```

Milestone 0 owner-suite evidence from the current checkout:

```text
uv run docling-system-hygiene-check
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  case_count=46
  status_counts.open=30
  measured_case_count=41

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycle components: 3
  code files above 800 lines: 31

uv run ruff check tests/unit/test_evidence_manifest_traces.py tests/unit/test_evidence_facade_contract.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_technical_reports.py
  All checks passed!

uv run pytest -q tests/unit/test_evidence_manifest_traces.py tests/unit/test_evidence_facade_contract.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_technical_reports.py
  20 passed
```

Current structural evidence:

- `build_evidence_trace_graph_specs(...)` dominates the module body and mixes
  document, semantic-trace, report-trace, context-pack, replay-lineage, and
  provenance-edge assembly in one function family.
- `persist_evidence_trace_graph(...)`, `evidence_trace_rows(...)`, and
  `evidence_trace_integrity_payload(...)` are already separate public seams,
  but they still live beside the large mixed trace-spec builder.
- `app/services/evidence_manifests.py` depends directly on the manifest-trace
  public surface, so the next split must preserve those import contracts while
  keeping the manifest owner from absorbing more trace implementation bodies.
- The broader owner case must remain honest if
  `app/services/evidence_manifests.py` or
  `app/services/evidence_claim_support_replay_alerts.py`
  stay above budget after this packet closes.

Milestone 1 local closeout baseline in the current checkout:

```text
wc -l app/services/evidence_manifest_traces.py app/services/evidence_manifest_trace_graph.py app/services/evidence_manifest_trace_assembly.py app/services/evidence_manifest_trace_replay.py app/services/evidence_manifests.py app/services/evidence_claim_support_replay_alerts.py
   203 app/services/evidence_manifest_traces.py
   204 app/services/evidence_manifest_trace_graph.py
   461 app/services/evidence_manifest_trace_assembly.py
   244 app/services/evidence_manifest_trace_replay.py
   725 app/services/evidence_manifests.py
   646 app/services/evidence_claim_support_replay_alerts.py

uv run pytest -q tests/unit/test_evidence_manifest_traces.py tests/unit/test_evidence_facade_contract.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_technical_reports.py
  23 passed

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_integrity.py tests/integration/test_technical_report_harness_audit_surfaces.py tests/integration/test_multivector_retrieval.py
  5 passed

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycle components: 3
  code files above 800 lines: 30
```

Additional closeout evidence:

- `app/services/evidence_manifest_traces.py` now exposes only the four public
  facade seams and no private helpers.
- graph canonicalization now lives in
  `app/services/evidence_manifest_trace_graph.py`.
- manifest or report or context-pack trace assembly now lives in
  `app/services/evidence_manifest_trace_assembly.py`.
- replay-lineage expansion now lives in
  `app/services/evidence_manifest_trace_replay.py`.
- `tests/unit/test_evidence_manifest_traces.py` now adds direct owner checks
  for placeholder replacement, deduped edges, and the facade size ratchet.

## Goal

Resolve the `app/services/evidence_manifest_traces.py` owner boundary so that:

- `app/services/evidence_manifest_traces.py` measures `<= 600` lines on the
  closeout baseline
- graph canonicalization and assembly are split along real owner seams instead
  of a cosmetic helper shuffle
- `app/services/evidence_manifests.py` keeps its current public behavior and
  does not absorb moved trace implementation bodies
- a dedicated owner suite exists for manifest-trace behavior before the packet
  closes
- the broader `IC-65AF4A6D8B1E` case remains explicitly `reduced` unless every
  remaining case-owned evidence file is within budget on the fresh closeout
  baseline

## Non-Goals

- No reopening of the already-closed selected evidence seams in
  `evidence_technical_report_exports.py`,
  `evidence_claim_feedback.py`,
  `evidence_semantic_trace.py`, or
  `evidence_audit_views.py`.
- No API, CLI, DB schema, migration, or storage-contract redesign.
- No silent debt shift into `app/services/evidence_manifests.py` or
  `app/services/evidence_claim_support_replay_alerts.py`.
- No provenance-export graph rewrite of
  `app/services/evidence_provenance_export_graph_core.py` or
  `app/services/evidence_provenance_export_graph_report.py`.
- No weakened trace, manifest, audit-surface, or retrieval integration
  coverage.

## Scope

In scope:

- live baseline refresh for the manifest-trace family
- dedicated owner-suite creation for manifest-trace behavior
- trace-graph spec decomposition within
  `app/services/evidence_manifest_traces.py`
- trace persistence and integrity boundary cleanup where needed
- routing, hygiene, improvement-case, index, and handoff updates needed for
  the manifest-trace closeout

Out of scope unless Milestone 0 explicitly widens the packet:

- `app/services/evidence_manifests.py` as a full owner-family retirement
- `app/services/evidence_claim_support_replay_alerts.py`
- broader claim-support replay product changes
- new technical-report evidence features

## Owner Surfaces

- primary owner:
  `app/services/evidence_manifest_traces.py`
- likely focused siblings under this packet:
  `app/services/evidence_manifest_trace_*.py`
- adjacent callers and contracts:
  `app/services/evidence_manifests.py`,
  `app/services/evidence.py`,
  `tests/unit/test_evidence_facade_contract.py`,
  `tests/unit/test_evidence_provenance_export_graph_core.py`,
  `tests/unit/test_technical_reports.py`,
  `tests/integration/test_technical_report_harness_integrity.py`,
  `tests/integration/test_technical_report_harness_audit_surfaces.py`,
  `tests/integration/test_multivector_retrieval.py`
- routing and prevention:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  this plan

## Placement Rules

- Keep `app/services/evidence_manifests.py` as the manifest-oriented caller and
  public surface. Do not move more trace-building logic into it just because it
  already imports the trace functions.
- New trace-graph canonicalization or assembly owners belong under focused
  `app/services/evidence_manifest_trace_*.py` siblings, not in
  `app/services/evidence_provenance_export_graph_core.py`,
  `app/services/evidence_semantic_trace.py`, or
  `app/services/evidence_claim_support_replay_alerts.py`.
- If replay-lineage expansion needs its own owner, keep it in a manifest-trace
  sibling under this packet rather than re-expanding the replay-alert owner.
- Any new owner module above `600` lines must receive same-milestone routing
  and a hygiene ratchet. No new or touched file may exceed `800` lines at
  milestone closeout.
- Add the dedicated owner suite as
  `tests/unit/test_evidence_manifest_traces.py`; do not continue expanding only
  the broader integration harnesses.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The file shrinks only because trace assembly is dumped into `evidence_manifests.py` or `evidence_claim_support_replay_alerts.py`. | `app/services/evidence_manifest_traces.py`, `app/services/evidence_manifests.py`, `app/services/evidence_claim_support_replay_alerts.py` | `uv run docling-system-hygiene-check`, staged `wc -l` review, focused manifest-trace unit suite | Any adjacent evidence owner grows by absorbing moved trace bodies or a touched file rises above its live ratchet without explicit routing | Intentionally move one trace-builder branch into `evidence_manifests.py` and confirm closeout review rejects it | A future session sees the direct import edge and treats the manifest owner as the easiest overflow bucket |
| The split is cosmetic and leaves one oversized mixed trace-builder owner behind renamed helpers. | `app/services/evidence_manifest_traces.py`, new trace siblings, new unit suite | `uv run pytest -q tests/unit/test_evidence_manifest_traces.py`, file-shape review | `build_evidence_trace_graph_specs(...)` still owns graph canonicalization, replay lineage, and provenance-edge expansion in one broad body at closeout | Keep the large builder intact and add only wrapper helpers; confirm the owner review blocks acceptance | A future session declares success because more helper names exist while the mixed owner remains effectively unchanged |
| Trace persistence or integrity recomputation breaks the manifest public surface or the audit and retrieval integrations. | `app/services/evidence_manifests.py`, trace persistence or integrity sibling owners, integration harnesses | `uv run pytest -q tests/unit/test_evidence_facade_contract.py tests/unit/test_evidence_manifest_traces.py tests/unit/test_technical_reports.py`, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_integrity.py tests/integration/test_technical_report_harness_audit_surfaces.py tests/integration/test_multivector_retrieval.py` | Caller imports break, trace hashes drift unexpectedly, or persisted and recomputed integrity no longer agree | Remove one manifest-trace export or perturb trace hash assembly and confirm the facade or integration gates fail | A future session rewires the owner split but forgets that retrieval and audit surfaces consume the persisted trace graph |
| The packet claims broader evidence-family retirement while `evidence_manifests.py` or `evidence_claim_support_replay_alerts.py` still exceed budget. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, this plan, handoff, index | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, `uv run docling-system-hygiene-check` | Registry or docs mark `IC-65AF4A6D8B1E` closed without live proof that every case-owned file is within budget | Leave `evidence_manifests.py` at `725` or replay alerts at `646` while claiming the whole case is resolved and confirm closeout review rejects it | A future session closes the owner case based on the manifest-trace split alone and loses track of the next blockers |
| The split introduces a new evidence import-cycle component by moving trace helpers into provenance or claim-support graph owners. | manifest-trace siblings, architecture docs, architecture probe | `uv run docling-system-architecture-inspect`, `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20` | The live Python cycle count increases above `3` or a new evidence-specific cycle appears | Add a back-import into a provenance-export or replay-alert owner and confirm the probe or inspection gate catches it | A future session chases "shared graph code" into a new cyclic utility knot |

Accepted residual after closeout:

- If `app/services/evidence_manifest_traces.py` closes under budget while
  `app/services/evidence_manifests.py` or
  `app/services/evidence_claim_support_replay_alerts.py`
  still exceed the default `600`-line budget, this packet is `resolved` for
  the manifest-trace owner and the broader `IC-65AF4A6D8B1E` case remains
  explicitly `reduced`.

## Milestone Sequence

Milestone 0 is mandatory and must run before any production code moves.

### Milestone 0 - Live Refresh And Owner-Test Seam

Status: resolved locally in the current checkout
Outcome label: `reduced`

- Refresh `git status -sb`, `wc -l` for the three remaining evidence owners,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-improvement-case-summary`, and the architecture probe.
- Add `tests/unit/test_evidence_manifest_traces.py` before broad code motion.
- Lock the follow-on scope to `app/services/evidence_manifest_traces.py` while
  keeping `evidence_manifests.py` and replay alerts as explicit adjacent
  blockers rather than silent spill targets.
- Milestone 0 closeout in the current checkout adds
  `tests/unit/test_evidence_manifest_traces.py` with focused owner coverage for
  placeholder-versus-materialized node preservation, replay-fixture lineage
  edges, complete trace-integrity recomputation, and hash-mismatch or
  recomputation-error reporting while leaving production evidence behavior
  unchanged.

Acceptance:

- live baseline and routed adjacency are recorded in this plan and the handoff
- the dedicated manifest-trace owner suite exists before large code motion
- no production code changes outside routing, tests, and docs land in this
  milestone

### Milestone 1 - Trace Graph Assembly Boundary

Status: resolved locally in the current checkout
Outcome label: `resolved`

- Extract graph canonicalization, manifest or report or context-pack trace
  assembly, and replay-lineage expansion into focused
  `app/services/evidence_manifest_trace_*.py` siblings.
- Reduce `build_evidence_trace_graph_specs(...)` to orchestration and contract
  forwarding only.
- Expand the new owner suite to cover node or edge dedupe, placeholder-node
  creation, replay-fixture lineage edges, and provenance-edge assembly.

Milestone 1 local outcome:

- `app/services/evidence_manifest_traces.py` now measures `203` lines.
- graph canonicalization now lives in
  `app/services/evidence_manifest_trace_graph.py` at `204` lines.
- mixed trace assembly now lives in
  `app/services/evidence_manifest_trace_assembly.py` at `461` lines.
- replay-lineage expansion now lives in
  `app/services/evidence_manifest_trace_replay.py` at `244` lines.
- `tests/unit/test_evidence_manifest_traces.py` now covers direct graph-owner
  placeholder replacement and edge dedupe, plus the `<= 600` facade budget
  ratchet.

Acceptance:

- `app/services/evidence_manifest_traces.py` is materially smaller and no
  longer contains the full mixed trace assembly body
- dedicated unit coverage exists for the moved graph-assembly concerns
- no spill occurred into `evidence_manifests.py` or replay alerts

### Milestone 2 - Closeout And Honest Broader Routing

Status: resolved locally in the current checkout
Outcome label: `resolved` for the scoped file and `reduced` for
`IC-65AF4A6D8B1E`

- Re-run the focused manifest-trace unit slice, the technical-report or
  audit-surface integration slices, hygiene, improvement-case, capability,
  architecture-inspection, architecture-quality, and architecture-probe gates.
- Add exact hygiene ratchets for the new manifest-trace owners and the reduced
  facade.
- Refresh `config/improvement_cases.yaml`, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` to match the fresh measured state.
- Leave the broader owner case explicitly `reduced` because
  `app/services/evidence_manifests.py` and
  `app/services/evidence_claim_support_replay_alerts.py`
  still exceed budget, and route the next blocker to the manifest owner.

Acceptance:

- `app/services/evidence_manifest_traces.py` is `<= 600` lines on the closeout
  baseline
- the facade no longer coexists with the full mixed trace assembly in one
  owner body
- facade and integration contracts remain green

## Required Implementation Artifacts

- focused manifest-trace owners under `app/services/evidence_manifest_trace_*.py`
- dedicated owner suite: `tests/unit/test_evidence_manifest_traces.py`
- updated routing and hygiene artifacts for every touched or newly created
  owner module

## Required Documentation And Handoff Updates

- update this plan with live milestone status and measured end-state counts
- update `docs/SESSION_HANDOFF.md` with the active or closed packet, exact
  manifest-trace measurements, case status, and next routing
- update `docs/agentic_architecture_index.md` so future sessions route to this
  packet instead of reopening the already-closed selected evidence seams
- update `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` so
  the broader evidence owner-family case matches the final measured state

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/evidence_manifest_traces.py app/services/evidence_manifest_trace_graph.py app/services/evidence_manifest_trace_assembly.py app/services/evidence_manifest_trace_replay.py tests/unit/test_evidence_manifest_traces.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py tests/unit/test_evidence_provenance_export_graph_core.py`
- `uv run pytest -q tests/unit/test_evidence_manifest_traces.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py tests/unit/test_evidence_provenance_export_graph_core.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_integrity.py tests/integration/test_technical_report_harness_audit_surfaces.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- `app/services/evidence_manifest_traces.py` measures `<= 600` lines on the
  closeout baseline
- no new or touched evidence owner file exceeds `800` lines
- `app/services/evidence_manifests.py` preserves its current public manifest
  surface and does not absorb moved trace implementation bodies
- dedicated unit coverage exists for manifest-trace behavior
- all required verification gates pass without weakening prior coverage
- the architecture-probe cycle count does not increase above `3`
- broader `IC-65AF4A6D8B1E` closure is claimed only if every remaining
  case-owned file is within budget on the refreshed closeout baseline

## Stop Conditions

- Milestone 0 shows the current blocker is no longer
  `app/services/evidence_manifest_traces.py`.
- The only viable reduction path requires moving substantial trace logic into
  `app/services/evidence_manifests.py` or
  `app/services/evidence_claim_support_replay_alerts.py`.
- The split would require an API, DB, or storage-contract redesign rather than
  an internal owner-boundary change.
- Focused owner or integration coverage has to be weakened to get green.

## Local Commit Closeout Policy

- Close each milestone with one local atomic commit after verification passes.
- Stage only the touched manifest-trace slice: implementation, tests, routing
  or hygiene files, this plan, the architecture index, and the session
  handoff.
- Do not mix unrelated dirty worktree changes into a milestone commit.
- A verified but uncommitted milestone is ready-to-close, not complete.

## Residual Risks And Next Routing

- `app/services/evidence_manifests.py` was the direct caller and immediate
  next blocker after this packet at the time of closeout; the later manifest-owner
  follow-on resolved that routed step locally.
- `app/services/evidence_claim_support_replay_alerts.py` may still need its own
  follow-on after the manifest and trace owners close.
- The immediate bounded follow-on after this packet is a dedicated manifest
  owner slice at `docs/evidence_manifest_owner_boundary_milestone_plan.md`.
- The manifest-owner follow-on is now resolved locally in the current checkout
  with `app/services/evidence_manifests.py` at `370` lines and
  `app/services/evidence_manifest_payloads.py` at `384`, so the next broader
  packet now routes to `app/services/evidence_claim_support_replay_alerts.py`.
