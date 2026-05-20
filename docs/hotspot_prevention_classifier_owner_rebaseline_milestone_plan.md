# Hotspot Prevention Classifier Owner Rebaseline Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: Milestone 0 resolved locally on 2026-05-19 through the standalone
packet bootstrap and coordination-doc reroute. Milestones 1 through 3 remain
pending.
Owner context: fresh broader-reselect packet after
`docs/agent_task_runtime_and_verification_boundary_milestone_plan.md`
resolved the worker and verification follow-on. The routed queue is active
again, and the current live architecture-quality summary now selects
`app/hotspot_prevention_classifier.py` as the honest next owner surface.

## Purpose

Resolve the next classifier-family technical and mechanical debt pass without
pretending the already-resolved 2026-05-16 hotspot-prevention family packet is
still the active child brief.

The current weakness is twofold:

- the live routed queue now selects `app/hotspot_prevention_classifier.py`,
  but the checked-in coordination docs previously still said no fresh child
  packet existed for that owner surface
- the routed root is only a `360` line / `4` definition dispatcher, while the
  real family complexity is distributed across helper and rule siblings such as
  `app/hotspot_prevention_classifier_support.py` at `486` lines with `33`
  defs/classes, `app/hotspot_prevention_claim_support_rules.py` at `436`
  lines, `app/hotspot_prevention_classifier_service_rules.py` at `384` lines,
  and `app/hotspot_prevention_classifier_schema_facades.py` at `204` lines

This packet exists to rebaseline that family honestly before another session
blindly reopens the 360-line dispatcher or, in the opposite failure mode,
keeps adding more rule branches to the helper sink because the queue only names
the root.

## Current Evidence

Milestone 0 rebaseline from the live checkout on 2026-05-19:

```text
git status -sb
  ## main...origin/main [ahead 2]
   M README.md

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=20
  legibility_gap_count=0
  stale_facade_hotspot_count=19
  max_hotspot_risk_score=471.06
  top_routed_hotspot_paths=["app/hotspot_prevention_classifier.py"]

uv run docling-system-improvement-case-summary
  case_count=63
  status_counts={"measured":1,"deployed":62}
  actionable_buckets.open_unconverted_count=0
  actionable_buckets.verified_undeployed_count=0

uv run docling-system-hygiene-check
  inherited budget debt: none
  new hygiene regressions: none

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  app/hotspot_prevention_classifier.py: 20 revisions, 360 lines, score 7200
  app/hotspot_prevention_classifier.py remains the first live non-trap routed owner
  Python cycles: none detected

wc -l app/hotspot_prevention_classifier.py \
  app/hotspot_prevention_classifier_support.py \
  app/hotspot_prevention_classifier_service_rules.py \
  app/hotspot_prevention_classifier_boundary_rules.py \
  app/hotspot_prevention_classifier_schema_facades.py \
  app/hotspot_prevention_classifier_agent_task_runtime_rules.py \
  app/hotspot_prevention_claim_support_rules.py \
  tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/unit/test_hotspot_prevention_family_rules.py \
  tests/unit/test_hotspot_prevention_wrapper_rules.py \
  tests/unit/hotspot_prevention_test_support.py
     360 app/hotspot_prevention_classifier.py
     486 app/hotspot_prevention_classifier_support.py
     384 app/hotspot_prevention_classifier_service_rules.py
     177 app/hotspot_prevention_classifier_boundary_rules.py
     204 app/hotspot_prevention_classifier_schema_facades.py
     125 app/hotspot_prevention_classifier_agent_task_runtime_rules.py
     436 app/hotspot_prevention_claim_support_rules.py
     341 tests/unit/test_hotspot_prevention.py
     372 tests/unit/test_hotspot_prevention_policy_contracts.py
     318 tests/unit/test_hotspot_prevention_family_rules.py
     296 tests/unit/test_hotspot_prevention_wrapper_rules.py
      50 tests/unit/hotspot_prevention_test_support.py

python - <<'PY'
from pathlib import Path
for path_str in [
    "app/hotspot_prevention_classifier.py",
    "app/hotspot_prevention_classifier_support.py",
    "app/hotspot_prevention_classifier_service_rules.py",
    "app/hotspot_prevention_classifier_boundary_rules.py",
    "app/hotspot_prevention_classifier_schema_facades.py",
    "app/hotspot_prevention_classifier_agent_task_runtime_rules.py",
    "app/hotspot_prevention_claim_support_rules.py",
]:
    text = Path(path_str).read_text().splitlines()
    defs = sum(
        1
        for line in text
        if line.startswith("def ")
        or line.startswith("async def ")
        or line.startswith("class ")
    )
    priv = sum(
        1
        for line in text
        if line.startswith("def _") or line.startswith("async def _")
    )
    print(f"{path_str} defs_or_classes={defs} private_helpers={priv}")
PY
  app/hotspot_prevention_classifier.py defs_or_classes=4 private_helpers=1
  app/hotspot_prevention_classifier_support.py defs_or_classes=33 private_helpers=1
  app/hotspot_prevention_classifier_service_rules.py defs_or_classes=6 private_helpers=0
  app/hotspot_prevention_classifier_boundary_rules.py defs_or_classes=7 private_helpers=0
  app/hotspot_prevention_classifier_schema_facades.py defs_or_classes=8 private_helpers=6
  app/hotspot_prevention_classifier_agent_task_runtime_rules.py defs_or_classes=2 private_helpers=0
  app/hotspot_prevention_claim_support_rules.py defs_or_classes=8 private_helpers=1
```

Mechanical-drift evidence captured during Milestone 0:

- the live summary routes `app/hotspot_prevention_classifier.py`
- the checked-in `build/architecture-governance/architecture_quality_report.json`
  still reports `top_routed_hotspot_paths=[]`
- `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md`
  previously said the queue was active again but still had no fresh child brief
- `docs/hotspot_prevention_family_boundary_milestone_plan.md` is already
  resolved, so reopening it as the active packet would be false routing rather
  than honest continuation

## Milestone 0 Closeout Summary

Milestone 0 resolves the control-plane ambiguity for the routed classifier
family:

- this standalone child brief now exists and records the live 2026-05-19
  classifier-family rebaseline
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` now point to this packet
  as the next bounded implementation brief instead of saying that no child
  brief exists
- the packet explicitly treats the 360-line root as the current routed owner
  while refusing to assume that the dispatcher itself is the whole remaining
  mixed surface

Milestone 0 does not resolve the classifier-family code debt. It resolves the
mechanical debt of having an active routed owner with no active child packet
and no explicit rebaseline for whether the true next split belongs in the root
dispatcher, the shared support sink, or a narrower rule cluster.

## Goal

Resolve the classifier-family debt so that:

- the next code-owning pass works from a current routed packet rather than a
  stale resolved brief
- `app/hotspot_prevention_classifier.py` either remains a narrow dispatcher
  with explicit family routing or is reduced further if Milestone 1 proves the
  root itself still owns mixed implementation
- `app/hotspot_prevention_classifier_support.py` stops functioning as an
  implicit generic helper sink if Milestone 1 proves its current `33`
  defs/classes mix is the real hard-to-change surface
- schema-facade, service-rule, boundary-rule, runtime-rule, and claim-support
  classifier families each have an honest owner boundary rather than growing by
  convenience inside the nearest existing helper file
- hotspot-prevention tests remain split by contract family, with the root
  smoke test staying narrow and family-specific growth moving into focused
  siblings
- the post-closeout routed queue no longer selects
  `app/hotspot_prevention_classifier.py` by default unless the live system
  proves a new classifier-family regrowth later

## Non-Goals

- No reopening of the already-resolved
  `docs/hotspot_prevention_family_boundary_milestone_plan.md` as if it were
  still the active child packet.
- No weakening of `uv run docling-system-hotspot-prevention-check --strict`,
  hotspot-prevention unit coverage, or hygiene ratchets merely to keep the
  root out of the routed queue.
- No broad rewrite of every historical hotspot classifier rule family.
- No unrelated rework of `app/services/search.py`, `app/services/evaluations.py`,
  `app/services/semantics.py`, or `app/services/agent_tasks.py` beyond the
  family-local classifier rules and tests needed to close this packet.
- No staging or rollback of the pre-existing `README.md` modification unless a
  later user request explicitly expands scope to that worktree delta.

## Scope

In scope:

- `app/hotspot_prevention_classifier.py`
- `app/hotspot_prevention_classifier_support.py`
- `app/hotspot_prevention_classifier_service_rules.py`
- `app/hotspot_prevention_classifier_boundary_rules.py`
- `app/hotspot_prevention_classifier_schema_facades.py`
- `app/hotspot_prevention_classifier_agent_task_runtime_rules.py`
- `app/hotspot_prevention_claim_support_rules.py`
- family-local follow-on modules introduced under the same prefix if Milestone 1
  or 2 proves the current helper mix still spans multiple owners
- `tests/unit/test_hotspot_prevention.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `tests/unit/test_hotspot_prevention_family_rules.py`
- `tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `tests/unit/hotspot_prevention_test_support.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `docs/hotspot_prevention_classifier_owner_rebaseline_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

Out of scope:

- unrelated route, worker, search, evaluation, semantics, or ORM code
- non-hotspot-prevention tests outside the family-local coverage needed to
  close this packet
- README cleanup that predates this packet

## Owner Surfaces

- routed root dispatcher: `app/hotspot_prevention_classifier.py`
- shared helper sink: `app/hotspot_prevention_classifier_support.py`
- service-family classifier rules:
  `app/hotspot_prevention_classifier_service_rules.py`
- boundary and compatibility-family rules:
  `app/hotspot_prevention_classifier_boundary_rules.py`
- schema facade classifier rules:
  `app/hotspot_prevention_classifier_schema_facades.py`
- runtime classifier rules:
  `app/hotspot_prevention_classifier_agent_task_runtime_rules.py`
- claim-support classifier rules:
  `app/hotspot_prevention_claim_support_rules.py`
- companion hotspot-prevention test family:
  `tests/unit/test_hotspot_prevention*.py`,
  `tests/unit/hotspot_prevention_test_support.py`
- control-plane routing and ratchets:
  `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`

## Placement Rules

- Keep `app/hotspot_prevention_classifier.py` as the public dispatch entry for
  `classify_changed_file`, `classify_python_addition`, and
  `classify_hotspot_implementation`. Do not move public entrypoint ownership
  into a hidden helper sink.
- If Milestone 1 proves the actual mixed debt lives in helper utilities, split
  those helpers into family-local modules under the same
  `app/hotspot_prevention_classifier_*` prefix rather than appending more
  logic to `app/hotspot_prevention_classifier_support.py`.
- If Milestone 2 proves schema-facade or service-rule logic still spans too
  many owners, extract within the classifier family first. Do not push that
  debt back into the protected app/service facades the classifier guards.
- Keep `tests/unit/test_hotspot_prevention.py` as analyzer smoke and
  compatibility coverage only. New family-specific negative paths belong in the
  focused policy-contract, blocked-family, wrapper, or new family-local test
  siblings.
- Treat the checked-in `build/architecture-governance/architecture_quality_report.json`
  as generated state. Regenerate it during closeout, but do not make the packet
  depend on stale saved values when live commands disagree.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet reopens the 360-line dispatcher even though the real mixed debt lives in helper sinks. | this plan, `app/hotspot_prevention_classifier.py`, helper siblings | Milestone 0 rebaseline evidence plus staged `wc -l` and def-count review | Milestone 1 starts by splitting only the root while `app/hotspot_prevention_classifier_support.py` and sibling rule files remain the actual mixed surfaces. | Draft a root-only split without a helper-family evidence review and confirm Milestone 0 blocks it. | A future session sees the routed root path and edits only that file because it is the operational queue label. |
| The root shrinks only because helper debt is dumped into another generic support sink. | `app/hotspot_prevention_classifier_support.py`, new family-local modules, hygiene policy | `uv run docling-system-hygiene-check`, staged `wc -l`, focused hotspot-prevention tests | Any touched helper sibling regrows above its same-milestone ratchet without a narrower owner boundary or new packet routing. | Move a mixed helper block into a new generic support file and confirm closeout rejects it. | A future session "fixes" the hotspot by renaming the sink and keeping the same owner mix. |
| Family-specific rule growth lands in the wrong classifier module because the existing file already imports the needed helpers. | service, boundary, schema, runtime, and claim-support classifier modules | focused `pytest` slice plus targeted `rg` review of touched rule families | A new rule family lands in the nearest existing classifier file without matching owner scope or tests. | Add a schema-facade rule to the service-rules module and confirm the review contract fails. | A future session appends "one more rule branch" wherever the import already exists. |
| The packet closes locally but the control plane still says there is no child brief or still points at the old resolved family plan. | handoff, architecture index, broader coordination brief | `git diff --check` plus targeted `rg` review across current-state docs | Any closeout leaves `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, or the broader brief still saying no classifier child packet exists. | Update only the plan file and leave the handoff stale. | A future session resumes from the handoff and assumes the queue is active but unplanned. |
| Mechanical drift returns because the saved architecture-quality artifact is not refreshed when the live summary changes. | generated report artifact, plan, handoff | live summary command plus regenerated report readback | The live queue and the saved report disagree at closeout. | Close the packet from `--summary` output only and never regenerate the saved report. | A future session trusts the checked-in artifact and routes to an already-retired or nonexistent packet. |

## Milestone Sequence

### Milestone 0: Live Rebaseline And Packet Bootstrap

Outcome label: resolved.

Create the standalone child brief, refresh the classifier-family evidence, and
update current-state routing docs so the active queue has an explicit packet
again.

Milestone 0 is complete only if:

- this plan exists as the active classifier-family child brief
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` all point to this packet
  as the next bounded implementation brief
- the packet records the live mismatch between the routed queue and the stale
  saved architecture-quality artifact
- the packet explicitly stops root-only implementation if the helper-family
  evidence shows the current routed root is only a label for a deeper sink

### Milestone 1: Dispatcher And Shared Helper Owner Split

Outcome label: reduced.

Use the Milestone 0 evidence to decide whether the real mixed surface is the
root dispatcher or the shared helper sink, then split the chosen owner into
family-local modules with explicit responsibilities.

Expected implementation shape:

- keep the public dispatch surface narrow in
  `app/hotspot_prevention_classifier.py`
- move mixed helper groups out of
  `app/hotspot_prevention_classifier_support.py` if its current 33
  defs/classes still span multiple unrelated concerns
- add focused family-local tests rather than regrowing the root analyzer smoke
  file

Milestone 1 must stop and write a narrower child packet if the evidence shows
that only one subordinate family, such as schema-facade helpers, is actually
mixed enough to justify a split.

### Milestone 2: Rule-Family Clarification And Control-Plane Routing

Outcome label: reduced.

Clarify the remaining rule-family boundaries, then add or refresh the control
plane needed to keep the reduced classifier family honest.

Expected closeout work:

- tighten `config/hotspot_prevention.yaml` and `config/hygiene_policy.yaml`
  for the post-split classifier family
- add or refresh improvement-case entries in `config/improvement_cases.yaml`
  for the actual owner surfaces touched by the split
- keep `tests/unit/test_hotspot_prevention.py` narrow while routing family
  growth into focused siblings

### Milestone 3: Queue Reroute And Durable Closeout

Outcome label: resolved.

Regenerate the architecture-quality artifact, rerun the routed queue, and
either retire the classifier root from the active queue or stop and draft
exactly one narrower child follow-on if live evidence still names a different
classifier-family owner.

Milestone 3 is complete only if:

- the live `uv run docling-system-architecture-quality-report --summary`
  output no longer selects `app/hotspot_prevention_classifier.py` by default,
  or it selects a narrower family-local successor that is explicitly routed
- the saved `build/architecture-governance/architecture_quality_report.json`
  is regenerated to the same routed truth
- handoff, index, broader coordination brief, and this plan all agree on the
  next state

## Required Implementation Artifacts

- updated classifier family modules under `app/hotspot_prevention_classifier*.py`
- updated family-local hotspot-prevention tests
- refreshed `config/hotspot_prevention.yaml`
- refreshed `config/hygiene_policy.yaml`
- refreshed `config/improvement_cases.yaml`
- regenerated `build/architecture-governance/architecture_quality_report.json`
- updated handoff and architecture-index docs

## Required Documentation And Handoff Updates

- `docs/hotspot_prevention_classifier_owner_rebaseline_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- any immediately adjacent resolved child brief whose summary would otherwise
  still say that no classifier packet exists

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/hotspot_prevention_classifier.py app/hotspot_prevention_classifier_support.py app/hotspot_prevention_classifier_service_rules.py app/hotspot_prevention_classifier_boundary_rules.py app/hotspot_prevention_classifier_schema_facades.py app/hotspot_prevention_classifier_agent_task_runtime_rules.py app/hotspot_prevention_claim_support_rules.py tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_policy_contracts.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py tests/unit/hotspot_prevention_test_support.py`
- `uv run pytest -q tests/unit/test_hotspot_prevention.py tests/unit/test_hotspot_prevention_policy_contracts.py tests/unit/test_hotspot_prevention_family_rules.py tests/unit/test_hotspot_prevention_wrapper_rules.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-architecture-quality-report`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- targeted `rg` review proving the same routed-packet truth appears in this
  plan, the handoff, the architecture index, and the broader coordination
  brief

## Acceptance Criteria

- Milestone 0 is resolved only when the active routed classifier owner has a
  durable standalone child brief and the current-state docs point to it.
- Later code milestones must prove whether the root dispatcher or one of the
  family-local helper sinks is the real mixed owner before moving code.
- No classifier-family closeout is accepted if the root looks smaller only
  because mixed helper logic was moved into another uncontrolled sink.
- The final closeout must keep hotspot prevention, hygiene, improvement-case
  validation, and architecture inspection green without weakening tests or
  ratchets.
- The final closeout must either route the root off the active queue or name
  one narrower successor packet explicitly.

## Stop Conditions

- Stop and write a narrower child packet if Milestone 0 shows the actual owner
  surface is a subordinate family such as schema-facade helpers rather than the
  broader classifier family.
- Stop if the only way to retire the routed root is to weaken
  `docling-system-hotspot-prevention-check --strict`, delete controlled
  violation coverage, or relax hygiene ratchets.
- Stop if the saved architecture-quality artifact cannot be regenerated to the
  same routed truth as the live summary.
- Stop if the required closeout would need the unrelated `README.md` delta to
  be staged or reverted.

## Local Commit Closeout Policy

- Milestone 0 may close with one docs-only atomic commit containing this new
  plan plus the handoff, architecture index, and broader coordination brief
  updates only.
- Later implementation milestones must stage only the verified classifier
  family, control-plane, generated-artifact, and handoff/doc slices touched by
  that milestone.
- Do not stage the pre-existing `README.md` modification with this packet
  unless a later explicit user request broadens scope to that work.

## Residual Risks And Next Milestone Routing

- The most likely remaining risk is that the routed root is only a dispatcher
  label and the real mixed debt lives in one narrower helper family. If
  Milestone 1 proves that, stop and write the narrower child packet rather than
  forcing the whole classifier family through one oversized split.
- If Milestone 3 retires the root successfully, route the next packet from the
  refreshed live `top_routed_hotspot_paths` output rather than from this
  packet's assumptions.
