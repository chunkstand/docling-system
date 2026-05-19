# Verified To Deployed Registry Closeout Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved through the 2026-05-19 docs-only verified-to-deployed
registry closeout. Packet B of
`docs/remaining_packet_queue_resolution_milestone_plan.md` is now complete,
the nine verified cases are recorded as deployed, and Packet C
`IC-3B4C9F2A76E1` is the next queued packet.
Owner context: docs-only closeout sweep for the verified cases that were
already under budget and already described as reduced, verified, or
implementation-complete in durable repo artifacts.

## Purpose

Deploy the already-verified cases without reopening code-owning packets.

After Packet A, the remaining debt was no longer stale `open` registry drift.
It was nine cases stuck in `verified` even though the live checkout already
showed the routed roots and owner-family successors below budget. This packet
records those nine cases as deployed, updates the queue truth, and leaves only
the two actual residual test packets open.

## Scope

In scope:

- `config/improvement_cases.yaml`
- `docs/verified_to_deployed_registry_closeout_milestone_plan.md`
- `docs/remaining_packet_queue_resolution_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/open_owner_backlog_resolution_milestone_plan.md`
- `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`
- `docs/documents_api_route_surface_boundary_milestone_plan.md`
- `docs/oversized_test_hotspots_boundary_milestone_plan.md`

Out of scope:

- production or test source edits
- Packet C / Packet D residual test splits
- any broader queue reprioritization beyond the verified closeout

## Current Evidence

Milestone 0 rebaseline from the live checkout on 2026-05-19 confirmed that the
Packet B cases were still below budget and did not need fresh code work:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":49,"open":2,"verified":9}

uv run docling-system-improvement-case-list --status verified
  IC-8304248AB64C  app/services/semantic_pass_lifecycle.py
  IC-ADCFFF108626  app/services/semantic_pass_reads.py
  IC-D49E037D5657  tests/integration/test_technical_report_harness_roundtrip.py
  IC-23F2C79C8AA7  tests/unit/test_documents_api.py
  IC-8AFAD4A415CA  app/services/runs.py
  IC-865AB8419D55  app/services/semantic_graph.py
  IC-A92BA42C6D18  app/services/semantic_generation.py
  IC-6F4E2B5A91C3  semantic generation owner-family modules
  IC-C8D41A2F77BE  semantic graph owner-family modules

wc -l app/services/semantic_pass_lifecycle.py \
  app/services/semantic_pass_reads.py \
  tests/integration/test_technical_report_harness_roundtrip.py \
  tests/unit/test_documents_api.py \
  app/services/runs.py \
  app/services/semantic_graph.py \
  app/services/semantic_generation.py \
  app/services/semantic_generation_brief.py \
  app/services/semantic_graph_promotions.py
    529 app/services/semantic_pass_lifecycle.py
    372 app/services/semantic_pass_reads.py
     93 tests/integration/test_technical_report_harness_roundtrip.py
    154 tests/unit/test_documents_api.py
    404 app/services/runs.py
    185 app/services/semantic_graph.py
     91 app/services/semantic_generation.py
    505 app/services/semantic_generation_brief.py
    589 app/services/semantic_graph_promotions.py
```

The live governance checks remain aligned with that rebaseline:

- `uv run docling-system-hygiene-check`: no regressions, no inherited budget debt
- `uv run docling-system-architecture-quality-report --summary`:
  `legibility_gap_count=0`, `top_routed_hotspot_paths=[]`

## Closeout Summary

The packet now deploys these previously verified cases:

- `IC-8304248AB64C`
- `IC-ADCFFF108626`
- `IC-D49E037D5657`
- `IC-23F2C79C8AA7`
- `IC-8AFAD4A415CA`
- `IC-865AB8419D55`
- `IC-A92BA42C6D18`
- `IC-6F4E2B5A91C3`
- `IC-C8D41A2F77BE`

The queue truth now becomes:

- Packet C: `IC-3B4C9F2A76E1`
- Packet D: `IC-25C1F7B9E4DA`
- Packet E: final queue exhaustion or rebaseline

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A verified case is deployed from stale docs even though the live owner regrew above budget. | `config/improvement_cases.yaml`, this packet doc | Fresh `wc -l`, hygiene check, and architecture quality summary | Any Packet B case has a live governed owner above `600` lines or contradictory current docs. | Leave a regrown `>600` owner in Packet B and confirm the closeout must stop. | Future Codex marks a case deployed because an earlier packet ended in `verified`. |
| Deployment refs are invented or drift away from real implementation history. | `config/improvement_cases.yaml` | case-by-case commit grounding against the existing packet docs and git history | A deployed Packet B case still has `deployment.deployed_ref: null` or a non-existent hash. | Fill the registry with placeholder hashes and confirm validation fails. | Future Codex loses the actual implementation lineage for the deployed cases. |
| Queue docs still point to Packet B after the sweep lands. | handoff, architecture index, broader queue docs | targeted `rg` consistency review | Counts or next-packet order disagree across durable docs. | Update the registry only and leave Packet B listed as next. | Future Codex reruns the same deploy sweep instead of moving to Packet C. |

## Required Verification Gates

- `git diff --check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- targeted `wc -l` proof for each deployed family
- targeted `rg` review across the queue docs for counts and next-packet order

## Acceptance Criteria

- The nine Packet B verified cases are recorded as deployed in
  `config/improvement_cases.yaml`.
- Live counts move from `open=2`, `verified=9`, `deployed=49` to
  `open=2`, `verified=0`, `deployed=58`.
- Only `IC-3B4C9F2A76E1` and `IC-25C1F7B9E4DA` remain open.
- The handoff, architecture index, broader coordination brief, and queue plan
  all point to Packet C as the next packet.

## Post-Closeout Alignment Audit

The later 2026-05-19 alignment audit confirms that the docs-only Packet A/B
queue closeouts did not shift debt into adjacent governance surfaces:

- `uv run docling-system-improvement-case-summary` now reports
  `open=2`, `verified=0`, and `deployed=58`.
- `uv run docling-system-hygiene-check` still reports `new hygiene regressions: none`
  and `inherited budget debt: none`.
- `uv run docling-system-hotspot-prevention-check --strict` still reports
  `known_hotspots=42`, `changed_hotspots=0`, and `blocked=0`.
- `uv run docling-system-architecture-inspect` remains `valid=true` with
  `violation_count=0`.
- `uv run docling-system-architecture-quality-report --summary` now reports
  `agent_legibility_average_score=90.0`,
  `broad_facade_count=2`,
  `legibility_gap_count=0`,
  `hotspot_count=20`,
  `max_hotspot_risk_score=471.06`, and
  `top_routed_hotspot_paths=[]`.

## Stop Conditions

- Stop if any Packet B family regrew above budget on the live rebaseline.
- Stop if a verified case still needs source edits rather than registry truth
  alignment.
- Stop if the docs disagree about the remaining queue after the registry
  changes.

## Local Commit Closeout Policy

- Close this packet with one docs-only atomic commit containing the registry
  sweep and durable queue-doc updates.
