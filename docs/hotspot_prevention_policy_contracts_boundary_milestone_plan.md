# Hotspot Prevention Policy Contracts Boundary Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: resolved locally in the current checkout on 2026-05-20
Owner context: bounded follow-on for the currently active architecture-quality
owner surface `tests/unit/test_hotspot_prevention_policy_contracts.py` after
the earlier hotspot-prevention family packet reduced
`tests/unit/test_hotspot_prevention.py` but left the policy-contract sibling
unrouted and regrown.

## Purpose

Reduce the mixed hotspot-prevention policy-contract test root into a narrow
smoke surface, move policy validation, report and CLI behavior, diff-collector
coverage, and packaging checks into focused sibling tests, then route the
reduced root as a deferred facade so the architecture-quality queue stops
reopening an already-split family.

## Current Evidence

- `uv run docling-system-architecture-quality-report --summary` currently
  selects `tests/unit/test_hotspot_prevention_policy_contracts.py` as
  `top_routed_hotspot_paths=["tests/unit/test_hotspot_prevention_policy_contracts.py"]`
  with `broader_rebaseline_candidate_count=0`.
- `tests/unit/test_hotspot_prevention_policy_contracts.py` currently mixes
  live-policy loading, policy payload validation, report and CLI assertions,
  git diff collector wiring, and pyproject packaging coverage in one root
  file.
- `config/hotspot_prevention.yaml` currently routes
  `tests/unit/test_hotspot_prevention.py` as a reduced facade but does not
  register `tests/unit/test_hotspot_prevention_policy_contracts.py` as a
  routed hotspot, so the live queue reopens the companion test family despite
  the earlier docs claiming it was already reduced.

## Goal

- Reduce `tests/unit/test_hotspot_prevention_policy_contracts.py` to a narrow
  smoke and compatibility surface.
- Move concern-specific assertions into focused sibling tests:
  `test_hotspot_prevention_policy_validation.py`,
  `test_hotspot_prevention_report_cli.py`,
  `test_hotspot_prevention_diff_collectors.py`, and
  `test_hotspot_prevention_packaging.py`.
- Register the reduced root in `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`, `docs/boring_change_architecture_milestone_plan.md`,
  and `docs/SESSION_HANDOFF.md`.

## Non-Goals

- Do not broaden scope into unrelated search-harness or broader cycle work.
- Do not rewrite hotspot-prevention runtime logic beyond the test and routing
  surfaces needed for this packet.
- Do not weaken negative-path or controlled-violation assertions to force a
  green result.

## Scope

- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `tests/unit/test_hotspot_prevention_policy_validation.py`
- `tests/unit/test_hotspot_prevention_report_cli.py`
- `tests/unit/test_hotspot_prevention_diff_collectors.py`
- `tests/unit/test_hotspot_prevention_packaging.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `docs/hotspot_prevention_policy_contracts_boundary_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

## Out Of Scope

- `app/services/search_harness_*`
- `tests/unit/test_search_api_harnesses.py`
- unrelated runtime, DB, API, or worker changes

## Owner Surfaces

- Root smoke surface: `tests/unit/test_hotspot_prevention_policy_contracts.py`
- Focused policy-validation sibling:
  `tests/unit/test_hotspot_prevention_policy_validation.py`
- Focused report and CLI sibling:
  `tests/unit/test_hotspot_prevention_report_cli.py`
- Focused git-diff collector sibling:
  `tests/unit/test_hotspot_prevention_diff_collectors.py`
- Focused packaging sibling:
  `tests/unit/test_hotspot_prevention_packaging.py`
- Routing and hygiene control surfaces:
  `config/hotspot_prevention.yaml`, `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`

## Placement Rules

- Keep `tests/unit/test_hotspot_prevention_policy_contracts.py` as the
  compatibility root that proves the live hotspot policy still exposes the
  expected governed surfaces and routing metadata.
- Place policy payload validation failures only in
  `tests/unit/test_hotspot_prevention_policy_validation.py`.
- Place report payload, numstat, exception-allowance, and CLI exit-path checks
  only in `tests/unit/test_hotspot_prevention_report_cli.py`.
- Place git diff and numstat subprocess wiring checks only in
  `tests/unit/test_hotspot_prevention_diff_collectors.py`.
- Place pyproject script exposure checks only in
  `tests/unit/test_hotspot_prevention_packaging.py`.
- Preserve the public test module names already referenced by repo docs; do not
  rename the existing root file.

## Weak-Point Prevention Contract

- Weak point forecast: the split could leave the reduced root unregistered, so
  raw hotspot ordering would keep reopening the same test surface.
  Owner surface: `config/hotspot_prevention.yaml`
  Prevention gate: `uv run docling-system-architecture-quality-report --summary`
  Fail threshold: the root still appears in `top_routed_hotspot_paths`.
  Controlled violation: the pre-milestone state already demonstrates this
  failure mode.
  Future-Codex misuse scenario: a future session adds more policy validation or
  CLI behavior back to the root file because it still looks like the official
  hotspot policy test. Routing metadata must point that work to focused
  siblings instead.

- Weak point forecast: the split could weaken negative-path or controlled
  validation coverage while shrinking the root file.
  Owner surface: `tests/unit/test_hotspot_prevention_policy_validation.py` and
  `tests/unit/test_hotspot_prevention_report_cli.py`
  Prevention gate: focused `pytest` slice over the hotspot-prevention family
  tests.
  Fail threshold: any moved validation or CLI/report assertion disappears
  without equivalent or stronger sibling coverage.
  Controlled violation: invalid policy payloads and strict CLI exit behavior
  must still fail exactly as before.

- Weak point forecast: the new sibling files could become unguided growth sinks.
  Owner surface: `config/hygiene_policy.yaml` and `config/improvement_cases.yaml`
  Prevention gate: `uv run docling-system-hygiene-check` and
  `uv run docling-system-improvement-case-validate`
  Fail threshold: missing ratchets, missing owner case linkage, or stale
  improvement-case routing.
  Controlled violation: hygiene or improvement-case validation should fail if
  the new files are not registered.

## Milestone Sequence

1. Gate and packet refresh.
   Outcome label: resolved
   Refresh the durable packet, record the live routed-hotspot evidence, and
   define the focused owner split before code movement.

2. Root reduction and sibling extraction.
   Outcome label: resolved
   Move policy validation, report and CLI behavior, diff-collector wiring, and
   packaging checks into focused sibling tests while keeping the root as a
   narrow policy-load and routing smoke surface.

3. Routing and closeout alignment.
   Outcome label: resolved
   Register the reduced root as a deferred reduced facade, exact-ratchet the
   new sibling files, refresh the improvement-case registry, and update the
   architecture handoff and index to the live post-split state.

## Required Implementation Artifacts

- Reduced `tests/unit/test_hotspot_prevention_policy_contracts.py`
- New focused sibling test files named in Scope
- Routed hotspot policy entry for the reduced root
- Hygiene policy ratchets for the reduced root and new siblings
- Improvement-case registry entry and updated family notes

## Required Documentation And Handoff Updates

- `docs/hotspot_prevention_policy_contracts_boundary_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_policy_contracts.py tests/unit/test_hotspot_prevention_policy_validation.py tests/unit/test_hotspot_prevention_report_cli.py tests/unit/test_hotspot_prevention_diff_collectors.py tests/unit/test_hotspot_prevention_packaging.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py tests/unit/hotspot_prevention_test_support.py`
- `uv run pytest -q tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_policy_contracts.py tests/unit/test_hotspot_prevention_policy_validation.py tests/unit/test_hotspot_prevention_report_cli.py tests/unit/test_hotspot_prevention_diff_collectors.py tests/unit/test_hotspot_prevention_packaging.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- `tests/unit/test_hotspot_prevention_policy_contracts.py` closes as a narrow
  compatibility and live-policy smoke surface with routing metadata assertions.
- Policy payload validation failures, report and CLI assertions, diff-collector
  wiring, and packaging checks each live in focused sibling files instead of
  the root.
- `config/hotspot_prevention.yaml` routes the reduced root as a deferred
  reduced facade toward the new sibling tests.
- `uv run docling-system-architecture-quality-report --summary` no longer
  selects `tests/unit/test_hotspot_prevention_policy_contracts.py` in
  `top_routed_hotspot_paths`.
- `uv run docling-system-hygiene-check` reports no new hygiene regressions and
  the new sibling files are ratcheted to their measured sizes.
- Durable docs and handoff artifacts describe the live post-split routing state
  instead of the stale queue-empty search-harness snapshot.

## Stop Conditions

- Stop if the split requires changing hotspot-prevention runtime behavior rather
  than only redistributing test coverage and routing metadata.
- Stop if the new sibling surfaces would exceed the default 600-line hygiene
  budget.
- Stop if closeout would require broad unrelated search-harness or runtime
  edits instead of a bounded hotspot-prevention family slice.

## Local Commit Closeout Policy

Close out as one atomic local milestone commit containing the reduced root,
focused sibling tests, routing and hygiene metadata, improvement-case updates,
and the required docs and handoff changes only after the verification gates
pass for this slice.

## Residual Risks And Next Routing

- If the routed queue clears after this packet, the next code-owning selection
  must come from a fresh live architecture-quality rebaseline rather than from
  the stale broader-rebaseline notes in the current handoff.
- The separate search-harness import cycle is outside this packet unless the
  verification stack proves it is newly affected by this work.

## Closeout State

- `tests/unit/test_hotspot_prevention_policy_contracts.py` now closes at
  `21 / 0` as the live-policy and routing smoke root.
- Focused sibling tests now carry the moved coverage at:
  `tests/unit/test_hotspot_prevention_policy_validation.py = 164 / 0`,
  `tests/unit/test_hotspot_prevention_report_cli.py = 123 / 0`,
  `tests/unit/test_hotspot_prevention_diff_collectors.py = 40 / 0`, and
  `tests/unit/test_hotspot_prevention_packaging.py = 10 / 0`.
- Shared hotspot-prevention support now closes at
  `tests/unit/hotspot_prevention_test_support.py = 133 / 2`.
- `config/hotspot_prevention.yaml` now routes the reduced root as a
  deferred reduced facade under `IC-B1FD75CDA84F`.
- `uv run docling-system-architecture-quality-report --summary` now reports
  `top_routed_hotspot_paths=[]` and
  `top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`,
  so the active queue is empty again and the next honest broader-rebaseline
  candidate returns to the search-harness test owner.

## Verification Results

- `git diff --check`
- `uv run ruff check tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_policy_contracts.py tests/unit/test_hotspot_prevention_policy_validation.py tests/unit/test_hotspot_prevention_report_cli.py tests/unit/test_hotspot_prevention_diff_collectors.py tests/unit/test_hotspot_prevention_packaging.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py tests/unit/hotspot_prevention_test_support.py`
- `uv run pytest -q tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_policy_contracts.py tests/unit/test_hotspot_prevention_policy_validation.py tests/unit/test_hotspot_prevention_report_cli.py tests/unit/test_hotspot_prevention_diff_collectors.py tests/unit/test_hotspot_prevention_packaging.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
