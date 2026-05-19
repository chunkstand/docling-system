# Stale Open Registry Closeout Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved through the 2026-05-19 docs-only stale-open registry
closeout. Packet A of
`docs/remaining_packet_queue_resolution_milestone_plan.md` is now complete,
the nine retirement-ready `open` cases are recorded as deployed, and Packet B
verified-to-deployed closeout is the next queued packet.
Owner context: docs-only closeout sweep for the stale `open` cases that were
already under budget and already described as resolved, reduced, or
retirement-ready in durable repo artifacts.

## Purpose

Close the stale registry gap without reopening already-reduced code packets.

The remaining weakness was mechanical rather than architectural. The registry
still listed nine cases as `open` even though the live checkout and their own
packet docs already showed the governed families below budget. This packet
converts those stale records to honest deployed state, refreshes the queue
docs, and leaves only the two genuinely code-owning residual test packets
open.

## Scope

In scope:

- `config/improvement_cases.yaml`
- `docs/stale_open_registry_closeout_milestone_plan.md`
- `docs/remaining_packet_queue_resolution_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/evidence_residual_owner_family_milestone_plan.md`
- `docs/evidence_claim_support_replay_alerts_boundary_milestone_plan.md`
- `docs/ui_module_residual_owner_family_milestone_plan.md`
- `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`

Out of scope:

- production or test source edits
- Packet B verified-case deployment
- Packet C / Packet D successor splits

## Current Evidence

Milestone 0 rebaseline from the live checkout on 2026-05-19 confirmed that the
Packet A cases were still below budget and no longer required code work:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":40,"open":11,"verified":9}

uv run docling-system-improvement-case-list --status open
  IC-65AF4A6D8B1E  evidence owner-family modules
  IC-FD18EE2D3309  tests/unit/test_cli.py
  IC-3B4C9F2A76E1  tests/unit/test_agent_task_context.py
  IC-25C1F7B9E4DA  tests/unit/test_search_service.py
  IC-81C531769EB3  app/services/semantic_governance.py
  IC-9A0332D41F79  app/services/docling_parser.py
  IC-33B4990DC366  app/services/quality.py
  IC-649D7B4E3AB5  app/services/semantic_candidates.py
  IC-4B6E9F8D2A10  evaluation residual owner-family modules
  IC-81F2C6D4B9A7  UI module residual owner family
  IC-2D5A7E9C4B18  semantic and technical-report residual owner family

wc -l app/services/evidence_claim_support_replay_alerts.py \
  tests/unit/test_cli.py \
  app/services/semantic_governance.py \
  app/services/docling_parser.py \
  app/services/quality.py \
  app/services/semantic_candidates.py \
  app/services/evaluation_fixtures.py \
  app/ui/modules/agents.js \
  app/services/technical_reports.py
    407 app/services/evidence_claim_support_replay_alerts.py
      0 tests/unit/test_cli.py
     39 app/services/semantic_governance.py
    199 app/services/docling_parser.py
     15 app/services/quality.py
    120 app/services/semantic_candidates.py
    376 app/services/evaluation_fixtures.py
    599 app/ui/modules/agents.js
    574 app/services/technical_reports.py
```

The same rebaseline also confirmed that only `IC-3B4C9F2A76E1` and
`IC-25C1F7B9E4DA` still point at live code-owning residual work.

## Closeout Summary

The packet now deploys these previously stale `open` cases:

- `IC-65AF4A6D8B1E`
- `IC-FD18EE2D3309`
- `IC-81C531769EB3`
- `IC-9A0332D41F79`
- `IC-33B4990DC366`
- `IC-649D7B4E3AB5`
- `IC-4B6E9F8D2A10`
- `IC-81F2C6D4B9A7`
- `IC-2D5A7E9C4B18`

The queue truth now becomes:

- Packet B: verified-to-deployed registry closeout
- Packet C: `IC-3B4C9F2A76E1`
- Packet D: `IC-25C1F7B9E4DA`
- Packet E: final queue exhaustion or rebaseline

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A stale registry sweep hides real regrowth because the status changes rely on old notes instead of live measurements. | `config/improvement_cases.yaml`, this packet doc | Fresh `wc -l`, hygiene check, and architecture quality summary | Any Packet A case has a live governed owner above `600` lines. | Leave a regrown `>600` owner in Packet A and confirm the closeout must stop. | Future Codex flips a status to deployed because a prior doc said `resolved locally`. |
| Queue docs diverge after the registry sweep. | handoff, architecture index, broader queue docs | targeted `rg` consistency review | Counts or next-packet order disagree across durable docs. | Update the YAML only and leave the handoff on the old `open=11` state. | Future Codex resumes from the wrong packet after a docs-only closeout. |
| Docs-only work accidentally closes the two real code packets. | queue plan, handoff, architecture index | explicit residual queue check | `IC-3B4C9F2A76E1` or `IC-25C1F7B9E4DA` is no longer clearly named as open. | Mark both residual test packets deployed in the same sweep. | Future Codex claims the backlog is exhausted while the over-budget successor tests still exist. |

## Required Verification Gates

- `git diff --check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- targeted `wc -l` proof for each closed family
- targeted `rg` review across the queue docs for counts and next-packet order

## Acceptance Criteria

- The nine Packet A stale `open` cases are recorded as deployed in
  `config/improvement_cases.yaml`.
- Live counts move from `open=11`, `verified=9`, `deployed=40` to
  `open=2`, `verified=9`, `deployed=49`.
- Only `IC-3B4C9F2A76E1` and `IC-25C1F7B9E4DA` remain open.
- The handoff, architecture index, broader coordination brief, and queue plan
  all point to Packet B as the next packet.

## Stop Conditions

- Stop if any Packet A family regrew above budget on the live rebaseline.
- Stop if a stale `open` case still needs source edits rather than registry
  truth alignment.
- Stop if the docs disagree about the remaining queue after the registry
  changes.

## Local Commit Closeout Policy

- Close this packet with one docs-only atomic commit containing the registry
  sweep and durable queue-doc updates.
