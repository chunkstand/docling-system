# UI Module Residual Owner Family Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally in the current checkout through the 2026-05-18 UI
module-family closeout pass. The atomic closeout commit is still pending while
the broader checkout remains dirty with unrelated work.
Owner context: follow-on packet for the shipped operator UI module monoliths
that remained above the live large-file threshold after `app/ui/app.js` was
reduced to a narrow bootstrap under `IC-1B643BA0AD90`.

## Purpose

Resolve the residual UI module debt without reopening the shipped bootstrap.

The routed weakness began in the module family:

- `app/ui/modules/agents.js` at `1300` lines
- `app/ui/modules/shared.js` at `930` lines

The local closeout now leaves the governed UI family at:

- `app/ui/modules/shared_runtime.js` at `307` lines
- `app/ui/modules/shared.js` at `517` lines
- `app/ui/modules/shared_search_rendering.js` at `115` lines
- `app/ui/modules/agents_collections.js` at `56` lines
- `app/ui/modules/agents_claim_support_replay.js` at `313` lines
- `app/ui/modules/agents_report_harness.js` at `318` lines
- `app/ui/modules/agents.js` at `599` lines
- `app/ui/app.js` still at `107` lines

## Closeout Summary

The 2026-05-18 local closeout completed the intended split without moving UI
ownership back into the bootstrap or into one new helper sink.

- Auth, stored credential, fetch, runtime-status, and protected-download
  ownership now live in `app/ui/modules/shared_runtime.js`.
- Harness-card and search-result rendering now live in
  `app/ui/modules/shared_search_rendering.js`.
- Task-collection rendering now lives in
  `app/ui/modules/agents_collections.js`.
- Claim-support replay worklist, queue, and status-refresh ownership now lives
  in `app/ui/modules/agents_claim_support_replay.js`.
- Technical-report harness contract, run-list, and packet rendering now lives
  in `app/ui/modules/agents_report_harness.js`.
- All shipped HTML entrypoints now load the split module graph before
  `app/ui/app.js`, and the focused UI suite remains green.

## Current Evidence

- The live architecture probe on 2026-05-18 now reports `11` code files above
  `800`, and no UI module remains in that backlog.
- `config/improvement_cases.yaml` keeps the governed UI family routed through
  `IC-81F2C6D4B9A7` until an atomic closeout commit records the verified local
  retirement.
- `config/hygiene_policy.yaml` now exact-ratchets the routed UI roots plus all
  newly introduced helper modules under `IC-81F2C6D4B9A7` so the split does not
  shift debt into another JavaScript sink.
- All shipped HTML entrypoints now load the split UI module graph before
  `/ui/app.js`.
- `tests/unit/test_ui.py` and `tests/unit/test_ui_static_assets.py` now assert
  the expanded asset graph and passed together at `10 passed`.
- `docs/residual_large_file_backlog_milestone_plan.md` now advances the queue
  past this resolved UI packet to the semantic/report residual family.

## Goal

Reduce the UI module family so that:

- `app/ui/modules/agents.js` and `app/ui/modules/shared.js` both fall below
  `800` lines, with the local closeout keeping both at or below the default
  `600`-line budget.
- `app/ui/app.js` remains the narrow shipped bootstrap.
- any new UI sibling left between `601` and `800` lines is routed in the same
  milestone with explicit hygiene ownership.
- UI behavior and static-asset tests remain green.

## Non-Goals

- No UI redesign or new product features.
- No moving shared runtime logic back into `app/ui/app.js`.
- No replacing module splits with one new `app/ui/modules/common.js` sink.

## Scope

In scope:

- `app/ui/modules/agents.js`
- `app/ui/modules/shared.js`
- family-local helper modules created under `app/ui/modules/`
- `tests/unit/test_ui.py`
- `tests/unit/test_ui_static_assets.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `docs/ui_module_residual_owner_family_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

Out of scope:

- changes to unrelated Python services
- broad CSS or asset-system rewrites
- changing `app/ui/app.js` from bootstrap to owner sink again

## Owner Surfaces

- `app/ui/app.js`
- `app/ui/modules/agents.js`
- `app/ui/modules/shared.js`
- any focused module siblings created by the packet
- `tests/unit/test_ui.py`
- `tests/unit/test_ui_static_assets.py`

## Placement Rules

- Keep `app/ui/app.js` as the narrow shipped bootstrap.
- Split shared runtime or page-family logic into focused module siblings under
  `app/ui/modules/`.
- Do not recreate a large generic helper sink under a different filename.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Shared runtime logic moves out of one JS monolith and regrows in another. | `app/ui/modules/*.js`, architecture probe | `node --check`, UI tests, architecture probe | a touched UI module still exceeds its ratchet or a new `>800` JS sibling appears | move split logic from `agents.js` into `shared.js` and confirm closeout rejects it | future Codex recreates the UI sink under a more generic filename |
| The bootstrap regrows because it is the easiest import surface. | `app/ui/app.js` | bootstrap line-count readback, UI tests | `app/ui/app.js` grows beyond its existing narrow role | add a moved page-factory block back to `app/ui/app.js` and confirm the packet fails | a later session reopens the bootstrap instead of routing through modules |
| Tests stay green because the packet removes interaction coverage. | UI unit roots | focused UI test slice | assertions disappear without equivalent replacement coverage | replace a targeted UI behavior assertion with a smoke check and confirm review or tests reject it | future Codex optimizes for file size and keeps only shallow asset checks |

## Milestone Sequence

### Milestone 0. Baseline Lock
Outcome label: reduced

Refresh the two routed line counts, confirm `IC-81F2C6D4B9A7`, and lock the UI
test slice before code motion.

### Milestone 1. Shared Runtime Split
Outcome label: reduced

Move shared runtime ownership out of `app/ui/modules/shared.js` without
regrowing the bootstrap.

### Milestone 2. Agents Module Split
Outcome label: reduced

Reduce `app/ui/modules/agents.js` below `800` through focused agent-specific
helpers or module siblings.

### Milestone 3. Closeout
Outcome label: resolved

Close the packet only when both routed JS module roots are below `800`, docs
are updated, and the UI verification slice is green.

Local result: resolved on 2026-05-18 in the current checkout. The governed UI
family no longer appears in the live `>800` backlog and no governed UI root is
above the default `600`-line budget.

## Required Implementation Artifacts

- focused UI module siblings created by the split
- refreshed routing config in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`
- updated closeout docs and handoff artifacts

## Required Documentation And Handoff Updates

- `docs/ui_module_residual_owner_family_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

## Required Verification Gates

- `git diff --check`
- `node --check app/ui/modules/shared_runtime.js`
- `node --check app/ui/modules/shared.js`
- `node --check app/ui/modules/shared_search_rendering.js`
- `node --check app/ui/modules/agents_collections.js`
- `node --check app/ui/modules/agents_claim_support_replay.js`
- `node --check app/ui/modules/agents_report_harness.js`
- `node --check app/ui/modules/agents.js`
- `node --check app/ui/app.js`
- `uv run pytest -q tests/unit/test_ui.py tests/unit/test_ui_static_assets.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- `app/ui/modules/agents.js` and `app/ui/modules/shared.js` both fall below
  `800` lines and the governed UI family has no file above the default
  `600`-line budget.
- `app/ui/app.js` remains the narrow bootstrap and does not regrow as a module
  sink.
- Newly introduced UI siblings are exact-ratcheted in the same milestone.
- `tests/unit/test_ui.py` and `tests/unit/test_ui_static_assets.py` stay green.

## Stop Conditions

- Stop if a fresh probe changes the routed UI backlog before code motion
  begins.
- Stop if a reduction plan requires moving implementation back into
  `app/ui/app.js`.
- Stop if the split only stays green by removing UI behavior assertions.

## Local Commit Closeout Policy

- Close this packet with one atomic local commit containing only the UI module
  changes, focused tests, routing updates, and doc or handoff updates.

## Residual Risks And Next Milestone Routing

- If a routed UI sibling remains between `601` and `800`, keep it routed under
  `IC-81F2C6D4B9A7` and name the exact follow-on before closeout.
- After this packet closes, return to
  `docs/residual_large_file_backlog_milestone_plan.md` and activate
  `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`
  unless a fresh rebaseline changes the queue.

## Verification Snapshot

- `node --check` passed across the full shipped UI module graph, including the
  new helper modules plus `app/ui/app.js`.
- `uv run pytest -q tests/unit/test_ui.py tests/unit/test_ui_static_assets.py`
  passed at `10 passed`.
- `uv run docling-system-improvement-case-validate` returned `valid=true`.
- `uv run docling-system-hygiene-check` reported `new hygiene regressions:
  none`.
- The live architecture probe now reports `11` code files above `800` with `0`
  Python cycle components.
