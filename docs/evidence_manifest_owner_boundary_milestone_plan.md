# Evidence Manifest Owner Boundary Milestone Plan

Date: 2026-05-15 local / 2026-05-15 UTC
Status: resolved locally in the current checkout as an uncommitted standalone
follow-on after
`docs/evidence_manifest_trace_graph_boundary_milestone_plan.md`; Milestones 0
through 2 are resolved locally, `app/services/evidence_manifests.py` now
measures `370` lines, `app/services/evidence_manifest_payloads.py` now measures
`384` lines, and the later replay-alert follow-on now reduces
`app/services/evidence_claim_support_replay_alerts.py` to `407` lines with
fixture-corpus snapshot lineage in
`app/services/evidence_claim_support_replay_alert_corpus.py` at `128`, leaving
the broader owner-family case locally retirement-ready pending commit

## Purpose

Reduce the next broader evidence owner without reopening the just-split
manifest-trace packet or silently shifting manifest work into replay-alert or
facade owners.

The immediate scoped problem was `app/services/evidence_manifests.py`, which
mixed technical-report evidence-manifest payload assembly, manifest integrity,
row shaping, persistence and refresh lifecycle, and trace-graph hydration in
one `725`-line owner. This packet isolates payload assembly behind a focused
manifest sibling while preserving the public manifest surface used by
`app/services/evidence.py`, agent-task routes, report drafting, and provenance
export callers.

## Current Evidence

Milestone 0 baseline refreshed from the local checkout on 2026-05-15 local /
2026-05-15 UTC after the manifest-trace packet closed locally:

```text
wc -l app/services/evidence_manifests.py app/services/evidence_claim_support_replay_alerts.py app/services/evidence_manifest_traces.py
   725 app/services/evidence_manifests.py
   646 app/services/evidence_claim_support_replay_alerts.py
   203 app/services/evidence_manifest_traces.py

python - <<'PY'
from pathlib import Path
path = Path("app/services/evidence_manifests.py")
for i, line in enumerate(path.read_text().splitlines(), 1):
    if line.startswith("def ") or line.startswith("async def "):
        print(f"{i}: {line}")
PY
  54: def _existing_evidence_manifest(
  67: def build_technical_report_evidence_manifest_payload(
  416: def _evidence_manifest_integrity_payload(
  458: def _evidence_manifest_response(
  470: def _evidence_manifest_row_from_payload(
  501: def _update_evidence_manifest_row_from_payload(
  526: def _evidence_manifest_has_release_readiness_db_gate_record(
  550: def _evidence_manifest_matches_current_payload(
  564: def persist_technical_report_evidence_manifest(
  622: def refresh_technical_report_evidence_manifest(
  670: def _ensure_evidence_trace_graph(
  685: def get_agent_task_evidence_manifest(
  691: def get_agent_task_evidence_trace(
```

Final local closeout baseline in the current checkout:

```text
wc -l app/services/evidence_manifests.py app/services/evidence_manifest_payloads.py app/services/evidence_claim_support_replay_alerts.py
   370 app/services/evidence_manifests.py
   384 app/services/evidence_manifest_payloads.py
   646 app/services/evidence_claim_support_replay_alerts.py

uv run pytest -q tests/unit/test_evidence_manifests.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py
  19 passed

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_integrity.py tests/integration/test_technical_report_harness_audit_surfaces.py tests/integration/test_multivector_retrieval.py
  5 passed

uv run docling-system-hygiene-check
  new hygiene regressions: none

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  3 Python cycle components
  30 code files above 800
```

Current structural evidence:

- the large manifest payload builder was the dominant owner body and the
  clearest first extraction seam
- `persist_technical_report_evidence_manifest(...)`,
  `refresh_technical_report_evidence_manifest(...)`, and the integrity or
  response helpers now remain in a smaller manifest facade without the mixed
  payload assembly body
- at the time this packet closed locally,
  `app/services/evidence_claim_support_replay_alerts.py` remained the last
  live `IC-65AF4A6D8B1E` blocker above the default `600`-line budget; the
  later replay-alert follow-on now resolves that final evidence split locally

## Goal

Resolve the `app/services/evidence_manifests.py` owner boundary so that:

- `app/services/evidence_manifests.py` measures `<= 600` lines on the closeout
  baseline
- technical-report evidence-manifest payload assembly no longer cohabits with
  the lifecycle and response surface in one owner body
- `app/services/evidence.py` and downstream callers keep the same public
  manifest surface
- a dedicated manifest owner suite exists before the packet closes
- the broader `IC-65AF4A6D8B1E` case remains explicitly `reduced` unless every
  remaining case-owned evidence file is within budget on the fresh closeout
  baseline

## Non-Goals

- No reopening of the manifest-trace split.
- No API, CLI, DB schema, migration, or storage-contract redesign.
- No silent debt shift into `app/services/evidence_claim_support_replay_alerts.py`
  or `app/services/evidence.py`.
- No weakened manifest, trace, audit-surface, or retrieval integration
  coverage.

## Owner Surfaces

- primary owner:
  `app/services/evidence_manifests.py`
- focused sibling under this packet:
  `app/services/evidence_manifest_payloads.py`
- adjacent callers and contracts:
  `app/services/evidence.py`,
  `app/services/agent_task_worker.py`,
  `app/services/agent_actions/report_drafting.py`,
  `app/services/evidence_provenance_export_graph_core.py`,
  `tests/unit/test_evidence_manifests.py`,
  `tests/unit/test_evidence_facade_contract.py`,
  `tests/unit/test_technical_reports.py`,
  `tests/integration/test_technical_report_harness_integrity.py`,
  `tests/integration/test_technical_report_harness_audit_surfaces.py`,
  `tests/integration/test_multivector_retrieval.py`

## Placement Rules

- Keep `app/services/evidence_manifests.py` as the manifest-oriented public
  surface; do not move lifecycle or response behavior into `app/services/evidence.py`.
- New manifest payload assembly belongs under a focused
  `app/services/evidence_manifest_*.py` sibling, not in replay-alert,
  provenance-export, or audit-view owners.
- No new or touched file may exceed `800` lines at milestone closeout.
- Add the dedicated owner suite as `tests/unit/test_evidence_manifests.py`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The file shrinks only because manifest work is dumped into replay-alert or facade owners. | `app/services/evidence_manifests.py`, `app/services/evidence_claim_support_replay_alerts.py`, `app/services/evidence.py` | `uv run docling-system-hygiene-check`, staged `wc -l` review, focused manifest unit suite | Any adjacent evidence owner grows by absorbing moved manifest bodies or a touched file rises above its live ratchet without explicit routing | Intentionally move one manifest payload branch into replay alerts and confirm closeout review rejects it | A future session uses the replay-alert owner as the next easiest overflow bucket |
| The split is cosmetic and leaves the broad payload builder in the facade owner. | `app/services/evidence_manifests.py`, `app/services/evidence_manifest_payloads.py`, new unit suite | `uv run pytest -q tests/unit/test_evidence_manifests.py`, file-shape review | `build_technical_report_evidence_manifest_payload(...)` still owns the mixed payload body in the facade at closeout | Keep the large builder intact and add only wrappers; confirm the owner review blocks acceptance | A future session declares success because a sibling file exists while the broad owner still does the real work |
| The split breaks manifest callers or trace hydration behavior. | manifest facade, report drafting, provenance export, agent-task routes, integration harnesses | `uv run pytest -q tests/unit/test_evidence_manifests.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py`, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_integrity.py tests/integration/test_technical_report_harness_audit_surfaces.py tests/integration/test_multivector_retrieval.py` | Caller imports break, manifest integrity drifts, or manifest and trace retrieval surfaces regress | Remove one manifest export or perturb the built payload and confirm the focused or integration gates fail | A future session changes internals and forgets that report drafting, API routes, and provenance export consume this manifest surface |
| The packet claims broader evidence-family retirement while replay alerts still exceed budget. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, this plan, handoff, index | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, `uv run docling-system-hygiene-check` | Registry or docs mark `IC-65AF4A6D8B1E` closed without live proof that every case-owned file is within budget | Leave replay alerts at `646` while claiming the whole case is resolved and confirm closeout review rejects it | A future session closes the owner case based on the manifest split alone and loses track of the last blocker |

## Milestone Sequence

### Milestone 0 - Live Refresh And Owner-Test Seam

Status: resolved locally in the current checkout
Outcome label: `reduced`

- Refresh `git status -sb`, `wc -l` for the remaining broader evidence owners,
  and current routing.
- Add `tests/unit/test_evidence_manifests.py` before broad code motion.
- Lock the follow-on scope to `app/services/evidence_manifests.py` while
  keeping replay alerts as the explicit adjacent blocker rather than a silent
  spill target.

### Milestone 1 - Manifest Payload Boundary

Status: resolved locally in the current checkout
Outcome label: `resolved`

- Extract technical-report evidence-manifest payload assembly into
  `app/services/evidence_manifest_payloads.py`.
- Reduce `build_technical_report_evidence_manifest_payload(...)` in
  `app/services/evidence_manifests.py` to a forwarding facade.
- Expand the new owner suite to cover payload aggregation, missing-task error
  handling, checklist completeness, and the facade size ratchet.

### Milestone 2 - Closeout And Honest Broader Routing

Status: resolved locally in the current checkout
Outcome label: `resolved` for the scoped file and `reduced` for
`IC-65AF4A6D8B1E`

- Add exact hygiene ratchets for the reduced facade and the new payload owner.
- Refresh `config/improvement_cases.yaml`, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and broader routing notes to match the
  fresh measured state.
- Route the next broader owner packet to
  `app/services/evidence_claim_support_replay_alerts.py`.

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/evidence_manifests.py app/services/evidence_manifest_payloads.py tests/unit/test_evidence_manifests.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py`
- `uv run pytest -q tests/unit/test_evidence_manifests.py tests/unit/test_evidence_facade_contract.py tests/unit/test_technical_reports.py`
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

- `app/services/evidence_manifests.py` measures `<= 600` lines on the closeout
  baseline
- `app/services/evidence_manifest_payloads.py` stays below `600` lines
- `app/services/evidence.py` preserves its current public manifest surface
- dedicated unit coverage exists for manifest-owner behavior
- all required verification gates pass without weakening prior coverage
- broader `IC-65AF4A6D8B1E` closure is claimed only if every remaining
  case-owned file is within budget on the refreshed closeout baseline

## Stop Conditions

- The only viable reduction path requires moving substantial manifest logic
  into replay-alert or facade owners.
- The split would require an API, DB, or storage-contract redesign rather than
  an internal owner-boundary change.
- Focused owner or integration coverage has to be weakened to get green.

## Local Commit Closeout Policy

- Close the milestone with one local atomic commit after verification passes.
- Stage only the touched manifest-owner slice: implementation, tests, routing
  or hygiene files, this plan, the architecture index, and the session
  handoff.
- Do not mix unrelated dirty worktree changes into a milestone commit.
- A verified but uncommitted milestone is ready-to-close, not complete.

## Residual Risks And Next Routing

- The later replay-alert follow-on now reduces
  `app/services/evidence_claim_support_replay_alerts.py` to `407` lines,
  adds `app/services/evidence_claim_support_replay_alert_corpus.py` at `128`,
  and leaves no governed evidence owner above budget in the local checkout.
- No further bounded evidence-owner follow-on remains after this predecessor
  packet. Once the replay-alert packet is committed, broader routing should
  return to `docs/boring_change_architecture_milestone_plan.md`.
