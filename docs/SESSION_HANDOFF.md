# Session Handoff

Date: 2026-04-27 local / 2026-04-28 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest committed checkpoint before this implementation pass: `4c7cf74` (`Harden claim support activation governance`)

## Current Position

`main` has local verified work that has not been pushed to `origin/main`. The current system is no longer just PDF ingest plus search; it is a durable local document-intelligence platform with:

- active-run-gated PDF ingest, parsing, validation, and promotion
- mixed chunk/table retrieval with replayable evaluations and harness governance
- figure, table, chunk, and artifact provenance preserved in Postgres plus canonical JSON artifacts
- authenticated remote mode and capability-gated API surfaces
- semantic ontology, fact-graph, and graph-memory workflows that stay additive until verified and approved
- technical-report generation workflows with claim/evidence packaging, verification, and audit bundles
- reusable document-generation context packs with pre-draft quality evaluation
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
4. `evaluate_document_generation_context_pack`
5. `draft_technical_report`
6. `verify_technical_report`

The workflow now preserves claim evidence at several levels:

- report plans and evidence cards are typed task outputs
- the report harness is a persisted wake-up packet with evidence cards, graph context, claim contract, allowed tools, required skills, and verifier policy
- `prepare_report_agent_harness` also writes `document_generation_context_pack.json`, a reusable generation input with context refs, retrieval plan, evidence cards, source evidence package refs, graph context, claim contract, freshness summary, quality contract, audit refs, and a stable hash
- `evaluate_document_generation_context_pack` records a verifier row, operator run, typed context, and evaluation artifact before a draft is generated
- `draft_technical_report` now requires a passed latest context-pack gate for the target harness, and the gate's context-pack hash must match the current harness hash before generation can run
- final technical-report audit bundles, evidence manifests, evidence traces, and PROV exports now include the context-pack artifact, evaluation artifact, verifier record, operator run, and hash-check chain as explicit audit material
- draft tasks record generation operator runs and persist a frozen claim-derivation evidence package
- claim provenance locks bind generated claims to evidence cards, search result IDs, source records, and hashes
- claim-support judgments are applied to generated claims before verification
- verification checks claim traceability, claim-support judgments, graph approval, concept coverage, refreshed context, and evidence closure
- `GET /agent-tasks/{task_id}/audit-bundle` exposes the draft, verification, evidence package export, claim derivations, operator runs, active-run impact, and signed PROV receipt material when signing is configured

The support-judge calibration path is now first-class:

- task type: `evaluate_claim_support_judge`
- governed promotion path: `draft_claim_support_calibration_policy -> verify_claim_support_calibration_policy -> apply_claim_support_calibration_policy`
- service: `app.services.claim_support_evaluations`
- persisted tables: `claim_support_fixture_sets`, `claim_support_calibration_policies`, `claim_support_evaluations`, `claim_support_evaluation_cases`, and `claim_support_policy_change_impacts`
- artifact kinds: `claim_support_judge_evaluation`, `claim_support_calibration_policy_draft`, `claim_support_calibration_policy_verification`, `claim_support_calibration_policy_activation`, and `claim_support_policy_activation_governance`
- operator runs: `technical_report_claim_support_judge_evaluation`, `claim_support_calibration_policy_verification`, and `claim_support_calibration_policy_activation`
- context builder: `evaluate_claim_support_judge`

The evaluation task replays governed hard-case fixture sets against the technical-report claim-support judge. Passing and failing gates are both persisted as completed, auditable evaluation results. Failed gates do not crash the worker; they preserve the failed case rows, reasons, artifact, operator metrics, fixture-set hash, calibration-policy hash, and typed context summary for review. Unpinned evaluations resolve the active policy for the requested policy name, while policy changes must pass through draft, replay verification, human approval, and activation. Verification now combines explicit/default fixtures with mined failed cases from prior claim-support evaluations and records a mined-failure manifest. Activation requires the draft row to still match the verified draft output, rejects retired-policy identity reuse, records approval metadata, verifier ID, fixture hash, mined-failure manifest, the prior active policy, the new active policy, hashes, operator run, verifier evidence, and reason, then writes a `claim_support_policy_activation_governance` artifact with policy diff, replay evidence, fixture-set diff, mined-failure summary, approval/retirement record, signed hash-chain receipt when signing is configured, PROV JSON-LD, an embedded change-impact report, and a linked `claim_support_policy_activated` semantic-governance event. The same change-impact payload is persisted in `claim_support_policy_change_impacts`, including prior technical-report support judgments, generated draft tasks, verifier tasks, affected IDs, replay recommendations, and a stable payload hash. The governance PROV graph names the activation artifact, governance artifact, and policy change-impact entity, records a non-null activation end time, and the activation operator run hashes the final governance-bearing output. The database enforces one active policy per policy name.

## Current Agent-Task Catalog Notes

The live action registry currently has 50 task types. The newest catalog additions are:

- `evaluate_document_generation_context_pack`
- `evaluate_claim_support_judge`
- `draft_claim_support_calibration_policy`
- `verify_claim_support_calibration_policy`
- `apply_claim_support_calibration_policy`

The durable docs have been updated to include it in the task lists and command examples. Operators can always verify the live catalog with:

```bash
uv run docling-system-agent-task-actions
```

Every registered action declares typed input, output schema metadata, side-effect level, approval requirement, capability, and context-builder name. `tests/unit/test_agent_action_contracts.py` checks that named context builders are registered.

## Verification Snapshot

Latest full code verification during this implementation pass:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
```

Result:

```text
768 passed in 105.43s
```

Focused claim-support verification during this implementation pass:

```bash
uv run python -m pytest tests/unit/test_alembic_0059_claim_support_policy_governance.py -q
uv run python -m pytest tests/unit/test_alembic_0060_claim_support_policy_change_impacts.py -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run python -m pytest tests/integration/test_claim_support_judge_evaluation_roundtrip.py -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run python -m pytest tests/integration/test_claim_support_judge_evaluation_roundtrip.py tests/integration/test_technical_report_harness_roundtrip.py -q
uv run alembic upgrade head
uv run alembic current
uv run docling-system-architecture-inspect
uv run ruff check .
```

Results:

```text
1 passed
1 passed
12 passed
13 passed
alembic current: 0060_claim_policy_impacts (head)
create_all verified against a clean temporary Postgres database with 73 tables
architecture inspection valid: true, violation_count: 0
ruff: All checks passed
```

Architecture inspection during this pass:

```bash
uv run docling-system-architecture-inspect
```

Results:

```text
valid: true
violation_count: 0
agent_action_count: 50
```

## Files Updated In This Pass

- [README.md](/Users/chunkstand/Documents/docling-system/README.md)
- [SYSTEM_PLAN.md](/Users/chunkstand/Documents/docling-system/SYSTEM_PLAN.md)
- [docs/SESSION_HANDOFF.md](/Users/chunkstand/Documents/docling-system/docs/SESSION_HANDOFF.md)
- [app/db/models.py](/Users/chunkstand/Documents/docling-system/app/db/models.py)
- [app/schemas/agent_tasks.py](/Users/chunkstand/Documents/docling-system/app/schemas/agent_tasks.py)
- [app/services/agent_task_actions.py](/Users/chunkstand/Documents/docling-system/app/services/agent_task_actions.py)
- [app/services/claim_support_policy_governance.py](/Users/chunkstand/Documents/docling-system/app/services/claim_support_policy_governance.py)
- [alembic/versions/0060_claim_support_policy_change_impacts.py](/Users/chunkstand/Documents/docling-system/alembic/versions/0060_claim_support_policy_change_impacts.py)
- [tests/integration/test_claim_support_judge_evaluation_roundtrip.py](/Users/chunkstand/Documents/docling-system/tests/integration/test_claim_support_judge_evaluation_roundtrip.py)
- [tests/unit/test_alembic_0060_claim_support_policy_change_impacts.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_alembic_0060_claim_support_policy_change_impacts.py)

## Next Suggested Pass

The next useful pass is to turn persisted policy change-impact rows into an operator replay workflow:

1. list `claim_support_policy_change_impacts` rows by policy activation
2. render impacted draft/support/verifier IDs and replay reasons in the operator surface/API
3. create queued replay tasks from the recommendations
4. close the impact row only after the replayed `draft_technical_report` and `verify_technical_report` tasks pass

That would move from identifying stale court-grade report artifacts to driving the replay loop that refreshes them.
