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
same source selection and dedupe path. The facade accepts
`ImprovementCaseImportRequest` and returns `ImprovementCaseImportResult`, so new
boundary surfaces can reuse a typed import contract instead of copying CLI
payload shape.

Architecture inspection reports include an `architecture_inspection_measurement`
snapshot with severity counts and contract surface counts. Record and summarize
those snapshots with:

```bash
uv run docling-system-architecture-measure-record
uv run docling-system-architecture-measure-summary
```

The default history path is `storage/architecture_inspections/history.jsonl`.
That local JSONL history gives future agents a stable trend signal instead of
relying on ad hoc inspection notes.

## Non-Goals

- no automatic Git commit or PR creation
- no DB/API expansion before the file-backed contract proves useful
- no free-form cause or artifact vocabularies
- no hidden prompt memory as the source of truth
