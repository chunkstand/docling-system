# Architecture Inspection Test Surface Boundary Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved through implementation commit `d7ddc23` and the current
durable closeout pass.

Owner context: this packet was the first honest routed owner after the
2026-05-19 queue-honesty refresh. The raw architecture-quality report surfaced
`tests/unit/test_architecture_inspection.py` as a mixed governance hotspot at
495 lines, ahead of `app/api/routers/agent_tasks.py`, with no structured
routing metadata yet keeping the root off the active queue.

## Purpose

Reduce the mixed architecture-inspection test root without weakening the
governance contracts or pushing the moved coverage into another broad sink.

## Outcome

- reduced `tests/unit/test_architecture_inspection.py` to a 61-line smoke and
  compatibility surface
- moved contract-map and persistence coverage into
  `tests/unit/test_architecture_inspection_contract_map.py` at 212 lines
- moved CLI coverage into
  `tests/unit/test_architecture_inspection_cli.py` at 40 lines
- moved rule-behavior and AST-boundary coverage into
  `tests/unit/test_architecture_inspection_rules.py` at 178 lines
- kept shared family helpers in
  `tests/unit/architecture_inspection_test_support.py` at 44 lines
- routed the reduced root as a deferred reduced facade in
  `config/hotspot_prevention.yaml`
- recorded `IC-B847B0E36C52` as deployed in
  `config/improvement_cases.yaml`

## Debt-Shift Check

- No architecture-inspection family file exceeds the default 600-line hygiene
  budget after the split.
- The shared support file stays at 44 lines and does not become a second mixed
  sink.
- The live routed queue advances to `app/api/routers/agent_tasks.py` after the
  closeout instead of looping back into the reduced governance root.

## Verification

- `uv run ruff check tests/unit/architecture_inspection_test_support.py tests/unit/test_architecture_inspection.py tests/unit/test_architecture_inspection_contract_map.py tests/unit/test_architecture_inspection_cli.py tests/unit/test_architecture_inspection_rules.py tests/unit/test_architecture_quality.py tests/unit/test_hotspot_prevention_policy_contracts.py`
- `uv run pytest -q tests/unit/test_architecture_inspection.py tests/unit/test_architecture_inspection_contract_map.py tests/unit/test_architecture_inspection_cli.py tests/unit/test_architecture_inspection_rules.py tests/unit/test_architecture_governance_imports.py tests/unit/test_api_architecture.py tests/unit/test_architecture_quality.py tests/unit/test_hotspot_prevention_policy_contracts.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --max-file-lines 800`

## Next Packet

After this closeout, the honest next routed owner is
`app/api/routers/agent_tasks.py`.
