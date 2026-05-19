# Hotspot Prevention Family Boundary Milestone Plan

Date: 2026-05-16 local / 2026-05-16 UTC
Status: resolved locally in the current checkout through Milestone 3 closeout.
`app/hotspot_prevention_classifier.py` is now a `360` line / `1` private-helper
dispatcher under `IC-6C1B516A3F92`, the classifier family now carries exact
same-milestone ratchets on
`app/hotspot_prevention_claim_support_rules.py` at `436 / 1`,
`app/hotspot_prevention_classifier_service_rules.py` at `384 / 0`,
`app/hotspot_prevention_classifier_boundary_rules.py` at `209 / 0`, and
`app/hotspot_prevention_classifier_support.py` at `571 / 1`, and
`tests/unit/test_hotspot_prevention.py` is now a `595` line / `0`
private-helper root under `IC-15F6E41A9C77` with focused sibling coverage in
`tests/unit/test_hotspot_prevention_family_rules.py` at `318 / 0`,
`tests/unit/test_hotspot_prevention_wrapper_rules.py` at `296 / 0`, and
`tests/unit/hotspot_prevention_test_support.py` at `50 / 2`. The broader
coordination brief is now
`docs/boring_change_architecture_milestone_plan.md`, which must activate the
next fresh bounded packet from the refreshed post-closeout baseline.
Later 2026-05-18 routing evidence reselects the companion test root under
`IC-15F6E41A9C77` as the next bounded packet because
`tests/unit/test_hotspot_prevention.py` has regrown to `653` lines while the
classifier-side owners remain under budget.
Owner context: targeted hotspot-prevention family follow-on after the semantic
lifecycle/read packet closed locally. This packet keeps the next slice inside a
single rule-and-test family instead of opening a giant mixed test backlog or a
cross-cutting app packet.

## Purpose

Reduce the hotspot-prevention family without weakening the enforcement layer it
protects.

The scoped problem is not only line count. The current family mixes two
different kinds of debt:

- `app/hotspot_prevention_classifier.py` has become the fallback sink for many
  closed packet guardrails and now carries too many unrelated rule families in
  one owner.
- `tests/unit/test_hotspot_prevention.py` has become the matching sink for too
  many negative-path and rule-composition assertions, making the family harder
  to evolve even when the classifier behavior stays correct.

This packet exists to split those two surfaces into clearer owner seams while
preserving the rule contract, the strict blocking behavior, and the already
closed packet-specific guardrails.

## Current Evidence

Closeout baseline refreshed from the current local checkout on 2026-05-16
local / 2026-05-16 UTC after the hotspot-prevention family packet resolved
locally:

```text
wc -l \
  app/hotspot_prevention_classifier.py \
  app/hotspot_prevention_claim_support_rules.py \
  app/hotspot_prevention_classifier_service_rules.py \
  app/hotspot_prevention_classifier_boundary_rules.py \
  app/hotspot_prevention_classifier_support.py \
  tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_family_rules.py \
  tests/unit/test_hotspot_prevention_wrapper_rules.py \
  tests/unit/hotspot_prevention_test_support.py
    360 app/hotspot_prevention_classifier.py
    436 app/hotspot_prevention_claim_support_rules.py
    384 app/hotspot_prevention_classifier_service_rules.py
    209 app/hotspot_prevention_classifier_boundary_rules.py
    571 app/hotspot_prevention_classifier_support.py
    595 tests/unit/test_hotspot_prevention.py
    318 tests/unit/test_hotspot_prevention_family_rules.py
    296 tests/unit/test_hotspot_prevention_wrapper_rules.py
     50 tests/unit/hotspot_prevention_test_support.py

python - <<'PY'
from pathlib import Path
for path_str in [
    "app/hotspot_prevention_classifier.py",
    "app/hotspot_prevention_claim_support_rules.py",
    "app/hotspot_prevention_classifier_service_rules.py",
    "app/hotspot_prevention_classifier_boundary_rules.py",
    "app/hotspot_prevention_classifier_support.py",
    "tests/unit/test_hotspot_prevention.py",
    "tests/unit/test_hotspot_prevention_family_rules.py",
    "tests/unit/test_hotspot_prevention_wrapper_rules.py",
    "tests/unit/hotspot_prevention_test_support.py",
]:
    path = Path(path_str)
    count = 0
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("def _") or stripped.startswith("async def _"):
            count += 1
    print(f"{path_str} private_helpers={count}")
PY
  app/hotspot_prevention_classifier.py private_helpers=1
  app/hotspot_prevention_claim_support_rules.py private_helpers=1
  app/hotspot_prevention_classifier_service_rules.py private_helpers=0
  app/hotspot_prevention_classifier_boundary_rules.py private_helpers=0
  app/hotspot_prevention_classifier_support.py private_helpers=1
  tests/unit/test_hotspot_prevention.py private_helpers=0
  tests/unit/test_hotspot_prevention_family_rules.py private_helpers=0
  tests/unit/test_hotspot_prevention_wrapper_rules.py private_helpers=0
  tests/unit/hotspot_prevention_test_support.py private_helpers=2

uv run ruff check app/hotspot_prevention_classifier.py \
  app/hotspot_prevention_classifier_service_rules.py \
  app/hotspot_prevention_classifier_boundary_rules.py \
  app/hotspot_prevention_claim_support_rules.py \
  app/hotspot_prevention_classifier_support.py \
  tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_family_rules.py \
  tests/unit/test_hotspot_prevention_wrapper_rules.py \
  tests/unit/hotspot_prevention_test_support.py
  pass

uv run pytest -q tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_family_rules.py \
  tests/unit/test_hotspot_prevention_wrapper_rules.py
  40 passed

uv run docling-system-hotspot-prevention-check --strict
  changed_hotspots=0
  blocked=0

uv run docling-system-hygiene-check
  new hygiene regressions: none
  hotspot-prevention family no longer appears in inherited budget debt

uv run docling-system-improvement-case-summary
  case_count=49
  status_counts.open=33
  status_counts.deployed=15
  measured_case_count=44

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=496.06

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  27 code files above 800 lines
  hotspot-prevention family no longer appears in the largest-file list
  Python cycle components: 3
```

Current structural evidence:

- `IC-6C1B516A3F92` now governs an exact-ratcheted classifier family: the
  public dispatcher is `360 / 1`, claim-support routes are `436 / 1`,
  source-family routes are `384 / 0`, boundary or wrapper routes are `209 / 0`,
  and shared support helpers are `571 / 1`.
- `IC-15F6E41A9C77` now governs an exact-ratcheted companion test family:
  `tests/unit/test_hotspot_prevention.py` is `595 / 0`, blocked-family
  coverage lives in `tests/unit/test_hotspot_prevention_family_rules.py` at
  `318 / 0`, wrapper or allowance coverage lives in
  `tests/unit/test_hotspot_prevention_wrapper_rules.py` at `296 / 0`, and the
  shared diff or policy helper lives in
  `tests/unit/hotspot_prevention_test_support.py` at `50 / 2`.
- The family is still narrow enough for one packet: classifier rule bodies,
  support siblings, and companion tests now form one coherent owner surface
  without leaving a new oversized sink behind.
- The three live Python cycle components do not currently include this family,
  so this packet is a size and owner-boundary reduction, not a cycle-break
  packet.
- The broader boring-change brief now has cleaner next-packet evidence: the
  closeout removes this family from the 800-line backlog and makes the
  remaining routed debt more clearly test-heavy.

## Goal

Reduce the hotspot-prevention family so that:

- `app/hotspot_prevention_classifier.py` is reduced under the default `600`
  line hygiene budget or split into focused sibling owners with explicit
  routing for any `601-800` residual
- `tests/unit/test_hotspot_prevention.py` is reduced below the
  architecture-probe `800`-line threshold without weakening negative coverage
- the public hotspot-prevention behavior remains unchanged at the rule,
  report, and strict-blocking boundary
- the packet closes with accurate handoff, index, and registry state

## Non-Goals

- No broad rewrite of every historical hotspot rule family.
- No reopening of search, CLI, semantics, agent-task, or evidence packets just
  because some of their guards are represented in this classifier.
- No weakening of controlled-violation coverage, negative-path coverage, or the
  strict blocking behavior to get under a size threshold.
- No local-import or dynamic-rule tricks that hide the same classifier or test
  coupling behind a green line-count result.

## Scope

In scope:

- `app/hotspot_prevention_classifier.py`
- `app/hotspot_prevention_claim_support_rules.py`
- `app/hotspot_prevention_classifier_service_rules.py`
- `app/hotspot_prevention_classifier_boundary_rules.py`
- `app/hotspot_prevention_classifier_support.py`
- `config/hotspot_prevention.yaml`
- `tests/unit/test_hotspot_prevention.py`
- `tests/unit/test_hotspot_prevention_family_rules.py`
- `tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `tests/unit/hotspot_prevention_test_support.py`
- same-milestone owner routing in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`
- packet routing updates in `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md`

Out of scope:

- unrelated large tests such as `tests/unit/test_evaluation_fixtures.py` or
  `tests/integration/test_postgres_roundtrip.py`
- unrelated app-family owners such as `app/services/technical_reports.py` or
  `app/ui/modules/agents.js`
- the three remaining Python cycle components

## Owner Surfaces

- `app/hotspot_prevention_classifier.py`
- `app/hotspot_prevention_claim_support_rules.py`
- `app/hotspot_prevention_classifier_service_rules.py`
- `app/hotspot_prevention_classifier_boundary_rules.py`
- `app/hotspot_prevention_classifier_support.py`
- `config/hotspot_prevention.yaml`
- `tests/unit/test_hotspot_prevention.py`
- `tests/unit/test_hotspot_prevention_family_rules.py`
- `tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `tests/unit/hotspot_prevention_test_support.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `docs/hotspot_prevention_family_boundary_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

## Placement Rules

- Keep rule-family ownership inside the hotspot-prevention family. Do not move
  classifier logic into closed packet facades such as `app/services/search.py`,
  `app/services/semantics.py`, `app/services/evidence.py`, or `app/cli.py`.
- New support helpers belong in focused hotspot-prevention siblings, not inside
  another already-large app service.
- Test decomposition must prefer helper fixtures or focused sibling test files
  over moving bulk assertions into another already-large general test.
- Any residual owner that lands between `601` and `800` lines must receive
  same-milestone routing in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The classifier shrinks only because code moved into another unowned support sink. | `app/hotspot_prevention_classifier.py`, support siblings, hygiene policy | `uv run docling-system-hygiene-check`, staged `wc -l`, architecture probe readback | Any touched sibling regrows above its routed ceiling without same-milestone routing | Move a large rule cluster into a new support file without registry updates and confirm closeout rejects it | A future session "solves" the classifier by dumping rule families into another giant helper |
| Test decomposition reduces lines by weakening negative-path coverage. | `tests/unit/test_hotspot_prevention.py`, focused sibling test files | `uv run pytest -q tests/unit/test_hotspot_prevention.py` plus any new focused sibling tests | Controlled violations, strict blocking checks, or report assertions get weaker than the pre-split contract | Remove one blocked-case assertion while shrinking the file and confirm review blocks the change | A future session optimizes for fewer lines instead of preserving guard behavior |
| Packet work leaks into closed source packets instead of staying in the hotspot-prevention family. | classifier family, touched source facades, handoff/index | staged diff review, focused ruff and pytest slices | The slice edits unrelated closed source packets without a direct hotspot-prevention contract reason | Add a search or semantics behavior edit unrelated to guard ownership and confirm closeout rejects the scope drift | A future session uses this packet as permission to revisit every file named in the rule config |
| Routing drifts and the repo keeps naming the resolved semantic packet as active work. | this packet, boring-change brief, handoff, architecture index, improvement-case registry | routing readback across docs and registry | Active packet names disagree across the plan, handoff, index, or registry | Point the handoff back at the semantic packet and confirm alignment review catches it | A future session starts in the wrong packet because one doc was left behind |

## Milestone Sequence

### Milestone 0 - Fresh Baseline And Owner Lock

Outcome label: reduced

Refresh the hotspot-prevention family baseline, bind the companion test into
owner routing, and freeze the exact packet scope before code changes.
Local status: resolved locally in the current checkout.

### Milestone 1 - Classifier Rule-Family Extraction

Outcome label: reduced

Reduce `app/hotspot_prevention_classifier.py` by extracting one or more
cohesive rule families or report-classification seams into focused sibling
owners while preserving the public classifier entrypoints and policy behavior.
Local status: resolved locally in the current checkout.

### Milestone 2 - Hotspot Prevention Test Decomposition

Outcome label: reduced

Reduce `tests/unit/test_hotspot_prevention.py` below `800` lines by moving
cohesive helper fixtures or focused rule-family assertions into narrower test
owners without weakening the negative-path contract.
Local status: resolved locally in the current checkout.

### Milestone 3 - Closeout, Ratchets, And Residual Routing

Outcome label: resolved

Close the packet by tightening ratchets, refreshing the registry and routing
docs, and proving the family no longer sits in inherited oversized-owner debt.
Local status: resolved locally in the current checkout; the broader
coordination brief must now pick the next bounded packet from the refreshed
baseline.

## Required Implementation Artifacts

- focused classifier-family code changes across the dispatcher, source-family,
  boundary, claim-support, and support siblings
- focused hotspot-prevention test decomposition changes across the root test,
  blocked-family sibling tests, wrapper sibling tests, and shared test support
- refreshed `config/improvement_cases.yaml`
- refreshed `config/hygiene_policy.yaml`
- refreshed `docs/hotspot_prevention_family_boundary_milestone_plan.md`
- refreshed `docs/SESSION_HANDOFF.md`
- refreshed `docs/agentic_architecture_index.md`
- refreshed `docs/boring_change_architecture_milestone_plan.md`

## Required Documentation And Handoff Updates

- record this packet as the latest resolved bounded implementation brief and
  reroute the next active work through the broader coordination brief
- update the handoff and index whenever the packet changes milestone status
- update the broader boring-change brief whenever this packet changes the next
  routed slice

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/hotspot_prevention_classifier.py app/hotspot_prevention_classifier_service_rules.py app/hotspot_prevention_classifier_boundary_rules.py app/hotspot_prevention_claim_support_rules.py app/hotspot_prevention_classifier_support.py tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py tests/unit/hotspot_prevention_test_support.py`
- `uv run pytest -q tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- the classifier root is reduced under `600` lines or any residual `601-800`
  owner is routed in the same milestone
- the hotspot-prevention test root is reduced below `800` lines
- the focused hotspot-prevention baseline remains green without weaker
  negative-path coverage
- the handoff, architecture index, broader boring-change brief, and improvement
  case registry reroute this packet from active work to the latest resolved
  bounded implementation brief and leave the next packet choice to the
  refreshed broader coordination brief

## Stop Conditions

- Stop if the only available reduction path is to weaken guard behavior or
  delete controlled-violation coverage.
- Stop if the next split would require broad unrelated source-packet rewrites.
- Stop and route a fresh follow-on if the family can only be reduced by turning
  one hotspot-prevention sibling into another oversized sink.

## Local Commit Closeout Policy

- Milestone 0 docs-and-routing work must commit only the plan, handoff, index,
  and directly affected registry files if committed separately.
- Every code-changing milestone after Milestone 0 must close as an atomic
  commit including code, tests, registry updates, and routing docs for this
  family only.

## Residual Risks And Next Milestone Routing

- This packet is now the latest resolved bounded implementation brief in the
  current checkout.
- The broader boring-change brief should now remeasure the remaining
  large-test and app/UI backlog and promote exactly one next narrow packet.
- Current evidence favors a fresh residual test-large-owner packet before
  reopening app or UI backlog, because the hotspot-prevention family no longer
  appears in the 800-line queue and the remaining largest-file backlog is now
  led by tests.
- The most likely post-closeout follow-ons remain the larger residual test
  backlog, `app/ui/modules/agents.js`, `app/services/semantic_orchestration.py`,
  `app/services/technical_reports.py`, and the remaining cycle-only work.
