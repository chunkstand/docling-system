# Hygiene Owner-Case Routing Boundary Milestone Plan

Date: 2026-05-14 local / 2026-05-14 UTC
Status: active stacked follow-on after
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
`docs/evaluations_service_boundary_milestone_plan.md`,
`docs/evidence_provenance_exports_boundary_milestone_plan.md`,
`docs/semantics_service_boundary_milestone_plan.md`,
`docs/cli_command_dispatch_boundary_milestone_plan.md`,
`docs/agent_task_schema_aggregation_boundary_milestone_plan.md`, and
`docs/oversized_test_hotspots_boundary_milestone_plan.md`; all seven prior
packets are now closed locally, Milestone 0 is resolved from the live
post-stack refresh through baseline commit `08a1a75`, Milestone 1 owner-case
bootstrap is resolved locally through checkpoint `d4f082c`, Milestone 2
owner-case binding conversion is resolved locally in the current worktree, and
Milestone 3 owner-case-only hygiene-contract enforcement is now the next
active code-changing slice
Owner context: active governance-first follow-on for the remaining
milestone-owned hygiene debt in `config/hygiene_policy.yaml`. This packet
assumes the earlier boundary and test packets have already reduced the major
service and test hotspots first. Milestone 0 must refresh the live post-stack
state, bind or reuse explicit owner cases for every remaining ratcheted
residual, and then remove the `owner_milestone` fallback from the active
hygiene contract so future sessions cannot hide debt behind milestone labels.

## Local Progress

Milestone 0 is resolved locally through baseline commit `08a1a75`, and
Milestone 1 owner-case bootstrap is resolved locally through checkpoint
`d4f082c`. Milestone 2 owner-case binding conversion is resolved locally in
the current worktree.
The stacked queue assumptions were revalidated against the live repo state,
the exact remaining residual owner set is now frozen in the active docs, the
three required family owner cases are now present in the registry, the live
hygiene policy now binds all eight residual files through explicit
`owner_case_id` values, and Milestone 3 owner-case-only hygiene-contract
enforcement is the next active slice.

Local Milestone 0 results:

- confirmed the seven upstream packets named in this plan are already closed
  locally, so this packet is no longer blocked on earlier stacked work
- confirmed the live residual hygiene-routing set still contains exactly eight
  `owner_milestone=residual-weakness-milestone-2` entries:
  `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`,
  `app/services/claim_support_replay_alert_fixture_corpus.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`, and
  `app/services/semantic_governance.py`
- confirmed none of those eight residual files already have explicit owner
  cases in `config/improvement_cases.yaml`, so Milestone 1 still needs the
  planned architecture-governance, claim-support support, and
  semantic-governance owner bootstrap
- refreshed the active routing artifacts so this plan, the handoff, and the
  architecture index then agreed that Milestone 0 was closed and Milestone 1
  was the next code-changing slice
- recorded baseline checkpoint `08a1a75` directly in the routed docs so the
  packet no longer reads like a pre-commit refresh snapshot
- confirmed the surrounding architecture state remains aligned with the
  oversized-test closeout baseline: `case_count=33`, `status_counts.open=22`,
  `status_counts.deployed=10`, `hotspot_count=10`,
  `max_hotspot_risk_score=501.06`, and Python cycle components=`5`

Local Milestone 0 verification:

- `git status -sb`: clean worktree at baseline checkpoint `08a1a75`; local
  `main` remained ahead of `origin/main`
- `uv run docling-system-improvement-case-summary`: `case_count=33`,
  `status_counts.open=22`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `actionable_buckets.open_unconverted_count=22`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `rg -n "owner_milestone: residual-weakness-milestone-2" config/hygiene_policy.yaml`:
  `150`, `155`, `343`, `348`, `369`, `472`, `477`, `550`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; the targeted residual files remain
  large but unchanged; Python cycle components=`5`

Local Milestone 1 results:

- created the architecture-governance residual family case
  `IC-08C078FD4F45`, anchored to `app/architecture_inspection.py`, covering
  `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`, and
  `app/services/improvement_cases.py`
- created the claim-support support residual family case `IC-7C73737C689F`,
  anchored to `app/services/claim_support_policy_governance.py`, covering
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py`
- created the semantic-governance residual owner case `IC-81C531769EB3`,
  anchored to `app/services/semantic_governance.py`
- moved the packet past missing-case routing: every live residual file from
  Milestone 0 now has a discoverable case ID in `config/improvement_cases.yaml`
  and no residual file remains routed only through
  `residual-weakness-milestone-2`
- recorded checkpoint `d4f082c` in the routed docs so the owner-bootstrap
  slice is anchored to a real committed milestone checkpoint instead of a
  worktree-only note
- refreshed the live registry counts after the bootstrap:
  `case_count=36`, `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`
- left the live hygiene policy unchanged for this milestone, so the eight
  residual `owner_milestone` entries still remained in
  `config/hygiene_policy.yaml` at checkpoint time, and Milestone 2 became the
  next active code-changing slice

Local Milestone 1 verification:

- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`,
  `actionable_buckets.open_unconverted_count=25`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`;
  inherited budget debt still lists the eight residual files under
  `owner=residual-weakness-milestone-2`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `rg -n "app/architecture_inspection.py|app/architecture_inspection_rules.py|app/services/claim_support_evaluations.py|app/services/claim_support_policy_governance.py|app/services/claim_support_replay_alert_fixture_corpus.py|app/services/improvement_case_intake.py|app/services/improvement_cases.py|app/services/semantic_governance.py|IC-08C078FD4F45|IC-7C73737C689F|IC-81C531769EB3" config/improvement_cases.yaml`:
  all eight residual files now resolve through the three new family case IDs

Local Milestone 2 results:

- replaced all eight live
  `owner_milestone=residual-weakness-milestone-2` entries in
  `config/hygiene_policy.yaml` with explicit `owner_case_id` bindings
- bound `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`, and
  `app/services/improvement_cases.py` to `IC-08C078FD4F45`
- bound `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py` to
  `IC-7C73737C689F`
- bound `app/services/semantic_governance.py` to `IC-81C531769EB3`
- preserved every existing `max_*` and `ratchet_max_*` ceiling while removing
  milestone-owned routing from the live hygiene policy
- refreshed the active routing docs so this plan, the handoff, and the
  architecture index agree that Milestone 2 is resolved locally and
  Milestone 3 is now the next active code-changing slice

Local Milestone 2 verification:

- `git diff --check`: pass
- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-import --source hygiene --dry-run`:
  pass
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; Python cycle components=`5`
- `rg -n "owner_milestone:" config/hygiene_policy.yaml`: no hits

## Purpose

Resolve the remaining owner-routing debt where hygiene still treats
`owner_milestone=residual-weakness-milestone-2` as an acceptable live owner
reference for real residual code debt.

The scoped problem is not that the cited files are still large. The deeper
problem is that the live governance layer still allows ratcheted inherited debt
to point at an old milestone label instead of a durable owner case. That weakens
three things at once:

- future routing clarity for architecture-governance, claim-support, and
  semantic-governance residuals
- deduplication discipline in `config/improvement_cases.yaml`
- the hygiene contract itself, because `owner_milestone` still works as a
  tolerated escape hatch

This packet resolves that governance debt end to end by converting every live
`owner_milestone=residual-weakness-milestone-2` ratchet to explicit
`owner_case_id` routing, creating or reusing the required owner cases, and
hard-failing any future attempt to reintroduce milestone-owned ratchets in the
active hygiene policy.

## Current Evidence

Live repo evidence refreshed from the current local checkout for Milestone 0
baseline commit `08a1a75` after oversized-test closeout commit `65c0c67` on
2026-05-14 local / 2026-05-14 UTC:

```text
uv run docling-system-improvement-case-summary
  case_count=33
  status_counts.open=22
  status_counts.deployed=10
  status_counts.measured=1
  actionable_buckets.open_unconverted_count=22

uv run docling-system-improvement-case-validate
  valid=true
  issue_count=0

uv run docling-system-hygiene-check
  valid baseline
  new hygiene regressions: none
  inherited budget debt still includes milestone-owned ratchets

rg -n "owner_milestone: residual-weakness-milestone-2" config/hygiene_policy.yaml
  150: owner_milestone: residual-weakness-milestone-2
  155: owner_milestone: residual-weakness-milestone-2
  343: owner_milestone: residual-weakness-milestone-2
  348: owner_milestone: residual-weakness-milestone-2
  369: owner_milestone: residual-weakness-milestone-2
  472: owner_milestone: residual-weakness-milestone-2
  477: owner_milestone: residual-weakness-milestone-2
  550: owner_milestone: residual-weakness-milestone-2

rg target residual paths in config/improvement_cases.yaml
  no explicit owner cases currently exist for:
    app/architecture_inspection.py
    app/architecture_inspection_rules.py
    app/services/claim_support_evaluations.py
    app/services/claim_support_policy_governance.py
    app/services/claim_support_replay_alert_fixture_corpus.py
    app/services/improvement_case_intake.py
    app/services/improvement_cases.py
    app/services/semantic_governance.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  app/architecture_inspection.py = 412 lines
  app/architecture_inspection_rules.py = 604 lines
  app/services/claim_support_evaluations.py = 1142 lines
  app/services/claim_support_policy_governance.py = 1259 lines
  app/services/claim_support_replay_alert_fixture_corpus.py = 972 lines
  app/services/improvement_case_intake.py = 820 lines
  app/services/improvement_cases.py = 876 lines
  app/services/semantic_governance.py = 1157 lines
  cycle component still includes:
    app.architecture_decisions
    app.architecture_inspection
    app.architecture_inspection_rules
    app.hygiene
    app.services.improvement_case_intake
```

Repo-current structural evidence:

- `docs/oversized_test_hotspots_boundary_milestone_plan.md` is now resolved
  locally through closeout commit `65c0c67`, so this hygiene-routing packet is
  no longer blocked on the prior oversized-test follow-on and Milestone 0 is
  the active next refresh rather than a hypothetical future rebaseline step.

- `docs/claim_support_policy_impacts_boundary_milestone_plan.md` already calls
  out that `app/services/claim_support_policy_governance.py` and
  `app/services/claim_support_evaluations.py` are oversized adjacent owners
  with milestone-owned inherited ratchets rather than explicit owner-case
  closure.
- `docs/hotspot_owner_resolution_plan.md` already established the repo policy
  that milestone-owned hygiene debt is only acceptable as a temporary bootstrap
  state and should be converted to explicit owner cases.
- `docs/improvement_loop.md` still documents the hygiene contract as requiring
  `owner_case_id` or `owner_milestone`, so the fallback remains normalized both
  in code and in durable repo guidance.
- The current `app/hygiene.py`, `app/hygiene_types.py`, and
  `tests/unit/test_hygiene.py` still parse and accept `owner_milestone`, which
  means future sessions can copy the old pattern without tripping a hard gate.

## Goal

Resolve the scoped owner-routing debt so that:

- `config/hygiene_policy.yaml` contains zero live `owner_milestone` entries
- every ratcheted inherited-debt entry is bound to an explicit
  `owner_case_id`
- every remaining residual file currently owned by
  `residual-weakness-milestone-2` has a durable owner case in
  `config/improvement_cases.yaml`
- the hygiene contract, tests, and docs reject `owner_milestone` as an active
  routing mechanism
- no new production owner modules are introduced just to relocate this routing
  debt
- the scoped owner-routing problem is `resolved` even if the broader file-size,
  hotspot, or cycle debt for the cited files remains open under explicit owner
  cases

## Non-Goals

- No claim-support, semantic, or architecture service split in this packet.
- No new `app/services/claim_support_*.py`,
  `app/services/semantic_*.py`, or `app/architecture_*.py` modules.
- No movement of implementation bodies out of
  `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`,
  `app/services/claim_support_replay_alert_fixture_corpus.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`, or
  `app/services/semantic_governance.py`.
- No attempt to mark the resulting broader owner cases `resolved` just because
  the routing is fixed. Those files may still remain large or cycle-involved.
- No new allowlist, sidecar registry, or second sink that preserves
  milestone-owned routing in another form.
- No reopening of the already-queued claim-support, evaluations, evidence,
  semantics, CLI, schema, or oversized-test decomposition packets.

## Scope

In scope:

- Milestone 0 post-stack refresh after the earlier queued packets close
- explicit owner-case bootstrap or reuse for every live
  `owner_milestone=residual-weakness-milestone-2` ratchet that still remains
  after Milestone 0
- conversion of all live milestone-owned ratchets to `owner_case_id`
- removal of `owner_milestone` from the active hygiene contract, tests, and
  process docs
- narrow improvement-case, hygiene, and handoff/index updates required to prove
  the routing is current

Out of scope:

- direct code reduction of the cited owner files
- runtime-health, CI release-gate, or broader boring-change implementation
- changes to canonical API, DB, ingest, retrieval, or artifact contracts
- any new helper sink whose only purpose is to preserve the old owner-milestone
  fallback

## Owner Surfaces

- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `app/hygiene.py`
- `app/hygiene_types.py`
- `tests/unit/test_hygiene.py`
- `tests/unit/test_improvement_case_intake.py`
- `docs/improvement_loop.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- target residual owner files whose routing must be bound, not split:
  - `app/architecture_inspection.py`
  - `app/architecture_inspection_rules.py`
  - `app/services/claim_support_evaluations.py`
  - `app/services/claim_support_policy_governance.py`
  - `app/services/claim_support_replay_alert_fixture_corpus.py`
  - `app/services/improvement_case_intake.py`
  - `app/services/improvement_cases.py`
  - `app/services/semantic_governance.py`

## Placement Rules

- Do not solve this packet by creating new service modules or moving
  implementation between the cited residual owner files.
- Keep all routing changes inside the governance surfaces:
  `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
  `app/hygiene.py`, `app/hygiene_types.py`, and the focused governance tests
  and docs.
- If Milestone 0 shows that one of the residual files already received an
  explicit owner case from a prior queued packet, reuse that live case rather
  than creating a duplicate.
- At most three new owner cases may be created after Milestone 0:
  one architecture-governance family case, one claim-support support-family
  case, and one semantic-governance case. Reuse live cases whenever possible.
- Keep each broader owner file under a stable file-path source reference so
  future imports and follow-on packets dedupe to the same owner case.
- Do not introduce a new compatibility facade or helper sink in `app/services/`
  or `app/` merely to record routing metadata.

## Weak-Point Prevention Contract

Freshness check: before implementation begins, rerun
`uv run docling-system-improvement-case-summary`,
`uv run docling-system-improvement-case-validate`,
`uv run docling-system-hygiene-check`,
`uv run docling-system-architecture-quality-report --summary`, and
`rg -n "owner_milestone: residual-weakness-milestone-2" config/hygiene_policy.yaml`.
If the post-stack repo state already differs materially from the evidence
captured here, update the live residual set before changing any routing.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Stacked implementation starts from stale repo state after earlier packets land | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md` | Milestone 0 refresh plus manual readback before edits | any prior queued packet is still open, a targeted file already gained an explicit case, or the residual `owner_milestone` set changed and the plan was not refreshed first | refresh after prior packets close and confirm the residual set before editing configs | a future session starts converting IDs from this draft without checking whether claim-support, semantics, or schema packets already changed the live owner set |
| `owner_milestone` remains a tolerated live fallback | `app/hygiene.py`, `app/hygiene_types.py`, `tests/unit/test_hygiene.py`, `docs/improvement_loop.md` | `uv run pytest -q tests/unit/test_hygiene.py` plus `rg -n "owner_milestone:" config/hygiene_policy.yaml` | any live policy entry still uses `owner_milestone`, or the hygiene tests still accept it as valid routing | add a fixture policy entry with `owner_milestone` and confirm the contract test fails | a future session copies the old ratchet pattern into hygiene to avoid recording a real owner case |
| Converted ratchets point at missing or duplicate owner cases | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml` | `uv run docling-system-improvement-case-validate` and targeted registry review | any converted ratchet lacks a matching `owner_case_id`, any file is attached to the wrong case family, or duplicate cases are created for the same live source reference | create a temporary bogus `owner_case_id` in a fixture or temp edit and verify validation or closeout review fails | a future session creates a second owner case for the same file because the first one is hard to find |
| Routing cleanup expands into unrelated code motion | this plan and the cited residual owner files | closeout diff review plus `git diff --check` | the milestone adds new service modules, moves implementation bodies, or changes unrelated production behavior instead of only fixing routing and gates | inspect a local prototype diff that adds a new `claim_support_*` helper and reject it before closeout | a future session uses this packet as permission to start splitting claim-support or semantic code without the dedicated boundary plans |

## Milestone Sequence

### Milestone 0 - Refresh the post-stack state and freeze the live residual set

Status: resolved locally in the current refresh window

Outcome label: reduced

Purpose: do not implement this packet against stale queue assumptions. Refresh
the live repo state after the prior stacked packets close, confirm which
`owner_milestone` entries still remain, and decide whether each residual should
reuse an already-created owner case or needs a new one.

Implementation:

- Rerun:
  - `git status -sb`
  - `uv run docling-system-improvement-case-summary`
  - `uv run docling-system-improvement-case-validate`
  - `uv run docling-system-hygiene-check`
  - `uv run docling-system-architecture-quality-report --summary`
  - `rg -n "owner_milestone: residual-weakness-milestone-2" config/hygiene_policy.yaml`
  - `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- Freeze the exact live residual owner set in this plan, the handoff, and the
  architecture index before code or config edits begin.
- If any residual file already has a correct explicit owner case after the
  earlier packets close, bind to that case and remove it from the new-case
  bootstrap list.
- If Milestone 0 finds zero live `owner_milestone` entries, stop the packet,
  update routing docs to record that the debt was already cleared elsewhere,
  and do not proceed to later milestones.

Acceptance signal:

- The implementation brief names the exact remaining live residual files and
  whether each one reuses an existing case or needs a new one.
- No config edits begin until the post-stack state is refreshed.

### Milestone 1 - Bootstrap explicit owner cases for every live residual family

Status: resolved locally through checkpoint `d4f082c`

Outcome label: resolved

Purpose: eliminate missing-case routing before changing the hygiene contract.

Implementation:

- Create or reuse explicit open owner cases for every live residual family still
  using `owner_milestone` after Milestone 0.
- Default family grouping, unless the live post-stack state makes reuse better:
  - architecture-governance family:
    `app/architecture_inspection.py`,
    `app/architecture_inspection_rules.py`,
    `app/services/improvement_case_intake.py`, and
    `app/services/improvement_cases.py`
  - claim-support support family:
    `app/services/claim_support_evaluations.py`,
    `app/services/claim_support_policy_governance.py`, and
    `app/services/claim_support_replay_alert_fixture_corpus.py`
  - semantic-governance family:
    `app/services/semantic_governance.py`
- Use explicit `unclear_ownership` owner cases with stable file-path source
  references so future dedupe resolves to the same case IDs.
- Record the new or reused case IDs in this plan and in
  `docs/SESSION_HANDOFF.md`.

Acceptance signal:

- Every live residual file from Milestone 0 has a discoverable case ID in
  `config/improvement_cases.yaml`.
- No file remains routed only through `residual-weakness-milestone-2`.

Local result:

- architecture-governance residual family -> `IC-08C078FD4F45`
- claim-support support residual family -> `IC-7C73737C689F`
- semantic-governance residual owner -> `IC-81C531769EB3`

### Milestone 2 - Convert the live hygiene policy to `owner_case_id` only

Status: resolved locally in the current worktree

Outcome label: resolved

Purpose: remove the milestone-owned routing from the live hygiene policy
without changing the underlying ratchet ceilings.

Implementation:

- Replace every live `owner_milestone` entry in `config/hygiene_policy.yaml`
  with the correct `owner_case_id`.
- Preserve the existing `max_*` and `ratchet_max_*` numbers unless Milestone 0
  proves a prior packet changed the underlying file sizes and the ratchets must
  be refreshed from live measurements.
- Update any closeout docs that still name
  `residual-weakness-milestone-2` as the active owner of those residual files.
- Keep the broader owner cases open as `open` or `reduced` according to live
  repo state; routing cleanup alone does not close the underlying file debt.

Acceptance signal:

- `rg -n "owner_milestone:" config/hygiene_policy.yaml` returns no hits.
- `uv run docling-system-improvement-case-validate` stays valid after the case
  binding change.

Local result:

- `config/hygiene_policy.yaml` now uses `owner_case_id` for all eight
  previously milestone-owned residual files.
- The active routing docs no longer describe
  `residual-weakness-milestone-2` as a live hygiene owner.

### Milestone 3 - Remove the fallback from the hygiene contract and prove the negative case

Status: next active code-changing slice

Outcome label: resolved

Purpose: make the owner-routing discipline executable so the old pattern cannot
re-enter the repo.

Implementation:

- Update `app/hygiene_types.py` and `app/hygiene.py` so ratcheted hygiene
  entries require `owner_case_id` rather than `owner_case_id or owner_milestone`.
- Update `tests/unit/test_hygiene.py` so the negative contract covers rejected
  `owner_milestone` entries instead of only missing-owner cases.
- Update `docs/improvement_loop.md` so the durable guidance matches the new
  executable contract.
- If needed, update focused improvement-case intake coverage so hygiene-import
  behavior still ignores inherited debt while blocking regressions remain
  observable.

Acceptance signal:

- The focused hygiene tests fail on `owner_milestone`.
- The active docs no longer tell future sessions that `owner_milestone` is a
  valid live owner reference.

### Milestone 4 - Close out the routing packet and record the new owner map

Outcome label: resolved

Purpose: finish with aligned docs, current evidence, and a clean next-packet
route.

Implementation:

- Refresh the live command stack one more time:
  - `uv run docling-system-improvement-case-summary`
  - `uv run docling-system-improvement-case-validate`
  - `uv run docling-system-hygiene-check`
  - `uv run docling-system-architecture-quality-report --summary`
  - `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- Update this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` with the final case IDs, refreshed
  counts, and the next stacked packet.
- If the broader coordination docs still assume these residuals are ownerless,
  update them in the same closeout commit.

Acceptance signal:

- The handoff and index no longer describe these residual files as
  milestone-owned hygiene debt.
- The closeout docs identify the next queued packet from the new explicit owner
  map rather than from the old milestone label.

## Required Implementation Artifacts

- Updated `config/improvement_cases.yaml` with explicit owner cases or reused
  live case bindings for every remaining residual family
- Updated `config/hygiene_policy.yaml` with zero `owner_milestone` entries
- Updated `app/hygiene.py` and `app/hygiene_types.py` removing the live
  milestone-owner fallback
- Updated `tests/unit/test_hygiene.py`, plus focused intake coverage only if
  required by the contract change
- No new production owner modules in `app/` or `app/services/`

## Required Documentation And Handoff Updates

- Update this plan with final status, closeout commit, and refreshed live
  evidence
- Update `docs/improvement_loop.md` to document `owner_case_id` as the sole
  valid ratchet owner reference
- Update `docs/SESSION_HANDOFF.md` with the new owner-case routing and next
  queued packet
- Update `docs/agentic_architecture_index.md` with the queued and then closed
  state of this packet
- Update any broader later-stack coordination doc only if it still claims these
  residuals are ownerless or milestone-owned after closeout

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/hygiene.py app/hygiene_types.py tests/unit/test_hygiene.py tests/unit/test_improvement_case_intake.py`
- `uv run pytest -q tests/unit/test_hygiene.py tests/unit/test_improvement_case_intake.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-import --source hygiene --dry-run`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `rg -n "owner_milestone:" config/hygiene_policy.yaml`

## Acceptance Criteria

- Every live ratcheted residual file formerly owned by
  `residual-weakness-milestone-2` is routed through an explicit
  `owner_case_id`.
- `config/hygiene_policy.yaml` contains zero `owner_milestone` keys after
  closeout.
- `config/improvement_cases.yaml` contains a durable owner case for each
  remaining residual family and no accidental duplicate case for the same
  file-path source reference.
- `app/hygiene.py`, `app/hygiene_types.py`, `tests/unit/test_hygiene.py`, and
  `docs/improvement_loop.md` all agree that `owner_case_id` is required for
  ratcheted inherited debt.
- The packet does not create new claim-support, semantic, or architecture side
  modules to relocate the debt.
- The broader owner files may remain large or cycle-involved, but that residual
  debt is explicitly routed through owner cases instead of a milestone label.
- Docs and handoff updates land in the same atomic closeout commit as the code
  and config changes.

## Stop Conditions

- Milestone 0 shows that a prior queued packet already removed all live
  `owner_milestone` entries.
- Milestone 0 finds that one or more targeted surfaces already have conflicting
  owner cases whose scope cannot be reconciled without reopening an earlier
  packet.
- Removing `owner_milestone` from the hygiene contract would break another
  still-live governance workflow that cannot be updated within this bounded
  packet.
- The implementation starts requiring new production owner modules or broad
  code motion inside the cited residual files. If that happens, stop and route
  the work back to the dedicated boundary plan for that owner family instead of
  broadening this packet.

## Local Commit Closeout Policy

- Close this packet in one atomic local commit after all verification gates
  pass.
- Include the routing config changes, focused hygiene code and test updates,
  this plan, `docs/improvement_loop.md`, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` in the same commit.
- Do not stage unrelated dirty worktree changes from the earlier claim-support
  implementation or any other in-flight packet.
- A verified but uncommitted routing cleanup is not complete.

## Residual Risks And Next Milestone Routing

- The resulting owner cases will usually remain `open` or `reduced` because
  this packet fixes routing, not the underlying size, hotspot, or cycle debt.
- If `app/services/semantic_governance.py` still remains large after the queued
  semantics packet, its follow-on reduction stays with the semantics or
  boring-change architecture lane, not with this routing packet.
- If `app/services/improvement_case_intake.py` or
  `app/services/improvement_cases.py` still participate in the architecture
  cycle after closeout, the follow-on cycle cleanup belongs to the broader
  boring-change architecture packet once the owner routing is explicit.
- After this packet closes, the next queued broader coordination packet should
  be `docs/runtime_health_orchestration_milestone_plan.md`, followed by
  `docs/ci_release_gate_parity_milestone_plan.md`, unless Milestone 0 refresh
  proves a different post-stack order is required.
