# Claim Support Judge Integration Residual Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally on 2026-05-18 after the routed hotspot queue selected
`IC-40CA7C1FFA84` as the next bounded test-family packet.
Owner context: residual claim-support integration compatibility and smoke
coverage rooted at
`tests/integration/test_claim_support_judge_evaluation_roundtrip.py` after the
earlier high-value paydown split moved the broad activation, change-impact,
waiver, replay-alert, and mined-failure scenarios into focused sibling tests
but left a 702-line shared support sink and a 632-line replay-alert promotions
surface.

## Purpose

Resolve the remaining claim-support integration debt without pretending the
339-line residual roundtrip smoke file is still the real problem.

The actual residual risk at selection time was twofold:

- shared family-local setup and governance logic had reconcentrated into
  `tests/integration/claim_support_judge_evaluation_roundtrip_support.py` at
  702 lines
- replay-alert promotion and candidate-coverage assertions had reconcentrated
  into
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`
  at 632 lines

This packet closes that debt by deleting the old shared support sink, replacing
it with focused support owners under the support budget, splitting replay-alert
coverage out of the promotions surface, and making the residual smoke root a
durably routed hotspot-prevention trap instead of a vague open owner.

## Current Evidence

- Live `wc -l` after the packet records:
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py=339`,
  `tests/integration/claim_support_policy_integration_task_support.py=13`,
  `tests/integration/claim_support_policy_change_impact_support.py=277`,
  `tests/integration/claim_support_policy_activation_governance_assertions.py=344`,
  `tests/integration/claim_support_policy_activation_governance_triggers.py=75`,
  `tests/integration/claim_support_policy_change_impacts_replay_alert_support.py=381`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_coverage.py=152`,
  and
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py=510`.
- The selected activation, change-impact, governance, waiver, and mined-failure
  siblings now measure `439`, `351`, `494`, `356`, `341`, `401`, and `293`
  lines respectively, so no selected scenario file exceeds the default
  `600`-line hygiene budget.
- `config/hotspot_prevention.yaml` did not previously govern
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`, which
  meant a future session could have regrown the residual smoke root without a
  checked-in trap.

## Goal

Resolve the selected residual packet so that:

- the claim-support judge roundtrip root remains a narrow smoke surface at or
  below `800` lines
- every new family-local support module stays at or below `400` lines
- replay-alert candidate and waiver coverage no longer hides inside the
  promotions surface
- hotspot prevention, hygiene ratchets, improvement-case state, and queue docs
  all route the next follow-on away from this family

## Acceptance Criteria

- `tests/integration/test_claim_support_judge_evaluation_roundtrip.py` remains
  at or below `800` lines as a smoke-only surface.
- Every new family-local support module remains at or below `400` lines and its
  exact private-helper ratchet.
- Replay-alert promotions and replay-alert coverage stay in separate owner
  files.
- `config/hotspot_prevention.yaml`, `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` all point to the same
  post-closeout queue state.
- Atomic commit rule: this milestone is complete only when the verified packet
  is staged and landed as one atomic commit with its closeout docs.
- Complete-after-commit rule: the packet is not complete until the atomic
  milestone commit exists.

## Non-Goals

- No reopening of `app/services/claim_support_*` service-boundary work.
- Anti-test-weakening rule: do not weaken tests, delete assertions, broaden
  skips, or narrow negative-path coverage just to improve the file counts.
- No new broad `tests/integration/claim_support_helpers.py` sink.
- No routed test-packet work outside the selected claim-support integration
  family.

## Scope

In scope:

- `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- `tests/integration/claim_support_policy_integration_task_support.py`
- `tests/integration/claim_support_policy_change_impact_support.py`
- `tests/integration/claim_support_policy_activation_governance_assertions.py`
- `tests/integration/claim_support_policy_activation_governance_triggers.py`
- `tests/integration/claim_support_policy_change_impacts_replay_alert_support.py`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py`
- `tests/integration/test_claim_support_policy_activation_waivers.py`
- `tests/integration/test_claim_support_policy_activation_change_impacts_roundtrip.py`
- `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`
- `tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py`
- `tests/integration/test_claim_support_policy_change_impacts_replay_alert_coverage.py`
- `tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`
- `tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py`
- `tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
- `app/hotspot_prevention_classifier_support.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `tests/unit/test_hotspot_prevention.py`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

Out of scope:

- technical-report harness routing work
- retrieval-learning or DB-model residual test packets
- unrelated claim-support service or API implementation

## Placement Rules

- Keep `tests/integration/test_claim_support_judge_evaluation_roundtrip.py` as
  a residual smoke and compatibility surface only.
- Keep family-local helpers in focused support files with explicit bounded
  ownership; no support file may exceed `400` lines.
- Keep replay-alert waiver/candidate coverage outside the promotions root when
  that coverage does not assert promotion governance directly.
- Route future root-file growth through hotspot prevention into the focused
  sibling tests or support modules listed in the routing metadata.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The residual root regrows because it still looks like the default place to add new claim-support scenarios. | `tests/integration/test_claim_support_judge_evaluation_roundtrip.py` | hotspot-prevention strict gate plus `tests/unit/test_hotspot_prevention.py` | any new scenario group or helper lands in the root smoke file | add a new replay-alert scenario to the root and confirm the gate blocks it | future Codex dumps a new change-impact branch back into the residual root |
| Family-local support debt just moves from one filename to another. | `tests/integration/claim_support_policy_*support.py`, `tests/integration/claim_support_policy_activation_governance_*` | exact hygiene ratchets | any support file exceeds `400` lines or its exact helper budget | regrow a new support module past `400` lines and confirm hygiene fails | future Codex replaces one support sink with a renamed support sink |
| Replay-alert promotions regrow because waiver/candidate coverage and promotion governance stay mixed. | replay-alert coverage/promotions siblings | focused Ruff and DB-backed integration slice | promotions file grows by absorbing non-promotion coverage again | move waiver candidate assertions back into promotions and confirm the packet becomes dishonest | future Codex adds unrelated candidate checks to the promotions file because it already touches replay alerts |
| Queue docs still select this family after the residual packet is locally closed. | handoff, architecture index, broader coordination brief | doc closeout review plus architecture-quality reroute | the current queue still names this packet as next after closeout | leave the top queue block unchanged and confirm routing drift remains | future Codex reopens this family instead of advancing to the technical-report harness packet |

## Milestone Sequence

### Milestone 0. Live Rebaseline And Split Integrity Lock
Outcome label: resolved

Refresh the live routed-queue evidence, measure the post-split file sizes, and
prove the residual debt is the support/promotions family rather than the root
smoke file itself.

### Milestone 1. Family-Local Support Decomposition
Outcome label: resolved

Delete the legacy 702-line support sink and replace it with focused setup,
change-impact, governance-assertion, governance-trigger, and replay-alert
support owners that remain under the support budget.

### Milestone 2. Replay-Alert Coverage Separation And Durable Routing
Outcome label: resolved

Split waiver/candidate coverage out of the replay-alert promotions surface,
exact-ratchet the landing-zone family, route the residual root through hotspot
prevention, and refresh the owner-case plus queue docs.

## 2026-05-18 Closeout Update

Milestones 0 through 2 are resolved locally in the current checkout.

- Deleted `tests/integration/claim_support_judge_evaluation_roundtrip_support.py`.
- Added focused support owners at `13`, `277`, `344`, `75`, and `381` lines in
  `claim_support_policy_integration_task_support.py`,
  `claim_support_policy_change_impact_support.py`,
  `claim_support_policy_activation_governance_assertions.py`,
  `claim_support_policy_activation_governance_triggers.py`, and
  `claim_support_policy_change_impacts_replay_alert_support.py`.
- Added
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_coverage.py`
  at `152` lines and reduced
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`
  to `510` lines.
- Wired `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
  into hotspot prevention as a deferred reduced facade routed to the focused
  claim-support integration family.
- Exact-ratcheted the selected claim-support landing-zone files in
  `config/hygiene_policy.yaml` and transitioned `IC-40CA7C1FFA84` from `open`
  to `verified`.

## Verification

Packet-local verification is recorded in the same milestone closeout:

- `git diff --check`: pass
- `uv run ruff check ...`: pass
- `uv run pytest -q tests/unit/test_hotspot_prevention.py`: `19 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs ...`: `18 passed`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `changed_hotspots=1`, `blocked=0`, `allowed=2`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-validate`: `valid=true`
- `uv run docling-system-improvement-case-summary`:
  `status_counts={"measured":1,"deployed":16,"open":30,"verified":12}`
- `uv run docling-system-architecture-quality-report --summary`:
  `top_routed_hotspot_paths=["tests/integration/test_technical_report_harness_roundtrip.py","tests/unit/test_hotspot_prevention.py"]`,
  `stale_facade_hotspot_count=8`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  `0` Python cycles and no code file above `799`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `2087 passed`

The handoff, index, and broader coordination brief must be refreshed in the
same packet so the next routed follow-on advances to the technical-report
harness family instead of circling back to this claim-support residual.

## Stop Conditions

- Stop if the residual support family cannot stay under the `400`-line support
  budget without reintroducing duplication or weakening assertions.
- Stop if the hotspot-prevention trap for the residual root cannot be added
  without reopening already-closed facade-routing behavior elsewhere.
- Stop if the queue docs cannot be refreshed consistently enough to make
  `tests/integration/test_technical_report_harness_roundtrip.py` the next
  active routed packet after this closeout.
