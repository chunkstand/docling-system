# Claim Support Residual Owner Family Milestone Plan

Date: 2026-05-14 local / 2026-05-14 UTC
Status: resolved locally through closeout commit `40024a3` on 2026-05-15 local
/ 2026-05-15 UTC after the freshness rebaseline, claim-support guardrail
hardening, policy-impact residual owner split, support-family residual owner
split, and verification closeout for `IC-E2270F89B397` and
`IC-7C73737C689F`
Owner context: the claim-support residual owner family no longer depends on
inherited over-budget compatibility seams. `app/services/claim_support_policy_impacts.py`,
`app/services/claim_support_evaluations.py`,
`app/services/claim_support_policy_governance.py`, and
`app/services/claim_support_replay_alert_fixture_corpus.py` are now compact
public seams, every extracted owner closes at or below the default `600`-line
budget, both claim-support improvement cases are now deployed locally, and the
remaining downstream routing returns to
`docs/boring_change_architecture_milestone_plan.md` plus the separate
hotspot-prevention residual `IC-6C1B516A3F92`.

## Purpose

Resolve the remaining claim-support service debt so the domain no longer
depends on inherited oversized owner files after the policy-impact facade split.

The issue is broader than one hotspot:

- the policy-impact facade is already narrow, but the extracted owners are not
  yet small enough to retire `IC-E2270F89B397`
- the support-family residual files were only routed into
  `IC-7C73737C689F`; they have not yet been decomposed behind explicit owner
  seams
- the live architecture probe still reports a Python cycle between
  `app.services.claim_support_policy_impacts` and
  `app.services.claim_support_replay_alert_promotions`

This plan resolves that claim-support residual program end to end by refreshing
live state, tightening the claim-support guardrails, closing the policy-impact
residual owner case, closing the support-family residual owner case, and
aligning the registry and handoff only after the live gates prove both cases
can be retired.

This is a standalone claim-support packet. Do not append these steps to
`docs/boring_change_architecture_milestone_plan.md`; that broader coordination
brief remains downstream of this domain-specific closeout.

## Closeout

Closeout outcome from closeout commit `40024a3`:

- `app/services/claim_support_policy_impacts.py` remains a `184` line /
  `0` private-helper compatibility facade, while the extracted policy-impact
  owner family now closes at `207 / 0`, `361 / 7`, `469 / 9`, `247 / 6`,
  `344 / 4`, `424 / 1`, `600 / 9`, `428 / 9`, and `535 / 6`.
- `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py` now close as
  compact public seams at `164 / 0`, `257 / 6`, and `206 / 0`, while the
  extracted support-family owners close at `534 / 7`, `319 / 4`, `339 / 1`,
  `534 / 6`, `559 / 2`, `328 / 4`, and `569 / 8`.
- The live claim-support cycle between
  `app.services.claim_support_policy_impacts` and
  `app.services.claim_support_replay_alert_promotions` is gone from the
  architecture probe.
- No new claim-support service hotspots formed during this split: the
  architecture-quality summary top hotspot paths still exclude claim-support
  service modules, the architecture probe top 20 no longer routes the split
  claim-support owner files, and the only directly related residual still
  carried by this packet is `app/hotspot_prevention_classifier.py` at `999`
  lines under `IC-6C1B516A3F92`.
- Strict hotspot prevention now guards the compact claim-support seams and
  allows only shrink-only residual refactors in those files; the closeout
  window passed with `blocked=0` and `allowed=7`.
- `IC-E2270F89B397` and `IC-7C73737C689F` are now deployed locally rather than
  reduced/open residuals.

Closeout verification from this local window:

- `uv run ruff check ...`: all checks passed across the touched claim-support,
  hotspot-prevention, and focused test surfaces
- `uv run pytest -q tests/unit/test_claim_support_policy_impacts.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_claim_support_evaluations.py tests/unit/test_claim_support_policy_governance.py tests/unit/test_claim_support_policy_imports.py tests/unit/test_hotspot_prevention.py`: `51 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_claim_support_judge_evaluation_roundtrip.py tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`: `17 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1995 passed`
- `uv run docling-system-hygiene-check`, `uv run docling-system-architecture-inspect`, `uv run docling-system-capability-contracts`, and `uv run docling-system-improvement-case-validate`: all green
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`: the claim-support cycle is gone and the remaining cycles are outside this family

## Current Evidence

The section below preserves the Milestone 0 starting baseline from 2026-05-14
for traceability. Use the Closeout section plus the aligned routing artifacts
for the final post-closeout state recorded by commit `40024a3`.

Live repo evidence refreshed from the current local checkout on 2026-05-14
local / 2026-05-14 UTC:

```text
git status -sb
  ## main...origin/main [ahead 2]
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
  ?? docs/search_compatibility_facade_boundary_milestone_plan.md

wc -l app/services/claim_support_policy_impacts.py app/services/claim_support_policy_impact_views.py app/services/claim_support_policy_impact_replay.py app/services/claim_support_replay_alert_promotions.py app/services/claim_support_evaluations.py app/services/claim_support_policy_governance.py app/services/claim_support_replay_alert_fixture_corpus.py
   184 app/services/claim_support_policy_impacts.py
   899 app/services/claim_support_policy_impact_views.py
   898 app/services/claim_support_policy_impact_replay.py
  1536 app/services/claim_support_replay_alert_promotions.py
  1142 app/services/claim_support_evaluations.py
  1259 app/services/claim_support_policy_governance.py
   972 app/services/claim_support_replay_alert_fixture_corpus.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 30
  Largest files include:
    app/services/claim_support_replay_alert_promotions.py = 1536
    app/services/claim_support_policy_governance.py = 1259
    app/services/claim_support_evaluations.py = 1142
    app/services/claim_support_replay_alert_fixture_corpus.py = 972
  Hotspots include:
    app/services/claim_support_policy_governance.py = 10 revisions, 1259 lines, score 12590
    app/services/claim_support_evaluations.py = 9 revisions, 1142 lines, score 10278
  Python cycles:
    app.services.claim_support_policy_impacts,
    app.services.claim_support_replay_alert_promotions

uv run docling-system-hygiene-check
  app/services/claim_support_evaluations.py: file_budget_inherited: 1142 lines exceeds target budget 600; owner=IC-7C73737C689F
  app/services/claim_support_policy_governance.py: file_budget_inherited: 1259 lines exceeds target budget 600; owner=IC-7C73737C689F
  app/services/claim_support_replay_alert_fixture_corpus.py: file_budget_inherited: 972 lines exceeds target budget 600; owner=IC-7C73737C689F
  new hygiene regressions: none

config/improvement_cases.yaml
  IC-E2270F89B397 remains reduced because app/services/claim_support_policy_impact_views.py,
  app/services/claim_support_policy_impact_replay.py, and
  app/services/claim_support_replay_alert_promotions.py still exceed the default
  600-line budget after closeout commit 3d7d090.
  IC-7C73737C689F remains open because
  app/services/claim_support_evaluations.py,
  app/services/claim_support_policy_governance.py, and
  app/services/claim_support_replay_alert_fixture_corpus.py still rely on
  inherited ratchet ceilings instead of resolved owner decompositions.
```

Repo-current structural evidence:

- `docs/claim_support_policy_impacts_boundary_milestone_plan.md` is resolved
  locally through closeout commit `3d7d090`, so the old subsystem-knot brief is
  not the right implementation surface anymore.
- The residual policy-impact owner case is larger than the selected excerpt
  alone suggests. `app/services/claim_support_replay_alert_promotions.py` is
  still `1536` lines and remains governed under `IC-E2270F89B397` alongside the
  `899`-line views owner and `898`-line replay owner.
- `app/services/claim_support_policy_impact_views.py` currently mixes detail,
  list, summary, worklist, alert feed, escalation receipt, and evidence-manifest
  refresh logic in one file.
- `app/services/claim_support_policy_impact_replay.py` currently mixes replay
  plan integrity, replay-task queueing, replay-status refresh, closure receipt
  construction, and closure governance in one file.
- `app/services/claim_support_replay_alert_promotions.py` currently mixes alert
  coverage summaries, candidate derivation, promotion-event shaping, and
  waiver-closure governance while also back-importing
  `claim_support_policy_change_impact_alerts(...)` from the
  `app.services.claim_support_policy_impacts` facade, which is the live source
  of the current claim-support cycle.
- `app/services/claim_support_evaluations.py` currently mixes built-in fixture
  authoring, fixture-set persistence, mined-failure harvesting, calibration
  policy persistence, and judge-evaluation runtime logic in one file.
- `app/services/claim_support_policy_governance.py` currently mixes policy
  change-impact payload assembly and persistence with policy-activation
  governance payload, receipt, PROV, and semantic-governance event recording.
- `app/services/claim_support_replay_alert_fixture_corpus.py` currently mixes
  corpus build, active-snapshot activation, semantic-governance receipt
  recording, integrity checking, and read summaries in one file.
- Direct owner tests are already small enough to support new focused test files
  instead of regrowing monoliths:
  `tests/unit/test_claim_support_evaluations.py` is `113` lines,
  `tests/unit/test_claim_support_policy_governance.py` is `37` lines,
  `tests/unit/test_claim_support_policy_impact_views.py` is `256` lines,
  `tests/unit/test_claim_support_policy_impact_replay.py` is `225` lines,
  and `tests/unit/test_claim_support_policy_impacts.py` is `116` lines.
- Existing DB-backed claim-support integration coverage is meaningful and must
  remain strong:
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`,
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py`,
  and `tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
  already exercise the sensitive runtime and governance seams this plan must
  preserve.

## Goal

Retire the remaining claim-support residual architecture so that:

- `IC-E2270F89B397` is resolved because
  `app/services/claim_support_policy_impact_views.py`,
  `app/services/claim_support_policy_impact_replay.py`, and
  `app/services/claim_support_replay_alert_promotions.py` are all reduced to
  bounded owner surfaces at or below the configured `600`-line budget
- `IC-7C73737C689F` is resolved because
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py` are all reduced
  to bounded owner surfaces at or below the configured `600`-line budget
- `app/services/claim_support_policy_impacts.py` remains a narrow compatibility
  facade
- the live claim-support import cycle between
  `app.services.claim_support_policy_impacts` and
  `app.services.claim_support_replay_alert_promotions` is removed
- the claim-support API, replay, governance, fixture, and evaluation contracts
  remain stable or better covered

## Non-Goals

- No DB model split for `app/db/model_domains/claim_support.py` in this packet.
- No redesign of technical-report, evidence-export, or semantic-governance
  behavior beyond the focused changes needed to preserve current claim-support
  contracts.
- No API route redesign for the claim-support route family.
- No migration or persistence-schema change unless a focused refactor proves one
  is required and separately routed.
- No test weakening, narrower assertions, added skips, or xfail broadening.
- No generic “clean up claim-support” sweep that touches adjacent evidence or
  report services without an explicit owner boundary.

## Scope

In scope:

- Milestone 0 freshness rebaseline for both open claim-support owner cases
- claim-support guardrail and cycle-first gate hardening
- reduction of the three residual `IC-E2270F89B397` owner files
- reduction of the three residual `IC-7C73737C689F` owner files
- direct owner tests for newly extracted claim-support modules
- route-boundary and DB-backed integration verification for the claim-support
  runtime family
- hygiene, improvement-case, architecture index, and session-handoff updates in
  the same closeout windows

Out of scope:

- `app/db/model_domains/claim_support.py`
- `app/services/evidence_claim_support_replay_alerts.py`
- `app/services/technical_reports.py` except for compatibility-preserving call
  sites or targeted tests
- semantic-governance residual owner case `IC-81C531769EB3`
- broader architecture-governance or boring-change coordination work

## Owner Surfaces

- compatibility facades and residual owners already in play:
  `app/services/claim_support_policy_impacts.py`,
  `app/services/claim_support_policy_impact_views.py`,
  `app/services/claim_support_policy_impact_replay.py`,
  `app/services/claim_support_replay_alert_promotions.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`,
  `app/services/claim_support_replay_alert_fixture_corpus.py`
- planned policy-impact owner modules:
  `app/services/claim_support_policy_impact_worklist.py`,
  `app/services/claim_support_policy_impact_alerts.py`,
  `app/services/claim_support_policy_impact_replay_queue.py`,
  `app/services/claim_support_policy_impact_replay_closure.py`,
  `app/services/claim_support_replay_alert_fixture_candidates.py`,
  `app/services/claim_support_replay_alert_promotion_governance.py`
- planned support-family owner modules:
  `app/services/claim_support_evaluation_fixtures.py`,
  `app/services/claim_support_calibration_policies.py`,
  `app/services/claim_support_judge_evaluation_runs.py`,
  `app/services/claim_support_policy_change_impact_governance.py`,
  `app/services/claim_support_policy_activation_governance.py`,
  `app/services/claim_support_replay_alert_fixture_corpus_build.py`,
  `app/services/claim_support_replay_alert_fixture_corpus_governance.py`
- existing adjacent owners that may be called but must not absorb new debt:
  `app/services/claim_support_replay_alert_waivers.py`,
  `app/services/evidence.py`,
  `app/services/semantic_governance.py`,
  `app/services/technical_reports.py`
- route surfaces:
  `app/api/routers/claim_support_policy_impacts.py`,
  `app/api/routers/agent_tasks.py`
- tests:
  `tests/unit/test_claim_support_policy_impacts.py`,
  `tests/unit/test_claim_support_policy_impact_views.py`,
  `tests/unit/test_claim_support_policy_impact_replay.py`,
  `tests/unit/test_claim_support_evaluations.py`,
  `tests/unit/test_claim_support_policy_governance.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`,
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py`,
  `tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
- routing and governance surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- Keep `app/services/claim_support_policy_impacts.py` as the public import
  surface for the policy-impact route family; do not make callers chase internal
  file moves.
- `app/services/claim_support_policy_impact_views.py` should close as a compact
  response and detail owner only. Worklist assembly and alert escalation do not
  belong there after closeout.
- `app/services/claim_support_policy_impact_replay.py` should close as a compact
  replay-entry and integrity owner only. Replay queueing and closure-governance
  bodies do not belong there after closeout.
- `app/services/claim_support_replay_alert_promotions.py` should close as a
  compact public seam only. Candidate derivation and promotion or waiver
  governance must move into named owner modules.
- `app/services/claim_support_evaluations.py` should close as a compatibility
  facade that delegates fixture authoring, calibration policy persistence, and
  judge-evaluation runs into explicit owners.
- `app/services/claim_support_policy_governance.py` should close as a compact
  compatibility surface that delegates change-impact payload work and
  activation-governance payload or receipt work into explicit owners.
- `app/services/claim_support_replay_alert_fixture_corpus.py` should close as a
  compact public seam that delegates corpus build and governance integrity into
  explicit owners; keep only trivial summary or wrapper behavior there if it
  materially reduces fan-in.
- Do not move claim-support logic into `app/services/evidence.py`,
  `app/services/technical_reports.py`, or unrelated agent-action files just to
  satisfy a line budget.
- Remove the direct back-import from
  `app/services/claim_support_replay_alert_promotions.py` into
  `app/services/claim_support_policy_impacts.py`; shared alert or worklist
  behavior should flow through focused owner modules instead.
- Prefer direct owner tests in new focused files such as
  `tests/unit/test_claim_support_policy_impact_alerts.py`,
  `tests/unit/test_claim_support_policy_impact_replay_queue.py`,
  `tests/unit/test_claim_support_evaluation_fixtures.py`, and
  `tests/unit/test_claim_support_policy_activation_governance.py` instead of
  regrowing the existing small facade tests.
- File ceilings after closeout:
  `app/services/claim_support_policy_impact_views.py` <= `350` lines and
  `<= 10` private helpers;
  `app/services/claim_support_policy_impact_replay.py` <= `350` lines and
  `<= 10` private helpers;
  `app/services/claim_support_replay_alert_promotions.py` <= `400` lines and
  `<= 12` private helpers;
  `app/services/claim_support_evaluations.py` <= `300` lines and
  `<= 8` private helpers;
  `app/services/claim_support_policy_governance.py` <= `325` lines and
  `<= 8` private helpers;
  `app/services/claim_support_replay_alert_fixture_corpus.py` <= `300` lines
  and `<= 8` private helpers;
  every new owner module introduced by this plan must close at `<= 600` lines
  and `<= 16` private helpers.
- If Milestone 0 evidence proves one of the named owner families still cannot
  close inside those ceilings without an additional unplanned owner, stop and
  write a fresh standalone follow-on rather than quietly broadening this plan.

## Weak-Point Prevention Contract

Freshness rule: rerun the Milestone 0 baseline commands in the same local
closeout window before coding. If the live line counts, cycle set, or owner
case measurements have drifted, update this plan first.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Policy-impact logic shrinks one file only by spilling into adjacent residual claim-support files or unnamed ad hoc files | claim-support policy-impact owners, support-family owners, staged file set | `uv run docling-system-hygiene-check`, `git diff --stat`, and focused `wc -l` recounts before commit | Any new claim-support service file not named in this plan appears, or an excluded adjacent file gains implementation debt, or any owner still exceeds its declared ceiling after a milestone that claims closure | Add a temporary helper to `app/services/claim_support_policy_governance.py` or an unnamed `claim_support_misc.py` and confirm the closeout gates reject it | A future session sees “claim support” in a helper name and appends it to the nearest large file |
| The live claim-support cycle survives or gets worse while files become smaller on paper | `app/services/claim_support_policy_impacts.py`, `app/services/claim_support_replay_alert_promotions.py`, new policy-impact owner modules | `uv run docling-system-architecture-inspect` and `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 30` | The cycle count rises above the Milestone 0 baseline, or the claim-support cycle still contains `app.services.claim_support_policy_impacts` after the policy-impact case claims resolution | Reintroduce a direct back-import from promotions into the facade and confirm the cycle gate fails | A later session keeps the public facade small by making extracted owners import back through it |
| Replay queueing, closure receipts, alert escalations, or semantic-governance receipts drift while the files are split | `claim_support_policy_impact_*`, `claim_support_replay_alert_*`, integration tests | Targeted unit tests plus `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` claim-support integration gates | Any hash receipt, deduplication key, replay status, or escalation contract changes without matching test evidence | Temporarily remove a replay-plan hash or closure receipt field and confirm unit or integration coverage fails | A future session treats replay closures or escalation receipts as just formatting logic and moves them without integrity coverage |
| Evaluation fixtures, mined failures, or calibration-policy semantics get weaker to make the split pass | `claim_support_evaluations.py` and new evaluation owners | Unit tests for fixture and policy owners plus `tests/integration/test_claim_support_judge_evaluation_roundtrip.py` and `tests/integration/test_claim_support_policy_mined_failures_roundtrip.py` | Hard-case coverage, policy-hash validation, or mined-failure manifest behavior becomes weaker or narrower | Temporarily remove a hard-case requirement or break fixture SHA validation and confirm the coverage fails | A later session simplifies built-in fixtures or policy validation because they seem like test scaffolding |
| Replay-alert fixture corpus snapshots become a soft cache instead of a governed artifact | `claim_support_replay_alert_fixture_corpus.py` and new corpus owner modules | Unit coverage for snapshot integrity plus integration and focused corpus-governance checks | Snapshot rows, receipt hashes, governance events, or artifact linkage can drift without detection | Temporarily break snapshot row hashing or governance receipt hashing and confirm integrity coverage fails | A future session optimizes the corpus builder and stops treating snapshot governance as first-class |
| Registry and docs claim the cases are closed before the live measurements agree | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, `docs/agentic_architecture_index.md`, `docs/SESSION_HANDOFF.md` | `uv run docling-system-improvement-case-validate`, `uv run docling-system-hygiene-check`, `git diff --check`, and docs alignment review | A milestone marks `IC-E2270F89B397` or `IC-7C73737C689F` resolved while their files still exceed the budget or the cycle still exists | Leave a ratchet ceiling or case status unchanged in a controlled draft and confirm alignment review catches it | A future session updates code and tests but forgets to retire the owner cases or refresh the handoff |

## Milestone Sequence

This is a stacked claim-support plan. Each milestone must commit atomically
after verification and docs or handoff updates for that milestone are complete.
Milestones 0 through 6 closed together in local closeout commit `40024a3`
after the focused unit, integration, hygiene, improvement-case, capability,
architecture, hotspot-prevention, and full DB-backed verification stack listed
above.

### Milestone 0 - Freshness Rebaseline And Scope Confirmation

Status: resolved locally through closeout commit `40024a3`
Outcome label: `resolved`

Implementation:

- Rerun the baseline commands from the Current Evidence section.
- Reconfirm the six residual claim-support service line counts and private
  helper counts.
- Reconfirm the live claim-support cycle in the architecture probe.
- Reconfirm that `IC-E2270F89B397` still covers
  `claim_support_policy_impact_views.py`,
  `claim_support_policy_impact_replay.py`, and
  `claim_support_replay_alert_promotions.py`, and that `IC-7C73737C689F` still
  covers `claim_support_evaluations.py`,
  `claim_support_policy_governance.py`, and
  `claim_support_replay_alert_fixture_corpus.py`.
- Update this plan first if any of those facts drift.

Acceptance for this milestone:

- The implementation plan matches the actual starting checkout.
- The remainder of the packet still fits inside the named owner modules and
  ceilings.
- If the work has drifted beyond those ceilings, implementation stops and a new
  standalone follow-on is written.

### Milestone 1 - Claim-Support Guardrails And Cycle Gate

Status: resolved locally through closeout commit `40024a3`
Outcome label: `resolved`

Implementation:

- Extend `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`, and
  `tests/unit/test_hotspot_prevention.py` so claim-support residual growth is
  blocked not only in `claim_support_policy_impacts.py`, but also across the
  residual owner files touched by this packet.
- Add a focused claim-support import or architecture contract check so the
  promotions file can no longer back-import the policy-impact facade after the
  policy-impact case claims closure.
- Add controlled-violation coverage proving the new guardrails fire.

Acceptance for this milestone:

- Claim-support residual additions in the wrong files are blocked by an
  executable gate.
- The controlled-violation coverage fails when reintroduced.
- The cycle-prevention guard exists before broad refactors begin.

### Milestone 2 - Resolve `IC-E2270F89B397` Policy-Impact Residuals

Status: resolved locally through closeout commit `40024a3`
Outcome label: `resolved`

Implementation:

- Reduce `app/services/claim_support_policy_impact_views.py` by moving worklist
  assembly and alert or escalation behavior into focused owner modules such as
  `claim_support_policy_impact_worklist.py` and
  `claim_support_policy_impact_alerts.py`.
- Reduce `app/services/claim_support_policy_impact_replay.py` by moving replay
  queue construction and replay closure or refresh logic into focused owner
  modules such as `claim_support_policy_impact_replay_queue.py` and
  `claim_support_policy_impact_replay_closure.py`.
- Reduce `app/services/claim_support_replay_alert_promotions.py` by moving
  candidate derivation and promotion or waiver governance into focused owner
  modules such as `claim_support_replay_alert_fixture_candidates.py` and
  `claim_support_replay_alert_promotion_governance.py`.
- Remove the direct back-import from promotions into the policy-impact facade by
  routing shared alert behavior through focused owners instead.
- Add direct owner tests for the new policy-impact owners and preserve route or
  integration coverage for the claim-support route family.

Acceptance for this milestone:

- `app/services/claim_support_policy_impact_views.py`,
  `app/services/claim_support_policy_impact_replay.py`, and
  `app/services/claim_support_replay_alert_promotions.py` all close at or below
  the declared ceilings and the repo’s `600`-line target.
- `app/services/claim_support_policy_impacts.py` remains a narrow compatibility
  facade.
- The claim-support cycle containing
  `app.services.claim_support_policy_impacts` is gone from the architecture
  probe.
- `IC-E2270F89B397` can be retired from fresh post-closeout evidence rather
  than remaining merely reduced.

### Milestone 3 - Reduce The Evaluation And Calibration Residual

Status: resolved locally through closeout commit `40024a3`
Outcome label: `reduced`

Implementation:

- Reduce `app/services/claim_support_evaluations.py` by moving fixture authoring
  and mining into `claim_support_evaluation_fixtures.py`, calibration-policy
  persistence into `claim_support_calibration_policies.py`, and judge-evaluation
  runtime and persistence into `claim_support_judge_evaluation_runs.py`.
- Keep `claim_support_evaluations.py` as the public compatibility surface for
  the existing evaluation API and service callers.
- Add direct owner tests for the extracted evaluation families.

Acceptance for this milestone:

- `app/services/claim_support_evaluations.py` closes at or below the declared
  ceiling.
- Every new evaluation owner file is within the repo’s `600`-line target.
- Calibration-policy hashes, fixture-set hashes, mined-failure manifest hashes,
  and claim-support judge results remain stable or better covered.
- `IC-7C73737C689F` is smaller but still open until the governance and corpus
  owners also close.

### Milestone 4 - Reduce The Claim-Support Governance Residual

Status: resolved locally through closeout commit `40024a3`
Outcome label: `reduced`

Implementation:

- Reduce `app/services/claim_support_policy_governance.py` by moving policy
  change-impact payload assembly and persistence into
  `claim_support_policy_change_impact_governance.py`.
- Move activation governance payload, PROV, receipt, and semantic-governance
  event recording into `claim_support_policy_activation_governance.py`.
- Keep `claim_support_policy_governance.py` as a compatibility surface for
  callers that still import through the old module.
- Add direct owner tests covering change-impact and activation-governance
  integrity separately.

Acceptance for this milestone:

- `app/services/claim_support_policy_governance.py` closes at or below the
  declared ceiling.
- Each extracted governance owner is within the repo’s `600`-line target.
- Policy-change impact payload hashes, activation governance receipts, PROV
  payloads, and semantic-governance event contracts remain stable or better
  covered.
- `IC-7C73737C689F` remains open only for the fixture-corpus residual if the
  evaluation owner already closed in Milestone 3.

### Milestone 5 - Resolve The Replay-Alert Fixture Corpus Residual And Retire `IC-7C73737C689F`

Status: resolved locally through closeout commit `40024a3`
Outcome label: `resolved`

Implementation:

- Reduce `app/services/claim_support_replay_alert_fixture_corpus.py` by moving
  corpus build and snapshot activation into
  `claim_support_replay_alert_fixture_corpus_build.py`.
- Move governance receipt creation and integrity checking into
  `claim_support_replay_alert_fixture_corpus_governance.py`.
- Keep only compact public wrappers or summary reads in
  `claim_support_replay_alert_fixture_corpus.py` if that materially preserves
  import stability without exceeding the target ceiling.
- Add direct owner tests for corpus build and governance integrity.

Acceptance for this milestone:

- `app/services/claim_support_replay_alert_fixture_corpus.py` closes at or below
  the declared ceiling.
- Every extracted corpus owner is within the repo’s `600`-line target.
- Snapshot row hashes, governance receipts, governance artifacts, and semantic
  event linkage remain stable or better covered.
- `IC-7C73737C689F` can be retired from fresh post-closeout evidence.

### Milestone 6 - Alignment And Full Claim-Support Closeout

Status: resolved locally through closeout commit `40024a3`
Outcome label: `resolved`

Implementation:

- Refresh `config/hygiene_policy.yaml` with the exact verified ceilings for all
  residual claim-support files and new owner modules touched by this packet.
- Update `config/improvement_cases.yaml` so both
  `IC-E2270F89B397` and `IC-7C73737C689F` record the post-closeout
  measurements and closeout commits, or explicitly remain open only if fresh
  evidence proves a smaller named residual still exists.
- Update this plan, `docs/agentic_architecture_index.md`, and
  `docs/SESSION_HANDOFF.md` with the exact closeout evidence and commit hashes.
- Run the full verification stack below in the same closeout window before the
  final retirement commit.

Acceptance for this milestone:

- Both claim-support owner cases are either retired from fresh evidence or
  rerouted explicitly with a smaller named residual.
- The registry, hygiene ratchets, architecture index, and handoff all agree on
  the same post-closeout state.
- The final closeout does not claim success from stale probe or hygiene output.

## Required Implementation Artifacts

- policy-impact owners:
  `app/services/claim_support_policy_impact_worklist.py`,
  `app/services/claim_support_policy_impact_alerts.py`,
  `app/services/claim_support_policy_impact_replay_queue.py`,
  `app/services/claim_support_policy_impact_replay_closure.py`,
  `app/services/claim_support_replay_alert_fixture_candidates.py`,
  `app/services/claim_support_replay_alert_promotion_governance.py`
- support-family owners:
  `app/services/claim_support_evaluation_fixtures.py`,
  `app/services/claim_support_calibration_policies.py`,
  `app/services/claim_support_judge_evaluation_runs.py`,
  `app/services/claim_support_policy_change_impact_governance.py`,
  `app/services/claim_support_policy_activation_governance.py`,
  `app/services/claim_support_replay_alert_fixture_corpus_build.py`,
  `app/services/claim_support_replay_alert_fixture_corpus_governance.py`
- updated compatibility surfaces:
  `app/services/claim_support_policy_impacts.py`,
  `app/services/claim_support_policy_impact_views.py`,
  `app/services/claim_support_policy_impact_replay.py`,
  `app/services/claim_support_replay_alert_promotions.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`,
  `app/services/claim_support_replay_alert_fixture_corpus.py`
- focused claim-support facade, import, and hotspot-prevention tests plus the
  existing DB-backed claim-support integration slices that cover each extracted
  owner family

## Required Documentation And Handoff Updates

- this plan:
  `docs/claim_support_residual_owner_family_milestone_plan.md`
- prior bounded claim-support plan for context only when final routing changes:
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`
- architecture index:
  `docs/agentic_architecture_index.md`
- canonical handoff:
  `docs/SESSION_HANDOFF.md`
- improvement-case registry:
  `config/improvement_cases.yaml`
- hygiene ratchets:
  `config/hygiene_policy.yaml`
- hotspot-prevention rules:
  `config/hotspot_prevention.yaml`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/claim_support_policy_impacts.py app/services/claim_support_policy_impact_views.py app/services/claim_support_policy_impact_replay.py app/services/claim_support_replay_alert_promotions.py app/services/claim_support_evaluations.py app/services/claim_support_policy_governance.py app/services/claim_support_replay_alert_fixture_corpus.py app/hotspot_prevention_classifier.py tests/unit/test_claim_support_policy_impacts.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_claim_support_evaluations.py tests/unit/test_claim_support_policy_governance.py tests/unit/test_claim_support_policy_imports.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_claim_support_policy_impacts.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_claim_support_evaluations.py tests/unit/test_claim_support_policy_governance.py tests/unit/test_claim_support_policy_imports.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_claim_support_judge_evaluation_roundtrip.py tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 30`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`
- final retirement milestone only:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- The residual policy-impact owners and support-family owners are all at or
  below the configured `600`-line budget.
- `app/services/claim_support_policy_impacts.py` remains a narrow compatibility
  facade and no longer participates in the live claim-support cycle.
- `IC-E2270F89B397` and `IC-7C73737C689F` are retired only when fresh hygiene,
  architecture, and registry evidence all agree.
- Claim-support policy activation, replay, alert escalation, fixture
  promotion, fixture-corpus governance, calibration-policy, and evaluation
  contracts remain stable or better covered.
- No new claim-support owner module is created outside the modules named in
  this plan.
- No tests, gates, or coverage were weakened to achieve green verification.

## Stop Conditions

- Stop if Milestone 0 shows the remaining claim-support owners no longer fit
  inside the named modules and ceilings.
- Stop if closing either owner case would require an unnamed additional owner
  module or a DB schema change that is not separately routed.
- Stop if the claim-support cycle cannot be removed without breaking public
  import stability through `app/services/claim_support_policy_impacts.py`.
- Stop if the only way to pass the packet is to weaken the existing
  claim-support integration gates.
- Stop if docs and registry alignment disagree about whether the cases are
  resolved after the final verification pass.

## Local Commit Closeout Policy

- Commit one milestone at a time only after its verification passes.
- Update the canonical docs and handoff in the same milestone commit as the code
  that completes that milestone.
- Stage only the verified claim-support slice.
- Do not claim either owner case retired until the post-closeout registry,
  hygiene, and architecture evidence agree.

## Residual Risks And Next Routing

- The biggest risk is transforming one large claim-support file into several
  medium-large files that still exceed the `600`-line budget. This plan treats
  that as failure, not success.
- A second risk is closing the file-budget findings while leaving the
  claim-support cycle in place. That is why cycle removal is part of the
  policy-impact milestone rather than an optional cleanup.
- A third risk is preserving behavior only by accident in governance and
  receipt-heavy codepaths. That is why the plan requires both direct owner tests
  and DB-backed claim-support integration runs.
- After this packet resolves locally, the remaining broader coordination brief
  is still `docs/boring_change_architecture_milestone_plan.md`, whose
  Milestone 0 must refresh the live repo state again before taking on any
  remaining cross-domain architecture backlog.
