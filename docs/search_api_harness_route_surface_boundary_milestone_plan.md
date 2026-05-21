# Search API Harness Route Surface Boundary Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: proposed in the current checkout after the 2026-05-20 broader
rebaseline rerun reselected `tests/unit/test_search_api_harnesses.py` as the
sole honest broader candidate while `top_routed_hotspot_paths=[]` remained
empty.
Owner context: fresh broader-rebaseline follow-on after the search-harness
service, CLI, cycle, and hotspot-prevention policy closeouts returned the live
routed queue to empty. Earlier search-family packets deliberately left
`tests/unit/test_search_api_harnesses.py` unchanged as inherited residual
debt, so this file is now the selected next packet from fresh measurements
rather than from stale queue notes.

## Purpose

Convert the remaining mixed search API harness test root into a narrow route
smoke surface, move definitions and descriptor, evaluation and release,
retrieval-learning and reranker, and audit and validation receipt contracts
into focused sibling tests, then route the reduced root so future search API
changes do not reconcentrate in one `764`-line owner.

## Current Evidence

- `uv run docling-system-architecture-quality-report --summary` currently
  reports `top_routed_hotspot_paths=[]`,
  `broader_rebaseline_candidate_count=1`, and
  `top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 25`
  currently reports `Python Cycles: None detected` and lists
  `tests/unit/test_search_api_harnesses.py` at `764` lines as the second
  largest repo file after `tests/unit/test_search_replays.py`.
- `tests/unit/test_search_api_harnesses.py` currently contains one monolithic
  happy-path route matrix plus four machine-readable detail error-path tests,
  mixing harness definitions, evaluations, releases and readiness,
  retrieval-learning candidate evaluations, reranker artifacts, audit bundles,
  and validation receipts in one root module.
- The earlier `docs/search_api_route_surface_boundary_milestone_plan.md`,
  `docs/search_harness_facade_boundary_milestone_plan.md`, and
  `docs/search_harness_cli_facade_boundary_milestone_plan.md` packets all kept
  this root unchanged on purpose, so it is inherited search-family debt rather
  than debt transferred by those reductions.

## Goal

- Reduce `tests/unit/test_search_api_harnesses.py` to a narrow compatibility
  and route-registration smoke surface.
- Move concern-specific coverage into focused sibling tests:
  `tests/unit/test_search_api_harness_definitions.py`,
  `tests/unit/test_search_api_harness_evaluations.py`,
  `tests/unit/test_search_api_harness_learning.py`, and
  `tests/unit/test_search_api_harness_audits.py`.
- Register the reduced root in `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`,
  `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md`.

## Non-Goals

- Do not change `app/api/routers/search.py` or
  `app/api/routers/search_learning.py` contracts in this packet.
- Do not reopen `app/services/search_harnesses.py`,
  `app/cli_commands/search_harness.py`, or
  `tests/unit/test_cli_search_harness.py`.
- Do not rewrite replay-only or non-harness search API coverage outside the
  selected harness family.
- Do not weaken machine-readable error-path assertions to make the split pass.

## Scope

- `tests/unit/test_search_api_harnesses.py`
- `tests/unit/test_search_api_harness_definitions.py`
- `tests/unit/test_search_api_harness_evaluations.py`
- `tests/unit/test_search_api_harness_learning.py`
- `tests/unit/test_search_api_harness_audits.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `docs/search_api_harness_route_surface_boundary_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

## Out Of Scope

- `tests/unit/test_search_api.py`
- `tests/unit/test_search_api_replays.py`
- `tests/unit/test_search_api_learning_audit.py`, except for narrow helper
  alignment if the harness split absolutely requires it
- search-harness runtime, reranker, or CLI implementation changes
- unrelated readiness, DB, worker, or UI work

## Owner Surfaces

- Root smoke surface: `tests/unit/test_search_api_harnesses.py`
- Focused definitions and descriptor sibling:
  `tests/unit/test_search_api_harness_definitions.py`
- Focused evaluation, release, and readiness sibling:
  `tests/unit/test_search_api_harness_evaluations.py`
- Focused retrieval-learning candidate and reranker artifact sibling:
  `tests/unit/test_search_api_harness_learning.py`
- Focused audit-bundle and validation-receipt sibling:
  `tests/unit/test_search_api_harness_audits.py`
- Routing and hygiene control surfaces:
  `config/hotspot_prevention.yaml`, `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`

## Placement Rules

- Keep `tests/unit/test_search_api_harnesses.py` as the compatibility root
  that proves the harness route family is registered and callable without
  carrying the full payload matrix.
- Place harness definition listing, descriptor payload assertions, and
  descriptor error-path coverage only in
  `tests/unit/test_search_api_harness_definitions.py`.
- Place harness evaluation post/list/detail plus release list/detail/readiness
  coverage and the corresponding machine-readable error-path assertions only in
  `tests/unit/test_search_api_harness_evaluations.py`.
- Place retrieval-learning candidate evaluation and reranker artifact coverage
  only in `tests/unit/test_search_api_harness_learning.py`.
- Place audit-bundle creation/detail/latest, training-audit creation/latest,
  and validation-receipt list/detail/latest coverage only in
  `tests/unit/test_search_api_harness_audits.py`.
- Keep `tests/unit/test_search_api_learning_audit.py` as its existing owner;
  do not use it as an overflow sink for moved harness-route coverage.
- Preserve the public root module name
  `tests/unit/test_search_api_harnesses.py` so existing docs and tooling keep
  resolving the family correctly.

## Weak-Point Prevention Contract

- Weak point forecast: the split could shrink the root but clone the current
  broad route matrix into multiple medium-sized siblings instead of creating
  real concern boundaries.
  Owner surface: the four new sibling tests and any new family-local support
  helper.
  Prevention gate: focused `ruff` and `pytest` over the entire harness test
  family plus manual line-count review in the final diff.
  Fail threshold: any new sibling exceeds the default `600`-line budget or
  duplicates large end-to-end payload scaffolding without a narrower ownership
  reason.
  Controlled violation: the pre-milestone root already demonstrates the
  oversized matrix failure mode.
  Future-Codex misuse scenario: a future session copies the same payload setup
  into each new file because the root shrink looked sufficient on paper.

- Weak point forecast: the split could reopen already reduced search-harness
  service or CLI facades by moving helper logic sideways instead of keeping the
  packet test-local.
  Owner surface: `app/services/search_harnesses.py`,
  `app/cli_commands/search_harness.py`, and
  `tests/unit/test_cli_search_harness.py`.
  Prevention gate: post-split `docling-system-architecture-quality-report
  --summary` plus the focused harness-family `pytest` slice.
  Fail threshold: a reduced facade regrows materially, or a previously closed
  search-harness service or CLI root reappears in `top_routed_hotspot_paths`.
  Controlled violation: none; if the split requires service or CLI rewrites,
  stop and re-plan.

- Weak point forecast: harness-route debt could be pushed into
  `tests/unit/test_search_api.py` or `tests/unit/test_search_api_learning_audit.py`
  instead of staying inside new focused harness siblings.
  Owner surface: the existing search API siblings and the new harness sibling
  modules.
  Prevention gate: focused `ruff` and `pytest` over the search API family plus
  post-split architecture-quality review.
  Fail threshold: adjacent established siblings regrow materially without
  owning the moved route families, or
  `tests/unit/test_search_api_harnesses.py` still remains the broader
  candidate after the split.
  Controlled violation: the earlier packets intentionally left this root
  unchanged; that history cannot justify new spillover.

- Weak point forecast: the docs could mention the selected packet while
  hotspot, hygiene, or improvement metadata stays stale, leaving the reduced
  root unguided after the actual split.
  Owner surface: `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`, and the
  architecture docs named in Scope.
  Prevention gate: `uv run docling-system-hotspot-prevention-check --strict`,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-improvement-case-validate`, and a direct handoff/index
  consistency read.
  Fail threshold: missing exact ratchets, missing owner-case linkage, or docs
  that still point only to the raw broader-rebaseline metric instead of the
  selected packet.
  Controlled violation: the current pre-implementation state intentionally has
  a selected packet without a reduced-facade route yet; the implementation
  closeout must remove that gap.

## Milestone Sequence

1. Gate and packet refresh.
   Outcome label: resolved
   Reconfirm the live broader-rebaseline evidence, map the monolithic root by
   concern, and lock the focused sibling names and ownership boundaries before
   edits begin.

2. Root reduction and definitions/evaluations extraction.
   Outcome label: resolved
   Keep `tests/unit/test_search_api_harnesses.py` as a narrow smoke surface
   and move definitions/descriptor plus evaluation/release/readiness contracts
   into focused siblings.

3. Learning and audit extraction.
   Outcome label: resolved
   Move retrieval-learning candidate evaluation, reranker artifact, audit
   bundle, training audit, and validation receipt coverage into focused
   siblings without reopening adjacent search API owners.

4. Routing and closeout alignment.
   Outcome label: resolved
   Route the reduced root in hotspot prevention, exact-ratchet the new files,
   refresh improvement-case metadata, and update the plan, handoff, index, and
   broader brief to the live post-split state.

## Required Implementation Artifacts

- Reduced `tests/unit/test_search_api_harnesses.py`
- New focused sibling tests named in Scope
- Family-local shared support only if repeated payload helpers cannot stay
  readable inline and the support remains private to this harness test family
- Routed hotspot-prevention, hygiene, and improvement-case metadata for the
  reduced root and new siblings

## Required Documentation And Handoff Updates

- `docs/search_api_harness_route_surface_boundary_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check tests/unit/test_search_api.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_harness_definitions.py tests/unit/test_search_api_harness_evaluations.py tests/unit/test_search_api_harness_learning.py tests/unit/test_search_api_harness_audits.py tests/unit/test_search_api_learning_audit.py`
- `uv run pytest -q tests/unit/test_search_api.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_harness_definitions.py tests/unit/test_search_api_harness_evaluations.py tests/unit/test_search_api_harness_learning.py tests/unit/test_search_api_harness_audits.py tests/unit/test_search_api_learning_audit.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`

## Acceptance Criteria

- `tests/unit/test_search_api_harnesses.py` closes as a narrow compatibility
  and route-registration smoke surface instead of a mixed payload matrix root.
- Definitions and descriptor, evaluation and release, learning and reranker,
  and audit and validation receipt coverage each live in focused sibling test
  modules with no concern overlap.
- `config/hotspot_prevention.yaml` routes the reduced root as a deferred
  reduced facade toward the new focused sibling tests, and
  `config/hygiene_policy.yaml` exact-ratchets the reduced root plus the new
  sibling files.
- `uv run docling-system-architecture-quality-report --summary` no longer
  surfaces `tests/unit/test_search_api_harnesses.py` in
  `top_broader_rebaseline_paths` and does not reopen reduced search service or
  CLI facades in `top_routed_hotspot_paths`.
- The plan, handoff, index, and broader coordination brief all describe the
  live post-split routing state rather than only the raw broader-rebaseline
  metric.

## Stop Conditions

- Stop if isolating the file requires route, service, or CLI behavior changes
  rather than bounded test redistribution and routing metadata updates.
- Stop if more than one new sibling would still exceed the default `600`-line
  budget without a clearly bounded family-local support extraction.
- Stop if the packet can only pass by weakening machine-readable error-path
  assertions or dropping release, audit, or validation-receipt coverage.
- Stop if the debt-shift audit shows material regrowth in
  `tests/unit/test_search_api.py`,
  `tests/unit/test_search_api_learning_audit.py`, or the reduced
  search-harness service or CLI facades.

## Local Commit Closeout Policy

Close out as one atomic local milestone commit containing the reduced root,
focused sibling tests, routing and hygiene metadata, improvement-case updates,
and required docs and handoff changes only after the verification gates pass.
Do not bundle unrelated readiness, runtime, or non-search work into the same
commit.
