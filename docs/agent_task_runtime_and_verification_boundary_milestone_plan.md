# Agent-Task Runtime And Verification Boundary Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved locally in the current 2026-05-19 checkout. The worker and
verification owner cases `IC-3F725D0A6C91` and `IC-86E1D4B72F0C` are now
deployed, the mixed runtime roots are reduced to narrow facades, and the later
live architecture-quality report now routes
`app/hotspot_prevention_classifier.py` as the honest next owner surface rather
than leaving the queue empty.
Owner context: broader rebaseline packet for the remaining hard-to-change
agent-task runtime lane after the earlier
`docs/agent_task_orchestration_boundary_milestone_plan.md` and
`docs/agent_task_residual_owner_family_milestone_plan.md` packets resolved the
central action, context, and service facade splits. This packet exists because
the routed queue is exhausted, but live hotspot evidence still clusters around
the runtime worker and verification execution surfaces.

## Purpose

Resolve the remaining agent-task runtime execution and verification debt
without reopening already-reduced compatibility facades.

The scoped weakness is no longer the old
`app/services/agent_task_actions.py` or
`app/services/agent_task_context.py` monoliths. Those surfaces are already
resolved and routed as reduced facades. The remaining hard-to-change runtime
debt is now concentrated in:

- `app/services/agent_task_worker.py`, which still mixes lease claiming,
  stale-task recovery, failure-artifact persistence, retry classification,
  promotable-result checkpointing, completion finalization, runtime freshness,
  and the worker loop in one file.
- `app/services/agent_task_verifications.py`, which still mixes search-harness
  evaluation verification, draft-harness comprehension checks, semantic
  registry verification, and grounded-document verification in one file.
- `app/services/agent_tasks.py`, which remains a busy compatibility seam over
  dependency, lifecycle, read, analytics, cost, and recommendation owners, but
  is already a deployed reduced facade and must not be reopened unless
  Milestone 0 proves real regrowth.
- `app/services/agent_task_actions.py`, which remains visible in hotspot
  reports because of churn and fan-out, but is already a deployed narrow
  composition facade and must likewise not be reopened unless Milestone 0 finds
  new mixed implementation.

This plan resolves that debt by creating fresh owner routing for the worker and
verification roots, preserving the public service seams, and requiring runtime
and DB-backed verification that proves the split did not weaken retry, failure,
approval, context, or verification behavior.

## Current Evidence

Milestone 0 rebaseline from the live checkout on 2026-05-19 before
implementation:

```text
git status -sb
  ## main...origin/main
   M README.md
   M docs/SESSION_HANDOFF.md

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=20
  stale_facade_hotspot_count=20
  max_hotspot_risk_score=471.06
  top_routed_hotspot_paths=[]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  hotspots include:
    app/services/agent_tasks.py = 12960
    app/services/agent_task_worker.py = 10792
    app/services/agent_task_actions.py = 10432
    app/services/agent_task_verifications.py = 10008
  Python cycles: none detected

wc -l app/services/agent_tasks.py app/services/agent_task_worker.py app/services/agent_task_actions.py app/services/agent_task_verifications.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_action_lookup.py
   324 app/services/agent_tasks.py
   568 app/services/agent_task_worker.py
   163 app/services/agent_task_actions.py
   556 app/services/agent_task_verifications.py
   466 tests/unit/test_agent_task_actions.py
   624 tests/unit/test_agent_task_worker.py
    92 tests/unit/test_agent_tasks_api.py
    48 tests/unit/test_agent_task_action_lookup.py

config/hygiene_policy.yaml
  app/services/agent_task_verifications.py max_lines=636 max_private_helpers=6
  app/services/agent_task_worker.py max_lines=696 max_private_helpers=11
  app/services/agent_tasks.py max_lines=324 max_private_helpers=0 owner_case_id=IC-4098E8370B88

config/hotspot_prevention.yaml
  app/services/agent_tasks.py = deferred_reduced_facade
  no dedicated routing entry exists for app/services/agent_task_worker.py
  no dedicated routing entry exists for app/services/agent_task_verifications.py
```

Repo-current structural evidence:

- `docs/agent_task_orchestration_boundary_milestone_plan.md` is already
  resolved through local closeout commit `7cf7465`, with
  `app/services/agent_task_actions.py` reduced to `163` lines and
  `app/services/agent_task_context.py` reduced to `121` lines.
- `docs/agent_task_residual_owner_family_milestone_plan.md` is already
  resolved through durable closeout commit `b9b3e46`, with
  `app/services/agent_tasks.py` reduced to `324` lines over
  `app/services/agent_task_dependencies.py`, `app/services/agent_task_reads.py`,
  and `app/services/agent_task_lifecycle.py`.
- `app/services/agent_task_worker.py` still exposes `18` functions spanning
  leases, stale recovery, finalization, failure handling, promotable-result
  checkpointing, processing, and the worker loop.
- `app/services/agent_task_verifications.py` still exposes `9` functions
  spanning search-harness verification, repair-case loading, draft-harness
  comprehension gates, semantic registry verification, and semantic grounded
  document verification.
- `tests/unit/test_agent_task_worker.py` is still a `624`-line root covering
  error classification, lease claiming, failure artifacts, runtime freshness,
  execution, cost and performance recording, checkpoint reuse, and retry
  behavior in one file.
- `tests/unit/test_agent_task_verifications.py` and
  `tests/unit/test_agent_task_verifications_drafts.py` already split some
  verification coverage, but the production root remains unsplit and still
  owns multiple search-harness and semantic verification families.
- `config/improvement_cases.yaml` currently has a deployed owner case for
  `app/services/agent_tasks.py` (`IC-4098E8370B88`) and prior deployed cases
  for the old `agent_task_actions` / `agent_task_context` roots, but it does
  not yet create dedicated current-state owner cases for
  `app/services/agent_task_worker.py` or
  `app/services/agent_task_verifications.py`.

## Closeout Summary

This packet resolves the remaining mixed worker and verification runtime debt
without reopening the already-reduced `agent_task_actions` or `agent_tasks`
facades:

- `app/services/agent_task_worker.py` now closes at `77` lines with `0`
  private helpers and forwards into `app/services/agent_task_worker_leases.py`
  at `223` lines, `app/services/agent_task_worker_finalization.py` at `253`
  lines, and `app/services/agent_task_worker_processing.py` at `155` lines.
- `app/services/agent_task_verifications.py` now closes at `111` lines with
  `0` private helpers and forwards into
  `app/services/agent_task_verifications_search_harness.py` at `369` lines and
  `app/services/agent_task_verifications_semantics.py` at `188` lines.
- Worker unit coverage now follows the owner split at `42`, `104`, `61`, and
  `462` lines across the root, lease, finalization, and processing test
  surfaces.
- Verification unit coverage now follows the owner split at `16`, `9`, `528`,
  and `366` lines across the root, draft-smoke, search-harness, and semantic
  test surfaces.
- `config/improvement_cases.yaml`, `config/hotspot_prevention.yaml`, and
  `config/hygiene_policy.yaml` now route and exact-ratchet both runtime roots
  and their owner-local successors under `IC-3F725D0A6C91` and
  `IC-86E1D4B72F0C`.
- The architecture probe no longer lists
  `app/services/agent_task_worker.py` or
  `app/services/agent_task_verifications.py` among the top hotspots, and the
  checkout still reports no Python cycles.

Later live-state alignment shows that this packet remains resolved, but the
broader rebaseline did not stay queue-empty: the current
`uv run docling-system-architecture-quality-report --summary` output now
reports `top_routed_hotspot_paths=["app/hotspot_prevention_classifier.py"]`.
The later child brief
`docs/hotspot_prevention_classifier_owner_rebaseline_milestone_plan.md` now
closes that reopened routed owner surface and returns the live queue to
`top_routed_hotspot_paths=[]` by routing the classifier root as a deferred
reduced facade instead of leaving it active.

## Verification Snapshot

The final closeout checkout passed the required gates:

- `git diff --check`
- `uv run ruff check ...`: pass for the worker, verification, and adjacent
  agent-task/runtime unit slice
- `uv run pytest -q ...`: `66 passed` for the focused worker, verification,
  action-lookup, runtime-health, and run-logic unit slice
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py tests/integration/test_agent_task_triage_roundtrip_search_harness.py tests/integration/test_agent_task_triage_roundtrip_search_harness_review.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py`: `13 passed`
- `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`: `6 passed`
- `uv run docling-system-agent-task-action-index`: pass
- `uv run docling-system-capability-contracts`: `valid=true`
- `uv run docling-system-improvement-case-validate`: `valid=true`
- `uv run docling-system-improvement-case-summary`: `case_count=63`,
  `status_counts={"measured":1,"deployed":62}`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `blocked=0`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `inherited budget debt: none`,
  `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=20`, `stale_facade_hotspot_count=20`,
  `max_hotspot_risk_score=471.06`, `top_routed_hotspot_paths=[]`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`: no Python cycles, and neither runtime root remains in the top hotspot list
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `2140 passed in 80.38s`

## Goal

Resolve the remaining agent-task runtime execution and verification debt so
that:

- `app/services/agent_task_worker.py` becomes a narrow public runtime
  execution facade at `max_lines <= 300` and `max_private_helpers <= 4`.
- `app/services/agent_task_verifications.py` becomes a narrow public
  verification facade at `max_lines <= 300` and `max_private_helpers <= 3`.
- The worker root routes lease management, failure and retry behavior,
  promotable-result checkpointing, and completion finalization into focused
  owner modules rather than keeping them in one runtime file.
- The verification root routes search-harness verification and semantic
  verification families into focused owner modules rather than keeping them in
  one mixed verification file.
- `app/services/agent_tasks.py` remains at or below its current exact facade
  budget of `324` lines / `0` private helpers unless Milestone 0 proves that
  the current public seam still owns non-forwarding mixed implementation.
- `app/services/agent_task_actions.py` remains at or below its current narrow
  facade shape and does not absorb new execution-family logic.
- Worker execution semantics, action names, context-builder names, output
  schema names and versions, failure-artifact contracts, approval behavior,
  context write behavior, and verification record behavior remain stable unless
  a later explicit contract-change packet says otherwise.
- Runtime, architecture, and DB-backed integration verification remains at
  least as strong as it is now.

## Non-Goals

- No API route redesign or agent-task schema rename.
- No ORM or migration work.
- No task-type rename, context-builder rename, output schema rename, or change
  to `/agent-tasks/actions` contract shape.
- No broad runtime-health rewrite outside the bounded worker seams needed to
  complete the split.
- No reopening of `app/services/agent_task_actions.py`,
  `app/services/agent_task_context.py`, or `app/services/agent_tasks.py` as if
  they were still the primary monoliths unless Milestone 0 proves regrowth in
  those exact roots.
- No weakening, deleting, or narrowing of runtime, worker, or DB-backed
  verification merely to satisfy a lower line count.
- No umbrella milestone commit that mixes this runtime packet with unrelated
  dirty README, queue-exhaustion, or other architecture follow-on work.

## Scope

In scope:

- `app/services/agent_task_worker.py`
- new `app/services/agent_task_worker_*.py` owner modules
- `app/services/agent_task_verifications.py`
- new `app/services/agent_task_verifications_*.py` owner modules
- `app/services/agent_tasks.py` only for explicit forwarding, import-seam, or
  route-hardening changes proven necessary by Milestone 0
- `app/services/agent_task_actions.py` only for explicit export or
  compatibility-forwarder changes proven necessary by Milestone 0
- `app/services/agent_task_action_lookup.py`
- `app/services/agent_task_verification_records.py`
- directly touched supporting seams such as `app/services/runtime.py`,
  `app/services/claim_support_policy_impacts.py`, `app/services/evidence.py`,
  and `app/services/storage.py` only where import direction or wrapper
  placement must be adjusted for the new owner modules
- `tests/unit/test_agent_task_worker.py`
- `tests/unit/test_agent_task_verifications.py`
- `tests/unit/test_agent_task_verifications_drafts.py`
- focused new `tests/unit/test_agent_task_worker_*.py` and
  `tests/unit/test_agent_task_verifications_*.py` siblings when the root tests
  split by owner family
- `tests/unit/test_agent_task_actions.py`
- `tests/unit/test_agent_task_action_lookup.py`
- `tests/unit/test_agent_tasks.py`
- `tests/unit/test_agent_tasks_api.py`
- `tests/unit/test_runtime_health.py`
- `tests/unit/test_runtime_service.py`
- `tests/unit/test_run_logic.py`
- `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `tests/integration/test_agent_task_triage_roundtrip.py`
- `tests/integration/test_agent_task_triage_roundtrip_search_harness.py`
- `tests/integration/test_agent_task_triage_roundtrip_search_harness_review.py`
- `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- `config/improvement_cases.yaml`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- this plan

Out of scope:

- search-service, evidence-owner, parser, UI, or DB-model follow-ons
- broad search-harness action-family rewrites unrelated to worker or
  verification execution
- historical queue-alignment or packet-exhaustion doc cleanup outside the
  minimum handoff/index updates this plan requires
- new product features in agent-task orchestration

## Owner Surfaces

- worker runtime boundary:
  `app/services/agent_task_worker.py`,
  new `app/services/agent_task_worker_*.py`,
  `tests/unit/test_agent_task_worker.py`,
  `tests/unit/test_runtime_health.py`,
  `tests/unit/test_runtime_service.py`,
  `tests/unit/test_run_logic.py`
- verification boundary:
  `app/services/agent_task_verifications.py`,
  new `app/services/agent_task_verifications_*.py`,
  `app/services/agent_task_verification_records.py`,
  `tests/unit/test_agent_task_verifications.py`,
  `tests/unit/test_agent_task_verifications_drafts.py`,
  `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`,
  `tests/integration/test_agent_task_triage_roundtrip.py`,
  `tests/integration/test_agent_task_triage_roundtrip_search_harness.py`,
  `tests/integration/test_agent_task_triage_roundtrip_search_harness_review.py`,
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- companion compatibility seams:
  `app/services/agent_tasks.py`,
  `app/services/agent_task_actions.py`,
  `app/services/agent_task_action_lookup.py`,
  `tests/unit/test_agent_task_actions.py`,
  `tests/unit/test_agent_task_action_lookup.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_agent_tasks_api.py`
- routing and governance:
  `config/improvement_cases.yaml`,
  `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  this plan

## Placement Rules

- Keep `app/services/agent_task_worker.py` as the public worker execution
  facade. New lease, stale-requeue, failure-artifact, retry, checkpoint, or
  finalization logic must land in focused `app/services/agent_task_worker_*.py`
  owners unless Milestone 0 proves the root facade itself is the right owner.
- Prefer worker owner names that match the executed concern boundary, such as
  `agent_task_worker_leases.py`,
  `agent_task_worker_finalization.py`, and
  `agent_task_worker_processing.py`, but preserve the owner split even if the
  exact filenames change during Milestone 0.
- Keep `app/services/agent_task_verifications.py` as the public verification
  facade. New search-harness verification and semantic verification logic must
  land in focused `app/services/agent_task_verifications_*.py` owners.
- Prefer verification owner names that match the executed concern boundary,
  such as `agent_task_verifications_search_harness.py`,
  `agent_task_verifications_semantics.py`, and
  `agent_task_verifications_support.py`, but do not create a generic dumping
  ground support module.
- `app/services/agent_tasks.py` may host only public orchestration entrypoints,
  explicit forwarders, and compatibility aliases after this packet. Do not
  move worker, verification, analytics, or lifecycle implementation back into
  that root.
- `app/services/agent_task_actions.py` may host only action catalog composition,
  explicit export shims, and execution entrypoints already required by the
  worker loop. Do not add new action-family implementation there.
- New tests must split by owner family. Do not replace one large root test with
  a new same-sized `*_support.py` sink.
- New guardrails must route future growth by owner family in
  `config/hotspot_prevention.yaml` and exact-ratchet the narrowed roots in
  `config/hygiene_policy.yaml`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet reopens already-resolved `agent_task_actions.py` or `agent_tasks.py` facades instead of routing the real runtime debt. | `docs/agent_task_orchestration_boundary_milestone_plan.md`, `docs/agent_task_residual_owner_family_milestone_plan.md`, `config/hotspot_prevention.yaml`, this plan | Milestone 0 freshness review plus `uv run docling-system-architecture-quality-report --summary` and targeted `rg` over routing docs/config | Any milestone selects `app/services/agent_task_actions.py` or `app/services/agent_tasks.py` as the primary split target without new owner-mixing evidence beyond explicit forwarders. | Draft a root-only split with no new worker or verification owner cases and confirm Milestone 0 blocks it. | A future session trusts churn reports alone and reopens a reduced facade because it still appears in hotspot output. |
| The worker split lowers line count but weakens retry, failure-artifact, lease, checkpoint, or finalization behavior. | `app/services/agent_task_worker.py`, new `app/services/agent_task_worker_*.py`, `tests/unit/test_agent_task_worker.py`, runtime and integration slices | Focused worker unit tests, runtime-health tests, DB-backed agent-task integration slice, and full DB-backed suite | Any moved worker path changes retry classification, skips failure artifacts, loses checkpoint reuse, or changes runtime freshness behavior without an explicit approved contract change. | Preserve and rerun the checkpoint-before-context-write-failure and checkpoint-reuse-on-retry tests after the split. | A future session extracts helper code, gets green on lint, but silently changes when promotable side effects are checkpointed or retried. |
| The verification split lowers line count but weakens search-harness, semantic registry, or grounded-document verification contracts. | `app/services/agent_task_verifications.py`, new `app/services/agent_task_verifications_*.py`, unit and integration verification tests | Focused verification unit slice, DB-backed orchestration slice, action index, capability contracts | Any moved verification path changes verification record fields, output schema names or versions, draft-migration rejection behavior, or release-gate reasoning without an explicit approved contract change. | Preserve and rerun the pre-context rejection tests plus a search-harness passed/failed verification pair after the split. | A future session moves helpers around and accidentally changes the verification payload or record semantics because only the happy path stayed covered. |
| The packet claims runtime debt is resolved while worker and verification roots remain unrouted under the control files. | `config/improvement_cases.yaml`, `config/hotspot_prevention.yaml`, `config/hygiene_policy.yaml`, handoff and index docs | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, `uv run docling-system-hotspot-prevention-check --strict`, handoff/index review | Any closeout lands without explicit worker and verification owner cases, without hotspot-prevention routing, or while handoff still says there is no queued standalone follow-on. | Create the plan and split code, but intentionally omit the new owner-case entries to confirm the validation and doc review would block closeout. | A future session completes the refactor locally, but the control plane still routes no next owner and later sessions regrow the same roots. |

## Milestone Sequence

### Milestone 0: Live Rebaseline And Owner Bootstrap
Outcome label: reduced

Scope:

- Reconfirm that the active debt is the worker and verification roots, not the
  already-reduced action, context, or task facades.
- Bootstrap fresh owner routing for `app/services/agent_task_worker.py` and
  `app/services/agent_task_verifications.py`.

Required work:

- Refresh live evidence from `git status -sb`,
  `uv run docling-system-architecture-quality-report --summary`,
  `python .../architecture_probe.py --format markdown --top 20`,
  `wc -l`, and targeted function-family review.
- Add dedicated improvement cases for
  `app/services/agent_task_worker.py` and
  `app/services/agent_task_verifications.py` with explicit verification stacks
  and acceptance conditions.
- Add hotspot-prevention routing for the worker and verification roots that
  blocks new lease, retry, failure-artifact, finalization, search-harness
  verification, and semantic verification implementation from regrowing the
  roots after the split.
- Tighten or add exact hygiene ratchets for the selected root and child owners
  that Milestone 1 and Milestone 2 create.

Milestone 0 is complete only if:

- the fresh evidence still points at worker and verification runtime ownership
  as the selected next packet, and
- the control files explicitly route those roots before implementation starts.

### Milestone 1: Worker Lease, Failure, And Finalization Split
Outcome label: resolved

Scope:

- Reduce `app/services/agent_task_worker.py` to a narrow public runtime
  execution facade.

Required work:

- Extract lease claim, heartbeat, and stale-task recovery into a focused worker
  owner module.
- Extract failure-artifact persistence, retry classification, promotable-result
  checkpointing, and success/failure finalization into focused worker owner
  modules.
- Keep the public worker entrypoints stable, including
  `claim_next_agent_task`, `process_agent_task`, and
  `run_agent_task_worker_loop`, unless Milestone 0 explicitly approves a
  different compatibility shape.
- Split `tests/unit/test_agent_task_worker.py` by owner family if the root test
  would otherwise remain an oversized mixed sink.

Milestone 1 is complete only if:

- `app/services/agent_task_worker.py` closes at `<= 300` lines and
  `<= 4` private helpers,
- no new worker owner exceeds the default `600`-line hygiene budget, and
- the worker focused unit and DB-backed integration gates pass without reducing
  failure or retry coverage.

### Milestone 2: Verification Family Split
Outcome label: resolved

Scope:

- Reduce `app/services/agent_task_verifications.py` to a narrow public
  verification facade.

Required work:

- Extract search-harness evaluation verification and draft-harness
  comprehension logic into a focused verification owner module.
- Extract semantic registry update verification and grounded-document
  verification into focused verification owner modules.
- Keep verification record creation, output schema names and versions, and
  public verification entrypoints stable.
- Split `tests/unit/test_agent_task_verifications.py` and
  `tests/unit/test_agent_task_verifications_drafts.py` by owner family when
  needed so the verification coverage follows the production ownership split.

Milestone 2 is complete only if:

- `app/services/agent_task_verifications.py` closes at `<= 300` lines and
  `<= 3` private helpers,
- no new verification owner exceeds the default `600`-line hygiene budget, and
- the search-harness, semantic, and DB-backed verification slices all pass
  without relaxing migration-rejection or verification-record assertions.

### Milestone 3: Companion Seam Hardening And Anti-Regrowth Gates
Outcome label: resolved

Scope:

- Preserve the reduced compatibility seams and prevent future regrowth.

Required work:

- Update `app/services/agent_tasks.py` only where explicit forwarding or import
  direction must change to use the new worker or verification owners.
- Update `app/services/agent_task_actions.py` only where explicit export shims
  or execution entrypoints must move to support the new worker shape.
- Add or refresh focused facade and lookup tests so future sessions cannot add
  mixed implementation back into the reduced roots.
- Refresh hotspot-prevention and hygiene contracts to match the post-split
  owner surfaces exactly.

Milestone 3 is complete only if:

- `app/services/agent_tasks.py` remains at or below `324` lines /
  `0` private helpers,
- `app/services/agent_task_actions.py` remains at or below its current narrow
  verified shape unless Milestone 0 approved a stricter exact ratchet, and
- the guardrails now route future worker and verification growth to the new
  owner modules rather than back into the reduced roots.

### Milestone 4: Full Runtime Closeout, Docs, And Commit
Outcome label: resolved

Scope:

- Prove the runtime lane end to end and close the packet durably.

Required work:

- Run the focused and full verification stacks.
- Update `config/improvement_cases.yaml`,
  `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`, and this plan with the final routed state,
  exact line budgets, verification results, and residual routing.
- Land the implementation, tests, docs, and control-file updates in one local
  atomic commit for this packet only.

Milestone 4 is complete only if:

- the full DB-backed suite passes,
- architecture, hotspot-prevention, hygiene, and improvement-case validation
  all pass,
- docs and handoff reflect the true post-closeout owner routing, and
- the milestone lands as a local atomic commit rather than a verified but
  uncommitted checkout.

## Required Implementation Artifacts

- A fresh worker owner-case packet in `config/improvement_cases.yaml` for
  `app/services/agent_task_worker.py`
- A fresh verification owner-case packet in `config/improvement_cases.yaml`
  for `app/services/agent_task_verifications.py`
- New focused `app/services/agent_task_worker_*.py` owners for lease,
  finalization, and processing support, or equivalent same-boundary names
- New focused `app/services/agent_task_verifications_*.py` owners for
  search-harness and semantic verification families, or equivalent
  same-boundary names
- Focused worker and verification unit-test siblings when the root tests split
- Updated hotspot-prevention and hygiene controls for the new owners
- Updated architecture index and handoff routing that make this packet and its
  closeout discoverable to later sessions

## Required Documentation And Handoff Updates

- `docs/agent_task_runtime_and_verification_boundary_milestone_plan.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- `config/improvement_cases.yaml`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`

Before closeout, the handoff must name:

- the latest resolved bounded implementation brief,
- whether a new queued standalone follow-on remains after this packet, and
- the exact worker and verification owner routing that replaced the mixed
  runtime roots.

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/agent_task_worker.py app/services/agent_task_worker_*.py app/services/agent_task_verifications.py app/services/agent_task_verifications_*.py app/services/agent_tasks.py app/services/agent_task_actions.py app/services/agent_task_action_lookup.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_task_worker_*.py tests/unit/test_agent_task_verifications.py tests/unit/test_agent_task_verifications_*.py tests/unit/test_agent_task_verifications_drafts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_tasks_api.py tests/unit/test_runtime_health.py tests/unit/test_runtime_service.py tests/unit/test_run_logic.py`
- `uv run pytest -q tests/unit/test_agent_task_worker.py tests/unit/test_agent_task_worker_*.py tests/unit/test_agent_task_verifications.py tests/unit/test_agent_task_verifications_*.py tests/unit/test_agent_task_verifications_drafts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_tasks_api.py tests/unit/test_runtime_health.py tests/unit/test_runtime_service.py tests/unit/test_run_logic.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py tests/integration/test_agent_task_triage_roundtrip_search_harness.py tests/integration/test_agent_task_triage_roundtrip_search_harness_review.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`
- `uv run docling-system-agent-task-action-index`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- Milestone 0 creates dedicated, validated owner cases for
  `app/services/agent_task_worker.py` and
  `app/services/agent_task_verifications.py`, and the control files route
  those roots explicitly before broad implementation begins.
- `app/services/agent_task_worker.py` closes at `<= 300` lines and
  `<= 4` private helpers while preserving public worker entrypoints and
  runtime behavior.
- `app/services/agent_task_verifications.py` closes at `<= 300` lines and
  `<= 3` private helpers while preserving public verification entrypoints,
  output schema metadata, verification record behavior, and draft-migration
  rejection behavior.
- `app/services/agent_tasks.py` remains at or below its current exact verified
  facade budget and does not regain dependency, lifecycle, detail, or trace
  implementation logic.
- `app/services/agent_task_actions.py` remains a narrow composition facade and
  does not regain new action-family implementation logic.
- Focused unit tests, focused DB-backed integration tests, architecture import
  tests, and the full DB-backed suite all pass without newly skipped coverage.
- `uv run docling-system-hotspot-prevention-check --strict`,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-improvement-case-validate`,
  `uv run docling-system-architecture-inspect`, and
  `uv run docling-system-capability-contracts` all remain green.
- The final closeout updates this plan, `docs/agentic_architecture_index.md`,
  and `docs/SESSION_HANDOFF.md` together with the control files in the same
  local atomic commit.

## Stop Conditions

- Stop and write a narrower child packet if Milestone 0 shows the real
  remaining debt is in a focused owner family such as search-harness,
  claim-support, or semantic-governance support modules rather than the worker
  or verification roots themselves.
- Stop if the split would require a task schema change, API contract change,
  task-type rename, or broader runtime-health redesign.
- Stop if the only way to get green would be to weaken runtime, worker,
  integration, or verification assertions.
- Stop if the rebaseline shows `app/services/agent_tasks.py` or
  `app/services/agent_task_actions.py` would need to regrow beyond their
  current verified facade contracts just to host the new owners.
- Stop if unrelated dirty worktree changes in the same touched files appear
  and cannot be cleanly separated from this packet.

## Local Commit Closeout Policy

- Each milestone must close with local verification before it is marked
  complete.
- A milestone is complete only after the required docs, handoff, and control
  files are updated and committed together with the code and tests for that
  milestone.
- Do not stage unrelated dirty worktree changes. Stage only the verified
  worker, verification, control-file, and doc slices for this packet.
- Do not mark Milestone 4 `resolved` until the full DB-backed suite, the
  runtime or architecture control gates, and the docs/handoff closeout all
  pass in the same checkout.

## Residual Risks And Next Milestone Routing

- If `tests/unit/test_agent_task_worker.py` remains above the default
  `600`-line hygiene budget after the production split, route a focused
  worker-test child packet instead of stretching this packet indefinitely.
- If `tests/unit/test_agent_task_verifications_drafts.py` or the selected
  integration roundtrip surfaces remain the next major sinks after the
  production split, route a focused verification-test child packet with the
  new owner boundaries already in place.
- If Milestone 0 proves the worker and verification roots are only symptoms of
  a deeper runtime-health or claim-support coupling issue, stop and route the
  remaining debt through a narrower owner-specific child plan rather than
  pretending this packet resolved it.
