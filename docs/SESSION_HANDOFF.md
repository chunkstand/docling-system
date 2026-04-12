# Session Handoff

Date: 2026-04-12 local / 2026-04-12 UTC verification
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
PR: `#1` `Build docling-system v1 ingestion, retrieval, evaluation, and run audit surfaces`
PR URL: `https://github.com/chunkstand/docling-system/pull/1`
Latest committed checkpoint before this handoff update: `ce4da3f` (`Add search feedback and replay lab`)

## Executive Summary

The branch now includes:

- Lopopolo milestone 2 quality surfaces
- legacy audit-field backfill so historical rows satisfy the current audit contract
- persisted search-request telemetry, feedback labels, replay suites, replay comparison, and ranking-dataset export
- a replay/quality operator UI that now exposes both replay execution and replay comparison controls
- a green live `docling-system-audit` result after migration `0011_search_feedback_replays`

What is now true:

- validation still gates promotion
- evaluation still does not gate promotion
- search requests are durable first-class records
- replay and trend surfaces exist in both the API and the operator UI
- the local corpus passes the current audit contract live

## What Landed Recently

### 1. Lopopolo Milestone 2

Commit:

- `0e41420` `Implement Lopopolo milestone 2 quality surfaces`

What changed:

- expanded `docling-system-audit` in `app/services/audit.py`
- added quality aggregation in `app/services/quality.py`
- added quality schemas in `app/schemas/quality.py`
- added:
  - `GET /quality/summary`
  - `GET /quality/failures`
  - `GET /quality/evaluations`
- added a quality panel to the UI

### 2. Legacy Audit Backfill

Commit:

- `5e98907` `Backfill legacy audit fields`

What changed:

- added reusable backfill logic in `app/services/cleanup.py`
- added CLI `docling-system-backfill-legacy-audit`
- normalized historical `figure_count` and `failure_stage` drift

Durable result:

- live `docling-system-audit` returned zero violations after the backfill

### 3. Retrieval Feedback And Replay Lab

Commit:

- `ce4da3f` `Add search feedback and replay lab`

What changed:

- added durable replay/feedback persistence in:
  - `app/db/models.py`
  - `alembic/versions/0011_search_feedback_replays.py`
- added replay and dataset services in:
  - `app/services/search_history.py`
  - `app/services/search_replays.py`
  - `app/services/quality.py`
- added API routes in `app/api/main.py`:
  - `POST /search/requests/{search_request_id}/feedback`
  - `GET /search/replays`
  - `POST /search/replays`
  - `GET /search/replays/{replay_run_id}`
  - `GET /search/replays/compare`
  - `GET /quality/trends`
- added CLI commands:
  - `uv run docling-system-run-replay-suite <source_type> --limit N`
  - `uv run docling-system-export-ranking-dataset --limit N`
- updated the UI to show:
  - search feedback labels
  - replay-run history
  - replay execution controls
  - replay comparison controls
  - search and feedback trend summaries

Relevant files:

- `app/api/main.py`
- `app/cli.py`
- `app/db/models.py`
- `app/schemas/search.py`
- `app/schemas/quality.py`
- `app/services/search_history.py`
- `app/services/search_replays.py`
- `app/services/quality.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `app/ui/styles.css`
- `README.md`
- `tests/unit/test_search_api.py`
- `tests/unit/test_search_replays.py`
- `tests/unit/test_quality_api.py`
- `tests/unit/test_quality_service.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_ui.py`

### 4. Gap-Closing Follow-Up

This handoff update also closes the post-milestone gaps that were still open after `ce4da3f`:

- the UI now exposes replay creation and replay comparison instead of only listing replay runs
- `README.md` now documents the replay/feedback endpoints and CLI commands
- this handoff reflects the current migration head and runtime state instead of the older milestone-2 state

## Current Runtime State

At handoff time:

- API health check succeeds at `http://127.0.0.1:8000/health`
- the API was restarted after the `0011_search_feedback_replays` migration
- the worker was restarted after the same migration
- Alembic head in the running database is `0011_search_feedback_replays`
- `docling-system-audit` completes live with zero violations
- the active/evaluated corpus remains eight documents

Live audit result:

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

Recent live replay/feedback verification:

- persisted direct search requests return `X-Search-Request-Id`
- request detail includes persisted rerank features and feedback labels
- `POST /search/requests/{id}/feedback` persists both ranked-result feedback and request-level `no_answer`
- `POST /search/replays` succeeded for `feedback` and `live_search_gaps`
- `GET /search/replays/compare` returned shared-query regression/improvement summaries
- `uv run docling-system-run-replay-suite feedback --limit 3` completed live
- `uv run docling-system-export-ranking-dataset --limit 5` emitted feedback and replay rows live

## Active Corpus State

Current active/evaluated set:

- `UPC_CH_5.pdf` -> fixture `upc_ch5`
- `UPC_CH_4.pdf` -> fixture `upc_ch4`
- `UPC_Appendix_N.pdf` -> fixture `born_digital_simple`
- `UPC_Appendix_B.pdf` -> fixture `appendix_b_prose_guidance`
- `UPC_CH_3.pdf` -> fixture `awkward_headers`
- `UPC_Ch_2.pdf` -> fixture `upc_ch2_figures`
- `UPC_CH_7.pdf` -> fixture `upc_ch7`
- `UPC_CH_1.pdf` -> fixture `prose_control`

## Verification Performed

Commands run and observed passing recently:

```bash
uv run ruff check app/api/main.py app/cli.py app/db/models.py app/schemas/search.py app/schemas/quality.py app/services/search_history.py app/services/search_replays.py app/services/quality.py alembic/versions/0011_search_feedback_replays.py tests/unit/test_search_api.py tests/unit/test_quality_api.py tests/unit/test_quality_service.py tests/unit/test_cli.py tests/unit/test_search_replays.py tests/unit/test_ui.py
uv run pytest tests/unit -q
uv run python -m compileall app tests
node --check app/ui/app.js
uv run alembic upgrade head
uv run docling-system-run-replay-suite feedback --limit 3
uv run docling-system-export-ranking-dataset --limit 5
uv run docling-system-audit
```

Key results:

- full unit suite passed
- JS syntax check passed
- compileall passed
- migration `0011_search_feedback_replays` applied live
- replay and export commands completed live
- audit stayed green after the new migration

## Current Contracts To Preserve

### Promotion

- validation still hard-gates promotion
- evaluation still does not block promotion

### Evaluation

- the fixed corpus in `docs/evaluation_corpus.yaml` remains the durable retrieval contract
- replay suites and mined candidates complement the fixed corpus; they do not replace it

### Search Telemetry

- every direct `/search` request persists a durable search-request record
- feedback labels are durable operator annotations, not transient UI state
- replay suites should consume persisted requests, feedback, and eval rows instead of recomputing ad hoc query lists in the browser

### Replay

- replay runs are persisted first-class records
- comparison is keyed by shared `(query_text, mode, filters)` identity
- ranking dataset export is a derived operator artifact, not a source of truth

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

### Supplements

- chapter PDFs remain canonical
- supplement PDFs remain narrow repair inputs only
- overlay outputs must preserve chapter-local page spans and original source-segment provenance

## Remaining Gaps / Risks

### 1. Evaluation Still Does Not Gate Promotion

Still deliberate. Retrieval quality can regress while promotion still advances if validation passes.

### 2. Replay UI Is Operational, Not Deeply Analytical Yet

The UI now runs and compares replay suites, but it is still a thin operator surface:

- no per-query drilldown modal for replay rows
- no persistent baseline pinning in the UI
- no charted trend history beyond list cards

### 3. Reranking Is Still Heuristic

The new harness is in place, but the reranker remains `heuristic_v1`. The main leverage now is harvesting labels and replay deltas to support a learned reranker or better scoring model later.

### 4. README And Handoff Are Current, But Product Docs Are Still Thin

The operator-facing commands and endpoints are documented. The deeper design contract for search telemetry, replay semantics, and dataset export still lives mostly in code and tests.

## Recommended Next Steps

### Priority 1: Learned-Ranking Prep

- add richer rerank feature snapshots where useful
- define the first offline ranking objective from replay and feedback rows
- add a pluggable reranker interface for experiments behind eval/replay gates

### Priority 2: Replay Drilldown

- expose replay-run detail in the UI
- show changed queries, removed hits, and added hits per replay row
- add a stable baseline pin or “compare to latest previous successful run” control

### Priority 3: Export And Operator Contracts

- document the ranking-dataset export schema
- document replay pass/fail semantics by source type
- document when feedback labels should be used versus when fixed-corpus evals should be extended

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

Quality:

```bash
curl -sS http://127.0.0.1:8000/quality/summary | jq
curl -sS http://127.0.0.1:8000/quality/failures | jq
curl -sS http://127.0.0.1:8000/quality/evaluations | jq
curl -sS http://127.0.0.1:8000/quality/eval-candidates | jq
curl -sS http://127.0.0.1:8000/quality/trends | jq
```

Replay:

```bash
uv run docling-system-replay-search <search_request_id>
uv run docling-system-run-replay-suite feedback --limit 12
uv run docling-system-run-replay-suite live_search_gaps --limit 12
uv run docling-system-export-ranking-dataset --limit 200
curl -sS "http://127.0.0.1:8000/search/replays/compare?baseline_replay_run_id=<id>&candidate_replay_run_id=<id>" | jq
```

Audit / cleanup:

```bash
uv run docling-system-backfill-legacy-audit
uv run docling-system-audit
```

Open the PR:

```text
https://github.com/chunkstand/docling-system/pull/1
```
