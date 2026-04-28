# Session Handoff

Date: 2026-04-27 local / 2026-04-28 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest committed checkpoint before this handoff update: `5f12b23` (`Harden claim support judge evaluation context`)

## Current Position

`main` is aligned with `origin/main` at the latest code checkpoint before this docs update. The current system is no longer just PDF ingest plus search; it is a durable local document-intelligence platform with:

- active-run-gated PDF ingest, parsing, validation, and promotion
- mixed chunk/table retrieval with replayable evaluations and harness governance
- figure, table, chunk, and artifact provenance preserved in Postgres plus canonical JSON artifacts
- authenticated remote mode and capability-gated API surfaces
- semantic ontology, fact-graph, and graph-memory workflows that stay additive until verified and approved
- technical-report generation workflows with claim/evidence packaging, verification, and audit bundles
- claim-support judge calibration with persisted replay evaluations and per-case evidence
- architecture, hygiene, improvement-case, and audit-bundle governance checks

## Recent Milestones Since The Prior Handoff

The old handoff captured the April 18 API hardening work. Since then, the repository has moved through retrieval/audit, semantic governance, and technical-report hardening passes.

Recent high-signal checkpoints include:

- `c51760c` `Harden retrieval training audit bundle closure`
- `13f8148` `Add audit bundle validation receipts`
- `e53690b` `Expose audit bundle receipt history`
- `4ee9cab` `Add semantic governance release readiness`
- `992c352` `Auto-validate release audit bundles`
- `2767944` `Add reranker artifact impact ledger`
- `c78af3a` `Include reranker artifacts in release audit bundles`
- `d883590` `Add technical report claim provenance locks`
- `3d0d810` `Tighten claim provenance lock validation`
- `ff0b855` `Add technical report claim support gate`
- `e9dbdef` `Add claim support judge evaluation replay`
- `5f12b23` `Harden claim support judge evaluation context`

## Current Technical-Report And Claim-Support State

The technical-report workflow is:

1. `plan_technical_report`
2. `build_report_evidence_cards`
3. `prepare_report_agent_harness`
4. `draft_technical_report`
5. `verify_technical_report`

The workflow now preserves claim evidence at several levels:

- report plans and evidence cards are typed task outputs
- the report harness is a persisted wake-up packet with evidence cards, graph context, claim contract, allowed tools, required skills, and verifier policy
- draft tasks record generation operator runs and persist a frozen claim-derivation evidence package
- claim provenance locks bind generated claims to evidence cards, search result IDs, source records, and hashes
- claim-support judgments are applied to generated claims before verification
- verification checks claim traceability, claim-support judgments, graph approval, concept coverage, refreshed context, and evidence closure
- `GET /agent-tasks/{task_id}/audit-bundle` exposes the draft, verification, evidence package export, claim derivations, operator runs, active-run impact, and signed PROV receipt material when signing is configured

The support-judge calibration path is now first-class:

- task type: `evaluate_claim_support_judge`
- service: `app.services.claim_support_evaluations`
- persisted tables: `claim_support_evaluations` and `claim_support_evaluation_cases`
- artifact kind: `claim_support_judge_evaluation`
- operator run: `technical_report_claim_support_judge_evaluation`
- context builder: `evaluate_claim_support_judge`

The evaluation task replays fixed hard-case fixtures against the technical-report claim-support judge. Passing and failing gates are both persisted as completed, auditable evaluation results. Failed gates do not crash the worker; they preserve the failed case rows, reasons, artifact, operator metrics, fixture-set hash, and typed context summary for review.

## Current Agent-Task Catalog Notes

The live action registry currently has 46 task types. The newest catalog addition is:

- `evaluate_claim_support_judge`

The durable docs have been updated to include it in the task lists and command examples. Operators can always verify the live catalog with:

```bash
uv run docling-system-agent-task-actions
```

Every registered action declares typed input, output schema metadata, side-effect level, approval requirement, capability, and context-builder name. `tests/unit/test_agent_action_contracts.py` checks that named context builders are registered.

## Verification Snapshot

Latest full code verification before this docs update:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
```

Result:

```text
749 passed
```

Focused claim-support verification before this docs update:

```bash
uv run python -m pytest tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_claim_support_evaluations.py tests/unit/test_agent_action_contracts.py -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run python -m pytest tests/integration/test_claim_support_judge_evaluation_roundtrip.py -q
```

Results:

```text
80 passed
2 passed
```

Documentation alignment verification during this docs update:

```bash
uv run docling-system-architecture-inspect
uv run python -m pytest tests/unit/test_agent_action_contracts.py tests/unit/test_architecture_inspection.py tests/unit/test_architecture_decisions.py -q
```

Results:

```text
valid: true
violation_count: 0
agent_action_count: 46
31 passed
```

## Files Updated In This Documentation Alignment

- [README.md](/Users/chunkstand/Documents/docling-system/README.md)
- [SYSTEM_PLAN.md](/Users/chunkstand/Documents/docling-system/SYSTEM_PLAN.md)
- [docs/SESSION_HANDOFF.md](/Users/chunkstand/Documents/docling-system/docs/SESSION_HANDOFF.md)

## Next Suggested Pass

The remaining useful next pass is not another docs update. It is an end-to-end live operator workflow run for the technical-report path:

1. create a report plan from an active ingested document
2. build evidence cards
3. prepare the report harness
4. draft a technical report
5. verify the report
6. export and inspect the audit bundle
7. run `evaluate_claim_support_judge`

That would validate the full document-generation audit chain against live corpus data rather than only fixtures and isolated integration tests.
