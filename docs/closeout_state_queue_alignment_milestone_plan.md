# Closeout State Queue Alignment Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally in the current checkout through the 2026-05-18
queue-alignment closeout. The top-level routing docs now agree on the next
code-owning packet, the stale shared-verification branch is explicitly
historical, and the closeout path is narrowed to a docs-only staging slice.
Owner context: mechanical closeout and routing debt across
`docs/SESSION_HANDOFF.md`,
`docs/residual_large_file_backlog_milestone_plan.md`,
`docs/agentic_architecture_index.md`,
`docs/boring_change_architecture_milestone_plan.md`, and
`docs/shared_verification_roots_milestone_plan.md`. The selected excerpt
understates the live weakness: the architecture index already treats
`docs/shared_verification_roots_milestone_plan.md` as stale historical
routing, while the parent large-file backlog already requires one child packet
per atomic closeout. The remaining issue is contradictory queue truth and
closeout wording across the durable docs.

## Purpose

Resolve the local closeout and stale-queue ambiguity so future sessions can
tell:

- which packet is actually next
- which child packets are only locally retirement-ready pending commit
- which historical packet must not reactivate without a fresh Milestone 0
  rebaseline
- how to land the pending closeout without staging unrelated dirty-worktree
  changes

This packet is about mechanics, not new feature or service work. The repo
already has narrower owner-family packets for the remaining code debt. The
problem is that the top-level routing and handoff artifacts still contain two
different queue stories and an omnibus closeout implication that conflicts with
the parent packet's one-child-at-a-time commit policy.

## 2026-05-18 Closeout Update

This coordination packet is now resolved locally in the current checkout.

- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`,
  `docs/residual_large_file_backlog_milestone_plan.md`,
  `docs/boring_change_architecture_milestone_plan.md`, and
  `docs/cross_cutting_large_file_residual_milestone_plan.md` now agree on the
  same post-closeout order:
  `docs/documents_service_boundary_milestone_plan.md`, then
  `docs/cross_cutting_verification_roots_milestone_plan.md`, then
  `docs/improvement_case_governance_self_hosting_milestone_plan.md`.
- `docs/shared_verification_roots_milestone_plan.md` remains explicitly
  historical and non-operational unless a later explicit Milestone 0
  rebaseline selects a new live shared verification owner surface.
- The queue docs no longer imply one atomic closeout commit for unrelated
  locally resolved child packets.
- The docs-only closeout path is now explicit: stage only this packet, the
  queue docs it governs, and any stale-packet status updates required by this
  coordination slice; do not stage unrelated service or test files from the
  dirty checkout.

## Current Evidence

- The selected `docs/SESSION_HANDOFF.md` excerpt that triggered this packet
  carried two different queue stories at once: the summary block routed next to
  `docs/documents_service_boundary_milestone_plan.md`, then
  `docs/cross_cutting_verification_roots_milestone_plan.md`, then
  `docs/improvement_case_governance_self_hosting_milestone_plan.md`, while a
  later paragraph still said the queued order was cross-cutting and then
  `docs/shared_verification_roots_milestone_plan.md`.
- That same triggering handoff paragraph said "The atomic closeout commit for
  all locally resolved packets is still pending", which over-bundled the
  pending work. `docs/residual_large_file_backlog_milestone_plan.md` already
  says to execute the sequence one child packet at a time and to close each
  milestone with one local atomic commit for that milestone only.
- `docs/agentic_architecture_index.md` was already more accurate than the
  selected handoff and parent backlog because it treated
  `docs/shared_verification_roots_milestone_plan.md` as a stale historical
  follow-on whose former targets were already reduced locally.
- `docs/shared_verification_roots_milestone_plan.md` starts with a stale-plan
  warning, but the body still documents the older `612`, `562`, and `1506`
  targets even though the DB-model and evaluation residual packets have already
  reduced those roots locally to `457`, `472`, and `445`.
- The current checkout is broadly dirty, so any closeout that relies on one
  large staging sweep is mechanically risky. This packet must preserve a clean
  packet-local closeout path, potentially through a narrow staged path set or a
  clean worktree, instead of assuming the current checkout can be committed as
  one bundle.

## Goal

Resolve the closeout-state debt so that:

- the handoff, architecture index, residual backlog brief, and umbrella brief
  all describe the same next active packet and follow-on order
- locally resolved child packets are described as `retirement-ready pending
  commit`, `committed`, `blocked by overlap`, or `superseded`, never as one
  vague omnibus local closeout
- `docs/shared_verification_roots_milestone_plan.md` is either explicitly
  retired from the active queue or refreshed to a new live owner set after a
  real Milestone 0 rebaseline
- the closeout path names an exact docs-only staging boundary and does not
  require capturing unrelated dirty-worktree changes
- future sessions can resume from durable docs without reopening stale queue
  branches

The scoped issue is `resolved` when the queue docs agree, the stale
shared-verification branch is quarantined behind explicit rebaseline semantics,
and the closeout policy no longer implies one mixed commit for unrelated local
packets.

## Non-Goals

- No implementation of the `documents.py`, verification-root, or governance
  self-hosting code splits owned by the later packets.
- No rewriting of `config/improvement_cases.yaml` or
  `config/hygiene_policy.yaml` unless Milestone 0 proves a queue doc currently
  cites stale owner-case facts.
- No deletion of historical milestone-plan evidence; stale packets can remain
  as historical records as long as they are removed from the live queue.
- No weakening of verification, threshold, or atomic-commit rules just to make
  the closeout easier to stage.
- No omnibus commit that mixes unrelated dirty-worktree changes into the
  resolved-local packet closeout.

## Scope

In scope:

- `docs/closeout_state_queue_alignment_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/shared_verification_roots_milestone_plan.md`
- `docs/cross_cutting_large_file_residual_milestone_plan.md` only as needed to
  preserve queue continuity after the closeout-state update
- packet-local staging and worktree procedure notes needed to keep the eventual
  closeout atomic and docs-only

Out of scope:

- `app/services/documents.py`
- `tests/unit/test_agent_task_verifications.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/unit/test_docling_parser.py`
- `tests/integration/test_search_harness_releases.py`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py`
- `app/services/improvement_cases.py`
- `app/services/improvement_case_intake.py`
- `tests/unit/test_improvement_case_intake.py`

## Owner Surfaces

- the queue and handoff docs listed above
- the stale historical packet
  `docs/shared_verification_roots_milestone_plan.md`
- the resolved-local child packet records that are currently waiting for
  closeout wording to stabilize:
  `docs/evaluation_residual_owner_family_milestone_plan.md`,
  `docs/ui_module_residual_owner_family_milestone_plan.md`, and
  `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`
- the parent packet
  `docs/cross_cutting_large_file_residual_milestone_plan.md` only where its
  forward-routing note must agree with the new coordination packet
- the eventual docs-only staged path set or clean-worktree closeout path

## Placement Rules

- Keep `docs/documents_service_boundary_milestone_plan.md` as the next
  code-owning packet unless Milestone 0 proves the live queue has changed.
- Keep `docs/cross_cutting_verification_roots_milestone_plan.md` as the live
  verification follow-on behind the document-service packet once this
  coordination packet resolves.
- Do not reactivate `docs/shared_verification_roots_milestone_plan.md` from
  queue docs unless a fresh explicit Milestone 0 rebaseline selects a new,
  still-live shared verification owner surface.
- Describe locally resolved child packets packet-by-packet. Do not use "all
  locally resolved packets" wording when the actual closeout units are separate
  child packets or separate milestones.
- Keep the closeout path docs-only and packet-local. If staging the closeout
  from the current checkout would capture unrelated work, move the closeout to
  a clean worktree or an equivalently narrow staging path rather than widening
  the commit.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The handoff, backlog brief, and architecture index keep different queue orders. | queue docs | Milestone 0 doc comparison and targeted `rg` checks | any top-level routing doc still names a different next packet after closeout | leave one stale queue reference in the handoff and confirm the grep finds it | future Codex resumes from the wrong durable artifact |
| The stale shared-verification packet remains in the live queue even though its original targets are already reduced. | `docs/shared_verification_roots_milestone_plan.md`, queue docs | stale-packet status update plus routing review | the stale packet is still described as the next or queued operational packet without an explicit rebaseline gate | keep the old queued wording in one parent doc and confirm review rejects it | future Codex reopens already-reduced DB-model or evaluation roots |
| The closeout wording collapses multiple child packets into one omnibus "pending commit" bundle. | handoff and parent backlog brief | comparison against the parent child-at-a-time commit policy | queue docs still imply one broad closeout commit for unrelated child packets | preserve the "all locally resolved packets" wording and confirm review flags the conflict | future Codex stages unrelated verified packets together just to clear the handoff |
| The docs-only closeout accidentally stages unrelated dirty-worktree changes. | staged path set, worktree procedure notes | `git status -sb`, staged-file review, docs-only closeout policy | any eventual closeout path requires unrelated source or test files to land with the routing fix | stage one unrelated app file with the docs-only packet and confirm the closeout policy rejects it | future Codex uses the dirty checkout as an excuse to widen the commit |
| A later session treats stale historical evidence inside older plans as the operational queue. | umbrella brief, stale historical packet, handoff | Milestone 2 status rewrite and residual-risk alignment | an older historical packet still reads like the live next step without a stale or historical marker | leave a live-looking status line in the historical packet and confirm doc review catches it | future Codex trusts a stale plan body over the current queue docs |

## Milestone Sequence

### Milestone 0. Live Rebaseline And Queue Truth Lock
Outcome label: reduced

Refresh the live queue, closeout state, and stale-packet status before any
further code-owning packet is treated as active.

This milestone must:

- compare `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/residual_large_file_backlog_milestone_plan.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/cross_cutting_large_file_residual_milestone_plan.md`, and
  `docs/shared_verification_roots_milestone_plan.md`
- record the exact contradictions between those docs
- confirm that `docs/documents_service_boundary_milestone_plan.md` remains the
  next code-owning packet once queue truth is restored
- classify whether `docs/shared_verification_roots_milestone_plan.md` should be
  retired from the live queue or explicitly rebaselined later
- lock this packet as the next coordination brief until the queue docs agree

### Milestone 1. Resolved-Local Packet Closeout Classification
Outcome label: reduced

Replace vague "resolved locally but pending" wording with explicit
packet-by-packet closeout state.

This milestone must:

- classify each affected child packet as `committed`, `retirement-ready pending
  commit`, `blocked by overlapping dirty work`, or `superseded`
- identify the exact docs-only staged path set needed for the eventual closeout
- decide whether any child packet needs its own narrow closeout commit rather
  than a grouped parent-note refresh
- remove any wording that implies one omnibus atomic closeout for unrelated
  locally resolved packets

### Milestone 2. Shared Verification Retirement Or Explicit Rebaseline
Outcome label: reduced

Finish the stale queued follow-on decision instead of leaving it half-active.

This milestone must:

- either mark `docs/shared_verification_roots_milestone_plan.md` as historical
  and non-operational or replace it with a fresh scoped owner set selected from
  live Milestone 0 evidence
- align the parent backlog, handoff, architecture index, and umbrella brief to
  that decision
- keep already-reduced DB-model and evaluation verification roots closed unless
  the new evidence proves a different live shared root still remains

### Milestone 3. Durable Routing And Atomic Closeout Path
Outcome label: resolved

Close the packet by making the docs-only closeout path explicit and stable.

This milestone must:

- leave one unambiguous queue order in the handoff, parent backlog, architecture
  index, and umbrella brief
- keep `docs/documents_service_boundary_milestone_plan.md`,
  `docs/cross_cutting_verification_roots_milestone_plan.md`, and
  `docs/improvement_case_governance_self_hosting_milestone_plan.md` in the
  correct post-closeout order
- document the clean-worktree or narrow-staging rule for the eventual atomic
  closeout
- remove any lingering operational wording that points to the stale shared
  packet as if it were still queued work

## Required Verification Gates

- Milestone 0 and every docs-only refresh:
  `git status -sb`
- Milestone 0 and every queue refresh:
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- Milestone 0 and every queue refresh:
  `uv run docling-system-architecture-quality-report --summary`
- every docs-only packet revision:
  `git diff --check`
- every queue closeout:
  `rg -n "closeout_state_queue_alignment_milestone_plan|documents_service_boundary_milestone_plan|cross_cutting_verification_roots_milestone_plan|shared_verification_roots_milestone_plan|all locally resolved packets" docs/SESSION_HANDOFF.md docs/agentic_architecture_index.md docs/residual_large_file_backlog_milestone_plan.md docs/boring_change_architecture_milestone_plan.md docs/cross_cutting_large_file_residual_milestone_plan.md docs/shared_verification_roots_milestone_plan.md`
- no broad `pytest` gate is required unless Milestone 0 proves the packet
  actually touches source, test, or config behavior outside the queue docs

## Acceptance Criteria

- the handoff, architecture index, residual backlog brief, and umbrella brief
  all agree on the same next packet and follow-on order
- `docs/shared_verification_roots_milestone_plan.md` is clearly marked
  historical or explicitly rebaselined; it is not half-active
- no queue doc still says one atomic closeout commit is pending "for all
  locally resolved packets"
- the closeout path names an exact docs-only staging boundary or clean-worktree
  fallback that avoids unrelated dirty files
- future routing returns to `docs/documents_service_boundary_milestone_plan.md`
  for code work, then to
  `docs/cross_cutting_verification_roots_milestone_plan.md`, then to
  `docs/improvement_case_governance_self_hosting_milestone_plan.md`

## Stop Conditions

- Stop and redo Milestone 0 if the live queue changes materially while this
  packet is in progress.
- Stop if the current dirty checkout cannot support a packet-local closeout
  path; write the clean-worktree or pathspec staging procedure first instead of
  pretending the packet is commit-ready.
- Stop if a proposed fix widens into a code-owning refactor. That work belongs
  to the later routed packets, not to this coordination packet.
- Stop if a later doc review still finds two different queue orders in the
  top-level routing docs.

## Local Commit Closeout Policy

- This packet is docs-only unless Milestone 0 proves a queue fact in config or
  code must also change.
- Stage only the new plan, the queue docs, and the stale historical packet
  status updates required by this packet.
- Do not stage unrelated dirty-worktree source or test files with this packet.
- If a clean atomic docs-only commit is not possible from the current checkout,
  close this packet from a clean worktree or equivalent narrow staging path
  before returning to the code-owning residual packets.

## Residual Risks And Next Milestone Routing

- The live code-owning queue still begins with
  `docs/documents_service_boundary_milestone_plan.md`, then
  `docs/cross_cutting_verification_roots_milestone_plan.md`, then
  `docs/improvement_case_governance_self_hosting_milestone_plan.md`.
- This packet is now resolved locally; the remaining work is the code-owning
  follow-on stack above, not additional queue repair inside this slice.
- `docs/shared_verification_roots_milestone_plan.md` must remain historical
  until a later explicit Milestone 0 rebaseline proves that a live shared
  verification root still needs a dedicated packet.
