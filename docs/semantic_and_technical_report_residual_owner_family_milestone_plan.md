# Semantic And Technical Report Residual Owner Family Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved through the 2026-05-19 stale-open registry closeout after
the 2026-05-18 closeout and gap-close pass.
Owner context: follow-on packet for the semantic, technical-report, and
audit-training owners that remained above the live large-file threshold after
the semantic lifecycle/read and audit-bundle facade closeouts and are now
reduced below the default 600-line budget.

## Purpose

Resolved the residual semantic and report owner debt without pushing the moved
implementation into unrelated large files.

The selected closeout now leaves the family at:

- `app/services/semantic_orchestration.py` at `543` lines and
  `app/services/semantic_orchestration_triage.py` at `570`
- `app/services/technical_reports.py` at `574` lines with
  `app/services/technical_report_verification.py` at `485` and
  `app/services/technical_report_task_context.py` at `33`
- `app/services/audit_bundle_training_runs.py` at `554` lines with
  `app/services/audit_bundle_training_run_payloads.py` at `159` and
  `app/services/audit_bundle_training_run_provenance.py` at `258`
- `tests/unit/test_technical_reports.py` at `486` and
  `tests/unit/test_technical_report_verification.py` at `125`

## Current Evidence

- The live architecture probe on 2026-05-18 now reports `8` code files above
  `800` with `0` Python cycle components, down from `11` before this packet.
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` now route
  the full semantic/report family through `IC-2D5A7E9C4B18` with exact ratchets
  for every new sibling and split unit root.
- The focused unit slice passed at `26 passed`, and the DB-backed integration
  slice passed at `4 passed`.
- The dependent downstream surfaces still passed at `7 passed, 1 skipped`
  across `tests/unit/test_agent_task_context.py`,
  `tests/unit/test_agent_task_context_reports_claim_support.py`, and
  `tests/integration/test_technical_report_harness_integrity.py`, so the split
  did not spill report-context or harness-integrity debt into adjacent owners.
- The broader backlog queue now advances to
  `docs/cross_cutting_large_file_residual_milestone_plan.md`.

## Goal

Reduce the semantic and technical-report residual family so that:

- all three routed services fall below `800` lines
- no new cycle appears
- any new `601-800` residual owner is routed in the same milestone
- semantic, technical-report, and audit-training verification remains at least
  as strong as before the split

## Non-Goals

- No moving ownership into `documents.py`, `eval_workbench.py`, or unrelated
  agent-task context owners.
- No semantic feature rewrite, report format rewrite, or audit-bundle contract
  regression.
- No weakening of unit or DB-backed harness coverage to make the roots smaller.

## Scope

In scope:

- `app/services/semantic_orchestration.py`
- `app/services/technical_reports.py`
- `app/services/audit_bundle_training_runs.py`
- focused family-local siblings created under `app/services/`
- `tests/unit/test_semantic_orchestration.py`
- `tests/unit/test_technical_reports.py`
- `tests/unit/test_technical_report_verification.py`
- `tests/unit/test_audit_bundle_training_runs.py`
- `tests/unit/test_audit_bundles_facade_contract.py`
- `tests/unit/test_audit_bundle_validation_receipts.py`
- `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `tests/integration/test_technical_report_harness_roundtrip.py`
- `tests/integration/test_technical_report_harness_audit_surfaces.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

Out of scope:

- unrelated parser, evaluation, or document-service refactors
- reopening already-closed semantic lifecycle/read or audit-bundle facade
  packets
- changing public API or artifact contracts outside the selected owners

## Owner Surfaces

- `app/services/semantic_orchestration.py`
- `app/services/technical_reports.py`
- `app/services/audit_bundle_training_runs.py`
- direct family-local siblings created by the packet
- the focused unit and integration tests listed above

## Placement Rules

- Keep moved implementation in family-local service siblings.
- Do not use `documents.py`, `eval_workbench.py`, or generic `*_common.py`
  sinks as landing zones.
- If shared test support is required, keep it local to this family and below
  the default `600`-line budget.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| One service gets smaller only because another adjacent owner becomes the new sink. | routed services, hygiene config, architecture probe | focused `ruff` and `pytest`, hygiene check, architecture probe | any touched sibling still exceeds its ratchet or a new `>800` owner appears | move report helpers from `technical_reports.py` into `semantic_orchestration.py` and confirm closeout rejects it | future Codex follows nearby vocabulary and recreates the same debt one file over |
| A split introduces a new cycle between semantic, report, and audit services. | routed services, architecture probe | architecture probe plus focused integration slice | any new Python cycle component appears | add a temporary backward import between report and semantic owners and confirm the packet fails | future Codex solves ownership by cross-importing large helpers instead of separating seams |
| Coverage narrows around report or semantic paths to keep the packet green. | focused unit and integration roots | focused unit slice plus DB-backed integration slice | assertions or scenarios disappear without stronger replacement coverage | replace a targeted report harness assertion with a smoke check and confirm review or tests reject it | future Codex optimizes for line count instead of contract coverage |

## Milestone Sequence

### Milestone 0. Baseline Lock
Outcome label: reduced

Refresh line counts, confirm `IC-2D5A7E9C4B18`, and lock the unit and
integration verification slices before code motion.

### Milestone 1. Semantic Orchestration Split
Outcome label: reduced

Reduce `app/services/semantic_orchestration.py` below `800` through
family-local semantic owners.

### Milestone 2. Technical Report And Audit-Training Split
Outcome label: reduced

Reduce `app/services/technical_reports.py` and
`app/services/audit_bundle_training_runs.py` below `800` without widening the
report or audit facades.

### Milestone 3. Closeout
Outcome label: resolved

Close the packet only after all three routed services are below `800`, the docs
are updated, and the focused unit plus DB-backed integration slices are green.

## Required Implementation Artifacts

- focused family-local service siblings or test-support files
- refreshed routing config in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`
- updated closeout docs and handoff artifacts

## Required Documentation And Handoff Updates

- `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/semantic_orchestration.py app/services/semantic_orchestration_triage.py app/services/technical_reports.py app/services/technical_report_verification.py app/services/technical_report_task_context.py app/services/audit_bundle_training_runs.py app/services/audit_bundle_training_run_payloads.py app/services/audit_bundle_training_run_provenance.py tests/unit/test_semantic_orchestration.py tests/unit/test_technical_reports.py tests/unit/test_technical_report_verification.py tests/unit/test_audit_bundle_training_runs.py tests/unit/test_audit_bundles_facade_contract.py tests/unit/test_audit_bundle_validation_receipts.py`
- `uv run pytest -q tests/unit/test_semantic_orchestration.py tests/unit/test_technical_reports.py tests/unit/test_technical_report_verification.py tests/unit/test_audit_bundle_training_runs.py tests/unit/test_audit_bundles_facade_contract.py tests/unit/test_audit_bundle_validation_receipts.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_technical_report_harness_audit_surfaces.py`
- `uv run pytest -q tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_reports_claim_support.py tests/integration/test_technical_report_harness_integrity.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- All three routed services fall below `800` lines.
- No new Python cycle appears.
- Any new `601-800` residual owner is routed in the same milestone.
- The focused unit and DB-backed integration slices pass without weaker
  assertions or broader skips.
- The downstream report-context and harness-integrity surfaces remain green,
  proving the split did not just move debt into adjacent owners.

## Stop Conditions

- Stop if a fresh probe changes the routed family before code motion begins.
- Stop if the reduction requires moving ownership into unrelated large service
  families.
- Stop if the split only stays green by weakening semantic, report, or audit
  verification.

## Local Commit Closeout Policy

- Close this packet with one atomic local commit containing only the semantic,
  report, and audit-training owner changes, focused verification, routing
  updates, and doc or handoff updates for this packet.

## Residual Risks And Next Milestone Routing

- No governed semantic/report owner remains between `601` and `800` in the
  local checkout, so no follow-on packet is required under `IC-2D5A7E9C4B18`
  before atomic closeout.
- After this packet, the active routed child packet is now
  `docs/cross_cutting_large_file_residual_milestone_plan.md`.
