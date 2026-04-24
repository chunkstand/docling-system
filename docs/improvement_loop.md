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
- an executable artifact target: `test`, `lint`, `contract`, `eval`,
  `generated_map`, `script`, `runbook`, or `permission_rule`
- a verification command or acceptance condition
- explicit evidence that verification catches the old failure and does not
  block good changes
- a workflow version so future changes can be compared by process version

Deployed, measured, and closed cases must also carry deployment refs. Measured
and closed cases must include a metric name and value.

## CLI

```bash
uv run docling-system-improvement-case-validate
uv run docling-system-improvement-case-summary
uv run docling-system-improvement-case-list
uv run docling-system-improvement-case-record \
  --title "Route capability strings drifted" \
  --observed-failure "Routers accepted free-form capability strings." \
  --cause-class missing_constraint \
  --artifact-type contract \
  --artifact-path app/api/route_contracts.py \
  --artifact-description "FastAPI route capability manifest and validator." \
  --verification-command "uv run pytest tests/unit/test_api_route_contracts.py -q"
```

## Non-Goals

- no automatic Git commit or PR creation
- no DB/API expansion before the file-backed contract proves useful
- no free-form cause or artifact vocabularies
- no hidden prompt memory as the source of truth
