# Audit Bundle And Retrieval Learning Hotspots Milestone Plan

Date: 2026-05-11 local / 2026-05-11 UTC
Status: in_progress
Owner context: new standalone hotspot-reduction plan for
`IC-2112B1ADC5E8` / `app/services/audit_bundles.py` and
`IC-0D58F1624037` / `app/services/retrieval_learning.py`. This plan does not
extend the earlier hotspot-owner sequence; it targets the two already
owner-routed large compatibility facades that still carry significant
line-count and helper-count debt.

## Purpose

Resolve the remaining size and complexity hotspot debt in:

- `app/services/audit_bundles.py`
- `app/services/retrieval_learning.py`

The owner-routing problem for these surfaces is already closed. What remains is
to reduce each file from a broad compatibility facade with mixed concerns into
a narrow, verified facade with focused owner modules for:

- audit-bundle payload assembly, validation-receipt lifecycle, and training or
  release provenance concerns
- retrieval-learning dataset materialization, candidate evaluation, reranker
  artifact generation, and governance-event recording concerns

## Current Evidence

Status refreshed from live repo commands and current routing docs on
2026-05-11 local / 2026-05-11 UTC:

```text
wc -l app/services/audit_bundles.py app/services/retrieval_learning.py app/services/audit_bundle_replay_alert_corpus.py app/services/retrieval_learning_replay_alert_sources.py
   3306 app/services/audit_bundles.py
   2482 app/services/retrieval_learning.py
    575 app/services/audit_bundle_replay_alert_corpus.py
    578 app/services/retrieval_learning_replay_alert_sources.py

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=24
  status_counts.deployed=1
  status_counts.measured=1
  oldest_open_case_id=IC-050E60059A34

uv run docling-system-hygiene-check
  inherited budget debt includes:
    app/services/audit_bundles.py owner=IC-2112B1ADC5E8
    app/services/retrieval_learning.py owner=IC-0D58F1624037
  new hygiene regressions: none
```

Current owner routing and residual hotspot measurements:

- `IC-2112B1ADC5E8` records `app/services/audit_bundles.py` at `3306` lines and
  `58` private helpers after the replay-alert corpus split.
- `IC-0D58F1624037` records `app/services/retrieval_learning.py` at `2482`
  lines and `46` private helpers after the replay-alert source split.
- `app/services/audit_bundles.py` already has one extracted owner module:
  `app/services/audit_bundle_replay_alert_corpus.py`.
- `app/services/retrieval_learning.py` already has one extracted owner module:
  `app/services/retrieval_learning_replay_alert_sources.py`.

Current concrete concern clusters visible in the broad files:

- `app/services/audit_bundles.py`
  - payload and reference serialization
  - schema and integrity validation
  - PROV graph construction and JSON-LD validation
  - validation-receipt lifecycle
  - training-run and release audit-bundle creation
- `app/services/retrieval_learning.py`
  - dataset materialization from feedback, replay, and claim-feedback sources
  - candidate package and threshold handling
  - candidate evaluation and change-impact reporting
  - reranker artifact creation and retrieval
  - governance-event recording for candidate and artifact flows

## Goal

Turn both files into narrow compatibility facades with focused owner modules and
measurably lower hotspot burden, without weakening runtime behavior, replay or
evaluation governance, audit-bundle integrity, or retrieval-learning data
contracts.

Success means:

- both owner cases remain explicit and current
- each milestone removes one coherent implementation family from the hotspot
  file into a focused owner module
- both files end the sequence with materially lower line and helper counts
- each file either leaves inherited hygiene debt entirely or is small enough to
  justify a final facade-only contract with a much lower ratchet ceiling
- audit-bundle, retrieval-learning, replay, and readiness verification remain
  green throughout

## Non-Goals

- No microservice extraction.
- No API route-family redesign.
- No schema redesign, table rename, or migration-number churn unless a narrow
  milestone proves it is required and safe.
- No broad `evidence.py`, `search.py`, or `agent_task_actions.py` work in this
  plan.
- No weakening of existing integration tests, audit-bundle validation, or
  retrieval-learning gates just to make the hotspot split easier.

## Scope

In scope:

- refreshing owner-case evidence for `IC-2112B1ADC5E8` and `IC-0D58F1624037`
- focused owner-module extraction from `app/services/audit_bundles.py`
- focused owner-module extraction from `app/services/retrieval_learning.py`
- new focused tests for extracted owner modules
- hygiene routing and ratchet updates for new owner modules
- docs and handoff updates needed to keep the new routing durable

Out of scope:

- unrelated UI, parser, or CLI restructuring
- new audit-bundle or retrieval-learning product capabilities
- parallel hotspot work on other services unless the new owner modules require
  a narrow helper dependency

## Owner Surfaces

- routing and governance:
  `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
  `docs/SESSION_HANDOFF.md`, and this plan
- audit-bundle hotspot:
  `app/services/audit_bundles.py`,
  `app/services/audit_bundle_*.py`,
  `tests/unit/test_search_api_harnesses.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_semantic_governance_ledger.py`
- retrieval-learning hotspot:
  `app/services/retrieval_learning.py`,
  `app/services/retrieval_learning_*.py`,
  `tests/unit/test_retrieval_learning_replay_alert_sources.py`,
  `tests/unit/test_search_api_harnesses.py`,
  `tests/integration/test_retrieval_learning_ledger.py`
- runtime and quality gates:
  `uv run docling-system-evaluation-data-readiness`,
  `uv run docling-system-agent-trace-review`,
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-hygiene-check`

## Placement Rules

- Keep `app/services/audit_bundles.py` and
  `app/services/retrieval_learning.py` as public compatibility facades until the
  owner cases are closed.
- New audit-bundle implementation must land in `app/services/audit_bundle_*.py`
  modules, not back in `audit_bundles.py`.
- New retrieval-learning implementation must land in
  `app/services/retrieval_learning_*.py` modules, not back in
  `retrieval_learning.py`.
- Do not create one new mega-module that simply relocates the hotspot.
- New tests must align to the extracted owner family and prove behavior through
  the existing public service entrypoints where appropriate.
- If a shared helper is needed across owner modules, give it an explicitly
  shared name and scope rather than burying it back inside the old facade.

## Weak-Point Prevention Contract

Weak point forecast: the likely failure is moving code into a new side file but
keeping the old hotspot as the real implementation center, or splitting along
incidental helper groups instead of stable owner boundaries. Another risk is
weakening audit or retrieval-learning verification to make the split appear
green.

Owner surface: the hotspot facades own compatibility, the new owner modules own
the extracted concerns, the focused tests own behavioral safety, the hygiene
policy owns no-growth ceilings, and this plan plus the handoff own the durable
sequence.

Freshness check: rerun
`uv run docling-system-architecture-quality-report --summary`,
`uv run docling-system-hygiene-check`, and
`uv run docling-system-improvement-case-summary` before each milestone closes.
For every implementation milestone, rerun
`uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
and `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` in the
same closeout window.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation |
| --- | --- | --- | --- | --- |
| Compatibility facade still contains the real implementation | hotspot file and new owner module family | focused unit and integration tests plus line-count diff review | the old file keeps most new logic or the new module is only a shallow wrapper | add a new helper to the old facade in a temp diff and reject the milestone when the reviewed diff shows hotspot growth without owner reduction |
| New owner module becomes the next dump file | `app/services/audit_bundle_*.py` or `app/services/retrieval_learning_*.py` | `uv run docling-system-hygiene-check` and architecture probe review | new owner module exceeds the target budget or mixes unrelated concerns | create an oversized mixed-concern trial module and verify hygiene would fail or the review threshold would block it |
| Audit-bundle validation semantics drift | audit-bundle owner modules and audit tests | `tests/unit/test_search_api_harnesses.py`, `tests/unit/test_agent_tasks_api.py`, `tests/integration/test_technical_report_harness_roundtrip.py`, `tests/integration/test_semantic_governance_ledger.py` | validation receipt, payload integrity, PROV graph, or audit-bundle route behavior changes unexpectedly | break one receipt or payload path in a controlled diff and verify the focused test fails |
| Retrieval-learning data or governance drift | retrieval-learning owner modules and retrieval tests | `tests/unit/test_search_api_harnesses.py`, `tests/unit/test_retrieval_learning_replay_alert_sources.py`, `tests/integration/test_retrieval_learning_ledger.py` | dataset materialization, candidate evaluation, reranker artifact, or governance-event behavior changes unexpectedly | remove one candidate or artifact field in a controlled diff and verify the focused test fails |
| Runtime quality stays green only because coverage got easier | runtime gates and docs | full DB-backed suite, readiness, trace review, and doc consistency | a milestone passes only after deleting, loosening, or narrowing required tests | compare before/after focused test scope in review and reject any split that reduces covered scenarios without stronger replacement coverage |

Future-Codex misuse scenario: the most likely wrong move is to extract a helper
cluster named after a transport detail, then continue adding business logic to
the old facade because it still “has the context.” This plan prevents that by
forcing named owner families around validation receipts, training or release
audit bundles, candidate evaluation, and reranker artifacts.

## Milestone Sequence

### Milestone 0: Baseline Lock And Split Targets

Outcome label: resolved

Purpose: freeze the current routed baseline and identify the exact first owner
families before any code movement starts.

Scope:

- refresh the live hotspot measurements for both files
- confirm both case IDs still match the current file state
- document the first split candidates and their owner-module destinations
- update this plan and the handoff with the refreshed baseline

Acceptance:

- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` still route
  `app/services/audit_bundles.py` through `IC-2112B1ADC5E8`
  and `app/services/retrieval_learning.py` through `IC-0D58F1624037`
- this plan identifies the first concrete extraction families for both files
- the refreshed baseline metrics in the plan match live command output

Implementation status on 2026-05-11 local / 2026-05-11 UTC:

- baseline lock refreshed in the plan, hygiene registry, architecture index,
  and session handoff
- `app/services/audit_bundles.py` measured at 3,306 lines and 58 private
  helpers before the first split
- first owner family confirmed as validation-receipt hashing, verification,
  persistence, and detail or latest response assembly under
  `app/services/audit_bundle_validation_receipts.py`

### Milestone 1: Audit Bundle Validation Receipt Split

Outcome label: reduced

Purpose: reduce `app/services/audit_bundles.py` by moving validation-receipt
and receipt-verification lifecycle concerns into a focused owner module.

Scope:

- add a narrow owner module such as
  `app/services/audit_bundle_validation_receipts.py`
- move receipt-core hashing, receipt verification, receipt-row creation, and
  latest or list retrieval helpers into that owner
- preserve the public `audit_bundles.py` entrypoints and route behavior

Acceptance:

- `app/services/audit_bundles.py` delegates the validation-receipt family to
  the new owner module
- focused audit-bundle receipt tests remain green
- the new owner module stays within a governed file budget
- `app/services/audit_bundles.py` line or helper count drops measurably
- remaining issue is explicitly routed to the next audit-bundle milestone

Implementation status on 2026-05-11 local / 2026-05-11 UTC:

- validation-receipt hashing, verification, row creation, and detail or latest
  response assembly now live in
  `app/services/audit_bundle_validation_receipts.py`
- `app/services/audit_bundles.py` now delegates validation-receipt creation and
  retrieval through the new owner module while preserving the public service
  entrypoints
- focused receipt tests are added in
  `tests/unit/test_audit_bundle_validation_receipts.py`
- the milestone is committed locally as `e2bc144`
  (`services: split audit bundle validation receipts`)
- current measured sizes after the split are:
  - `app/services/audit_bundles.py`: 3,018 lines, 51 private helpers
  - `app/services/audit_bundle_validation_receipts.py`: 447 lines, 2 private
    helpers
- the remaining routed audit-bundle hotspot work is now the payload and PROV
  owner split from Milestone 3

### Milestone 2: Retrieval Learning Candidate And Artifact Split

Outcome label: reduced

Purpose: reduce `app/services/retrieval_learning.py` by moving candidate
evaluation and reranker-artifact flows into focused owner modules.

Scope:

- add focused owner modules such as
  `app/services/retrieval_learning_candidates.py` and
  `app/services/retrieval_learning_artifacts.py`
- move candidate package, threshold resolution, change-impact reporting,
  reranker artifact creation, and detail or list response assembly into those
  owners
- keep `retrieval_learning.py` as the compatibility facade

Acceptance:

- candidate evaluation and reranker artifact flows no longer live primarily in
  `app/services/retrieval_learning.py`
- retrieval-learning unit and integration tests remain green
- the new owner modules stay within governed budgets
- `app/services/retrieval_learning.py` line or helper count drops measurably
- remaining issue is explicitly routed to the next retrieval-learning milestone

### Milestone 3: Audit Bundle Payload And PROV Split

Outcome label: reduced

Purpose: continue shrinking `app/services/audit_bundles.py` by moving one
payload-construction family behind the facade.

Scope:

- move either search-harness release bundle payload assembly or retrieval
  training-run payload and PROV graph construction into a new
  `app/services/audit_bundle_*.py` owner module
- keep schema validation, integrity checks, and public API behavior unchanged

Acceptance:

- one coherent payload or provenance family is fully delegated out of
  `app/services/audit_bundles.py`
- audit-bundle integration tests remain green
- the old facade’s line or helper count drops again

### Milestone 4: Retrieval Learning Dataset And Governance Split

Outcome label: reduced

Purpose: continue shrinking `app/services/retrieval_learning.py` by moving
dataset materialization and governance-event recording into focused owners.

Scope:

- move dataset materialization and source-normalization flows into a dedicated
  owner module
- move candidate or artifact governance-event recording into a focused owner if
  it does not naturally live with the dataset module
- preserve current durable rows, payload schemas, and route responses

Acceptance:

- dataset materialization and governance-event handling no longer live
  primarily in `app/services/retrieval_learning.py`
- retrieval-learning ledger integration tests remain green
- the old facade’s line or helper count drops again

### Milestone 5: Compatibility Facade Closeout

Outcome label: resolved

Purpose: finish the hotspot program by proving both files are narrow
compatibility facades with explicit owner families and updated case evidence.

Scope:

- tighten the residual facade contract for both files
- ratchet the hygiene ceilings to the new verified sizes
- update both improvement cases with deployed refs, measurements, and final
  owner-module routing
- refresh this plan, the handoff, and any affected architecture index docs

Acceptance:

- both files have lower verified hotspot burden than the current baseline
- both files primarily re-export or orchestrate focused owner modules instead of
  mixing several implementation families directly
- `config/improvement_cases.yaml` records updated measurement evidence for both
  cases
- `uv run docling-system-hygiene-check`,
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`,
  and `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
  remain green
- this plan and the handoff explicitly route the next oldest remaining open
  hotspot after these two are closed

## Required Implementation Artifacts

- new focused owner modules under `app/services/audit_bundle_*.py`
- new focused owner modules under `app/services/retrieval_learning_*.py`
- focused unit and integration tests for each extracted concern
- updated improvement-case entries and hygiene budgets for new owner modules

## Required Documentation And Handoff Updates

Every milestone in this plan must update:

- this plan
- `docs/SESSION_HANDOFF.md`

Update when affected:

- `docs/agentic_architecture_index.md`
- `docs/improvement_loop.md`
- `README.md`
- `SYSTEM_PLAN.md`

## Required Verification Gates

Every milestone:

```bash
git diff --check
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hygiene-check
uv run docling-system-improvement-case-summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

When `config/improvement_cases.yaml` or `config/hygiene_policy.yaml` changes:

```bash
uv run docling-system-improvement-case-validate
```

Audit-bundle milestones:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_semantic_governance_ledger.py
uv run pytest -q tests/unit/test_search_api_harnesses.py
uv run pytest -q tests/unit/test_agent_tasks_api.py
```

Retrieval-learning milestones:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_retrieval_learning_ledger.py
uv run pytest -q tests/unit/test_retrieval_learning_replay_alert_sources.py
uv run pytest -q tests/unit/test_search_api_harnesses.py
```

Runtime confidence after every implementation milestone:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
```

## Acceptance Criteria

This plan is complete only when:

- both hotspots remain explicitly owner-routed throughout
- `app/services/audit_bundles.py` and `app/services/retrieval_learning.py`
  each lose at least two coherent implementation families to focused owner
  modules
- each file ends the sequence as a narrower compatibility facade than the
  current baseline
- replacement owner modules are governed by explicit file budgets and tests
- runtime verification, readiness, and trace review remain green
- each milestone closes with docs, handoff, and one atomic local commit

## Stop Conditions

Stop and update the handoff before continuing if:

- a proposed extraction cannot be named as a stable owner family
- a new owner module would immediately exceed the file budget and become the
  next hotspot
- integration, readiness, or trace-review failures cannot be isolated to the
  milestone slice
- unrelated dirty files prevent staging a clean milestone commit

## Local Commit Closeout Policy

Each milestone closes as one local atomic commit after verification passes:

```bash
git status --short
git diff --stat
git add <milestone files only>
git diff --cached --stat
git commit -m "<area>: complete hotspot milestone <N> <short-name>"
git status -sb
```

A milestone in this plan is complete only after that local atomic commit
succeeds. A verified but uncommitted milestone is ready-to-close, not complete.

## Residual Risks And Next Milestone Routing

Residual risk after this plan will likely shift from these two files to the
next oldest open architecture hotspot such as `app/services/evidence.py` or the
remaining claim-support governance surfaces. The final closeout milestone must
route the next oldest open owner case explicitly rather than assuming these two
still dominate the backlog.

## Closeout Checklist

- [x] Baseline lock completed
- [x] Audit bundle validation-receipt owner split completed
- [ ] Retrieval-learning candidate and artifact split completed
- [ ] Audit-bundle payload or PROV split completed
- [ ] Retrieval-learning dataset and governance split completed
- [ ] Both cases updated with deployed refs and new measurements
- [ ] Docs and handoff aligned
- [ ] Each milestone committed atomically after verification
