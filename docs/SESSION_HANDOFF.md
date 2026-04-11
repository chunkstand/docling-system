# Session Handoff

Date: 2026-04-10 (local) / 2026-04-11 UTC runtime timestamps
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Last committed checkpoint: `d409f39` (`Close retrieval gaps and add bitter lesson guidance`)

## Executive Summary

The system is now beyond the prior table/figure milestone. The main change in this session was adding a persisted, run-scoped evaluation subsystem that:

- reads `docs/evaluation_corpus.yaml`
- evaluates the same production search path against an explicit `run_id`
- stores evaluation summaries and per-query results in Postgres
- records query-level candidate rank, baseline rank, and rank delta
- exposes the latest evaluation through API and UI
- provides CLI commands for evaluating one run or the whole corpus

The `born_digital_simple` gap is closed with `UPC_Appendix_N.pdf`, and the ranking fix for table-title queries remains in place. The current evaluation corpus runs cleanly end to end.

## Current Runtime State

At handoff time:

- Postgres is healthy on `localhost:5432`
- API is running on `http://127.0.0.1:8000`
- one worker process is running
- Alembic head is `0008_run_evaluations`

Verification:

```bash
curl -sS http://127.0.0.1:8000/health
uv run alembic current
```

Results:

```json
{"status":"ok"}
```

```text
0008_run_evaluations (head)
```

Current active document set:

```json
[
  {
    "document_id": "4a3134a8-088d-441c-b5da-735563ed5e35",
    "source_filename": "UPC_Appendix_N.pdf",
    "active_run_id": "befc5635-1cab-456c-b8bf-0aa27fd6497f",
    "latest_validation_status": "passed",
    "table_count": 1,
    "figure_count": 0,
    "latest_evaluation_fixture": "born_digital_simple",
    "latest_evaluation_status": "completed"
  },
  {
    "document_id": "4a8da24f-603b-4540-baa2-431a2b10baaf",
    "source_filename": "UPC_CH_3.pdf",
    "active_run_id": "0ac3a1ff-5a6b-47d6-90a1-31157b0e055c",
    "latest_validation_status": "passed",
    "table_count": 2,
    "figure_count": 29,
    "latest_evaluation_fixture": "awkward_headers",
    "latest_evaluation_status": "completed"
  },
  {
    "document_id": "215a55c7-508f-41ba-8440-cba24f0c3e41",
    "source_filename": "UPC_Ch_2.pdf",
    "active_run_id": "2c094484-7651-4efd-b26a-0b9b8ca9237c",
    "latest_validation_status": "passed",
    "table_count": 0,
    "figure_count": 18,
    "latest_evaluation_fixture": "upc_ch2_figures",
    "latest_evaluation_status": "completed"
  },
  {
    "document_id": "f9cf2f57-441f-495b-9fb1-6108da3d1731",
    "source_filename": "UPC_CH_7.pdf",
    "active_run_id": "cc4c107c-a1ab-4bc4-b461-355aadcd7855",
    "latest_validation_status": "passed",
    "table_count": 11,
    "figure_count": 10,
    "latest_evaluation_fixture": "upc_ch7",
    "latest_evaluation_status": "completed"
  },
  {
    "document_id": "a85d7a04-5ee6-4067-af9b-7012f54fab39",
    "source_filename": "UPC_CH_1.pdf",
    "active_run_id": "2c95e372-0b2a-46f0-9c1e-f6c3a85b5137",
    "latest_validation_status": "passed",
    "table_count": 0,
    "figure_count": 0,
    "latest_evaluation_fixture": "prose_control",
    "latest_evaluation_status": "completed"
  }
]
```

## What Changed In This Session

### 1. Run-Scoped Evaluation Storage

Added persisted evaluation storage:

- `document_run_evaluations`
- `document_run_evaluation_queries`

Files:

- `app/db/models.py`
- `alembic/versions/0008_run_evaluations.py`

Current stored evaluation contract:

- one evaluation record per `(run_id, corpus_name, eval_version)`
- fixture name
- evaluation status: `pending`, `completed`, `failed`, or `skipped`
- summary JSON with aggregate counts
- per-query rows with:
  - query text
  - search mode
  - filters
  - expected result type
  - expected top-N threshold
  - pass/fail
  - candidate rank
  - baseline rank
  - rank delta
  - candidate/baseline score
  - candidate/baseline labels
  - top-result snapshots in details JSON

### 2. Search Refactor For Explicit `run_id`

Production search now supports two scopes using the same code path:

- default active-run search for API/UI behavior
- explicit `run_id` search for evaluation

File:

- `app/services/search.py`

Important implementation detail:

- evaluation does not use a parallel “shadow” search implementation
- it calls the same production search/ranking logic with `run_id=<candidate>` or `run_id=<baseline>`

This was the main architectural requirement for trustworthy regression deltas.

### 3. Evaluation Service

Added a new evaluation service:

- `app/services/evaluations.py`

Behavior:

- reads `docs/evaluation_corpus.yaml`
- matches a fixture by `document.source_filename`
- compiles expected table/chunk queries into evaluation cases
- evaluates the candidate run
- optionally evaluates a baseline run
- persists summary and per-query rows

Current corpus behavior:

- fixtures with no matching path are skipped
- matched fixtures produce stored evaluation results
- query-level pass/fail is based on expected result type appearing within expected top-N

### 4. Worker Integration

Evaluation is now part of the worker path.

Order:

1. parse
2. persist artifacts/chunks/tables/figures
3. validate
4. evaluate
5. promote

File:

- `app/services/runs.py`

Important choice:

- evaluation is non-blocking for promotion in the current implementation
- validation still gates promotion
- evaluation failure records evaluation status but does not currently reject an otherwise valid run

### 5. CLI Commands

Added:

- `docling-system-eval-run <run_id> [--baseline-run-id <run_id>]`
- `docling-system-eval-corpus`

Files:

- `app/cli.py`
- `pyproject.toml`

Purpose:

- operator-triggered re-evaluation of one run
- batch re-evaluation of all active documents with matching fixtures

### 6. API And UI Surfacing

Added:

- latest evaluation summary on document list/detail payloads
- `GET /documents/{document_id}/evaluations/latest`
- read-only UI rendering for latest evaluation status and per-query results

Files:

- `app/schemas/evaluations.py`
- `app/schemas/documents.py`
- `app/services/documents.py`
- `app/api/main.py`
- `app/ui/index.html`
- `app/ui/app.js`

Live example:

`GET /documents/4a8da24f-603b-4540-baa2-431a2b10baaf/evaluations/latest` currently returns:

- fixture: `awkward_headers`
- `query_count: 3`
- `passed_queries: 3`
- `failed_queries: 0`
- all three queries currently rank the expected type at candidate rank `1`

## Evaluation Corpus Status

Current configured fixtures:

- `upc_ch7`
- `upc_ch2_figures`
- `born_digital_simple`
- `awkward_headers`
- `prose_control`

`born_digital_simple` is now:

- path: `/Users/chunkstand/Documents/UPC/UPC_Appendix_N.pdf`
- expected logical table count: `1`
- logical table tolerance: `0`
- query: `correlation between temperature ranges`

Corpus-wide evaluation command:

```bash
uv run docling-system-eval-corpus
```

Current result:

- all five configured fixtures complete successfully
- all configured query cases currently pass

Important limitation:

- current stored baseline deltas are only meaningful when a baseline run is provided or an older active run is still available for comparison
- the current corpus run shown in this session was evaluated with `baseline_run_id: null`, so `rank_delta` is null for those rows

The plumbing for deltas exists; the next useful step is to evaluate candidate reprocesses against previous active runs so query-level regressions become longitudinal instead of single-run snapshots.

## Current Contracts

### Promotion Gate

Promotion still requires validation success before `documents.active_run_id` advances.

Evaluation does not currently gate promotion.

This split is intentional:

- validation protects search integrity and artifact correctness
- evaluation measures retrieval quality over time

### Search

`POST /search` remains the active-corpus endpoint.

New internal/runtime capability:

- the service layer can now execute the same search path against an explicit `run_id`

This is used by evaluation and should remain the single ranking implementation.

### Evaluation Storage

Evaluation is now a first-class persisted subsystem and must not be overloaded into:

- `validation_results_json`
- ad hoc metric files
- hand-written notes in docs

Validation and evaluation are separate concerns and should remain separate.

## Files Changed Or Added Recently

Core runtime:

- `app/api/main.py`
- `app/cli.py`
- `app/db/models.py`
- `app/schemas/documents.py`
- `app/schemas/evaluations.py`
- `app/services/documents.py`
- `app/services/evaluations.py`
- `app/services/runs.py`
- `app/services/search.py`

UI:

- `app/ui/index.html`
- `app/ui/app.js`

Migration:

- `alembic/versions/0008_run_evaluations.py`

Tests:

- `tests/unit/test_cli.py`
- `tests/unit/test_documents_api.py`
- `tests/unit/test_evaluation_service.py`
- `tests/unit/test_search_service.py`
- `tests/unit/test_ui.py`

Config:

- `pyproject.toml`

## Verification Performed

Commands run this session:

```bash
uv run alembic upgrade head
uv run pytest tests
uv run python -m compileall app tests
uv run docling-system-eval-corpus
curl -sS http://127.0.0.1:8000/documents/<document_id>/evaluations/latest | jq
```

Passing results:

- `uv run pytest tests` -> `44 passed, 1 skipped`
- `uv run python -m compileall app tests` passed
- migration to `0008_run_evaluations` passed
- batch evaluation over the configured corpus completed successfully

Live runtime checks:

- API health check succeeded
- document list now includes `latest_evaluation`
- latest evaluation route returns persisted query-level rows

## Known Gaps / Risks

### 1. Evaluation Does Not Yet Gate Promotion

This is deliberate for now, but it means:

- a retrieval regression can still be promoted if validation passes

That is a good v1 default while metrics are new, but not the likely end state.

### 2. Query-Level Deltas Need Longitudinal Baselines

The schema supports:

- `baseline_run_id`
- `baseline_rank`
- `rank_delta`

But the currently persisted corpus evaluation rows were created without baselines.

To make regression deltas useful in practice, the next session should evaluate reprocess runs against the prior active run before promotion.

### 3. `UPC_Appendix_B.pdf` Is In The Document Set But Not In The Eval Corpus

There is an active document for:

- `UPC_Appendix_B.pdf`

It has:

- validation `passed`
- `table_count=0`
- no evaluation fixture match

This is not a correctness issue, but it is an example of a document in the system that is outside the current fixed eval set.

### 4. Worktree Is Not Clean

This session’s evaluation work is not committed yet.

Current modified/untracked files include:

- runtime files
- UI files
- new migration
- new evaluation schema/service
- tests

Do not assume the branch is committed or pushed past `d409f39`.

## Next Steps For The Next Session

### Priority 1: Decide Whether Evaluation Should Influence Promotion

Recommended path:

1. keep validation as the hard promotion gate
2. add explicit policy for eval-based warnings vs blocking failures
3. only make evaluation gating mandatory after baseline deltas are stable and trusted

### Priority 2: Capture Real Baseline Deltas On Reprocess

Implement or tighten the worker/evaluator behavior so:

- candidate run evaluates against prior active run
- query rows persist real `baseline_rank` and `rank_delta`

This is the missing step that turns the evaluation schema into a true regression tracker.

### Priority 3: Expand Corpus Richness

The current corpus now covers five named fixtures, but query coverage is still sparse.

Best next move:

- add more query cases per fixture
- explicitly include mode and filters where it matters
- add negative or adversarial queries where ranking confusion is likely

### Priority 4: Commit This Milestone

Suggested workflow:

```bash
git status
git add ...
git commit -m "Add run-scoped evaluation and query regression tracking"
```

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

List documents:

```bash
curl -sS http://127.0.0.1:8000/documents | jq
```

Read latest evaluation:

```bash
curl -sS http://127.0.0.1:8000/documents/<document_id>/evaluations/latest | jq
```

Evaluate one run:

```bash
uv run docling-system-eval-run <run_id>
```

Evaluate one run against a baseline:

```bash
uv run docling-system-eval-run <candidate_run_id> --baseline-run-id <baseline_run_id>
```

Evaluate all matching active fixtures:

```bash
uv run docling-system-eval-corpus
```

Run full tests:

```bash
uv run pytest tests
```
