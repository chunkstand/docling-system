# Session Handoff

Date: 2026-04-12 local / 2026-04-12 UTC verification
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
PR: `#1` `Build docling-system v1 ingestion, retrieval, evaluation, and run audit surfaces`
PR URL: `https://github.com/chunkstand/docling-system/pull/1`
Latest committed checkpoint: `5a1659a` (`Add replayable run failures and audit surfaces`)

## Executive Summary

This session closed two substantive areas of work and split them cleanly in git history:

1. evaluation deepening
2. harness milestone 1 for replayable failures and auditability

The branch is pushed, the PR is open, the working tree is clean, Alembic is at `0009_run_failure_artifacts`, the audit passes with zero violations, and the active eight-document corpus still evaluates cleanly.

## What Landed This Session

### 1. Evaluation Deepening

Commit:

- `e8e867c` `Deepen evaluation coverage and harden caption checks`

What changed:

- expanded `docs/evaluation_corpus.yaml` so every fixture now has at least three retrieval queries
- increased query depth for thin fixtures such as:
  - `born_digital_simple`
  - `appendix_b_prose_guidance`
  - `upc_ch4`
  - `upc_ch5`
  - `upc_ch7`
- added figure structural assertions for active documents that previously lacked them:
  - `awkward_headers` (`UPC_CH_3.pdf`)
  - `upc_ch7` (`UPC_CH_7.pdf`)
- hardened evaluation caption checks in `app/services/evaluations.py` so non-string caption-like values no longer crash structural evaluation
- fixed a YAML fixture parsing issue by quoting `Flood: M/P/E Systems`

Relevant files:

- `docs/evaluation_corpus.yaml`
- `app/services/evaluations.py`
- `tests/unit/test_eval_config.py`
- `tests/unit/test_evaluation_service.py`

Durable outcome:

- all active documents still evaluate successfully
- the fixed corpus is materially stronger than the prior session

### 2. Harness Milestone 1

Commit:

- `5a1659a` `Add replayable run failures and audit surfaces`

What changed:

- added `document_runs.failure_stage`
- added `document_runs.failure_artifact_path`
- added migration `0009_run_failure_artifacts`
- failed runs now persist replayable `failure.json` artifacts in the run directory
- successful runs clear stale failure artifacts
- terminal stale-lease failures also emit failure artifacts
- added `GET /documents/{document_id}/runs`
- added `GET /runs/{run_id}/failure-artifact`
- added `docling-system-audit` CLI
- added a basic integrity audit service for:
  - active-run completion invariant
  - active-run validation invariant
  - completed-run artifact presence
  - failed-run replayability
- added operator UI support for recent processing attempts and failure artifact links
- backfilled one legacy failed run locally so the new audit contract is clean on the current dataset

Relevant files:

- `alembic/versions/0009_run_failure_artifacts.py`
- `app/api/main.py`
- `app/cli.py`
- `app/db/models.py`
- `app/schemas/documents.py`
- `app/services/audit.py`
- `app/services/cleanup.py`
- `app/services/documents.py`
- `app/services/runs.py`
- `app/services/storage.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `app/ui/styles.css`
- `tests/unit/test_cli.py`
- `tests/unit/test_documents_api.py`
- `tests/unit/test_run_logic.py`
- `tests/unit/test_ui.py`

Durable outcome:

- failed runs are now inspectable and replay-oriented rather than just error-message oriented
- the system has a machine-checkable audit surface, not only ad hoc inspection

## Git State

Current branch:

- `codex/docling-system-build`

Recent commits:

```text
5a1659a Add replayable run failures and audit surfaces
e8e867c Deepen evaluation coverage and harden caption checks
cb47ba0 Update session handoff
69f21bb Refine operator UI and add Appendix B evaluation fixture
```

Push / PR state:

- branch pushed to `origin/codex/docling-system-build`
- PR open against `main`
- PR URL: `https://github.com/chunkstand/docling-system/pull/1`

Working tree:

```text
[clean worktree]
```

## Current Runtime State

At handoff time:

- API health check succeeds at `http://127.0.0.1:8000/health`
- Alembic head is `0009_run_failure_artifacts`
- `docling-system-audit` reports zero violations
- active evaluated corpus remains eight documents

Verification:

```bash
curl -sS http://127.0.0.1:8000/health
uv run alembic current
uv run docling-system-audit
git status --short
```

Observed results:

```json
{"status":"ok"}
```

```text
0009_run_failure_artifacts (head)
```

```json
{"checked_documents":8,"checked_runs":27,"violation_count":0,"violations":[]}
```

```text
[clean worktree]
```

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

Notable current eval depth:

- `upc_ch5` now evaluates `4` queries and still passes all structural checks
- `upc_ch7` now evaluates `4` queries and now also pins figure-count/caption/provenance/artifact coverage
- `awkward_headers` now pins `29` figures structurally and passes
- `appendix_b_prose_guidance` now evaluates `3` prose queries

## Verification Performed This Session

Commands run and observed passing:

```bash
uv run pytest -q
uv run pytest tests/unit/test_eval_config.py tests/unit/test_evaluation_service.py -q
node --check app/ui/app.js
uv run python -m compileall app tests
uv run alembic upgrade head
uv run docling-system-eval-corpus
uv run docling-system-audit
```

Key results:

- `64 passed, 1 skipped` on the full pytest suite
- `8 passed` for eval-config / evaluation-service focused tests
- JS syntax check passed
- compileall passed
- migration to `0009_run_failure_artifacts` succeeded
- full corpus eval succeeded for all eight active fixtures
- audit passed with zero violations

## Current Contracts To Preserve

### Promotion

- validation still hard-gates promotion
- evaluation still does not block promotion

### Evaluation

- the fixed corpus in `docs/evaluation_corpus.yaml` is now stronger and should remain the durable contract
- fixture regressions should be fixed by corpus/ranking/provenance work before adding more ad hoc heuristics
- figure assertions now matter for `UPC_CH_3.pdf` and `UPC_CH_7.pdf`; do not silently weaken them

### Harness

- failed runs should continue to emit replayable `failure.json`
- `docling-system-audit` should stay green or failures should be treated as real invariant regressions
- `GET /documents/{document_id}/runs` and `GET /runs/{run_id}/failure-artifact` are now part of the operator surface

### Supplements

- chapter PDFs remain canonical
- supplement PDFs remain narrow repair inputs only
- overlay outputs must preserve chapter-local page span and original source-segment provenance

## Known Gaps / Risks

### 1. Evaluation Still Does Not Gate Promotion

This is still deliberate. A run can promote if validation passes even if retrieval quality is worse.

### 2. Audit Is Foundational, Not Yet Deep

The new audit currently checks a useful first set of invariants, but it is still a thin harness:

- no count-crosschecks between DB rows and run summaries
- no artifact-hash consistency checks
- no evaluation-presence invariant for all completed latest runs
- no richer corpus quality dashboard yet

### 3. Failure Artifacts Are Replay-Oriented But Minimal

Current `failure.json` is useful, but stage-local snapshots are still limited. There is still room to persist:

- parsed previews
- partial normalized tables/chunks/figures
- richer config/runtime metadata

### 4. PR Contains Full Branch History

The PR is correct, but it includes the full buildout since `main`, not only the final two commits.

## Recommended Next Steps

### Priority 1: Lopopolo Milestone 2

Deepen the audit contract and expose corpus quality.

Target implementation scope:

- expand `docling-system-audit` to verify:
  - run summary counts against persisted DB rows
  - latest evaluation presence for completed latest runs
  - table/figure artifact path existence when DB rows claim artifacts
  - required `failure.json` schema fields
  - known failure-stage membership
- add corpus quality API endpoints such as:
  - `GET /quality/summary`
  - `GET /quality/failures`
  - `GET /quality/evaluations`
- add a UI quality panel for:
  - latest eval status across documents
  - failed query counts
  - structural check failures
  - failed runs grouped by stage
- add unit/API tests for each audit rule and quality endpoint

Why this is next:

- milestone 1 made failures replayable
- milestone 2 should make the system judge itself more rigorously and expose that quality state without manual inspection

### Priority 2: Add Better Quality Dashboards

- corpus quality summaries
- evaluation trend summaries
- explicit regression/improvement views from persisted eval data

### Priority 3: Specify Nontrivial Transform Contracts

- document chunk normalization contract
- document logical-table build contract
- document overlay contract
- document figure-caption resolution contract

### Priority 4: Decide PR Strategy

- either merge the current PR as the full v1 build branch
- or split future work into narrower follow-up branches after this one lands

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

Read document runs:

```bash
curl -sS http://127.0.0.1:8000/documents/<document_id>/runs | jq
```

Read a failure artifact:

```bash
curl -sS http://127.0.0.1:8000/runs/<run_id>/failure-artifact | jq
```

Run the corpus eval sweep:

```bash
uv run docling-system-eval-corpus
```

Run the integrity audit:

```bash
uv run docling-system-audit
```

Open the PR:

```text
https://github.com/chunkstand/docling-system/pull/1
```
