# Evidence Claim Support Replay Alerts Boundary Milestone Plan

Date: 2026-05-15 local / 2026-05-15 UTC
Status: resolved locally in the current checkout as the latest resolved bounded
evidence-owner follow-on after
`docs/evidence_manifest_owner_boundary_milestone_plan.md`; Milestones 0
through 2 are resolved locally, `app/services/evidence_claim_support_replay_alerts.py`
now measures `407` lines / `4` private helpers,
`app/services/evidence_claim_support_replay_alert_corpus.py` now measures
`128` lines / `0` private helpers, and the broader `IC-65AF4A6D8B1E` case now
has no governed file above the default `600`-line budget in the local checkout
and is locally retirement-ready pending an atomic milestone commit. The current
broader repo active bounded packet is now
`docs/hotspot_prevention_family_boundary_milestone_plan.md`.
Owner context: final bounded evidence-owner follow-on for
`IC-65AF4A6D8B1E` after the manifest-trace and manifest-owner packets closed
locally. This packet isolates replay-alert fixture-corpus snapshot lineage from
waiver-closure lifecycle integrity so the replay-alert root becomes a narrow
compatibility and orchestration owner without reopening manifest, provenance,
or policy-impact seams.

## Purpose

Retire the last live over-budget evidence owner in the local checkout without
shifting replay-alert corpus lineage into adjacent evidence, claim-support, or
facade modules.

The scoped problem was `app/services/evidence_claim_support_replay_alerts.py`,
which mixed waiver-closure event lookup, waiver integrity validation, closure
payload shaping, fixture-corpus snapshot governance integrity wiring, fixture
row shaping, snapshot payload assembly, and promotion-event snapshot indexing in
one `646`-line owner. This packet moves the replay-alert fixture-corpus
snapshot lineage family behind a focused sibling while preserving the public
surface consumed through `app/services/evidence.py` and technical-report
surfaces.

## Current Evidence

Milestone 0 baseline refreshed from the local checkout on 2026-05-15 local /
2026-05-15 UTC after the manifest-owner packet closed locally:

```text
wc -l app/services/evidence_claim_support_replay_alerts.py
   646 app/services/evidence_claim_support_replay_alerts.py

python - <<'PY'
from pathlib import Path
path = Path("app/services/evidence_claim_support_replay_alerts.py")
for i, line in enumerate(path.read_text().splitlines(), 1):
    if line.startswith("def ") or line.startswith("async def "):
        print(f"{i}: {line}")
PY
  34: def _claim_support_replay_alert_waiver_closure_events_by_impact(
  68: def _waiver_closure_event_integrity(
  246: def _waiver_closure_event_payload(
  291: def _replay_alert_fixture_corpus_snapshot_governance_integrity(
  418: def _replay_alert_fixture_corpus_row_payload(
  440: def _replay_alert_fixture_corpus_snapshot_payload(
  495: def _claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event(
  529: def _claim_support_replay_alert_waiver_lifecycle_summary(
```

Final local closeout baseline in the current checkout:

```text
wc -l app/services/evidence_claim_support_replay_alerts.py app/services/evidence_claim_support_replay_alert_corpus.py tests/unit/test_evidence_claim_support_replay_alerts.py
   407 app/services/evidence_claim_support_replay_alerts.py
   128 app/services/evidence_claim_support_replay_alert_corpus.py
   135 tests/unit/test_evidence_claim_support_replay_alerts.py

python - <<'PY'
from pathlib import Path
for path_str in [
    "app/services/evidence_claim_support_replay_alerts.py",
    "app/services/evidence_claim_support_replay_alert_corpus.py",
]:
    path = Path(path_str)
    count = 0
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("def _") or stripped.startswith("async def _"):
            count += 1
    print(f"{path_str} private_helpers={count}")
PY
  app/services/evidence_claim_support_replay_alerts.py private_helpers=4
  app/services/evidence_claim_support_replay_alert_corpus.py private_helpers=0

uv run pytest -q tests/unit/test_evidence_claim_support_replay_alerts.py tests/unit/test_evidence_facade_contract.py tests/unit/test_replay_alert_waiver_integrity.py tests/unit/test_claim_support_policy_impacts.py tests/unit/test_technical_reports.py
  24 passed

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_integrity.py tests/integration/test_technical_report_harness_audit_surfaces.py tests/integration/test_multivector_retrieval.py
  5 passed

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycle components: 3
  code files above 800 lines: 30
```

Current structural evidence:

- waiver-closure lookup, integrity checks, payload shaping, and lifecycle
  summary remain cohesive replay-alert root responsibilities
- replay-alert fixture-corpus snapshot row shaping, snapshot payload assembly,
  and promotion-event indexing form a separate lineage owner with a narrower
  shared dependency on
  `app/services/claim_support_replay_alert_fixture_corpus.py`
- the public replay-alert evidence aliases still need to route through
  `app/services/evidence_claim_support_replay_alerts.py` because
  `app/services/evidence.py` preserves that compatibility seam
- the broader evidence owner-family max is now
  `app/services/evidence_provenance_export_graph_core.py` at `549` lines, so
  this packet removes the final live over-budget evidence owner rather than
  simply rerouting to another evidence sibling

## Goal

Resolve the replay-alert evidence owner boundary so that:

- `app/services/evidence_claim_support_replay_alerts.py` measures `<= 600`
  lines on the closeout baseline
- replay-alert fixture-corpus snapshot lineage no longer cohabits with waiver
  closure integrity and lifecycle ownership in one root body
- `app/services/evidence.py` and downstream callers keep the same public
  replay-alert evidence surface
- a dedicated replay-alert owner suite exists before the packet closes
- the broader `IC-65AF4A6D8B1E` case is marked retirement-ready only if every
  governed owner surface is within budget on the refreshed closeout baseline

## Non-Goals

- No reopening of the manifest-trace or manifest-owner packets.
- No API, CLI, DB schema, migration, or storage-contract redesign.
- No silent debt shift into `app/services/evidence.py`,
  `app/services/evidence_claim_support_impacts.py`, or
  `app/services/claim_support_policy_impacts.py`.
- No weakening of replay-alert waiver, policy-impact, manifest, or
  technical-report verification coverage.

## Scope

In scope:

- live baseline refresh for the replay-alert evidence owner
- extraction of fixture-corpus snapshot lineage into a focused sibling owner
- replay-alert facade and compatibility alias preservation
- dedicated replay-alert owner test coverage
- routing, hygiene, improvement-case, index, and handoff updates needed for
  the closeout

Out of scope:

- broader claim-support policy-impact owner reductions
- manifest, provenance-export, or semantic-trace owner reshaping
- new replay-alert product features or workflow changes

## Owner Surfaces

- primary owner:
  `app/services/evidence_claim_support_replay_alerts.py`
- focused sibling under this packet:
  `app/services/evidence_claim_support_replay_alert_corpus.py`
- adjacent contracts and callers:
  `app/services/evidence.py`,
  `app/services/claim_support_replay_alert_fixture_corpus.py`,
  `tests/unit/test_evidence_claim_support_replay_alerts.py`,
  `tests/unit/test_evidence_facade_contract.py`,
  `tests/unit/test_replay_alert_waiver_integrity.py`,
  `tests/unit/test_claim_support_policy_impacts.py`,
  `tests/unit/test_technical_reports.py`,
  `tests/integration/test_technical_report_harness_integrity.py`,
  `tests/integration/test_technical_report_harness_audit_surfaces.py`,
  `tests/integration/test_multivector_retrieval.py`
- routing and prevention:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/evidence_residual_owner_family_milestone_plan.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  this plan

## Placement Rules

- Keep `app/services/evidence_claim_support_replay_alerts.py` as the public
  replay-alert evidence surface; do not move compatibility aliases into
  `app/services/evidence.py`.
- New replay-alert fixture-corpus snapshot lineage belongs under focused
  `app/services/evidence_claim_support_replay_alert_*.py` siblings, not inside
  manifest, provenance-export, semantic-trace, or policy-impact owners.
- Shared corpus governance integrity should reuse
  `app/services/claim_support_replay_alert_fixture_corpus.py` instead of
  duplicating the generic governance contract.
- No new or touched file may exceed `800` lines at milestone closeout.
- Add the dedicated owner suite as
  `tests/unit/test_evidence_claim_support_replay_alerts.py`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The replay-alert root shrinks only because snapshot lineage is dumped into another evidence facade or claim-support owner. | `app/services/evidence_claim_support_replay_alerts.py`, `app/services/evidence.py`, `app/services/evidence_claim_support_impacts.py` | `uv run docling-system-hygiene-check`, staged `wc -l` review, focused replay-alert unit suite | Any adjacent owner absorbs moved replay-alert bodies or a touched file rises above its recorded ratchet without explicit routing | Intentionally move one snapshot helper into `evidence.py` and confirm closeout review rejects it | A future session uses the public evidence facade as the easiest overflow bucket |
| The new corpus owner duplicates governance-integrity logic instead of reusing the shared fixture-corpus contract. | `app/services/evidence_claim_support_replay_alert_corpus.py`, `app/services/claim_support_replay_alert_fixture_corpus.py`, new owner suite | `uv run pytest -q tests/unit/test_evidence_claim_support_replay_alerts.py` | Snapshot governance integrity no longer resolves through the shared claim-support owner | Monkeypatch the corpus owner to return a different function object and confirm the owner suite fails | A future session forks replay-alert corpus integrity logic and creates silent divergence between evidence and claim-support surfaces |
| The split breaks replay-alert compatibility aliases used through `app/services/evidence.py`. | replay-alert facade, `app/services/evidence.py`, facade-contract tests | `uv run pytest -q tests/unit/test_evidence_claim_support_replay_alerts.py tests/unit/test_evidence_facade_contract.py tests/unit/test_replay_alert_waiver_integrity.py tests/unit/test_claim_support_policy_impacts.py tests/unit/test_technical_reports.py` | Moved snapshot helpers or waiver helpers stop re-exporting through the replay-alert facade or the top-level evidence facade | Remove one alias forwarding assignment and confirm the facade-contract test fails | A future session changes internals and forgets that report and evidence callers consume this surface indirectly |
| The packet claims broader evidence-family retirement without proving the family is now within budget. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, handoff, index, this plan | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, `uv run docling-system-hygiene-check`, architecture probe | Registry or docs claim broader retirement while any governed evidence owner still exceeds budget on the fresh closeout baseline | Leave one governed evidence owner above `600` while declaring the case retired and confirm the routing review blocks acceptance | A future session closes the broader evidence case from local prose without a measured owner-family baseline |

## Milestone Sequence

### Milestone 0 - Live Refresh And Owner-Test Seam

Status: resolved locally in the current checkout
Outcome label: reduced

- Refresh `git status -sb`, `wc -l`, and the active evidence-owner routing.
- Add `tests/unit/test_evidence_claim_support_replay_alerts.py` before broad
  code motion.
- Lock the follow-on scope to the replay-alert evidence owner while preserving
  the existing shared claim-support corpus governance contract.

### Milestone 1 - Replay-Alert Corpus Boundary

Status: resolved locally in the current checkout
Outcome label: resolved

- Extract fixture-corpus snapshot row shaping, snapshot payload assembly, and
  promotion-event snapshot indexing into
  `app/services/evidence_claim_support_replay_alert_corpus.py`.
- Reduce the replay-alert root to waiver-closure lifecycle integrity and
  forwarding assignments.
- Expand the dedicated owner suite to cover shared governance reuse, snapshot
  payload completeness, promotion-event indexing, facade re-exports, and the
  root size ratchet.

### Milestone 2 - Closeout And Honest Broader Routing

Status: resolved locally in the current checkout
Outcome label: resolved

- Add exact hygiene ratchets for the replay-alert root and the new corpus owner.
- Refresh `config/improvement_cases.yaml`, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and the broader routing notes to match
  the fresh measured state.
- Mark the broader evidence owner-family case as locally retirement-ready
  pending an atomic closeout commit because no governed file remains above the
  default budget in the current checkout.

## Required Implementation Artifacts

- `app/services/evidence_claim_support_replay_alerts.py`
- `app/services/evidence_claim_support_replay_alert_corpus.py`
- `tests/unit/test_evidence_claim_support_replay_alerts.py`
- replay-alert facade coverage in
  `tests/unit/test_evidence_facade_contract.py`
- updated routing and hygiene artifacts for every touched or newly created
  owner module

## Required Documentation And Handoff Updates

- update this plan with live milestone status and measured end-state counts
- update `docs/SESSION_HANDOFF.md` with the active ready-to-close packet,
  exact replay-alert measurements, broader case state, and next routing
- update `docs/agentic_architecture_index.md` so future sessions route to this
  packet instead of reopening the manifest-owner packet
- update `docs/evidence_manifest_owner_boundary_milestone_plan.md`,
  `docs/evidence_manifest_trace_graph_boundary_milestone_plan.md`,
  `docs/evidence_residual_owner_family_milestone_plan.md`, and
  `docs/boring_change_architecture_milestone_plan.md` where they still present
  replay alerts as an unresolved live blocker
- update `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` so
  owner routing matches the final measured state

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/evidence_claim_support_replay_alerts.py app/services/evidence_claim_support_replay_alert_corpus.py tests/unit/test_evidence_claim_support_replay_alerts.py tests/unit/test_evidence_facade_contract.py tests/unit/test_replay_alert_waiver_integrity.py tests/unit/test_claim_support_policy_impacts.py tests/unit/test_technical_reports.py`
- `uv run pytest -q tests/unit/test_evidence_claim_support_replay_alerts.py tests/unit/test_evidence_facade_contract.py tests/unit/test_replay_alert_waiver_integrity.py tests/unit/test_claim_support_policy_impacts.py tests/unit/test_technical_reports.py`
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

- `app/services/evidence_claim_support_replay_alerts.py` measures `<= 600`
  lines on the closeout baseline
- `app/services/evidence_claim_support_replay_alert_corpus.py` stays below
  `600` lines
- `app/services/evidence.py` preserves its current public replay-alert surface
- dedicated unit coverage exists for replay-alert evidence-owner behavior
- all required verification gates pass without weakening prior coverage
- the refreshed closeout baseline shows no governed `IC-65AF4A6D8B1E` owner
  above the default `600`-line budget

## Stop Conditions

- The only viable reduction path requires moving substantial replay-alert logic
  into `app/services/evidence.py`,
  `app/services/evidence_claim_support_impacts.py`, or another already-owned
  evidence or claim-support surface.
- The split would require an API, DB, or storage-contract redesign rather than
  an internal owner-boundary change.
- Focused owner or integration coverage has to be weakened to get green.

## Local Commit Closeout Policy

- Close the milestone with one local atomic commit after verification passes.
- Stage only the touched replay-alert slice: implementation, tests, routing or
  hygiene files, this plan, the architecture index, and the session handoff.
- Do not mix unrelated dirty worktree changes into a milestone commit.
- A verified but uncommitted milestone is ready-to-close, not complete.

## Residual Risks And Next Routing

- No further bounded evidence-owner follow-on remains if this packet is
  committed cleanly; the broader evidence owner-family case is locally
  retirement-ready in the current checkout.
- The next broader coordination route returns to
  `docs/boring_change_architecture_milestone_plan.md` for non-evidence large
  owners, test monoliths, and the remaining cycle backlog.
