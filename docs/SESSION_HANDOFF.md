# Session Handoff

Date: 2026-04-28 local / 2026-04-28 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest committed checkpoint before this implementation pass: `56b312f` (`Harden replay alert fixture promotions`)

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
- `5985c72` `Add claim support replay alert escalations`
- `7f1b2d2` `Harden claim support replay escalations`
- `f95470c` `Add replay alert fixture promotion loop`
- `56b312f` `Harden replay alert fixture promotions`

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
- artifact kinds: `claim_support_judge_evaluation`, `claim_support_calibration_policy_draft`, `claim_support_calibration_policy_verification`, `claim_support_calibration_policy_activation`, `claim_support_policy_activation_governance`, `claim_support_replay_alert_fixture_coverage_waiver`, `claim_support_policy_change_impact_replay_plan`, `claim_support_policy_impact_replay_closure`, `claim_support_policy_impact_replay_escalation`, and `claim_support_policy_impact_fixture_promotion`
- operator runs: `technical_report_claim_support_judge_evaluation`, `claim_support_calibration_policy_verification`, and `claim_support_calibration_policy_activation`
- context builder: `evaluate_claim_support_judge`

The evaluation task replays governed hard-case fixture sets against the technical-report claim-support judge. Passing and failing gates are both persisted as completed, auditable evaluation results. Failed gates do not crash the worker; they preserve the failed case rows, reasons, artifact, operator metrics, fixture-set hash, calibration-policy hash, and typed context summary for review. Unpinned evaluations resolve the active policy for the requested policy name, while policy changes must pass through draft, replay verification, human approval, and activation. Verification now combines explicit/default fixtures with the latest promoted replay-alert fixtures and mined failed cases from prior claim-support evaluations, then records both replay-alert fixture coverage and mined-failure manifests. The replay-alert coverage requirement is enabled by default, so stale escalation receipts that have not been promoted into fixture coverage force the verifier gate to fail instead of allowing a policy promotion with known uncovered replay alerts. If that requirement is disabled, the task schema requires a waiver operator, reason, severity, and expiry; verification writes a durable waiver artifact/hash with lifecycle metadata and optional remediation owner; activation blocks expired waivers and requires a separate waiver-specific activation approval from a different operator; activation governance carries both the waiver and the second approval; and decision signals classify active, expiring, expired, unmanaged, high-severity, and fixture-promotion-remediable waiver posture. Activation requires the draft row to still match the verified draft output, rejects retired-policy identity reuse, records approval metadata, verifier ID, fixture hash, replay-alert fixture summary, replay-alert coverage waiver, waiver activation approval, mined-failure manifest, the prior active policy, the new active policy, hashes, operator run, verifier evidence, and reason, then writes a `claim_support_policy_activation_governance` artifact with policy diff, replay evidence, fixture-set diff, replay-alert fixture summary, replay-alert coverage waiver, mined-failure summary, approval/retirement record, signed hash-chain receipt when signing is configured, PROV JSON-LD, an embedded change-impact report, and a linked `claim_support_policy_activated` semantic-governance event. The same change-impact payload is persisted in `claim_support_policy_change_impacts`, including prior technical-report support judgments, generated draft tasks, verifier tasks, affected IDs, replay recommendations, a reserved row ID, and a payload hash that is recomputed before insert. Operators can inspect the impact ledger through `GET /agent-tasks/claim-support-policy-change-impacts`, inspect status counts and stale open rows through `GET /agent-tasks/claim-support-policy-change-impacts/summary`, load the remediation worklist through `GET /agent-tasks/claim-support-policy-change-impacts/worklist`, load stale/blocked alert rows through `GET /agent-tasks/claim-support-policy-change-impacts/alerts`, record idempotent escalation receipts through `POST /agent-tasks/claim-support-policy-change-impacts/alerts/escalations`, mine escalated alert rows into hard-case candidates through `GET /agent-tasks/claim-support-policy-change-impacts/alerts/fixture-candidates`, promote unconverted candidates into governed fixture sets through `POST /agent-tasks/claim-support-policy-change-impacts/alerts/fixture-promotions`, queue managed remediation through either `POST /agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-tasks` or the `queue_claim_support_policy_change_impact_replay` task action, and refresh closure through `POST /agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-status`. The CLI commands `docling-system-claim-support-replay-alerts` and `docling-system-claim-support-replay-fixtures` emit the alert posture and alert-derived fixture coverage as JSON, YAML, or tabular reports; the alert CLI can record escalation receipts and the fixture CLI can promote unconverted candidates with `--promote`. The Agent Workflows UI now exposes the worklist with stale-row controls, returned/matching row counts, affected audit-bundle links, replay task links, closure receipt links, and queue/refresh actions; decision signals surface open, stale, and blocked claim-support replay impacts, stale escalation receipts that remain unconverted into fixture coverage, and replay-alert fixture coverage waivers. Replay queueing now prevalidates every recommendation before task creation, creates all child tasks and the row plan/status update in one transaction, is idempotent once replay tasks exist, and rejects replay-plan or terminal closure payload hash mismatches before mutating status. Worker finalization refreshes related impact rows after replay task success or failure. Impact rows carry replay task IDs, replay plans, replay status, and immutable closure receipts; replay-required rows do not close until the replayed draft and technical-report verification tasks produce passed gate evidence. Zero-replay `no_action_required` rows close during activation with the same closure artifact and semantic-governance event used for completed replay rows. Terminal closures must carry a row-level hash, matching payload hash, matching row status, and `replay_closed_at`; stale/blocked alert escalations write immutable `claim_support_policy_impact_replay_escalation` artifacts and `claim_support_policy_impact_replay_escalated` semantic-governance events. The alert feed is DB-filtered to blocked rows plus stale open rows, while escalation recording revalidates each target row under `FOR UPDATE` before writing a receipt. Existing technical-report evidence manifests for affected verification tasks are refreshed in the same escalation transaction, so older manifest rows do not hide newly recorded escalation evidence. Fixture promotion writes immutable `claim_support_policy_impact_fixture_promotion` artifacts and `claim_support_policy_impact_fixture_promoted` semantic-governance events that connect source impact rows, escalation receipts, candidate fixtures, and the promoted fixture set; candidate IDs are stable for the impacted derivation/fallback draft payload, while source payload hashes preserve mutable escalation receipt state and promotion responses report bounded candidate coverage. Promotion now also refreshes existing technical-report evidence manifests for affected verification tasks, and technical-report audit bundles, evidence manifests, and evidence traces surface related policy-change replay impact status, escalation evidence, and fixture-promotion events until replay closes and after alert coverage is promoted. The governance PROV graph names the activation artifact, governance artifact, and policy change-impact row entity, records a non-null activation end time, and the activation operator run hashes the final governance-bearing output. The database enforces one active policy per policy name.

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
792 passed in 86.48s (0:01:26)
```

Focused claim-support verification during this implementation pass:

```bash
uv run ruff check .
git diff --check
uv run pytest -q tests/unit/test_agent_task_actions.py::test_get_agent_task_action_exposes_claim_support_policy_workflow_metadata tests/unit/test_agent_tasks_api.py::test_agent_task_actions_route_exposes_output_schema_metadata_for_all_migrated_tasks tests/unit/test_agent_tasks_api.py::test_create_agent_task_route_returns_422_on_invalid_inner_payload tests/unit/test_agent_tasks_api.py::test_agent_task_routes_use_service_layer tests/unit/test_cli.py::test_agent_task_remaining_milestone9_clis_print_payloads
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_claim_support_judge_evaluation_roundtrip.py::test_claim_support_policy_activation_carries_replay_alert_coverage_waiver tests/integration/test_claim_support_judge_evaluation_roundtrip.py::test_claim_support_policy_activation_blocks_expired_replay_alert_coverage_waiver tests/integration/test_claim_support_judge_evaluation_roundtrip.py::test_claim_support_change_impact_replay_prevalidates_before_creating_tasks
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
uv run docling-system-architecture-inspect
```

Results:

```text
ruff: All checks passed
git diff --check: passed
claim-support action schema/API/CLI checks: 5 passed in 8.60s
claim-support replay-alert waiver lifecycle integration: 3 passed in 5.34s
full integration-enabled suite: 793 passed in 105.86s (0:01:45)
architecture inspection valid: true, violation_count: 0
api_route_count: 127
agent_action_count: 51
```

Architecture inspection during this pass:

```bash
uv run docling-system-architecture-inspect
```

Results:

```text
valid: true
violation_count: 0
api_route_count: 127
agent_action_count: 51
```

## Files Updated In This Pass

- [README.md](/Users/chunkstand/Documents/docling-system/README.md)
- [docs/SESSION_HANDOFF.md](/Users/chunkstand/Documents/docling-system/docs/SESSION_HANDOFF.md)
- [SYSTEM_PLAN.md](/Users/chunkstand/Documents/docling-system/SYSTEM_PLAN.md)
- [app/schemas/agent_tasks.py](/Users/chunkstand/Documents/docling-system/app/schemas/agent_tasks.py)
- [app/services/agent_task_actions.py](/Users/chunkstand/Documents/docling-system/app/services/agent_task_actions.py)
- [app/services/agent_tasks.py](/Users/chunkstand/Documents/docling-system/app/services/agent_tasks.py)
- [app/services/claim_support_policy_governance.py](/Users/chunkstand/Documents/docling-system/app/services/claim_support_policy_governance.py)
- [tests/integration/test_claim_support_judge_evaluation_roundtrip.py](/Users/chunkstand/Documents/docling-system/tests/integration/test_claim_support_judge_evaluation_roundtrip.py)

## Next Suggested Pass

The next useful pass is waiver closure control for replay-alert fixture coverage:

1. write immutable waiver-closure receipts when fixture promotion covers the waived escalation set
2. suppress active-waiver posture only after the closure receipt references the promotion artifact and waiver hash
3. surface unresolved expired waivers separately from closed/superseded waivers in audit bundles and decision signals

That would complete the loop from waiver creation to waiver retirement without making artifact inspection the durable contract.
