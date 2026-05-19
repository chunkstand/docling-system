# Cross-Cutting Verification Roots Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally in the current checkout through the 2026-05-18
verification-root closeout. The parent packet and documents-service sink are
already resolved locally, and this packet now closes the remaining
cross-cutting verification roots to the default `<=600` budget without
creating a new support sink.
Owner context: narrower verification-boundary packet for the remaining
cross-cutting large or high-cost verification roots under `IC-6C3E1A7B9D52`.
The parent cross-cutting packet is already resolved locally, and the adjacent
architecture-governance pair under `IC-08C078FD4F45` is explicitly out of
scope.

## Purpose

Resolve the mechanically expensive mixed-scenario verification roots without
turning this into another vague repo-wide test cleanup packet.

The current weakness is not missing coverage. The repo has strong contract and
integration verification. The problem is that several high-value verification
families still live in broad roots that are hard to reason about, slow to
change safely, and easy to regress through unrelated broad edits.

This packet exists to decompose the selected verification roots into
family-local siblings or support while preserving or strengthening the exact
behavior they prove today.

## 2026-05-18 Closeout Update

- The selected roots now measure `324`, `331`, `540`, `269`, and `437` lines
  across `tests/unit/test_agent_task_verifications.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/unit/test_docling_parser.py`,
  `tests/integration/test_search_harness_releases.py`, and
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`.
- New family-local siblings and support now carry the moved scenario families:
  `tests/unit/test_agent_task_verifications_drafts.py` at `567`,
  `tests/integration/test_postgres_roundtrip_semantics.py` at `503`,
  `tests/integration/test_postgres_roundtrip_failures.py` at `181`,
  `tests/unit/test_docling_parser_logical_tables.py` at `160`,
  `tests/unit/test_docling_parser_table_supplements.py` at `391`,
  `tests/integration/test_search_harness_release_readiness.py` at `224`,
  `tests/integration/test_claim_support_policy_activation_waivers.py` at `349`,
  `tests/integration/test_claim_support_policy_activation_retired_identity.py`
  at `85`, with family-local support reuse in
  `tests/unit/agent_task_verification_support.py` at `328`,
  `tests/integration/postgres_roundtrip_support.py` at `159`, and
  `tests/integration/search_harness_release_support.py` at `242` plus
  `tests/integration/search_harness_release_audit_support.py` at `296`.
- No selected root exceeds `600` lines, and no new family-local support file
  exceeds `400`.
- The focused unit slice passed at `28 passed`, and the DB-backed integration
  slice passed at `19 passed`, so this packet now closes as a verified
  cross-cutting reduction rather than a further narrowing backlog item.
- Final closeout reruns also stayed green after the semantic-pass import-edge
  fix: `git diff --check` passed, the cycle-focused import gate passed at
  `6 passed`, `uv run docling-system-improvement-case-validate` returned
  `valid=true`, `uv run docling-system-hygiene-check` reported
  `new hygiene regressions: none`, `uv run docling-system-architecture-quality-report --summary`
  kept `max_hotspot_risk_score=491.06` at this packet's own closeout point,
  and the architecture probe now reports `0` Python cycle components with
  `0` code files above `800`. Later broader queue closeouts lowered the live
  summary to `486.06` without reopening this verification packet.

## Current Evidence

- Live `wc -l` on 2026-05-18 in the current dirty checkout now measures:
  `tests/unit/test_agent_task_verifications.py` at `324`,
  `tests/integration/test_postgres_roundtrip.py` at `331`,
  `tests/unit/test_docling_parser.py` at `540`,
  `tests/integration/test_search_harness_releases.py` at `269`, and
  `tests/integration/test_claim_support_policy_activation_roundtrip.py` at
  `437`.
- Those live counts already differ from the broader review snapshot that named
  `tests/unit/test_docling_parser.py` at `1080` and
  `tests/integration/test_claim_support_policy_activation_roundtrip.py` at
  `827`. Execute this packet only from a fresh Milestone 0 rebaseline, not from
  stale earlier counts.
- `config/hygiene_policy.yaml` now exact-ratchets the selected roots plus the
  newly added parser, search-harness, and claim-support siblings or support
  under `IC-6C3E1A7B9D52`, so the packet does not simply move scenario load
  into a new ungoverned owner.
- `docs/cross_cutting_large_file_residual_milestone_plan.md` already routes the
  selected verification roots as the remaining mixed service or verification
  family after the documents-service sink.
- The final split leaves the selected roots focused:
  `tests/unit/test_docling_parser.py` now carries parser conversion and fallback
  behavior while logical-table construction lives in
  `tests/unit/test_docling_parser_logical_tables.py`;
  `tests/integration/test_search_harness_releases.py` now carries release and
  audit-bundle coverage while readiness assessment lives in
  `tests/integration/test_search_harness_release_readiness.py`; and
  `tests/integration/test_claim_support_policy_activation_roundtrip.py` now
  carries the core promotion and stale-draft guards while waiver behavior lives
  in `tests/integration/test_claim_support_policy_activation_waivers.py`.
- The selected roots are already cited by other bounded packets as durable proof
  points. This packet must therefore update downstream verification commands,
  handoffs, and routed docs when scenario ownership moves; otherwise the repo
  will keep running stale single-file commands after the split.
- The current worktree is broadly dirty with active local implementation work,
  and related support siblings already exist in the checkout. Milestone 0 must
  stop if the selected roots are already changing in a conflicting way that
  cannot be separated safely from this packet.

## Goal

Resolve the selected verification-root debt so that:

- each selected root closes at or below the default `600`-line hygiene target
- each root becomes a narrow manifest or family-local suite rather than a
  multi-concern monolith
- domain- or scenario-specific cases move into focused siblings instead of a
  new generic support sink
- any new focused sibling between `401` and `600` lines receives same-milestone
  routing and an exact hygiene budget
- any new support file stays at or below `400` lines and remains family-local
- every verification command, plan, and handoff that previously assumed one big
  root is updated to run the narrowed root plus its new focused siblings
- coverage remains equivalent or stronger than today across the focused unit and
  DB-backed integration slices

The scoped issue is `resolved` when the selected roots no longer collapse
multiple concern families into one file, no selected root exceeds `600` lines,
and the governing verification commands and docs point at the new file set
rather than stale monolith paths.

## Non-Goals

- No service-boundary refactor of `app/services/documents.py`,
  `app/services/improvement_cases.py`, or the broader governance pair.
- No reopening of already-resolved DB-model, evaluation, UI, semantic/report,
  or documents-service packets.
- No parser, claim-support, search, or agent-task production-code rewrite
  unless Milestone 0 proves a test split is impossible without a direct
  same-scope contract fix.
- No new generic `tests/helpers.py`, broad `conftest.py` sink, or catch-all
  `tests/support.py`.
- No weakening of assertions, skips, xfails, fixture fidelity, or DB-backed
  integration coverage just to achieve smaller file sizes.
- No treating the stale `docs/shared_verification_roots_milestone_plan.md`
  packet as the implementation brief for this scope; that older packet targets
  different roots and must remain historical unless a later rebaseline selects
  it again.

## Scope

In scope:

- `tests/unit/test_agent_task_verifications.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/unit/test_docling_parser.py`
- `tests/integration/test_search_harness_releases.py`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py`
- focused new siblings such as
  `tests/unit/test_agent_task_verifications_*.py`,
  `tests/integration/test_postgres_roundtrip_*.py`,
  `tests/unit/test_docling_parser_*.py`,
  `tests/integration/test_search_harness_releases_*.py`, and
  `tests/integration/test_claim_support_policy_activation_*.py`
- family-local support files created specifically for the selected roots, for
  example `tests/unit/*_support.py` or `tests/integration/*_support.py` files
  whose names stay local to the selected verification family
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` if new
  siblings between `401` and `600` lines require same-milestone routing
- the routed docs and handoff artifacts that must change when verification
  commands stop being single-file invocations

Out of scope:

- `app/services/documents.py`
- `app/services/improvement_cases.py`
- `tests/unit/test_improvement_case_intake.py`
- the stale shared verification packet rooted in
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`, and
  `tests/unit/test_evaluation_fixtures.py`
- the final zero-oversized closeout owned by
  `docs/residual_large_file_backlog_milestone_plan.md`

## Owner Surfaces

- the five selected verification roots
- any focused sibling suites created by this packet
- any family-local support files created by this packet
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` when new
  siblings need routing
- milestone docs, handoff docs, and plan references whose verification commands
  must be updated to the new file set

## Placement Rules

- Keep agent-task verification cases in
  `tests/unit/test_agent_task_verifications_*.py` or equivalent
  agent-task-local siblings, not in `tests/unit/test_agent_tasks.py` or
  production service modules.
- Keep parser fallback, logical-table, and supplement-overlay cases in
  parser-local siblings such as `tests/unit/test_docling_parser_*.py`, not in
  generic support files or unrelated semantics roots.
- Keep DB-backed document, search, semantic, and failure-path integration
  scenarios split into family-local
  `tests/integration/test_postgres_roundtrip_*.py` siblings rather than moving
  them into search, semantics, or documents-service packets ad hoc.
- Keep search-harness release coverage in search-harness-local integration
  siblings, not in `tests/integration/test_postgres_roundtrip.py`.
- Keep claim-support activation flows in claim-support-local integration
  siblings, not in the search-harness or generic policy-impact roots.
- Preserve the selected root filenames as narrow shared manifests or
  high-signal suites where helpful, but update every affected verification
  command or doc when coverage moves into new siblings.
- Do not create a generic cross-family support file. Any support file must be
  named for one selected family and may not exceed `400` lines.
- Any new focused sibling between `401` and `600` lines must receive
  same-milestone routing and an exact hygiene ratchet. No new focused sibling
  may exceed `600` lines.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A selected root gets smaller only because cases were deleted, assertions weakened, or failure paths dropped. | selected verification roots and new siblings | focused unit or integration slices plus command-inventory review | line count drops while scenario count or assertion fidelity shrinks | replace a real scenario block with a smoke assertion and confirm focused tests or review fail | future Codex optimizes for file size instead of contract fidelity |
| The split creates a new generic support sink or just moves the monolith one file over. | new sibling suites, new `*_support.py`, `config/hygiene_policy.yaml` | `wc -l` readback, hygiene check, architecture probe | any new support file exceeds `400` or any new sibling exceeds `600` without routing | dump shared helpers into a broad `tests/support.py` or a 700-line sibling and confirm closeout rejects it | future Codex uses “support” as a loophole to hide the same debt |
| Verification commands and routed docs drift after scenarios move into siblings. | milestone docs, handoff docs, verification commands, root files | `git diff --check`, doc review, focused rerun commands copied from updated docs | docs still point at stale single-file commands that no longer run the full moved coverage | leave one milestone doc invoking only the old root and confirm review rejects the packet | a later session trusts the old command list and silently skips moved cases |
| Domain-specific scenarios are relocated into the wrong nearby family. | selected roots and new siblings | focused family-local test slices, scope review, routing review | search-harness, claim-support, parser, agent-task, or DB-backed roundtrip cases end up in the wrong family | move claim-support activation cases into `test_postgres_roundtrip.py` or parser supplement cases into a generic root and confirm review rejects it | future Codex chooses the nearest large test file rather than the correct family |
| The queued packet is activated on stale measurements or while overlapping documents-service work is still unresolved. | this plan, `docs/documents_service_boundary_milestone_plan.md`, selected roots, worktree state | Milestone 0 rebaseline, `git status -sb`, fresh `wc -l` readback | root set or overlapping edits differ materially from the drafted baseline | try to start the packet before reconciling the dirty overlapping checkout and confirm the plan stops | a future session resumes from old prose and edits the wrong roots in parallel |

## Milestone Sequence

### Milestone 0. Rebaseline And Command Inventory Lock
Outcome label: reduced

Refresh the live line counts, overlapping local edits, and downstream command
inventory for the selected verification family before code motion begins.

This milestone must:

- remeasure the five selected roots with fresh `wc -l`
- confirm whether `docs/documents_service_boundary_milestone_plan.md` has
  already closed or still overlaps the selected roots
- inventory every routed doc, handoff, or plan command that currently invokes
  the selected roots directly
- confirm which selected roots are still above `800` and which already sit in
  the `601-800` residual band
- stop if conflicting local edits cannot be separated safely

### Milestone 1. Unit Verification Root Split
Outcome label: reduced

Reduce `tests/unit/test_agent_task_verifications.py` and the remaining
high-cost `tests/unit/test_docling_parser.py` into focused family-local
siblings or support while keeping assertion fidelity equal or stronger.

Preferred targets include:

- `tests/unit/test_agent_task_verifications_search_harness.py`
- `tests/unit/test_agent_task_verifications_semantic_registry.py`
- `tests/unit/test_agent_task_verifications_semantic_grounding.py`
- `tests/unit/test_docling_parser_*.py`
- `tests/unit/test_docling_parser_table_supplements.py` if the live rebaseline
  confirms that table-supplement coverage is already separating cleanly

### Milestone 2. Integration Verification Root Split
Outcome label: reduced

Reduce `tests/integration/test_postgres_roundtrip.py`,
`tests/integration/test_search_harness_releases.py`, and
`tests/integration/test_claim_support_policy_activation_roundtrip.py` into
focused family-local siblings or support while preserving DB-backed contract
coverage.

Preferred targets include:

- `tests/integration/test_postgres_roundtrip_document_lifecycle.py`
- `tests/integration/test_postgres_roundtrip_semantics.py`
- `tests/integration/test_postgres_roundtrip_failure_paths.py`
- `tests/integration/test_search_harness_releases_*.py`
- `tests/integration/test_claim_support_policy_activation_*.py`

### Milestone 3. Verification Command And Routing Alignment
Outcome label: reduced

Update every routed verification command, plan, and handoff that depended on a
single selected root so the durable docs invoke the narrowed root plus its new
siblings explicitly.

This milestone must also add same-milestone routing for any new `401-600` line
siblings created by Milestones 1 or 2.

### Milestone 4. Closeout
Outcome label: resolved

Close the packet only after:

- every selected verification root is at or below `600` lines
- no new sibling exceeds `600` lines
- no new support file exceeds `400` lines
- focused unit and DB-backed integration gates are green
- affected docs and handoff artifacts now run the correct narrowed file set

## Required Implementation Artifacts

- narrowed selected verification roots
- focused sibling suites for the moved scenario families
- any family-local support files needed to keep repeated setup readable without
  creating a new sink
- refreshed routing config for any new `401-600` siblings
- updated doc or handoff command lists that point at the narrowed file set

## Required Documentation And Handoff Updates

- `docs/cross_cutting_verification_roots_milestone_plan.md`
- `docs/cross_cutting_large_file_residual_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- `docs/shared_verification_roots_milestone_plan.md` only if its stale status or
  routing note must be clarified to avoid confusion with this packet

## Required Verification Gates

- `git diff --check`
- `uv run ruff check tests/unit/test_agent_task_verifications.py tests/unit/test_agent_task_verifications_drafts.py tests/unit/agent_task_verification_support.py tests/unit/test_docling_parser.py tests/unit/test_docling_parser_logical_tables.py tests/unit/test_docling_parser_table_supplements.py tests/integration/test_postgres_roundtrip.py tests/integration/test_postgres_roundtrip_semantics.py tests/integration/test_postgres_roundtrip_failures.py tests/integration/postgres_roundtrip_support.py tests/integration/test_search_harness_releases.py tests/integration/test_search_harness_release_readiness.py tests/integration/search_harness_release_support.py tests/integration/search_harness_release_audit_support.py tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_activation_waivers.py tests/integration/test_claim_support_policy_activation_retired_identity.py`
- `uv run pytest -q tests/unit/test_agent_task_verifications.py tests/unit/test_agent_task_verifications_drafts.py tests/unit/test_docling_parser.py tests/unit/test_docling_parser_logical_tables.py tests/unit/test_docling_parser_table_supplements.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_postgres_roundtrip_semantics.py tests/integration/test_postgres_roundtrip_failures.py tests/integration/test_search_harness_releases.py tests/integration/test_search_harness_release_readiness.py tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_activation_waivers.py tests/integration/test_claim_support_policy_activation_retired_identity.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- `tests/unit/test_agent_task_verifications.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/unit/test_docling_parser.py`,
  `tests/integration/test_search_harness_releases.py`, and
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`
  all close at or below `600` lines.
- No new sibling created by this packet exceeds `600` lines, and no new support
  file exceeds `400` lines.
- Every moved scenario family lands in a family-local sibling rather than a
  generic helper or unrelated test root.
- The focused unit slice and DB-backed integration slice pass without weaker
  assertions, broader skips, or narrower scenario coverage.
- Every affected routed verification command in plans or handoffs is updated to
  run the narrowed root plus its siblings explicitly.
- Any new sibling between `401` and `600` lines is routed in
  `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` during the
  same milestone.

## Stop Conditions

- Stop if `docs/documents_service_boundary_milestone_plan.md` still has active
  overlapping edits in the selected roots that cannot be separated safely.
- Stop if a fresh Milestone 0 rebaseline shows the selected root set has
  materially changed from this draft and needs a different packet boundary.
- Stop if preserving coverage requires a broader production-code refactor that
  belongs in a service-boundary packet instead of this verification packet.
- Stop if the split depends on weakening assertions, deleting scenarios, or
  leaving durable docs pointed at stale command paths.

## Local Commit Closeout Policy

- Close this packet with one atomic local commit containing only the selected
  verification-root changes, any new focused sibling or support files, routing
  config changes required by new `401-600` siblings, and the aligned docs or
  handoff updates for this packet.
- Stage only the verified milestone slice and leave unrelated dirty or
  untracked files alone.
- Treat the packet as ready-to-close, not complete, until that atomic local
  commit exists and its hash is recorded in `docs/SESSION_HANDOFF.md`.

## Residual Risks And Next Milestone Routing

- This packet resolves the verification branch under `IC-6C3E1A7B9D52`. The
  remaining adjacent family debt was the governance self-hosting packet under
  `IC-08C078FD4F45`, which is now also resolved locally in the current
  checkout.
- The next active code-owning follow-on was
  `docs/improvement_case_governance_self_hosting_milestone_plan.md`; the next
  packet must now be reselected from
  `docs/boring_change_architecture_milestone_plan.md`.
- Do not reactivate `docs/shared_verification_roots_milestone_plan.md` as the
  active packet for this scope unless a later Milestone 0 rebaseline proves its
  older selected roots are again the correct next target.
