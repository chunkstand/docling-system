# General Improvement Loop

Status: Active repo-local contract

## Purpose

The retrieval repair loop already observes failures, classifies them, converts
them into bounded artifacts, verifies changes, and measures outcomes. The
general improvement-case contract applies the same pattern to agent and
codebase failures that are not necessarily retrieval failures.

## Contract

The machine-readable registry lives at `config/improvement_cases.yaml`.

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
