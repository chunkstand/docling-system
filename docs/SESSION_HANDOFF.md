# Session Handoff

Date: 2026-04-12 local / 2026-04-12 UTC verification
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
PR: `#1` `Build docling-system v1 ingestion, retrieval, evaluation, and run audit surfaces`
PR URL: `https://github.com/chunkstand/docling-system/pull/1`
Latest committed checkpoint before this handoff update: `5e98907` (`Backfill legacy audit fields`)

## Executive Summary

This session completed Lopopolo milestone 2 and then repaired the historical corpus so the stricter audit contract passes live.

What is now true:

- deeper audit invariants are implemented
- corpus quality is exposed through dedicated API endpoints and an operator UI quality panel
- legacy run rows were backfilled so historical data conforms to the current audit contract
- `uv run docling-system-audit` now completes live with zero violations

## What Landed This Session

### 1. Lopopolo Milestone 2

Commit:

- `0e41420` `Implement Lopopolo milestone 2 quality surfaces`

What changed:

- expanded `docling-system-audit` in `app/services/audit.py` to verify:
  - run chunk/table/figure summary counts against persisted DB rows
  - latest evaluation presence for completed latest runs
  - table and figure artifact path existence when rows claim artifacts
  - required `failure.json` schema fields
  - known failure-stage membership
- added corpus quality aggregation service in `app/services/quality.py`
- added typed quality schemas in `app/schemas/quality.py`
- added new quality endpoints:
  - `GET /quality/summary`
  - `GET /quality/failures`
  - `GET /quality/evaluations`
- added a quality panel to the operator UI showing:
  - latest evaluation coverage
  - failed query totals
  - structural check failures
  - failed runs grouped by stage
  - evaluation and run failure rollups
- added unit tests for the new audit rules, quality service logic, quality API routes, and UI presence

Relevant files:

- `app/api/main.py`
- `app/schemas/quality.py`
- `app/services/audit.py`
- `app/services/quality.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `app/ui/styles.css`
- `tests/unit/test_audit_service.py`
- `tests/unit/test_quality_api.py`
- `tests/unit/test_quality_service.py`
- `tests/unit/test_ui.py`

Durable outcome:

- milestone 2 is implemented rather than still planned
- the system now exposes corpus quality as a first-class operator surface
- the audit contract is materially deeper than milestone 1

### 2. Legacy Audit Backfill

Commit:

- `5e98907` `Backfill legacy audit fields`

Why this was needed:

- after milestone 2, the first live audit no longer passed
- the failures were historical-data drift, not current-run behavior regressions
- old runs predated the current figure-count and failure-stage contract

Observed live audit failure before backfill:

```json
{
  "checked_documents": 8,
  "checked_runs": 27,
  "checked_evaluations": 14,
  "checked_tables": 481,
  "checked_figures": 344,
  "violation_count": 15,
  "violation_counts_by_code": {
    "failed_run_unknown_failure_stage": 1,
    "run_figure_count_mismatch": 14
  }
}
```

What changed:

- added reusable legacy audit-field backfill logic in `app/services/cleanup.py`
- added CLI entrypoint `docling-system-backfill-legacy-audit`
- backfill now:
  - fills missing `chunk_count`, `table_count`, and `figure_count` from persisted DB rows
  - normalizes legacy failure stages using existing validation metadata
  - rewrites persisted `failure.json` artifacts when the normalized failure stage changes
- added unit coverage for the cleanup/backfill path and CLI wiring

Relevant files:

- `app/cli.py`
- `app/services/cleanup.py`
- `pyproject.toml`
- `tests/unit/test_cleanup.py`
- `tests/unit/test_cli.py`

Live backfill result:

```json
{
  "runs_scanned": 27,
  "chunk_count_backfilled": 0,
  "table_count_backfilled": 0,
  "figure_count_backfilled": 15,
  "failure_stage_backfilled": 1,
  "failure_artifacts_updated": 1
}
```

Durable outcome:

- the stricter audit contract now works against the current local corpus, not only against fresh runs
- legacy drift is normalized in a reusable way instead of being repaired by one-off SQL

## Git State

Current branch:

- `codex/docling-system-build`

Recent commits:

```text
5e98907 Backfill legacy audit fields
0e41420 Implement Lopopolo milestone 2 quality surfaces
f3a0e20 Update handoff with next Lopopolo milestone
5a1659a Add replayable run failures and audit surfaces
e8e867c Deepen evaluation coverage and harden caption checks
```

Push / PR state:

- PR `#1` is still the correct PR for this work
- the branch should remain aligned with `origin/codex/docling-system-build`
- this handoff assumes the latest local commits are pushed before the next session starts

## Current Runtime State

At handoff time:

- API health check succeeds at `http://127.0.0.1:8000/health`
- Alembic head in the running database is `0009_run_failure_artifacts`
- `docling-system-audit` completes live with zero violations
- the active evaluated corpus remains eight documents

Live audit result after backfill:

```json
{
  "checked_documents": 8,
  "checked_runs": 27,
  "checked_evaluations": 14,
  "checked_tables": 481,
  "checked_figures": 344,
  "violation_count": 0,
  "violation_counts_by_code": {},
  "violations": []
}
```

Additional live confirmation:

- `document_runs.figure_count is null` count: `0`
- `document_runs.failure_stage = 'legacy_failure'` count: `0`

## Active Corpus State

Current active/evaluated set remains:

- `UPC_CH_5.pdf` -> fixture `upc_ch5`
- `UPC_CH_4.pdf` -> fixture `upc_ch4`
- `UPC_Appendix_N.pdf` -> fixture `born_digital_simple`
- `UPC_Appendix_B.pdf` -> fixture `appendix_b_prose_guidance`
- `UPC_CH_3.pdf` -> fixture `awkward_headers`
- `UPC_Ch_2.pdf` -> fixture `upc_ch2_figures`
- `UPC_CH_7.pdf` -> fixture `upc_ch7`
- `UPC_CH_1.pdf` -> fixture `prose_control`

## Verification Performed This Session

Commands run and observed passing:

```bash
uv run ruff check app/services/audit.py app/services/quality.py app/schemas/quality.py app/api/main.py tests/unit/test_audit_service.py tests/unit/test_quality_service.py tests/unit/test_quality_api.py tests/unit/test_ui.py
uv run pytest tests/unit -q
uv run python -m compileall app tests
node --check app/ui/app.js
uv run ruff check app/services/cleanup.py app/cli.py tests/unit/test_cleanup.py tests/unit/test_cli.py pyproject.toml
uv run pytest tests/unit/test_cleanup.py tests/unit/test_cli.py tests/unit/test_audit_service.py tests/unit/test_quality_service.py tests/unit/test_quality_api.py -q
uv run docling-system-backfill-legacy-audit
uv run docling-system-audit
```

Key results:

- `72 passed` on the full unit suite
- milestone 2 lint checks passed
- cleanup/backfill lint checks passed
- JS syntax check passed
- compileall passed
- legacy audit-field backfill completed successfully
- live audit passed with zero violations after the backfill

## Current Contracts To Preserve

### Promotion

- validation still hard-gates promotion
- evaluation still does not block promotion

### Evaluation

- the fixed corpus in `docs/evaluation_corpus.yaml` remains the durable retrieval contract
- quality endpoints should report persisted evaluation state, not recompute ad hoc document-by-document status in the UI

### Audit

- `docling-system-audit` now checks:
  - active-run completion and validation invariants
  - completed-run document artifact presence
  - failed-run replayability
  - run summary count crosschecks
  - latest-evaluation presence for completed latest runs
  - table/figure artifact-path existence
  - required `failure.json` schema fields
  - known failure-stage membership
- audit failures should still be treated as real invariants unless a row is explicitly identified as legacy data requiring backfill

### Backfill

- use `docling-system-backfill-legacy-audit` for historical normalization instead of manual SQL
- the intended historical normalization behavior is:
  - missing run counts are filled from persisted child rows
  - legacy failure-stage values are normalized from existing validation metadata when possible
  - matching persisted `failure.json` artifacts are rewritten to stay in sync

### Supplements

- chapter PDFs remain canonical
- supplement PDFs remain narrow repair inputs only
- overlay outputs must preserve chapter-local page span and original source-segment provenance

## Known Gaps / Risks

### 1. Evaluation Still Does Not Gate Promotion

This is still deliberate. A run can promote if validation passes even if retrieval quality is worse.

### 2. Quality Surfaces Are First Useful Slice, Not Final Dashboard

Milestone 2 now exposes summary/failures/evaluations, but it is still a thin operational dashboard:

- no historical trend charts
- no eval deltas over time across many runs
- no explicit artifact-hash consistency audit yet
- no richer regression drilldown UI yet

### 3. Backfill Logic Is Heuristic for Truly Legacy Rows

The current backfill normalizes legacy rows using persisted run metadata and `validation_results`. That is the right operational move here, but if older datasets with different historical shapes appear later, additional mapping rules may be needed.

### 4. PR Contains Full Branch History

The PR is still correct, but it includes the full buildout since `main`, not only the milestone 2 and backfill commits.

## Recommended Next Steps

### Priority 1: Better Quality Dashboards

- corpus quality summaries over time
- evaluation trend summaries
- regression/improvement views from persisted eval data
- clearer UI surfacing for which documents are missing evaluation vs failing evaluation

### Priority 2: Specify Nontrivial Transform Contracts

- document chunk normalization contract
- document logical-table build contract
- document overlay contract
- document figure-caption resolution contract

### Priority 3: Consider Whether Completed Latest Runs Should Always Be Evaluated

The audit now expects persisted evaluation presence for completed latest runs. If there is ever a workflow where that should not be true, the product contract should be clarified explicitly rather than relaxed implicitly.

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

Run the quality summary endpoint:

```bash
curl -sS http://127.0.0.1:8000/quality/summary | jq
```

Run the quality failures endpoint:

```bash
curl -sS http://127.0.0.1:8000/quality/failures | jq
```

Run the quality evaluations endpoint:

```bash
curl -sS http://127.0.0.1:8000/quality/evaluations | jq
```

Run the legacy backfill:

```bash
uv run docling-system-backfill-legacy-audit
```

Run the integrity audit:

```bash
uv run docling-system-audit
```

Open the PR:

```text
https://github.com/chunkstand/docling-system/pull/1
```
