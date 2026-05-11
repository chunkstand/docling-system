# General Improvement Loop

Status: Active repo-local contract
Status refreshed: 2026-05-11 local / 2026-05-11 UTC

## Purpose

The retrieval repair loop already observes failures, classifies them, converts
them into bounded artifacts, verifies changes, and measures outcomes. The
general improvement-case contract applies the same pattern to agent and
codebase failures that are not necessarily retrieval failures.

## Contract

The machine-readable registry lives at `config/improvement_cases.yaml`.

Current registry state from the 2026-05-11 local / 2026-05-11 UTC owner-split
closeout sequence through the local audit-and-evidence model-domain milestone:

- `uv run docling-system-improvement-case-summary` reports `case_count=26`,
  with one measured hygiene-gate case and 25 open architecture-governance
  cases.
- The architecture quality report emits current hotspot candidates for large or
  high-churn surfaces, and those candidates are now imported as open registry
  cases with structured owner surfaces, verification commands, and stop
  conditions.
- `app/services/audit_bundles.py` and `app/services/retrieval_learning.py` now
  have explicit owner-bootstrap cases (`IC-2112B1ADC5E8` and
  `IC-0D58F1624037`) instead of remaining milestone-owned hygiene debt.
- `app/ui/app.js` remains governed by explicit owner-bootstrap case
  `IC-1B643BA0AD90`. Milestone 6 reduced the shipped bootstrap from 4,335
  lines to 107 and moved the shared runtime plus page-family logic into
  `app/ui/modules/`, so this UI hotspot now routes through a real owner
  module family rather than one monolithic script.
- `IC-F2A8110185EB` remains the top open architecture-governance owner case, but
  the committed local retrieval-interaction, replay/release governance,
  retrieval-learning, evaluation-feedback, agent-task, audit-and-evidence,
  claim-support, and semantic-memory splits narrowed it to a 345-line
  compatibility facade with
  dedicated owner modules at
  `app/db/model_domains/retrieval_interactions.py`,
  `app/db/model_domains/retrieval_replay_governance.py`,
  `app/db/model_domains/retrieval_learning_examples.py`, and
  `app/db/model_domains/retrieval_learning_artifacts.py`,
  `app/db/model_domains/evaluation_feedback.py`, and
  `app/db/model_domains/agent_tasks.py`, and
  `app/db/model_domains/audit_and_evidence.py`, and
  `app/db/model_domains/claim_support.py`, and
  `app/db/model_domains/semantic_memory.py`. The High Value Technical Paydown
  plan is now closed locally. The compatibility-facade / public-import-contract
  milestone has started: Milestone 1 now lands an exact facade gate in
  `tests/unit/test_db_models_facade_contract.py`, the Milestone 1 closeout is
  committed locally as `776fa73`, and the next bounded
  follow-up for this owner case is Milestone 2 narrowing in
  `docs/db_models_compatibility_facade_milestone_plan.md`.
- `IC-050E60059A34` remains open but is now narrowed further: the committed
  local technical-report derivation/export split reduced
  `app/services/evidence.py` to 6,307 architecture-probe lines and moved the
  new owner family into `app/services/evidence_technical_report_exports.py`.
- `IC-A1E186A34097` remains open but is now narrowed further: the committed
  local report action-family split reduced `app/services/agent_task_actions.py`
  to 2,746 architecture-probe lines, reduced fan-out to 36, and moved the new
  owner family into `app/services/agent_actions/report_actions.py`.
- `IC-FD18EE2D3309`, `IC-03D7EFA03213`, and `IC-23F2C79C8AA7` remain open but
  are now narrowed substantially: the committed local test hotspot split pack A
  reduced `tests/unit/test_cli.py` to 424 lines, `tests/unit/test_search_api.py`
  to 436 lines, and `tests/unit/test_documents_api.py` to 613 lines while
  moving the split coverage into focused route-family and CLI owner files,
  including `tests/unit/test_cli_search_harness.py`.
- `IC-934588120F94` and `IC-40CA7C1FFA84` remain open but are now narrowed
  substantially: the committed local test hotspot split pack B reduced
  `tests/unit/test_agent_task_actions.py` to 417 lines and
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py` to
  337 lines while moving the split coverage into focused action-family and
  claim-support scenario-family files, including the aligned replay-alert
  change-impact split into activation, prevalidation, promotion, and
  governance files.
- The next routed implementation slice is now the `IC-F2A8110185EB` /
  `app/db/models.py` compatibility-facade Milestone 2 continuation from
  `docs/db_models_compatibility_facade_milestone_plan.md`.
- DB-backed import sources such as `eval-failure-cases`, `failed-agent-tasks`,
  and `failed-agent-verifications` require local Postgres to be available before
  they can be trusted as current.

Every case must declare:

- a closed cause class: `missing_context`, `missing_test`,
  `missing_constraint`, `bad_pattern`, `bad_tool`, `unclear_ownership`, or
  `unsafe_permission`
- a workflow version so future changes can be compared by process version

`open` and `suppressed` cases capture the observe/classify stage. `converted`,
`verified`, `deployed`, `measured`, and `closed` cases must also declare an
executable repo-local artifact target: `test`, `lint`, `contract`, `eval`,
`generated_map`, `script`, `runbook`, or `permission_rule`.

Converted cases must include a verification command or acceptance condition.
Verified, deployed, measured, and closed cases must explicitly prove that the
artifact catches the old failure and does not block good changes.

Deployed, measured, and closed cases must also carry deployment refs. Measured
and closed cases must include a metric name and value.

The repo hygiene command validates the registry by default:

```bash
uv run docling-system-hygiene-check
uv run docling-system-architecture-inspect
```

The hygiene command is now a ratchet gate for strict file/helper budgets. Current
inherited overages remain visible under an `inherited budget debt` section, but
they do not fail the command while they stay at or below their recorded
`ratchet_max_*` ceilings. Growth beyond a ratchet ceiling is reported under
`new hygiene regressions` and exits non-zero. Every ratcheted budget entry in
`config/hygiene_policy.yaml` must carry an `owner_case_id` or
`owner_milestone`; the hygiene tests include a policy negative case so unowned
ratchets cannot become hidden tolerance. The hygiene improvement-case import
source observes only blocking hygiene findings, so ratcheted inherited debt does
not create duplicate open cases while no-growth regressions still can.

## CLI

```bash
uv run docling-system-improvement-case-validate
uv run docling-system-improvement-case-summary
uv run docling-system-improvement-case-list
uv run docling-system-improvement-case-import --source hygiene --dry-run
uv run docling-system-improvement-case-import \
  --source architecture-governance-report \
  --source-path-for \
  architecture-governance-report=build/architecture-governance/architecture_governance_report.json
uv run docling-system-improvement-case-import --source all
uv run docling-system-improvement-case-update \
  --case-id IC-20260424-hygiene-gate \
  --status measured \
  --deployed-ref 78ec3c8 \
  --metric-name hygiene_architecture_findings \
  --metric-value 0
uv run docling-system-improvement-case-record \
  --title "Route capability strings drifted" \
  --observed-failure "Routers accepted free-form capability strings." \
  --cause-class missing_constraint \
  --artifact-type contract \
  --artifact-path app/api/route_contracts.py \
  --artifact-description "FastAPI route capability manifest and validator." \
  --verification-command "uv run pytest tests/unit/test_api_route_contracts.py -q"
```

The update command transitions existing cases after conversion. It validates the
full registry before writing, so a `measured` or `closed` transition cannot land
without both a deployment ref and metric evidence.

The import command observes existing repo surfaces and writes deduped `open`
cases keyed by `source_type` and `source_ref`. Supported sources are:

- `hygiene`: Ruff regressions, duplicate-helper findings, file-budget findings,
  and improvement-case contract findings
- `architecture-governance-report`: architecture inspection violations and stale
  measurement freshness from a JSON governance report
- `eval-failure-cases`: unresolved DB-backed evaluation failure cases
- `failed-agent-tasks`: failed DB-backed agent tasks
- `failed-agent-verifications`: failed or errored agent verification rows
- `all`: all of the above

Summary output includes lifecycle buckets for open unconverted cases,
converted-but-unverified cases, verified-but-undeployed cases, repeated cause
classes, and the oldest open case ID.

The import orchestration lives in `app.services.improvement_case_intake`; the
CLI is only an argument parser and JSON renderer. Keep new observation sources
behind that service facade so later API, worker, or UI surfaces can reuse the
same source selection and dedupe path. The facade owns an internal source
registry that records each source's kind, DB-session requirement, and
source-path support, so adding a source means declaring its operational
contract before routing it. The facade accepts keyed `source_paths` so each
file-backed source receives only its own input path; the CLI exposes that as
repeatable `--source-path-for SOURCE=PATH`. The legacy `source_path` shortcut is
still accepted only when the selected source set has exactly one file-backed
source, and the facade rejects path input for sources whose registry entry does
not declare file-path support. The facade accepts
`ImprovementCaseImportRequest` and returns `ImprovementCaseImportResult`, so new
boundary surfaces can reuse a typed import contract instead of copying CLI
payload shape.

Architecture inspection reports include an `architecture_inspection_measurement`
snapshot with severity counts, contract surface counts, per-rule violation
counts, and per-contract violation counts. Record and summarize those snapshots
with:

```bash
uv run docling-system-architecture-measure-record
uv run docling-system-architecture-measure-summary
uv run docling-system-architecture-governance-report \
  --record-current \
  --history-path build/architecture-governance/architecture_measurement_history.jsonl \
  --output-path build/architecture-governance/architecture_governance_report.json
```

The architecture-governance CI workflow dry-runs
`docling-system-improvement-case-import --source architecture-governance-report`
against the generated report with keyed `--source-path-for` input before the
architecture gates, which proves the report remains a valid self-improvement
intake source.

The default history path is `storage/architecture_inspections/history.jsonl`.
That local JSONL history gives future agents a stable trend signal instead of
relying on ad hoc inspection notes. The summary command reports aggregate
violation deltas and rule-level or contract-level deltas, so recurring boundary
failures can be measured against stable rule IDs instead of prose labels. The
architecture contract map publishes the measurement, summary, and delta field
lists as a machine-readable contract for agents that need to compare history
records across commits. Operators and agents can also read the latest
architecture inspection report and measurement trend through
`GET /architecture/inspection` and `GET /architecture/measurements/summary`;
both endpoints are read-only and require the `system:read` API capability in
remote mode. The summary endpoint includes `current_commit_sha`,
`latest_recorded_commit_sha`, `is_current`, and `recording_required` so stale
measurement histories are explicit instead of silently looking current. The
governance report command packages that inspection and freshness state as a
CI-uploaded JSON artifact. In CI, `--record-current` writes only to the
build-scoped history file, so GitHub and future agents can observe architecture
health without relying on ignored local `storage/` history.

## Non-Goals

- no automatic Git commit or PR creation
- no write-side DB/API expansion before the file-backed contract proves useful
- no free-form cause or artifact vocabularies
- no hidden prompt memory as the source of truth
