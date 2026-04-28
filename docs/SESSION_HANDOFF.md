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
- artifact kinds: `claim_support_judge_evaluation`, `claim_support_calibration_policy_draft`, `claim_support_calibration_policy_verification`, `claim_support_calibration_policy_activation`, `claim_support_policy_activation_governance`, and `claim_support_policy_change_impact_replay_plan`
- operator runs: `technical_report_claim_support_judge_evaluation`, `claim_support_calibration_policy_verification`, and `claim_support_calibration_policy_activation`
- context builder: `evaluate_claim_support_judge`

The evaluation task replays governed hard-case fixture sets against the technical-report claim-support judge. Passing and failing gates are both persisted as completed, auditable evaluation results. Failed gates do not crash the worker; they preserve the failed case rows, reasons, artifact, operator metrics, fixture-set hash, calibration-policy hash, and typed context summary for review. Unpinned evaluations resolve the active policy for the requested policy name, while policy changes must pass through draft, replay verification, human approval, and activation. Verification now combines explicit/default fixtures with mined failed cases from prior claim-support evaluations and records a mined-failure manifest. Activation requires the draft row to still match the verified draft output, rejects retired-policy identity reuse, records approval metadata, verifier ID, fixture hash, mined-failure manifest, the prior active policy, the new active policy, hashes, operator run, verifier evidence, and reason, then writes a `claim_support_policy_activation_governance` artifact with policy diff, replay evidence, fixture-set diff, mined-failure summary, approval/retirement record, signed hash-chain receipt when signing is configured, PROV JSON-LD, an embedded change-impact report, and a linked `claim_support_policy_activated` semantic-governance event. The same change-impact payload is persisted in `claim_support_policy_change_impacts`, including prior technical-report support judgments, generated draft tasks, verifier tasks, affected IDs, replay recommendations, a reserved row ID, and a payload hash that is recomputed before insert. Operators can inspect the impact ledger through `GET /agent-tasks/claim-support-policy-change-impacts`, queue managed remediation through either `POST /agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-tasks` or the `queue_claim_support_policy_change_impact_replay` task action, and refresh closure through `POST /agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-status`. Replay queueing now prevalidates every recommendation before task creation, creates all child tasks and the row plan/status update in one transaction, is idempotent once replay tasks exist, and rejects replay-plan or closure payload hash mismatches before mutating status. Impact rows carry replay task IDs, replay plans, replay status, and closure receipts; they do not close until the replayed draft and technical-report verification tasks produce passed gate evidence. The governance PROV graph names the activation artifact, governance artifact, and policy change-impact row entity, records a non-null activation end time, and the activation operator run hashes the final governance-bearing output. The database enforces one active policy per policy name.

## Current Agent-Task Catalog Notes

The live action registry currently has 51 task types. The newest catalog additions are:

- `evaluate_document_generation_context_pack`
- `evaluate_claim_support_judge`
- `draft_claim_support_calibration_policy`
- `verify_claim_support_calibration_policy`
- `apply_claim_support_calibration_policy`
- `queue_claim_support_policy_change_impact_replay`

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
772 passed in 94.74s
```

Focused claim-support verification during this implementation pass:

```bash
uv run python -m pytest tests/unit/test_alembic_0061_claim_support_impact_replay.py tests/unit/test_agent_tasks_api.py::test_claim_support_policy_change_impact_detail_route_returns_error_code tests/unit/test_agent_tasks_api.py::test_agent_task_actions_route_exposes_output_schema_metadata_for_all_migrated_tasks tests/unit/test_agent_task_actions.py::test_get_agent_task_action_exposes_claim_support_policy_workflow_metadata -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run python -m pytest tests/integration/test_claim_support_judge_evaluation_roundtrip.py -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run python -m pytest tests/integration/test_technical_report_harness_roundtrip.py -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run python -m pytest tests/integration/test_claim_support_judge_evaluation_roundtrip.py tests/integration/test_technical_report_harness_roundtrip.py -q
uv run alembic upgrade head
uv run alembic current
uv run docling-system-architecture-inspect --write-map
uv run docling-system-architecture-inspect
uv run ruff check .
```

Results:

```text
4 passed
13 passed
1 passed
14 passed
alembic current: 0061_claim_impact_replay (head)
create_all verified by the integration harness against temporary Postgres schemas
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
agent_action_count: 51
```

## Files Updated In This Pass

- [README.md](/Users/chunkstand/Documents/docling-system/README.md)
- [SYSTEM_PLAN.md](/Users/chunkstand/Documents/docling-system/SYSTEM_PLAN.md)
- [docs/SESSION_HANDOFF.md](/Users/chunkstand/Documents/docling-system/docs/SESSION_HANDOFF.md)
- [app/db/models.py](/Users/chunkstand/Documents/docling-system/app/db/models.py)
- [app/schemas/agent_tasks.py](/Users/chunkstand/Documents/docling-system/app/schemas/agent_tasks.py)
- [app/services/agent_task_actions.py](/Users/chunkstand/Documents/docling-system/app/services/agent_task_actions.py)
- [app/services/claim_support_policy_impacts.py](/Users/chunkstand/Documents/docling-system/app/services/claim_support_policy_impacts.py)
- [app/services/claim_support_policy_governance.py](/Users/chunkstand/Documents/docling-system/app/services/claim_support_policy_governance.py)
- [alembic/versions/0061_claim_support_impact_replay_lifecycle.py](/Users/chunkstand/Documents/docling-system/alembic/versions/0061_claim_support_impact_replay_lifecycle.py)
- [alembic/versions/0060_claim_support_policy_change_impacts.py](/Users/chunkstand/Documents/docling-system/alembic/versions/0060_claim_support_policy_change_impacts.py)
- [tests/integration/test_claim_support_judge_evaluation_roundtrip.py](/Users/chunkstand/Documents/docling-system/tests/integration/test_claim_support_judge_evaluation_roundtrip.py)
- [tests/unit/test_alembic_0061_claim_support_impact_replay.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_alembic_0061_claim_support_impact_replay.py)
- [tests/unit/test_agent_tasks_api.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_agent_tasks_api.py)
- [tests/unit/test_alembic_0060_claim_support_policy_change_impacts.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_alembic_0060_claim_support_policy_change_impacts.py)
- [tests/unit/test_claim_support_policy_governance.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_claim_support_policy_governance.py)

## Next Suggested Pass

The next useful pass is to make managed replay easier to operate at scale:

1. add operator UI tables for `claim_support_policy_change_impacts`
2. show replay status, open replay tasks, and closure receipts beside report audit bundles
3. add a stale-impact filter for rows still in `pending`, `queued`, `in_progress`, or `blocked`
4. add an optional worker-side refresher that updates replay closure status after child tasks complete

That would move the new replay lifecycle from API/operator-task support into everyday operational visibility.
